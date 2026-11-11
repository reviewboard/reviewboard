.. _github-app-webhook-handler-hook:

===========================
GitHubAppWebhookHandlerHook
===========================

.. versionadded:: 9.0

GitHub App Webhook Handlers provide a way for extensions to handle GitHub
events on your repositories, such as pull requests being opened.

.. TODO: Add this once we have more docs on connecting a GitHub App
    .. note::

    This is only available when connecting through a GitHub App. If you're
    currently connected through a GitHub Personal Access Token, you can
    follow these steps to migrate to an App connection.


.. currentmodule:: reviewboard.hostingsvcs.github.webhooks


Creating GitHub App Webhook Handlers
====================================

To create a GitHub App Webhook Handler, you'll need to subclass
:py:class:`BaseGitHubAppWebhookHandler` and pass an instance of it to
:py:class:`~reviewboard.extensions.hooks.GitHubAppWebhookHandlerHook`.

You must set the following:

* :py:attr:`~BaseGitHubAppWebhookHandler.handler_id`:

  A unique ID for the handler. This should be prefixed with a vendor or
  extension ID to avoid collisions.

* :py:attr:`~BaseGitHubAppWebhookHandler.events`:

  A set of the names of the `GitHub events`_ the handler supports.

* :py:attr:`~BaseGitHubAppWebhookHandler.required_permissions`:

  A mapping of the `GitHub App permissions`_ needed for those events to
  the access level required (``read``, ``write`` or ``admin``).

* :py:attr:`~BaseGitHubAppWebhookHandler.event_labels`:

  A mapping of the event names in
  :py:attr:`~BaseGitHubAppWebhookHandler.events` to labels that will be
  shown in the admin UI as the requested events for the App (e.g.
  ``pull_request`` -> ``Pull Request``).

  Labels in :py:data:`DEFAULT_GITHUB_APP_EVENT_LABELS` take precedence
  over these, so you only need to set this for events that aren't already
  listed there.

* :py:attr:`~BaseGitHubAppWebhookHandler.permission_labels`:

  A mapping of the permissions in
  :py:attr:`~BaseGitHubAppWebhookHandler.required_permissions` to labels
  that will be shown in the admin UI as the requested permissions for the
  App (e.g. ``statuses`` -> ``Commit Statuses``).

  Labels in :py:data:`DEFAULT_GITHUB_APP_PERMISSION_LABELS` take precedence
  over these, so you only need to set this for permissions that aren't already
  listed there.

Handlers must also implement
:py:meth:`~BaseGitHubAppWebhookHandler.handle_event`, which is given a
:py:class:`GitHubAppWebhookEvent`.

Before calling a handler, Review Board will:

* Verify the delivery's signature against the app's webhook secret.
  Deliveries that fail verification are rejected, and never reach handlers.

* Look up the installation account and repository the event applies to.
  The installation account will be ``None`` if Review Board doesn't have
  an account for the installation. The repository will be ``None`` if there's
  no installation account, if the event isn't about a repository, or if the
  repository isn't an active repository in Review Board.

Any number of handlers can handle the same event, and they're called in the
order they were registered. Any errors raised by a handler are logged
along with GitHub's delivery ID, and don't prevent other handlers from being
called. The delivery is always acknowledged to GitHub.

.. TODO: Once we bake in broker support we can remove this.
.. note::
    GitHub times out a delivery after 10 seconds, so handlers should avoid
    long-running work where possible.


.. _GitHub events:
   https://docs.github.com/en/webhooks/webhook-events-and-payloads

.. _GitHub App permissions:
   https://docs.github.com/en/rest/authentication/permissions-required-for-github-apps


Events and Permissions
======================

When an administrator creates a GitHub App, Review Board requests a default
set of events and permissions, along with those required by all registered
handlers.

:py:data:`DEFAULT_GITHUB_APP_EVENTS` lists the events that are requested by
default by Review Board and :py:data:`DEFAULT_GITHUB_APP_PERMISSIONS` lists
the permissions that are requested by default by Review Board.

When a new handler is registered and you already have an app connection,
administrators must manually update the app's settings on GitHub to add any
new required events or permissions.


Example
=======

.. code-block:: python

    from __future__ import annotations

    import logging
    from typing import TYPE_CHECKING

    from reviewboard.extensions.base import Extension
    from reviewboard.extensions.hooks import GitHubAppWebhookHandlerHook
    from reviewboard.hostingsvcs.github.webhooks import (
        BaseGitHubAppWebhookHandler,
    )

    if TYPE_CHECKING:
        from reviewboard.hostingsvcs.github.webhooks import (
            GitHubAppWebhookEvent,
        )


    logger = logging.getLogger(__name__)


    class PullRequestLogger(BaseGitHubAppWebhookHandler):
        handler_id = 'sample_extension.pull-request-logger'
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

        def handle_event(
            self,
            event: GitHubAppWebhookEvent,
        ) -> None:
            repository = event.repository

            if repository is None:
                # This pull request is on a repository that isn't in
                # Review Board.
                return

            logger.info(
                'Pull request #%s was %s on %s (delivery %s).',
                event.payload['number'],
                event.payload['action'],
                repository.name,
                event.delivery_id)


    class SampleExtension(Extension):
        def initialize(self) -> None:
            GitHubAppWebhookHandlerHook(self, PullRequestLogger())
