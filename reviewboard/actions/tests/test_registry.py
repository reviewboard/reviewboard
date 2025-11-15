"""Unit tests for the actions registry.

Version Added:
    6.0
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from djblets.registries.errors import AlreadyRegisteredError

from reviewboard.actions import (AttachmentPoint,
                                 BaseAction,
                                 BaseMenuAction,
                                 actions_registry)
from reviewboard.actions.errors import DepthLimitExceededError
from reviewboard.actions.registry import ActionsRegistry
from reviewboard.testing import TestCase

if TYPE_CHECKING:
    from collections.abc import Iterator


class TestAction(BaseAction):
    action_id = 'test'


class TestHeaderAction(BaseAction):
    action_id = 'header-action'
    attachment = AttachmentPoint.HEADER


class TestMenuAction(BaseMenuAction):
    action_id = 'menu-action'


class TestMenuItemAction(BaseAction):
    action_id = 'menu-item-action'
    parent_id = 'menu-action'


class TestNestedMenuAction(BaseMenuAction):
    action_id = 'nested-menu-action'
    parent_id = 'menu-action'


class TestNested2MenuAction(BaseMenuAction):
    action_id = 'nested-2-menu-action'
    parent_id = 'nested-menu-action'


class TooDeeplyNestedAction(BaseAction):
    action_id = 'nested-3-action'
    parent_id = 'nested-2-menu-action'


class _TestActionsRegistry(ActionsRegistry):
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

        actions_registry = _TestActionsRegistry()
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

        actions_registry = _TestActionsRegistry()
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
        actions_registry = _TestActionsRegistry()

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
