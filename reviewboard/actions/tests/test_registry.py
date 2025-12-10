"""Unit tests for the actions registry.

Version Added:
    6.0
"""

from __future__ import annotations

from djblets.registries.errors import AlreadyRegisteredError

from reviewboard.actions import AttachmentPoint
from reviewboard.actions.base import ActionPlacement
from reviewboard.actions.tests.base import (
    TestAction,
    TestActionsRegistry,
    TestHeaderAction,
    TestMenuAction,
    TestMenuItemAction,
    TestNested2MenuAction,
    TestNestedMenuAction,
    TooDeeplyNestedAction,
)
from reviewboard.testing import TestCase


class ActionsRegistryTests(TestCase):
    """Unit tests for the actions registry.

    Version Added:
        6.0
    """

    def test_register(self) -> None:
        """Testing ActionsRegistry.register"""
        test_action = TestMenuAction()

        actions_registry = TestActionsRegistry()
        actions_registry.register(test_action)

        with self.assertRaises(AlreadyRegisteredError):
            actions_registry.register(test_action)

        self.assertEqual(
            actions_registry._by_attachment_point,
            {
                'review-request': {
                    'menu-action': (
                        test_action,
                        test_action.get_placement('review-request'),
                    ),
                },
            })

        self.assertEqual(actions_registry._deferred_placements, {})

    def test_register_child_of_missing_action(self) -> None:
        """Testing ActionsRegistry.register of action with missing parent
        actions
        """
        test_action = TestMenuItemAction()

        actions_registry = TestActionsRegistry()
        actions_registry.register(test_action)

        with self.assertRaises(AlreadyRegisteredError):
            actions_registry.register(test_action)

        self.assertEqual(actions_registry._by_attachment_point, {})
        self.assertEqual(
            actions_registry._deferred_placements,
            {
                ('menu-action', 'review-request'): {
                    'menu-item-action': test_action,
                },
            })

    def test_register_child_of_missing_placement(self) -> None:
        """Testing ActionsRegistry.register of action with one missing
        placement
        """
        assert TestMenuItemAction.placements

        class MyTestMenuItemAction(TestMenuItemAction):
            placements = [
                *TestMenuItemAction.placements,
                ActionPlacement(attachment='header',
                                parent_id='missing-parent'),
            ]

        test_menu_action = TestMenuAction()
        test_menu_item_action = MyTestMenuItemAction()

        actions_registry = TestActionsRegistry()
        actions_registry.register(test_menu_action)
        actions_registry.register(test_menu_item_action)

        self.assertEqual(
            actions_registry._by_attachment_point,
            {
                'review-request': {
                    'menu-action': (
                        test_menu_action,
                        test_menu_action.get_placement('review-request'),
                    ),
                    'menu-item-action': (
                        test_menu_item_action,
                        test_menu_item_action.get_placement('review-request'),
                    ),
                },
            })

        self.assertEqual(
            actions_registry._deferred_placements,
            {
                ('missing-parent', 'header'): {
                    'menu-item-action': test_menu_item_action,
                },
            })

    def test_register_with_previously_deferred(self) -> None:
        """Testing ActionsRegistry.register of action previously unregistered
        and deferred with children
        """
        test_menu_action = TestMenuAction()
        test_menu_item_action = TestMenuItemAction()

        actions_registry = TestActionsRegistry()
        actions_registry.register(test_menu_action)
        actions_registry.register(test_menu_item_action)

        # Unregister the parent.
        actions_registry.unregister(test_menu_action)

        self.assertEqual(actions_registry._by_attachment_point, {})
        self.assertEqual(
            actions_registry._deferred_placements,
            {
                ('menu-action', 'review-request'): {
                    'menu-item-action': test_menu_item_action,
                },
            })

        # And re-register it.
        actions_registry.register(test_menu_action)

        test_menu_action_placement = \
            test_menu_action.get_placement('review-request')
        test_menu_item_action_placement = \
            test_menu_item_action.get_placement('review-request')

        self.assertIn(test_menu_item_action,
                      test_menu_action_placement.child_actions)
        self.assertIs(test_menu_item_action_placement.parent_action,
                      test_menu_action)

        self.assertEqual(
            actions_registry._by_attachment_point,
            {
                'review-request': {
                    'menu-action': (
                        test_menu_action,
                        test_menu_action_placement,
                    ),
                    'menu-item-action': (
                        test_menu_item_action,
                        test_menu_item_action_placement,
                    ),
                },
            })

        self.assertEqual(actions_registry._deferred_placements, {})

    def test_unregister(self) -> None:
        """Testing ActionsRegistry.unregister"""
        test_action = TestAction()

        actions_registry = TestActionsRegistry()
        actions_registry.register(test_action)

        self.assertEqual(
            actions_registry._by_attachment_point,
            {
                'review-request': {
                    'test': (
                        test_action,
                        test_action.get_placement('review-request'),
                    ),
                },
            })
        self.assertEqual(actions_registry._deferred_placements, {})

        actions_registry.unregister(test_action)

        self.assertEqual(actions_registry._by_attachment_point, {})
        self.assertEqual(actions_registry._deferred_placements, {})

    def test_unregister_with_children(self) -> None:
        """Testing ActionsRegistry.unregister of action with children"""
        test_menu_action = TestMenuAction()
        test_menu_item_action = TestMenuItemAction()

        actions_registry = TestActionsRegistry()
        actions_registry.register(test_menu_action)
        actions_registry.register(test_menu_item_action)

        self.assertEqual(
            actions_registry._by_attachment_point,
            {
                'review-request': {
                    'menu-action': (
                        test_menu_action,
                        test_menu_action.get_placement('review-request'),
                    ),
                    'menu-item-action': (
                        test_menu_item_action,
                        test_menu_item_action.get_placement('review-request'),
                    ),
                },
            })
        self.assertEqual(actions_registry._deferred_placements, {})

        actions_registry.unregister(test_menu_action)

        self.assertEqual(actions_registry._by_attachment_point, {})
        self.assertEqual(
            actions_registry._deferred_placements,
            {
                ('menu-action', 'review-request'): {
                    'menu-item-action': test_menu_item_action,
                },
            })

    def test_get_for_attachment(self) -> None:
        """Testing ActionsRegistry.get_for_attachment"""
        actions_registry = TestActionsRegistry()

        test_action = TestAction()
        test_header_action = TestHeaderAction()

        actions_registry.register(test_action)
        actions_registry.register(test_header_action)

        self.assertEqual(
            actions_registry._by_attachment_point,
            {
                'header': {
                    'header-action': (
                        test_header_action,
                        test_header_action.get_placement('header'),
                    ),
                },
                'review-request': {
                    'test': (
                        test_action,
                        test_action.get_placement('review-request'),
                    ),
                },
            })

        self.assertEqual(
            list(actions_registry.get_for_attachment(AttachmentPoint.HEADER)),
            [
                test_header_action,
            ])

        self.assertEqual(
            list(actions_registry.get_for_attachment(
                AttachmentPoint.REVIEW_REQUEST)),
            [
                test_action,
            ])

    def test_deferred_placements(self) -> None:
        """Testing ActionsRegistry.register with deferred placements"""
        action = TestMenuItemAction()

        # Register the action with an unregistered parent.
        actions_registry = TestActionsRegistry()
        actions_registry.register(action)

        self.assertIs(actions_registry.get_action(action.action_id), action)
        self.assertEqual(
            actions_registry._deferred_placements,
            {
                ('menu-action', 'review-request'): {
                    'menu-item-action': action,
                },
            })

        # Now register the missing action.
        menu_action = TestMenuAction()
        actions_registry.register(menu_action)

        self.assertIn(
            action,
            menu_action.get_placement('review-request').child_actions)
        self.assertIn(action, menu_action.child_actions)

        self.assertIs(
            actions_registry.get_action(menu_action.action_id),
            menu_action)
        self.assertEqual(actions_registry._deferred_placements, {})

    def test_too_deeply_nested(self) -> None:
        """Testing ActionsRegistry with actions that are too deeply nested"""
        test_menu_action = TestMenuAction()
        nested_action = TestNestedMenuAction()
        nested2_action = TestNested2MenuAction()
        nested3_action = TooDeeplyNestedAction()

        actions_registry = TestActionsRegistry()
        actions_registry.register(test_menu_action)
        actions_registry.register(nested_action)
        actions_registry.register(nested2_action)

        with self.assertLogs() as cm:
            actions_registry.register(nested3_action)

        self.assertEqual(cm.output, [
            'ERROR:reviewboard.actions.registry:Action "nested-3-action" '
            'exceeds the maximum depth limit of 2 for attachment point(s) '
            '"review-request".',
        ])
