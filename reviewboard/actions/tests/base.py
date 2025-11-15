"""Base support for action unit tests.

Version Added:
    7.1
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from reviewboard.actions import (AttachmentPoint,
                                 BaseAction,
                                 BaseGroupAction,
                                 BaseMenuAction)
from reviewboard.actions.registry import ActionsRegistry

if TYPE_CHECKING:
    from collections.abc import Iterator


class TestAction(BaseAction):
    """Basic action for testing.

    Version Added:
        7.1
    """

    action_id = 'test'


class TestHeaderAction(BaseAction):
    """Basic header action for testing.

    Version Added:
        7.1
    """

    action_id = 'header-action'
    attachment = AttachmentPoint.HEADER


class TestGroupAction(BaseGroupAction):
    """Basic group action for testing.

    Version Added:
        7.1
    """

    action_id = 'group-action'

    children = [
        'group-item-2-action',
        'group-item-1-action',
    ]


class TestGroupItemAction1(BaseAction):
    """Basic group item action for testing.

    Version Added:
        7.1
    """

    action_id = 'group-item-1-action'
    parent_id = 'group-action'


class TestGroupItemAction2(BaseAction):
    """Basic group item action for testing.

    Version Added:
        7.1
    """

    action_id = 'group-item-2-action'
    parent_id = 'group-action'


class TestGroupItemAction3(BaseAction):
    """Basic group item action for testing.

    Version Added:
        7.1
    """

    action_id = 'group-item-3-action'
    parent_id = 'group-action'


class TestMenuAction(BaseMenuAction):
    """Basic menu action for testing.

    Version Added:
        7.1
    """

    action_id = 'menu-action'


class TestMenuItemAction(BaseAction):
    """Basic menu item action for testing.

    Version Added:
        7.1
    """

    action_id = 'menu-item-action'
    parent_id = 'menu-action'


class TestNestedMenuAction(BaseMenuAction):
    """Basic nested menu action for testing.

    Version Added:
        7.1
    """

    action_id = 'nested-menu-action'
    parent_id = 'menu-action'


class TestNested2MenuAction(BaseMenuAction):
    """Second-level nested menu action for testing.

    Version Added:
        7.1
    """

    action_id = 'nested-2-menu-action'
    parent_id = 'nested-menu-action'


class TooDeeplyNestedAction(BaseAction):
    """Third-level (too-deep) nested menu action for testing.

    Version Added:
        7.1
    """

    action_id = 'nested-3-action'
    parent_id = 'nested-2-menu-action'


class TestActionsRegistry(ActionsRegistry):
    """Empty actions registry for testing purposes.

    Version Added:
        7.1
    """

    def get_defaults(self) -> Iterator[BaseAction]:
        """Return an empty set of defaults.

        Yields:
            reviewboard.actions.base.BaseAction:
            Each action (but none, really).
        """
        yield from []
