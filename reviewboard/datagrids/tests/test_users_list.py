"""Unit tests for the users list page.

Version Added:
    5.0.7
"""

from __future__ import annotations

from django.contrib.auth.models import User
from django.db.models import Count, Q
from djblets.testing.decorators import add_fixtures

from reviewboard.accounts.models import Profile
from reviewboard.datagrids.tests.base import BaseViewTestCase
from reviewboard.reviews.models import ReviewRequest
from reviewboard.site.models import LocalSite


class UsersDataGridTests(BaseViewTestCase):
    """Unit tests for the users view."""

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
                'where': Q(is_active=True),
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
                'where': (Q(username__istartswith='A') &
                          Q(is_active=True)),
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

    @add_fixtures(['test_users'])
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
                'where': Q(is_active=True),
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

    @add_fixtures(['test_users'])
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
                'where': Q(is_active=True),
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

    @add_fixtures(['test_users'])
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
                'where': Q(is_active=True),
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

    @add_fixtures(['test_users'])
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
                'where': Q(is_active=True),
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

    @add_fixtures(['test_users'])
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
                'where': Q(is_active=True),
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

    @add_fixtures(['test_users'])
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
                'where': Q(is_active=True),
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

    @add_fixtures(['test_site', 'test_users'])
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
                'where': Q(is_active=True),
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

    @add_fixtures(['test_site', 'test_users'])
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
                'num_joins': 1,
                'tables': {
                    'auth_user',
                    'site_localsite_users',
                },
                'where': Q(local_site=local_site) & Q(is_active=True),
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
