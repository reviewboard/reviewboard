"""Unit tests for the groups page.

Version Added:
    5.0.7
"""

from __future__ import annotations

from typing import Optional

from django.contrib.auth.models import Permission, User
from django.db.models import Count, Q
from djblets.testing.decorators import add_fixtures

from reviewboard.accounts.models import LocalSiteProfile, Profile
from reviewboard.datagrids.tests.base import BaseViewTestCase
from reviewboard.reviews.models import Group, ReviewRequest
from reviewboard.site.models import LocalSite


class GroupListViewTests(BaseViewTestCase):
    """Unit tests for the group_list view."""

    datagrid_url = '/groups/'

    @add_fixtures(['test_users'])
    def test_with_access(self):
        """Testing group_list view"""
        self._test_with_access()

    @add_fixtures(['test_site', 'test_users'])
    def test_with_access_with_local_site(self):
        """Testing group_list view on a Local Site"""
        self._test_with_access(with_local_site=True,
                               local_sites_in_db=True)

    @add_fixtures(['test_site', 'test_users'])
    def test_with_access_with_local_sites_in_db(self):
        """Testing group_list view with Local Sites in the database"""
        self._test_with_access(local_sites_in_db=True)

    @add_fixtures(['test_users'])
    def test_as_anonymous_and_redirect(self):
        """Testing group_list view with site-wide login enabled"""
        with self.siteconfig_settings({'auth_require_sitewide_login': True},
                                      reload_settings=False):
            response = self.client.get('/groups/')

        self.assertEqual(response.status_code, 302)

    def _test_with_access(
        self,
        *,
        with_local_site: bool = False,
        local_sites_in_db: bool = False,
    ) -> None:
        """Common tests for a user with access to the datagrid.

        This accesses the groups datagrid as a logged-in user with access
        to the global site or Local Site (depending on the test), checking
        queries and datagrid row results.

        Args:
            with_local_site (bool, optional):
                Whether to test with a Local Site for the query and objects.

            local_sites_in_db (bool, optional):
                Whether to expect Local Sites in the database.

        Raises:
            AssertionError:
                One of the checks failed.
        """
        local_site: Optional[LocalSite]

        if with_local_site:
            local_site = self.get_local_site(name=self.local_site_name)
        else:
            local_site = None

        self.client.login(username='doc', password='doc')
        user = User.objects.get(username='doc')
        profile = user.get_profile()

        for i in range(10):
            self.create_review_group(
                local_site=local_site,
                name='group-%02d' % (i + 1))

        self._prefetch_cached()

        queries = [
            {
                'model': User,
                'where': Q(pk=user.pk),
            },
            {
                'model': Profile,
                'where': Q(user=user),
            },
        ]

        if local_site:
            queries += [
                {
                    'model': LocalSite,
                    'tables': {
                        'site_localsite',
                    },
                    'where': Q(name=local_site.name),
                },
                {
                    'extra': {
                        'a': ('1', []),
                    },
                    'limit': 1,
                    'model': User,
                    'num_joins': 1,
                    'tables': {
                        'auth_user',
                        'site_localsite_users',
                    },
                    'where': (Q(local_site__id=local_site.pk) &
                              Q(pk=user.pk)),
                },
            ]

        queries += [
            {
                'model': Permission,
                'num_joins': 2,
                'tables': {
                    'auth_permission',
                    'auth_user_user_permissions',
                    'django_content_type',
                },
                'values_select': ('content_type__app_label', 'codename'),
                'where': Q(user__id=user.pk),
            },
            {
                'model': Permission,
                'num_joins': 4,
                'tables': {
                    'auth_group',
                    'auth_group_permissions',
                    'auth_permission',
                    'auth_user_groups',
                    'django_content_type',
                },
                'values_select': ('content_type__app_label', 'codename'),
                'where': Q(group__user=user),
            },
        ]

        if local_site:
            queries += [
                {
                    'extra': {
                        'a': ('1', []),
                    },
                    'limit': 1,
                    'model': User,
                    'num_joins': 1,
                    'tables': {
                        'site_localsite_admins',
                        'auth_user',
                    },
                    'where': (Q(local_site_admins__id=local_site.pk) &
                              Q(pk=user.pk)),
                },
                {
                    'model': LocalSiteProfile,
                    'where': (Q(local_site=local_site) &
                              Q(profile=profile) &
                              Q(user=user)),
                },
            ]

        queries += [
            {
                'model': Profile,
                'type': 'UPDATE',
                'where': Q(pk=profile.pk),
            },

            # Fetch the number of items across all datagrid pages.
            {
                'annotations': {'__count': Count('*')},
                'inner_query': {
                    'distinct': True,
                    'model': Group,
                    'num_joins': 1,
                    'subquery': True,
                    'tables': {
                        'reviews_group',
                        'reviews_group_users',
                    },
                    'where': (((Q(invite_only=False) &
                                Q(visible=True)) |
                               Q(users=user.pk)) &
                              Q(local_site=local_site)),
                },
                'model': Group,
            },

            # Fetch the IDs of the items for one page.
            {
                'distinct': True,
                'limit': 10,
                'model': Group,
                'num_joins': 1,
                'order_by': ('name',),
                'tables': {
                    'reviews_group',
                    'reviews_group_users',
                },
                'values_select': ('pk',),
                'where': (((Q(invite_only=False) &
                            Q(visible=True)) |
                           Q(users=user.pk)) &
                          Q(local_site=local_site)),
            },

            # Fetch the IDs of the page's groups that are starred.
            {
                'model': Group,
                'num_joins': 1,
                'tables': {
                    'accounts_profile_starred_groups',
                    'reviews_group',
                },
                'values_select': ('pk',),
                'where': (Q(starred_by__id=profile.pk) &
                          Q(pk__in=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10])),
            },

            # Fetch the data for one page based on the IDs.
            {
                'model': Group,
                'where': Q(pk__in=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]),
            },
        ]

        # NOTE: This represents a performance bug due to a bad query.
        #       It's being tracked and will be resolved in a future
        #       change.
        for i in range(10):
            if local_site:
                queries += [
                    {
                        'model': LocalSite,
                        'tables': {
                            'site_localsite',
                        },
                        'where': Q(id=local_site.pk)
                    }
                ]

            queries += [
                {
                    'annotations': {'__count': Count('*')},
                    'model': ReviewRequest,
                    'num_joins': 1,
                    'tables': {
                        'reviews_reviewrequest',
                        'reviews_reviewrequest_target_groups',
                    },
                    'where': (Q(target_groups__id=i + 1) &
                              Q(public=True) &
                              Q(status='P')),
                },
            ]

        with self.assertQueries(queries, check_subqueries=True):
            response = self.client.get(
                self.get_datagrid_url(local_site=local_site))

        self.assertEqual(response.status_code, 200)

        datagrid = self._get_context_var(response, 'datagrid')
        assert datagrid is not None
        self.assertEqual(len(datagrid.rows), 10)
        self.assertEqual(datagrid.rows[0]['object'].name, 'group-01')
        self.assertEqual(datagrid.rows[1]['object'].name, 'group-02')
        self.assertEqual(datagrid.rows[2]['object'].name, 'group-03')
        self.assertEqual(datagrid.rows[3]['object'].name, 'group-04')
        self.assertEqual(datagrid.rows[4]['object'].name, 'group-05')
        self.assertEqual(datagrid.rows[5]['object'].name, 'group-06')
        self.assertEqual(datagrid.rows[6]['object'].name, 'group-07')
        self.assertEqual(datagrid.rows[7]['object'].name, 'group-08')
        self.assertEqual(datagrid.rows[8]['object'].name, 'group-09')
        self.assertEqual(datagrid.rows[9]['object'].name, 'group-10')
