"""Unit tests for reviewboard.admin.views.ConnectServiceView.

Version Added:
    9.0
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING
from unittest import skip

from django.urls import reverse

from reviewboard.hostingsvcs.base import hosting_service_registry
from reviewboard.hostingsvcs.models import HostingServiceAccount
from reviewboard.testing import TestCase
from reviewboard.testing.hosting_services import TestService

if TYPE_CHECKING:
    from collections.abc import Sequence


class ConnectServiceViewTests(TestCase):
    """Unit tests for ConnectServiceView.

    Version Added:
        9.0
    """

    fixtures: Sequence[str] = ['test_users', 'test_scmtools']

    def setUp(self) -> None:
        """Set up state for the test."""
        super().setUp()

        hosting_service_registry.register(TestService)

    def tearDown(self) -> None:
        """Tear down state for the test."""
        hosting_service_registry.unregister(TestService)

        super().tearDown()

    def test_get(self) -> None:
        """Testing ConnectServiceView GET returns the connect UI fragment"""
        self.client.login(username='admin', password='admin')
        response = self.client.get(self._get_url('test'))

        self.assertEqual(response.status_code, 200)

        # The form fields are rendered. The service name/logo are shown in the
        # dialog header (client-side), not in this fragment.
        self.assertIn(b'hosting_account_username', response.content)

    def test_get_with_unknown_service(self) -> None:
        """Testing ConnectServiceView GET with an unknown service"""
        self.client.login(username='admin', password='admin')
        response = self.client.get(self._get_url('not-a-real-service'))

        self.assertEqual(response.status_code, 404)

    def test_get_requires_staff(self) -> None:
        """Testing ConnectServiceView GET requires a staff member"""
        self.client.login(username='doc', password='doc')
        response = self.client.get(self._get_url('test'))

        self.assertEqual(response.status_code, 302)

    def test_get_with_github_renders_choices(self) -> None:
        """Testing ConnectServiceView GET for GitHub renders the connection
        method choices
        """
        self.client.login(username='admin', password='admin')
        response = self.client.get(self._get_url('github'))

        self.assertEqual(response.status_code, 200)

        content = response.content
        self.assertIn(b'Connect using a GitHub App', content)
        self.assertIn(b'Connect with a Personal Access Token', content)

        # The PAT method links to its own page rather than rendering the form
        # inline.
        self.assertIn(b'method=pat', content)
        self.assertNotIn(b'hosting_account_username', content)

    @skip('Disabled until implementation is complete')
    def test_get_with_github_connected_accounts(self) -> None:
        """Testing ConnectServiceView GET for GitHub renders "Add a
        repository" options for connected accounts
        """
        HostingServiceAccount.objects.create(
            service_name='github',
            username='acme-org',
            data={
                'github_app': {
                    'app_account_id': 1,
                    'installation_id': 42,
                    'owner_avatar_url': 'https://example.com/avatar.png',
                    'owner_login': 'acme-org',
                    'role': 'installation',
                },
            })

        self.client.login(username='admin', password='admin')
        response = self.client.get(self._get_url('github'))

        self.assertEqual(response.status_code, 200)

        content = response.content
        self.assertIn(b'Add a repository for acme-org', content)
        self.assertIn(b'https://example.com/avatar.png', content)

    def test_get_with_github_pat_method(self) -> None:
        """Testing ConnectServiceView GET for GitHub with ?method=pat renders
        the Personal Access Token form
        """
        self.client.login(username='admin', password='admin')
        url = f'{self._get_url("github")}?method=pat'
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'hosting_account_username', response.content)

    def test_post_creates_account(self) -> None:
        """Testing ConnectServiceView POST creates a hosting service account"""
        self.client.login(username='admin', password='admin')
        response = self.client.post(self._get_url('test'), {
            'hosting_account_username': 'myuser',
            'hosting_account_password': 'mypass',
        })

        self.assertEqual(response.status_code, 200)

        rsp = json.loads(response.content)
        self.assertTrue(rsp['success'])
        self.assertEqual(rsp['redirect'], reverse('connected-services-list'))

        account = HostingServiceAccount.objects.get(service_name='test',
                                                    username='myuser')
        self.assertTrue(account.is_authorized)

    def test_post_with_authorization_error(self) -> None:
        """Testing ConnectServiceView POST surfaces an AuthorizationError"""
        self.client.login(username='admin', password='admin')
        response = self.client.post(self._get_url('test'), {
            'hosting_account_username': 'baduser',
            'hosting_account_password': 'mypass',
        })

        self.assertEqual(response.status_code, 200)

        rsp = json.loads(response.content)
        self.assertFalse(rsp['success'])
        self.assertIn('Unable to link the account', rsp['html'])

        self.assertFalse(
            HostingServiceAccount.objects.filter(username='baduser').exists())

    def test_post_with_two_factor_auth_required(self) -> None:
        """Testing ConnectServiceView POST surfaces a
        TwoFactorAuthCodeRequiredError
        """
        self.client.login(username='admin', password='admin')
        response = self.client.post(self._get_url('test'), {
            'hosting_account_username': '2fa-user',
            'hosting_account_password': 'mypass',
        })

        self.assertEqual(response.status_code, 200)

        rsp = json.loads(response.content)
        self.assertFalse(rsp['success'])
        self.assertIn('2FA code', rsp['html'])

    def test_post_with_invalid_form(self) -> None:
        """Testing ConnectServiceView POST with a missing required field"""
        self.client.login(username='admin', password='admin')
        response = self.client.post(self._get_url('test'), {
            'hosting_account_username': 'myuser',
        })

        self.assertEqual(response.status_code, 200)

        rsp = json.loads(response.content)
        self.assertFalse(rsp['success'])

        self.assertFalse(
            HostingServiceAccount.objects.filter(username='myuser').exists())

    def test_post_requires_staff(self) -> None:
        """Testing ConnectServiceView POST requires a staff member"""
        self.client.login(username='doc', password='doc')
        response = self.client.post(self._get_url('test'), {
            'hosting_account_username': 'myuser',
            'hosting_account_password': 'mypass',
        })

        self.assertEqual(response.status_code, 302)
        self.assertFalse(
            HostingServiceAccount.objects.filter(username='myuser').exists())

    def _get_url(
        self,
        service_id: str,
    ) -> str:
        """Return the connect URL for a service.

        Args:
            service_id (str):
                The ID of the hosting service.

        Returns:
            str:
            The connect URL.
        """
        return reverse('connected-services-connect',
                       kwargs={'service_id': service_id})
