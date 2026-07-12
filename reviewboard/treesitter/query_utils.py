"""Methods for interacting with Tree Sitter queries.

Version Added:
    9.0
"""

from __future__ import annotations

import itertools
import re
from functools import lru_cache
from textwrap import dedent
from typing import TYPE_CHECKING

import tree_sitter
from tree_sitter_language_pack import get_language, get_parser

from reviewboard.treesitter.lua_patterns import lua_pattern_to_python

if TYPE_CHECKING:
    from collections.abc import Collection, Iterable, Iterator
    from typing import TypeAlias


#: An edit to make to queries.
#:
#: Version Added:
#:     9.0
#:
#: Tuple:
#:     0 (int):
#:         The start byte of the edit range.
#:
#:     1 (int):
#:         The end byte of the edit range.
#:
#:     2 (bytes):
#:         The content to replace the range with.
QueryEdit: TypeAlias = tuple[int, int, bytes]


@lru_cache(maxsize=1)
def get_query_language() -> tree_sitter.Language:
    """Return a language object for the query language.

    Version Added:
        9.0

    Returns:
        tree_sitter.Language:
        The language object for working with query files.
    """
    return get_language('query')


def apply_edits(
    content: bytes,
    edits: Iterable[QueryEdit],
) -> bytes:
    """Apply edits to a query file.

    Version Added:
        9.0

    Args:
        content (bytes):
            The content of the query file.

        edits (iterable of QueryEdit):
            The edits to apply.

    Returns:
        bytes:
        The edited queries.
    """
    new_content = bytearray(content)

    sorted_edits = sorted(edits, key=lambda edit: edit[0], reverse=True)

    for (start, end, replacement) in sorted_edits:
        new_content[start:end] = replacement

    return bytes(new_content)


@lru_cache(maxsize=1)
def get_set3_directive_query() -> tree_sitter.Query:
    """Return a query for finding set! directives with 3 arguments.

    Version Added:
        9.0

    Returns:
        tree_sitter.Query:
        The query object.
    """
    return tree_sitter.Query(
        get_query_language(),
        dedent("""
            ((predicate
              name: (identifier) @_name
              parameters: (parameters
                (capture) . (identifier) . (_)
              ))
             (#eq? @_name "set"))
        """))


def get_set3_edits(
    tree: tree_sitter.Tree,
) -> Iterator[QueryEdit]:
    """Return edits to filter out set! directives with 3 arguments.

    The queries bundled in nvim-treesitter include a version of #set! that
    accepts three arguments. The implementation of the #set! directive in
    py-tree-sitter errors out if it encounters this, and there's no way for us
    to override this directive at that stage.

    This will find any queries that use #set! with three parameters and filter
    them out.

    Version Added:
        9.0

    Args:
        tree (tree_sitter.Tree):
            The parsed queries.

    Yields:
        QueryEdit:
        Matching regions to edit.
    """
    query = get_set3_directive_query()
    cursor = tree_sitter.QueryCursor(query)
    captures = cursor.captures(tree.root_node)

    for node in captures.get('_name', []):
        while node.parent != tree.root_node and node.parent is not None:
            node = node.parent

        yield (node.start_byte, node.end_byte, b'')


@lru_cache(maxsize=1)
def get_lua_match_query() -> tree_sitter.Query:
    """Return a query for finding all lua-match? predicates.

    Version Added:
        9.0

    Returns:
        tree_sitter.Query:
        The query object.
    """
    return tree_sitter.Query(
        get_query_language(),
        dedent("""
            ((predicate
              name: (identifier) @_name)
             (#any-of? @_name "lua-match" "not-lua-match"))
        """))


def get_lua_match_edits(
    tree: tree_sitter.Tree,
) -> Iterator[QueryEdit]:
    """Return edits to convert lua-match? predicates to match?

    This function finds lua-match? and lua-not-match? predicates in queries
    (which use Lua patterns) and converts them to standard match? and
    not-match? predicates (using Python regexes).

    Version Added:
        9.0

    Args:
        tree (tree_sitter.Tree):
            The parsed queries.

    Yields:
        QueryEdit:
        Matching regions to edit.

    Raises:
        ValueError:
            An unexpected node was found, or the pattern could not be
            converted.
    """
    query = get_lua_match_query()
    cursor = tree_sitter.QueryCursor(query)
    captures = cursor.captures(tree.root_node)

    for node in captures.get('_name', []):
        old_predicate = node.text
        assert old_predicate is not None

        if old_predicate == b'lua-match':
            new_predicate = 'match'
        elif old_predicate == b'not-lua-match':
            new_predicate = 'not-match'
        else:
            raise ValueError(
                f'Query for lua-match predicates found unexpected '
                f'node "{old_predicate.decode()}')

        predicate_node = node.parent
        assert predicate_node is not None

        predicate_args_node = predicate_node.child(4)
        assert predicate_args_node is not None

        predicate_args = predicate_args_node.text
        assert predicate_args is not None

        name, lua_pattern = predicate_args.decode().split(' ', 1)

        python_regex = lua_pattern_to_python(
            lua_pattern.removeprefix('"').removesuffix('"'))

        if python_regex is None:
            raise ValueError(
                f'Lua pattern {lua_pattern} could not be converted into a '
                f'Python regular expression.'
            )

        # The scheme files require backslashes to be escaped.
        python_regex = python_regex.replace('\\', '\\\\')

        replacement = f'(#{new_predicate}? {name} "{python_regex}")'

        yield (predicate_node.start_byte, predicate_node.end_byte,
               replacement.encode())


@lru_cache(maxsize=1)
def get_gsub_query() -> tree_sitter.Query:
    """Return a query for finding all gsub! directives.

    Version Added:
        9.0

    Returns:
        tree_sitter.Query:
        The query object.
    """
    return tree_sitter.Query(
        get_query_language(),
        dedent("""
            ((predicate
              name: (identifier) @_name)
             (#eq? @_name "gsub"))
        """))


def get_gsub_edits(
    tree: tree_sitter.Tree,
) -> Iterator[QueryEdit]:
    """Return edits to convert gsub! directives to use python regexes.

    This function finds gsub! directives in queries and converts their Lua
    pattern arguments to Python regex patterns.

    Version Added:
        9.0

    Args:
        tree (tree_sitter.Tree):
            The parsed queries.

    Yields:
        QueryEdit:
        Matching regions to edit.

    Raises:
        ValueError:
            The directive could not be converted into a python regex.
    """
    query = get_gsub_query()
    cursor = tree_sitter.QueryCursor(query)
    captures = cursor.captures(tree.root_node)

    for node in captures.get('_name', []):
        predicate_node = node.parent
        assert predicate_node is not None

        predicate_args_node = predicate_node.child(4)
        assert predicate_args_node is not None

        predicate_args = predicate_args_node.text
        assert predicate_args is not None

        name, rest = predicate_args.decode().split(' ', 1)
        lua_pattern, lua_replacement = rest.rsplit(' ', 1)

        python_regex = lua_pattern_to_python(
            lua_pattern.removeprefix('"').removesuffix('"'))

        if python_regex is None:
            raise ValueError(
                f'Lua pattern {lua_pattern} could not be converted into a '
                f'Python regular expression.'
            )

        # Convert Lua backreferences (%1, %2, etc.) to Python ones (\1, \2).
        python_replacement = re.sub(r'%(\d+)', r'\\\1', lua_replacement)

        # The scheme files require backslashes to be escaped.
        python_regex = python_regex.replace('\\', '\\\\')
        python_replacement = python_replacement.replace('\\', '\\\\')

        replacement = f'(#gsub! {name} "{python_regex}" {python_replacement})'

        yield (predicate_node.start_byte, predicate_node.end_byte,
               replacement.encode())


@lru_cache(maxsize=1)
def get_all_predicates_query() -> tree_sitter.Query:
    """Return a query for finding all predicates.

    Version Added:
        9.0

    Returns:
        tree_sitter.Query:
        The query object.
    """
    return tree_sitter.Query(
        get_query_language(),
        dedent("""
            ((predicate
              name: (identifier) @_name))
        """))


def apply_standard_query_edits(
    queries: bytes,
) -> bytes:
    """Apply standard edits to queries.

    Version Added:
        9.0

    Args:
        queries (bytes):
            The queries content to edit.

    Returns:
        bytes:
        The edited query content.
    """
    parser = get_parser('query')
    tree = parser.parse(queries)

    edits = itertools.chain(
        get_set3_edits(tree),
        get_lua_match_edits(tree),
        get_gsub_edits(tree),
    )

    return apply_edits(queries, edits)


@lru_cache(maxsize=1)
def get_all_captures_query() -> tree_sitter.Query:
    """Return a query for finding all captures.

    Version Added:
        9.0

    Returns:
        tree_sitter.Query:
        The query object.
    """
    return tree_sitter.Query(
        get_query_language(),
        '(capture) @_capture')


def _get_pattern_root_name(
    node: tree_sitter.Node,
) -> str | None:
    """Return the name of the root node matched by a pattern.

    This unwraps groupings to find the outermost node that the pattern
    matches in the target language.

    Version Added:
        9.0

    Args:
        node (tree_sitter.Node):
            A top-level pattern node in a parsed query file.

    Returns:
        str:
        The node name, or ``None`` if the pattern does not match a single
        named node.
    """
    groupings = {'named_node', 'grouping', 'list', 'anonymous_node'}

    while node.type == 'grouping':
        inner = None

        for child in node.named_children:
            if child.type in groupings:
                inner = child
                break

        if inner is None:
            return None

        node = inner

    if node.type == 'named_node':
        name_node = node.child_by_field_name('name')

        if name_node is not None and name_node.text is not None:
            return name_node.text.decode()

    return None


def filter_query_patterns(
    queries: bytes,
    *,
    keep_captures: Collection[str],
    drop_node_types: Collection[str] = (),
) -> bytes:
    """Filter queries down to patterns using the given captures.

    This keeps only top-level patterns that contain at least one capture in
    ``keep_captures``, dropping all other patterns along with any comments
    immediately preceding them. Duplicate patterns (which can result from
    ``; inherits:`` resolution pulling in the same parent twice) are also
    dropped.

    Patterns whose outermost matched node is in ``drop_node_types`` are
    dropped even if they use a wanted capture. This is used to drop wrapper
    patterns (such as Python's ``decorated_definition``) where an inner
    pattern already captures the interesting node.

    Version Added:
        9.0

    Args:
        queries (bytes):
            The queries content to filter.

        keep_captures (collection of str):
            The capture names (without the leading ``@``) that mark a
            pattern to keep.

        drop_node_types (collection of str, optional):
            Names of outermost matched nodes whose patterns should be
            dropped regardless of captures.

    Returns:
        bytes:
        The filtered query content.
    """
    parser = get_parser('query')
    tree = parser.parse(queries)

    captures_query = get_all_captures_query()

    edits: list[QueryEdit] = []
    pending_comment_edits: list[QueryEdit] = []
    seen_patterns: set[bytes] = set()

    for node in tree.root_node.named_children:
        if node.type == 'comment':
            pending_comment_edits.append((node.start_byte, node.end_byte,
                                          b''))
            continue

        cursor = tree_sitter.QueryCursor(captures_query)
        captures = cursor.captures(node)

        capture_names = {
            capture_node.text.decode().removeprefix('@')
            for capture_node in captures.get('_capture', [])
            if capture_node.text is not None
        }

        pattern_text = node.text or b''

        keep = (
            pattern_text not in seen_patterns and
            _get_pattern_root_name(node) not in drop_node_types and
            any(
                name in keep_captures
                for name in capture_names
            )
        )

        seen_patterns.add(pattern_text)

        if not keep:
            edits += pending_comment_edits
            edits.append((node.start_byte, node.end_byte, b''))

        pending_comment_edits = []

    # Trailing comments no longer describe anything that follows them.
    edits += pending_comment_edits

    result = apply_edits(queries, edits)

    return re.sub(rb'\n{3,}', b'\n\n', result).strip()


def get_all_predicate_names(
    tree: tree_sitter.Tree,
) -> set[str]:
    """Return all the predicate names used in the queries.

    Version Added:
        9.0

    Args:
        tree (tree_sitter.Tree):
            The parsed queries.

    Returns:
        set:
        A set of all the predicate names used in the queries.
    """
    result: set[str] = set()

    query = get_all_predicates_query()
    cursor = tree_sitter.QueryCursor(query)
    captures = cursor.captures(tree.root_node)

    for node in captures.get('_name', []):
        parent = node.parent
        assert parent is not None

        sibling = parent.child(2)
        assert sibling is not None

        text = sibling.text

        if text is not None:
            result.add(text.decode())

    return result
