"""Unit tests for the dashboard.

Version Added:
    5.0.7
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, TYPE_CHECKING

import kgb
from django.contrib.auth.models import User
from django.db.models import Count, Q
from djblets.testing.decorators import add_fixtures

from reviewboard.accounts.models import (Profile,
                                         ReviewRequestVisit)
from reviewboard.accounts.testing.queries import \
    get_user_local_site_profile_equeries
from reviewboard.datagrids.grids import DashboardDataGrid
from reviewboard.datagrids.tests.base import BaseViewTestCase
from reviewboard.diffviewer.models import DiffSet
from reviewboard.reviews.models import (Group,
                                        ReviewRequest,
                                        ReviewRequestDraft)
from reviewboard.reviews.testing.queries.review_requests import (
    get_review_requests_from_user_q,
    get_review_requests_to_group_q,
    get_review_requests_to_or_from_user_q,
    get_review_requests_to_user_directly_q,
    get_review_requests_to_user_q,
)
from reviewboard.site.models import LocalSite
from reviewboard.site.testing.queries import \
    get_local_site_is_accessible_by_equeries
from reviewboard.testing.queries.http import get_http_request_start_equeries

if TYPE_CHECKING:
    from djblets.db.query_comparator import ExpectedQueries

    from reviewboard.testing.queries.base import ExpectedQResult


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

        self.client.login(username='doc', password='doc')

        user = User.objects.get(username='doc')
        profile = user.get_profile()

        profile.starred_groups.clear()

        grumpy = User.objects.get(username='grumpy')

        review_request_pks: List[int] = []

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
                review_request_pks.append(review_request.pk)

        # This will be ordered with newest at the top.
        review_request_pks.reverse()

        self._prefetch_cached(local_site=local_site,
                              user=user)

        equeries = self._build_datagrid_equeries(
            user=user,
            profile=profile,
            local_site=local_site,
            local_sites_in_db=local_sites_in_db,
            review_request_pks=review_request_pks,
            rows_q_result=get_review_requests_to_or_from_user_q(
                user=user,
                to_or_from_user=user,
                to_or_from_user_profile=profile,
                local_site=local_site,
                has_local_sites_in_db=local_sites_in_db,
                status='P'))

        with self.assertQueries(equeries):
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

        self.client.login(username='doc', password='doc')

        user = User.objects.get(username='doc')
        profile = user.get_profile()

        profile.starred_groups.clear()

        review_request_pks: List[int] = []

        for i in range(10):
            review_request = self.create_review_request(
                local_site=local_site,
                local_id=i + 1,
                summary='Test %s' % (i + 1),
                publish=True)

            if i < 5:
                review_request.target_people.add(user)
                review_request_pks.append(review_request.pk)

        # This will be ordered with newest at the top.
        review_request_pks.reverse()

        self._prefetch_cached(local_site=local_site,
                              user=user)

        equeries = self._build_datagrid_equeries(
            user=user,
            profile=profile,
            local_site=local_site,
            local_sites_in_db=local_sites_in_db,
            review_request_pks=review_request_pks,
            rows_q_result=get_review_requests_to_user_q(
                user=user,
                to_user=user,
                to_user_profile=profile,
                local_site=local_site,
                has_local_sites_in_db=local_sites_in_db,
                status='P'))

        with self.assertQueries(equeries):
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

        self.client.login(username='admin', password='admin')

        user = User.objects.get(username='admin')
        grumpy = User.objects.get(username='grumpy')

        profile = user.get_profile()
        profile.starred_groups.clear()

        review_request_pks: List[int] = []

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

            if submitter is user:
                review_request_pks.append(review_request.pk)

        # This will be ordered with newest at the top.
        review_request_pks.reverse()

        self._prefetch_cached(local_site=local_site,
                              user=user)

        equeries = self._build_datagrid_equeries(
            user=user,
            profile=profile,
            local_site=local_site,
            local_sites_in_db=local_sites_in_db,
            review_request_pks=review_request_pks,
            extra=self._build_extra(user=user,
                                    include_new_review_count=True),
            include_star_column=True,
            rows_q_result=get_review_requests_from_user_q(
                user=user,
                from_user=user,
                local_site=local_site,
                has_local_sites_in_db=local_sites_in_db,
                status='P'))

        with self.assertQueries(equeries):
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

        self.client.login(username='doc', password='doc')

        user = User.objects.get(username='doc')
        profile = user.get_profile()

        profile.starred_groups.clear()

        grumpy = User.objects.get(username='grumpy')

        review_request_pks: List[int] = []

        for i in range(10):
            if i < 5:
                submitter = user
            else:
                submitter = grumpy

            review_request = self.create_review_request(
                summary='Test %s' % (i + 1),
                submitter=submitter,
                local_site=local_site,
                local_id=i + 1,
                publish=True)

            if submitter is user:
                review_request_pks.append(review_request.pk)

        # This will be ordered with newest at the top.
        review_request_pks.reverse()

        self._prefetch_cached(local_site=local_site,
                              user=user)

        equeries = self._build_datagrid_equeries(
            user=user,
            profile=profile,
            local_site=local_site,
            local_sites_in_db=local_sites_in_db,
            review_request_pks=review_request_pks,
            rows_q_result=get_review_requests_from_user_q(
                user=user,
                from_user=user,
                local_site=local_site,
                has_local_sites_in_db=local_sites_in_db,
                status=None))

        with self.assertQueries(equeries):
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

        self.client.login(username='doc', password='doc')

        user = User.objects.get(username='doc')
        profile = user.get_profile()

        profile.starred_groups.clear()

        group = self.create_review_group(local_site=local_site)
        group.users.add(user)

        review_request_pks: List[int] = []

        for i in range(15):
            review_request = self.create_review_request(
                summary='Test %s' % (i + 1),
                publish=True,
                local_site=local_site,
                local_id=i + 1)

            if i < 5:
                review_request.target_people.add(user)
                review_request_pks.append(review_request.pk)
            elif i < 10:
                review_request.target_groups.add(group)

        # This will be ordered with newest at the top.
        review_request_pks.reverse()

        self._prefetch_cached(local_site=local_site,
                              user=user)

        equeries = self._build_datagrid_equeries(
            user=user,
            profile=profile,
            local_site=local_site,
            local_sites_in_db=local_sites_in_db,
            review_request_pks=review_request_pks,
            rows_q_result=get_review_requests_to_user_directly_q(
                user=user,
                to_user=user,
                to_user_profile=profile,
                local_site=local_site,
                status='P',
                has_local_sites_in_db=local_sites_in_db))

        with self.assertQueries(equeries):
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
        else:
            local_site_q = Q()

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

        review_request_pks: List[int] = []

        for i in range(15):
            review_request = self.create_review_request(
                summary='Test %s' % (i + 1),
                publish=True,
                local_site=local_site,
                local_id=i + 1)

            if i < 5:
                review_request.target_groups.add(group1)
                review_request_pks.append(review_request.pk)
            elif i < 10:
                review_request.target_groups.add(group2)

        # This will be ordered with newest at the top.
        review_request_pks.reverse()

        self._prefetch_cached(local_site=local_site,
                              user=user)

        load_state_equeries: ExpectedQueries = [
            {
                '__note__': 'Fetch the group being viewed',
                'model': Group,
                'where': (Q(name='devgroup') &
                          local_site_q),
            },
        ]

        if local_site:
            load_state_equeries += [
                {
                    '__note__': 'Fetch the accessed Local Site (again)',
                    'model': LocalSite,
                    'where': Q(id=local_site.pk),
                },
            ] + get_local_site_is_accessible_by_equeries(
                user=user,
                local_site=local_site)

        equeries = self._build_datagrid_equeries(
            user=user,
            profile=profile,
            local_site=local_site,
            local_sites_in_db=local_sites_in_db,
            review_request_pks=review_request_pks,
            load_state_equeries=load_state_equeries,
            rows_q_result=get_review_requests_to_group_q(
                to_group_name='devgroup',
                user=user,
                local_site=local_site,
                status='P',
                has_local_sites_in_db=local_sites_in_db))

        with self.assertQueries(equeries):
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
        else:
            local_site_q = Q()

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

        load_state_equeries: ExpectedQueries = [
            {
                '__note__': 'Fetch the group being viewed',
                'model': Group,
                'where': (Q(name='devgroup') &
                          local_site_q),
            },
        ]

        if local_site:
            load_state_equeries += [
                {
                    '__note__': 'Fetch the accessed Local Site (again)',
                    'model': LocalSite,
                    'where': Q(id=local_site.pk),
                },
            ] + get_local_site_is_accessible_by_equeries(
                user=user,
                local_site=local_site)

        equeries = self._build_datagrid_equeries(
            user=user,
            profile=profile,
            local_site=local_site,
            local_sites_in_db=local_sites_in_db,
            review_request_pks=[review_request.pk],
            load_state_equeries=load_state_equeries,
            rows_q_result=get_review_requests_to_group_q(
                to_group_name='devgroup',
                user=user,
                local_site=local_site,
                status='P',
                has_local_sites_in_db=local_sites_in_db))

        with self.assertQueries(equeries):
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

        equeries = get_http_request_start_equeries(
            user=user,
            local_site=local_site)
        equeries += get_user_local_site_profile_equeries(
            user=user,
            profile=profile,
            local_site=local_site)
        equeries += [
            {
                'model': Group,
                'where': (Q(name='devgroup') &
                          local_site_q),
            },
        ]

        with self.assertQueries(equeries):
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

        self.client.login(username='doc', password='doc')

        user = User.objects.get(username='doc')
        profile = user.get_profile()

        profile.starred_groups.clear()

        review_requests = []
        diffset_histories = []

        review_request_pks: List[int] = []

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
                review_request_pks.append(review_request.pk)

        # This will be ordered with newest at the top.
        review_request_pks.reverse()

        self._prefetch_cached(local_site=local_site,
                              user=user)

        equeries = self._build_datagrid_equeries(
            user=user,
            profile=profile,
            extra=self._build_extra(user=user,
                                    include_new_review_count=True,
                                    include_mycomments=True,
                                    include_publicreviewcount=True),
            local_site=local_site,
            local_sites_in_db=local_sites_in_db,
            review_request_pks=review_request_pks,
            include_star_column=True,
            include_to_me_column=True,
            column_data_select_related={
                'diffset_history',
                'repository',
            },
            rows_q_result=get_review_requests_to_user_q(
                user=user,
                to_user=user,
                to_user_profile=profile,
                local_site=local_site,
                has_local_sites_in_db=local_sites_in_db,
                status='P'))

        equeries += [
            {
                '__note__': 'Fetch the diffsets for each review request',
                'model': DiffSet,
                'where': Q(history__in=diffset_histories),
            },
            {
                '__note__': 'Fetch the target groups for each review request',
                'join_types': {
                    'reviews_reviewrequest_target_groups': 'INNER JOIN',
                },
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
                '__note__': 'Fetch the target users for each review request',
                'join_types': {
                    'reviews_reviewrequest_target_people': 'INNER JOIN',
                },
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

        with self.assertQueries(equeries):
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

        equeries = self._build_datagrid_equeries(
            user=user,
            profile=profile,
            local_site=local_site,
            local_sites_in_db=local_sites_in_db,
            review_request_pks=[
                muted.pk,
                archived.pk,
                visible.pk,
            ],
            include_archived=True,
            rows_q_result=get_review_requests_to_user_q(
                user=user,
                to_user=user,
                to_user_profile=profile,
                local_site=local_site,
                has_local_sites_in_db=local_sites_in_db,
                status='P'))

        with self.assertQueries(equeries):
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

        equeries = self._build_datagrid_equeries(
            user=user,
            profile=profile,
            local_site=local_site,
            local_sites_in_db=local_sites_in_db,
            review_request_pks=[],
            rows_q_result=get_review_requests_to_user_q(
                user=user,
                to_user=user,
                to_user_profile=profile,
                local_site=local_site,
                has_local_sites_in_db=local_sites_in_db,
                status='P'))

        with self.assertQueries(equeries):
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

        equeries = self._build_datagrid_equeries(
            user=user,
            profile=profile,
            local_site=local_site,
            local_sites_in_db=local_sites_in_db,
            review_request_pks=[
                review_request4.pk,
                review_request3.pk,
                review_request2.pk,
            ],
            sidebar_equeries=[
                {
                    '__note__': (
                        "Fetch the list of a user's starred review groups"
                    ),
                    'join_types': {
                        'accounts_profile_starred_groups': 'INNER JOIN',
                    },
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
            ],
            rows_q_result=get_review_requests_to_user_q(
                user=user,
                to_user=user,
                to_user_profile=profile,
                local_site=local_site,
                has_local_sites_in_db=local_sites_in_db,
                target_groups=[
                    devgroup,
                    privgroup,
                ],
                status='P'))

        # Now load the dashboard and get the sidebar items.
        with self.assertQueries(equeries):
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

    def _build_datagrid_equeries(
        self,
        *,
        user: User,
        profile: Profile,
        review_request_pks: List[int],
        rows_q_result: ExpectedQResult,
        extra: Dict[str, Any] = {},
        load_state_equeries: ExpectedQueries = [],
        sidebar_equeries: ExpectedQueries = [],
        local_site: Optional[LocalSite] = None,
        local_sites_in_db: bool = False,
        include_archived: bool = False,
        include_star_column: bool = False,
        include_to_me_column: bool = False,
        column_data_select_related: Set[str] = set(),
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

            rows_q_result (dict):
                The result for a Q-expression for the datagrid rows queryset.

            extra (dict, optional):
                Extra queries to add to the rows queryset.

            load_state_equeries (list of dict, optional):
                Additional expected queries to add to the datagrid
                state-loading phase.

            sidebar_equeries (list of dict, optional):
                Additional expected queries to add to the sidebar-rendering
                phase.

            local_site (reviewboard.site.models.LocalSite, optional):
                The Local Site that's being accessed, if any.

            local_sites_in_db (bool, optional):
                Whether the database contains any Local Sites.

            include_archived (bool, optional):
                Whether archived review requests will be returned in results.

            include_star_column (bool, optional):
                Whether the star column will be included in the list of
                enabled dashboard columns.

            include_to_me_column (bool, optional):
                Whether the To Me column will be included in the list of
                enabled dashboard columns.

            column_data_select_related (set of str, optional):
                Any additional relations included when selecting related
                models for the columns.

        Returns:
            list of dict:
            The list of expected queries.
        """
        if local_sites_in_db:
            local_site_q = Q(local_site=local_site)
        else:
            local_site_q = Q()

        if not extra:
            extra = self._build_extra(user=user,
                                      include_new_review_count=True,
                                      include_mycomments=True)

        rows_q = rows_q_result['q']
        rows_q_tables = rows_q_result['tables']
        rows_q_num_joins = len(rows_q_tables) - 1
        rows_q_join_types = rows_q_result.get('join_types', {})

        equeries = get_http_request_start_equeries(
            user=user,
            local_site=local_site)
        equeries += get_user_local_site_profile_equeries(
            user=user,
            profile=profile,
            local_site=local_site)
        equeries += load_state_equeries
        equeries += rows_q_result.get('prep_equeries', [])
        equeries += [
            {
                '__note__': "Fetch the list of a user's review groups",
                'join_types': {
                    'reviews_group_users': 'INNER JOIN',
                },
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
        ]
        equeries += sidebar_equeries
        equeries += [
            {
                '__note__': 'Update datagrid state on the user profile',
                'type': 'UPDATE',
                'model': Profile,
                'where': Q(pk=user.pk),
            },
        ]

        if include_archived:
            equeries += [
                {
                    '__note__': (
                        'Fetch the number of items across all datagrid pages '
                        'with archived review requests shown'
                    ),
                    'annotations': {'__count': Count('*')},
                    'join_types': rows_q_join_types,
                    'model': ReviewRequest,
                    'num_joins': rows_q_num_joins,
                    'tables': rows_q_tables,
                    'where': (Q(rows_q) &
                              Q(local_site=local_site)),
                },
            ]

            if review_request_pks:
                equeries += [
                    {
                        '__note__': (
                            'Fetch the IDs of the items for one page with '
                            'archived review requests shown'
                        ),
                        'join_types': rows_q_join_types,
                        'model': ReviewRequest,
                        'num_joins': rows_q_num_joins,
                        'tables': rows_q_tables,
                        'values_select': ('pk',),
                        'extra': extra,
                        'where': (Q(rows_q) &
                                  Q(local_site=local_site)),
                        'order_by': ('-last_updated',),
                        'distinct': True,
                        'limit': len(review_request_pks),
                    },
                ]
        else:
            equeries += [
                {
                    '__note__': (
                        'Fetch the number of items across all datagrid pages'
                    ),
                    'annotations': {'__count': Count('*')},
                    'join_types': rows_q_join_types,
                    'model': ReviewRequest,
                    'num_joins': rows_q_num_joins,
                    'tables': rows_q_tables,
                    'where': (Q(rows_q) &
                              ~Q(__Q__subquery__=1) &
                              Q(local_site=local_site)),

                    'subqueries': [
                        {
                            'model': ReviewRequestVisit,
                            'values_select': ('review_request_id',),
                            'where': (Q(user=user) &
                                      ~Q(visibility='V')),
                        },
                    ],
                },
            ]

            if review_request_pks:
                equeries += [
                    {
                        '__note__': 'Fetch the IDs of the items for one page',
                        'join_types': rows_q_join_types,
                        'model': ReviewRequest,
                        'num_joins': rows_q_num_joins,
                        'tables': rows_q_tables,
                        'values_select': ('pk',),
                        'extra': extra,
                        'where': (Q(rows_q) &
                                  ~Q(__Q__subquery__=1) &
                                  Q(local_site=local_site)),
                        'order_by': ('-last_updated',),
                        'distinct': True,
                        'limit': len(review_request_pks),

                        'subqueries': [
                            {
                                'model': ReviewRequestVisit,
                                'values_select': ('review_request_id',),
                                'where': (Q(user=user) &
                                          ~Q(visibility='V')),
                            },
                        ],
                    },
                ]

        if include_star_column:
            equeries += [
                {
                    '__note__': (
                        "Starred column: Fetch the IDs of the page's review "
                        "requests that are starred"
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

        if include_to_me_column:
            equeries += [
                {
                    '__note__': (
                        "To Me column: Fetch the IDs of the page's review "
                        "requests that are targeting the user"
                    ),
                    'join_types': {
                        'reviews_reviewrequest_target_people': 'INNER JOIN',
                    },
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

        if review_request_pks:
            if local_site is not None:
                equeries += [
                    {
                        '__note__': (
                            'Fetch the data for one page based on the IDs '
                            'on the Local Site'
                        ),
                        'model': ReviewRequest,
                        'select_related': column_data_select_related | {
                            'local_site',
                            'submitter',
                        },
                        'extra': extra,
                        'where': Q(pk__in=review_request_pks),
                    },
                ]
            else:
                equeries += [
                    {
                        '__note__': (
                            'Fetch the data for one page based on the IDs'
                        ),
                        'model': ReviewRequest,
                        'select_related': column_data_select_related | {
                            'submitter'
                        },
                        'extra': extra,
                        'where': Q(pk__in=review_request_pks),
                    },
                ]

        return equeries

    def _build_extra(
        self,
        *,
        user: User,
        include_new_review_count: bool = False,
        include_mycomments: bool = False,
        include_publicreviewcount: bool = False,
    ) -> Dict[str, Any]:
        """Return data for the extra queries for the datagrid querysets.

        Args:
            user (django.contrib.auth.models.User):
                The user performing the request.

            include_new_review_count (bool, optional):
                Whether to include the ``new_review_count`` column information.

            include_mycomments (bool, optional):
                Whether to include the ``mycomments`` column information.

            include_publicreviewcount (bool, optional):
                Whether to include the ``publicreviewcount`` column
                information.

        Returns:
            dict:
            The resulting extra query dictionary.
        """
        user_id = user.pk

        extra: Dict[str, Any] = {
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
                   AND accounts_reviewrequestvisit.user_id = {user_id}
            """, []),
        }

        if include_new_review_count:
            extra['new_review_count'] = (f"""
                SELECT COUNT(*)
                  FROM reviews_review, accounts_reviewrequestvisit
                  WHERE reviews_review.public
                    AND reviews_review.review_request_id =
                        reviews_reviewrequest.id
                    AND accounts_reviewrequestvisit.review_request_id =
                        reviews_reviewrequest.id
                    AND accounts_reviewrequestvisit.user_id = {user_id}
                    AND reviews_review.timestamp >
                        accounts_reviewrequestvisit.timestamp
                    AND reviews_review.user_id != {user_id}
            """, [])

        if include_mycomments:
            extra.update({
                'mycomments_my_reviews': (f"""
                    SELECT COUNT(1)
                      FROM reviews_review
                      WHERE reviews_review.user_id = {user_id}
                        AND reviews_review.review_request_id =
                            reviews_reviewrequest.id
                """, []),
                'mycomments_private_reviews': (f"""
                    SELECT COUNT(1)
                      FROM reviews_review
                      WHERE reviews_review.user_id = {user_id}
                        AND reviews_review.review_request_id =
                            reviews_reviewrequest.id
                        AND NOT reviews_review.public
                """, []),
                'mycomments_shipit_reviews': (f"""
                    SELECT COUNT(1)
                      FROM reviews_review
                      WHERE reviews_review.user_id = {user_id}
                        AND reviews_review.review_request_id =
                            reviews_reviewrequest.id
                        AND reviews_review.ship_it
                """, []),
            })

        if include_publicreviewcount:
            extra['publicreviewcount_count'] = ("""
                SELECT COUNT(*)
                  FROM reviews_review
                 WHERE reviews_review.public
                   AND reviews_review.base_reply_to_id is NULL
                   AND reviews_review.review_request_id =
                       reviews_reviewrequest.id
            """, [])

        return extra
