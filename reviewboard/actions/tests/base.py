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
from reviewboard.actions.renderers import ButtonActionRenderer

if TYPE_CHECKING:
    from collections.abc import Iterator

    from django.template import Context
    from typelets.django.json import SerializableDjangoJSONDict


class TestAction(BaseAction):
    """Basic action for testing.

    Version Added:
        7.1
    """

    action_id = 'test'
    label = 'Test Action 1'


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
    label = 'Test Group'

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
    label = 'Test Menu'


class TestMenuItemAction(BaseAction):
    """Basic menu item action for testing.

    Version Added:
        7.1
    """

    action_id = 'menu-item-action'
    parent_id = 'menu-action'
    label = 'Menu Item Action 1'
    icon_class = 'my-icon'
    verbose_label = 'Verbose Menu Item Action 1'
    description = ['Menu Item 1 description.']


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


class SpecialButtonActionRenderer(ButtonActionRenderer):
    """Action renderer with additional button state for testing purposes.

    Version Added:
        7.1
    """

    js_view_class = 'SpecialButtonActionView'

    def get_js_view_data(
        self,
        *,
        context: Context,
    ) -> SerializableDjangoJSONDict:
        """Return data to be passed to the rendered JavaScript view.

        This provides a custom label for the view and some extra view-specific
        state.

        Args:
            context (django.template.Context):
                The current rendering context.

        Returns:
            dict:
            A dictionary of options to pass to the view instance.
        """
        label = self.action.get_label(context=context)

        return {
            'label': f'~~{label}~~',
            'specialKey': [123, 456],
        }


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
