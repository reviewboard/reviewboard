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
        self.assertNotIn('redirect', rsp)

        account = HostingServiceAccount.objects.get(service_name='test',
                                                    username='myuser')
        self.assertTrue(account.is_authorized)

        # The success step offers the next actions for the account, and
        # reloads the list when closed.
        html = rsp['html']
        self.assertIn('Connected to Test Service', html)
        self.assertIn(
            f'data-wizard-close-url="{reverse("connected-services-list")}"',
            html)
        self.assertIn(
            '/admin/db/scmtools/repository/add/?hosting_type=test&amp;'
            f'hosting_account={account.pk}&amp;'
            'next=%2Fadmin%2Fconnected-services%2F',
            html)
        self.assertIn(
            '/admin/db/hostingsvcs/configuredbugtracker/add/?'
            f'service_name=test&amp;hosting_account={account.pk}&amp;'
            'next=%2Fadmin%2Fconnected-services%2F',
            html)

    def test_post_with_bug_tracker_service(self) -> None:
        """Testing ConnectServiceView POST with a bug tracker service offers
        only a bug tracker
        """
        class BugTrackerTestService(TestService):
            hosting_service_id = 'test-bug-tracker'
            name = 'Test Bug Tracker'
            supports_repositories = False

            # Don't reuse the parent class's cached connect UI.
            _connect_ui = None

        hosting_service_registry.register(BugTrackerTestService)

        try:
            self.client.login(username='admin', password='admin')
            response = self.client.post(
                self._get_url('test-bug-tracker'),
                {
                    'hosting_account_username': 'myuser',
                    'hosting_account_password': 'mypass',
                })
        finally:
            hosting_service_registry.unregister(BugTrackerTestService)

        self.assertEqual(response.status_code, 200)

        rsp = json.loads(response.content)
        self.assertTrue(rsp['success'])

        html = rsp['html']
        self.assertIn('Add a bug tracker', html)
        self.assertNotIn('Add a repository', html)

    def test_add_object_actions_with_local_site_account(self) -> None:
        """Testing BaseHostingServiceConnectUI.get_add_object_actions with a
        Local Site account includes the Local Site
        """
        local_site = self.create_local_site()
        account = HostingServiceAccount.objects.create(
            local_site=local_site,
            service_name='test',
            username='myuser')

        actions = TestService.connect_ui.get_add_object_actions(
            self.create_http_request(),
            account=account)

        self.assertEqual(len(actions), 2)

        for action in actions:
            self.assertIn(f'local_site={local_site.pk}', action['url'])

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

    def test_get_with_authenticated_bug_tracker_service(self) -> None:
        """Testing ConnectServiceView GET with a bug tracker service that
        connects accounts
        """
        self.client.login(username='admin', password='admin')

        response = self.client.get(self._get_url('jira'))

        # The deployment choice is offered first. JIRA configurations
        # require an account, so there is no link to configure one
        # without linking.
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'?deployment=cloud', response.content)
        self.assertIn(b'?deployment=dc', response.content)
        self.assertNotIn(b'/jira/bug-trackers/add/', response.content)

    def test_get_jira_cloud_form(self) -> None:
        """Testing ConnectServiceView GET with the JIRA Cloud deployment"""
        self.client.login(username='admin', password='admin')

        response = self.client.get(self._get_url('jira'),
                                   {'deployment': 'cloud'})

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'jira_cloud_site', response.content)
        self.assertIn(b'hosting_account_username', response.content)
        self.assertIn(b'API token', response.content)

        # The server URL field belongs to the Data Center flow.
        self.assertNotIn(b'name="jira_server_url"', response.content)

    def test_get_jira_dc_form(self) -> None:
        """Testing ConnectServiceView GET with the JIRA Data Center
        deployment
        """
        self.client.login(username='admin', password='admin')

        response = self.client.get(self._get_url('jira'),
                                   {'deployment': 'dc'})

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'name="jira_server_url"', response.content)
        self.assertIn(b'hosting_account_username', response.content)

        # The site name field belongs to the Cloud flow.
        self.assertNotIn(b'name="jira_cloud_site"', response.content)

    def test_get_bugzilla_form(self) -> None:
        """Testing ConnectServiceView GET with Bugzilla"""
        self.client.login(username='admin', password='admin')

        response = self.client.get(self._get_url('bugzilla'))

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'name="bugzilla_url"', response.content)
        self.assertIn(b'hosting_account_username', response.content)
        self.assertIn(b'API key', response.content)

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
