"""Unit tests for the user page.

Version Added:
    5.0.7
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, TYPE_CHECKING

from django.contrib.auth.models import User
from django.db.models import Count, Q
from django.urls import reverse
from djblets.testing.decorators import add_fixtures

from reviewboard.accounts.models import Profile
from reviewboard.accounts.testing.queries import get_user_profile_equeries
from reviewboard.datagrids.builtin_items import UserGroupsItem, UserProfileItem
from reviewboard.datagrids.tests.base import BaseViewTestCase
from reviewboard.reviews.models import Group, Review, ReviewRequest
from reviewboard.reviews.testing.queries.review_groups import \
    get_review_groups_accessible_q
from reviewboard.reviews.testing.queries.review_requests import \
    get_review_requests_from_user_q
from reviewboard.reviews.testing.queries.reviews import \
    get_reviews_from_user_q
from reviewboard.site.models import LocalSite
from reviewboard.testing.queries.http import get_http_request_start_equeries

if TYPE_CHECKING:
    from djblets.db.query_comparator import ExpectedQueries


class SubmitterViewTests(BaseViewTestCase):
    """Unit tests for the submitter view."""

    datagrid_url = '/users/grumpy/'

    @add_fixtures(['test_users'])
    def test_with_private_review_requests(self):
        """Testing submitter view with private review requests"""
        self._test_with_private_review_requests()

    @add_fixtures(['test_site', 'test_users'])
    def test_with_private_review_requests_with_local_site(self):
        """Testing submitter view with private review requests on a
        Local Site
        """
        self._test_with_private_review_requests(with_local_site=True,
                                                local_sites_in_db=True)

    @add_fixtures(['test_site', 'test_users'])
    def test_with_private_review_requests_with_local_sites_in_db(self):
        """Testing submitter view with private review requests with
        Local Sites in the database
        """
        self._test_with_private_review_requests(local_sites_in_db=True)

    @add_fixtures(['test_users'])
    def test_sidebar(self):
        """Testing submitter view sidebar"""
        self._test_sidebar()

    @add_fixtures(['test_site', 'test_users'])
    def test_sidebar_with_local_site(self):
        """Testing submitter view sidebar on a Local Site"""
        self._test_sidebar(with_local_site=True,
                           local_sites_in_db=True)

    @add_fixtures(['test_site', 'test_users'])
    def test_sidebar_with_local_sites_in_db(self):
        """Testing submitter view sidebar with Local Sites in the database"""
        self._test_sidebar(local_sites_in_db=True)

    def test_match_url_with_email_address(self):
        """Testing submitter view URL matching with e-mail address
        as username
        """
        # Test if this throws an exception. Bug #1250
        reverse('user', args=['user@example.com'])

    @add_fixtures(['test_users'])
    def test_with_private_reviews(self):
        """Testing reviews page of submitter view with private reviews"""
        self._test_with_private_reviews()

    @add_fixtures(['test_site', 'test_users'])
    def test_with_private_reviews_with_local_site(self):
        """Testing reviews page of submitter view with private reviews on a
        Local Site
        """
        self._test_with_private_reviews(with_local_site=True,
                                        local_sites_in_db=True)

    @add_fixtures(['test_site', 'test_users'])
    def test_with_private_reviews_with_local_sites_in_db(self):
        """Testing reviews page of submitter view with private reviews with
        Local Sites in the database
        """
        self._test_with_private_reviews(local_sites_in_db=True)

    def _test_with_private_review_requests(
        self,
        *,
        with_local_site: bool = False,
        local_sites_in_db: bool = False,
    ) -> None:
        """Common tests for checking access to private review requests.

        This accesses the User page's datagrid as a logged-in user with
        access to the global site or Local Site (depending on the test),
        checking queries and datagrid row results to make sure inaccessible
        private review requests are excluded.

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

        ReviewRequest.objects.all().delete()

        self.client.login(username='doc', password='doc')
        user = User.objects.get(username='doc')
        profile = user.get_profile()

        grumpy = User.objects.get(username='grumpy')
        grumpy.review_groups.clear()

        if local_site:
            local_site.users.add(grumpy)

        group1 = Group.objects.create(
            local_site=local_site,
            name='test-group-1')
        group1.users.add(grumpy)

        group2 = Group.objects.create(
            local_site=local_site,
            name='test-group-2',
            invite_only=True)
        group2.users.add(grumpy)

        review_requests: List[ReviewRequest] = []
        review_request_pks: List[int] = []

        for i in range(5):
            review_request = self.create_review_request(
                local_site=local_site,
                local_id=i + 1,
                summary='Summary %s' % (i + 1),
                submitter=grumpy,
                publish=True)

            review_requests.append(review_request)

            if i >= 3:
                review_request.target_groups.add(group2)
            else:
                review_request_pks.append(review_request.pk)

        # This will be ordered with newest at the top.
        review_request_pks.reverse()

        self._prefetch_cached(local_site=local_site)

        equeries = self._build_user_review_requests_datagrid_equeries(
            user=user,
            viewed_user=grumpy,
            profile=profile,
            local_site=local_site,
            local_sites_in_db=local_sites_in_db,
            review_request_pks=review_request_pks,
            accessible_review_group_ids=[group1.pk])

        with self.assertQueries(equeries):
            response = self.client.get(
                self.get_datagrid_url(local_site=local_site))

        self.assertEqual(response.status_code, 200)

        datagrid = self._get_context_var(response, 'datagrid')
        assert datagrid is not None
        self.assertEqual(len(datagrid.rows), 3)
        self.assertEqual(datagrid.rows[0]['object'].summary, 'Summary 3')
        self.assertEqual(datagrid.rows[1]['object'].summary, 'Summary 2')
        self.assertEqual(datagrid.rows[2]['object'].summary, 'Summary 1')

    def _test_sidebar(
        self,
        *,
        with_local_site: bool = False,
        local_sites_in_db: bool = False,
    ) -> None:
        """Common tests for checking access to private review requests.

        This accesses the User page's datagrid as a logged-in user with
        access to the global site or Local Site (depending on the test),
        checking queries and datagrid row results to make sure inaccessible
        private review requests are excluded.

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

        grumpy = User.objects.get(username='grumpy')
        grumpy.review_groups.clear()

        if local_site:
            local_site.users.add(grumpy)

        group1 = self.create_review_group(
            local_site=local_site,
            name='test-group-1')
        group1.users.add(grumpy)

        group2 = self.create_review_group(
            local_site=local_site,
            name='test-group-2',
            invite_only=True)
        group2.users.add(grumpy)

        self._prefetch_cached(local_site=local_site)

        equeries = self._build_user_review_requests_datagrid_equeries(
            user=user,
            viewed_user=grumpy,
            profile=profile,
            local_site=local_site,
            local_sites_in_db=local_sites_in_db,
            review_request_pks=[],
            accessible_review_group_ids=[group1.pk])

        # Now load the page and get the sidebar items.
        with self.assertQueries(equeries):
            response = self.client.get(
                self.get_datagrid_url(local_site=local_site))

        self.assertEqual(response.status_code, 200)

        datagrid = self._get_context_var(response, 'datagrid')
        assert datagrid is not None

        sidebar_items = datagrid.sidebar_items
        self.assertEqual(len(sidebar_items), 2)

        # Test the User Profile section.
        section = sidebar_items[0]
        self.assertIsInstance(section, UserProfileItem)

        # Test the Groups section.
        section = sidebar_items[1]
        self.assertIsInstance(section, UserGroupsItem)
        self.assertEqual(str(section.label), 'Groups')

        if local_site:
            # Due to a bug, we don't report groups for Local Sites.
            self.assertEqual(len(section.items), 0)
        else:
            self.assertEqual(len(section.items), 1)
            self.assertEqual(str(section.items[0].label),
                             'test-group-1')

    def _test_with_private_reviews(
        self,
        *,
        with_local_site: bool = False,
        local_sites_in_db: bool = False,
    ) -> None:
        """Common tests for checking access to private reviews.

        This accesses the User page's reviews datagrid as a logged-in user with
        access to the global site or Local Site (depending on the test),
        checking queries and datagrid row results to make sure inaccessible
        private reviews are excluded.

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

        ReviewRequest.objects.all().delete()
        Review.objects.all().delete()

        self.client.login(username='doc', password='doc')
        user = User.objects.get(username='doc')
        profile = user.get_profile()

        grumpy = User.objects.get(username='grumpy')
        dopey = User.objects.get(username='dopey')

        if local_site:
            local_site.users.add(dopey, grumpy)

        user.review_groups.clear()
        dopey.review_groups.clear()
        grumpy.review_groups.clear()

        group = Group.objects.create(
            local_site=local_site,
            name='test-group',
            invite_only=True)
        group.users.add(dopey, grumpy)

        review_request1 = self.create_review_request(
            local_site=local_site,
            local_id=1,
            summary='Summary 1',
            submitter=dopey,
            publish=True)
        review_request2 = self.create_review_request(
            local_site=local_site,
            local_id=2,
            summary='Summary 2',
            submitter=dopey,
            publish=True)
        review_request2.target_groups.add(group)

        reviews: List[Review] = []
        review_pks: List[int] = []

        for i in range(5):
            review = self.create_review(review_request1,
                                        user=grumpy,
                                        publish=True)
            reviews.append(review)
            review_pks.append(review.pk)

        reviews += [
            self.create_review(review_request2,
                               user=grumpy,
                               publish=True)
            for i in range(5)
        ]

        # This will be ordered with newest at the top.
        review_pks.reverse()

        self._prefetch_cached(local_site=local_site)

        equeries = self._build_user_reviews_datagrid_equeries(
            user=user,
            viewed_user=grumpy,
            profile=profile,
            local_site=local_site,
            local_sites_in_db=local_sites_in_db,
            review_pks=review_pks)

        with self.assertQueries(equeries):
            response = self.client.get(
                '%sreviews/' % self.get_datagrid_url(local_site=local_site))

        self.assertEqual(response.status_code, 200)

        datagrid = self._get_context_var(response, 'datagrid')
        assert datagrid is not None

        self.assertEqual(len(datagrid.rows), 5)
        self.assertEqual(datagrid.rows[0]['object'], reviews[4])
        self.assertEqual(datagrid.rows[1]['object'], reviews[3])
        self.assertEqual(datagrid.rows[2]['object'], reviews[2])
        self.assertEqual(datagrid.rows[3]['object'], reviews[1])
        self.assertEqual(datagrid.rows[4]['object'], reviews[0])

    def _build_user_review_requests_datagrid_equeries(
        self,
        *,
        user: User,
        viewed_user: User,
        review_request_pks: List[int],
        profile: Optional[Profile] = None,
        local_site: Optional[LocalSite] = None,
        local_sites_in_db: bool = False,
        accessible_review_group_ids: Sequence[int] = [],
    ) -> ExpectedQueries:
        """Return expected queries for viewing the user reviews datagrid.

        This assumes that the user has access to the datagrid, and that any
        cacheable state is already cached.

        Version Added:
            5.0.7

        Args:
            user (django.contrib.auth.models.User):
                The user accessing the datagrid.

            review_request_pks (list of int):
                The list of review request IDs that are expected to be listed,
                in result order.

            profile (reviewboard.accounts.models.Profile):
                The user's profile.

            local_site (reviewboard.site.models.LocalSite, optional):
                The Local Site that's being accessed, if any.

            local_sites_in_db (bool, optional):
                Whether the database contains any Local Sites.

            accessible_review_group_ids (list of int, optional):
                A list of accessible review group IDs that would be expected in
                the query.

        Returns:
            list of dict:
            The list of expected queries.
        """
        if local_sites_in_db:
            local_site_q = Q(local_site=local_site)
        else:
            local_site_q = Q()

        extra: Dict[str, Any] = {
            'new_review_count': ("""
                SELECT COUNT(*)
                  FROM reviews_review, accounts_reviewrequestvisit
                  WHERE reviews_review.public
                    AND reviews_review.review_request_id =
                        reviews_reviewrequest.id
                    AND accounts_reviewrequestvisit.review_request_id =
                        reviews_reviewrequest.id
                    AND accounts_reviewrequestvisit.user_id = 2
                    AND reviews_review.timestamp >
                        accounts_reviewrequestvisit.timestamp
                    AND reviews_review.user_id != 2
            """, []),
            'draft_summary': ("""
                SELECT reviews_reviewrequestdraft.summary
                  FROM reviews_reviewrequestdraft
                  WHERE reviews_reviewrequestdraft.review_request_id =
                        reviews_reviewrequest.id
            """, []),
            'visibility': ("""
                SELECT accounts_reviewrequestvisit.visibility
                  FROM accounts_reviewrequestvisit
                 WHERE accounts_reviewrequestvisit.review_request_id =
                       reviews_reviewrequest.id
                   AND accounts_reviewrequestvisit.user_id = 2
            """, []),
        }

        groups_q_result = get_review_groups_accessible_q(
            user=user,
            local_site=None,
            needs_user_permission_queries=False)
        groups_q = groups_q_result['q']
        groups_q_tables = groups_q_result['tables']
        groups_q_num_joins = len(groups_q_tables) - 1
        groups_q_join_types = groups_q_result.get('join_types', {})

        rows_q_result = get_review_requests_from_user_q(
            user=user,
            from_user=viewed_user.username,
            local_site=local_site,
            has_local_sites_in_db=local_sites_in_db,
            filter_private=True,
            show_inactive=True,
            status=None,
            accessible_review_group_ids=accessible_review_group_ids,
            needs_local_site_profile_query=True)
        rows_q = rows_q_result['q']
        rows_q_tables = rows_q_result['tables']
        rows_q_num_joins = len(rows_q_tables) - 1
        rows_q_join_types = rows_q_result.get('join_types', {})
        rows_q_subqueries = rows_q_result.get('subqueries', [])

        equeries = get_http_request_start_equeries(
            user=user,
            local_site=local_site)

        if local_site:
            equeries += [
                {
                    '__note__': 'Fetch the viewed user on the Local Site',
                    'join_types': {
                        'site_localsite_users': 'INNER JOIN',
                    },
                    'model': User,
                    'num_joins': 1,
                    'tables': {
                        'auth_user',
                        'site_localsite_users',
                    },
                    'where': (Q(local_site__id=local_site.pk) &
                              Q(username=viewed_user.username)),
                },
            ]
        else:
            equeries += [
                {
                    '__note__': 'Fetch the viewed user',
                    'model': User,
                    'where': Q(username=viewed_user.username),
                },
            ]

        equeries += rows_q_result.get('prep_equeries', [])
        equeries += groups_q_result.get('prep_equeries', [])
        equeries += [
            {
                # TODO: Remove the redundant local_site Q in the
                #       implementation.
                '__note__': (
                    "Fetch the list of the viewed user's review groups"
                ),
                'distinct': True,
                'join_types': groups_q_join_types,
                'model': Group,
                'num_joins': groups_q_num_joins,
                'only_fields': {
                    'id',
                    'local_site',
                    'name',
                },
                'tables': groups_q_tables,
                'where': (Q(users__id=viewed_user.pk) &
                          Q(groups_q) &
                          local_site_q),
            },
            {
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
        ]

        if review_request_pks:
            equeries += [
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
                        "Fetch the IDs of the page's review requests that "
                        "are starred."
                    ),
                    'join_types': {
                        'accounts_profile_starred_review_requests':
                            'INNER JOIN',
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

            if local_site:
                equeries += [
                    {
                        '__note__': (
                            'Fetch the data for one page based on the IDs '
                            'on the Local Site'
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
                        '__note__': (
                            'Fetch the data for one page based on the IDs'
                        ),
                        'extra': extra,
                        'model': ReviewRequest,
                        'select_related': {'submitter'},
                        'where': Q(pk__in=review_request_pks),
                    },
                ]

        equeries += get_user_profile_equeries(user=viewed_user)

        return equeries

    def _build_user_reviews_datagrid_equeries(
        self,
        *,
        user: User,
        viewed_user: User,
        review_pks: List[int],
        profile: Optional[Profile] = None,
        local_site: Optional[LocalSite] = None,
        local_sites_in_db: bool = False,
    ) -> ExpectedQueries:
        """Return expected queries for viewing the user reviews datagrid.

        This assumes that the user has access to the datagrid, and that any
        cacheable state is already cached.

        Version Added:
            5.0.7

        Args:
            user (django.contrib.auth.models.User):
                The user accessing the datagrid.

            viewed_user (django.contrib.auth.models.User):
                The user viewing the datagrid.

            review_pks (list of int):
                The list of review IDs that are expected to be listed, in
                result order.

            profile (reviewboard.accounts.models.Profile):
                The user's profile.

            local_site (reviewboard.site.models.LocalSite, optional):
                The Local Site that's being accessed, if any.

            local_sites_in_db (bool, optional):
                Whether the database contains any Local Sites.

        Returns:
            list of dict:
            The list of expected queries.
        """
        if local_sites_in_db:
            local_site_q = Q(local_site=local_site)
        else:
            local_site_q = Q()

        extra: Dict[str, Any] = {}

        groups_q_result = get_review_groups_accessible_q(
            user=user,
            local_site=None,
            needs_user_permission_queries=False)
        groups_q = groups_q_result['q']
        groups_q_tables = groups_q_result['tables']
        groups_q_num_joins = len(groups_q_tables) - 1
        groups_q_join_types = groups_q_result.get('join_types', {})

        rows_q_result = get_reviews_from_user_q(
            user=user,
            from_user=viewed_user.username,
            local_site=local_site,
            has_local_sites_in_db=local_sites_in_db,
            filter_private=True,
            status=None,
            public=True,
            needs_local_site_profile_query=True)
        rows_q = rows_q_result['q']
        rows_q_tables = rows_q_result['tables']
        rows_q_num_joins = len(rows_q_tables) - 1
        rows_q_join_types = rows_q_result.get('join_types', {})
        rows_q_subqueries = rows_q_result.get('subqueries', [])

        equeries = get_http_request_start_equeries(
            user=user,
            local_site=local_site)

        if local_site:
            equeries += [
                {
                    '__note__': 'Fetch the viewed user on the Local Site',
                    'join_types': {
                        'site_localsite_users': 'INNER JOIN',
                    },
                    'model': User,
                    'num_joins': 1,
                    'tables': {
                        'auth_user',
                        'site_localsite_users',
                    },
                    'where': (Q(local_site__id=local_site.pk) &
                              Q(username=viewed_user.username)),
                },
            ]
        else:
            equeries += [
                {
                    '__note__': 'Fetch the viewed user',
                    'model': User,
                    'where': Q(username=viewed_user.username),
                },
            ]

        equeries += rows_q_result.get('prep_equeries', [])
        equeries += groups_q_result.get('prep_equeries', [])
        equeries += [
            {
                # TODO: Remove the redundant local_site Q in the
                #       implementation.
                '__note__': (
                    "Fetch the list of the viewed user's review groups"
                ),
                'distinct': True,
                'join_types': groups_q_join_types,
                'model': Group,
                'num_joins': groups_q_num_joins,
                'only_fields': {
                    'id',
                    'local_site',
                    'name',
                },
                'tables': groups_q_tables,
                'where': (Q(users__id=viewed_user.pk) &
                          Q(groups_q) &
                          local_site_q),
            },
            {
                '__note__': (
                    'Fetch the number of items across all datagrid pages'
                ),
                'annotations': {'__count': Count('*')},
                'join_types': rows_q_join_types,
                'model': Review,
                'num_joins': rows_q_num_joins,
                'subqueries': rows_q_subqueries,
                'tables': rows_q_tables,
                'where': (Q(rows_q) &
                          Q(review_request__local_site=local_site)),
            },
        ]

        if review_pks:
            equeries += [
                {
                    '__note__': 'Fetch the IDs of the items for one page',
                    'distinct': True,
                    'extra': extra,
                    'join_types': rows_q_join_types,
                    'limit': len(review_pks),
                    'model': Review,
                    'num_joins': rows_q_num_joins,
                    'order_by': ('-timestamp',),
                    'subqueries': rows_q_subqueries,
                    'tables': rows_q_tables,
                    'values_select': ('pk',),
                    'where': (Q(rows_q) &
                              Q(review_request__local_site=local_site)),
                },
                {
                    '__note__': (
                        'Fetch the data for one page based on the IDs'
                    ),
                    'extra': extra,
                    'model': Review,
                    'select_related': {'review_request'},
                    'where': Q(pk__in=review_pks),
                },
            ]

        equeries += get_user_profile_equeries(user=viewed_user)

        return equeries
