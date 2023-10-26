"""Unit tests for the dashboard.

Version Added:
    5.0.7
"""

from __future__ import annotations

import kgb
from django.contrib.auth.models import User
from django.db.models import Count, Q, QuerySet
from djblets.testing.decorators import add_fixtures

from reviewboard.accounts.models import (LocalSiteProfile,
                                         Profile,
                                         ReviewRequestVisit)
from reviewboard.datagrids.grids import DashboardDataGrid
from reviewboard.datagrids.tests.base import BaseViewTestCase
from reviewboard.diffviewer.models import DiffSet
from reviewboard.reviews.models import (Group,
                                        ReviewRequest,
                                        ReviewRequestDraft)
from reviewboard.site.models import LocalSite


class DashboardViewTests(kgb.SpyAgency, BaseViewTestCase):
    """Unit tests for the dashboard view."""

    def setUp(self):
        """Set up the test state.

        This will temporarily patch :py:meth:`django.db.models.QuerySet.
        __eq__` to help compare with nested queries. This is a temporary
        issue, and this function will soon be removed.
        """
        super().setUp()

        # This is a very temporary hack to work around some assertQueries
        # comparisons that fail due to our improper use of a nested query.
        # It will be removed as soon as this issue is fixed.
        self._old_queryset_eq = QuerySet.__eq__

        def _queryset_eq(_self, other):
            return repr(_self) == repr(other)

        QuerySet.__eq__ = _queryset_eq

    def tearDown(self):
        """Tear down test state.

        This will restore :py:meth:`django.db.models.QuerySet.__eq__` to
        defaults.
        """
        QuerySet.__eq__ = self._old_queryset_eq

        super().tearDown()

    @add_fixtures(['test_users'])
    def test_incoming(self):
        """Testing dashboard view (incoming)"""
        self.client.login(username='doc', password='doc')

        user = User.objects.get(username='doc')
        profile = user.get_profile()

        for i in range(10):
            review_request = self.create_review_request(
                summary='Test %s' % (i + 1),
                publish=True)

            if i < 5:
                review_request.target_people.add(user)

        extra = {
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
            'mycomments_my_reviews': ("""
                SELECT COUNT(1)
                  FROM reviews_review
                  WHERE reviews_review.user_id = 2
                    AND reviews_review.review_request_id =
                        reviews_reviewrequest.id
            """, []),
            'mycomments_private_reviews': ("""
                SELECT COUNT(1)
                  FROM reviews_review
                  WHERE reviews_review.user_id = 2
                    AND reviews_review.review_request_id =
                        reviews_reviewrequest.id
                    AND NOT reviews_review.public
            """, []),
            'mycomments_shipit_reviews': ("""
                SELECT COUNT(1)
                  FROM reviews_review
                  WHERE reviews_review.user_id = 2
                    AND reviews_review.review_request_id =
                        reviews_reviewrequest.id
                    AND reviews_review.ship_it
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

        # Prime the caches.
        LocalSite.objects.has_local_sites()

        # 10 queries:
        #
        # 1. Fetch logged-in user
        # 2. Fetch logged-in user's Profile
        # 3. Fetch logged-in user's LocalSiteProfile
        # 4. Fetch IDs of logged-in user's review groups
        # 5. Fetch logged-in user's review groups (not from IDs)
        # 6. Fetch logged-in user's starred review groups
        # 7. Set profile's sort_submitter_columns, dashboard_columns, and
        #    extra_data
        # 8. Fetch total number of review requests
        # 9. Fetch IDs of page of review requests
        # 10. Fetch data for review requests
        queries = [
            {
                'model': User,
                'where': Q(pk=user.pk),
            },
            {
                'model': Profile,
                'where': Q(user=user),
            },
            {
                'model': LocalSiteProfile,
                'where': (Q(local_site=None) &
                          Q(profile=profile) &
                          Q(user=user)),
            },
            {
                'model': Group,
                'num_joins': 1,
                'values_select': ('pk',),
                'tables': {
                    'reviews_group',
                    'reviews_group_users',
                },
                'where': Q(users__id=user.pk),
            },
            {
                'model': Group,
                'num_joins': 1,
                'tables': {
                    'reviews_group',
                    'reviews_group_users',
                },
                'where': (Q(users__id=user.pk) &
                          Q(local_site=None)),
                'order_by': ('name',),
            },
            {
                'model': Group,
                'num_joins': 1,
                'tables': {
                    'accounts_profile_starred_groups',
                    'reviews_group',
                },
                'where': (Q(starred_by__id=user.pk) &
                          Q(local_site=None) &
                          ~Q(name__in=set())),
                'order_by': ('name',),
            },
            {
                'type': 'UPDATE',
                'model': Profile,
                'where': Q(pk=user.pk),
            },
            {
                'model': ReviewRequest,
                'annotations': {'__count': Count('*')},
            },
            {
                'model': ReviewRequest,
                'num_joins': 4,
                'tables': {
                    'accounts_profile_starred_review_requests',
                    'auth_user',
                    'reviews_reviewrequest',
                    'reviews_reviewrequest_target_groups',
                    'reviews_reviewrequest_target_people',
                },
                'values_select': ('pk',),
                'extra': extra,
                'where': (
                    Q(Q(Q(public=True) |
                        Q(submitter=user)) &
                      Q(submitter__is_active=True) &
                      Q(status='P') &
                      Q(Q(target_people=user) |
                        Q(target_groups__in=[]) |
                        Q(starred_by=profile))) &
                    ~Q(pk__in=ReviewRequestVisit.objects.none()) &
                    Q(local_site=None)
                ),
                'order_by': ('-last_updated',),
                'distinct': True,
                'limit': 5,
            },
            {
                'model': ReviewRequest,
                'select_related': {'submitter'},
                'extra': extra,
                'where': Q(pk__in=[5, 4, 3, 2, 1]),
            },
        ]

        with self.assertQueries(queries):
            response = self.client.get('/dashboard/', {'view': 'incoming'})

        self.assertEqual(response.status_code, 200)

        datagrid = self._get_context_var(response, 'datagrid')
        self.assertTrue(datagrid)
        self.assertEqual(len(datagrid.rows), 5)
        self.assertEqual(datagrid.rows[0]['object'].summary, 'Test 5')
        self.assertEqual(datagrid.rows[1]['object'].summary, 'Test 4')
        self.assertEqual(datagrid.rows[2]['object'].summary, 'Test 3')
        self.assertEqual(datagrid.rows[3]['object'].summary, 'Test 2')
        self.assertEqual(datagrid.rows[4]['object'].summary, 'Test 1')

    @add_fixtures(['test_users'])
    def test_outgoing(self):
        """Testing dashboard view (outgoing)"""
        self.client.login(username='admin', password='admin')

        user = User.objects.get(username='admin')
        grumpy = User.objects.get(username='grumpy')

        profile = user.get_profile()

        for i in range(10):
            if i < 5:
                submitter = user
            else:
                submitter = grumpy

            self.create_review_request(
                summary='Test %s' % (i + 1),
                submitter=submitter,
                publish=True)

        extra = {
            'new_review_count': ("""
                SELECT COUNT(*)
                  FROM reviews_review, accounts_reviewrequestvisit
                  WHERE reviews_review.public
                    AND reviews_review.review_request_id =
                        reviews_reviewrequest.id
                    AND accounts_reviewrequestvisit.review_request_id =
                        reviews_reviewrequest.id
                    AND accounts_reviewrequestvisit.user_id = 1
                    AND reviews_review.timestamp >
                        accounts_reviewrequestvisit.timestamp
                    AND reviews_review.user_id != 1
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
                   AND accounts_reviewrequestvisit.user_id = 1
            """, []),
        }

        # Prime the caches.
        LocalSite.objects.has_local_sites()

        # 10 queries:
        #
        # 1. Fetch logged-in user
        # 2. Fetch logged-in user's Profile
        # 3. Fetch logged-in user's LocalSiteProfile
        # 4. Fetch logged-in user's review groups
        # 5. Fetch logged-in user's starred review groups (empty, won't
        #    execute)
        # 6. Set profile's sort_submitter_columns, dashboard_columns, and
        #    extra_data
        # 7. Fetch total number of review requests
        # 8. Fetch IDs of page of review requests
        # 9. Prefetch starred status of review requests
        #    (ReviewRequestStarColumn)
        # 10. Fetch data for review requests
        queries = [
            {
                'model': User,
                'where': Q(pk=user.pk),
            },
            {
                'model': Profile,
                'where': Q(user=user),
            },
            {
                'model': LocalSiteProfile,
                'where': (Q(local_site=None) &
                          Q(profile=profile) &
                          Q(user=user)),
            },
            {
                'model': Group,
                'num_joins': 1,
                'tables': {
                    'reviews_group',
                    'reviews_group_users',
                },
                'where': (Q(users__id=user.pk) &
                          Q(local_site=None)),
                'order_by': ('name',),
            },
            {
                'model': Group,
                'num_joins': 1,
                'tables': {
                    'accounts_profile_starred_groups',
                    'reviews_group',
                },
                'where': (Q(starred_by__id=user.pk) &
                          Q(local_site=None) &
                          ~Q(name__in=set())),
                'order_by': ('name',),
            },
            {
                'type': 'UPDATE',
                'model': Profile,
                'where': Q(pk=user.pk),
            },
            {
                'model': ReviewRequest,
                'annotations': {'__count': Count('*')},
            },
            {
                'model': ReviewRequest,
                'num_joins': 1,
                'tables': {
                    'auth_user',
                    'reviews_reviewrequest',
                },
                'values_select': ('pk',),
                'extra': extra,
                'where': (
                    Q(Q(Q(public=True) |
                        Q(submitter=user)) &
                      Q(submitter__is_active=True) &
                      Q(status='P') &
                      Q(submitter=user)) &
                    ~Q(pk__in=ReviewRequestVisit.objects.none()) &
                    Q(local_site=None)
                ),
                'order_by': ('-last_updated',),
                'distinct': True,
                'limit': 5,
            },
            {
                'model': ReviewRequest,
                'num_joins': 1,
                'tables': {
                    'accounts_profile_starred_review_requests',
                    'reviews_reviewrequest',
                },
                'values_select': ('pk',),
                'where': (Q(starred_by__id=user.pk) &
                          Q(pk__in=[5, 4, 3, 2, 1])),
            },
            {
                'model': ReviewRequest,
                'select_related': {'submitter'},
                'extra': extra,
                'where': Q(pk__in=[5, 4, 3, 2, 1]),
            },
        ]

        with self.assertQueries(queries):
            response = self.client.get('/dashboard/', {'view': 'outgoing'})

        self.assertEqual(response.status_code, 200)

        datagrid = self._get_context_var(response, 'datagrid')
        self.assertTrue(datagrid)
        self.assertEqual(len(datagrid.rows), 5)
        self.assertEqual(datagrid.rows[0]['object'].summary, 'Test 5')
        self.assertEqual(datagrid.rows[1]['object'].summary, 'Test 4')
        self.assertEqual(datagrid.rows[2]['object'].summary, 'Test 3')
        self.assertEqual(datagrid.rows[3]['object'].summary, 'Test 2')
        self.assertEqual(datagrid.rows[4]['object'].summary, 'Test 1')

    @add_fixtures(['test_users'])
    def test_outgoing_mine(self):
        """Testing dashboard view (mine)"""
        self.client.login(username='doc', password='doc')

        user = User.objects.get(username='doc')
        profile = user.get_profile()

        grumpy = User.objects.get(username='grumpy')

        for i in range(10):
            if i < 5:
                submitter = user
            else:
                submitter = grumpy

            self.create_review_request(
                summary='Test %s' % (i + 1),
                submitter=submitter,
                publish=True)

        extra = {
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
            'mycomments_my_reviews': ("""
                SELECT COUNT(1)
                  FROM reviews_review
                  WHERE reviews_review.user_id = 2
                    AND reviews_review.review_request_id =
                        reviews_reviewrequest.id
            """, []),
            'mycomments_private_reviews': ("""
                SELECT COUNT(1)
                  FROM reviews_review
                  WHERE reviews_review.user_id = 2
                    AND reviews_review.review_request_id =
                        reviews_reviewrequest.id
                    AND NOT reviews_review.public
            """, []),
            'mycomments_shipit_reviews': ("""
                SELECT COUNT(1)
                  FROM reviews_review
                  WHERE reviews_review.user_id = 2
                    AND reviews_review.review_request_id =
                        reviews_reviewrequest.id
                    AND reviews_review.ship_it
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

        # Prime the caches.
        LocalSite.objects.has_local_sites()

        # 13 queries:
        #
        # 1. Fetch logged-in user
        # 2. Fetch logged-in user's Profile
        # 3. Fetch logged-in user's LocalSiteProfile
        # 4. Fetch logged-in user's review groups (not from IDs)
        # 5. Fetch logged-in user's starred review groups
        # 6. Set profile's sort_submitter_columns, dashboard_columns, and
        #     extra_data
        # 7. Fetch total number of review requests
        # 8. Fetch IDs of page of review requests
        # 9. Fetch data for review requests
        queries = [
            {
                'model': User,
                'where': Q(pk=user.pk),
            },
            {
                'model': Profile,
                'where': Q(user=user),
            },
            {
                'model': LocalSiteProfile,
                'where': (Q(local_site=None) &
                          Q(profile=profile) &
                          Q(user=user)),
            },
            {
                'model': Group,
                'num_joins': 1,
                'tables': {
                    'reviews_group',
                    'reviews_group_users',
                },
                'where': (Q(users__id=user.pk) &
                          Q(local_site=None)),
                'order_by': ('name',),
            },
            {
                'model': Group,
                'num_joins': 1,
                'tables': {
                    'accounts_profile_starred_groups',
                    'reviews_group',
                },
                'where': (Q(starred_by__id=user.pk) &
                          Q(local_site=None) &
                          ~Q(name__in=set())),
                'order_by': ('name',),
            },
            {
                'type': 'UPDATE',
                'model': Profile,
                'where': Q(pk=user.pk),
            },
            {
                'model': ReviewRequest,
                'annotations': {'__count': Count('*')},
            },
            {
                'model': ReviewRequest,
                'num_joins': 1,
                'tables': {
                    'auth_user',
                    'reviews_reviewrequest',
                },
                'values_select': ('pk',),
                'extra': extra,
                'where': (
                    Q(Q(Q(public=True) |
                        Q(submitter=user)) &
                      Q(submitter__is_active=True) &
                      Q(submitter=user)) &
                    ~Q(pk__in=ReviewRequestVisit.objects.none()) &
                    Q(local_site=None)
                ),
                'order_by': ('-last_updated',),
                'distinct': True,
                'limit': 5,
            },
            {
                'model': ReviewRequest,
                'select_related': {'submitter'},
                'extra': extra,
                'where': Q(pk__in=[5, 4, 3, 2, 1]),
            },
        ]

        with self.assertQueries(queries):
            response = self.client.get('/dashboard/', {'view': 'mine'})

        self.assertEqual(response.status_code, 200)

        datagrid = self._get_context_var(response, 'datagrid')
        self.assertTrue(datagrid is not None)
        self.assertEqual(len(datagrid.rows), 5)
        self.assertEqual(datagrid.rows[0]['object'].summary, 'Test 5')
        self.assertEqual(datagrid.rows[1]['object'].summary, 'Test 4')
        self.assertEqual(datagrid.rows[2]['object'].summary, 'Test 3')
        self.assertEqual(datagrid.rows[3]['object'].summary, 'Test 2')
        self.assertEqual(datagrid.rows[4]['object'].summary, 'Test 1')

    @add_fixtures(['test_users'])
    def test_to_me(self):
        """Testing dashboard view (to-me)"""
        self.client.login(username='doc', password='doc')

        user = User.objects.get(username='doc')
        profile = user.get_profile()

        group = self.create_review_group()
        group.users.add(user)

        for i in range(15):
            review_request = self.create_review_request(
                summary='Test %s' % (i + 1),
                publish=True)

            if i < 5:
                review_request.target_people.add(user)
            elif i < 10:
                review_request.target_groups.add(group)

        extra = {
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
            'mycomments_my_reviews': ("""
                SELECT COUNT(1)
                  FROM reviews_review
                  WHERE reviews_review.user_id = 2
                    AND reviews_review.review_request_id =
                        reviews_reviewrequest.id
            """, []),
            'mycomments_private_reviews': ("""
                SELECT COUNT(1)
                  FROM reviews_review
                  WHERE reviews_review.user_id = 2
                    AND reviews_review.review_request_id =
                        reviews_reviewrequest.id
                    AND NOT reviews_review.public
            """, []),
            'mycomments_shipit_reviews': ("""
                SELECT COUNT(1)
                  FROM reviews_review
                  WHERE reviews_review.user_id = 2
                    AND reviews_review.review_request_id =
                        reviews_reviewrequest.id
                    AND reviews_review.ship_it
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

        # 9 queries:
        #
        # 1. Fetch logged-in user
        # 2. Fetch logged-in user's Profile
        # 3. Fetch logged-in user's LocalSiteProfile
        # 4. Fetch review request IDs of logged-in user's non-visible
        #    ReviewRequestVisits
        # 5. Fetch logged-in user's review groups (not from IDs)
        # 6. Fetch logged-in user's starred review groups
        # 7. Set profile's sort_submitter_columns, dashboard_columns, and
        #    extra_data
        # 8. Fetch total number of review requests
        # 9. Fetch IDs of page of review requests
        # 10. Fetch data for review requests
        queries = [
            {
                'model': User,
                'where': Q(pk=user.pk),
            },
            {
                'model': Profile,
                'where': Q(user=user),
            },
            {
                'model': LocalSiteProfile,
                'where': (Q(local_site=None) &
                          Q(profile=profile) &
                          Q(user=user)),
            },
            {
                'model': Group,
                'num_joins': 1,
                'tables': {
                    'reviews_group',
                    'reviews_group_users',
                },
                'where': (Q(users__id=user.pk) &
                          Q(local_site=None)),
                'order_by': ('name',),
            },
            {
                'model': Group,
                'num_joins': 1,
                'tables': {
                    'accounts_profile_starred_groups',
                    'reviews_group',
                },
                'where': (Q(starred_by__id=user.pk) &
                          Q(local_site=None) &
                          ~Q(name__in={'test-group'})),
                'order_by': ('name',),
            },
            {
                'type': 'UPDATE',
                'model': Profile,
                'where': Q(pk=user.pk),
            },
            {
                'model': ReviewRequest,
                'annotations': {'__count': Count('*')},
            },
            {
                'model': ReviewRequest,
                'num_joins': 3,
                'tables': {
                    'accounts_profile_starred_review_requests',
                    'auth_user',
                    'reviews_reviewrequest',
                    'reviews_reviewrequest_target_people',
                },
                'values_select': ('pk',),
                'extra': extra,
                'where': (
                    Q(Q(Q(public=True) |
                        Q(submitter=user)) &
                      Q(submitter__is_active=True) &
                      Q(status='P') &
                      (Q(target_people=user) |
                       Q(starred_by=profile))) &
                    ~Q(pk__in=ReviewRequestVisit.objects.none()) &
                    Q(local_site=None)
                ),
                'order_by': ('-last_updated',),
                'distinct': True,
                'limit': 5,
            },
            {
                'model': ReviewRequest,
                'select_related': {'submitter'},
                'extra': extra,
                'where': Q(pk__in=[5, 4, 3, 2, 1]),
            },
        ]

        with self.assertQueries(queries):
            response = self.client.get('/dashboard/', {'view': 'to-me'})

        self.assertEqual(response.status_code, 200)

        datagrid = self._get_context_var(response, 'datagrid')
        self.assertTrue(datagrid)
        self.assertEqual(len(datagrid.rows), 5)
        self.assertEqual(datagrid.rows[0]['object'].summary, 'Test 5')
        self.assertEqual(datagrid.rows[1]['object'].summary, 'Test 4')
        self.assertEqual(datagrid.rows[2]['object'].summary, 'Test 3')
        self.assertEqual(datagrid.rows[3]['object'].summary, 'Test 2')
        self.assertEqual(datagrid.rows[4]['object'].summary, 'Test 1')

    @add_fixtures(['test_users'])
    def test_to_group_with_joined_groups(self):
        """Testing dashboard view with to-group and joined groups"""
        self.client.login(username='doc', password='doc')

        user = User.objects.get(username='doc')
        profile = user.get_profile()

        group = self.create_review_group(name='devgroup')
        group.users.add(User.objects.get(username='doc'))

        group2 = self.create_review_group(name='test-group')

        for i in range(15):
            review_request = self.create_review_request(
                summary='Test %s' % (i + 1),
                publish=True)

            if i < 5:
                review_request.target_groups.add(group)
            elif i < 10:
                review_request.target_groups.add(group2)

        extra = {
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
            'mycomments_my_reviews': ("""
                SELECT COUNT(1)
                  FROM reviews_review
                  WHERE reviews_review.user_id = 2
                    AND reviews_review.review_request_id =
                        reviews_reviewrequest.id
            """, []),
            'mycomments_private_reviews': ("""
                SELECT COUNT(1)
                  FROM reviews_review
                  WHERE reviews_review.user_id = 2
                    AND reviews_review.review_request_id =
                        reviews_reviewrequest.id
                    AND NOT reviews_review.public
            """, []),
            'mycomments_shipit_reviews': ("""
                SELECT COUNT(1)
                  FROM reviews_review
                  WHERE reviews_review.user_id = 2
                    AND reviews_review.review_request_id =
                        reviews_reviewrequest.id
                    AND reviews_review.ship_it
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

        # 10 queries:
        #
        # 1. Fetch logged-in user
        # 2. Fetch logged-in user's Profile
        # 3. Fetch logged-in user's LocalSiteProfile
        # 4. Fetch group "devgroup".
        # 5. Fetch logged-in user's review groups (not from IDs)
        # 6. Fetch logged-in user's starred review groups
        # 7. Set profile's sort_submitter_columns, dashboard_columns, and
        #    extra_data
        # 8. Fetch total number of review requests
        # 9. Fetch IDs of page of review requests
        # 10. Fetch data for review requests
        queries = [
            {
                'model': User,
                'where': Q(pk=user.pk),
            },
            {
                'model': Profile,
                'where': Q(user=user),
            },
            {
                'model': LocalSiteProfile,
                'where': (Q(local_site=None) &
                          Q(profile=profile) &
                          Q(user=user)),
            },
            {
                'model': Group,
                'where': (Q(local_site=None) &
                          Q(name='devgroup')),
            },
            {
                'model': Group,
                'num_joins': 1,
                'tables': {
                    'reviews_group',
                    'reviews_group_users',
                },
                'where': (Q(users__id=user.pk) &
                          Q(local_site=None)),
                'order_by': ('name',),
            },
            {
                'model': Group,
                'num_joins': 1,
                'tables': {
                    'accounts_profile_starred_groups',
                    'reviews_group',
                },
                'where': (Q(starred_by__id=user.pk) &
                          Q(local_site=None) &
                          ~Q(name__in={'devgroup'})),
                'order_by': ('name',),
            },
            {
                'type': 'UPDATE',
                'model': Profile,
                'where': Q(pk=user.pk),
            },
            {
                'model': ReviewRequest,
                'annotations': {'__count': Count('*')},
            },
            {
                'model': ReviewRequest,
                'num_joins': 3,
                'tables': {
                    'auth_user',
                    'reviews_group',
                    'reviews_reviewrequest',
                    'reviews_reviewrequest_target_groups',
                },
                'values_select': ('pk',),
                'extra': extra,
                'where': (
                    Q(Q(Q(public=True) |
                        Q(submitter=user)) &
                      Q(submitter__is_active=True) &
                      Q(status='P') &
                      Q(target_groups__name='devgroup')) &
                    ~Q(pk__in=ReviewRequestVisit.objects.none()) &
                    Q(local_site=None)
                ),
                'order_by': ('-last_updated',),
                'distinct': True,
                'limit': 5,
            },
            {
                'model': ReviewRequest,
                'select_related': {'submitter'},
                'extra': extra,
                'where': Q(pk__in=[5, 4, 3, 2, 1]),
            },
        ]

        with self.assertQueries(queries):
            response = self.client.get(
                '/dashboard/',
                {
                    'view': 'to-group',
                    'group': 'devgroup',
                })

        self.assertEqual(response.status_code, 200)

        datagrid = self._get_context_var(response, 'datagrid')
        self.assertTrue(datagrid)
        self.assertEqual(len(datagrid.rows), 5)
        self.assertEqual(datagrid.rows[0]['object'].summary, 'Test 5')
        self.assertEqual(datagrid.rows[1]['object'].summary, 'Test 4')
        self.assertEqual(datagrid.rows[2]['object'].summary, 'Test 3')
        self.assertEqual(datagrid.rows[3]['object'].summary, 'Test 2')
        self.assertEqual(datagrid.rows[4]['object'].summary, 'Test 1')

    @add_fixtures(['test_users'])
    def test_to_group_with_unjoined_public_group(self):
        """Testing dashboard view with to-group and unjoined public group"""
        self.client.login(username='doc', password='doc')

        user = User.objects.get(username='doc')
        profile = user.get_profile()

        group = self.create_review_group(name='devgroup')

        review_request = self.create_review_request(summary='Test 1',
                                                    publish=True)
        review_request.target_groups.add(group)

        extra = {
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
            'mycomments_my_reviews': ("""
                SELECT COUNT(1)
                  FROM reviews_review
                  WHERE reviews_review.user_id = 2
                    AND reviews_review.review_request_id =
                        reviews_reviewrequest.id
            """, []),
            'mycomments_private_reviews': ("""
                SELECT COUNT(1)
                  FROM reviews_review
                  WHERE reviews_review.user_id = 2
                    AND reviews_review.review_request_id =
                        reviews_reviewrequest.id
                    AND NOT reviews_review.public
            """, []),
            'mycomments_shipit_reviews': ("""
                SELECT COUNT(1)
                  FROM reviews_review
                  WHERE reviews_review.user_id = 2
                    AND reviews_review.review_request_id =
                        reviews_reviewrequest.id
                    AND reviews_review.ship_it
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

        # 10 queries:
        #
        # 1. Fetch logged-in user
        # 2. Fetch logged-in user's Profile
        # 3. Fetch logged-in user's LocalSiteProfile
        # 4. Fetch group "devgroup".
        # 5. Fetch logged-in user's review groups (not from IDs)
        # 6. Fetch logged-in user's starred review groups
        # 7. Set profile's sort_submitter_columns, dashboard_columns, and
        #    extra_data
        # 8. Fetch total number of review requests
        # 9. Fetch IDs of page of review requests
        # 10. Fetch data for review requests
        queries = [
            {
                'model': User,
                'where': Q(pk=user.pk),
            },
            {
                'model': Profile,
                'where': Q(user=user),
            },
            {
                'model': LocalSiteProfile,
                'where': (Q(local_site=None) &
                          Q(profile=profile) &
                          Q(user=user)),
            },
            {
                'model': Group,
                'where': (Q(local_site=None) &
                          Q(name='devgroup')),
            },
            {
                'model': Group,
                'num_joins': 1,
                'tables': {
                    'reviews_group',
                    'reviews_group_users',
                },
                'where': (Q(users__id=user.pk) &
                          Q(local_site=None)),
                'order_by': ('name',),
            },
            {
                'model': Group,
                'num_joins': 1,
                'tables': {
                    'accounts_profile_starred_groups',
                    'reviews_group',
                },
                'where': (Q(starred_by__id=user.pk) &
                          Q(local_site=None) &
                          ~Q(name__in=set())),
                'order_by': ('name',),
            },
            {
                'type': 'UPDATE',
                'model': Profile,
                'where': Q(pk=user.pk),
            },
            {
                'model': ReviewRequest,
                'annotations': {'__count': Count('*')},
            },
            {
                'model': ReviewRequest,
                'num_joins': 3,
                'tables': {
                    'auth_user',
                    'reviews_group',
                    'reviews_reviewrequest',
                    'reviews_reviewrequest_target_groups',
                },
                'values_select': ('pk',),
                'extra': extra,
                'where': (
                    Q(Q(Q(public=True) |
                        Q(submitter=user)) &
                      Q(submitter__is_active=True) &
                      Q(status='P') &
                      Q(target_groups__name='devgroup')) &
                    ~Q(pk__in=ReviewRequestVisit.objects.none()) &
                    Q(local_site=None)
                ),
                'order_by': ('-last_updated',),
                'distinct': True,
                'limit': 1,
            },
            {
                'model': ReviewRequest,
                'select_related': {'submitter'},
                'extra': extra,
                'where': Q(pk__in=[1]),
            },
        ]

        with self.assertQueries(queries):
            response = self.client.get(
                '/dashboard/',
                {
                    'view': 'to-group',
                    'group': 'devgroup',
                })
        self.assertEqual(response.status_code, 200)

    @add_fixtures(['test_users'])
    def test_to_group_with_unjoined_private_group(self):
        """Testing dashboard view with to-group and unjoined private group"""
        self.client.login(username='doc', password='doc')

        group = self.create_review_group(name='new-private', invite_only=True)

        review_request = self.create_review_request(summary='Test 1',
                                                    publish=True)
        review_request.target_groups.add(group)

        response = self.client.get('/dashboard/',
                                   {'view': 'to-group',
                                    'group': 'devgroup'})
        self.assertEqual(response.status_code, 404)

    @add_fixtures(['test_users'])
    def test_with_all_columns(self):
        """Testing dashboard view with all columns"""
        self.client.login(username='doc', password='doc')

        user = User.objects.get(username='doc')
        profile = user.get_profile()

        review_requests = []
        diffset_histories = []

        for i in range(10):
            review_request = self.create_review_request(
                summary='Test %s' % (i + 1),
                publish=True)

            if i < 5:
                review_request.target_people.add(user)
                diffset_histories.append(review_request.diffset_history)
                review_requests.append(review_request)

        extra = {
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
            'mycomments_my_reviews': ("""
                SELECT COUNT(1)
                  FROM reviews_review
                  WHERE reviews_review.user_id = 2
                    AND reviews_review.review_request_id =
                        reviews_reviewrequest.id
            """, []),
            'mycomments_private_reviews': ("""
                SELECT COUNT(1)
                  FROM reviews_review
                  WHERE reviews_review.user_id = 2
                    AND reviews_review.review_request_id =
                        reviews_reviewrequest.id
                    AND NOT reviews_review.public
            """, []),
            'mycomments_shipit_reviews': ("""
                SELECT COUNT(1)
                  FROM reviews_review
                  WHERE reviews_review.user_id = 2
                    AND reviews_review.review_request_id =
                        reviews_reviewrequest.id
                    AND reviews_review.ship_it
            """, []),
            'publicreviewcount_count': ("""
                SELECT COUNT(*)
                  FROM reviews_review
                 WHERE reviews_review.public
                   AND reviews_review.base_reply_to_id is NULL
                   AND reviews_review.review_request_id =
                       reviews_reviewrequest.id
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

        # Prime the caches.
        LocalSite.objects.has_local_sites()

        # 15 queries:
        #
        # 1. Fetch logged-in user
        # 2. Fetch logged-in user's Profile
        # 3. Fetch logged-in user's LocalSiteProfile
        # 4. Fetch IDs of logged-in user's review groups
        # 5. Fetch logged-in user's review groups (not from IDs)
        # 6. Fetch logged-in user's starred review groups
        # 7. Set profile's sort_submitter_columns, dashboard_columns, and
        #    extra_data
        # 8. Fetch total number of review requests
        # 9. Fetch IDs of page of review requests
        # 10. Prefetch starred status of review requests
        #     (ReviewRequestStarColumn)
        # 11. Prefetch IDs of target people for review requests (PeopleColumn)
        # 12. Fetch data for review requests
        # 13. Prefetch diffsets for review requests (DiffSizeColumn)
        # 14. Prefetch target groups for review requests (GroupsColumn)
        # 15. Prefetch target people for review requests (PeopleColumn)
        queries = [
            {
                'model': User,
                'where': Q(pk=user.pk),
            },
            {
                'model': Profile,
                'where': Q(user=user),
            },
            {
                'model': LocalSiteProfile,
                'where': (Q(local_site=None) &
                          Q(profile=profile) &
                          Q(user=user)),
            },
            {
                'model': Group,
                'num_joins': 1,
                'values_select': ('pk',),
                'tables': {
                    'reviews_group',
                    'reviews_group_users',
                },
                'where': Q(users__id=user.pk),
            },
            {
                'model': Group,
                'num_joins': 1,
                'tables': {
                    'reviews_group',
                    'reviews_group_users',
                },
                'where': (Q(users__id=user.pk) &
                          Q(local_site=None)),
                'order_by': ('name',),
            },
            {
                'model': Group,
                'num_joins': 1,
                'tables': {
                    'accounts_profile_starred_groups',
                    'reviews_group',
                },
                'where': (Q(starred_by__id=user.pk) &
                          Q(local_site=None) &
                          ~Q(name__in=set())),
                'order_by': ('name',),
            },
            {
                'type': 'UPDATE',
                'model': Profile,
                'where': Q(pk=user.pk),
            },
            {
                'model': ReviewRequest,
                'annotations': {'__count': Count('*')},
            },
            {
                'model': ReviewRequest,
                'num_joins': 4,
                'tables': {
                    'accounts_profile_starred_review_requests',
                    'auth_user',
                    'reviews_reviewrequest',
                    'reviews_reviewrequest_target_groups',
                    'reviews_reviewrequest_target_people',
                },
                'values_select': ('pk',),
                'extra': extra,
                'where': (
                    Q(Q(Q(public=True) |
                        Q(submitter=user)) &
                      Q(submitter__is_active=True) &
                      Q(status='P') &
                      Q(Q(target_people=user) |
                        Q(target_groups__in=[]) |
                        Q(starred_by=profile))) &
                    ~Q(pk__in=ReviewRequestVisit.objects.none()) &
                    Q(local_site=None)
                ),
                'order_by': ('-last_updated',),
                'distinct': True,
                'limit': 5,
            },
            {
                'model': ReviewRequest,
                'num_joins': 1,
                'tables': {
                    'accounts_profile_starred_review_requests',
                    'reviews_reviewrequest',
                },
                'values_select': ('pk',),
                'where': (Q(starred_by__id=user.pk) &
                          Q(pk__in=[5, 4, 3, 2, 1])),
            },
            {
                'model': ReviewRequest,
                'num_joins': 1,
                'tables': {
                    'reviews_reviewrequest',
                    'reviews_reviewrequest_target_people',
                },
                'values_select': ('pk',),
                'where': (Q(target_people__id=user.pk) &
                          Q(pk__in=[5, 4, 3, 2, 1])),
            },
            {
                'model': ReviewRequest,
                'select_related': {
                    'diffset_history',
                    'repository',
                    'submitter',
                },
                'extra': extra,
                'where': Q(pk__in=[5, 4, 3, 2, 1]),
            },
            {
                'model': DiffSet,
                'where': Q(history__in=diffset_histories),
            },
            {
                'model': Group,
                'num_joins': 1,
                'tables': {
                    'reviews_group',
                    'reviews_reviewrequest_target_groups',
                },
                'extra': {
                    '_prefetch_related_val_reviewrequest_id': (
                        '"reviews_reviewrequest_target_groups".'
                        '"reviewrequest_id"',
                        []
                    ),
                },
                'where': Q(review_requests__in=review_requests),
            },
            {
                'model': User,
                'num_joins': 1,
                'tables': {
                    'auth_user',
                    'reviews_reviewrequest_target_people',
                },
                'extra': {
                    '_prefetch_related_val_reviewrequest_id': (
                        '"reviews_reviewrequest_target_people".'
                        '"reviewrequest_id"',
                        []
                    ),
                },
                'where': Q(directed_review_requests__in=review_requests),
            },
        ]

        column_ids = sorted(
            _column.id
            for _column in DashboardDataGrid.get_columns()
        )

        with self.assertQueries(queries):
            response = self.client.get(
                '/dashboard/',
                {
                    'columns': ','.join(column_ids),
                    'view': 'incoming',
                })

        self.assertEqual(response.status_code, 200)

        datagrid = self._get_context_var(response, 'datagrid')
        self.assertIsNotNone(datagrid)
        self.assertEqual(len(datagrid.rows), 5)
        self.assertEqual(datagrid.rows[0]['object'].summary, 'Test 5')
        self.assertEqual(datagrid.rows[1]['object'].summary, 'Test 4')
        self.assertEqual(datagrid.rows[2]['object'].summary, 'Test 3')
        self.assertEqual(datagrid.rows[3]['object'].summary, 'Test 2')
        self.assertEqual(datagrid.rows[4]['object'].summary, 'Test 1')

        self.assertEqual(
            [
                _stateful_column.id
                for _stateful_column in datagrid.columns
            ],
            column_ids)

    @add_fixtures(['test_users'])
    def test_show_archived(self):
        """Testing dashboard view with show-archived"""
        visible = self.create_review_request(summary='Test 1', publish=True)
        archived = self.create_review_request(summary='Test 2', publish=True)
        muted = self.create_review_request(summary='Test 3', publish=True)

        self.client.login(username='doc', password='doc')
        user = User.objects.get(username='doc')

        visible.target_people.add(user)
        archived.target_people.add(user)
        muted.target_people.add(user)

        self.client.get(visible.get_absolute_url())
        self.client.get(archived.get_absolute_url())
        self.client.get(muted.get_absolute_url())

        visit = ReviewRequestVisit.objects.get(user__username=user,
                                               review_request=archived.id)
        visit.visibility = ReviewRequestVisit.ARCHIVED
        visit.save()

        visit = ReviewRequestVisit.objects.get(user__username=user,
                                               review_request=muted.id)
        visit.visibility = ReviewRequestVisit.MUTED
        visit.save()

        response = self.client.get('/dashboard/', {'show-archived': '1'})
        self.assertEqual(response.status_code, 200)

        datagrid = self._get_context_var(response, 'datagrid')
        self.assertTrue(datagrid)
        self.assertEqual(len(datagrid.rows), 3)
        self.assertEqual(datagrid.rows[0]['object'].summary, 'Test 3')
        self.assertEqual(datagrid.rows[1]['object'].summary, 'Test 2')
        self.assertEqual(datagrid.rows[2]['object'].summary, 'Test 1')

        response = self.client.get('/dashboard/', {'show-archived': '0'})
        self.assertEqual(response.status_code, 200)

        datagrid = self._get_context_var(response, 'datagrid')
        self.assertTrue(datagrid)
        self.assertEqual(len(datagrid.rows), 1)
        self.assertEqual(datagrid.rows[0]['object'].summary, 'Test 1')

        self.client.logout()
        self.client.login(username='grumpy', password='grumpy')
        user = User.objects.get(username='grumpy')

        visible.target_people.add(user)
        archived.target_people.add(user)
        muted.target_people.add(user)

        self.client.get(visible.get_absolute_url())
        self.client.get(archived.get_absolute_url())
        self.client.get(muted.get_absolute_url())

        response = self.client.get('/dashboard/', {'show-archived': '1'})
        self.assertEqual(response.status_code, 200)

        datagrid = self._get_context_var(response, 'datagrid')
        self.assertTrue(datagrid)
        self.assertEqual(len(datagrid.rows), 3)
        self.assertEqual(datagrid.rows[0]['object'].summary, 'Test 3')
        self.assertEqual(datagrid.rows[1]['object'].summary, 'Test 2')
        self.assertEqual(datagrid.rows[2]['object'].summary, 'Test 1')

        response = self.client.get('/dashboard/', {'show-archived': '0'})
        self.assertEqual(response.status_code, 200)

        datagrid = self._get_context_var(response, 'datagrid')
        self.assertTrue(datagrid)
        self.assertEqual(len(datagrid.rows), 3)
        self.assertEqual(datagrid.rows[0]['object'].summary, 'Test 3')
        self.assertEqual(datagrid.rows[1]['object'].summary, 'Test 2')
        self.assertEqual(datagrid.rows[2]['object'].summary, 'Test 1')

    @add_fixtures(['test_users'])
    def test_archived_with_null_extra_data(self):
        """Testing dashboard view with archived review requests and null
        extra_data
        """
        # We encountered a bug where the archived state in the dashboard was
        # assuming that Profile.extra_data was always a dictionary. In modern
        # versions of Review Board, the default value for that field is an
        # empty dict, but old versions defaulted it to None. This test verifies
        # that the bug is fixed.
        archived = self.create_review_request(summary='Test 1', publish=True)

        self.client.login(username='doc', password='doc')
        user = User.objects.get(username='doc')

        profile = user.get_profile()
        profile.extra_data = None
        profile.save(update_fields=('extra_data',))

        archived.target_people.add(user)

        self.client.get(archived.get_absolute_url())

        visit = ReviewRequestVisit.objects.get(user__username=user,
                                               review_request=archived.id)
        visit.visibility = ReviewRequestVisit.ARCHIVED
        visit.save()

        response = self.client.get('/dashboard/', {'show-archived': '0'})
        self.assertEqual(response.status_code, 200)

    @add_fixtures(['test_users'])
    def test_sidebar(self):
        """Testing dashboard sidebar"""
        self.client.login(username='doc', password='doc')
        user = User.objects.get(username='doc')
        profile = user.get_profile()

        # Create all the test data.
        devgroup = self.create_review_group(name='devgroup')
        devgroup.users.add(user)

        privgroup = self.create_review_group(name='privgroup')
        privgroup.users.add(user)

        review_request = self.create_review_request(submitter=user,
                                                    publish=True)

        review_request = self.create_review_request(submitter='grumpy')
        draft = ReviewRequestDraft.create(review_request)
        draft.target_people.add(user)
        review_request.publish(review_request.submitter)

        review_request = self.create_review_request(submitter='grumpy')
        draft = ReviewRequestDraft.create(review_request)
        draft.target_groups.add(devgroup)
        review_request.publish(review_request.submitter)

        review_request = self.create_review_request(submitter='grumpy')
        draft = ReviewRequestDraft.create(review_request)
        draft.target_groups.add(privgroup)
        review_request.publish(review_request.submitter)
        profile.star_review_request(review_request)

        # Now load the dashboard and get the sidebar items.
        response = self.client.get('/dashboard/')
        self.assertEqual(response.status_code, 200)

        sidebar_items = \
            self._get_context_var(response, 'datagrid').sidebar_items
        self.assertEqual(len(sidebar_items), 3)

        # Test the "Overview" section.
        section = sidebar_items[0]
        self.assertEqual(str(section.label), 'Overview')

        # Test the "Outgoing" section.
        section = sidebar_items[1]
        self.assertEqual(str(section.label), 'Outgoing')
        self.assertEqual(len(section.items), 2)
        self.assertEqual(str(section.items[0].label), 'All')
        self.assertEqual(section.items[0].count, 1)
        self.assertEqual(str(section.items[1].label), 'Open')
        self.assertEqual(section.items[1].count, 1)

        # Test the "Incoming" section.
        section = sidebar_items[2]
        self.assertEqual(str(section.label), 'Incoming')
        self.assertEqual(len(section.items), 5)
        self.assertEqual(str(section.items[0].label), 'Open')
        self.assertEqual(section.items[0].count, 3)
        self.assertEqual(str(section.items[1].label), 'To Me')
        self.assertEqual(section.items[1].count, 1)
        self.assertEqual(str(section.items[2].label), 'Starred')
        self.assertEqual(section.items[2].count, 1)
        self.assertEqual(str(section.items[3].label), 'devgroup')
        self.assertEqual(section.items[3].count, 1)
        self.assertEqual(str(section.items[4].label), 'privgroup')
        self.assertEqual(section.items[4].count, 1)
