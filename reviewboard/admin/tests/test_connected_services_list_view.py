"""Unit tests for reviewboard.admin.views.ConnectedServicesListView."""

from __future__ import annotations

from django.urls import reverse

from reviewboard.hostingsvcs.models import HostingServiceAccount
from reviewboard.testing.testcase import TestCase


class ConnectedServicesListViewTests(TestCase):
    """Unit tests for ConnectedServicesListView."""

    fixtures = ['test_users', 'test_scmtools']

    @classmethod
    def setUpClass(cls) -> None:
        """Set up the test case class."""
        super().setUpClass()

        cls.url = reverse('connected-services-list')

    def test_get(self) -> None:
        """Testing ConnectedServicesListView GET"""
        self.client.login(username='admin', password='admin')
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

        context = response.context
        self.assertEqual(context['title'], 'Connected Services')

        # The "available services" list should contain every visible service
        # that needs authorization, such as GitHub.
        available_ids = {
            service['id']
            for service in context['available_services']
        }
        self.assertIn('github', available_ids)

    def test_get_with_accounts(self) -> None:
        """Testing ConnectedServicesListView GET with hosting accounts"""
        HostingServiceAccount.objects.create(
            service_name='github',
            username='user1',
            visible=True)

        self.client.login(username='admin', password='admin')
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['service_entries']), 1)
        self.assertIn(b'user1', response.content)

        # GitHub supports repositories, so an account with no repositories
        # shows a "0 repositories" detail.
        self.assertIn(b'0 repositories', response.content)

    def test_get_with_repository_count(self) -> None:
        """Testing ConnectedServicesListView GET renders the repository count
        """
        account = HostingServiceAccount.objects.create(
            service_name='github',
            username='user1',
            visible=True)
        self.create_repository(hosting_account=account)
        self.create_repository(name='Test Repo 2',
                               hosting_account=account)

        self.client.login(username='admin', password='admin')
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'2 repositories', response.content)

    def test_get_renders_account_menu(self) -> None:
        """Testing ConnectedServicesListView GET renders the account settings
        menu with an Edit Credentials item
        """
        account = HostingServiceAccount.objects.create(
            service_name='bitbucket',
            username='user1',
            visible=True)

        self.client.login(username='admin', password='admin')
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

        content = response.content
        self.assertIn(b'data-account-menu', content)
        self.assertIn(b'edit-credentials', content)
        self.assertIn(
            reverse(
                'connected-services-account-edit-credentials',
                kwargs={
                    'service_id': 'bitbucket',
                    'account_id': account.pk,
                }).encode('utf-8'),
            content)

    def test_get_github_pat_renders_account_menu(self) -> None:
        """Testing ConnectedServicesListView GET renders the account menu for a
        GitHub Personal Access Token account
        """
        HostingServiceAccount.objects.create(
            service_name='github',
            username='user1',
            visible=True)

        self.client.login(username='admin', password='admin')
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'data-account-menu', response.content)
        self.assertIn(b'edit-credentials', response.content)

    def test_get_github_app_install_omits_account_menu(self) -> None:
        """Testing ConnectedServicesListView GET omits the account menu for a
        GitHub App installation account
        """
        HostingServiceAccount.objects.create(
            service_name='github',
            username='acme-org',
            visible=True,
            data={
                'github_app': {
                    'app_account_id': 1,
                    'installation_id': 42,
                    'owner_login': 'myuser',
                    'owner_type': 'user',
                    'repository_selection': 'all',
                    'role': 'installation',
                },
            })

        self.client.login(username='admin', password='admin')
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

        # App installations have no credentials to edit, so they get no menu.
        self.assertIn(b'acme-org', response.content)
        self.assertNotIn(b'data-account-menu', response.content)

    def test_get_without_attention_items(self) -> None:
        """Testing ConnectedServicesListView GET shows no alert when no
        connection needs attention
        """
        HostingServiceAccount.objects.create(
            service_name='github',
            username='user1',
            visible=True)

        self.client.login(username='admin', password='admin')
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['attention_items'], [])
        self.assertNotIn(b'needs attention', response.content)

    def test_get_with_attention_item(self) -> None:
        """Testing ConnectedServicesListView GET shows an alert for a
        suspended GitHub installation
        """
        account = HostingServiceAccount.objects.create(
            service_name='github',
            username='acme-org',
            visible=True,
            data={
                'github_app': {
                    'role': 'installation',
                    'status': 'suspended',
                    'app_account_id': 1,
                    'installation_id': 42,
                    'owner_login': 'acme-org',
                    'owner_type': 'organization',
                },
            })

        self.client.login(username='admin', password='admin')
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

        self.assertEqual(len(response.context['attention_items']), 1)

        content = response.content
        self.assertIn(b'1 connection needs attention', content)
        self.assertIn(b'Suspended on GitHub', content)

        # The fix action is wired up for the client to dispatch, pointing at
        # the reconnect view, which verifies the state with GitHub first.
        self.assertIn(b'data-attention-fix', content)
        self.assertIn(
            f'github-app/{account.pk}/reconnect/'.encode('utf-8'),
            content)

    def test_get_attention_items_pluralize(self) -> None:
        """Testing ConnectedServicesListView GET pluralizes the alert heading
        """
        for username in ('acme-org', 'beta-org'):
            HostingServiceAccount.objects.create(
                service_name='github',
                username=username,
                visible=True,
                data={
                    'github_app': {
                        'role': 'installation',
                        'status': 'removed',
                        'app_account_id': 1,
                        'installation_id': 42,
                        'owner_login': username,
                    },
                })

        self.client.login(username='admin', password='admin')
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['attention_items']), 2)
        self.assertIn(b'2 connections need attention', response.content)

    def test_get_sorts_entries_by_service_name(self) -> None:
        """Testing ConnectedServicesListView GET sorts entries by service
        name
        """
        HostingServiceAccount.objects.create(
            service_name='github',
            username='user1',
            visible=True)
        HostingServiceAccount.objects.create(
            service_name='bitbucket',
            username='user2',
            visible=True)

        self.client.login(username='admin', password='admin')
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

        content = response.content
        self.assertEqual(len(response.context['service_entries']), 2)

        # Bitbucket should sort before GitHub.
        self.assertLess(content.index(b'user2'), content.index(b'user1'))

    def test_get_with_invisible_account(self) -> None:
        """Testing ConnectedServicesListView GET with an invisible account"""
        HostingServiceAccount.objects.create(
            service_name='github',
            username='user1',
            visible=False)

        client = self.client
        client.login(username='admin', password='admin')
        response = client.get(self.url)

        self.assertEqual(response.status_code, 200)

        # The service group is still built from the account, but the account
        # row itself is hidden in the rendered entry.
        self.assertEqual(len(response.context['service_entries']), 1)
        self.assertNotIn(b'user1', response.content)

    def test_get_with_unknown_service(self) -> None:
        """Testing ConnectedServicesListView GET with an account whose
        service is not in the registry
        """
        HostingServiceAccount.objects.create(
            service_name='not-a-real-service',
            username='user1',
            visible=True)

        self.client.login(username='admin', password='admin')
        response = self.client.get(self.url)

        # Accounts with an unloadable service are grouped under None and
        # filtered out, rather than crashing the view.
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['service_entries'], [])

    def test_get_pops_auto_connect_url(self) -> None:
        """Testing ConnectedServicesListView GET pops connect_wizard_url"""
        client = self.client
        client.login(username='admin', password='admin')

        session = client.session
        session['connect_wizard_url'] = '/admin/connected-services/foo/'
        session.save()

        response = client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['auto_connect_url'],
                         '/admin/connected-services/foo/')

        # The value is single-use, so it should be cleared from the session.
        self.assertNotIn('connect_wizard_url', client.session)

    def test_get_without_auto_connect_url(self) -> None:
        """Testing ConnectedServicesListView GET without connect_wizard_url"""
        client = self.client
        client.login(username='admin', password='admin')
        response = client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context['auto_connect_url'])

    def test_get_requires_staff(self) -> None:
        """Testing ConnectedServicesListView GET requires a staff member"""
        client = self.client
        client.login(username='doc', password='doc')
        response = client.get(self.url)

        # Non-staff users are redirected to the admin login.
        self.assertEqual(response.status_code, 302)

    def test_get_with_anonymous(self) -> None:
        """Testing ConnectedServicesListView GET with an anonymous user"""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)
