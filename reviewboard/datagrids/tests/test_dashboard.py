"""Unit tests for the dashboard.

Version Added:
    5.0.7
"""

from __future__ import annotations

from typing import Optional

import kgb
from django.contrib.auth.models import User
from django.db.models import Count, Q
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

    datagrid_url = '/dashboard/'

    @add_fixtures(['test_users'])
    def test_overview(self):
        """Testing dashboard view (overview)"""
        self._test_overview()

    @add_fixtures(['test_site', 'test_users'])
    def test_overview_with_local_site(self):
        """Testing dashboard view (overview) on a Local Site"""
        self._test_overview(with_local_site=True,
                            local_sites_in_db=True)

    @add_fixtures(['test_site', 'test_users'])
    def test_overview_with_local_sites_in_db(self):
        """Testing dashboard view (overview) with Local Sites in the database
        """
        self._test_overview(local_sites_in_db=True)

    @add_fixtures(['test_users'])
    def test_incoming(self):
        """Testing dashboard view (Incoming -> Open)"""
        self._test_incoming_open()

    @add_fixtures(['test_site', 'test_users'])
    def test_incoming_with_local_site(self):
        """Testing dashboard view (Incoming -> Open) on a Local Site"""
        self._test_incoming_open(with_local_site=True,
                                 local_sites_in_db=True)

    @add_fixtures(['test_site', 'test_users'])
    def test_incoming_with_local_sites_in_db(self):
        """Testing dashboard view (Incoming -> Open) with Local Sites in the
        database
        """
        self._test_incoming_open(local_sites_in_db=True)

    @add_fixtures(['test_users'])
    def test_outgoing(self):
        """Testing dashboard view (Outgoing -> Open)"""
        self._test_outgoing_open()

    @add_fixtures(['test_site', 'test_users'])
    def test_outgoing_open_with_local_site(self):
        """Testing dashboard view (Outgoing -> Open) on a Local Site"""
        self._test_outgoing_open(with_local_site=True,
                                 local_sites_in_db=True)

    @add_fixtures(['test_site', 'test_users'])
    def test_outgoing_open_with_local_sites_in_db(self):
        """Testing dashboard view (Outgoing -> Open) with Local Sites in the
        database
        """
        self._test_outgoing_open(local_sites_in_db=True)

    @add_fixtures(['test_users'])
    def test_outgoing_all(self):
        """Testing dashboard view (Outgoing -> All)"""
        self._test_outgoing_all()

    @add_fixtures(['test_site', 'test_users'])
    def test_outgoing_all_with_local_site(self):
        """Testing dashboard view (Outgoing -> All) on Local Site"""
        self._test_outgoing_all(with_local_site=True,
                                local_sites_in_db=True)

    @add_fixtures(['test_site', 'test_users'])
    def test_outgoing_all_with_local_sites_in_db(self):
        """Testing dashboard view (Outgoing -> All) with Local Sites in the
        database
        """
        self._test_outgoing_all(local_sites_in_db=True)

    @add_fixtures(['test_users'])
    def test_incoming_to_me(self):
        """Testing dashboard view (Incoming -> To Me)"""
        self._test_to_me()

    @add_fixtures(['test_site', 'test_users'])
    def test_incoming_to_me_with_local_site(self):
        """Testing dashboard view (Incoming -> To Me) on Local Site"""
        self._test_to_me(with_local_site=True,
                         local_sites_in_db=True)

    @add_fixtures(['test_site', 'test_users'])
    def test_incoming_to_me_with_local_sites_in_db(self):
        """Testing dashboard view (Incoming -> To Me) with Local Sites in the
        database
        """
        self._test_to_me(local_sites_in_db=True)

    @add_fixtures(['test_users'])
    def test_to_group_with_joined_groups(self):
        """Testing dashboard view with to-group and joined groups"""
        self._test_to_group_with_joined_groups()

    @add_fixtures(['test_site', 'test_users'])
    def test_to_group_with_joined_groups_with_local_site(self):
        """Testing dashboard view with to-group and joined groups on
        Local Site
        """
        self._test_to_group_with_joined_groups(with_local_site=True,
                                               local_sites_in_db=True)

    @add_fixtures(['test_site', 'test_users'])
    def test_to_group_with_joined_groups_with_local_sites_in_db(self):
        """Testing dashboard view with to-group and joined groups on
        Local Sites in the database
        """
        self._test_to_group_with_joined_groups(local_sites_in_db=True)

    @add_fixtures(['test_users'])
    def test_to_group_with_unjoined_public_group(self):
        """Testing dashboard view with to-group and unjoined public group"""
        self._test_to_group_with_unjoined_groups_public()

    @add_fixtures(['test_site', 'test_users'])
    def test_to_group_with_unjoined_public_group_with_local_site(self):
        """Testing dashboard view with to-group and unjoined public group on
        Local Site
        """
        self._test_to_group_with_unjoined_groups_public(
            with_local_site=True,
            local_sites_in_db=True)

    @add_fixtures(['test_site', 'test_users'])
    def test_to_group_with_unjoined_public_group_with_local_sites_in_db(self):
        """Testing dashboard view with to-group and unjoined public group with
        Local Site in the database
        """
        self._test_to_group_with_unjoined_groups_public(
            local_sites_in_db=True)

    @add_fixtures(['test_users'])
    def test_to_group_with_unjoined_private_group(self):
        """Testing dashboard view with to-group and unjoined private group"""
        self._test_to_group_with_unjoined_private_group()

    @add_fixtures(['test_site', 'test_users'])
    def test_to_group_with_unjoined_private_group_with_local_site(self):
        """Testing dashboard view with to-group and unjoined private group
        on Local Site
        """
        self._test_to_group_with_unjoined_private_group(
            with_local_site=True,
            local_sites_in_db=True)

    @add_fixtures(['test_site', 'test_users'])
    def test_to_group_with_unjoined_private_group_with_local_sites_in_db(self):
        """Testing dashboard view with to-group and unjoined private group
        with Local Sites in the database
        """
        self._test_to_group_with_unjoined_private_group(local_sites_in_db=True)

    @add_fixtures(['test_users'])
    def test_with_all_columns(self):
        """Testing dashboard view with all columns"""
        self._test_with_all_columns()

    @add_fixtures(['test_site', 'test_users'])
    def test_with_all_columns_with_local_site(self):
        """Testing dashboard view with all columns on a Local Site"""
        self._test_with_all_columns(with_local_site=True,
                                    local_sites_in_db=True)

    @add_fixtures(['test_site', 'test_users'])
    def test_with_all_columns_with_local_sites_in_db(self):
        """Testing dashboard view with all columns with Local Sites in the
        database
        """
        self._test_with_all_columns(local_sites_in_db=True)

    @add_fixtures(['test_users'])
    def test_show_archived(self):
        """Testing dashboard view with show-archived"""
        self._test_show_archived()

    @add_fixtures(['test_site', 'test_users'])
    def test_show_archived_with_local_site(self):
        """Testing dashboard view with show-archived on a Local Site"""
        self._test_show_archived(with_local_site=True,
                                 local_sites_in_db=True)

    @add_fixtures(['test_site', 'test_users'])
    def test_show_archived_with_local_sites_in_db(self):
        """Testing dashboard view with show-archived with Local Sites in the
        database
        """
        self._test_show_archived(local_sites_in_db=True)

    @add_fixtures(['test_users'])
    def test_archived_with_null_extra_data(self):
        """Testing dashboard view with archived review requests and null
        extra_data
        """
        self._test_archived_with_null_extra_data()

    @add_fixtures(['test_site', 'test_users'])
    def test_archived_with_null_extra_data_with_local_site(self):
        """Testing dashboard view with archived review requests and null
        extra_data on a Local Site
        """
        self._test_archived_with_null_extra_data(
            with_local_site=True,
            local_sites_in_db=True)

    @add_fixtures(['test_site', 'test_users'])
    def test_archived_with_null_extra_data_with_local_sites_in_db(self):
        """Testing dashboard view with archived review requests and null
        extra_data with Local Sites in a database
        """
        self._test_archived_with_null_extra_data(local_sites_in_db=True)

    @add_fixtures(['test_users'])
    def test_sidebar(self):
        """Testing dashboard sidebar"""
        self._test_sidebar()

    @add_fixtures(['test_site', 'test_users'])
    def test_sidebar_with_local_site(self):
        """Testing dashboard sidebar on a Local Site"""
        self._test_sidebar(with_local_site=True,
                           local_sites_in_db=True)

    @add_fixtures(['test_site', 'test_users'])
    def test_sidebar_with_local_sites_in_db(self):
        """Testing dashboard sidebar with Local Sites in the database"""
        self._test_sidebar(local_sites_in_db=True)

    def _test_overview(
        self,
        *,
        with_local_site: bool = False,
        local_sites_in_db: bool = False,
    ) -> None:
        """Common tests for Overview.

        This accesses the Dashboard, checking the Overview view for queries
        and expected datagrid row results.

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

        if local_sites_in_db:
            local_site_q = Q(local_site=local_site)
        else:
            local_site_q = Q()

        self.client.login(username='doc', password='doc')

        user = User.objects.get(username='doc')
        profile = user.get_profile()

        profile.starred_groups.clear()

        grumpy = User.objects.get(username='grumpy')

        for i in range(10):
            if i < 5:
                submitter = user
            else:
                submitter = grumpy

            review_request = self.create_review_request(
                local_site=local_site,
                local_id=i + 1,
                summary='Test %s' % (i + 1),
                submitter=submitter,
                publish=True)

            if i < 5:
                review_request.target_people.add(user)

        self._prefetch_cached(local_site=local_site,
                              user=user)

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
                    'model': User,
                    'extra': {
                        'a': ('1', []),
                    },
                    'limit': 1,
                    'num_joins': 1,
                    'tables': {
                        'auth_user',
                        'site_localsite_users',
                    },
                    'where': Q(local_site__id=local_site.pk) & Q(pk=user.pk),
                },
            ]

        queries += [
            {
                'model': LocalSiteProfile,
                'where': (Q(local_site=local_site) &
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

            # Fetch the list of a user's review groups.
            {
                'model': Group,
                'num_joins': 1,
                'only_fields': {
                    'id',
                    'incoming_request_count',
                    'name',
                },
                'tables': {
                    'reviews_group',
                    'reviews_group_users',
                },
                'where': (Q(users__id=user.pk) &
                          Q(local_site_q)),
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
                      local_site_q &
                      Q(Q(target_people=user) |
                        Q(target_groups__in=[]) |
                        Q(starred_by=profile) |
                        Q(submitter=user))) &
                    ~Q(pk__in=ReviewRequestVisit.objects.none()) &
                    Q(local_site=local_site)
                ),
                'order_by': ('-last_updated',),
                'distinct': True,
                'limit': 5,
            },
        ]

        if local_site:
            queries += [
                {
                    'model': ReviewRequest,
                    'select_related': {
                        'local_site',
                        'submitter',
                    },
                    'extra': extra,
                    'where': Q(pk__in=[5, 4, 3, 2, 1]),
                },
            ]
        else:
            queries += [
                {
                    'model': ReviewRequest,
                    'select_related': {'submitter'},
                    'extra': extra,
                    'where': Q(pk__in=[5, 4, 3, 2, 1]),
                },
            ]

        with self.assertQueries(queries):
            response = self.client.get(
                self.get_datagrid_url(local_site=local_site),
                {
                    'view': 'overview',
                })

        self.assertEqual(response.status_code, 200)

        datagrid = self._get_context_var(response, 'datagrid')
        assert datagrid is not None
        self.assertEqual(len(datagrid.rows), 5)
        self.assertEqual(datagrid.rows[0]['object'].summary, 'Test 5')
        self.assertEqual(datagrid.rows[1]['object'].summary, 'Test 4')
        self.assertEqual(datagrid.rows[2]['object'].summary, 'Test 3')
        self.assertEqual(datagrid.rows[3]['object'].summary, 'Test 2')
        self.assertEqual(datagrid.rows[4]['object'].summary, 'Test 1')

    def _test_incoming_open(
        self,
        *,
        with_local_site: bool = False,
        local_sites_in_db: bool = False,
    ) -> None:
        """Common tests for the Incoming -> Open view.

        This accesses the Dashboard, checking the Incoming -> Open view for
        queries and expected datagrid row results.

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

        if local_sites_in_db:
            local_site_q = Q(local_site=local_site)
        else:
            local_site_q = Q()

        self.client.login(username='doc', password='doc')

        user = User.objects.get(username='doc')
        profile = user.get_profile()

        profile.starred_groups.clear()

        for i in range(10):
            review_request = self.create_review_request(
                local_site=local_site,
                local_id=i + 1,
                summary='Test %s' % (i + 1),
                publish=True)

            if i < 5:
                review_request.target_people.add(user)

        self._prefetch_cached(local_site=local_site,
                              user=user)

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
                    'model': User,
                    'extra': {
                        'a': ('1', []),
                    },
                    'limit': 1,
                    'num_joins': 1,
                    'tables': {
                        'auth_user',
                        'site_localsite_users',
                    },
                    'where': Q(local_site__id=local_site.pk) & Q(pk=user.pk),
                },
            ]

        queries += [
            {
                'model': LocalSiteProfile,
                'where': (Q(local_site=local_site) &
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

            # Fetch the list of a user's review groups.
            {
                'model': Group,
                'num_joins': 1,
                'only_fields': {
                    'id',
                    'incoming_request_count',
                    'name',
                },
                'tables': {
                    'reviews_group',
                    'reviews_group_users',
                },
                'where': (Q(users__id=user.pk) &
                          Q(local_site_q)),
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
                      local_site_q &
                      Q(Q(target_people=user) |
                        Q(target_groups__in=[]) |
                        Q(starred_by=profile))) &
                    ~Q(pk__in=ReviewRequestVisit.objects.none()) &
                    Q(local_site=local_site)
                ),
                'order_by': ('-last_updated',),
                'distinct': True,
                'limit': 5,
            },
        ]

        if local_site:
            queries += [
                {
                    'model': ReviewRequest,
                    'select_related': {
                        'local_site',
                        'submitter',
                    },
                    'extra': extra,
                    'where': Q(pk__in=[5, 4, 3, 2, 1]),
                },
            ]
        else:
            queries += [
                {
                    'model': ReviewRequest,
                    'select_related': {'submitter'},
                    'extra': extra,
                    'where': Q(pk__in=[5, 4, 3, 2, 1]),
                },
            ]

        with self.assertQueries(queries):
            response = self.client.get(
                self.get_datagrid_url(local_site=local_site),
                {
                    'view': 'incoming',
                })

        self.assertEqual(response.status_code, 200)

        datagrid = self._get_context_var(response, 'datagrid')
        assert datagrid is not None
        self.assertEqual(len(datagrid.rows), 5)
        self.assertEqual(datagrid.rows[0]['object'].summary, 'Test 5')
        self.assertEqual(datagrid.rows[1]['object'].summary, 'Test 4')
        self.assertEqual(datagrid.rows[2]['object'].summary, 'Test 3')
        self.assertEqual(datagrid.rows[3]['object'].summary, 'Test 2')
        self.assertEqual(datagrid.rows[4]['object'].summary, 'Test 1')

    def _test_outgoing_open(
        self,
        *,
        with_local_site: bool = False,
        local_sites_in_db: bool = False,
    ) -> None:
        """Common tests for Outgoing -> Open.

        This accesses the Dashboard, checking the Outgoing -> Open view for
        queries and expected datagrid row results.

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

        if local_sites_in_db:
            local_site_q = Q(local_site=local_site)
        else:
            local_site_q = Q()

        self.client.login(username='admin', password='admin')

        user = User.objects.get(username='admin')
        grumpy = User.objects.get(username='grumpy')

        profile = user.get_profile()
        profile.starred_groups.clear()

        for i in range(10):
            if i < 5:
                submitter = user
            else:
                submitter = grumpy

            self.create_review_request(
                local_site=local_site,
                local_id=i + 1,
                summary='Test %s' % (i + 1),
                submitter=submitter,
                publish=True)

        self._prefetch_cached(local_site=local_site,
                              user=user)

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
            queries.append({
                'model': LocalSite,
                'tables': {
                    'site_localsite',
                },
                'where': Q(name=local_site.name),
            })

        queries += [
            {
                'model': LocalSiteProfile,
                'where': (Q(local_site=local_site) &
                          Q(profile=profile) &
                          Q(user=user)),
            },

            # Fetch the list of a user's review groups.
            {
                'model': Group,
                'num_joins': 1,
                'only_fields': {
                    'id',
                    'incoming_request_count',
                    'name',
                },
                'tables': {
                    'reviews_group',
                    'reviews_group_users',
                },
                'where': (Q(users__id=user.pk) &
                          Q(local_site_q)),
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
                      local_site_q &
                      Q(submitter=user)) &
                    ~Q(pk__in=ReviewRequestVisit.objects.none()) &
                    Q(local_site=local_site)
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
                'where': (Q(starred_by__id=profile.pk) &
                          Q(pk__in=[5, 4, 3, 2, 1])),
            },
        ]

        if local_site:
            queries += [
                {
                    'model': ReviewRequest,
                    'select_related': {
                        'local_site',
                        'submitter',
                    },
                    'extra': extra,
                    'where': Q(pk__in=[5, 4, 3, 2, 1]),
                },
            ]
        else:
            queries += [
                {
                    'model': ReviewRequest,
                    'select_related': {'submitter'},
                    'extra': extra,
                    'where': Q(pk__in=[5, 4, 3, 2, 1]),
                },
            ]

        with self.assertQueries(queries):
            response = self.client.get(
                self.get_datagrid_url(local_site=local_site),
                {
                    'view': 'outgoing',
                })

        self.assertEqual(response.status_code, 200)

        datagrid = self._get_context_var(response, 'datagrid')
        assert datagrid is not None
        self.assertEqual(len(datagrid.rows), 5)
        self.assertEqual(datagrid.rows[0]['object'].summary, 'Test 5')
        self.assertEqual(datagrid.rows[1]['object'].summary, 'Test 4')
        self.assertEqual(datagrid.rows[2]['object'].summary, 'Test 3')
        self.assertEqual(datagrid.rows[3]['object'].summary, 'Test 2')
        self.assertEqual(datagrid.rows[4]['object'].summary, 'Test 1')

    def _test_outgoing_all(
        self,
        *,
        with_local_site: bool = False,
        local_sites_in_db: bool = False,
    ) -> None:
        """Common tests for Outgoing -> All.

        This accesses the Dashboard, checking the Outgoing -> All view for
        queries and expected datagrid row results.

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

        if local_sites_in_db:
            local_site_q = Q(local_site=local_site)
        else:
            local_site_q = Q()

        self.client.login(username='doc', password='doc')

        user = User.objects.get(username='doc')
        profile = user.get_profile()

        profile.starred_groups.clear()

        grumpy = User.objects.get(username='grumpy')

        for i in range(10):
            if i < 5:
                submitter = user
            else:
                submitter = grumpy

            self.create_review_request(
                summary='Test %s' % (i + 1),
                submitter=submitter,
                local_site=local_site,
                local_id=i + 1,
                publish=True)

        self._prefetch_cached(local_site=local_site,
                              user=user)

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
                    'model': User,
                    'extra': {
                        'a': ('1', []),
                    },
                    'limit': 1,
                    'num_joins': 1,
                    'tables': {
                        'auth_user',
                        'site_localsite_users',
                    },
                    'where': Q(local_site__id=local_site.pk) & Q(pk=user.pk),
                },
            ]

        queries += [
            {
                'model': LocalSiteProfile,
                'where': (Q(local_site=local_site) &
                          Q(profile=profile) &
                          Q(user=user)),
            },

            # Fetch the list of a user's review groups.
            {
                'model': Group,
                'num_joins': 1,
                'only_fields': {
                    'id',
                    'incoming_request_count',
                    'name',
                },
                'tables': {
                    'reviews_group',
                    'reviews_group_users',
                },
                'where': (Q(users__id=user.pk) &
                          Q(local_site_q)),
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
                      local_site_q &
                      Q(submitter=user)) &
                    ~Q(pk__in=ReviewRequestVisit.objects.none()) &
                    Q(local_site=local_site)
                ),
                'order_by': ('-last_updated',),
                'distinct': True,
                'limit': 5,
            },
        ]

        if local_site:
            queries += [
                {
                    'model': ReviewRequest,
                    'select_related': {
                        'local_site',
                        'submitter',
                    },
                    'extra': extra,
                    'where': Q(pk__in=[5, 4, 3, 2, 1]),
                },
            ]
        else:
            queries += [
                {
                    'model': ReviewRequest,
                    'select_related': {'submitter'},
                    'extra': extra,
                    'where': Q(pk__in=[5, 4, 3, 2, 1]),
                },
            ]

        with self.assertQueries(queries):
            response = self.client.get(
                self.get_datagrid_url(local_site=local_site),
                {
                    'view': 'mine',
                })

        self.assertEqual(response.status_code, 200)

        datagrid = self._get_context_var(response, 'datagrid')
        assert datagrid is not None

        self.assertEqual(len(datagrid.rows), 5)
        self.assertEqual(datagrid.rows[0]['object'].summary, 'Test 5')
        self.assertEqual(datagrid.rows[1]['object'].summary, 'Test 4')
        self.assertEqual(datagrid.rows[2]['object'].summary, 'Test 3')
        self.assertEqual(datagrid.rows[3]['object'].summary, 'Test 2')
        self.assertEqual(datagrid.rows[4]['object'].summary, 'Test 1')

    def _test_to_me(
        self,
        *,
        with_local_site: bool = False,
        local_sites_in_db: bool = False,
    ) -> None:
        """Common tests for Incoming -> To Me.

        This accesses the Dashboard, checking the Incoming -> To Me view for
        queries and expected datagrid row results.

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

        if local_sites_in_db:
            local_site_q = Q(local_site=local_site)
        else:
            local_site_q = Q()

        self.client.login(username='doc', password='doc')

        user = User.objects.get(username='doc')
        profile = user.get_profile()

        profile.starred_groups.clear()

        group = self.create_review_group(local_site=local_site)
        group.users.add(user)

        for i in range(15):
            review_request = self.create_review_request(
                summary='Test %s' % (i + 1),
                publish=True,
                local_site=local_site,
                local_id=i + 1)

            if i < 5:
                review_request.target_people.add(user)
            elif i < 10:
                review_request.target_groups.add(group)

        self._prefetch_cached(local_site=local_site,
                              user=user)

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
                    'model': User,
                    'extra': {
                        'a': ('1', []),
                    },
                    'limit': 1,
                    'num_joins': 1,
                    'tables': {
                        'auth_user',
                        'site_localsite_users',
                    },
                    'where': Q(local_site__id=local_site.pk) & Q(pk=user.pk),
                },
            ]

        queries += [
            {
                'model': LocalSiteProfile,
                'where': (Q(local_site=local_site) &
                          Q(profile=profile) &
                          Q(user=user)),
            },

            # Fetch the list of a user's review groups.
            {
                'model': Group,
                'num_joins': 1,
                'only_fields': {
                    'id',
                    'incoming_request_count',
                    'name',
                },
                'tables': {
                    'reviews_group',
                    'reviews_group_users',
                },
                'where': (Q(users__id=user.pk) &
                          Q(local_site_q)),
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
                      local_site_q &
                      (Q(target_people=user) |
                       Q(starred_by=profile))) &
                    ~Q(pk__in=ReviewRequestVisit.objects.none()) &
                    Q(local_site=local_site)
                ),
                'order_by': ('-last_updated',),
                'distinct': True,
                'limit': 5,
            },
        ]

        if local_site:
            queries += [
                {
                    'model': ReviewRequest,
                    'select_related': {
                        'local_site',
                        'submitter',
                    },
                    'extra': extra,
                    'where': Q(pk__in=[5, 4, 3, 2, 1]),
                },
            ]
        else:
            queries += [
                {
                    'model': ReviewRequest,
                    'select_related': {'submitter'},
                    'extra': extra,
                    'where': Q(pk__in=[5, 4, 3, 2, 1]),
                },
            ]

        with self.assertQueries(queries):
            response = self.client.get(
                self.get_datagrid_url(local_site=local_site),
                {
                    'view': 'to-me',
                })

        self.assertEqual(response.status_code, 200)

        datagrid = self._get_context_var(response, 'datagrid')
        assert datagrid is not None

        self.assertEqual(len(datagrid.rows), 5)
        self.assertEqual(datagrid.rows[0]['object'].summary, 'Test 5')
        self.assertEqual(datagrid.rows[1]['object'].summary, 'Test 4')
        self.assertEqual(datagrid.rows[2]['object'].summary, 'Test 3')
        self.assertEqual(datagrid.rows[3]['object'].summary, 'Test 2')
        self.assertEqual(datagrid.rows[4]['object'].summary, 'Test 1')

    def _test_to_group_with_joined_groups(
        self,
        *,
        with_local_site: bool = False,
        local_sites_in_db: bool = False,
    ) -> None:
        """Common tests for Incoming -> To Group with joined groups.

        This accesses the Dashboard, checking the Incoming -> To Group view
        with joined groups for queries and expected datagrid row results.

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

        if local_sites_in_db:
            local_site_q = Q(local_site=local_site)
            target_groups_local_site_q = \
                Q(target_groups__local_site=local_site)
        else:
            local_site_q = Q()
            target_groups_local_site_q = Q()

        self.client.login(username='doc', password='doc')

        user = User.objects.get(username='doc')
        profile = user.get_profile()

        profile.starred_groups.clear()

        group1 = self.create_review_group(
            name='devgroup',
            local_site=local_site)
        group1.users.add(User.objects.get(username='doc'))

        group2 = self.create_review_group(
            name='test-group',
            local_site=local_site)

        for i in range(15):
            review_request = self.create_review_request(
                summary='Test %s' % (i + 1),
                publish=True,
                local_site=local_site,
                local_id=i + 1)

            if i < 5:
                review_request.target_groups.add(group1)
            elif i < 10:
                review_request.target_groups.add(group2)

        user.get_site_profile(local_site=local_site)
        self._prefetch_cached(local_site=local_site,
                              user=user)

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
                    'model': User,
                    'extra': {
                        'a': ('1', []),
                    },
                    'limit': 1,
                    'num_joins': 1,
                    'tables': {
                        'auth_user',
                        'site_localsite_users',
                    },
                    'where': Q(local_site__id=local_site.pk) & Q(pk=user.pk),
                },
            ]

        queries += [
            {
                'model': LocalSiteProfile,
                'where': (Q(local_site=local_site) &
                          Q(profile=profile) &
                          Q(user=user)),
            },
            {
                'model': Group,
                'where': (Q(name='devgroup') &
                          Q(local_site_q)),
            },
        ]

        if local_site:
            queries += [
                {
                    'model': LocalSite,
                    'tables': {
                        'site_localsite',
                    },
                    'where': Q(id=local_site.pk),
                },
                {
                    'model': User,
                    'extra': {
                        'a': ('1', []),
                    },
                    'limit': 1,
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
            # Fetch the list of a user's review groups.
            {
                'model': Group,
                'num_joins': 1,
                'only_fields': {
                    'id',
                    'incoming_request_count',
                    'name',
                },
                'tables': {
                    'reviews_group',
                    'reviews_group_users',
                },
                'where': (Q(users__id=user.pk) &
                          Q(local_site_q)),
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
                      local_site_q &
                      Q(target_groups__name='devgroup') &
                      target_groups_local_site_q) &
                    ~Q(pk__in=ReviewRequestVisit.objects.none()) &
                    Q(local_site=local_site)
                ),
                'order_by': ('-last_updated',),
                'distinct': True,
                'limit': 5,
            },
        ]

        if local_site:
            queries += [
                {
                    'model': ReviewRequest,
                    'select_related': {
                        'local_site',
                        'submitter',
                    },
                    'extra': extra,
                    'where': Q(pk__in=[5, 4, 3, 2, 1]),
                },
            ]
        else:
            queries += [
                {
                    'model': ReviewRequest,
                    'select_related': {'submitter'},
                    'extra': extra,
                    'where': Q(pk__in=[5, 4, 3, 2, 1]),
                },
            ]

        with self.assertQueries(queries):
            response = self.client.get(
                self.get_datagrid_url(local_site=local_site),
                {
                    'group': 'devgroup',
                    'view': 'to-group',
                })

        self.assertEqual(response.status_code, 200)

        datagrid = self._get_context_var(response, 'datagrid')
        assert datagrid is not None

        self.assertEqual(len(datagrid.rows), 5)
        self.assertEqual(datagrid.rows[0]['object'].summary, 'Test 5')
        self.assertEqual(datagrid.rows[1]['object'].summary, 'Test 4')
        self.assertEqual(datagrid.rows[2]['object'].summary, 'Test 3')
        self.assertEqual(datagrid.rows[3]['object'].summary, 'Test 2')
        self.assertEqual(datagrid.rows[4]['object'].summary, 'Test 1')

    def _test_to_group_with_unjoined_groups_public(
        self,
        *,
        with_local_site: bool = False,
        local_sites_in_db: bool = False,
    ) -> None:
        """Common tests for Incoming -> To Group with unjoined public groups.

        This accesses the Dashboard, checking the Incoming -> To Group view
        with unjoined public groups for queries and expected datagrid row
        results.

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

        if local_sites_in_db:
            local_site_q = Q(local_site=local_site)
            target_groups_local_site_q = \
                Q(target_groups__local_site=local_site)
        else:
            local_site_q = Q()
            target_groups_local_site_q = Q()

        self.client.login(username='doc', password='doc')

        user = User.objects.get(username='doc')
        profile = user.get_profile()

        profile.starred_groups.clear()

        group = self.create_review_group(
            name='devgroup',
            local_site=local_site)

        review_request = self.create_review_request(
            summary='Test 1',
            publish=True,
            local_site=local_site,
            local_id=1)
        review_request.target_groups.add(group)

        self._prefetch_cached(local_site=local_site,
                              user=user)

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
                    'model': User,
                    'extra': {
                        'a': ('1', []),
                    },
                    'limit': 1,
                    'num_joins': 1,
                    'tables': {
                        'auth_user',
                        'site_localsite_users',
                    },
                    'where': Q(local_site__id=local_site.pk) & Q(pk=user.pk),
                },
            ]

        queries += [
            {
                'model': LocalSiteProfile,
                'where': (Q(local_site=local_site) &
                          Q(profile=profile) &
                          Q(user=user)),
            },
            {
                'model': Group,
                'where': (Q(name='devgroup') &
                          Q(local_site_q)),
            },
        ]

        if local_site:
            queries += [
                {
                    'model': LocalSite,
                    'tables': {
                        'site_localsite',
                    },
                    'where': Q(id=local_site.pk),
                },
                {
                    'model': User,
                    'extra': {
                        'a': ('1', []),
                    },
                    'limit': 1,
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
            # Fetch the list of a user's review groups.
            {
                'model': Group,
                'num_joins': 1,
                'only_fields': {
                    'id',
                    'incoming_request_count',
                    'name',
                },
                'tables': {
                    'reviews_group',
                    'reviews_group_users',
                },
                'where': (Q(users__id=user.pk) &
                          Q(local_site_q)),
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
                      local_site_q &
                      Q(target_groups__name='devgroup') &
                      target_groups_local_site_q) &
                    ~Q(pk__in=ReviewRequestVisit.objects.none()) &
                    Q(local_site=local_site)
                ),
                'order_by': ('-last_updated',),
                'distinct': True,
                'limit': 1,
            },
        ]

        if local_site:
            queries += [
                {
                    'model': ReviewRequest,
                    'select_related': {
                        'local_site',
                        'submitter',
                    },
                    'extra': extra,
                    'where': Q(pk__in=[review_request.pk]),
                },
            ]
        else:
            queries += [
                {
                    'model': ReviewRequest,
                    'select_related': {
                        'submitter',
                    },
                    'extra': extra,
                    'where': Q(pk__in=[review_request.pk]),
                },
            ]

        with self.assertQueries(queries):
            response = self.client.get(
                self.get_datagrid_url(local_site=local_site),
                {
                    'group': 'devgroup',
                    'view': 'to-group',
                })

        self.assertEqual(response.status_code, 200)

    def _test_to_group_with_unjoined_private_group(
        self,
        *,
        with_local_site: bool = False,
        local_sites_in_db: bool = False,
    ) -> None:
        """Common tests for Incoming -> To Group with unjoined private groups.

        This accesses the Dashboard, checking the Incoming -> To Group view
        with unjoined private groups for queries and expected datagrid row
        results.

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

        if local_sites_in_db:
            local_site_q = Q(local_site=local_site)
        else:
            local_site_q = Q()

        self.client.login(username='doc', password='doc')

        user = User.objects.get(username='doc')
        profile = user.get_profile()

        group = self.create_review_group(
            name='new-private',
            invite_only=True,
            local_site=local_site)

        review_request = self.create_review_request(
            summary='Test 1',
            publish=True,
            local_site=local_site,
            local_id=1)
        review_request.target_groups.add(group)

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
                    'model': User,
                    'extra': {
                        'a': ('1', []),
                    },
                    'limit': 1,
                    'num_joins': 1,
                    'tables': {
                        'auth_user',
                        'site_localsite_users',
                    },
                    'where': Q(local_site__id=local_site.pk) & Q(pk=user.pk),
                },
            ]

        queries += [
            {
                'model': LocalSiteProfile,
                'where': (Q(local_site=local_site) &
                          Q(profile=profile) &
                          Q(user=user)),
            },
            {
                'model': Group,
                'tables': {
                    'reviews_group',
                },
                'where': (Q(name='devgroup') &
                          Q(local_site_q)),
            },
        ]

        with self.assertQueries(queries):
            response = self.client.get(
                self.get_datagrid_url(local_site=local_site),
                {
                    'group': 'devgroup',
                    'view': 'to-group',
                })

        self.assertEqual(response.status_code, 404)

    def _test_with_all_columns(
        self,
        *,
        with_local_site: bool = False,
        local_sites_in_db: bool = False,
    ) -> None:
        """Common tests for checking all available columns.

        This accesses the Dashboard, enabling all columns and checking the
        resutling queries.

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

        if local_sites_in_db:
            local_site_q = Q(local_site=local_site)
        else:
            local_site_q = Q()

        self.client.login(username='doc', password='doc')

        user = User.objects.get(username='doc')
        profile = user.get_profile()

        profile.starred_groups.clear()

        review_requests = []
        diffset_histories = []

        for i in range(10):
            review_request = self.create_review_request(
                summary='Test %s' % (i + 1),
                local_site=local_site,
                local_id=i + 1,
                publish=True)

            if i < 5:
                review_request.target_people.add(user)
                diffset_histories.append(review_request.diffset_history)
                review_requests.append(review_request)

        self._prefetch_cached(local_site=local_site,
                              user=user)

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
                    'model': User,
                    'extra': {
                        'a': ('1', []),
                    },
                    'limit': 1,
                    'num_joins': 1,
                    'tables': {
                        'auth_user',
                        'site_localsite_users',
                    },
                    'where': Q(local_site__id=local_site.pk) & Q(pk=user.pk),
                },
            ]

        queries += [
            {
                'model': LocalSiteProfile,
                'where': (Q(local_site=local_site) &
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

            # Fetch the list of a user's review groups.
            {
                'model': Group,
                'num_joins': 1,
                'only_fields': {
                    'id',
                    'incoming_request_count',
                    'name',
                },
                'tables': {
                    'reviews_group',
                    'reviews_group_users',
                },
                'where': (Q(users__id=user.pk) &
                          Q(local_site_q)),
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
                      local_site_q &
                      Q(Q(target_people=user) |
                        Q(target_groups__in=[]) |
                        Q(starred_by=profile))) &
                    ~Q(pk__in=ReviewRequestVisit.objects.none()) &
                    Q(local_site=local_site)
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
                'where': (Q(starred_by__id=profile.pk) &
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
        ]

        if local_site:
            queries += [
                {
                    'model': ReviewRequest,
                    'select_related': {
                        'diffset_history',
                        'local_site',
                        'repository',
                        'submitter',
                    },
                    'extra': extra,
                    'where': Q(pk__in=[5, 4, 3, 2, 1]),
                },
            ]
        else:
            queries += [
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
            ]

        queries += [
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
                self.get_datagrid_url(local_site=local_site),
                {
                    'columns': ','.join(column_ids),
                    'view': 'incoming',
                })

        self.assertEqual(response.status_code, 200)

        datagrid = self._get_context_var(response, 'datagrid')
        assert datagrid is not None
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

    def _test_show_archived(
        self,
        *,
        with_local_site: bool = False,
        local_sites_in_db: bool = False,
    ) -> None:
        """Common tests for showing archived review requests.

        This accesses the Dashboard with various archived review request
        states and filters.

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

        if local_sites_in_db:
            local_site_q = Q(local_site=local_site)
        else:
            local_site_q = Q()

        dashboard_url = self.get_datagrid_url(local_site=local_site)

        self.client.login(username='doc', password='doc')
        user = User.objects.get(username='doc')
        profile = user.get_profile()

        profile.starred_groups.clear()

        if local_site:
            local_site.users.add(user)

        visible = self.create_review_request(
            local_site=local_site,
            local_id=1,
            summary='Test 1',
            publish=True)
        archived = self.create_review_request(
            local_site=local_site,
            local_id=2,
            summary='Test 2',
            publish=True)
        muted = self.create_review_request(
            local_site=local_site,
            local_id=3,
            summary='Test 3',
            publish=True)

        visible.target_people.add(user)
        archived.target_people.add(user)
        muted.target_people.add(user)

        self.client.get(visible.get_absolute_url())
        self.client.get(archived.get_absolute_url())
        self.client.get(muted.get_absolute_url())

        visit = ReviewRequestVisit.objects.get(user__username=user,
                                               review_request=archived.pk)
        visit.visibility = ReviewRequestVisit.ARCHIVED
        visit.save(update_fields=('visibility',))

        visit = ReviewRequestVisit.objects.get(user__username=user,
                                               review_request=muted.pk)
        visit.visibility = ReviewRequestVisit.MUTED
        visit.save(update_fields=('visibility',))

        self._prefetch_cached(local_site=local_site,
                              user=user)

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
                    'model': User,
                    'extra': {
                        'a': ('1', []),
                    },
                    'limit': 1,
                    'num_joins': 1,
                    'tables': {
                        'auth_user',
                        'site_localsite_users',
                    },
                    'where': Q(local_site__id=local_site.pk) & Q(pk=user.pk),
                },
            ]

        queries += [
            {
                'model': LocalSiteProfile,
                'where': (Q(local_site=local_site) &
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
                'where': Q(users__id=user.pk),
                'values_select': ('pk',),
            },

            # Fetch the list of a user's review groups.
            {
                'model': Group,
                'num_joins': 1,
                'only_fields': {
                    'id',
                    'incoming_request_count',
                    'name',
                },
                'tables': {
                    'reviews_group',
                    'reviews_group_users',
                },
                'where': (Q(users__id=user.pk) &
                          Q(local_site_q)),
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
                    'reviews_reviewrequest_target_groups',
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
                      local_site_q &
                      (Q(target_people=user) |
                       Q(target_groups__in=[]) |
                       Q(starred_by=profile))) &
                    Q(local_site=local_site)
                ),
                'order_by': ('-last_updated',),
                'distinct': True,
                'limit': 3,
            },
        ]

        if local_site:
            queries += [
                {
                    'model': ReviewRequest,
                    'select_related': {
                        'local_site',
                        'submitter',
                    },
                    'extra': extra,
                    'where': Q(pk__in=[3, 2, 1]),
                },
            ]
        else:
            queries += [
                {
                    'model': ReviewRequest,
                    'select_related': {'submitter'},
                    'extra': extra,
                    'where': Q(pk__in=[3, 2, 1]),
                },
            ]

        with self.assertQueries(queries):
            response = self.client.get(
                dashboard_url,
                {
                    'show-archived': '1',
                    'view': 'incoming',
                })

        self.assertEqual(response.status_code, 200)

        datagrid = self._get_context_var(response, 'datagrid')
        assert datagrid is not None
        self.assertEqual(len(datagrid.rows), 3)
        self.assertEqual(datagrid.rows[0]['object'].summary, 'Test 3')
        self.assertEqual(datagrid.rows[1]['object'].summary, 'Test 2')
        self.assertEqual(datagrid.rows[2]['object'].summary, 'Test 1')

        response = self.client.get(
            dashboard_url,
            {
                'show-archived': '0',
                'view': 'incoming',
            })

        self.assertEqual(response.status_code, 200)

        datagrid = self._get_context_var(response, 'datagrid')
        assert datagrid is not None
        self.assertEqual(len(datagrid.rows), 1)
        self.assertEqual(datagrid.rows[0]['object'].summary, 'Test 1')

        self.client.logout()
        self.client.login(username='grumpy', password='grumpy')
        user = User.objects.get(username='grumpy')

        if local_site:
            local_site.users.add(user)

        visible.target_people.add(user)
        archived.target_people.add(user)
        muted.target_people.add(user)

        self.client.get(visible.get_absolute_url())
        self.client.get(archived.get_absolute_url())
        self.client.get(muted.get_absolute_url())

        response = self.client.get(dashboard_url, {'show-archived': '1'})
        self.assertEqual(response.status_code, 200)

        datagrid = self._get_context_var(response, 'datagrid')
        assert datagrid is not None
        self.assertEqual(len(datagrid.rows), 3)
        self.assertEqual(datagrid.rows[0]['object'].summary, 'Test 3')
        self.assertEqual(datagrid.rows[1]['object'].summary, 'Test 2')
        self.assertEqual(datagrid.rows[2]['object'].summary, 'Test 1')

        response = self.client.get(
            dashboard_url,
            {
                'show-archived': '0',
                'view': 'incoming',
            })
        self.assertEqual(response.status_code, 200)

        datagrid = self._get_context_var(response, 'datagrid')
        assert datagrid is not None
        self.assertEqual(len(datagrid.rows), 3)
        self.assertEqual(datagrid.rows[0]['object'].summary, 'Test 3')
        self.assertEqual(datagrid.rows[1]['object'].summary, 'Test 2')
        self.assertEqual(datagrid.rows[2]['object'].summary, 'Test 1')

    def _test_archived_with_null_extra_data(
        self,
        *,
        with_local_site: bool = False,
        local_sites_in_db: bool = False,
    ) -> None:
        """Common tests for archived review requests with null extra_data.

        This accesses the Dashboard with archived review requests containing
        null extra_data.

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

        if local_sites_in_db:
            local_site_q = Q(local_site=local_site)
        else:
            local_site_q = Q()

        # We encountered a bug where the archived state in the dashboard was
        # assuming that Profile.extra_data was always a dictionary. In modern
        # versions of Review Board, the default value for that field is an
        # empty dict, but old versions defaulted it to None. This test verifies
        # that the bug is fixed.
        archived = self.create_review_request(
            local_site=local_site,
            local_id=1,
            summary='Test 1',
            publish=True)

        self.client.login(username='doc', password='doc')
        user = User.objects.get(username='doc')

        profile = user.get_profile()
        profile.extra_data = None
        profile.save(update_fields=('extra_data',))
        profile.starred_groups.clear()

        archived.target_people.add(user)

        self.client.get(archived.get_absolute_url())

        visit = ReviewRequestVisit.objects.get(user__username=user,
                                               review_request=archived.id)
        visit.visibility = ReviewRequestVisit.ARCHIVED
        visit.save(update_fields=('visibility',))

        self._prefetch_cached(local_site=local_site,
                              user=user)

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
                    'model': User,
                    'extra': {
                        'a': ('1', []),
                    },
                    'limit': 1,
                    'num_joins': 1,
                    'tables': {
                        'auth_user',
                        'site_localsite_users',
                    },
                    'where': Q(local_site__id=local_site.pk) & Q(pk=user.pk),
                },
            ]

        queries += [
            {
                'model': LocalSiteProfile,
                'where': (Q(local_site=local_site) &
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
                'where': Q(users__id=user.pk),
                'values_select': ('pk',),
            },

            # Fetch the list of a user's review groups.
            {
                'model': Group,
                'num_joins': 1,
                'only_fields': {
                    'id',
                    'incoming_request_count',
                    'name',
                },
                'tables': {
                    'reviews_group',
                    'reviews_group_users',
                },
                'where': (Q(users__id=user.pk) &
                          Q(local_site_q)),
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
                    'reviews_reviewrequest_target_groups',
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
                      local_site_q &
                      (Q(target_people=user) |
                       Q(target_groups__in=[]) |
                       Q(starred_by=profile))) &
                    Q(local_site=local_site)
                ),
                'order_by': ('-last_updated',),
                'distinct': True,
                'limit': 3,
            },
            {
                'model': ReviewRequest,
                'select_related': {'submitter'},
                'extra': extra,
                'where': Q(pk__in=[3, 2, 1]),
            },
        ]

        with self.assertQueries(queries):
            response = self.client.get(
                self.get_datagrid_url(local_site=local_site),
                {
                    'show-archived': '0',
                    'view': 'incoming',
                })

        self.assertEqual(response.status_code, 200)

    def _test_sidebar(
        self,
        *,
        with_local_site: bool = False,
        local_sites_in_db: bool = False,
    ) -> None:
        """Common tests for the sidebar.

        This accesses the Dashboard and checks the queries and results in
        the sidebar.

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

        if local_sites_in_db:
            local_site_q = Q(local_site=local_site)
        else:
            local_site_q = Q()

        self.client.login(username='doc', password='doc')
        user = User.objects.get(username='doc')
        profile = user.get_profile()

        user.review_groups.clear()

        # Create all the test data.
        devgroup = self.create_review_group(
            local_site=local_site,
            name='devgroup')
        devgroup.users.add(user)

        privgroup = self.create_review_group(
            local_site=local_site,
            name='privgroup')
        privgroup.users.add(user)

        self.create_review_request(
            local_site=local_site,
            local_id=1,
            submitter=user,
            publish=True)

        review_request2 = self.create_review_request(
            local_site=local_site,
            local_id=2,
            submitter='grumpy')
        draft = ReviewRequestDraft.create(review_request2)
        draft.target_people.add(user)
        review_request2.publish(review_request2.submitter)

        review_request3 = self.create_review_request(
            local_site=local_site,
            local_id=3,
            submitter='grumpy')
        draft = ReviewRequestDraft.create(review_request3)
        draft.target_groups.add(devgroup)
        review_request3.publish(review_request3.submitter)

        review_request4 = self.create_review_request(
            local_site=local_site,
            local_id=4,
            submitter='grumpy')
        draft = ReviewRequestDraft.create(review_request4)
        draft.target_groups.add(privgroup)
        review_request4.publish(review_request4.submitter)
        profile.star_review_request(review_request4)

        # Join a group.
        devgroup.users.add(user)

        # Star some groups.
        profile.star_review_group(devgroup)
        profile.star_review_group(privgroup)

        self._prefetch_cached(local_site=local_site,
                              user=user)

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
                    'model': User,
                    'extra': {
                        'a': ('1', []),
                    },
                    'limit': 1,
                    'num_joins': 1,
                    'tables': {
                        'auth_user',
                        'site_localsite_users',
                    },
                    'where': Q(local_site__id=local_site.pk) & Q(pk=user.pk),
                },
            ]

        queries += [
            {
                'model': LocalSiteProfile,
                'where': (Q(local_site=local_site) &
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
                'where': Q(users__id=user.pk),
                'values_select': ('pk',),
            },

            # Fetch the list of a user's review groups.
            {
                'model': Group,
                'num_joins': 1,
                'only_fields': {
                    'id',
                    'incoming_request_count',
                    'name',
                },
                'tables': {
                    'reviews_group',
                    'reviews_group_users',
                },
                'where': (Q(users__id=user.pk) &
                          Q(local_site_q)),
            },

            # Fetch the list of a user's starred review groups.
            {
                'model': Group,
                'num_joins': 1,
                'only_fields': {
                    'id',
                    'incoming_request_count',
                    'name',
                },
                'tables': {
                    'accounts_profile_starred_groups',
                    'reviews_group',
                },
                'where': (Q(starred_by__id=profile.pk) &
                          ~Q(pk__in={devgroup.pk, privgroup.pk}) &
                          Q(local_site_q)),
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
                    'reviews_reviewrequest_target_groups',
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
                      local_site_q &
                      (Q(target_people=user) |
                       Q(target_groups__in=[devgroup.pk, privgroup.pk]) |
                       Q(starred_by=profile))) &
                    ~Q(pk__in=ReviewRequestVisit.objects.none()) &
                    Q(local_site=local_site)
                ),
                'order_by': ('-last_updated',),
                'distinct': True,
                'limit': 3,
            },
        ]

        if local_site:
            queries += [
                {
                    'model': ReviewRequest,
                    'select_related': {
                        'local_site',
                        'submitter',
                    },
                    'extra': extra,
                    'where': Q(pk__in=[
                        review_request4.pk,
                        review_request3.pk,
                        review_request2.pk,
                    ]),
                },
            ]
        else:
            queries += [
                {
                    'model': ReviewRequest,
                    'select_related': {'submitter'},
                    'extra': extra,
                    'where': Q(pk__in=[
                        review_request4.pk,
                        review_request3.pk,
                        review_request2.pk,
                    ]),
                },
            ]

        # Now load the dashboard and get the sidebar items.
        with self.assertQueries(queries):
            response = self.client.get(
                self.get_datagrid_url(local_site=local_site),
                {
                    'view': 'incoming',
                })

        self.assertEqual(response.status_code, 200)

        datagrid = self._get_context_var(response, 'datagrid')
        assert datagrid

        sidebar_items = datagrid.sidebar_items
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
