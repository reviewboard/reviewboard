"""Unit tests for the GitHub App webhook handler.

Version Added:
    9.0
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
from typing import TYPE_CHECKING

import kgb

from reviewboard.hostingsvcs.github.views import GitHubAppWebHookView
from reviewboard.hostingsvcs.github.webhooks import (
    BaseGitHubAppWebHookHandler,
    github_app_webhook_handler_registry,
)
from reviewboard.hostingsvcs.models import HostingServiceAccount
from reviewboard.hostingsvcs.tests.github.base import GitHubTestCase
from reviewboard.scmtools.crypto_utils import encrypt_password
from reviewboard.site.urlresolvers import local_site_reverse

if TYPE_CHECKING:
    from typing import Any

    from django.test.client import _MonkeyPatchedWSGIResponse

    from reviewboard.hostingsvcs.github.webhooks import GitHubAppWebHookEvent
    from reviewboard.scmtools.models import Repository


class RecordingHandler(BaseGitHubAppWebHookHandler):
    """A webhook handler that records the events it receives.

    Version Added:
        9.0
    """

    handler_id = 'recording-handler'
    events = {'pull_request'}

    ######################
    # Instance variables #
    ######################

    #: The events received by the handler.
    received: list[GitHubAppWebHookEvent]

    #: The installation status seen when each event was received.
    statuses: list[str | None]

    def __init__(self) -> None:
        """Initialize the handler."""
        self.received = []
        self.statuses = []

    def handle_event(
        self,
        event: GitHubAppWebHookEvent,
    ) -> None:
        """Record an event.

        Args:
            event (reviewboard.hostingsvcs.github.webhooks.
                   GitHubAppWebHookEvent):
                The event to record.
        """
        self.received.append(event)

        installation_account = event.installation_account

        if installation_account is None:
            self.statuses.append(None)
        else:
            installation_account.refresh_from_db()
            self.statuses.append(
                installation_account.data['github_app']['status'])


class FailingHandler(BaseGitHubAppWebHookHandler):
    """A webhook handler that raises an error.

    Version Added:
        9.0
    """

    handler_id = 'failing-handler'
    events = {'pull_request'}

    def handle_event(
        self,
        event: GitHubAppWebHookEvent,
    ) -> None:
        """Raise an error.

        Args:
            event (reviewboard.hostingsvcs.github.webhooks.
                   GitHubAppWebHookEvent, unused):
                The event.

        Raises:
            Exception:
                Always raised.
        """
        raise Exception('Fail')


class GitHubAppWebHookViewTests(GitHubTestCase):
    """Unit tests for GitHubAppWebHookView.

    Version Added:
        9.0
    """

    def setUp(self) -> None:
        """Set up the test."""
        super().setUp()

        self.url = local_site_reverse(
            'github-app-webhook',
            kwargs={'hosting_service_id': 'github'})

    def test_post_acknowledges_delivery(self) -> None:
        """Testing GitHubAppWebHookView POST acknowledges the delivery"""
        url = local_site_reverse('github-app-webhook',
                                 kwargs={'hosting_service_id': 'github'})

        # GitHub is the caller, so the endpoint accepts an unauthenticated,
        # CSRF-free POST.
        response = self.client.post(url,
                                    data='{}',
                                    content_type='application/json',
                                    HTTP_X_GITHUB_EVENT='ping')

        self.assertEqual(response.status_code, 204)

    def test_get_not_allowed(self) -> None:
        """Testing GitHubAppWebHookView rejects GET requests"""
        url = local_site_reverse('github-app-webhook',
                                 kwargs={'hosting_service_id': 'github'})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 405)

    def test_post_with_bad_signature(self) -> None:
        """Testing GitHubAppWebHookView rejects a bad signature"""
        response = self._post_event(
            'installation',
            self._installation_payload('deleted'),
            secret='wrongsecret')

        self.assertEqual(response.status_code, 400)

    def test_post_with_missing_signature(self) -> None:
        """Testing GitHubAppWebHookView rejects a missing signature"""
        self._create_app_installation_account()

        response = self._post_event(
            'installation',
            self._installation_payload('deleted'),
            sign=False)

        self.assertEqual(response.status_code, 400)

    def test_post_with_unknown_app_id(self) -> None:
        """Testing GitHubAppWebHookView rejects an unknown app ID"""
        self._create_app_installation_account()

        response = self._post_event(
            'installation',
            self._installation_payload('deleted', app_id=99999))

        self.assertEqual(response.status_code, 400)

    def test_post_with_empty_webhook_secret(self) -> None:
        """Testing GitHubAppWebHookView rejects a delivery for an app record
        stored without a webhook secret
        """
        app_account = self._create_app_installation_account()
        app_account.data['github_app']['webhook_secret'] = encrypt_password('')
        app_account.save(update_fields=('data',))

        # An empty secret is a key anyone can sign with, so a delivery signed
        # with it must not be accepted.
        response = self._post_event(
            'installation',
            self._installation_payload('deleted'),
            secret='')

        self.assertEqual(response.status_code, 400)

    def test_installation_deleted_marks_removed(self) -> None:
        """Testing GitHubAppWebHookView marks an installation removed"""
        installation = self._create_app_installation_account()

        response = self._post_event('installation',
                                    self._installation_payload('deleted'))

        self.assertEqual(response.status_code, 204)

        installation.refresh_from_db()
        self.assertEqual(installation.data['github_app']['status'], 'removed')

    def test_installation_suspend_marks_suspended(self) -> None:
        """Testing GitHubAppWebHookView marks an installation suspended"""
        installation = self._create_app_installation_account()

        response = self._post_event('installation',
                                    self._installation_payload('suspend'))

        self.assertEqual(response.status_code, 204)

        installation.refresh_from_db()
        self.assertEqual(installation.data['github_app']['status'],
                         'suspended')

    def test_installation_unsuspend_marks_active(self) -> None:
        """Testing GitHubAppWebHookView clears status on unsuspend"""
        installation = self._create_app_installation_account(
            status='suspended')

        response = self._post_event('installation',
                                    self._installation_payload('unsuspend'))

        self.assertEqual(response.status_code, 204)

        installation.refresh_from_db()
        self.assertEqual(installation.data['github_app']['status'], 'active')

    def test_installation_created_heals_reinstall(self) -> None:
        """Testing GitHubAppWebHookView heals a reinstall by owner ID

        A reinstall performed on the GitHub side issues a new installation ID.
        Matching on the stable owner ID lets the 'created' event update the
        existing account rather than leaving it broken.
        """
        installation = self._create_app_installation_account(status='removed')

        response = self._post_event(
            'installation',
            self._installation_payload('created', installation_id=1234))

        self.assertEqual(response.status_code, 204)

        installation.refresh_from_db()
        github_app = installation.data['github_app']
        self.assertEqual(github_app['status'], 'active')
        self.assertEqual(github_app['installation_id'], 1234)

    def test_installation_created_without_existing_account(self) -> None:
        """Testing GitHubAppWebHookView ignores 'created' with no account"""
        self._create_app_record_account()

        response = self._post_event('installation',
                                    self._installation_payload('created'))

        # The wizard owns brand-new installs, so nothing is created here.
        self.assertEqual(response.status_code, 204)

        roles = [
            account.data.get('github_app', {}).get('role')
            for account in HostingServiceAccount.objects.filter(
                service_name='github')
        ]
        self.assertNotIn('installation', roles)

    def test_installation_repositories_updates_selection(self) -> None:
        """Testing GitHubAppWebHookView updates repository_selection"""
        installation = self._create_app_installation_account()

        payload = self._installation_payload('added')
        payload['repository_selection'] = 'selected'

        response = self._post_event('installation_repositories', payload)

        self.assertEqual(response.status_code, 204)

        installation.refresh_from_db()
        self.assertEqual(
            installation.data['github_app']['repository_selection'],
            'selected')

    def test_unhandled_action_is_acknowledged(self) -> None:
        """Testing GitHubAppWebHookView acknowledges an unhandled action"""
        self._create_app_installation_account()

        response = self._post_event(
            'installation',
            self._installation_payload('new_permissions_accepted'))

        self.assertEqual(response.status_code, 204)

    def test_installation_event_with_invalid_payload(
        self,
    ) -> None:
        """Testing GitHubAppWebHookView rejects an installation event whose
        payload passes base validation but fails installation validation
        """
        installation = self._create_app_installation_account()
        old_data = installation.data

        payload = self._installation_payload('added')
        payload['repository_selection'] = 'bogus'

        with self.assertLogs('reviewboard.hostingsvcs.github.views',
                             level='WARNING') as logs:
            response = self._post_event('installation_repositories', payload,
                                        delivery_id='delivery-1')

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content, b'Invalid payload format')

        self.assertEqual(len(logs.records), 1)
        self.assertTrue(logs.records[0].getMessage().startswith(
            'Could not decode GitHub App webhook installation_repositories '
            'payload (delivery delivery-1): '))

        installation.refresh_from_db()
        self.assertEqual(installation.data, old_data)

    def test_installation_event_with_error(self) -> None:
        """Testing GitHubAppWebHookView raises errors from installation
        event handling so GitHub reports a failed delivery
        """
        self._create_app_installation_account()

        self.spy_on(GitHubAppWebHookView._handle_installation_event,
                    owner=GitHubAppWebHookView,
                    op=kgb.SpyOpRaise(Exception('fail')))

        with self.assertRaisesMessage(Exception, 'fail'):
            self._post_event('installation',
                             self._installation_payload('deleted'))

    def test_installation_target_renames_owner(self) -> None:
        """Testing GitHubAppWebHookView refreshes the owner login on rename"""
        installation = self._create_app_installation_account()

        response = self._post_event(
            'installation_target',
            self._installation_target_payload(owner_id=555,
                                              new_login='neworg'))

        self.assertEqual(response.status_code, 204)

        installation.refresh_from_db()
        self.assertEqual(installation.data['github_app']['owner_login'],
                         'neworg')
        self.assertEqual(installation.username, 'neworg')

    def test_installation_target_unknown_owner_ignored(self) -> None:
        """Testing GitHubAppWebHookView ignores a rename for unknown owner"""
        installation = self._create_app_installation_account()

        response = self._post_event(
            'installation_target',
            self._installation_target_payload(owner_id=999,
                                              new_login='neworg'))

        self.assertEqual(response.status_code, 204)

        installation.refresh_from_db()
        self.assertEqual(installation.data['github_app']['owner_login'],
                         'myorg')
        self.assertEqual(installation.username, 'myorg')

    def test_unhandled_event(self) -> None:
        """Testing GitHubAppWebHookView acknowledges an event with no
        handlers without verifying it
        """
        handler = self._register_handler(RecordingHandler())

        response = self._post_event('push',
                                    self._pull_request_payload(),
                                    sign=False)

        self.assertEqual(response.status_code, 204)
        self.assertEqual(handler.received, [])

    def test_handler_with_bad_signature(self) -> None:
        """Testing GitHubAppWebHookView does not call handlers for a delivery
        with a bad signature
        """
        self._create_app_installation_account()
        handler = self._register_handler(RecordingHandler())

        with self.assertLogs(level=logging.WARNING) as logs:
            response = self._post_event('pull_request',
                                        self._pull_request_payload(),
                                        secret='wrongsecret',
                                        delivery_id='delivery-1')

        self.assertEqual(response.status_code, 400)
        self.assertEqual(handler.received, [])
        self.assertEqual(
            logs.records[0].getMessage(),
            'Could not verify the signature of GitHub App webhook '
            'pull_request event (delivery delivery-1).')

    def test_handler_with_invalid_payload(self) -> None:
        """Testing GitHubAppWebHookView rejects an invalid payload for an
        event with handlers
        """
        handler = self._register_handler(RecordingHandler())

        with self.assertLogs('reviewboard.hostingsvcs.github.views',
                             level='WARNING') as logs:
            response = self.client.post(self.url,
                                        data=b'blah',
                                        content_type='application/json',
                                        headers={
                                            'X-GitHub-Delivery': 'delivery-1',
                                            'X-GitHub-Event': 'pull_request',
                                        })

        self.assertEqual(response.status_code, 400)
        self.assertEqual(handler.received, [])
        self.assertEqual(len(logs.records), 1)
        self.assertTrue(logs.records[0].getMessage().startswith(
            'Could not decode GitHub App webhook payload (delivery '
            'delivery-1): '))

    def test_handler_receives_event(self) -> None:
        """Testing GitHubAppWebHookView passes a verified event to its
        handlers
        """
        installation = self._create_app_installation_account()
        repository = self._create_installation_repository(installation)
        handler = self._register_handler(RecordingHandler())
        payload = self._pull_request_payload()

        response = self._post_event('pull_request',
                                    payload,
                                    delivery_id='delivery-1')

        self.assertEqual(response.status_code, 204)
        self.assertEqual(len(handler.received), 1)

        event = handler.received[0]
        self.assertEqual(event.event_name, 'pull_request')
        self.assertEqual(event.delivery_id, 'delivery-1')
        self.assertEqual(event.payload, payload)
        self.assertEqual(
            event.app_account.pk,
            installation.data['github_app']['app_account_id'])
        self.assertEqual(event.installation_account, installation)
        self.assertEqual(event.repository, repository)

    def test_handler_with_untracked_repository(self) -> None:
        """Testing GitHubAppWebHookView passes no repository for a repository
        not found in RB
        """
        installation = self._create_app_installation_account()
        self._create_installation_repository(installation)
        handler = self._register_handler(RecordingHandler())

        response = self._post_event(
            'pull_request',
            self._pull_request_payload(repo_name='otherrepo'))

        self.assertEqual(response.status_code, 204)
        self.assertEqual(len(handler.received), 1)
        self.assertEqual(handler.received[0].installation_account,
                         installation)
        self.assertIsNone(handler.received[0].repository)

    def test_handler_without_repository_in_payload(self) -> None:
        """Testing GitHubAppWebHookView passes no repository for a payload
        without one
        """
        installation = self._create_app_installation_account()
        self._create_installation_repository(installation)
        handler = self._register_handler(RecordingHandler())
        payload = self._pull_request_payload()
        del payload['repository']

        response = self._post_event('pull_request', payload)

        self.assertEqual(response.status_code, 204)
        self.assertEqual(len(handler.received), 1)
        self.assertIsNone(handler.received[0].repository)

    def test_handler_with_error(self) -> None:
        """Testing GitHubAppWebHookView logs a handler error and calls the
        remaining handlers
        """
        self._create_app_installation_account()
        self._register_handler(FailingHandler())
        handler = self._register_handler(RecordingHandler())

        with self.assertLogs() as logs:
            response = self._post_event('pull_request',
                                        self._pull_request_payload(),
                                        delivery_id='delivery-1')

        self.assertEqual(response.status_code, 204)
        self.assertEqual(len(handler.received), 1)
        self.assertEqual(len(logs.records), 1)
        self.assertEqual(
            logs.records[0].getMessage(),
            "Error handling GitHub App webhook pull_request event in "
            "handler 'failing-handler' (delivery delivery-1): Fail")

    def test_handler_for_builtin_event(self) -> None:
        """Testing GitHubAppWebHookView calls handlers for a built-in event
        after handling it
        """
        installation = self._create_app_installation_account()

        class InstallationHandler(RecordingHandler):
            handler_id = 'installation-handler'
            events = {'installation'}

        handler = self._register_handler(InstallationHandler())

        response = self._post_event('installation',
                                    self._installation_payload('deleted'))

        self.assertEqual(response.status_code, 204)
        self.assertEqual(len(handler.received), 1)
        self.assertEqual(handler.received[0].installation_account,
                         installation)
        self.assertEqual(handler.statuses, ['removed'])

    def _register_handler(
        self,
        handler: BaseGitHubAppWebHookHandler,
    ) -> BaseGitHubAppWebHookHandler:
        """Register a webhook handler for the duration of the test.

        Args:
            handler (BaseGitHubAppWebHookHandler):
                The handler to register.

        Returns:
            BaseGitHubAppWebHookHandler:
            The registered handler.
        """
        github_app_webhook_handler_registry.register(handler)
        self.addCleanup(github_app_webhook_handler_registry.unregister,
                        handler)

        return handler

    def _create_installation_repository(
        self,
        installation: HostingServiceAccount,
        *,
        repo_name: str = 'myrepo',
    ) -> Repository:
        """Return a new repository connected through an installation.

        Args:
            installation (reviewboard.hostingsvcs.models.
                          HostingServiceAccount):
                The installation account.

            repo_name (str, optional):
                The name of the repository on GitHub.

        Returns:
            reviewboard.scmtools.models.Repository:
            The new repository.
        """
        return self.create_repository(
            hosting_account=installation,
            extra_data={
                'repository_plan': 'public-org',
                'github_public_org_name': 'myorg',
                'github_public_org_repo_name': repo_name,
            })

    def _pull_request_payload(
        self,
        *,
        installation_id: int = 99,
        owner_login: str = 'myorg',
        repo_name: str = 'myrepo',
    ) -> dict[str, Any]:
        """Return a webhook payload for an opened pull request event.

        Args:
            installation_id (int, optional):
                The installation ID to include.

            owner_login (str, optional):
                The login of the repository owner.

            repo_name (str, optional):
                The name of the repository.

        Returns:
            dict:
            The webhook payload.
        """
        return {
            'action': 'opened',
            'installation': {
                'id': installation_id,
                'node_id': 'abc',
            },
            'number': 6,
            'pull_request': {
                'id': 1000,
                'number': 6,
            },
            'repository': {
                'full_name': f'{owner_login}/{repo_name}',
                'name': repo_name,
                'owner': {
                    'login': owner_login,
                },
            },
        }

    def _installation_payload(
        self,
        action: str,
        *,
        app_id: (int | None) = None,
        installation_id: int = 99,
        owner_id: int = 555,
        owner_login: str = 'myorg',
    ) -> dict[str, Any]:
        """Return a webhook payload for an installation event.

        Args:
            action (str):
                The event action.

            app_id (int, optional):
                The app ID to include. Defaults to the test app's ID.

            installation_id (int, optional):
                The installation ID to include.

            owner_id (int, optional):
                The owner ID to include.

            owner_login (str, optional):
                The owner login to include.

        Returns:
            dict:
            The webhook payload.
        """
        return {
            'action': action,
            'installation': {
                'id': installation_id,
                'app_id': app_id if app_id is not None else self.app_id,
                'account': {
                    'id': owner_id,
                    'login': owner_login,
                    'type': 'Organization',
                },
            },
        }

    def _installation_target_payload(
        self,
        *,
        owner_id: int,
        new_login: str,
        old_login: str = 'myorg',
        installation_id: int = 99,
    ) -> dict[str, Any]:
        """Return a webhook payload for an installation_target rename event.

        The ``installation`` object mirrors what GitHub sends for this event:
        a lightweight object with only an ID, and no app ID. The renamed
        account is at the top level.

        Args:
            owner_id (int):
                The stable owner ID of the renamed account.

            new_login (str):
                The account's new login.

            old_login (str, optional):
                The account's previous login.

            installation_id (int, optional):
                The installation ID to include.

        Returns:
            dict:
            The webhook payload.
        """
        return {
            'action': 'renamed',
            'target_type': 'Organization',
            'account': {
                'id': owner_id,
                'login': new_login,
                'type': 'Organization',
            },
            'changes': {
                'login': {
                    'from': old_login,
                },
            },
            'installation': {
                'id': installation_id,
            },
        }

    def _post_event(
        self,
        event: str,
        payload: dict[str, Any],
        *,
        secret: (str | None) = None,
        sign: bool = True,
        delivery_id: (str | None) = None,
    ) -> _MonkeyPatchedWSGIResponse:
        """POST a signed webhook delivery to the view.

        Args:
            event (str):
                The value for the ``X-GitHub-Event`` header.

            payload (dict):
                The JSON payload to send.

            secret (str, optional):
                The secret to sign with. Defaults to the test webhook secret.
                An empty string signs with an empty key.

            sign (bool, optional):
                Whether to include a signature header at all.

            delivery_id (str, optional):
                The value for the ``X-GitHub-Delivery`` header, if any.

        Returns:
            django.test.client.HttpResponse:
            The response from the view.
        """
        body = json.dumps(payload).encode('utf-8')
        headers = {'X-GitHub-Event': event}

        if delivery_id is not None:
            headers['X-GitHub-Delivery'] = delivery_id

        if sign:
            if secret is None:
                secret = self.webhook_secret

            digest = hmac.new(secret.encode('utf-8'),
                              body,
                              hashlib.sha256).hexdigest()
            headers['X-Hub-Signature-256'] = f'sha256={digest}'

        return self.client.post(self.url,
                                data=body,
                                content_type='application/json',
                                headers=headers)
