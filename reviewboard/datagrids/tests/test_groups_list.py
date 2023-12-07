"""Unit tests for the groups page.

Version Added:
    5.0.7
"""

from __future__ import annotations

from typing import Optional, Sequence, TYPE_CHECKING

from django.contrib.auth.models import User
from django.db.models import Count, Q
from djblets.testing.decorators import add_fixtures

from reviewboard.accounts.models import Profile
from reviewboard.datagrids.tests.base import BaseViewTestCase
from reviewboard.reviews.models import Group, ReviewRequest
from reviewboard.reviews.testing.queries.review_groups import (
    get_review_groups_accessible_prep_equeries,
    get_review_groups_accessible_q,
)
from reviewboard.site.models import LocalSite
from reviewboard.testing.queries.http import get_http_request_start_equeries

if TYPE_CHECKING:
    from djblets.db.query_comparator import ExpectedQueries


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

        review_groups = [
            self.create_review_group(local_site=local_site,
                                     name='group-%02d' % (i + 1))
            for i in range(10)
        ]

        self._prefetch_cached()

        equeries = self._build_datagrid_equeries(
            user=user,
            profile=profile,
            local_site=local_site,
            local_sites_in_db=local_sites_in_db,
            review_groups=review_groups)

        with self.assertQueries(equeries, check_subqueries=True):
            response = self.client.get(
                self.get_datagrid_url(local_site=local_site))

        self.assertEqual(response.status_code, 200)

        datagrid = self._get_context_var(response, 'datagrid')
        assert datagrid is not None
        self.assertEqual(
            [
                row['object']
                for row in datagrid.rows
            ],
            review_groups)

    def _build_datagrid_equeries(
        self,
        *,
        user: User,
        profile: Profile,
        local_site: Optional[LocalSite] = None,
        local_sites_in_db: bool = False,
        review_groups: Sequence[Group],
    ) -> ExpectedQueries:
        """Return expected queries for viewing the datagrid.

        This assumes that the user has access to the datagrid, and that any
        cacheable state is already cached.

        Version Added:
            5.0.7

        Args:
            user (django.contrib.auth.models.User):
                The user accessing the datagrid.

            profile (reviewboard.accounts.models.Profile):
                The user's profile.

            local_site (reviewboard.site.models.LocalSite, optional):
                The Local Site that's being accessed, if any.

            local_sites_in_db (bool, optional):
                Whether the database contains any Local Sites.

            review_groups (list of reviewboard.reviews.models.group.Group):
                The list of review groups that should be returned in the
                results, in display order.

        Returns:
            list of dict:
            The list of expected queries.
        """
        review_group_pks = [
            _group.pk
            for _group in review_groups
        ]

        if local_site is not None:
            row_data_select_related = {
                'local_site',
            }
        else:
            row_data_select_related = set()

        rows_q_result = get_review_groups_accessible_q(
            user=user,
            local_site=local_site)
        rows_q = rows_q_result['q']
        rows_q_tables = rows_q_result['tables']
        rows_q_num_joins = len(rows_q_tables) - 1

        equeries = get_http_request_start_equeries(
            user=user,
            local_site=local_site)
        equeries += get_review_groups_accessible_prep_equeries(
            user=user,
            local_site=local_site,
            needs_local_site_profile_query=True)
        equeries += [
            {
                '__note__': 'Update datagrid state on the user profile',
                'model': Profile,
                'type': 'UPDATE',
                'where': Q(pk=profile.pk),
            },
            {
                '__note__': (
                    'Fetch the number of items across all datagrid pages'
                ),
                'annotations': {'__count': Count('*')},
                'model': Group,

                'subqueries': [
                    {
                        'distinct': True,
                        'model': Group,
                        'num_joins': rows_q_num_joins,
                        'subquery': True,
                        'tables': rows_q_tables,
                        'where': rows_q,
                    },
                ],
            },
            {
                '__note__': 'Fetch the IDs of the items for one page',
                'distinct': True,
                'limit': 10,
                'model': Group,
                'num_joins': rows_q_num_joins,
                'order_by': ('name',),
                'tables': rows_q_tables,
                'values_select': ('pk',),
                'where': rows_q,
            },
            {
                '__note__': (
                    "Fetch the IDs of the page's groups that are starred."
                ),
                'model': Group,
                'num_joins': 1,
                'tables': {
                    'accounts_profile_starred_groups',
                    'reviews_group',
                },
                'values_select': ('pk',),
                'where': (Q(starred_by__id=profile.pk) &
                          Q(pk__in=review_group_pks)),
            },
            {
                '__note__': (
                    'Fetch the data for one page based on the IDs.'
                ),
                'annotations': {
                    'column_pending_review_request_count': Count(
                        'review_requests',
                        filter=(Q(review_requests__public=True) &
                                Q(review_requests__status='P'))),
                },
                'group_by': True,
                'model': Group,
                'num_joins': 2,
                'select_related': row_data_select_related,
                'tables': {
                    'reviews_group',
                    'reviews_reviewrequest',
                    'reviews_reviewrequest_target_groups',
                },
                'where': Q(pk__in=review_group_pks),
            },
        ]

        return equeries
