"""Unit tests for the All Review Requests page.

Version Added:
    5.0.7
"""

from __future__ import annotations

from django.contrib.auth.models import User
from djblets.testing.decorators import add_fixtures

from reviewboard.datagrids.tests.base import BaseViewTestCase
from reviewboard.reviews.models import ReviewRequest


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
