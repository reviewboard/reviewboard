"""Unit tests for reviewboard.extensions.hooks.GitHubAppWebhookHandlerHook.

Version Added:
    9.0
"""

from __future__ import annotations

from reviewboard.extensions.hooks import GitHubAppWebhookHandlerHook
from reviewboard.extensions.tests.testcases import BaseExtensionHookTestCase
from reviewboard.hostingsvcs.github.webhooks import (
    BaseGitHubAppWebhookHandler,
    github_app_webhook_handler_registry,
)


class _TestHandler(BaseGitHubAppWebhookHandler):
    """A test handler.

    Version Added:
        9.0
    """

    handler_id = 'test-handler'
    events = {'pull_request'}
    event_labels = {
        'pull_request': 'Pull request',
    }
    required_permissions = {
        'pull_requests': 'read',
    }
    permission_labels = {
        'pull_requests': 'Pull requests',
    }


class GitHubAppWebhookHandlerHookTests(BaseExtensionHookTestCase):
    """Testing GitHubAppWebhookHandlerHook."""

    def test_register(self) -> None:
        """Testing GitHubAppWebhookHandlerHook initializing"""
        handler = _TestHandler()
        GitHubAppWebhookHandlerHook(self.extension, handler)

        self.assertIs(
            github_app_webhook_handler_registry.get('handler_id',
                                                    'test-handler'),
            handler)

    def test_unregister(self) -> None:
        """Testing GitHubAppWebhookHandlerHook uninitializing"""
        hook = GitHubAppWebhookHandlerHook(self.extension,
                                           _TestHandler())
        hook.disable_hook()

        self.assertIsNone(
            github_app_webhook_handler_registry.get('handler_id',
                                                    'test-handler'))
