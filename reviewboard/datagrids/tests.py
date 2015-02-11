from __future__ import print_function, unicode_literals

from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.utils import six
from djblets.siteconfig.models import SiteConfiguration
from djblets.testing.decorators import add_fixtures

from reviewboard.datagrids.builtin_items import UserGroupsItem, UserProfileItem
from reviewboard.reviews.models import Group, ReviewRequest, ReviewRequestDraft
from reviewboard.testing import TestCase


class BaseViewTestCase(TestCase):
    def setUp(self):
        super(BaseViewTestCase, self).setUp()

        self.siteconfig = SiteConfiguration.objects.get_current()
        self.siteconfig.set("auth_require_sitewide_login", False)
        self.siteconfig.save()

    def _get_context_var(self, response, varname):
        for context in response.context:
            if varname in context:
                return context[varname]

        return None


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
        self.siteconfig.set("auth_require_sitewide_login", True)
        self.siteconfig.save()

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
        self.assertEqual(len(sidebar_items), 2)

        # Test the Outgoing section.
        section = sidebar_items[0]
        self.assertEqual(six.text_type(section.label), 'Outgoing')
        self.assertEqual(len(section.items), 2)
        self.assertEqual(six.text_type(section.items[0].label), 'All')
        self.assertEqual(section.items[0].count, 1)
        self.assertEqual(six.text_type(section.items[1].label), 'Open')
        self.assertEqual(section.items[1].count, 1)

        # Test the Incoming section.
        section = sidebar_items[1]
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
        self.siteconfig.set("auth_require_sitewide_login", True)
        self.siteconfig.save()

        response = self.client.get('/groups/')
        self.assertEqual(response.status_code, 302)


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
        self.assertEqual(datagrid.rows[1]['object'].username, 'doc')
        self.assertEqual(datagrid.rows[2]['object'].username, 'dopey')
        self.assertEqual(datagrid.rows[3]['object'].username, 'grumpy')

    @add_fixtures(['test_users'])
    def test_as_anonymous_and_redirect(self):
        """Testing users_list view as anonymous with anonymous
        access disabled
        """
        self.siteconfig.set("auth_require_sitewide_login", True)
        self.siteconfig.save()

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
