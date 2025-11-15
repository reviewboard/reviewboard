"""Unit tests for the actions registry.

Version Added:
    6.0
"""

from __future__ import annotations

from djblets.registries.errors import AlreadyRegisteredError

from reviewboard.actions import (AttachmentPoint,
                                 actions_registry)
from reviewboard.actions.errors import DepthLimitExceededError
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

    def setUp(self) -> None:
        """Set up the test case."""
        super().setUp()

        self.test_action = TestAction()
        self.test_header_action = TestHeaderAction()
        self.test_menu_action = TestMenuAction()
        self.test_menu_item_action = TestMenuItemAction()

    def tearDown(self) -> None:
        """Tear down the test case."""
        super().tearDown()
        actions_registry.reset()

    def test_register(self) -> None:
        """Testing ActionsRegistry.register"""
        test_action = self.test_action

        actions_registry = TestActionsRegistry()
        actions_registry.register(test_action)

        with self.assertRaises(AlreadyRegisteredError):
            actions_registry.register(test_action)

        self.assertEqual(
            actions_registry._by_attachment_point,
            {
                'review-request': {
                    'test': test_action,
                },
            })

    def test_unregister(self) -> None:
        """Testing ActionsRegistry.unregister"""
        test_action = self.test_action

        actions_registry = TestActionsRegistry()
        actions_registry.register(test_action)

        self.assertEqual(
            actions_registry._by_attachment_point,
            {
                'review-request': {
                    'test': test_action,
                },
            })

        actions_registry.unregister(test_action)

        self.assertEqual(actions_registry._by_attachment_point, {})

    def test_get_for_attachment(self) -> None:
        """Testing ActionsRegistry.get_for_attachment"""
        actions_registry = TestActionsRegistry()

        test_action = self.test_action
        test_header_action = self.test_header_action

        actions_registry.register(test_action)
        actions_registry.register(test_header_action)

        self.assertEqual(
            actions_registry._by_attachment_point,
            {
                'header': {
                    'header-action': test_header_action,
                },
                'review-request': {
                    'test': test_action,
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

    def test_menu(self) -> None:
        """Testing ActionsRegistry with menu actions"""
        actions_registry.register(self.test_menu_action)
        actions_registry.register(self.test_menu_item_action)

        self.assertIn(self.test_menu_item_action,
                      self.test_menu_action.child_actions)

        actions_registry.unregister(self.test_menu_item_action)

        self.assertNotIn(self.test_menu_item_action,
                         self.test_menu_action.child_actions)

    def test_deferred_registration(self) -> None:
        """Testing ActionsRegistry.register with deferred child registration
        """
        actions_registry.register(self.test_menu_item_action)

        self.assertIsNone(
            actions_registry.get('action_id',
                                 self.test_menu_item_action.action_id))
        self.assertIn(
            self.test_menu_item_action,
            actions_registry._deferred_registrations)

        actions_registry.register(self.test_menu_action)

        self.assertIn(self.test_menu_item_action,
                      self.test_menu_action.child_actions)

        self.assertEqual(
            actions_registry.get('action_id',
                                 self.test_menu_item_action.action_id),
            self.test_menu_item_action)
        self.assertEqual(actions_registry._deferred_registrations, [])

    def test_too_deeply_nested(self) -> None:
        """Testing ActionsRegistry with actions that are too deeply nested"""
        nested_action = TestNestedMenuAction()
        nested2_action = TestNested2MenuAction()
        nested3_action = TooDeeplyNestedAction()

        actions_registry.register(self.test_menu_action)
        actions_registry.register(nested_action)
        actions_registry.register(nested2_action)

        with self.assertRaises(DepthLimitExceededError):
            actions_registry.register(nested3_action)
