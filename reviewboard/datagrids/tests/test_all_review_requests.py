"""Unit tests for the All Review Requests page.

Version Added:
    5.0.7
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, TYPE_CHECKING

from django.contrib.auth.models import User
from django.db.models import Count, Q
from djblets.testing.decorators import add_fixtures

from reviewboard.accounts.models import Profile
from reviewboard.datagrids.tests.base import BaseViewTestCase
from reviewboard.reviews.models import ReviewRequest
from reviewboard.reviews.testing.queries.review_requests import \
    get_review_requests_accessible_q
from reviewboard.site.models import LocalSite
from reviewboard.testing.queries.http import get_http_request_start_equeries

if TYPE_CHECKING:
    from djblets.db.query_comparator import ExpectedQueries


class AllReviewRequestViewTests(BaseViewTestCase):
    """Unit tests for the all_review_requests view."""

    datagrid_url = '/r/'

    @add_fixtures(['test_users'])
    def test_with_access(self):
        """Testing all_review_requests view"""
        self._test_with_access()

    @add_fixtures(['test_site', 'test_users'])
    def test_with_access_with_local_site(self):
        """Testing all_review_requests view on a Local Site"""
        self._test_with_access(with_local_site=True,
                               local_sites_in_db=True)

    @add_fixtures(['test_site', 'test_users'])
    def test_with_access_with_local_sites_in_db(self):
        """Testing all_review_requests view with Local Sites in the database
        """
        self._test_with_access(local_sites_in_db=True)

    def test_as_anonymous_and_redirect(self):
        """Testing all_review_requests view as anonymous user
        with anonymous access disabled
        """
        with self.siteconfig_settings({'auth_require_sitewide_login': True},
                                      reload_settings=False):
            response = self.client.get('/r/')

        self.assertEqual(response.status_code, 302)

    @add_fixtures(['test_scmtools', 'test_users'])
    def test_with_private_review_requests(self):
        """Testing all_review_requests view with private review requests"""
        self._test_with_private_review_requests()

    @add_fixtures(['test_site', 'test_scmtools', 'test_users'])
    def test_with_private_review_requests_with_local_site(self):
        """Testing all_review_requests view with private review requests on
        a Local Site
        """
        self._test_with_private_review_requests(with_local_site=True,
                                                local_sites_in_db=True)

    @add_fixtures(['test_site', 'test_scmtools', 'test_users'])
    def test_with_private_review_requests_with_local_sites_in_db(self):
        """Testing all_review_requests view with private review requests with
        Local Sites in the database
        """
        self._test_with_private_review_requests(local_sites_in_db=True)

    @add_fixtures(['test_users'])
    def test_with_inactive_users(self):
        """Testing all_review_requests view with review requests from inactive
        users
        """
        self._test_with_inactive_users()

    @add_fixtures(['test_site', 'test_users'])
    def test_with_inactive_users_with_local_site(self):
        """Testing all_review_requests view with review requests from inactive
        users on a Local Site
        """
        self._test_with_inactive_users(with_local_site=True,
                                       local_sites_in_db=True)

    @add_fixtures(['test_site', 'test_users'])
    def test_with_inactive_users_with_local_sites_in_db(self):
        """Testing all_review_requests view with review requests from inactive
        users with Local Sites in the database
        """
        self._test_with_inactive_users(local_sites_in_db=True)

    def _test_with_access(
        self,
        *,
        with_local_site: bool = False,
        local_sites_in_db: bool = False,
    ) -> None:
        """Common tests for a user with access to the datagrid.

        This accesses the All Review Requests datagrid as a logged-in user with
        access to the global site or Local Site (depending on the test),
        checking queries and datagrid row results.

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

        review_request_1 = self.create_review_request(
            local_site=local_site,
            local_id=1,
            summary='Test 1',
            publish=True)
        review_request_2 = self.create_review_request(
            local_site=local_site,
            local_id=2,
            summary='Test 2',
            publish=True)
        review_request_3 = self.create_review_request(
            local_site=local_site,
            local_id=3,
            summary='Test 3',
            publish=True)

        self.client.login(username='grumpy', password='grumpy')
        user = User.objects.get(username='grumpy')
        profile = user.get_profile()

        if local_site:
            local_site.users.add(user)

        self._prefetch_cached(local_site=local_site)

        equeries = self._build_datagrid_equeries(
            user=user,
            profile=profile,
            local_site=local_site,
            local_sites_in_db=local_sites_in_db,
            review_request_pks=[
                review_request_3.pk,
                review_request_2.pk,
                review_request_1.pk,
            ])

        with self.assertQueries(equeries):
            response = self.client.get(
                self.get_datagrid_url(local_site=local_site))

        self.assertEqual(response.status_code, 200)

        datagrid = self._get_context_var(response, 'datagrid')
        assert datagrid is not None
        self.assertEqual(len(datagrid.rows), 3)
        self.assertEqual(datagrid.rows[0]['object'].summary, 'Test 3')
        self.assertEqual(datagrid.rows[1]['object'].summary, 'Test 2')
        self.assertEqual(datagrid.rows[2]['object'].summary, 'Test 1')

    def _test_with_private_review_requests(
        self,
        *,
        with_local_site: bool = False,
        local_sites_in_db: bool = False,
    ) -> None:
        """Common tests for checking access to private review requests.

        This accesses the All Review Requests datagrid as a logged-in user with
        access to the global site or Local Site (depending on the test),
        checking queries and datagrid row results to make sure only accessible
        private review requests are included.

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

        user = User.objects.get(username='grumpy')
        profile = user.get_profile()

        if local_site:
            local_site.users.add(user)

        # These are public
        review_request_1 = self.create_review_request(
            local_site=local_site,
            local_id=1,
            summary='Test 1',
            publish=True)
        review_request_2 = self.create_review_request(
            local_site=local_site,
            local_id=2,
            summary='Test 2',
            publish=True)

        repository1 = self.create_repository(
            local_site=local_site,
            name='repo1',
            public=False,
            users=[user])
        review_request_3 = self.create_review_request(
            local_site=local_site,
            local_id=3,
            summary='Test 3',
            repository=repository1,
            publish=True)

        group1 = self.create_review_group(
            local_site=local_site,
            name='group1',
            invite_only=True,
            users=[user])
        review_request_4 = self.create_review_request(
            local_site=local_site,
            local_id=4,
            summary='Test 4',
            publish=True,
            target_groups=[group1])

        # These are private
        repository2 = self.create_repository(
            local_site=local_site,
            name='group2',
            public=False)
        self.create_review_request(
            local_site=local_site,
            local_id=5,
            summary='Test 5',
            repository=repository2,
            publish=True)

        group2 = self.create_review_group(
            local_site=local_site,
            name='group2',
            invite_only=True)
        self.create_review_request(
            local_site=local_site,
            local_id=6,
            summary='Test 6',
            publish=True,
            target_groups=[group2])

        # Log in and check what we get.
        self.client.login(username='grumpy', password='grumpy')

        self._prefetch_cached(local_site=local_site)

        equeries = self._build_datagrid_equeries(
            user=user,
            profile=profile,
            local_site=local_site,
            local_sites_in_db=local_sites_in_db,
            review_request_pks=[
                review_request_4.pk,
                review_request_3.pk,
                review_request_2.pk,
                review_request_1.pk,
            ],
            repositories_pks=[repository1.pk],
            target_groups_pks=[group1.pk])

        with self.assertQueries(equeries):
            response = self.client.get(
                self.get_datagrid_url(local_site=local_site))

        self.assertEqual(response.status_code, 200)

        datagrid = self._get_context_var(response, 'datagrid')
        assert datagrid is not None
        self.assertEqual(len(datagrid.rows), 4)
        self.assertEqual(datagrid.rows[0]['object'].summary, 'Test 4')
        self.assertEqual(datagrid.rows[1]['object'].summary, 'Test 3')
        self.assertEqual(datagrid.rows[2]['object'].summary, 'Test 2')
        self.assertEqual(datagrid.rows[3]['object'].summary, 'Test 1')

    def _test_with_inactive_users(
        self,
        *,
        with_local_site: bool = False,
        local_sites_in_db: bool = False,
    ) -> None:
        """Common tests for checking for review requests from inactive users.

        This accesses the All Review Requests datagrid as a logged-in user with
        access to the global site or Local Site (depending on the test),
        checking queries and datagrid row results to make sure review requests
        from inactive users are included.

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

        User.objects.filter(username='doc').update(is_active=False)

        review_request_1 = self.create_review_request(
            local_site=local_site,
            local_id=1,
            summary='Test 1',
            submitter='doc',
            publish=True)
        review_request_1.close(ReviewRequest.SUBMITTED)

        review_request_2 = self.create_review_request(
            local_site=local_site,
            local_id=2,
            summary='Test 2',
            submitter='grumpy',
            publish=True)

        self.client.login(username='grumpy', password='grumpy')
        user = User.objects.get(username='grumpy')
        profile = user.get_profile()

        if local_site:
            local_site.users.add(user)

        self._prefetch_cached(local_site=local_site,
                              user=user)

        equeries = self._build_datagrid_equeries(
            user=user,
            profile=profile,
            local_site=local_site,
            local_sites_in_db=local_sites_in_db,
            review_request_pks=[
                review_request_2.pk,
                review_request_1.pk,
            ])

        with self.assertQueries(equeries):
            response = self.client.get(
                self.get_datagrid_url(local_site=local_site))

        self.assertEqual(response.status_code, 200)

        datagrid = self._get_context_var(response, 'datagrid')
        assert datagrid is not None
        self.assertEqual(len(datagrid.rows), 2)
        self.assertEqual(datagrid.rows[0]['object'].summary, 'Test 2')
        self.assertEqual(datagrid.rows[1]['object'].summary, 'Test 1')

    def _build_datagrid_equeries(
        self,
        *,
        user: User,
        profile: Profile,
        review_request_pks: List[int],
        local_site: Optional[LocalSite] = None,
        local_sites_in_db: bool = False,
        repositories_pks: List[int] = [],
        target_groups_pks: List[int] = [],
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

            review_request_pks (list of int):
                The list of review request IDs that are expected to be
                listed, in result order.

            local_site (reviewboard.site.models.LocalSite, optional):
                The Local Site that's being accessed, if any.

            local_sites_in_db (bool, optional):
                Whether the database contains any Local Sites.

            repositories_pks (list of int, optional):
                The list of any repository IDs that should be part of the
                query.

            target_groups_pks (list of int, optional):
                The list of any target group IDs that should be part of the
                query.

        Returns:
            list of dict:
            The list of expected queries.
        """
        user_pk = user.pk
        extra: Dict[str, Any] = {
            'new_review_count': (f"""
                SELECT COUNT(*)
                  FROM reviews_review, accounts_reviewrequestvisit
                  WHERE reviews_review.public
                    AND reviews_review.review_request_id =
                        reviews_reviewrequest.id
                    AND accounts_reviewrequestvisit.review_request_id =
                        reviews_reviewrequest.id
                    AND accounts_reviewrequestvisit.user_id = {user_pk}
                    AND reviews_review.timestamp >
                        accounts_reviewrequestvisit.timestamp
                    AND reviews_review.user_id != {user_pk}
            """, []),
            'draft_summary': ("""
                SELECT reviews_reviewrequestdraft.summary
                  FROM reviews_reviewrequestdraft
                  WHERE reviews_reviewrequestdraft.review_request_id =
                        reviews_reviewrequest.id
            """, []),
            'visibility': (f"""
                SELECT accounts_reviewrequestvisit.visibility
                  FROM accounts_reviewrequestvisit
                 WHERE accounts_reviewrequestvisit.review_request_id =
                       reviews_reviewrequest.id
                   AND accounts_reviewrequestvisit.user_id = {user_pk}
            """, []),
        }

        rows_q_result = get_review_requests_accessible_q(
            user=user,
            local_site=local_site,
            has_local_sites_in_db=local_sites_in_db,
            filter_private=True,
            show_inactive=True,
            status=None,
            accessible_repository_ids=repositories_pks,
            accessible_review_group_ids=target_groups_pks,
            needs_local_site_profile_query=True)
        rows_q = rows_q_result['q']
        rows_q_tables = rows_q_result['tables']
        rows_q_num_joins = len(rows_q_tables) - 1
        rows_q_join_types = rows_q_result.get('join_types', {})
        rows_q_subqueries = rows_q_result.get('subqueries', [])

        equeries = get_http_request_start_equeries(
            user=user,
            local_site=local_site)
        equeries += rows_q_result.get('prep_equeries', [])
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
                'join_types': rows_q_join_types,
                'model': ReviewRequest,
                'num_joins': rows_q_num_joins,
                'subqueries': rows_q_subqueries,
                'tables': rows_q_tables,
                'where': (Q(rows_q) &
                          Q(local_site=local_site)),
            },
            {
                '__note__': 'Fetch the IDs of the items for one page',
                'distinct': True,
                'extra': extra,
                'join_types': rows_q_join_types,
                'limit': len(review_request_pks),
                'model': ReviewRequest,
                'num_joins': rows_q_num_joins,
                'order_by': ('-last_updated',),
                'subqueries': rows_q_subqueries,
                'tables': rows_q_tables,
                'values_select': ('pk',),
                'where': (Q(rows_q) &
                          Q(local_site=local_site)),
            },
            {
                '__note__': (
                    "Fetch the IDs of the page's review requests that are "
                    "starred."
                ),
                'join_types': {
                    'accounts_profile_starred_review_requests': 'INNER JOIN',
                },
                'model': ReviewRequest,
                'num_joins': 1,
                'tables': {
                    'accounts_profile_starred_review_requests',
                    'reviews_reviewrequest',
                },
                'values_select': ('pk',),
                'where': (Q(starred_by__id=profile.pk) &
                          Q(pk__in=review_request_pks)),
            },
        ]

        if local_site is not None:
            equeries += [
                {
                    '__note__': (
                        'Fetch the data for one page based on the IDs on the '
                        'Local Site'
                    ),
                    'extra': extra,
                    'model': ReviewRequest,
                    'select_related': {
                        'local_site',
                        'submitter',
                    },
                    'where': Q(pk__in=review_request_pks),
                },
            ]
        else:
            equeries += [
                {
                    '__note__': 'Fetch the data for one page based on the IDs',
                    'extra': extra,
                    'model': ReviewRequest,
                    'select_related': {'submitter'},
                    'where': Q(pk__in=review_request_pks),
                },
            ]

        return equeries
