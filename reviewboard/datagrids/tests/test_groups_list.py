"""Unit tests for the groups page.

Version Added:
    5.0.7
"""

from __future__ import annotations

from django.db.models import Count, Q
from djblets.testing.decorators import add_fixtures

from reviewboard.datagrids.tests.base import BaseViewTestCase
from reviewboard.reviews.models import Group, ReviewRequest


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
