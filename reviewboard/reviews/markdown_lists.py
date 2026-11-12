"""Markdown list indentation that matches GitHub.

Python-Markdown only nests content inside a list item when it's indented by 4
spaces per level. In GFM and CommonMark, content belongs to an item when it
lines up with where the item's text starts (2 spaces for "- item" and 3 for
"1. item").

This re-indents list content from the CommonMark layout to 4-space indentation.

Version Added:
    9.0
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from markdown.extensions import Extension
from markdown.preprocessors import Preprocessor

if TYPE_CHECKING:
    from collections.abc import Sequence

    from markdown import Markdown


#: The number of spaces Python-Markdown wants for each level of nesting.
_NEST_INDENT = 4

#: The most spaces a list marker can be indented past its container.
#:
#: Any more makes it an indented code block.
_MAX_MARKER_INDENT = 3

#: Regex for blockquote markers.
_QUOTE_MARKER_RE = re.compile(r' {0,3}> ?')

#: Regex for list items.
_LIST_ITEM_RE = re.compile(
    r'^(?P<indent> *)(?P<marker>[-*+]|\d{1,9}[.)])(?P<space> *)(?P<text>.*)$')

#: Regex for a thematic break indicator.
_THEMATIC_BREAK_RE = re.compile(r'^ {0,3}([-*_])(?: *\1){2,} *$')

#: Regex for code fences.
_FENCE_RE = re.compile(r'^ *(?P<fence>`{3,}|~{3,})')


class _Context:
    """The lists and code fence open in one level of blockquotes.

    Version Added:
        9.0
    """

    ######################
    # Instance variables #
    ######################

    #: The column where the text starts for each open list item.
    content_cols: list[int]

    #: The fence of the open fenced code block, if any.
    fence: str | None

    def __init__(self) -> None:
        """Initialize the context."""
        self.content_cols = []
        self.fence = None


def normalize_list_indentation(
    lines: Sequence[str],
) -> list[str]:
    """Re-indent list content so Python-Markdown nests it like GitHub.

    Content indented to where its list item's text starts belongs to that
    item. This method will normalize it to 4 spaces per level so
    Python-Markdown treats it properly. Any extra indentation (such as for
    code blocks) will be preserved.

    Version Added:
        9.0

    Args:
        lines (list of str):
            The lines of Markdown, with tabs already expanded.

    Returns:
        list of str:
        The re-indented lines.
    """
    contexts: list[_Context] = [_Context()]
    result: list[str] = []

    for line in lines:
        # Text in a fenced code block may start with ">", which isn't a
        # blockquote. Only look as deep as the open fence.
        max_depth: (int | None) = None

        for depth, context in enumerate(contexts):
            if context.fence is not None:
                max_depth = depth
                break

        prefix, quote_depth = _split_quote_prefix(line, max_depth)
        text = line[len(prefix):]

        # A blockquote marker closes any items at the levels outside it that
        # it isn't indented far enough to be inside.
        pos = 0

        for context in contexts[:quote_depth]:
            m = _QUOTE_MARKER_RE.match(line, pos)
            assert m

            marker_indent = len(m.group()) - len(m.group().lstrip(' '))
            content_cols = context.content_cols

            while content_cols and marker_indent < content_cols[-1]:
                content_cols.pop()

            pos = m.end()

        # Leaving a blockquote closes everything inside it.
        del contexts[quote_depth + 1:]

        while len(contexts) <= quote_depth:
            contexts.append(_Context())

        if text.strip():
            text = _normalize_line(text, contexts[quote_depth])

        result.append(prefix + text)

    return result


def _split_quote_prefix(
    line: str,
    max_depth: (int | None) = None,
) -> tuple[str, int]:
    """Return the blockquote markers at the start of a line.

    Version Added:
        9.0

    Args:
        line (str):
            The line.

        max_depth (int, optional):
            The most blockquote markers to take.

    Returns:
        tuple:
        A 2-tuple of the markers and how many there are.
    """
    pos = 0
    depth = 0

    while max_depth is None or depth < max_depth:
        m = _QUOTE_MARKER_RE.match(line, pos)

        if not m:
            break

        pos = m.end()
        depth += 1

    return line[:pos], depth


def _normalize_line(
    line: str,
    context: _Context,
) -> str:
    """Re-indent one line within a blockquote level.

    Version Added:
        9.0

    Args:
        line (str):
            The line, without any blockquote prefix. This isn't blank.

        context (_Context):
            The lists and fence open at this level.

    Returns:
        str:
        The re-indented line.
    """
    content_cols = context.content_cols
    indent = len(line) - len(line.lstrip(' '))

    if context.fence is not None:
        # Lines in a fenced code block move with the block, but aren't
        # parsed.
        stripped = line.strip()

        if (stripped.startswith(context.fence) and
            stripped == stripped[0] * len(stripped)):
            context.fence = None

        if content_cols and indent >= content_cols[-1]:
            return _shift(line, indent, content_cols)

        return line

    # Close any items this line isn't indented far enough to be inside.
    while content_cols and indent < content_cols[-1]:
        content_cols.pop()

    m = _LIST_ITEM_RE.match(line)

    if content_cols:
        max_marker_indent = content_cols[-1] + _MAX_MARKER_INDENT
    else:
        max_marker_indent = _MAX_MARKER_INDENT

    if (m and
        (m.group('space') or not m.group('text')) and
        indent <= max_marker_indent and
        not _THEMATIC_BREAK_RE.match(line)):
        # A new list item. Its text starts after the marker and the spaces
        # after it. More than 4 spaces means the text is a code block, so
        # only 1 of them counts.
        num_spaces = len(m.group('space'))

        if num_spaces == 0 or num_spaces > _NEST_INDENT:
            num_spaces = 1

        new_indent = _NEST_INDENT * len(content_cols)
        content_cols.append(indent + len(m.group('marker')) + num_spaces)

        return ' ' * new_indent + line[indent:]

    m = _FENCE_RE.match(line)

    if m:
        context.fence = m.group('fence')

    return _shift(line, indent, content_cols)


def _shift(
    line: str,
    indent: int,
    content_cols: Sequence[int],
) -> str:
    """Move a line of item content to Python-Markdown's indentation.

    Version Added:
        9.0

    Args:
        line (str):
            The line.

        indent (int):
            The number of spaces the line starts with.

        content_cols (list of int):
            The column where the text starts for each open list item. The
            line belongs to the last one.

    Returns:
        str:
        The moved line.
    """
    if not content_cols:
        return line

    new_indent = _NEST_INDENT * len(content_cols) + indent - content_cols[-1]

    return ' ' * new_indent + line[indent:]


class _ListIndentPreprocessor(Preprocessor):
    """Re-indents list content before the Markdown is parsed.

    Version Added:
        9.0
    """

    def run(
        self,
        lines: list[str],
    ) -> list[str]:
        """Re-indent the lines.

        Args:
            lines (list of str):
                The lines of Markdown.

        Returns:
            list of str:
            The re-indented lines.
        """
        return normalize_list_indentation(lines)


class ListIndentExtension(Extension):
    """Nests Markdown list content like GitHub.

    Version Added:
        9.0
    """

    def extendMarkdown(  # noqa: N802
        self,
        md: Markdown,
    ) -> None:
        """Add the preprocessor to the Markdown instance.

        This runs after tabs are expanded, and before fenced code blocks
        are pulled out.

        Args:
            md (markdown.Markdown):
                The Markdown instance.
        """
        md.preprocessors.register(_ListIndentPreprocessor(md),
                                  'md_list_indent', 28)
