"""Methods for finding interesting lines in code.

Version Added:
    9.0
"""

from __future__ import annotations

import logging
import os
import re
from functools import lru_cache
from typing import TYPE_CHECKING

import tree_sitter

from reviewboard.treesitter.core import get_language, get_queries
from reviewboard.treesitter.predicates import create_predicate_handler

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from typing import TypeAlias

    from reviewboard.treesitter.language import SupportedLanguage


logger = logging.getLogger(__name__)


# A list of regular expressions for headers in the source code that we can
# display in collapsed regions of diffs and diff fragments in reviews.
HEADER_REGEXES: Mapping[str, list[re.Pattern[str]]] = {
    '.cs': [
        re.compile(
            r'^\s*((public|private|protected|static)\s+)+'
            r'([a-zA-Z_][a-zA-Z0-9_\.\[\]]*\s+)+?'     # return arguments
            r'[a-zA-Z_][a-zA-Z0-9_]*'                  # method name
            r'\s*\('                                   # signature start
        ),
        re.compile(
            r'^\s*('
            r'(public|static|private|protected|internal|abstract|partial)'
            r'\s+)*'
            r'(class|struct)\s+([A-Za-z0-9_])+'
        ),
    ],

    # This can match C/C++/Objective C header files
    '.c': [
        re.compile(r'^@(interface|implementation|class|protocol)'),
        re.compile(r'^[A-Za-z0-9$_]'),
    ],
    '.java': [
        re.compile(
            r'^\s*((public|private|protected|static)\s+)+'
            r'([a-zA-Z_][a-zA-Z0-9_\.\[\]]*\s+)+?'     # return arguments
            r'[a-zA-Z_][a-zA-Z0-9_]*'                  # method name
            r'\s*\('                                   # signature start
        ),
        re.compile(
            r'^\s*('
            r'(public|static|private|protected)'
            r'\s+)*'
            r'(class|struct)\s+([A-Za-z0-9_])+'
        ),
    ],
    '.js': [
        re.compile(r'^\s*function [A-Za-z0-9_]+\s*\('),
        re.compile(r'^\s*(var\s+)?[A-Za-z0-9_]+\s*[=:]\s*function\s*\('),
    ],
    '.m': [
        re.compile(r'^@(interface|implementation|class|protocol)'),
        re.compile(r'^[-+]\s+\([^\)]+\)\s+[A-Za-z0-9_]+[^;]*$'),
        re.compile(r'^[A-Za-z0-9$_]'),
    ],
    '.php': [
        re.compile(r'^\s*(public|private|protected)?\s*'
                   r'(class|function) [A-Za-z0-9_]+'),
    ],
    '.pl': [
        re.compile(r'^\s*sub [A-Za-z0-9_]+'),
    ],
    '.py': [
        re.compile(r'^\s*(def|class) [A-Za-z0-9_]+\s*\(?'),
    ],
    '.rb': [
        re.compile(r'^\s*(def|class) [A-Za-z0-9_]+\s*\(?'),
    ],
}


HEADER_REGEX_ALIASES = {
    # C/C++/Objective-C
    '.cc': '.c',
    '.cpp': '.c',
    '.cxx': '.c',
    '.c++': '.c',
    '.h': '.c',
    '.hh': '.c',
    '.hpp': '.c',
    '.hxx': '.c',
    '.h++': '.c',
    '.C': '.c',
    '.H': '.c',
    '.mm': '.m',

    # Perl
    '.pm': '.pl',

    # Python
    'SConstruct': '.py',
    'SConscript': '.py',
    '.pyw': '.py',
    '.sc': '.py',

    # Ruby
    'Rakefile': '.rb',
    '.rbw': '.rb',
    '.rake': '.rb',
    '.gemspec': '.rb',
    '.rbx': '.rb',
}


#: A type for an interesting line.
#:
#: This is a 2-tuple of (line number, line content).
#:
#: Version Added:
#:     9.0
InterestingLine: TypeAlias = tuple[int, str]


#: The query capture names used for interesting lines.
#:
#: The vendored ``interesting_lines.scm`` files may contain other captures
#: (such as ``function.inner``), which we ignore.
_INTERESTING_CAPTURES = ('class.outer', 'function.outer')


def _get_interesting_lines_via_regex(
    filename: str,
    file_content: Sequence[str],
) -> Sequence[InterestingLine]:
    """Get interesting lines for a file using regexes.

    Version Added:
        9.0

    Args:
        filename (str):
            The name of the file.

        file_content (list of str):
            The content of the file, split into lines.

    Returns:
        list:
        A list of interesting lines in the file.
    """
    header_regexes: list[re.Pattern[str]] = []

    if filename in HEADER_REGEX_ALIASES:
        header_regexes = HEADER_REGEXES[HEADER_REGEX_ALIASES[filename]]
    else:
        ext = os.path.splitext(filename)[1].lower()

        if ext in HEADER_REGEXES:
            header_regexes = HEADER_REGEXES[ext]
        elif ext in HEADER_REGEX_ALIASES:
            header_regexes = HEADER_REGEXES[HEADER_REGEX_ALIASES[ext]]

    interesting_lines: list[InterestingLine] = []

    ws_only = re.compile(r'^\s*$')

    for line_number, line in enumerate(file_content):
        if ws_only.match(line):
            continue

        for regex in header_regexes:
            if regex.match(line):
                interesting_lines.append((line_number, line))
                break

    return interesting_lines


# TODO: make this configurable the way we do with Pygments lexers.
@lru_cache
def _get_interesting_lines_query(
    language_name: SupportedLanguage,
) -> tree_sitter.Query | None:
    """Return the compiled interesting lines query for a language.

    Version Added:
        9.0

    Args:
        language_name (str):
            The tree-sitter language name.

    Returns:
        tree_sitter.Query:
        The compiled query, or ``None`` if the language has no interesting
        lines queries or they failed to compile.
    """
    queries = get_queries(language_name, 'interesting_lines.scm')

    if not queries:
        return None

    try:
        return tree_sitter.Query(get_language(language_name), queries)
    except Exception as e:
        # A broken query file must not break diff rendering. Fall back to
        # the regex scanner.
        logger.warning('Failed to compile interesting lines queries for '
                       'language %s: %s',
                       language_name, e)

        return None


def _get_interesting_lines_via_ts(
    language_name: SupportedLanguage,
    file_content: Sequence[str],
    tree: tree_sitter.Tree,
) -> Sequence[InterestingLine] | None:
    """Get interesting lines for a file using tree-sitter queries.

    Version Added:
        9.0

    Args:
        language_name (str):
            The tree-sitter language name for the file.

        file_content (list of str):
            The content of the file, split into lines.

        tree (tree_sitter.Tree):
            The parsed tree-sitter tree for the file.

    Returns:
        list:
        A list of interesting lines in the file, or ``None`` if there are
        no queries available for the language or the file could not
        usefully be parsed.
    """
    query = _get_interesting_lines_query(language_name)

    if query is None:
        return None

    predicate_handler = create_predicate_handler(query=query)
    cursor = tree_sitter.QueryCursor(query)
    captures = cursor.captures(tree.root_node, predicate_handler)

    rows: set[int] = set()

    for capture_name in _INTERESTING_CAPTURES:
        for node in captures.get(capture_name, []):
            row = node.start_point.row

            # Guard against error-recovery nodes with odd extents.
            if row < len(file_content):
                rows.add(row)

    if not rows and tree.root_node.has_error:
        # Nothing was found and the file did not parse cleanly. The file
        # may be broken (or not really this language at all), so let the
        # regex scanner have a shot at it. A clean parse with no matches
        # stays authoritative: the file simply has no definitions.
        return None

    return [
        (row, file_content[row])
        for row in sorted(rows)
    ]


def get_interesting_lines(
    *,
    filename: str,
    language_name: SupportedLanguage | None,
    file_content: Sequence[str],
    tree: tree_sitter.Tree | None,
) -> Sequence[InterestingLine]:
    """Get interesting lines for a file.

    Version Added:
        9.0

    Args:
        filename (str):
            The name of the file.

        language_name (str):
            The tree-sitter language name for the file, if available.

        file_content (list of str):
            The content of the file, split into lines.

        tree (tree_sitter.Tree):
            The parsed tree-sitter tree for the file, if available.

    Returns:
        list:
        A list of interesting lines in the file.
    """
    if language_name and tree:
        interesting_lines = _get_interesting_lines_via_ts(
            language_name, file_content, tree)

        if interesting_lines is not None:
            # If the queries ran, their result is authoritative, even when
            # empty. Falling back on an empty result would reintroduce the
            # regex false positives for files that simply have no
            # definitions.
            return interesting_lines

    return _get_interesting_lines_via_regex(filename, file_content)
