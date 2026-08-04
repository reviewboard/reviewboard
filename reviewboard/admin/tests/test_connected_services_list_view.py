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

        self.client.login(username='admin', password='admin')
        response = self.client.get(self.url)

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

    def test_get_requires_staff(self) -> None:
        """Testing ConnectedServicesListView GET requires a staff member"""
        self.client.login(username='doc', password='doc')
        response = self.client.get(self.url)

        # Non-staff users are redirected to the admin login.
        self.assertEqual(response.status_code, 302)

    def test_get_with_anonymous(self) -> None:
        """Testing ConnectedServicesListView GET with an anonymous user"""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)
