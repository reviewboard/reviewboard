"""Tree Sitter query predicate handlers.

Version Added:
    9.0
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

from reviewboard.treesitter.debug import DEBUG_TREESITTER

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence
    from typing import Literal, TypeAlias

    import tree_sitter

    PredicateArgs: TypeAlias = Sequence[
        tuple[str, Literal['capture', 'string']]]

    PredicateCaptures: TypeAlias = Mapping[str, Sequence[tree_sitter.Node]]


logger = logging.getLogger(__name__)


def _any_contains_predicate(
    args: PredicateArgs,
    captures: PredicateCaptures,
    pattern_index: int,
    query: tree_sitter.Query,
) -> bool:
    """Handle the 'any-contains?' predicate.

    Checks if any node in a capture contains the expected text.

    Version Added:
        9.0

    Args:
        args (PredicateArgs):
            The predicate arguments.

        captures (PredicateCaptures):
            The captured nodes.

        pattern_index (int):
            The pattern index from the query.

        query (tree_sitter.Query):
            The query object to store settings in.

    Returns:
        bool:
        Whether the predicate matches.
    """
    if len(args) < 2:
        return False

    capture_id = args[0][0]
    expected_values = (
        arg[0]
        for arg in args[1:]
    )

    nodes = captures.get(capture_id)

    if not nodes:
        return False

    for node in nodes:
        node_text = node.text

        if not node_text:
            continue

        if any(
            expected_value.encode() in node_text
            for expected_value in expected_values
        ):
            return True

    return False


def _contains_predicate(
    args: PredicateArgs,
    captures: PredicateCaptures,
    pattern_index: int,
    query: tree_sitter.Query,
) -> bool:
    """Handle the 'contains?' predicate.

    Checks if the first node in a capture contains the expected text.

    Version Added:
        9.0

    Args:
        args (PredicateArgs):
            The predicate arguments.

        captures (PredicateCaptures):
            The captured nodes.

        pattern_index (int):
            The pattern index from the query.

        query (tree_sitter.Query):
            The query object to store settings in.

    Returns:
        bool:
        Whether the predicate matches.
    """
    if len(args) < 2:
        return False

    capture_id = args[0][0]
    expected_values = (
        arg[0]
        for arg in args[1:]
    )

    nodes = captures.get(capture_id)

    if not nodes:
        return False

    for node in nodes:
        node_text = node.text

        if not node_text:
            continue

        if all(
            expected_value.encode() in node_text
            for expected_value in expected_values
        ):
            return True

    return False


def _gsub_directive(
    args: PredicateArgs,
    captures: PredicateCaptures,
    pattern_index: int,
    query: tree_sitter.Query,
) -> bool:
    """Handle the 'gsub!' directive.

    Applies regex substitution to captured node text and stores the result
    in the query's pattern settings.

    Version Added:
        9.0

    Args:
        args (PredicateArgs):
            The predicate arguments.

        captures (PredicateCaptures):
            The captured nodes.

        pattern_index (int):
            The pattern index from the query.

        query (tree_sitter.Query):
            The query object to store settings in.

    Returns:
        bool:
        Always returns True (directives don't filter matches).
    """
    if len(args) < 3:
        return True

    capture_id = args[0][0]
    pattern = args[1][0]
    replacement = args[2][0]

    nodes = captures.get(capture_id)

    if not nodes or len(nodes) != 1:
        return True

    node = nodes[0]
    node_text = node.text

    if not node_text:
        return True

    # Get the original text
    text = node_text.decode('utf-8', errors='replace')

    # Apply regex substitution
    try:
        transformed_text = re.sub(pattern, replacement, text)
    except re.error:
        # If regex fails, just use original text
        transformed_text = text

    # Store in query pattern settings
    settings = query.pattern_settings(pattern_index)
    settings[capture_id] = transformed_text

    return True


def _has_ancestor_predicate(
    args: PredicateArgs,
    captures: PredicateCaptures,
    pattern_index: int,
    query: tree_sitter.Query,
) -> bool:
    """Handle the 'has-ancestor?' predicate.

    Checks if any captured node has an ancestor with one of the specified
    types.

    Version Added:
        9.0

    Args:
        args (PredicateArgs):
            The predicate arguments.

        captures (PredicateCaptures):
            The captured nodes.

        pattern_index (int):
            The pattern index from the query.

        query (tree_sitter.Query):
            The query object to store settings in.

    Returns:
        bool:
        Whether the predicate matches.
    """
    if len(args) < 2:
        return True

    capture_id = args[0][0]
    ancestor_types = {arg[0] for arg in args[1:]}

    nodes = captures.get(capture_id)

    if not nodes:
        return True

    for node in nodes:
        cur = node.parent

        while cur:
            if cur.type in ancestor_types:
                return True

            cur = cur.parent

    return False


def _has_parent_predicate(
    args: PredicateArgs,
    captures: PredicateCaptures,
    pattern_index: int,
    query: tree_sitter.Query,
) -> bool:
    """Handle the 'has-parent?' predicate.

    Checks if any captured node has a direct parent with one of the specified
    types.

    Version Added:
        9.0

    Args:
        args (PredicateArgs):
            The predicate arguments.

        captures (PredicateCaptures):
            The captured nodes.

        pattern_index (int):
            The pattern index from the query.

        query (tree_sitter.Query):
            The query object to store settings in.

    Returns:
        bool:
        Whether the predicate matches.
    """
    if len(args) < 2:
        return True

    capture_id = args[0][0]
    parent_types = {arg[0] for arg in args[1:]}

    nodes = captures.get(capture_id)
    if not nodes:
        return True

    for node in nodes:
        parent = node.parent

        if parent and parent.type in parent_types:
            return True

    return False


def _not_has_ancestor_predicate(
    args: PredicateArgs,
    captures: PredicateCaptures,
    pattern_index: int,
    query: tree_sitter.Query,
) -> bool:
    """Handle the 'not-has-ancestor?' predicate.

    Checks if no captured node has an ancestor with one of the specified types.

    Version Added:
        9.0

    Args:
        args (PredicateArgs):
            The predicate arguments.

        captures (PredicateCaptures):
            The captured nodes.

        pattern_index (int):
            The pattern index from the query.

        query (tree_sitter.Query):
            The query object to store settings in.

    Returns:
        bool:
        Whether the predicate matches.
    """
    return not _has_ancestor_predicate(args, captures, pattern_index, query)


def _not_has_parent_predicate(
    args: PredicateArgs,
    captures: PredicateCaptures,
    pattern_index: int,
    query: tree_sitter.Query,
) -> bool:
    """Handle the 'not-has-parent?' predicate.

    Checks if no captured node has a direct parent with one of the specified
    types.

    Version Added:
        9.0

    Args:
        args (PredicateArgs):
            The predicate arguments.

        captures (PredicateCaptures):
            The captured nodes.

        pattern_index (int):
            The pattern index from the query.

        query (tree_sitter.Query):
            The query object to store settings in.

    Returns:
        bool:
        Whether the predicate matches.
    """
    return not _has_parent_predicate(args, captures, pattern_index, query)


#: Registry of predicate handlers.
#:
#: Version Added:
#:     9.0
PREDICATE_HANDLERS: Mapping[
    str,
    Callable[[PredicateArgs, PredicateCaptures, int, tree_sitter.Query], bool]
] = {
    'any-contains?': _any_contains_predicate,
    'contains?': _contains_predicate,
    'gsub!': _gsub_directive,
    'has-ancestor?': _has_ancestor_predicate,
    'has-parent?': _has_parent_predicate,
    'not-has-ancestor?': _not_has_ancestor_predicate,
    'not-has-parent?': _not_has_parent_predicate,
}


def create_predicate_handler(
    query: tree_sitter.Query,
) -> tree_sitter.QueryPredicate:
    """Create a predicate handler function with captured context.

    Version Added:
        9.0

    Args:
        query (tree_sitter.Query):
            Query object for accessing pattern settings.

    Returns:
        tree_sitter.QueryPredicate:
        A predicate handler function.
    """
    def handle_predicate(
        predicate: str,
        args: PredicateArgs,
        pattern_index: int,
        captures: PredicateCaptures,
    ) -> bool:
        """Handle TreeSitter query predicates.

        Args:
            predicate (str):
                The predicate name.

            args (PredicateArgs):
                The predicate arguments.

            pattern_index (int):
                The pattern index from the query.

            captures (PredicateCaptures):
                The captured nodes.

        Returns:
            bool:
            Whether the predicate matches.
        """
        handler = PREDICATE_HANDLERS.get(predicate)

        if not handler:
            if DEBUG_TREESITTER:
                logger.debug(
                    'Unknown TreeSitter predicate: %s (args=%r, '
                    'pattern_index=%d, captures=%r)',
                    predicate, args, pattern_index, captures)

            return False

        return handler(args, captures, pattern_index, query)

    return handle_predicate
