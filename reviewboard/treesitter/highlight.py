"""Tree-sitter based syntax highlighting.

Version Added:
    9.0
"""

from __future__ import annotations

import itertools
import logging
from collections import defaultdict
from typing import TYPE_CHECKING

import tree_sitter

from reviewboard.treesitter.core import (
    get_language,
    get_parser,
    get_queries,
)
from reviewboard.treesitter.debug import DEBUG_TREESITTER
from reviewboard.treesitter.language import SUPPORTED_LANGUAGES
from reviewboard.treesitter.predicates import create_predicate_handler

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence
    from typing import TypeAlias

    from reviewboard.treesitter.language import SupportedLanguage


logger = logging.getLogger(__name__)


#: A set of highlight classes that are supported by our syntax CSS.
#:
#: Version Added:
#:     9.0
HIGHLIGHT_CLASSES = {
    'attribute.builtin',
    'boolean',
    'comment',
    'operator',
    'constructor',
    'keyword',
    'keyword.import',
    'number',
    'constant',
    'constant.builtin',
    'function',
    'function.builtin',
    'function.call',
    'function.method.call',
    'module',
    'string',
    'string.regexp',
    'tag',
    'tag.attribute',
    'type.builtin',
    'variable',
    'variable.builtin',
}


#: Highlight classes to explicitly ignore.
#:
#: This set is dynamically updated during runtime as we discover
#: capture names that don't map to any highlighting classes.
#:
#: Version Added:
#:     9.0
HIGHLIGHT_IGNORE = {
    'none',
    'punctuation',
    'punctuation.bracket',
    'punctuation.delimiter',
    'punctuation.special',
    'spell',
    'tag.delimiter',
}


#: Type aliases for a highlighted node.
#:
#: Version Added:
#:     9.0
HighlightNode: TypeAlias = tuple[str, int, int]


#: Index constants for HighlightNode tuple access.
#:
#: Version Added:
#:     9.0
NODE_NAME = 0
NODE_START = 1
NODE_END = 2


#: Type alias for a highlight event.
#:
#: Version Added:
#:     9.0
HighlightEvent: TypeAlias = tuple[str, int]

#: Index constants for HighlightEvent tuple access.
#:
#: Version Added:
#:     9.0
EVENT_TAG = 0
EVENT_POSITION = 1


#: Information about a highlight capture.
#:
#: Version Added:
#:     9.0
HighlightCapture: TypeAlias = (
    tuple[
        str,  # capture name
        int,  # start row
        int,  # start column
        int,  # end row
        int,  # end column
    ] |
    # When DEBUG_TREESITTER is True, this includes the node.text so we can
    # print out the content of certain captures. This makes it easier to decide
    # how to assign CSS classes to capture names.
    tuple[str, int, int, int, int, bytes]
)


#: Index constants for HighlightCapture tuple access.
#:
#: Version Added:
#:     9.0
HIGHLIGHT_CAPTURE_NAME = 0
HIGHLIGHT_CAPTURE_START_ROW = 1
HIGHLIGHT_CAPTURE_START_COL = 2
HIGHLIGHT_CAPTURE_END_ROW = 3
HIGHLIGHT_CAPTURE_END_COL = 4
HIGHLIGHT_CAPTURE_NODE_TEXT = 5


def _get_nodes_by_line(
    captures: Iterable[HighlightCapture],
    lines: Sequence[str],
) -> list[Sequence[HighlightNode]]:
    """Get the nodes for each line.

    Version Added:
        9.0

    Args:
        captures (iterator of HighlightCapture):
            The captures dictionary from the highlight query.

        lines (list of str):
            The file content, split into lines.

    Returns:
        list of list of HighlightNode:
        The nodes for each line.
    """
    def _byte_to_char_pos(
        line: str,
        line_bytes: bytes,
        byte_pos: int,
    ) -> int:
        if byte_pos == 0:
            return 0
        elif byte_pos >= len(line_bytes):
            return len(line)
        else:
            return len(line_bytes[:byte_pos].decode('utf-8'))

    nodes_by_line: list[list[HighlightNode]] = [[] for _ in range(len(lines))]

    lines_bytes: list[bytes | None] = [None for _ in range(len(lines))]

    for highlight_capture in captures:
        name = highlight_capture[HIGHLIGHT_CAPTURE_NAME]
        start_row = highlight_capture[HIGHLIGHT_CAPTURE_START_ROW]
        start_col = highlight_capture[HIGHLIGHT_CAPTURE_START_COL]
        end_row = highlight_capture[HIGHLIGHT_CAPTURE_END_ROW]
        end_col = highlight_capture[HIGHLIGHT_CAPTURE_END_COL]

        # Convert byte positions to character positions.
        start_line = lines[start_row]
        start_line_bytes = lines_bytes[start_row]

        if start_line_bytes is None:
            start_line_bytes = lines[start_row].encode()
            lines_bytes[start_row] = start_line_bytes

        end_line = lines[end_row]
        end_line_bytes = lines_bytes[end_row]

        if end_line_bytes is None:
            end_line_bytes = lines[end_row].encode()
            lines_bytes[end_row] = end_line_bytes

        start_char_col = _byte_to_char_pos(
            start_line, start_line_bytes, start_col)
        end_char_col = _byte_to_char_pos(
            end_line, end_line_bytes, end_col)

        # The captured nodes from highlight queries can include nodes that
        # span multiple lines (for example, an entire python docstring
        # will be identified as a single string node).
        #
        # If the node does cover multiple lines, split it up into multiple
        # pieces.
        if start_row == end_row:
            nodes_by_line[start_row].append(
                (name, start_char_col, end_char_col))
        else:
            line_end = len(lines[start_row])
            nodes_by_line[start_row].append(
                (name, start_char_col, line_end))

            for i in range(start_row + 1, end_row):
                nodes_by_line[i].append((name, 0, len(lines[i])))

            nodes_by_line[end_row].append((name, 0, end_char_col))

        if DEBUG_TREESITTER and name in {
            'string.escape',
            'type.definition',
        }:
            assert len(highlight_capture) == 6
            node_text = highlight_capture[HIGHLIGHT_CAPTURE_NODE_TEXT]
            logger.debug('TreeSitter capture: %s = %r', name, node_text)

    # Process all lines at once and return complete collection
    result: list[Sequence[HighlightNode]] = []

    for nodes in nodes_by_line:
        if len(nodes) <= 1:
            result.append(nodes)
        else:
            # Sort first in order of start column, and second for the longest
            # items first (since some captures are contained within others).
            result.append(sorted(
                nodes,
                key=lambda node: (node[NODE_START],
                                  node[NODE_START] - node[NODE_END])))

    return result


#: Cache mapping capture name to <span> tag for highlights.
#:
#: Version Added:
#:     9.0
_highlight_tag_cache: dict[str, str | None] = {}


def _find_matching_highlight_tag(
    capture_name: str,
) -> str | None:
    """Return a matching highlight span tag for a capture name.

    Version Added:
        9.0

    Args:
        capture_name (str):
            The name of the capture group.

    Returns:
        str:
        The opening span tag to use for highlighting. If the capture group is
        not supported for highlighting, this will return ``None``.
    """
    if capture_name in HIGHLIGHT_IGNORE:
        return None

    try:
        return _highlight_tag_cache[capture_name]
    except KeyError:
        if capture_name in HIGHLIGHT_CLASSES:
            class_name = capture_name.replace('.', '-')
            result = f'<span class="ts-{class_name}">'
        elif '.' in capture_name:
            result = _find_matching_highlight_tag(
                capture_name.rsplit('.', 1)[0])
        else:
            result = None

        if result is not None:
            _highlight_tag_cache[capture_name] = result
        else:
            HIGHLIGHT_IGNORE.add(capture_name)

        return result


def _get_events_by_line(
    nodes_by_line: Sequence[Sequence[HighlightNode]],
) -> Sequence[Sequence[HighlightEvent]]:
    """Get the highlight events for each line.

    Version Added:
        9.0

    Args:
        nodes_by_line (list of list of HighlightNode):
            The sequence of lists of nodes for each line.

    Returns:
        list of list of HighlightEvent:
        The events for each line.
    """
    result: list[Sequence[HighlightEvent]] = []

    for nodes in nodes_by_line:
        events: list[HighlightEvent] = []
        # Track spans we've already added to avoid duplicates. Many grammars
        # will add events such as "string" and "string.documentation" for the
        # same spans. If we don't do this, the resulting HTML will have
        # <span class="ts-string"><span class="ts-string">...</span></span>
        # for instances like that.
        added_spans: set[tuple[str, int, int]] = set()

        for node_name, start, end in nodes:
            if span_tag := _find_matching_highlight_tag(node_name):
                span_key = (span_tag, start, end)

                if span_key not in added_spans:
                    events.append((span_tag, start))
                    events.append(('</span>', end))

                    added_spans.add(span_key)

        if len(events) <= 1:
            # Skip sorting if there's one or fewer event.
            result.append(events)
        else:
            result.append(sorted(
                events, key=lambda event: event[EVENT_POSITION]))

    return result


def _apply_events(
    lines: Sequence[str],
    events_by_line: Sequence[Sequence[HighlightEvent]],
) -> list[str]:
    """Apply highlight events to all lines at once.

    Version Added:
        9.0

    Args:
        lines (sequence of str):
            The lines to highlight.

        events_by_line (sequence of sequence of HighlightEvent):
            The events to apply to each line.

    Returns:
        list of str:
        The highlighted lines with HTML tags added.
    """
    # Pre-allocate result list with correct size for better performance.
    result = [''] * len(lines)

    # HTML escape characters for inline processing.
    html_escape_chars = {
        ord('&'): '&amp;',
        ord('<'): '&lt;',
        ord('>'): '&gt;',
        ord("'"): '&#39;',
        ord('"'): '&quot;',
    }

    # Apply events to each line.
    for i, (line, events) in enumerate(zip(lines, events_by_line)):
        if not events:
            # Simple case of a line with no highlight events.
            result[i] = line.translate(html_escape_chars)
        else:
            parts: list[str] = []
            event_i = 0
            n_events = len(events)
            last_pos = 0

            for pos in range(len(line) + 1):
                # Apply any events at the current position.
                while (event_i < n_events and
                       events[event_i][EVENT_POSITION] == pos):
                    # Add escaped text segment before this event.
                    if pos > last_pos:
                        parts.append(
                            line[last_pos:pos].translate(html_escape_chars))
                        last_pos = pos

                    parts.append(events[event_i][EVENT_TAG])
                    event_i += 1

            # Add any remaining text.
            if last_pos < len(line):
                parts.append(line[last_pos:].translate(html_escape_chars))

            result[i] = ''.join(parts)

    return result


def _highlight_tree(
    tree: tree_sitter.Tree,
    root_node: tree_sitter.Node,
    language_name: SupportedLanguage,
) -> Sequence[HighlightCapture]:
    """Highlight a subtree with a given language.

    Version Added:
        9.0

    Args:
        tree (tree_sitter.Tree):
            The tree sitter tree to apply highlighting to.

        root_node (tree_sitter.Node):
            The node to apply highlighting to.

        language_name (reviewboard.treesitter.language.SupportedLanguage):
            The name of the language to use for highlighting.

    Returns:
        list of HighlightCapture:
        Information about each captured range.
    """
    queries = get_queries(language_name, 'highlights.scm')

    if not queries:
        return []

    ts_language = get_language(language_name)
    query = tree_sitter.Query(ts_language, queries)
    predicate_handler = create_predicate_handler(query=query)
    cursor = tree_sitter.QueryCursor(query)
    captures = cursor.captures(root_node, predicate_handler)

    if not captures:
        return []

    # Filter out any captures which we know do not correspond to highlighting
    # classes.
    names = set(captures.keys()) - HIGHLIGHT_IGNORE

    result: list[HighlightCapture] = []

    # We sort these by largest capture name first so that more-specific
    # captures (eg. constant.builtin) will take precedence over less-specific
    # ones (constant).
    for name in sorted(names, key=lambda name: (-len(name), name)):
        nodes = captures[name]

        for node in nodes:
            node_text = node.text

            if node_text is None:
                continue

            start_point = node.start_point
            end_point = node.end_point

            if DEBUG_TREESITTER:
                result.append((
                    name,
                    start_point.row,
                    start_point.column,
                    end_point.row,
                    end_point.column,
                    node_text,
                ))
            else:
                result.append((
                    name,
                    start_point.row,
                    start_point.column,
                    end_point.row,
                    end_point.column,
                ))

    return result


def _highlight_injections(
    *,
    content: bytes,
    language_name: SupportedLanguage,
    ranges: Sequence[tree_sitter.Range],
) -> Sequence[HighlightCapture]:
    """Highlight an injected language.

    In TreeSitter, an "injection" is a region of a document that should be
    highlighted using a different language. Examples of this include
    ``<script>`` and ``<style>`` tags in HTML files or fenced code blocks
    in Markdown documents.

    Args:
        content (bytes):
            The file content.

        language_name (reviewboard.treesitter.language.SupportedLanguage):
            The name of the language to highlight the node with.

        ranges (list of tree_sitter.Range):
            The ranges that should be highlighted using this language.

    Yields:
        HighlightCapture:
        The captured highlighted regions.
    """
    logger.debug('Highlighting injections for language %s',
                 language_name)

    parser = get_parser(language_name)

    try:
        parser.included_ranges = ranges
        tree = parser.parse(content)

        return _highlight_tree(tree, tree.root_node, language_name)
    finally:
        del parser.included_ranges


def highlight(
    content: bytes,
    lines: Sequence[str],
    tree: tree_sitter.Tree,
    language_name: SupportedLanguage,
) -> Sequence[str] | None:
    """Apply highlighting to a file.

    Version Added:
        9.0

    Args:
        content (bytes):
            The file content.

        lines (list of str):
            A list of lines in the file.

        tree (tree_sitter.Tree):
            The parsed syntax tree.

        language_name (reviewboard.treesitter.language.SupportedLanguage):
            The language for the file.

    Returns:
        list of str:
        A list of lines, with syntax highlighting applied.
    """
    if language_name not in SUPPORTED_LANGUAGES:
        logger.warning('Highlighting requested for unsupported language %s',
                       language_name)

        return None

    logger.debug('Highlighting file for language %s',
                 language_name)

    captures = _highlight_tree(tree, tree.root_node, language_name)

    if not captures:
        return None

    chained_captures = [captures]

    injections_queries = get_queries(language_name, 'injections.scm')

    if injections_queries:
        ts_language = get_language(language_name)
        injections_query = tree_sitter.Query(ts_language, injections_queries)
        predicate_handler = create_predicate_handler(query=injections_query)
        cursor = tree_sitter.QueryCursor(injections_query)
        matches = cursor.matches(tree.root_node, predicate_handler)

        injection_ranges: defaultdict[
            SupportedLanguage,
            set[tree_sitter.Range]
        ] = defaultdict(set)

        for pattern_index, match in matches:
            nodes = match.get('injection.content')

            if not nodes:
                continue

            if 'injection.language' in match:
                language_node = match['injection.language'][0]
                language_text = language_node.text
                assert language_text is not None

                matched_lang = language = language_text.decode()
            else:
                matched_lang = None

            for node in nodes:
                injection_lang = matched_lang

                # Other queries may use set! or gsub! to store the language in
                # the pattern settings.
                if not injection_lang:
                    settings = injections_query.pattern_settings(pattern_index)
                    injection_lang = settings.get('injection.language')

                if (injection_lang is None or
                    injection_lang not in SUPPORTED_LANGUAGES):
                    continue

                injection_ranges[injection_lang].add(node.range)

        for language, ranges in injection_ranges.items():
            chained_captures.append(_highlight_injections(
                content=content,
                language_name=language,
                ranges=sorted(ranges, key=lambda range: range.start_byte),
            ))

    nodes_by_line = _get_nodes_by_line(itertools.chain(*chained_captures),
                                       lines)
    events_by_line = _get_events_by_line(nodes_by_line)

    return _apply_events(lines, events_by_line)
