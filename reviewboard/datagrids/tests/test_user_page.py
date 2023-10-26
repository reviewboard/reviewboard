"""Unit tests for the user page.

Version Added:
    5.0.7
"""

from __future__ import annotations

from django.contrib.auth.models import User
from django.db.models import Count, Q
from django.urls import reverse
from djblets.testing.decorators import add_fixtures

from reviewboard.accounts.models import Profile
from reviewboard.datagrids.builtin_items import UserGroupsItem, UserProfileItem
from reviewboard.datagrids.tests.base import BaseViewTestCase
from reviewboard.reviews.models import Group, Review, ReviewRequest
from reviewboard.site.models import LocalSite


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

        # Prime the cache.
        LocalSite.objects.has_local_sites()

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
                'num_joins': 5,
                'tables': {
                    'auth_user',
                    'reviews_group',
                    'reviews_review',
                    'reviews_reviewrequest',
                    'reviews_reviewrequest_target_groups',
                    'scmtools_repository',
                },
                'where': (
                    Q(Q(base_reply_to=None) &
                      Q(user__username='grumpy') &
                      Q(Q(review_request__repository=None) |
                        Q(review_request__repository__public=True)) &
                      Q(Q(review_request__target_groups=None) |
                        Q(review_request__target_groups__invite_only=False)) &
                      Q(public=True)) &
                    Q(review_request__local_site=None)
                ),
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
        assert datagrid is not None

        self.assertEqual(len(datagrid.rows), 5)
        self.assertEqual(datagrid.rows[0]['object'], reviews[4])
        self.assertEqual(datagrid.rows[1]['object'], reviews[3])
        self.assertEqual(datagrid.rows[2]['object'], reviews[2])
        self.assertEqual(datagrid.rows[3]['object'], reviews[1])
        self.assertEqual(datagrid.rows[4]['object'], reviews[0])
