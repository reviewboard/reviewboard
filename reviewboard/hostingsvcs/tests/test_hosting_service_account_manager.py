"""Unit tests for reviewboard.hostingsvcs.managers."""

from django.db.models import Q

from reviewboard.hostingsvcs.models import HostingServiceAccount
from reviewboard.site.models import LocalSite
from reviewboard.testing import TestCase


class HostingServiceAccountManagerTests(TestCase):
    """Unit tests for HostingServiceAccountManager."""

    def test_accessible(self):
        """Testing HostingServiceAccountManager.accessible"""
        account1 = HostingServiceAccount.objects.create(
            service_name='github',
            username='user1',
            visible=True)
        account2 = HostingServiceAccount.objects.create(
            service_name='bitbucket',
            username='user2',
            visible=True)
        HostingServiceAccount.objects.create(
            service_name='gitlab',
            username='user3',
            visible=False)
        HostingServiceAccount.objects.create(
            service_name='gitlab',
            username='user4',
            visible=False)

        # Pre-fetch stats, so they don't interfere with query counts below.
        self.assertFalse(LocalSite.objects.has_local_sites())

        queries = [
            {
                'model': HostingServiceAccount,
                'where': Q(visible=True),
                'order_by': ('pk',),
            },
        ]

        with self.assertQueries(queries):
            self.assertQuerysetEqual(
                HostingServiceAccount.objects.accessible().order_by('pk'),
                [account1, account2])

    def test_accessible_with_visible_only_false(self):
        """Testing HostingServiceAccountManager.accessible with
        visible_only=False
        """
        account1 = HostingServiceAccount.objects.create(
            service_name='github',
            username='user1',
            visible=True)
        account2 = HostingServiceAccount.objects.create(
            service_name='bitbucket',
            username='user2',
            visible=True)
        account3 = HostingServiceAccount.objects.create(
            service_name='gitlab',
            username='user3',
            visible=False)
        account4 = HostingServiceAccount.objects.create(
            service_name='gitlab',
            username='user4',
            visible=False)

        # Pre-fetch stats, so they don't interfere with query counts below.
        self.assertFalse(LocalSite.objects.has_local_sites())

        queries = [
            {
                'model': HostingServiceAccount,
                'order_by': ('pk',),
            },
        ]

        with self.assertQueries(queries):
            self.assertQuerysetEqual(
                (
                    HostingServiceAccount.objects
                    .accessible(visible_only=False)
                    .order_by('pk')
                ),
                [account1, account2, account3, account4])

    def test_accessible_with_visible_with_local_site_in_db(self):
        """Testing HostingServiceAccountManager.accessible with LocalSites in
        database
        """
        local_site = self.create_local_site()

        account1 = HostingServiceAccount.objects.create(
            service_name='github',
            username='user1',
            visible=True)
        HostingServiceAccount.objects.create(
            service_name='bitbucket',
            username='user2',
            visible=True,
            local_site=local_site)
        HostingServiceAccount.objects.create(
            service_name='gitlab',
            username='user3',
            visible=False)
        HostingServiceAccount.objects.create(
            service_name='gitlab',
            username='user4',
            visible=False)

        # Pre-fetch stats, so they don't interfere with query counts below.
        self.assertTrue(LocalSite.objects.has_local_sites())

        queries = [
            {
                'model': HostingServiceAccount,
                'where': (Q(local_site=None) &
                          Q(visible=True)),
            },
        ]

        with self.assertQueries(queries):
            self.assertQuerysetEqual(
                HostingServiceAccount.objects.accessible(),
                [account1])

    def test_accessible_with_visible_with_local_site(self):
        """Testing HostingServiceAccountManager.accessible with local_site="""
        local_site = self.create_local_site()

        HostingServiceAccount.objects.create(
            service_name='github',
            username='user1',
            visible=True)
        account2 = HostingServiceAccount.objects.create(
            service_name='bitbucket',
            username='user2',
            visible=True,
            local_site=local_site)
        HostingServiceAccount.objects.create(
            service_name='gitlab',
            username='user3',
            visible=False)
        HostingServiceAccount.objects.create(
            service_name='gitlab',
            username='user4',
            visible=False,
            local_site=local_site)

        # Pre-fetch stats, so they don't interfere with query counts below.
        self.assertTrue(LocalSite.objects.has_local_sites())

        queries = [
            {
                'model': HostingServiceAccount,
                'where': (Q(local_site=local_site) &
                          Q(visible=True)),
                'order_by': ('pk',),
            },
        ]

        with self.assertQueries(queries):
            self.assertQuerysetEqual(
                (
                    HostingServiceAccount.objects
                    .accessible(local_site=local_site)
                    .order_by('pk')
                ),
                [account2])

    def test_accessible_with_visible_with_local_site_all(self):
        """Testing HostingServiceAccountManager.accessible with
        local_site=LocalSite.ALL
        """
        local_site = self.create_local_site()

        account1 = HostingServiceAccount.objects.create(
            service_name='github',
            username='user1',
            visible=True,
            local_site=local_site)
        account2 = HostingServiceAccount.objects.create(
            service_name='bitbucket',
            username='user2',
            visible=True,
            local_site=local_site)
        HostingServiceAccount.objects.create(
            service_name='gitlab',
            username='user3',
            visible=False)
        HostingServiceAccount.objects.create(
            service_name='gitlab',
            username='user4',
            visible=False,
            local_site=local_site)

        # Pre-fetch stats, so they don't interfere with query counts below.
        self.assertTrue(LocalSite.objects.has_local_sites())

        queries = [
            {
                'model': HostingServiceAccount,
                'where': Q(visible=True),
                'order_by': ('pk',),
            },
        ]

        with self.assertQueries(queries):
            self.assertQuerysetEqual(
                (
                    HostingServiceAccount.objects
                    .accessible(local_site=LocalSite.ALL)
                    .order_by('pk')
                ),
                [account1, account2])
