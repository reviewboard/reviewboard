"""Unit tests for ConnectedServiceRepositoriesView.

Version Added:
    9.0
"""

from __future__ import annotations

from django.urls import reverse

from reviewboard.hostingsvcs.models import HostingServiceAccount
from reviewboard.testing.testcase import TestCase


class ConnectedServiceRepositoriesViewTests(TestCase):
    """Unit tests for ConnectedServiceRepositoriesView.

    Version Added:
        9.0
    """

    fixtures = ['test_users', 'test_scmtools']

    @classmethod
    def setUpClass(cls) -> None:
        """Set up the test case class."""
        super().setUpClass()

        cls.url = reverse('connected-services-repositories',
                          kwargs={'service_id': 'github'})

    def setUp(self) -> None:
        """Set up the test case."""
        super().setUp()

        self.account = HostingServiceAccount.objects.create(
            service_name='github',
            username='user1',
            visible=True)

    def test_get(self) -> None:
        """Testing ConnectedServiceRepositoriesView GET"""
        repository = self.create_repository(name='My Repo',
                                            hosting_account=self.account)

        self.client.login(username='admin', password='admin')
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

        content = response.content
        self.assertIn(b'My Repo', content)

        # Each repository links to its admin change page.
        change_url = reverse('admin:scmtools_repository_change',
                             args=(repository.pk,))
        self.assertIn(change_url.encode('utf-8'), content)

    def test_get_uses_hosting_service_display_path(self) -> None:
        """Testing ConnectedServiceRepositoriesView GET uses the hosting
        service's customized display path
        """
        self.create_repository(
            name='My Repo',
            hosting_account=self.account,
            path='git://github.com/example/reviewboard.git')

        self.client.login(username='admin', password='admin')
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

        # GitHub turns the clone URL into an "owner/repo" identifier.
        content = response.content
        self.assertIn(b'example/reviewboard', content)
        self.assertNotIn(b'git://github.com/example/reviewboard.git', content)

    def test_get_scopes_to_service(self) -> None:
        """Testing ConnectedServiceRepositoriesView GET only returns
        repositories for the requested service
        """
        bitbucket_account = HostingServiceAccount.objects.create(
            service_name='bitbucket',
            username='user2',
            visible=True)
        self.create_repository(name='GitHub Repo',
                               hosting_account=self.account)
        self.create_repository(name='Bitbucket Repo',
                               hosting_account=bitbucket_account)

        self.client.login(username='admin', password='admin')
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'GitHub Repo', response.content)
        self.assertNotIn(b'Bitbucket Repo', response.content)

    def test_get_filters_by_account(self) -> None:
        """Testing ConnectedServiceRepositoriesView GET filters by account"""
        account2 = HostingServiceAccount.objects.create(
            service_name='github',
            username='user2',
            visible=True)
        self.create_repository(name='Repo One',
                               hosting_account=self.account)
        self.create_repository(name='Repo Two',
                               hosting_account=account2)

        self.client.login(username='admin', password='admin')
        response = self.client.get(self.url, {
            'account': self.account.pk,
        })

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Repo One', response.content)
        self.assertNotIn(b'Repo Two', response.content)

    def test_get_with_invalid_account(self) -> None:
        """Testing ConnectedServiceRepositoriesView GET with a non-numeric
        account
        """
        self.create_repository(name='Repo One',
                               hosting_account=self.account)

        self.client.login(username='admin', password='admin')
        response = self.client.get(self.url, {
            'account': 'abc',
        })

        self.assertEqual(response.status_code, 404)

    def test_get_filters_by_search(self) -> None:
        """Testing ConnectedServiceRepositoriesView GET filters by search
        term
        """
        self.create_repository(name='Alpha',
                               hosting_account=self.account)
        self.create_repository(name='Beta',
                               hosting_account=self.account)

        self.client.login(username='admin', password='admin')
        response = self.client.get(self.url, {
            'q': 'Alph',
        })

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Alpha', response.content)
        self.assertNotIn(b'Beta', response.content)

    def test_get_paginates(self) -> None:
        """Testing ConnectedServiceRepositoriesView GET paginates results"""
        for i in range(30):
            self.create_repository(name=f'Repo {i:02d}',
                                   hosting_account=self.account)

        self.client.login(username='admin', password='admin')
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['X-Total-Count'], '30')
        self.assertEqual(response['X-Page-Number'], '1')
        self.assertEqual(response['X-Num-Pages'], '2')

        # The first page holds the page size (25) of repositories.
        self.assertEqual(
            response.content.count(
                b'<li class="rb-c-admin-cs-service-items__item">'),
            25)

    def test_get_second_page(self) -> None:
        """Testing ConnectedServiceRepositoriesView GET returns a later
        page
        """
        for i in range(30):
            self.create_repository(name=f'Repo {i:02d}',
                                   hosting_account=self.account)

        self.client.login(username='admin', password='admin')
        response = self.client.get(self.url, {
            'page': '2',
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['X-Page-Number'], '2')
        self.assertEqual(
            response.content.count(
                b'<li class="rb-c-admin-cs-service-items__item">'),
            5)

    def test_get_invalid_page_falls_back_to_first(self) -> None:
        """Testing ConnectedServiceRepositoriesView GET falls back to the
        first page for an invalid page number
        """
        self.create_repository(name='Only Repo',
                               hosting_account=self.account)

        self.client.login(username='admin', password='admin')
        response = self.client.get(self.url, {
            'page': 'bogus',
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['X-Page-Number'], '1')

    def test_get_includes_invisible_and_archived(self) -> None:
        """Testing ConnectedServiceRepositoriesView GET includes invisible
        and archived repositories
        """
        self.create_repository(name='Visible Repo',
                               hosting_account=self.account)
        self.create_repository(name='Hidden Repo',
                               hosting_account=self.account,
                               visible=False)
        self.create_repository(name='Archived Repo',
                               hosting_account=self.account,
                               archived=True)

        self.client.login(username='admin', password='admin')
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['X-Total-Count'], '3')

        content = response.content
        self.assertIn(b'Visible Repo', content)
        self.assertIn(b'Hidden Repo', content)
        self.assertIn(b'Archived Repo', content)

    def test_get_empty(self) -> None:
        """Testing ConnectedServiceRepositoriesView GET with no matching
        repositories renders the empty state
        """
        self.client.login(username='admin', password='admin')
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['X-Total-Count'], '0')
        self.assertIn(b'No repositories match', response.content)

    def test_get_with_unregistered_service(self) -> None:
        """Testing ConnectedServiceRepositoriesView GET with a service that
        is not registered
        """
        self.client.login(username='admin', password='admin')
        response = self.client.get(
            reverse('connected-services-repositories',
                    kwargs={'service_id': 'not-a-real-service'}))

        self.assertEqual(response.status_code, 404)

    def test_get_requires_staff(self) -> None:
        """Testing ConnectedServiceRepositoriesView GET requires a staff
        member
        """
        self.client.login(username='doc', password='doc')
        response = self.client.get(self.url)

        # Non-staff users are redirected to the admin login.
        self.assertEqual(response.status_code, 302)

    def test_get_with_anonymous(self) -> None:
        """Testing ConnectedServiceRepositoriesView GET with an anonymous
        user
        """
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)
