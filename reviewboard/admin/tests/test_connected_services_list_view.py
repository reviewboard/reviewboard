"""Unit tests for reviewboard.admin.views.ConnectedServicesListView."""

from __future__ import annotations

import json
import re

from django.urls import reverse

from reviewboard.admin.views import ConnectedServiceRepositoriesView
from reviewboard.hostingsvcs.models import (
    ConfiguredBugTracker,
    HostingServiceAccount,
)
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

    def test_get_renders_repositories_per_page(self) -> None:
        """Testing ConnectedServicesListView GET passes the repositories page
        size to the client
        """
        self.client.login(username='admin', password='admin')
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

        # The client sizes its search and paginator controls from this, so it
        # must be the page size the repositories endpoint actually uses.
        per_page = ConnectedServiceRepositoriesView.repositories_per_page
        self.assertEqual(response.context['repositories_per_page'], per_page)
        self.assertIn(f'repositoriesPerPage: {per_page},'.encode('utf-8'),
                      response.content)

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

        # An account with no connected repositories does not show the
        # repositories row.
        self.assertNotIn(b'connected repositor', response.content)

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
        self.assertIn(b'2 connected repositories', response.content)

    def test_get_repositories_disclosure_is_an_accessible_button(self) -> None:
        """Testing ConnectedServicesListView GET renders the repositories
        disclosure as a button wired to the panel it controls
        """
        account = HostingServiceAccount.objects.create(
            service_name='github',
            username='user1',
            visible=True)
        self.create_repository(name='Test Repo',
                               hosting_account=account)

        self.client.login(username='admin', password='admin')
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

        content = response.content.decode('utf-8')

        # The disclosure must be a real button, so it's reachable and
        # operable by keyboard without any scripted key handling.
        m = re.search(
            r'<button class="rb-c-admin-cs-service-items__header"'
            r'\s+type="button"'
            r'\s+aria-expanded="false"'
            r'\s+aria-controls="(?P<panel_id>[^"]+)">',
            content)
        self.assertIsNotNone(m)
        assert m is not None

        # aria-controls has to name the panel that actually gets shown, or
        # assistive tech is pointed at nothing.
        panel_m = re.search(
            r'<div class="rb-c-admin-cs-service-items__panel"\s+'
            r'id="(?P<panel_id>[^"]+)"',
            content)
        self.assertIsNotNone(panel_m)
        assert panel_m is not None

        self.assertEqual(m.group('panel_id'), panel_m.group('panel_id'))

    def test_get_repository_count_totals_across_accounts(self) -> None:
        """Testing ConnectedServicesListView GET totals the repository count
        across all accounts for a service
        """
        account1 = HostingServiceAccount.objects.create(
            service_name='github',
            username='user1',
            visible=True)
        account2 = HostingServiceAccount.objects.create(
            service_name='github',
            username='user2',
            visible=True)
        self.create_repository(name='Test Repo 1',
                               hosting_account=account1)
        self.create_repository(name='Test Repo 2',
                               hosting_account=account2)
        self.create_repository(name='Test Repo 3',
                               hosting_account=account2)

        self.client.login(username='admin', password='admin')
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

        # The single card shows the service-wide total, not a per-account
        # count.
        self.assertIn(b'3 connected repositories', response.content)

    def test_get_filter_accounts_covers_every_listed_repository(self) -> None:
        """Testing ConnectedServicesListView GET offers a filter option for
        every account contributing repositories, including invisible ones
        """
        visible_account = HostingServiceAccount.objects.create(
            service_name='github',
            username='visible-user',
            visible=True)
        invisible_account = HostingServiceAccount.objects.create(
            service_name='github',
            username='invisible-user',
            visible=False)
        empty_account = HostingServiceAccount.objects.create(
            service_name='github',
            username='empty-user',
            visible=True)
        self.create_repository(name='Visible Repo',
                               hosting_account=visible_account)
        self.create_repository(name='Invisible Repo',
                               hosting_account=invisible_account)

        self.client.login(username='admin', password='admin')
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

        content = response.content

        # The repository list spans all accounts, so every account owning
        # repositories must be filterable. Leaving one out would show rows
        # that no filter option could narrow down to.
        for account in (visible_account, invisible_account):
            self.assertIn(
                json.dumps({
                    'id': account.pk,
                    'label': f'{account.username} (PAT)',
                }, sort_keys=True).encode('utf-8'),
                content)

        # An account with no repositories contributes no rows, so it is not
        # worth offering as a filter.
        self.assertNotIn(f'"id": {empty_account.pk},'.encode('utf-8'),
                         content)

    def test_get_marks_pat_account_sharing_username(self) -> None:
        """Testing ConnectedServicesListView GET marks a PAT account with
        "(PAT)" in the filter dropdown when it shares a username with an app
        installation
        """
        pat_account = HostingServiceAccount.objects.create(
            service_name='github',
            username='example',
            visible=True)
        install_account = HostingServiceAccount.objects.create(
            service_name='github',
            username='example',
            visible=True,
            data={
                'github_app': {
                    'app_account_id': 1,
                    'installation_id': 42,
                    'owner_login': 'example',
                    'owner_type': 'organization',
                    'role': 'installation',
                },
            })
        self.create_repository(name='Repo A',
                               hosting_account=pat_account)
        self.create_repository(name='Repo B',
                               hosting_account=install_account)

        self.client.login(username='admin', password='admin')
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

        # The filter dropdown JSON tags the PAT account so it can be told
        # apart from the app installation with the same username, which is
        # left untagged.
        self.assertIn(json.dumps({
            'id': pat_account.pk,
            'label': 'example (PAT)',
        }, sort_keys=True).encode('utf-8'), response.content)
        self.assertIn(json.dumps({
            'id': install_account.pk,
            'label': 'example',
        }, sort_keys=True).encode('utf-8'), response.content)

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
        self.assertNotIn(b'edit-credentials', response.content)

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


class ConnectedServicesListViewBugTrackerTests(TestCase):
    """Unit tests for bug trackers in ConnectedServicesListView.

    Version Added:
        9.0
    """

    fixtures = ['test_users']

    @classmethod
    def setUpClass(cls) -> None:
        """Set up the test case class."""
        super().setUpClass()

        cls.url = reverse('connected-services-list')

    def setUp(self) -> None:
        """Set up the test case."""
        super().setUp()

        self.client.login(username='admin', password='admin')

    def test_get_lists_bug_trackers(self) -> None:
        """Testing ConnectedServicesListView GET lists bug tracker
        configurations, including for services with no accounts
        """
        ConfiguredBugTracker.objects.create(
            name='My Splat Tracker',
            service_name='splat',
            settings={'splat_org_name': 'my-org'})
        ConfiguredBugTracker.objects.create(
            name='My Disabled Tracker',
            service_name='splat',
            enabled=False,
            settings={'splat_org_name': 'other-org'})

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['service_entries']), 1)

        # The configurations are behind a disclosure whose content is
        # fetched from the bug trackers endpoint.
        self.assertIn(b'2 bug trackers', response.content)
        self.assertIn(b'data-item-type="bug-trackers"', response.content)
        self.assertIn(b'data-item-count="2"', response.content)

        # There are no accounts, so the accounts list is omitted
        # entirely rather than rendering as an empty block.
        self.assertNotIn(b'rb-c-admin-cs-accounts', response.content)

    def test_get_never_lists_in_repo_configs(self) -> None:
        """Testing ConnectedServicesListView GET never lists bug tracker
        configurations for in-repo services
        """
        HostingServiceAccount.objects.create(
            service_name='gitlab',
            username='user1',
            visible=True)

        # Such rows come from migrating repositories that used another
        # hosting service's bug tracker.
        ConfiguredBugTracker.objects.create(
            name='GitLab Issues',
            service_name='gitlab',
            settings={})

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

        # The account renders, but the tracker is managed through the
        # repository configuration, not here.
        self.assertIn(b'user1', response.content)
        self.assertNotIn(b'GitLab Issues', response.content)

    def test_get_never_lists_sentinel(self) -> None:
        """Testing ConnectedServicesListView GET never lists the sentinel
        bug tracker
        """
        ConfiguredBugTracker.objects.get_sentinel()

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['service_entries']), 0)
        self.assertNotIn(b'Unattributed Bugs', response.content)
