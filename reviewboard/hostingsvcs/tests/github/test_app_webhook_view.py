"""Unit tests for the GitHub App webhook handler.

Version Added:
    9.0
"""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import TYPE_CHECKING

from reviewboard.hostingsvcs.models import HostingServiceAccount
from reviewboard.hostingsvcs.tests.github.base import GitHubTestCase
from reviewboard.scmtools.crypto_utils import encrypt_password
from reviewboard.site.urlresolvers import local_site_reverse

if TYPE_CHECKING:
    from typing import Any

    from django.test.client import _MonkeyPatchedWSGIResponse


class GitHubAppWebhookViewTests(GitHubTestCase):
    """Unit tests for GitHubAppWebhookView.

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
        """Testing GitHubAppWebhookView POST acknowledges the delivery"""
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
        """Testing GitHubAppWebhookView rejects GET requests"""
        url = local_site_reverse('github-app-webhook',
                                 kwargs={'hosting_service_id': 'github'})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 405)

    def test_post_with_bad_signature(self) -> None:
        """Testing GitHubAppWebhookView rejects a bad signature"""
        response = self._post_event(
            'installation',
            self._installation_payload('deleted'),
            secret='wrongsecret')

        self.assertEqual(response.status_code, 400)

    def test_post_with_missing_signature(self) -> None:
        """Testing GitHubAppWebhookView rejects a missing signature"""
        self._create_app_installation_account()

        response = self._post_event(
            'installation',
            self._installation_payload('deleted'),
            sign=False)

        self.assertEqual(response.status_code, 400)

    def test_post_with_unknown_app_id(self) -> None:
        """Testing GitHubAppWebhookView rejects an unknown app ID"""
        self._create_app_installation_account()

        response = self._post_event(
            'installation',
            self._installation_payload('deleted', app_id=99999))

        self.assertEqual(response.status_code, 400)

    def test_post_with_empty_webhook_secret(self) -> None:
        """Testing GitHubAppWebhookView rejects a delivery for an app record
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
        """Testing GitHubAppWebhookView marks an installation removed"""
        installation = self._create_app_installation_account()

        response = self._post_event('installation',
                                    self._installation_payload('deleted'))

        self.assertEqual(response.status_code, 204)

        installation.refresh_from_db()
        self.assertEqual(installation.data['github_app']['status'], 'removed')

    def test_installation_suspend_marks_suspended(self) -> None:
        """Testing GitHubAppWebhookView marks an installation suspended"""
        installation = self._create_app_installation_account()

        response = self._post_event('installation',
                                    self._installation_payload('suspend'))

        self.assertEqual(response.status_code, 204)

        installation.refresh_from_db()
        self.assertEqual(installation.data['github_app']['status'],
                         'suspended')

    def test_installation_unsuspend_marks_active(self) -> None:
        """Testing GitHubAppWebhookView clears status on unsuspend"""
        installation = self._create_app_installation_account(
            status='suspended')

        response = self._post_event('installation',
                                    self._installation_payload('unsuspend'))

        self.assertEqual(response.status_code, 204)

        installation.refresh_from_db()
        self.assertEqual(installation.data['github_app']['status'], 'active')

    def test_installation_created_heals_reinstall(self) -> None:
        """Testing GitHubAppWebhookView heals a reinstall by owner ID

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
        """Testing GitHubAppWebhookView ignores 'created' with no account"""
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
        """Testing GitHubAppWebhookView updates repository_selection"""
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
        """Testing GitHubAppWebhookView acknowledges an unhandled action"""
        self._create_app_installation_account()

        response = self._post_event(
            'installation',
            self._installation_payload('new_permissions_accepted'))

        self.assertEqual(response.status_code, 204)

    def test_installation_target_renames_owner(self) -> None:
        """Testing GitHubAppWebhookView refreshes the owner login on rename"""
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
        """Testing GitHubAppWebhookView ignores a rename for unknown owner"""
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

        Returns:
            django.test.client.HttpResponse:
            The response from the view.
        """
        body = json.dumps(payload).encode('utf-8')
        headers = {'X-GitHub-Event': event}

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
