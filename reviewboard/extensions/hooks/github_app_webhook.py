"""Extension hook for registering GitHub App webhook handlers.

Version Added:
    9.0
"""

from __future__ import annotations

from djblets.extensions.hooks import BaseRegistryHook, ExtensionHookPoint

from reviewboard.hostingsvcs.github.webhooks import (
    BaseGitHubAppWebhookHandler,
    github_app_webhook_handler_registry,
)


class GitHubAppWebhookHandlerHook(
    BaseRegistryHook[BaseGitHubAppWebhookHandler],
    metaclass=ExtensionHookPoint,
):
    """Extension hook for registering GitHub App webhook handlers.

    See :ref:`github-app-webhook-handler-hook` for instructions.

    Version Added:
        9.0
    """

    registry = github_app_webhook_handler_registry
