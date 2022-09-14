"""Unit tests for reviewboard.datagrids."""

from datetime import timedelta

import kgb
from django.contrib.auth.models import AnonymousUser, User
from django.core.cache import cache
from django.db.models import Count, Q, QuerySet
from django.test.client import RequestFactory
from django.urls import reverse
from django.utils.safestring import SafeText
from djblets.datagrid.grids import DataGrid
from djblets.siteconfig.models import SiteConfiguration
from djblets.testing.decorators import add_fixtures

from reviewboard.accounts.models import (LocalSiteProfile,
                                         Profile,
                                         ReviewRequestVisit)
from reviewboard.datagrids.builtin_items import UserGroupsItem, UserProfileItem
from reviewboard.datagrids.columns import (FullNameColumn,
                                           ShipItColumn,
                                           SummaryColumn,
                                           UsernameColumn)
from reviewboard.datagrids.grids import DashboardDataGrid
from reviewboard.diffviewer.models import DiffSet
from reviewboard.reviews.models import (Group,
                                        ReviewRequest,
                                        ReviewRequestDraft,
                                        Review)
from reviewboard.site.models import LocalSite
from reviewboard.testing import TestCase


class BaseViewTestCase(TestCase):
    """Base class for tests of dashboard views."""

    def setUp(self):
        """Set up the test case."""
        super(BaseViewTestCase, self).setUp()

        self.siteconfig = SiteConfiguration.objects.get_current()
        self._old_auth_require_sitewide_login = \
            self.siteconfig.get('auth_require_sitewide_login')
        self.siteconfig.set('auth_require_sitewide_login', False)
        self.siteconfig.save()

    def tearDown(self):
        super(BaseViewTestCase, self).tearDown()

        self.siteconfig = SiteConfiguration.objects.get_current()
        self.siteconfig.set('auth_require_sitewide_login',
                            self._old_auth_require_sitewide_login)
        self.siteconfig.save()

    def _prefetch_cached(self, local_site=None):
        """Pre-fetch cacheable statistics and data.

        Version Added:
            5.0

        Args:
            local_site (reviewboard.site.models.LocalSite, optional):
                The Local Site being used for the test.
        """
        SiteConfiguration.objects.get_current()

        if local_site is not None:
            LocalSite.objects.get_local_site_acl_stats(local_site)

        for user in User.objects.all():
            user.get_local_site_stats()

    def _get_context_var(self, response, varname):
        """Return a variable from the view context."""
        for context in response.context:
            if varname in context:
                return context[varname]

        return None


class BaseColumnTestCase(TestCase):
    """Base class for defining a column unit test."""

    #: An instance of the column to use on the datagrid.
    column = None

    fixtures = ['test_users']

    def setUp(self):
        super(BaseColumnTestCase, self).setUp()

        class TestDataGrid(DataGrid):
            column = self.column

        request_factory = RequestFactory()
        self.request = request_factory.get('/')
        self.request.user = User.objects.get(username='doc')

        self.grid = TestDataGrid(self.request)
        self.stateful_column = self.grid.get_stateful_column(self.column)


class AllReviewRequestViewTests(BaseViewTestCase):
    """Unit tests for the all_review_requests view."""

    @add_fixtures(['test_users'])
    def test_with_access(self):
        """Testing all_review_requests view"""
        self.create_review_request(summary='Test 1', publish=True)
        self.create_review_request(summary='Test 2', publish=True)
        self.create_review_request(summary='Test 3', publish=True)

        self.client.login(username='grumpy', password='grumpy')

        response = self.client.get('/r/')
        self.assertEqual(response.status_code, 200)

        datagrid = self._get_context_var(response, 'datagrid')
        self.assertTrue(datagrid)
        self.assertEqual(len(datagrid.rows), 3)
        self.assertEqual(datagrid.rows[0]['object'].summary, 'Test 3')
        self.assertEqual(datagrid.rows[1]['object'].summary, 'Test 2')
        self.assertEqual(datagrid.rows[2]['object'].summary, 'Test 1')

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
        user = User.objects.get(username='grumpy')

        # These are public
        self.create_review_request(summary='Test 1', publish=True)
        self.create_review_request(summary='Test 2', publish=True)

        repository1 = self.create_repository(name='repo1',
                                             public=False)
        repository1.users.add(user)
        self.create_review_request(summary='Test 3',
                                   repository=repository1,
                                   publish=True)

        group1 = self.create_review_group(name='group1',
                                          invite_only=True)
        group1.users.add(user)
        review_request = self.create_review_request(summary='Test 4',
                                                    publish=True)
        review_request.target_groups.add(group1)

        # These are private
        repository2 = self.create_repository(name='group2',
                                             public=False)
        self.create_review_request(summary='Test 5',
                                   repository=repository2,
                                   publish=True)

        group2 = self.create_review_group(name='group2',
                                          invite_only=True)
        review_request = self.create_review_request(summary='Test 6',
                                                    publish=True)
        review_request.target_groups.add(group2)

        # Log in and check what we get.
        self.client.login(username='grumpy', password='grumpy')

        response = self.client.get('/r/')
        self.assertEqual(response.status_code, 200)

        datagrid = self._get_context_var(response, 'datagrid')
        self.assertTrue(datagrid)
        self.assertEqual(len(datagrid.rows), 4)
        self.assertEqual(datagrid.rows[0]['object'].summary, 'Test 4')
        self.assertEqual(datagrid.rows[1]['object'].summary, 'Test 3')
        self.assertEqual(datagrid.rows[2]['object'].summary, 'Test 2')
        self.assertEqual(datagrid.rows[3]['object'].summary, 'Test 1')

    @add_fixtures(['test_users'])
    def test_with_inactive_users(self):
        """Testing all_review_requests view with review requests from inactive
        users"""
        user = User.objects.get(username='doc')
        user.is_active = False
        user.save()

        rr = self.create_review_request(summary='Test 1', submitter='doc',
                                        publish=True)
        rr.close(ReviewRequest.SUBMITTED)
        self.create_review_request(summary='Test 2', submitter='grumpy',
                                   publish=True)

        self.client.login(username='grumpy', password='grumpy')
        response = self.client.get('/r/')
        self.assertEqual(response.status_code, 200)

        datagrid = self._get_context_var(response, 'datagrid')
        self.assertTrue(datagrid)
        self.assertEqual(len(datagrid.rows), 2)
        self.assertEqual(datagrid.rows[0]['object'].summary, 'Test 2')
        self.assertEqual(datagrid.rows[1]['object'].summary, 'Test 1')


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
                      Q(local_site=None) &
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
                      Q(local_site=None) &
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
                      Q(local_site=None) &
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
                      Q(local_site=None) &
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
                      Q(local_site=None) &
                      Q(local_site=None) &
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
                      Q(local_site=None) &
                      Q(local_site=None) &
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
                      Q(local_site=None) &
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


class GroupListViewTests(BaseViewTestCase):
    """Unit tests for the group_list view."""

    @add_fixtures(['test_users'])
    def test_with_access(self):
        """Testing group_list view"""
        for i in range(10):
            # We're using %x instead of %d so that "a" will come after "9".
            # Otherwise "10" comes between "1" and "2".
            self.create_review_group(name='group-%x' % (i + 1))

        self._prefetch_cached()

        # 13 queries:
        #
        # 1. Fetch total number of results
        # 2. Fetch IDs of page of results
        # 3. Fetch data for page of results
        # 4. Fetch review request count on group-1
        # 5. Fetch review request count on group-2
        # 6. Fetch review request count on group-3
        # 7. Fetch review request count on group-4
        # 8. Fetch review request count on group-5
        # 9. Fetch review request count on group-6
        # 10. Fetch review request count on group-7
        # 11. Fetch review request count on group-8
        # 12. Fetch review request count on group-9
        # 13. Fetch review request count on group-a
        queries = [
            {
                'model': Group,
                'annotations': {'__count': Count('*')},
            },
            {
                'model': Group,
                'values_select': ('pk',),
                'where': (Q(invite_only=False) &
                          Q(visible=True) &
                          Q(local_site=None)),
                'order_by': ('name',),
                'distinct': True,
                'limit': 10,
            },
            {
                'model': Group,
                'where': Q(pk__in=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]),
            },
            {
                'model': ReviewRequest,
                'num_joins': 1,
                'tables': {
                    'reviews_reviewrequest',
                    'reviews_reviewrequest_target_groups',
                },
                'annotations': {'__count': Count('*')},
                'where': (Q(target_groups__id=1) &
                          Q(public=True) &
                          Q(status='P')),
            },
            {
                'model': ReviewRequest,
                'num_joins': 1,
                'tables': {
                    'reviews_reviewrequest',
                    'reviews_reviewrequest_target_groups',
                },
                'annotations': {'__count': Count('*')},
                'where': (Q(target_groups__id=2) &
                          Q(public=True) &
                          Q(status='P')),
            },
            {
                'model': ReviewRequest,
                'num_joins': 1,
                'tables': {
                    'reviews_reviewrequest',
                    'reviews_reviewrequest_target_groups',
                },
                'annotations': {'__count': Count('*')},
                'where': (Q(target_groups__id=3) &
                          Q(public=True) &
                          Q(status='P')),
            },
            {
                'model': ReviewRequest,
                'num_joins': 1,
                'tables': {
                    'reviews_reviewrequest',
                    'reviews_reviewrequest_target_groups',
                },
                'annotations': {'__count': Count('*')},
                'where': (Q(target_groups__id=4) &
                          Q(public=True) &
                          Q(status='P')),
            },
            {
                'model': ReviewRequest,
                'num_joins': 1,
                'tables': {
                    'reviews_reviewrequest',
                    'reviews_reviewrequest_target_groups',
                },
                'annotations': {'__count': Count('*')},
                'where': (Q(target_groups__id=5) &
                          Q(public=True) &
                          Q(status='P')),
            },
            {
                'model': ReviewRequest,
                'num_joins': 1,
                'tables': {
                    'reviews_reviewrequest',
                    'reviews_reviewrequest_target_groups',
                },
                'annotations': {'__count': Count('*')},
                'where': (Q(target_groups__id=6) &
                          Q(public=True) &
                          Q(status='P')),
            },
            {
                'model': ReviewRequest,
                'num_joins': 1,
                'tables': {
                    'reviews_reviewrequest',
                    'reviews_reviewrequest_target_groups',
                },
                'annotations': {'__count': Count('*')},
                'where': (Q(target_groups__id=7) &
                          Q(public=True) &
                          Q(status='P')),
            },
            {
                'model': ReviewRequest,
                'num_joins': 1,
                'tables': {
                    'reviews_reviewrequest',
                    'reviews_reviewrequest_target_groups',
                },
                'annotations': {'__count': Count('*')},
                'where': (Q(target_groups__id=8) &
                          Q(public=True) &
                          Q(status='P')),
            },
            {
                'model': ReviewRequest,
                'num_joins': 1,
                'tables': {
                    'reviews_reviewrequest',
                    'reviews_reviewrequest_target_groups',
                },
                'annotations': {'__count': Count('*')},
                'where': (Q(target_groups__id=9) &
                          Q(public=True) &
                          Q(status='P')),
            },
            {
                'model': ReviewRequest,
                'num_joins': 1,
                'tables': {
                    'reviews_reviewrequest',
                    'reviews_reviewrequest_target_groups',
                },
                'annotations': {'__count': Count('*')},
                'where': (Q(target_groups__id=10) &
                          Q(public=True) &
                          Q(status='P')),
            },
        ]

        with self.assertQueries(queries):
            response = self.client.get('/groups/')

        self.assertEqual(response.status_code, 200)

        datagrid = self._get_context_var(response, 'datagrid')
        self.assertTrue(datagrid)
        self.assertEqual(len(datagrid.rows), 10)
        self.assertEqual(datagrid.rows[0]['object'].name, 'group-1')
        self.assertEqual(datagrid.rows[1]['object'].name, 'group-2')
        self.assertEqual(datagrid.rows[2]['object'].name, 'group-3')
        self.assertEqual(datagrid.rows[3]['object'].name, 'group-4')
        self.assertEqual(datagrid.rows[4]['object'].name, 'group-5')
        self.assertEqual(datagrid.rows[5]['object'].name, 'group-6')
        self.assertEqual(datagrid.rows[6]['object'].name, 'group-7')
        self.assertEqual(datagrid.rows[7]['object'].name, 'group-8')
        self.assertEqual(datagrid.rows[8]['object'].name, 'group-9')
        self.assertEqual(datagrid.rows[9]['object'].name, 'group-a')

    @add_fixtures(['test_users'])
    def test_as_anonymous_and_redirect(self):
        """Testing group_list view with site-wide login enabled"""
        with self.siteconfig_settings({'auth_require_sitewide_login': True},
                                      reload_settings=False):
            response = self.client.get('/groups/')

        self.assertEqual(response.status_code, 302)


class UsersDataGridTests(BaseViewTestCase):
    """Unit tests for the users view."""

    fixtures = ['test_users']

    def tearDown(self):
        super(UsersDataGridTests, self).tearDown()

        cache.clear()

    @classmethod
    def setUpClass(cls):
        super(UsersDataGridTests, cls).setUpClass()

        cache.clear()

    def test_all_profiles_public(self):
        """Testing UsersDataGrid when all user profiles are public"""
        Profile.objects.create(user_id=3)
        self.client.login(username='doc', password='doc')
        self._prefetch_cached()

        user = User.objects.get(username='doc')
        profile = user.get_profile()

        # 6 queries:
        #
        # 1. Fetch logged-in user
        # 2. Fetch logged-in user's profile
        # 3. Set profile's sort_submitter_columns and submitter_columns
        # 4. Fetch total number of users for datagrid
        # 5. Fetch IDs of users for datagrid
        # 6. Fetch users + profiles from IDs
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
                'type': 'UPDATE',
                'model': Profile,
                'where': Q(pk=profile.pk),
            },
            {
                'model': User,
                'annotations': {'__count': Count('*')},
            },
            {
                'model': User,
                'distinct': True,
                'values_select': ('pk',),
                'where': Q(is_active=True),
                'order_by': ('username',),
                'limit': 4,
            },
            {
                'model': User,
                'select_related': ('profile',),
                'where': Q(pk__in=[1, 2, 3, 4]),
            },
        ]

        with self.assertQueries(queries):
            response = self.client.get('/users/?columns=fullname')

        self.assertEqual(response.status_code, 200)
        datagrid = self._get_context_var(response, 'datagrid')
        self.assertIsNotNone(datagrid)

        self.assertEqual(len(datagrid.rows), 4)

        for row in datagrid.rows:
            user = row['object']
            self.assertInHTML('<a href="/users/%s/">%s</a>'
                              % (user.username, user.get_full_name()),
                              row['cells'][0])

    def test_all_profiles_public_anonymous(self):
        """Testing UsersDataGrid when all user profiles are public and
        the user is anonymous
        """
        Profile.objects.create(user_id=3)
        self.client.logout()
        self._prefetch_cached()

        # 3 queries:
        #
        # 1. Fetch total number of users for datagrid
        # 2. Fetch IDs of users for datagrid
        # 3. Fetch users + profiles from IDs
        queries = [
            {
                'model': User,
                'annotations': {'__count': Count('*')},
            },
            {
                'model': User,
                'distinct': True,
                'values_select': ('pk',),
                'where': Q(is_active=True),
                'order_by': ('username',),
                'limit': 4,
            },
            {
                'model': User,
                'select_related': ('profile',),
                'where': Q(pk__in=[1, 2, 3, 4]),
            },
        ]

        with self.assertQueries(queries):
            response = self.client.get('/users/?columns=fullname')

        self.assertEqual(response.status_code, 200)
        datagrid = self._get_context_var(response, 'datagrid')
        self.assertIsNotNone(datagrid)

        self.assertEqual(len(datagrid.rows), 4)

        for row in datagrid.rows:
            user = row['object']
            self.assertInHTML('<a href="/users/%s/"></a>' % user.username,
                              row['cells'][0])

    def test_profile_not_exists(self):
        """Testing UsersDataGrid when a profile does not exist"""
        Profile.objects.all().update(is_private=True)
        self.client.login(username='doc', password='doc')
        self._prefetch_cached()

        user = User.objects.get(username='doc')
        profile = user.get_profile()

        dopey = User.objects.get(username='dopey')

        # 10 queries:
        #
        # 1. Fetch logged-in user
        # 2. Fetch logged-in user's profile
        # 3. Set profile's sort_submitter_columns and submitter_columns
        # 4. Fetch total number of users for datagrid
        # 5. Fetch IDs of users for datagrid
        # 6. Fetch users + profiles from IDs
        # 7. Attempt to fetch missing profile for user ID 3 (dopey)
        # 8. Create savepoint
        # 9. Create profile for user ID 3 (dopey)
        # 10. Release savepoint
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
                'type': 'UPDATE',
                'model': Profile,
                'where': Q(pk=profile.pk),
            },
            {
                'model': User,
                'annotations': {'__count': Count('*')},
            },
            {
                'model': User,
                'distinct': True,
                'values_select': ('pk',),
                'where': Q(is_active=True),
                'order_by': ('username',),
                'limit': 4,
            },
            {
                'model': User,
                'select_related': ('profile',),
                'where': Q(pk__in=[1, 2, 3, 4]),
            },
            {
                'model': Profile,
                'where': Q(user=dopey),
            },
            {
                'type': 'INSERT',
                'model': Profile,
            },
        ]

        with self.assertQueries(queries, num_statements=10):
            response = self.client.get('/users/?columns=fullname')

        self.assertEqual(response.status_code, 200)

        datagrid = self._get_context_var(response, 'datagrid')
        self.assertIsNotNone(datagrid)

        self.assertEqual(len(datagrid.rows), 4)

        rows_by_username = {
            row['object'].username: row
            for row in datagrid.rows
        }

        self.assertInHTML('<a href="/users/admin/"></a>',
                          rows_by_username['admin']['cells'][0])
        self.assertInHTML('<a href="/users/doc/">Doc Dwarf</a>',
                          rows_by_username['doc']['cells'][0])
        self.assertInHTML('<a href="/users/dopey/">Dopey Dwarf</a>',
                          rows_by_username['dopey']['cells'][0])
        self.assertInHTML('<a href="/users/grumpy/"></a>',
                          rows_by_username['grumpy']['cells'][0])

    def test_all_profiles_private(self):
        """Testing UsersDataGrid when all user profiles are private"""
        Profile.objects.create(user_id=3)
        Profile.objects.all().update(is_private=True)

        self.client.login(username='doc', password='doc')

        user = User.objects.get(username='doc')
        profile = user.get_profile()

        self._prefetch_cached()

        # 6 queries:
        #
        # 1. Fetch logged-in user
        # 2. Fetch logged-in user's profile
        # 3. Set profile's sort_submitter_columns and submitter_columns
        # 4. Fetch total number of users for datagrid
        # 5. Fetch IDs of users for datagrid
        # 6. Fetch users + profiles from IDs
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
                'type': 'UPDATE',
                'model': Profile,
                'where': Q(pk=profile.pk),
            },
            {
                'model': User,
                'annotations': {'__count': Count('*')},
            },
            {
                'model': User,
                'distinct': True,
                'values_select': ('pk',),
                'where': Q(is_active=True),
                'order_by': ('username',),
                'limit': 4,
            },
            {
                'model': User,
                'select_related': ('profile',),
                'where': Q(pk__in=[1, 2, 3, 4]),
            },
        ]

        with self.assertQueries(queries):
            response = self.client.get('/users/?columns=fullname')

        self.assertEqual(response.status_code, 200)

        datagrid = self._get_context_var(response, 'datagrid')
        self.assertIsNotNone(datagrid)

        self.assertEqual(len(datagrid.rows), 4)

        rows_by_username = {
            row['object'].username: row
            for row in datagrid.rows
        }

        self.assertInHTML('<a href="/users/admin/"></a>',
                          rows_by_username['admin']['cells'][0])
        self.assertInHTML('<a href="/users/doc/">Doc Dwarf</a>',
                          rows_by_username['doc']['cells'][0])
        self.assertInHTML('<a href="/users/dopey/"></a>',
                          rows_by_username['dopey']['cells'][0])
        self.assertInHTML('<a href="/users/grumpy/"></a>',
                          rows_by_username['grumpy']['cells'][0])

    def test_all_profiles_private_anonymous(self):
        """Testing UsersDataGrid when all users profiles are private and the
        user is anonymous
        """
        Profile.objects.create(user_id=3)
        Profile.objects.all().update(is_private=True)
        self.client.logout()
        self._prefetch_cached()

        # 3 queries:
        #
        # 1. Fetch total number of users for datagrid
        # 2. Fetch IDs of users for datagrid
        # 3. Fetch users + profiles from IDs
        queries = [
            {
                'model': User,
                'annotations': {'__count': Count('*')},
            },
            {
                'model': User,
                'distinct': True,
                'values_select': ('pk',),
                'where': Q(is_active=True),
                'order_by': ('username',),
                'limit': 4,
            },
            {
                'model': User,
                'select_related': ('profile',),
                'where': Q(pk__in=[1, 2, 3, 4]),
            },
        ]

        with self.assertQueries(queries):
            response = self.client.get('/users/?columns=fullname')

        self.assertEqual(response.status_code, 200)
        datagrid = self._get_context_var(response, 'datagrid')
        self.assertIsNotNone(datagrid)

        self.assertEqual(len(datagrid.rows), 4)

        for row in datagrid.rows:
            user = row['object']
            self.assertInHTML('<a href="/users/%s/"></a>' % user.username,
                              row['cells'][0])

    def test_all_profiles_private_admin(self):
        """Testing UsersDataGrid when all users profiles are private and the
        user is an admin
        """
        Profile.objects.create(user_id=3)
        Profile.objects.all().update(is_private=True)
        self.client.login(username='admin', password='admin')
        self._prefetch_cached()

        user = User.objects.get(username='admin')
        profile = user.get_profile()

        # 6 queries:
        #
        # 1. Fetch logged-in user
        # 2. Fetch logged-in user's profile
        # 3. Set profile's sort_submitter_columns and submitter_columns
        # 4. Fetch total number of users for datagrid
        # 5. Fetch IDs of users for datagrid
        # 6. Fetch users + profiles from IDs
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
                'type': 'UPDATE',
                'model': Profile,
                'where': Q(pk=profile.pk),
            },
            {
                'model': User,
                'annotations': {'__count': Count('*')},
            },
            {
                'model': User,
                'distinct': True,
                'values_select': ('pk',),
                'where': Q(is_active=True),
                'order_by': ('username',),
                'limit': 4,
            },
            {
                'model': User,
                'select_related': ('profile',),
                'where': Q(pk__in=[1, 2, 3, 4]),
            },
        ]

        with self.assertQueries(queries):
            response = self.client.get('/users/?columns=fullname')

        self.assertEqual(response.status_code, 200)
        datagrid = self._get_context_var(response, 'datagrid')
        self.assertIsNotNone(datagrid)

        self.assertEqual(len(datagrid.rows), 4)

        for row in datagrid.rows:
            user = row['object']
            self.assertInHTML('<a href="/users/%s/">%s</a>'
                              % (user.username, user.get_full_name()),
                              row['cells'][0])

    @add_fixtures(['test_site'])
    def test_all_profile_private_local_site_admin(self):
        """Testing UsersDataGrid when all profiles are private for a LocalSite
        admin
        """
        Profile.objects.create(user_id=3)
        Profile.objects.all().update(is_private=True)
        self.client.login(username='doc', password='doc')
        self._prefetch_cached()

        user = User.objects.get(username='doc')
        profile = user.get_profile()

        # 6 queries:
        #
        # 1. Fetch logged-in user
        # 2. Fetch logged-in user's profile
        # 3. Set profile's sort_submitter_columns and submitter_columns
        # 4. Fetch total number of users for datagrid
        # 5. Fetch IDs of users for datagrid
        # 6. Fetch users + profiles from IDs
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
                'type': 'UPDATE',
                'model': Profile,
                'where': Q(pk=profile.pk),
            },
            {
                'model': User,
                'annotations': {'__count': Count('*')},
            },
            {
                'model': User,
                'values_select': ('pk',),
                'where': Q(is_active=True),
                'order_by': ('username',),
                'distinct': True,
                'limit': 4,
            },
            {
                'model': User,
                'select_related': ('profile',),
                'where': Q(pk__in=[1, 2, 3, 4]),
            },
        ]

        with self.assertQueries(queries):
            response = self.client.get('/users/?columns=fullname')

        self.assertEqual(response.status_code, 200)
        datagrid = self._get_context_var(response, 'datagrid')
        self.assertIsNotNone(datagrid)

        self.assertEqual(len(datagrid.rows), 4)

        rows_by_username = {
            row['object'].username: row
            for row in datagrid.rows
        }

        self.assertInHTML('<a href="/users/admin/">Admin User</a>',
                          rows_by_username['admin']['cells'][0])
        self.assertInHTML('<a href="/users/doc/">Doc Dwarf</a>',
                          rows_by_username['doc']['cells'][0])
        self.assertInHTML('<a href="/users/dopey/"></a>',
                          rows_by_username['dopey']['cells'][0])
        self.assertInHTML('<a href="/users/grumpy/"></a>',
                          rows_by_username['grumpy']['cells'][0])

    @add_fixtures(['test_site'])
    def test_all_profile_private_local_site_admin_local_site(self):
        """Testing UsersDataGrid when all profiles are private for a LocalSite
        admin on a LocalSite
        """
        dopey = User.objects.get(username='dopey')
        Profile.objects.create(user=dopey)
        Profile.objects.all().update(is_private=True)

        local_site = LocalSite.objects.get(name='local-site-2')

        self.client.login(username='doc', password='doc')
        self._prefetch_cached(local_site=local_site)

        user = User.objects.get(username='doc')
        profile = user.get_profile()

        # 8 queries:
        #
        # 1. Fetch logged-in user
        # 2. Fetch logged-in user's profile
        # 3. Fetch LocalSite
        # 4. Check LocalSite membership
        # 5. Set profile's sort_submitter_columns and submitter_columns
        # 6. Fetch total number of users for datagrid
        # 7. Fetch IDs of users for datagrid
        # 8. Fetch users + profiles from IDs
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
                'model': LocalSite,
                'where': Q(name='local-site-2'),
            },
            {
                'model': User,
                'num_joins': 1,
                'tables': {
                    'auth_user',
                    'site_localsite_users',
                },
                'where': Q(local_site__id=local_site.pk) & Q(pk=user.pk),
                'extra': {
                    'a': ('1', []),
                },
                'limit': 1,
            },
            {
                'type': 'UPDATE',
                'model': Profile,
                'where': Q(pk=profile.pk),
            },
            {
                'model': User,
                'annotations': {'__count': Count('*')},
            },
            {
                'model': User,
                'num_joins': 1,
                'tables': {
                    'auth_user',
                    'site_localsite_users',
                },
                'values_select': ('pk',),
                'where': Q(local_site=local_site) & Q(is_active=True),
                'order_by': ('username',),
                'distinct': True,
                'limit': 2,
            },
            {
                'model': User,
                'select_related': ('profile',),
                'where': Q(pk__in=[1, 2]),
            },
        ]

        with self.assertQueries(queries):
            response = self.client.get(
                '/s/local-site-2/users/?columns=fullname')

        self.assertEqual(response.status_code, 200)
        datagrid = self._get_context_var(response, 'datagrid')
        self.assertIsNotNone(datagrid)

        self.assertEqual(len(datagrid.rows), 2)

        for row in datagrid.rows:
            user = row['object']
            self.assertInHTML('<a href="/s/local-site-2/users/%s/">%s</a>'
                              % (user.username, user.get_full_name()),
                              row['cells'][0])


class SubmitterListViewTests(BaseViewTestCase):
    """Unit tests for the users_list view."""

    def test_with_access(self):
        """Testing users_list view"""
        users = [
            self.create_user(username='test-user-%s' % (i + 1))
            for i in range(5)
        ]

        # 28 queries:
        #
        # 1. Fetch total result count
        # 2. Fetch the IDs for a page worth of results
        # 3. Fetch data for IDs
        # 4. Attempt to fetch profile for user ID 1
        # 5. Create savepoint
        # 6. Create profile for user ID 1
        # 7. Release savepoint
        # 8. Fetch number of review requests for user ID 1
        # 9. Attempt to fetch profile for user ID 2
        # 10. Create savepoint
        # 11. Create profile for user ID 2
        # 12. Release savepoint
        # 13. Fetch number of review requests for user ID 2
        # 14. Attempt to fetch profile for user ID 3
        # 15. Create savepoint
        # 16. Create profile for user ID 3
        # 17. Release savepoint
        # 18. Fetch number of review requests for user ID 3
        # 19. Attempt to fetch profile for user ID 5
        # 20. Create savepoint
        # 21. Create profile for user ID 4
        # 22. Release savepoint
        # 23. Fetch number of review requests for user ID 4
        # 24. Attempt to fetch profile for user ID 5
        # 25. Create savepoint
        # 26. Create profile for user ID 5
        # 27. Release savepoint
        # 28. Fetch number of review requests for user ID 5
        queries = [
            {
                'model': User,
                'annotations': {'__count': Count('*')},
            },
            {
                'model': User,
                'values_select': ('pk',),
                'order_by': ('username',),
                'where': Q(is_active=True),
                'distinct': True,
                'limit': 5,
            },
            {
                'model': User,
                'select_related': {'profile'},
                'where': Q(pk__in=[1, 2, 3, 4, 5]),
            },
            {
                'model': Profile,
                'where': Q(user=users[0]),
            },
            {
                'type': 'INSERT',
                'model': Profile,
            },
            {
                'model': ReviewRequest,
                'num_joins': 1,
                'tables': {
                    'reviews_reviewrequest',
                    'reviews_reviewrequest_target_people',
                },
                'annotations': {'__count': Count('*')},
                'where': (Q(target_people__id=1) &
                          Q(public=True) &
                          Q(status='P')),
            },
            {
                'model': Profile,
                'where': Q(user=users[1]),
            },
            {
                'type': 'INSERT',
                'model': Profile,
            },
            {
                'model': ReviewRequest,
                'num_joins': 1,
                'tables': {
                    'reviews_reviewrequest',
                    'reviews_reviewrequest_target_people',
                },
                'annotations': {'__count': Count('*')},
                'where': (Q(target_people__id=2) &
                          Q(public=True) &
                          Q(status='P')),
            },
            {
                'model': Profile,
                'where': Q(user=users[2]),
            },
            {
                'type': 'INSERT',
                'model': Profile,
            },
            {
                'model': ReviewRequest,
                'num_joins': 1,
                'tables': {
                    'reviews_reviewrequest',
                    'reviews_reviewrequest_target_people',
                },
                'annotations': {'__count': Count('*')},
                'where': (Q(target_people__id=3) &
                          Q(public=True) &
                          Q(status='P')),
            },
            {
                'model': Profile,
                'where': Q(user=users[3]),
            },
            {
                'type': 'INSERT',
                'model': Profile,
            },
            {
                'model': ReviewRequest,
                'num_joins': 1,
                'tables': {
                    'reviews_reviewrequest',
                    'reviews_reviewrequest_target_people',
                },
                'annotations': {'__count': Count('*')},
                'where': (Q(target_people__id=4) &
                          Q(public=True) &
                          Q(status='P')),
            },
            {
                'model': Profile,
                'where': Q(user=users[4]),
            },
            {
                'type': 'INSERT',
                'model': Profile,
            },
            {
                'model': ReviewRequest,
                'num_joins': 1,
                'tables': {
                    'reviews_reviewrequest',
                    'reviews_reviewrequest_target_people',
                },
                'annotations': {'__count': Count('*')},
                'where': (Q(target_people__id=5) &
                          Q(public=True) &
                          Q(status='P')),
            },
        ]

        with self.assertQueries(queries, num_statements=28):
            response = self.client.get('/users/')

        self.assertEqual(response.status_code, 200)

        datagrid = self._get_context_var(response, 'datagrid')
        self.assertTrue(datagrid)
        self.assertEqual(len(datagrid.rows), 5)
        self.assertEqual(datagrid.rows[0]['object'].username, 'test-user-1')
        self.assertEqual(datagrid.rows[1]['object'].username, 'test-user-2')
        self.assertEqual(datagrid.rows[2]['object'].username, 'test-user-3')
        self.assertEqual(datagrid.rows[3]['object'].username, 'test-user-4')
        self.assertEqual(datagrid.rows[4]['object'].username, 'test-user-5')

    def test_with_access_with_letter(self):
        """Testing users_list view with ?letter="""
        users = [
            self.create_user(username='aa'),
            self.create_user(username='ab'),
            self.create_user(username='ac'),
            self.create_user(username='da'),
            self.create_user(username='db'),
        ]

        # 18 queries:
        #
        # 1. Fetch total result count
        # 2. Fetch the IDs for a page worth of results
        # 3. Fetch data for IDs
        # 4. Attempt to fetch profile for user ID 1
        # 5. Create savepoint
        # 6. Create profile for user ID 1
        # 7. Release savepoint
        # 8. Fetch number of review requests for user ID 1
        # 9. Attempt to fetch profile for user ID 2
        # 10. Create savepoint
        # 11. Create profile for user ID 2
        # 12. Release savepoint
        # 13. Fetch number of review requests for user ID 2
        # 14. Attempt to fetch profile for user ID 3
        # 15. Create savepoint
        # 16. Create profile for user ID 3
        # 17. Release savepoint
        # 18. Fetch number of review requests for user ID 3
        queries = [
            {
                'model': User,
                'annotations': {'__count': Count('*')},
            },
            {
                'model': User,
                'values_select': ('pk',),
                'order_by': ('username',),
                'where': (Q(username__istartswith='A') &
                          Q(is_active=True)),
                'distinct': True,
                'limit': 3,
            },
            {
                'model': User,
                'select_related': {'profile'},
                'where': Q(pk__in=[1, 2, 3]),
            },
            {
                'model': Profile,
                'where': Q(user=users[0]),
            },
            {
                'type': 'INSERT',
                'model': Profile,
            },
            {
                'model': ReviewRequest,
                'num_joins': 1,
                'tables': {
                    'reviews_reviewrequest',
                    'reviews_reviewrequest_target_people',
                },
                'annotations': {'__count': Count('*')},
                'where': (Q(target_people__id=1) &
                          Q(public=True) &
                          Q(status='P')),
            },
            {
                'model': Profile,
                'where': Q(user=users[1]),
            },
            {
                'type': 'INSERT',
                'model': Profile,
            },
            {
                'model': ReviewRequest,
                'num_joins': 1,
                'tables': {
                    'reviews_reviewrequest',
                    'reviews_reviewrequest_target_people',
                },
                'annotations': {'__count': Count('*')},
                'where': (Q(target_people__id=2) &
                          Q(public=True) &
                          Q(status='P')),
            },
            {
                'model': Profile,
                'where': Q(user=users[2]),
            },
            {
                'type': 'INSERT',
                'model': Profile,
            },
            {
                'model': ReviewRequest,
                'num_joins': 1,
                'tables': {
                    'reviews_reviewrequest',
                    'reviews_reviewrequest_target_people',
                },
                'annotations': {'__count': Count('*')},
                'where': (Q(target_people__id=3) &
                          Q(public=True) &
                          Q(status='P')),
            },
        ]

        with self.assertQueries(queries, num_statements=18):
            response = self.client.get('/users/?letter=A')

        self.assertEqual(response.status_code, 200)

        datagrid = self._get_context_var(response, 'datagrid')
        self.assertTrue(datagrid)
        self.assertEqual(len(datagrid.rows), 3)
        self.assertEqual(datagrid.rows[0]['object'].username, 'aa')
        self.assertEqual(datagrid.rows[1]['object'].username, 'ab')
        self.assertEqual(datagrid.rows[2]['object'].username, 'ac')

    @add_fixtures(['test_users'])
    def test_as_anonymous_and_redirect(self):
        """Testing users_list view as anonymous with anonymous
        access disabled
        """
        with self.siteconfig_settings({'auth_require_sitewide_login': True},
                                      reload_settings=False):
            response = self.client.get('/users/')

        self.assertEqual(response.status_code, 302)


class SubmitterViewTests(BaseViewTestCase):
    """Unit tests for the submitter view."""

    @add_fixtures(['test_users'])
    def test_with_private_review_requests(self):
        """Testing submitter view with private review requests"""
        ReviewRequest.objects.all().delete()

        user = User.objects.get(username='grumpy')
        user.review_groups.clear()

        group1 = Group.objects.create(name='test-group-1')
        group1.users.add(user)

        group2 = Group.objects.create(name='test-group-2', invite_only=True)
        group2.users.add(user)

        review_requests = []

        for i in range(5):
            review_request = self.create_review_request(
                summary='Summary %s' % (i + 1),
                submitter=user,
                publish=True)

            review_requests.append(review_request)

            if i >= 3:
                review_request.target_groups.add(group2)

        # 6 queries:
        #
        # 1. Fetch user
        # 2. Fetch groups accessible by user
        # 3. Fetch total review request count
        # 4. Fetch IDs of page of review requests
        # 5. Fetch data for review requests
        # 6. Fetch user's profile.
        queries = [
            {
                'model': User,
                'where': Q(username='grumpy'),
            },
            {
                'model': Group,
                'num_joins': 1,
                'tables': {
                    'reviews_group',
                    'reviews_group_users',
                },
                'where': (Q(users__id=4) &
                          Q(Q(invite_only=False) &
                            Q(visible=True) &
                            Q(local_site=None)) &
                          Q(local_site=None)),
                'distinct': True,
                'order_by': ('name',),
            },
            {
                'model': ReviewRequest,
                'annotations': {'__count': Count('*')},
            },
            {
                'model': ReviewRequest,
                'num_joins': 4,
                'tables': {
                    'auth_user',
                    'reviews_group',
                    'reviews_reviewrequest',
                    'reviews_reviewrequest_target_groups',
                    'scmtools_repository',
                },
                'values_select': ('pk',),
                'where': (Q(Q(public=True) &
                            Q(local_site=None) &
                            Q(submitter__username='grumpy') &
                            Q(Q(repository=None) |
                              Q(repository__public=True)) &
                            Q(Q(target_groups=None) |
                              Q(target_groups__invite_only=False))) &
                          Q(local_site=None)),
                'distinct': True,
                'order_by': ('-last_updated',),
                'limit': 3,
            },
            {
                'model': ReviewRequest,
                'select_related': {'submitter'},
                'where': Q(pk__in=[3, 2, 1]),
            },
            {
                'model': Profile,
                'where': Q(user=user),
            },
        ]

        with self.assertQueries(queries):
            response = self.client.get('/users/grumpy/')

        self.assertEqual(response.status_code, 200)

        datagrid = self._get_context_var(response, 'datagrid')
        self.assertIsNotNone(datagrid)
        self.assertEqual(len(datagrid.rows), 3)
        self.assertEqual(datagrid.rows[0]['object'].summary, 'Summary 3')
        self.assertEqual(datagrid.rows[1]['object'].summary, 'Summary 2')
        self.assertEqual(datagrid.rows[2]['object'].summary, 'Summary 1')

    @add_fixtures(['test_users'])
    def test_sidebar(self):
        """Testing submitter view sidebar"""
        user = User.objects.get(username='grumpy')
        user.review_groups.clear()

        group1 = Group.objects.create(name='test-group-1')
        group1.users.add(user)

        group2 = Group.objects.create(name='test-group-2', invite_only=True)
        group2.users.add(user)

        # Now load the page and get the sidebar items.
        response = self.client.get('/users/grumpy/')
        self.assertEqual(response.status_code, 200)

        datagrid = self._get_context_var(response, 'datagrid')
        self.assertIsNotNone(datagrid)

        sidebar_items = \
            self._get_context_var(response, 'datagrid').sidebar_items
        self.assertEqual(len(sidebar_items), 2)

        # Test the User Profile section.
        section = sidebar_items[0]
        self.assertIsInstance(section, UserProfileItem)

        # Test the Groups section.
        section = sidebar_items[1]
        self.assertIsInstance(section, UserGroupsItem)
        self.assertEqual(str(section.label), 'Groups')
        self.assertEqual(len(section.items), 1)
        self.assertEqual(str(section.items[0].label),
                         'test-group-1')

    def test_match_url_with_email_address(self):
        """Testing submitter view URL matching with e-mail address
        as username
        """
        # Test if this throws an exception. Bug #1250
        reverse('user', args=['user@example.com'])

    @add_fixtures(['test_users'])
    def test_with_private_reviews(self):
        """Testing reviews page of submitter view with private reviews"""
        ReviewRequest.objects.all().delete()
        Review.objects.all().delete()

        user1 = User.objects.get(username='doc')
        user2 = User.objects.get(username='grumpy')

        user1.review_groups.clear()
        user2.review_groups.clear()

        group = Group.objects.create(name='test-group', invite_only=True)
        group.users.add(user1, user2)

        review_request1 = self.create_review_request(summary='Summary 1',
                                                     submitter=user1,
                                                     publish=True)
        review_request2 = self.create_review_request(summary='Summary 2',
                                                     submitter=user1,
                                                     publish=True)
        review_request2.target_groups.add(group)

        reviews = [
            self.create_review(review_request1,
                               user=user2,
                               publish=True)
            for i in range(5)
        ] + [
            self.create_review(review_request2,
                               user=user2,
                               publish=True)
            for i in range(5)
        ]

        # 6 queries:
        #
        # 1. Fetch user
        # 2. Fetch groups accessible by user
        # 3. Fetch total review count
        # 4. Fetch IDs of page of reviews
        # 5. Fetch data for reviews
        # 6. Fetch user's profile.
        queries = [
            {
                'model': User,
                'where': Q(username='grumpy'),
            },
            {
                'model': Group,
                'num_joins': 1,
                'tables': {
                    'reviews_group',
                    'reviews_group_users',
                },
                'where': (Q(users__id=4) &
                          Q(Q(invite_only=False) &
                            Q(visible=True) &
                            Q(local_site=None)) &
                          Q(local_site=None)),
                'distinct': True,
                'order_by': ('name',),
            },
            {
                'model': Review,
                'annotations': {'__count': Count('*')},
            },
            {
                'model': Review,
                'num_joins': 5,
                'tables': {
                    'auth_user',
                    'reviews_group',
                    'reviews_review',
                    'reviews_reviewrequest',
                    'reviews_reviewrequest_target_groups',
                    'scmtools_repository',
                },
                'values_select': ('pk',),
                'where': (
                    Q(Q(base_reply_to=None) &
                      Q(review_request__local_site=None) &
                      Q(user__username='grumpy') &
                      Q(Q(review_request__repository=None) |
                        Q(review_request__repository__public=True)) &
                      Q(Q(review_request__target_groups=None) |
                        Q(review_request__target_groups__invite_only=False)) &
                      Q(public=True)) &
                    Q(review_request__local_site=None)
                ),
                'distinct': True,
                'order_by': ('-timestamp',),
                'limit': 5,
            },
            {
                'model': Review,
                'select_related': {'review_request'},
                'where': Q(pk__in=[5, 4, 3, 2, 1]),
            },
            {
                'model': Profile,
                'where': Q(user=user2),
            },
        ]

        with self.assertQueries(queries):
            response = self.client.get('/users/grumpy/reviews/')

        self.assertEqual(response.status_code, 200)

        datagrid = self._get_context_var(response, 'datagrid')
        self.assertIsNotNone(datagrid)
        self.assertEqual(len(datagrid.rows), 5)
        self.assertEqual(datagrid.rows[0]['object'], reviews[4])
        self.assertEqual(datagrid.rows[1]['object'], reviews[3])
        self.assertEqual(datagrid.rows[2]['object'], reviews[2])
        self.assertEqual(datagrid.rows[3]['object'], reviews[1])
        self.assertEqual(datagrid.rows[4]['object'], reviews[0])


class FullNameColumnTests(BaseColumnTestCase):
    """Testing reviewboard.datagrids.columns.FullNameColumn."""

    column = FullNameColumn()

    def test_render_anonymous(self):
        """Testing FullNameColumn.render_data when the viewing user is
        anonymous
        """
        user = User.objects.get(username='grumpy')
        self.request.user = AnonymousUser()

        self.assertEqual(
            self.column.render_data(self.stateful_column, user),
            '')

    def test_render_public(self):
        """Testing FullNameColumn.render_data for a user with a public
        profile
        """
        user = User.objects.get(username='grumpy')

        self.assertEqual(
            self.column.render_data(self.stateful_column, user),
            user.get_full_name())

    def test_render_private(self):
        """Testing FullNameColumn.render_data for a user with a private
        profile
        """
        user = User.objects.get(username='grumpy')

        profile = user.get_profile()
        profile.is_private = True
        profile.save(update_fields=('is_private',))

        self.assertEqual(
            self.column.render_data(self.stateful_column, user),
            '')

    def test_render_private_admin(self):
        """Testing FullNameColumn.render_data for a user with a private
        profile viewed by an admin
        """
        user = User.objects.get(username='grumpy')

        profile = user.get_profile()
        profile.is_private = True
        profile.save(update_fields=('is_private',))

        self.request.user = User.objects.get(username='admin')

        self.assertEqual(
            self.column.render_data(self.stateful_column, user),
            user.get_full_name())

    @add_fixtures(['test_site'])
    def test_render_private_localsite(self):
        """Testing FullNameColumn.render_data for a user with a private
        profile viewed by a fellow LocalSite member
        """
        user = User.objects.get(username='grumpy')

        profile = user.get_profile()
        profile.is_private = True
        profile.save(update_fields=('is_private',))

        site = LocalSite.objects.get(name='local-site-1')
        site.users.add(user)

        self.assertEqual(
            self.column.render_data(self.stateful_column, user),
            '')

    @add_fixtures(['test_site'])
    def test_render_private_localsite_admin(self):
        """Testing FullNameColumn.render_data for a user with a private
        profile viewed by a LocalSite admin
        """
        user = User.objects.get(username='admin')

        profile = user.get_profile()
        profile.is_private = True
        profile.save(update_fields=('is_private',))

        self.assertEqual(
            self.column.render_data(self.stateful_column, user),
            user.get_full_name())

    @add_fixtures(['test_site'])
    def test_render_private_localsite_admin_other_site(self):
        """Testing FullNameColumn.render_data for a user with a private
        profile viewed by an admin of a LocalSite of which they are not a
        member
        """
        user = User.objects.get(username='grumpy')

        profile = user.get_profile()
        profile.is_private = True
        profile.save(update_fields=('is_private',))

        site = LocalSite.objects.create(name='local-site-3')
        site.users.add(user)
        site.users.add(self.request.user)

        self.assertEqual(
            self.column.render_data(self.stateful_column, user),
            '')

    def test_render_data_escapes_name(self):
        """Testing FullNameColumn.render_data escapes the full name"""
        user = User.objects.get(username='grumpy')
        user.first_name = '<script>alert("unsafe")</script>'
        user.last_name = '""'
        user.save(update_fields=('first_name', 'last_name'))

        rendered = self.column.render_data(self.stateful_column, user)

        self.assertIsInstance(rendered, SafeText)
        self.assertEqual(rendered,
                         '&lt;script&gt;alert(&quot;unsafe&quot;)'
                         '&lt;/script&gt; &quot;&quot;')


class ShipItColumnTests(BaseColumnTestCase):
    """Testing reviewboard.datagrids.columns.ShipItColumn."""

    column = ShipItColumn()

    def test_render_data_with_none(self):
        """Testing ShipItColumn.render_data with 0 Ship It!'s, 0 issues"""
        review_request = self.create_review_request(publish=True)

        self.assertEqual(
            self.column.render_data(self.stateful_column, review_request),
            '')

    def test_render_data_with_one_shipit(self):
        """Testing ShipItColumn.render_data with 1 Ship It!"""
        review_request = self.create_review_request(publish=True)
        review_request.shipit_count = 1
        review_request.last_review_activity_timestamp = (
            review_request.last_updated + timedelta(hours=1))

        self.assertHTMLEqual(
            self.column.render_data(self.stateful_column, review_request),
            '<div class="shipit-count-container"'
            '     title="1 Ship It!"'
            '     aria-label="1 Ship It!">'
            ' <span aria-hidden="true" class="shipit-count">'
            '  <span class="rb-icon rb-icon-datagrid-shipit"></span>'
            '  1'
            ' </span>'
            '</div>')

    def test_render_data_with_many_shipits(self):
        """Testing ShipItColumn.render_data with many Ship It!'s"""
        review_request = self.create_review_request(publish=True)
        review_request.shipit_count = 2
        review_request.last_review_activity_timestamp = (
            review_request.last_updated + timedelta(hours=1))

        self.assertHTMLEqual(
            self.column.render_data(self.stateful_column, review_request),
            '<div class="shipit-count-container"'
            '     title="2 Ship It\'s!"'
            '     aria-label="2 Ship It\'s!">'
            ' <span aria-hidden="true" class="shipit-count">'
            '  <span class="rb-icon rb-icon-datagrid-shipit"></span>'
            '  2'
            ' </span>'
            '</div>')

    def test_render_data_with_shipit_stale(self):
        """Testing ShipItColumn.render_data with Ship It!'s and stale"""
        review_request = self.create_review_request(publish=True)
        review_request.shipit_count = 1
        review_request.last_review_activity_timestamp = (
            review_request.last_updated - timedelta(hours=1))

        self.assertHTMLEqual(
            self.column.render_data(self.stateful_column, review_request),
            '<div class="shipit-count-container -is-stale"'
            '     title="1 Ship It! (New updates to review)"'
            '     aria-label="1 Ship It! (New updates to review)">'
            ' <span aria-hidden="true" class="shipit-count">'
            '  <span class="rb-icon rb-icon-datagrid-shipit"></span>'
            '  1'
            ' </span>'
            '</div>')

    def test_render_data_with_one_open_issue(self):
        """Testing ShipItColumn.render_data with one open issue"""
        review_request = self.create_review_request(publish=True)
        review_request.issue_open_count = 1
        review_request.shipit_count = 1

        self.assertHTMLEqual(
            self.column.render_data(self.stateful_column, review_request),
            '<div class="issue-count-container"'
            '     title="1 issue opened"'
            '     aria-label="1 issue opened">'
            ' <span aria-hidden="true" class="issue-count">'
            '  <span class="rb-icon rb-icon-datagrid-open-issues"></span>'
            '  1'
            ' </span>'
            '</div>')

    def test_render_data_with_many_open_issues(self):
        """Testing ShipItColumn.render_data with many open issues"""
        review_request = self.create_review_request(publish=True)
        review_request.issue_open_count = 2
        review_request.shipit_count = 1

        self.assertHTMLEqual(
            self.column.render_data(self.stateful_column, review_request),
            '<div class="issue-count-container"'
            '     title="2 issues opened"'
            '     aria-label="2 issues opened">'
            ' <span aria-hidden="true" class="issue-count">'
            '  <span class="rb-icon rb-icon-datagrid-open-issues"></span>'
            '  2'
            ' </span>'
            '</div>')

    def test_render_data_with_one_issue_pending_verification(self):
        """Testing ShipItColumn.render_data with one issue pending verification
        """
        review_request = self.create_review_request(publish=True)
        review_request.issue_verifying_count = 1
        review_request.shipit_count = 1

        self.assertHTMLEqual(
            self.column.render_data(self.stateful_column, review_request),
            '<div class="issue-count-container"'
            '     title="1 issue requiring verification"'
            '     aria-label="1 issue requiring verification">'
            ' <span aria-hidden="true" class="issue-count">'
            '  <span class="rb-icon rb-icon-datagrid-issue-verifying"></span>'
            '  1'
            ' </span>'
            '</div>')

    def test_render_data_with_many_pending_verification(self):
        """Testing ShipItColumn.render_data with many issues pending
        verification
        """
        review_request = self.create_review_request(publish=True)
        review_request.issue_verifying_count = 2
        review_request.shipit_count = 1

        self.assertHTMLEqual(
            self.column.render_data(self.stateful_column, review_request),
            '<div class="issue-count-container"'
            '     title="2 issues requiring verification"'
            '     aria-label="2 issues requiring verification">'
            ' <span aria-hidden="true" class="issue-count">'
            '  <span class="rb-icon rb-icon-datagrid-issue-verifying"></span>'
            '  2'
            ' </span>'
            '</div>')

    def test_render_data_with_one_issue_and_one_pending_verification(self):
        """Testing ShipItColumn.render_data with 1 open issue and pending
        verification
        """
        review_request = self.create_review_request(publish=True)
        review_request.issue_open_count = 1
        review_request.issue_verifying_count = 1
        review_request.shipit_count = 1

        self.assertHTMLEqual(
            self.column.render_data(self.stateful_column, review_request),
            '<div class="issue-count-container"'
            '     title="1 issue opened, 1 requiring verification"'
            '     aria-label="1 issue opened, 1 requiring verification">'
            ' <span aria-hidden="true" class="issue-count">'
            '  <span class="rb-icon rb-icon-datagrid-open-issues"></span>'
            '  1'
            ' </span>'
            ' <span aria-hidden="true" class="issue-verifying-count">'
            '  <span class="rb-icon rb-icon-datagrid-issue-verifying"></span>'
            '  1'
            ' </span>'
            '</div>')

    def test_render_data_with_many_issues_and_one_pending_verification(self):
        """Testing ShipItColumn.render_data with many open issues and 1
        pending verification
        """
        review_request = self.create_review_request(publish=True)
        review_request.issue_open_count = 5
        review_request.issue_verifying_count = 1
        review_request.shipit_count = 1

        self.assertHTMLEqual(
            self.column.render_data(self.stateful_column, review_request),
            '<div class="issue-count-container"'
            '     title="5 issues opened, 1 requiring verification"'
            '     aria-label="5 issues opened, 1 requiring verification">'
            ' <span aria-hidden="true" class="issue-count">'
            '  <span class="rb-icon rb-icon-datagrid-open-issues"></span>'
            '  5'
            ' </span>'
            ' <span aria-hidden="true" class="issue-verifying-count">'
            '  <span class="rb-icon rb-icon-datagrid-issue-verifying"></span>'
            '  1'
            ' </span>'
            '</div>')

    def test_render_data_with_many_issues_and_many_pending_verification(self):
        """Testing ShipItColumn.render_data with many open issues and many
        pending verification
        """
        review_request = self.create_review_request(publish=True)
        review_request.issue_open_count = 5
        review_request.issue_verifying_count = 3
        review_request.shipit_count = 1

        self.assertHTMLEqual(
            self.column.render_data(self.stateful_column, review_request),
            '<div class="issue-count-container"'
            '     title="5 issues opened, 3 requiring verification"'
            '     aria-label="5 issues opened, 3 requiring verification">'
            ' <span aria-hidden="true" class="issue-count">'
            '  <span class="rb-icon rb-icon-datagrid-open-issues"></span>'
            '  5'
            ' </span>'
            ' <span aria-hidden="true" class="issue-verifying-count">'
            '  <span class="rb-icon rb-icon-datagrid-issue-verifying"></span>'
            '  3'
            ' </span>'
            '</div>')


class SummaryColumnTests(BaseColumnTestCase):
    """Testing reviewboard.datagrids.columns.SummaryColumn."""

    column = SummaryColumn()

    def test_render_data(self):
        """Testing SummaryColumn.render_data"""
        review_request = self.create_review_request(summary='Summary 1',
                                                    publish=True)

        # These are generally set by the column's augment_queryset().
        review_request.draft_summary = None
        review_request.visibility = ReviewRequestVisit.VISIBLE

        self.assertEqual(
            self.column.render_data(self.stateful_column, review_request),
            '<span>Summary 1</span>')

    def test_render_data_with_draft(self):
        """Testing SummaryColumn.render_data with draft review request"""
        review_request = self.create_review_request(
            summary='Summary 1',
            submitter=self.request.user)

        # These are generally set by the column's augment_queryset().
        review_request.draft_summary = None
        review_request.visibility = ReviewRequestVisit.VISIBLE

        self.assertEqual(
            self.column.render_data(self.stateful_column, review_request),
            '<label class="label-draft">Draft</label>'
            '<span>Summary 1</span>')

    def test_render_data_with_draft_summary(self):
        """Testing SummaryColumn.render_data with draft summary"""
        review_request = self.create_review_request(
            summary='Summary 1',
            submitter=self.request.user)

        # These are generally set by the column's augment_queryset().
        review_request.draft_summary = 'Draft Summary 1'
        review_request.visibility = ReviewRequestVisit.VISIBLE

        self.assertEqual(
            self.column.render_data(self.stateful_column, review_request),
            '<label class="label-draft">Draft</label>'
            '<span>Draft Summary 1</span>')

    def test_render_data_with_draft_and_no_summary(self):
        """Testing SummaryColumn.render_data with draft and no summary"""
        review_request = self.create_review_request(
            submitter=self.request.user)

        # These are generally set by the column's augment_queryset().
        review_request.draft_summary = None
        review_request.visibility = ReviewRequestVisit.VISIBLE

        review_request.summary = None

        self.assertEqual(
            self.column.render_data(self.stateful_column, review_request),
            '<label class="label-draft">Draft</label>'
            '<span class="no-summary">No Summary</span>')

    def test_render_data_with_archived(self):
        """Testing SummaryColumn.render_data with archived review request"""
        review_request = self.create_review_request(
            summary='Summary 1',
            submitter=self.request.user,
            publish=True)

        # These are generally set by the column's augment_queryset().
        review_request.draft_summary = None
        review_request.visibility = ReviewRequestVisit.ARCHIVED

        self.assertEqual(
            self.column.render_data(self.stateful_column, review_request),
            '<label class="label-archived">Archived</label>'
            '<span>Summary 1</span>')

    def test_render_data_with_muted(self):
        """Testing SummaryColumn.render_data with muted review request"""
        review_request = self.create_review_request(
            summary='Summary 1',
            submitter=self.request.user,
            publish=True)

        # These are generally set by the column's augment_queryset().
        review_request.draft_summary = None
        review_request.visibility = ReviewRequestVisit.MUTED

        self.assertEqual(
            self.column.render_data(self.stateful_column, review_request),
            '<label class="label-muted">Muted</label>'
            '<span>Summary 1</span>')

    def test_render_data_with_draft_and_archived(self):
        """Testing SummaryColumn.render_data with draft and archived
        review request
        """
        review_request = self.create_review_request(
            summary='Summary 1',
            submitter=self.request.user)

        # These are generally set by the column's augment_queryset().
        review_request.draft_summary = None
        review_request.visibility = ReviewRequestVisit.ARCHIVED

        self.assertEqual(
            self.column.render_data(self.stateful_column, review_request),
            '<label class="label-draft">Draft</label>'
            '<label class="label-archived">Archived</label>'
            '<span>Summary 1</span>')

    def test_render_data_with_draft_and_muted(self):
        """Testing SummaryColumn.render_data with draft and muted
        review request
        """
        review_request = self.create_review_request(
            summary='Summary 1',
            submitter=self.request.user)

        # These are generally set by the column's augment_queryset().
        review_request.draft_summary = None
        review_request.visibility = ReviewRequestVisit.MUTED

        self.assertEqual(
            self.column.render_data(self.stateful_column, review_request),
            '<label class="label-draft">Draft</label>'
            '<label class="label-muted">Muted</label>'
            '<span>Summary 1</span>')

    def test_render_data_with_submitted(self):
        """Testing SummaryColumn.render_data with submitted review request"""
        review_request = self.create_review_request(
            summary='Summary 1',
            status=ReviewRequest.SUBMITTED,
            submitter=self.request.user,
            public=True)

        # These are generally set by the column's augment_queryset().
        review_request.draft_summary = None
        review_request.visibility = ReviewRequestVisit.VISIBLE

        self.assertEqual(
            self.column.render_data(self.stateful_column, review_request),
            '<label class="label-submitted">Submitted</label>'
            '<span>Summary 1</span>')

    def test_render_data_with_discarded(self):
        """Testing SummaryColumn.render_data with discarded review request"""
        review_request = self.create_review_request(
            summary='Summary 1',
            status=ReviewRequest.DISCARDED,
            submitter=self.request.user,
            public=True)

        # These are generally set by the column's augment_queryset().
        review_request.draft_summary = None
        review_request.visibility = ReviewRequestVisit.VISIBLE

        self.assertEqual(
            self.column.render_data(self.stateful_column, review_request),
            '<label class="label-discarded">Discarded</label>'
            '<span>Summary 1</span>')


class UsernameColumnTests(BaseColumnTestCase):
    """Tests for reviewboard.datagrids.columns.UsernameColumn."""

    column = UsernameColumn()

    @add_fixtures(['test_site'])
    def test_render(self):
        """Testing UsernameColumn.render_cell"""
        user = User.objects.get(username='doc')
        self.assertIn(
            'href="/users/doc/"',
            self.column.render_cell(self.stateful_column, user, None))

    @add_fixtures(['test_site'])
    def test_render_local_site(self):
        """Testing UsernameColumn.render_cell on a LocalSite"""
        self.request._local_site_name = self.local_site_name
        user = User.objects.get(username='doc')

        self.assertIn(
            'href="/s/%s/users/doc/"' % self.local_site_name,
            self.column.render_cell(self.stateful_column, user, None))
