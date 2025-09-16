"""Debug helpers for working with Tree Sitter.

Version Added:
    8.0
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import tree_sitter


#: Debug flag for TreeSitter highlighting.
#:
#: Version Added:
#:     8.0
DEBUG_TREESITTER = (os.environ.get('RB_DEBUG_TREESITTER', '') == '1')


def print_tree(
    tree: tree_sitter.Tree,
) -> None:
    """Print a tree to stdout.

    Version Added:
        8.0

    Args:
        tree (tree_sitter.Tree):
            The tree to print.
    """
    indent = 0
    cursor = tree.walk()
    visited_children = False

    while True:
        if not visited_children:
            node = cursor.node
            assert node is not None

            print('    ' * indent + f' {cursor.node}')

            if cursor.goto_first_child():
                indent += 1
            else:
                visited_children = True
        elif cursor.goto_next_sibling():
            visited_children = False
        elif cursor.goto_parent():
            indent -= 1
        else:
            break
