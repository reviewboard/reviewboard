"""Unit tests for reviewboard.hostingsvcs.github.webhooks.

Version Added:
    9.0
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from djblets.registries.errors import (AlreadyRegisteredError,
                                       RegistrationError)

from reviewboard.hostingsvcs.github.webhooks import (
    BaseGitHubAppWebHookHandler,
    GitHubAppWebHookHandlerRegistry,
    merge_github_app_permissions,
)
from reviewboard.testing import TestCase

if TYPE_CHECKING:
    from collections.abc import Mapping

    from reviewboard.hostingsvcs.github.webhooks import \
        GitHubAppPermissionLevel


def _make_handler(
    *,
    handler_id: str = 'test-handler',
    events: (set[str] | None) = None,
    required_permissions:
        (Mapping[str, GitHubAppPermissionLevel] | None) = None,
    event_labels: (Mapping[str, str] | None) = None,
    permission_labels: (Mapping[str, str] | None) = None,
) -> BaseGitHubAppWebHookHandler:
    """Return a new handler instance.

    Args:
        handler_id (str, optional):
            The ID of the handler.

        events (set of str, optional):
            The events the handler receives.

            This defaults to ``pull_request``.

        required_permissions (dict, optional):
            The permissions the handler requires.

            This defaults to ``pull_requests: read``.

        event_labels (dict, optional):
            The labels for the handler's events.

            This defaults to a label for ``pull_request``.

        permission_labels (dict, optional):
            The labels for the handler's required permissions.

            This defaults to a label for ``pull_requests``.

    Returns:
        reviewboard.hostingsvcs.github.webhooks.BaseGitHubAppWebHookHandler:
        The new handler.
    """
    if events is None:
        events = {'pull_request'}

    if required_permissions is None:
        required_permissions = {
            'pull_requests': 'read',
        }

    if event_labels is None:
        event_labels = {
            'pull_request': 'Pull request',
        }

    if permission_labels is None:
        permission_labels = {
            'pull_requests': 'Pull request',
        }

    handler_cls = type(
        'TestHandler',
        (BaseGitHubAppWebHookHandler,),
        {
            'handler_id': handler_id,
            'events': events,
            'required_permissions': required_permissions,
            'event_labels': event_labels,
            'permission_labels': permission_labels,
        })

    return handler_cls()


class GitHubAppWebHookHandlerRegistryTests(TestCase):
    """Unit tests for GitHubAppWebHookHandlerRegistry.

    Version Added:
        9.0
    """

    def setUp(self) -> None:
        """Set up the test."""
        super().setUp()

        self.registry = GitHubAppWebHookHandlerRegistry()

    def test_register(self) -> None:
        """Testing GitHubAppWebHookHandlerRegistry.register"""
        registry = self.registry

        handler = _make_handler()
        registry.register(handler)

        self.assertIs(registry.get('handler_id', 'test-handler'),
                      handler)

    def test_register_with_duplicate_handler_id(self) -> None:
        """Testing GitHubAppWebHookHandlerRegistry.register with a duplicate
        handler ID
        """
        registry = self.registry

        registry.register(_make_handler())

        with self.assertRaises(AlreadyRegisteredError):
            registry.register(_make_handler(events={'push'}))

    def test_unregister(self) -> None:
        """Testing GitHubAppWebHookHandlerRegistry.unregister"""
        registry = self.registry

        handler = _make_handler()
        registry.register(handler)
        registry.unregister(handler)

        self.assertIsNone(registry.get('handler_id', 'test-handler'))
        self.assertEqual(registry.get_handlers_for_event('pull_request'),
                         [])

    def test_register_with_empty_handler_id(self) -> None:
        """Testing GitHubAppWebHookHandlerRegistry.register with empty
        handler_id
        """
        registry = self.registry
        handler = _make_handler(handler_id='')

        message = (
            f'Could not register GitHub App webhook handler {handler}: '
            f'handler_id must be a non-empty string.'
        )

        with self.assertRaisesMessage(RegistrationError, message):
            registry.register(handler)

        self.assertEqual(list(registry), [])

    def test_register_with_missing_handler_id(self) -> None:
        """Testing GitHubAppWebHookHandlerRegistry.register with missing
        handler_id
        """
        class TestHandler(BaseGitHubAppWebHookHandler):
            events = {'push'}

        registry = self.registry
        handler = TestHandler()

        message = (
            f'Could not register GitHub App webhook handler {handler}: '
            f'handler_id must be a non-empty string.'
        )

        with self.assertRaisesMessage(RegistrationError, message):
            registry.register(handler)

        self.assertEqual(list(registry), [])

    def test_register_with_empty_events(self) -> None:
        """Testing GitHubAppWebHookHandlerRegistry.register with empty
        events
        """
        registry = self.registry
        handler = _make_handler(events=set())

        message = (
            f'Could not register GitHub App webhook handler {handler}: '
            f'events must be a non-empty set.'
        )

        with self.assertRaisesMessage(RegistrationError, message):
            registry.register(handler)

        self.assertEqual(list(registry), [])

    def test_register_with_events_not_set(self) -> None:
        """Testing GitHubAppWebHookHandlerRegistry.register with events
        that are not a set
        """
        registry = self.registry
        handler = _make_handler()
        handler.events = ('push',)  # type: ignore

        message = (
            f'Could not register GitHub App webhook handler {handler}: '
            f'events must be a non-empty set.'
        )

        with self.assertRaisesMessage(RegistrationError, message):
            registry.register(handler)

        self.assertEqual(list(registry), [])

    def test_register_with_invalid_permission_level(self) -> None:
        """Testing GitHubAppWebHookHandlerRegistry.register with invalid
        permission access level
        """
        registry = self.registry
        handler = _make_handler(
            required_permissions={'issues': 'blah'},  # type: ignore
        )

        message = (
            f"Could not register GitHub App webhook handler {handler}: "
            f"required_permissions has invalid access level "
            f"'blah' for permission 'issues'."
        )

        with self.assertRaisesMessage(RegistrationError, message):
            registry.register(handler)

        self.assertEqual(list(registry), [])

    def test_get_handlers_for_event(self) -> None:
        """Testing GitHubAppWebHookHandlerRegistry.get_handlers_for_event"""
        registry = self.registry

        handler1 = _make_handler(handler_id='test-handler1',
                                 events={'pull_request', 'push'})
        handler2 = _make_handler(handler_id='test-handler2',
                                 events={'issues'})
        handler3 = _make_handler(handler_id='test-handler3')

        registry.register(handler1)
        registry.register(handler2)
        registry.register(handler3)

        self.assertEqual(registry.get_handlers_for_event('pull_request'),
                         [handler1, handler3])
        self.assertEqual(registry.get_handlers_for_event('issues'),
                         [handler2])

    def test_get_handlers_for_event_with_no_match(self) -> None:
        """Testing GitHubAppWebHookHandlerRegistry.get_handlers_for_event
        with no matching handlers
        """
        registry = self.registry

        registry.register(_make_handler())

        self.assertEqual(registry.get_handlers_for_event('ping'), [])

    def test_get_events(self) -> None:
        """Testing GitHubAppWebHookHandlerRegistry.get_events"""
        registry = self.registry

        registry.register(_make_handler(handler_id='test-handler1',
                                        events={'push', 'pull_request'}))
        registry.register(_make_handler(handler_id='test-handler2',
                                        events={'pull_request', 'issues'}))

        self.assertEqual(registry.get_events(),
                         {'issues', 'pull_request', 'push'})

    def test_get_events_with_no_handlers(self) -> None:
        """Testing GitHubAppWebHookHandlerRegistry.get_events with no
        handlers
        """
        self.assertEqual(self.registry.get_events(), set())

    def test_get_events_after_register(self) -> None:
        """Testing GitHubAppWebHookHandlerRegistry.get_events is
        recomputed after registering a handler
        """
        registry = self.registry

        registry.register(_make_handler(handler_id='test-handler1',
                                        events={'push'}))

        self.assertEqual(registry.get_events(), {'push'})

        registry.register(_make_handler(handler_id='test-handler2'))

        self.assertEqual(registry.get_events(),
                         {'pull_request', 'push'})

    def test_get_events_after_unregister(self) -> None:
        """Testing GitHubAppWebHookHandlerRegistry.get_events is
        recomputed after unregistering a handler
        """
        registry = self.registry

        handler = _make_handler(handler_id='test-handler1',
                                events={'push'})
        registry.register(handler)
        registry.register(_make_handler(handler_id='test-handler2'))

        self.assertEqual(registry.get_events(),
                         {'pull_request', 'push'})

        registry.unregister(handler)

        self.assertEqual(registry.get_events(), {'pull_request'})

    def test_get_required_permissions(self) -> None:
        """Testing GitHubAppWebHookHandlerRegistry.get_required_permissions"""
        registry = self.registry

        registry.register(_make_handler(
            handler_id='test-handler1',
            required_permissions={
                'pull_requests': 'read',
                'statuses': 'write',
            }))
        registry.register(_make_handler(
            handler_id='test-handler2',
            required_permissions={
                'checks': 'write',
                'pull_requests': 'write',
            }))

        self.assertEqual(
            registry.get_required_permissions(),
            {
                'checks': 'write',
                'pull_requests': 'write',
                'statuses': 'write',
            })

    def test_get_required_permissions_with_no_handlers(self) -> None:
        """Testing GitHubAppWebHookHandlerRegistry.get_required_permissions
        with no handlers
        """
        self.assertEqual(self.registry.get_required_permissions(), {})

    def test_get_event_labels(self) -> None:
        """Testing GitHubAppWebHookHandlerRegistry.get_event_labels"""
        registry = self.registry

        registry.register(_make_handler(
            handler_id='test-handler1',
            event_labels={
                'pull_request': 'Pull request 1',
            }))
        registry.register(_make_handler(
            handler_id='test-handler2',
            events={'check_run', 'pull_request'},
            event_labels={
                'check_run': 'Check run',
                'pull_request': 'Pull request 2',
            }))

        self.assertEqual(
            registry.get_event_labels(),
            {
                'check_run': 'Check run',
                'pull_request': 'Pull request 1',
            })

    def test_get_event_labels_with_no_handlers(self) -> None:
        """Testing GitHubAppWebHookHandlerRegistry.get_event_labels with no
        handlers
        """
        self.assertEqual(self.registry.get_event_labels(), {})

    def test_get_permission_labels(self) -> None:
        """Testing GitHubAppWebHookHandlerRegistry.get_permission_labels"""
        registry = self.registry

        registry.register(_make_handler(
            handler_id='test-handler1',
            permission_labels={
                'checks': 'Checks 1',
            }))
        registry.register(_make_handler(
            handler_id='test-handler2',
            permission_labels={
                'checks': 'Checks 2',
                'issues': 'Issues',
            }))

        self.assertEqual(
            registry.get_permission_labels(),
            {
                'checks': 'Checks 1',
                'issues': 'Issues',
            })

    def test_get_permission_labels_with_no_handlers(self) -> None:
        """Testing GitHubAppWebHookHandlerRegistry.get_permission_labels with
        no handlers
        """
        self.assertEqual(self.registry.get_permission_labels(), {})


class MergeGitHubAppPermissionsTests(TestCase):
    """Unit tests for merge_github_app_permissions.

    Version Added:
        9.0
    """

    def test_with_permissions(self) -> None:
        """Testing merge_github_app_permissions with different permissions"""
        self.assertEqual(
            merge_github_app_permissions([
                {'contents': 'read'},
                {'statuses': 'write'},
            ]),
            {
                'contents': 'read',
                'statuses': 'write',
            })

    def test_with_duplicate_permission(self) -> None:
        """Testing merge_github_app_permissions with duplicate permissions of
        different access levels
        """
        self.assertEqual(
            merge_github_app_permissions([
                {'contents': 'admin'},
                {'contents': 'read'},
            ]),
            {'contents': 'admin'})

    def test_with_unknown_level(self) -> None:
        """Testing merge_github_app_permissions logs and skips an unknown
        access level
        """
        with self.assertLogs('reviewboard.hostingsvcs.github.webhooks',
                             level='WARNING') as logs:
            result = merge_github_app_permissions([
                {'contents': 'read'},
                {
                    'contents': 'custom',  # type: ignore
                    'statuses': 'custom',  # type: ignore
                },
            ])

        self.assertEqual(result, {'contents': 'read'})
        self.assertEqual(
            [record.getMessage() for record in logs.records],
            [
                "Unknown access level 'custom' for GitHub App permission "
                "'contents'.",
                "Unknown access level 'custom' for GitHub App permission "
                "'statuses'.",
            ])
