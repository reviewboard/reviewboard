from __future__ import print_function, unicode_literals

from django.contrib.auth.models import AnonymousUser, User
from django.core.cache import cache
from django.core.urlresolvers import reverse
from django.test.client import RequestFactory
from django.utils import six
from django.utils.safestring import SafeText
from djblets.datagrid.grids import DataGrid
from djblets.siteconfig.models import SiteConfiguration
from djblets.testing.decorators import add_fixtures

from reviewboard.accounts.models import Profile, ReviewRequestVisit
from reviewboard.datagrids.builtin_items import UserGroupsItem, UserProfileItem
from reviewboard.datagrids.columns import (FullNameColumn, SummaryColumn,
                                           UsernameColumn)
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

        repository1 = self.create_repository(public=False)
        repository1.users.add(user)
        self.create_review_request(summary='Test 3',
                                   repository=repository1,
                                   publish=True)

        group1 = self.create_review_group(invite_only=True)
        group1.users.add(user)
        review_request = self.create_review_request(summary='Test 4',
                                                    publish=True)
        review_request.target_groups.add(group1)

        # These are private
        repository2 = self.create_repository(public=False)
        self.create_review_request(summary='Test 5',
                                   repository=repository2,
                                   publish=True)

        group2 = self.create_review_group(invite_only=True)
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


class DashboardViewTests(BaseViewTestCase):
    """Unit tests for the dashboard view."""

    @add_fixtures(['test_users'])
    def test_incoming(self):
        """Testing dashboard view (incoming)"""
        self.client.login(username='doc', password='doc')

        user = User.objects.get(username='doc')

        review_request = self.create_review_request(summary='Test 1',
                                                    publish=True)
        review_request.target_people.add(user)

        review_request = self.create_review_request(summary='Test 2',
                                                    publish=True)
        review_request.target_people.add(user)

        review_request = self.create_review_request(summary='Test 3',
                                                    publish=True)

        response = self.client.get('/dashboard/', {'view': 'incoming'})
        self.assertEqual(response.status_code, 200)

        datagrid = self._get_context_var(response, 'datagrid')
        self.assertTrue(datagrid)
        self.assertEqual(len(datagrid.rows), 2)
        self.assertEqual(datagrid.rows[0]['object'].summary, 'Test 2')
        self.assertEqual(datagrid.rows[1]['object'].summary, 'Test 1')

    @add_fixtures(['test_users'])
    def test_outgoing(self):
        """Testing dashboard view (outgoing)"""
        self.client.login(username='admin', password='admin')

        user = User.objects.get(username='admin')

        self.create_review_request(summary='Test 1',
                                   submitter=user,
                                   publish=True)

        self.create_review_request(summary='Test 2',
                                   submitter=user,
                                   publish=True)

        self.create_review_request(summary='Test 3',
                                   submitter='grumpy',
                                   publish=True)

        response = self.client.get('/dashboard/', {'view': 'outgoing'})
        self.assertEqual(response.status_code, 200)

        datagrid = self._get_context_var(response, 'datagrid')
        self.assertTrue(datagrid)
        self.assertEqual(len(datagrid.rows), 2)
        self.assertEqual(datagrid.rows[0]['object'].summary, 'Test 2')
        self.assertEqual(datagrid.rows[1]['object'].summary, 'Test 1')

    @add_fixtures(['test_users'])
    def test_outgoing_mine(self):
        """Testing dashboard view (mine)"""
        self.client.login(username='doc', password='doc')

        self.create_review_request(summary='Test 1',
                                   submitter='doc',
                                   publish=True)
        self.create_review_request(summary='Test 2',
                                   submitter='doc',
                                   publish=True)
        self.create_review_request(summary='Test 3',
                                   submitter='grumpy',
                                   publish=True)

        response = self.client.get('/dashboard/', {'view': 'mine'})
        self.assertEqual(response.status_code, 200)

        datagrid = self._get_context_var(response, 'datagrid')
        self.assertTrue(datagrid is not None)
        self.assertEqual(len(datagrid.rows), 2)
        self.assertEqual(datagrid.rows[0]['object'].summary, 'Test 2')
        self.assertEqual(datagrid.rows[1]['object'].summary, 'Test 1')

    @add_fixtures(['test_users'])
    def test_to_me(self):
        """Testing dashboard view (to-me)"""
        self.client.login(username='doc', password='doc')

        user = User.objects.get(username='doc')

        group = self.create_review_group()
        group.users.add(user)

        review_request = self.create_review_request(summary='Test 1',
                                                    publish=True)
        review_request.target_people.add(user)

        review_request = self.create_review_request(summary='Test 2',
                                                    publish=True)
        review_request.target_people.add(user)

        review_request = self.create_review_request(summary='Test 3',
                                                    publish=True)
        review_request.target_groups.add(group)

        response = self.client.get('/dashboard/', {'view': 'to-me'})
        self.assertEqual(response.status_code, 200)

        datagrid = self._get_context_var(response, 'datagrid')
        self.assertTrue(datagrid)
        self.assertEqual(len(datagrid.rows), 2)
        self.assertEqual(datagrid.rows[0]['object'].summary, 'Test 2')
        self.assertEqual(datagrid.rows[1]['object'].summary, 'Test 1')

    @add_fixtures(['test_users'])
    def test_to_group_with_joined_groups(self):
        """Testing dashboard view with to-group and joined groups"""
        self.client.login(username='doc', password='doc')

        group = self.create_review_group(name='devgroup')
        group.users.add(User.objects.get(username='doc'))

        review_request = self.create_review_request(summary='Test 1',
                                                    publish=True)
        review_request.target_groups.add(group)

        review_request = self.create_review_request(summary='Test 2',
                                                    publish=True)
        review_request.target_groups.add(group)

        review_request = self.create_review_request(summary='Test 3',
                                                    publish=True)
        review_request.target_groups.add(
            self.create_review_group(name='test-group'))

        response = self.client.get('/dashboard/',
                                   {'view': 'to-group',
                                    'group': 'devgroup'})
        self.assertEqual(response.status_code, 200)

        datagrid = self._get_context_var(response, 'datagrid')
        self.assertTrue(datagrid)
        self.assertEqual(len(datagrid.rows), 2)
        self.assertEqual(datagrid.rows[0]['object'].summary, 'Test 2')
        self.assertEqual(datagrid.rows[1]['object'].summary, 'Test 1')

    @add_fixtures(['test_users'])
    def test_to_group_with_unjoined_public_group(self):
        """Testing dashboard view with to-group and unjoined public group"""
        self.client.login(username='doc', password='doc')

        group = self.create_review_group(name='devgroup')

        review_request = self.create_review_request(summary='Test 1',
                                                    publish=True)
        review_request.target_groups.add(group)

        response = self.client.get('/dashboard/',
                                   {'view': 'to-group',
                                    'group': 'devgroup'})
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
        self.assertEqual(six.text_type(section.label), 'Overview')

        # Test the "Outgoing" section.
        section = sidebar_items[1]
        self.assertEqual(six.text_type(section.label), 'Outgoing')
        self.assertEqual(len(section.items), 2)
        self.assertEqual(six.text_type(section.items[0].label), 'All')
        self.assertEqual(section.items[0].count, 1)
        self.assertEqual(six.text_type(section.items[1].label), 'Open')
        self.assertEqual(section.items[1].count, 1)

        # Test the "Incoming" section.
        section = sidebar_items[2]
        self.assertEqual(six.text_type(section.label), 'Incoming')
        self.assertEqual(len(section.items), 5)
        self.assertEqual(six.text_type(section.items[0].label), 'Open')
        self.assertEqual(section.items[0].count, 3)
        self.assertEqual(six.text_type(section.items[1].label), 'To Me')
        self.assertEqual(section.items[1].count, 1)
        self.assertEqual(six.text_type(section.items[2].label), 'Starred')
        self.assertEqual(section.items[2].count, 1)
        self.assertEqual(six.text_type(section.items[3].label), 'devgroup')
        self.assertEqual(section.items[3].count, 1)
        self.assertEqual(six.text_type(section.items[4].label), 'privgroup')
        self.assertEqual(section.items[4].count, 1)


class GroupListViewTests(BaseViewTestCase):
    """Unit tests for the group_list view."""

    @add_fixtures(['test_users'])
    def test_with_access(self):
        """Testing group_list view"""
        self.create_review_group(name='devgroup')
        self.create_review_group(name='emptygroup')
        self.create_review_group(name='newgroup')
        self.create_review_group(name='privgroup')

        response = self.client.get('/groups/')
        self.assertEqual(response.status_code, 200)

        datagrid = self._get_context_var(response, 'datagrid')
        self.assertTrue(datagrid)
        self.assertEqual(len(datagrid.rows), 4)
        self.assertEqual(datagrid.rows[0]['object'].name, 'devgroup')
        self.assertEqual(datagrid.rows[1]['object'].name, 'emptygroup')
        self.assertEqual(datagrid.rows[2]['object'].name, 'newgroup')
        self.assertEqual(datagrid.rows[3]['object'].name, 'privgroup')

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

        with self.assertNumQueries(6):
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

        with self.assertNumQueries(3):
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
        """Testing UsersDataGrid when a profile does exist"""
        Profile.objects.all().update(is_private=True)

        self.client.login(username='doc', password='doc')

        with self.assertNumQueries(11):
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

        with self.assertNumQueries(7):
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

        with self.assertNumQueries(3):
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

        with self.assertNumQueries(6):
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

        with self.assertNumQueries(7):
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
        Profile.objects.create(user_id=3)
        Profile.objects.all().update(is_private=True)
        self.client.login(username='doc', password='doc')

        with self.assertNumQueries(9):
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

    @add_fixtures(['test_users'])
    def test_with_access(self):
        """Testing users_list view"""
        response = self.client.get('/users/')
        self.assertEqual(response.status_code, 200)

        datagrid = self._get_context_var(response, 'datagrid')
        self.assertTrue(datagrid)
        self.assertEqual(len(datagrid.rows), 4)
        self.assertEqual(datagrid.rows[0]['object'].username, 'admin')

        response = self.client.get('/users/?letter=D')
        self.assertEqual(response.status_code, 200)

        datagrid = self._get_context_var(response, 'datagrid')
        self.assertTrue(datagrid)
        self.assertEqual(len(datagrid.rows), 2)
        self.assertEqual(datagrid.rows[0]['object'].username, 'doc')
        self.assertEqual(datagrid.rows[1]['object'].username, 'dopey')

        response = self.client.get('/users/?letter=G')
        self.assertEqual(response.status_code, 200)

        datagrid = self._get_context_var(response, 'datagrid')
        self.assertTrue(datagrid)
        self.assertEqual(len(datagrid.rows), 1)

        self.assertEqual(datagrid.rows[0]['object'].username, 'grumpy')

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

        self.create_review_request(summary='Summary 1', submitter=user,
                                   publish=True)

        review_request = self.create_review_request(summary='Summary 2',
                                                    submitter=user,
                                                    publish=True)
        review_request.target_groups.add(group2)

        response = self.client.get('/users/grumpy/')
        self.assertEqual(response.status_code, 200)

        datagrid = self._get_context_var(response, 'datagrid')
        self.assertIsNotNone(datagrid)
        self.assertEqual(len(datagrid.rows), 1)
        self.assertEqual(datagrid.rows[0]['object'].summary, 'Summary 1')

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
        self.assertEqual(six.text_type(section.label), 'Groups')
        self.assertEqual(len(section.items), 1)
        self.assertEqual(six.text_type(section.items[0].label),
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
        group.users.add(user1)
        group.users.add(user2)

        review_request1 = self.create_review_request(summary='Summary 1',
                                                     submitter=user1,
                                                     publish=True)
        review_request2 = self.create_review_request(summary='Summary 2',
                                                     submitter=user1,
                                                     publish=True)
        review_request2.target_groups.add(group)

        self.create_review(review_request1, user=user2,
                           publish=True)
        self.create_review(review_request2, user=user2,
                           publish=True)

        response = self.client.get('/users/grumpy/reviews/')
        self.assertEqual(response.status_code, 200)

        datagrid = self._get_context_var(response, 'datagrid')
        self.assertIsNotNone(datagrid)
        self.assertEqual(len(datagrid.rows), 1)
        self.assertEqual(datagrid.rows[0]['object'].review_request,
                         review_request1)


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
