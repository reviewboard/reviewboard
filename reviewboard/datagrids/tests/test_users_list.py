"""Unit tests for the users list page.

Version Added:
    5.0.7
"""

from __future__ import annotations

from typing import Optional

from django.contrib.auth.models import User
from django.db.models import Count, Q
from djblets.testing.decorators import add_fixtures

from reviewboard.accounts.models import Profile
from reviewboard.datagrids.tests.base import BaseViewTestCase
from reviewboard.reviews.models import ReviewRequest
from reviewboard.site.models import LocalSite


class UsersDataGridTests(BaseViewTestCase):
    """Unit tests for the users view."""

    datagrid_url = '/users/'

    @add_fixtures(['test_users'])
    def test_with_access(self):
        """Testing users_list view"""
        self._test_with_access()

    @add_fixtures(['test_site', 'test_users'])
    def test_with_access_with_local_site(self):
        """Testing users_list view on a Local Site"""
        self._test_with_access(with_local_site=True,
                               local_sites_in_db=True)

    @add_fixtures(['test_site', 'test_users'])
    def test_with_access_with_local_sites_in_db(self):
        """Testing users_list view with Local Sites in the database"""
        self._test_with_access(local_sites_in_db=True)

    @add_fixtures(['test_users'])
    def test_with_access_with_letter(self):
        """Testing users_list view with ?letter="""
        self._test_with_access_with_letter()

    @add_fixtures(['test_site', 'test_users'])
    def test_with_access_with_letter_with_local_site(self):
        """Testing users_list view with ?letter= on a Local Site"""
        self._test_with_access_with_letter(with_local_site=True,
                                           local_sites_in_db=True)

    @add_fixtures(['test_site', 'test_users'])
    def test_with_access_with_letter_with_local_sites_in_db(self):
        """Testing users_list view with ?letter= with Local Sites in the
        database
        """
        self._test_with_access_with_letter(local_sites_in_db=True)

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
        self._test_all_profiles_public()

    @add_fixtures(['test_site', 'test_users'])
    def test_all_profiles_public_with_local_site(self):
        """Testing UsersDataGrid when all user profiles are public on a
        Local Site
        """
        self._test_all_profiles_public(with_local_site=True,
                                       local_sites_in_db=True)

    @add_fixtures(['test_site', 'test_users'])
    def test_all_profiles_public_with_local_sites_in_db(self):
        """Testing UsersDataGrid when all user profiles are public with
        Local Sites in the database
        """
        self._test_all_profiles_public(local_sites_in_db=True)

    @add_fixtures(['test_users'])
    def test_all_profiles_public_anonymous(self):
        """Testing UsersDataGrid when all user profiles are public and
        the user is anonymous
        """
        self._test_all_profiles_public_anonymous()

    @add_fixtures(['test_site', 'test_users'])
    def test_all_profiles_public_anonymous_with_local_site(self):
        """Testing UsersDataGrid when all user profiles are public and
        the user is anonymous on a Local Site
        """
        self._test_all_profiles_public_anonymous(with_local_site=True,
                                                 local_sites_in_db=True)

    @add_fixtures(['test_site', 'test_users'])
    def test_all_profiles_public_anonymous_with_local_sites_in_db(self):
        """Testing UsersDataGrid when all user profiles are public and
        the user is anonymous with Local Sites in the database
        """
        self._test_all_profiles_public_anonymous(local_sites_in_db=True)

    @add_fixtures(['test_users'])
    def test_profile_not_exists(self):
        """Testing UsersDataGrid when a profile does not exist"""
        self._test_profile_not_exists()

    @add_fixtures(['test_site', 'test_users'])
    def test_profile_not_exists_with_local_site(self):
        """Testing UsersDataGrid when a profile does not exist on a Local Site
        """
        self._test_profile_not_exists(with_local_site=True,
                                      local_sites_in_db=True)

    @add_fixtures(['test_site', 'test_users'])
    def test_profile_not_exists_with_local_sites_in_db(self):
        """Testing UsersDataGrid when a profile does not exist with Local Sites
        in the database
        """
        self._test_profile_not_exists(local_sites_in_db=True)

    @add_fixtures(['test_users'])
    def test_all_profiles_private(self):
        """Testing UsersDataGrid when all user profiles are private"""
        self._test_all_profiles_private()

    @add_fixtures(['test_site', 'test_users'])
    def test_all_profiles_private_with_local_site(self):
        """Testing UsersDataGrid when all user profiles are private on a
        Local Site
        """
        self._test_all_profiles_private(with_local_site=True,
                                        local_sites_in_db=True)

    @add_fixtures(['test_site', 'test_users'])
    def test_all_profiles_private_with_local_sites_in_db(self):
        """Testing UsersDataGrid when all user profiles are private with
        Local Sites in the database
        """
        self._test_all_profiles_private(local_sites_in_db=True)

    @add_fixtures(['test_users'])
    def test_all_profiles_private_anonymous(self):
        """Testing UsersDataGrid when all users profiles are private and the
        user is anonymous
        """
        self._test_all_profiles_private_anonymous()

    @add_fixtures(['test_site', 'test_users'])
    def test_all_profiles_private_anonymous_with_local_site(self):
        """Testing UsersDataGrid when all users profiles are private and the
        user is anonymous on a Local Site
        """
        self._test_all_profiles_private_anonymous(with_local_site=True,
                                                  local_sites_in_db=True)

    @add_fixtures(['test_site', 'test_users'])
    def test_all_profiles_private_anonymous_with_local_sites_in_db(self):
        """Testing UsersDataGrid when all users profiles are private and the
        user is anonymous with Local Sites in the database
        """
        self._test_all_profiles_private_anonymous(local_sites_in_db=True)

    @add_fixtures(['test_users'])
    def test_all_profiles_private_admin(self):
        """Testing UsersDataGrid when all users profiles are private and the
        user is an admin
        """
        self._test_all_profiles_private_admin()

    @add_fixtures(['test_site', 'test_users'])
    def test_all_profiles_private_admin_with_local_site(self):
        """Testing UsersDataGrid when all users profiles are private and the
        user is an admin on a Local Site
        """
        self._test_all_profiles_private_admin(with_local_site=True,
                                              local_sites_in_db=True)

    @add_fixtures(['test_users', 'test_site'])
    def test_all_profile_private_local_site_admin(self):
        """Testing UsersDataGrid when all profiles are private for a LocalSite
        admin
        """
        Profile.objects.create(user_id=3)
        Profile.objects.all().update(is_private=True)
        self.client.login(username='doc', password='doc')

        user = User.objects.get(username='doc')
        profile = user.get_profile()

        self._prefetch_cached(user=user)

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
                'model': Profile,
                'type': 'UPDATE',
                'where': Q(pk=profile.pk),
            },
            {
                'annotations': {'__count': Count('*')},
                'model': User,
                'where': Q(is_active=True),
            },
            {
                'distinct': True,
                'limit': 4,
                'model': User,
                'order_by': ('username',),
                'values_select': ('pk',),
                'where': Q(is_active=True),
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
        assert datagrid is not None

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

    @add_fixtures(['test_users', 'test_site'])
    def test_all_profile_private_local_site_admin_local_site(self):
        """Testing UsersDataGrid when all profiles are private for a LocalSite
        admin on a LocalSite
        """
        dopey = User.objects.get(username='dopey')
        Profile.objects.create(user=dopey)
        Profile.objects.all().update(is_private=True)

        local_site = LocalSite.objects.get(name='local-site-2')

        self.client.login(username='doc', password='doc')

        user = User.objects.get(username='doc')
        profile = user.get_profile()

        self._prefetch_cached(local_site=local_site,
                              user=user)

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
                'extra': {
                    'a': ('1', []),
                },
                'limit': 1,
                'model': User,
                'num_joins': 1,
                'tables': {
                    'auth_user',
                    'site_localsite_users',
                },
                'where': Q(local_site__id=local_site.pk) & Q(pk=user.pk),
            },
            {
                'model': Profile,
                'type': 'UPDATE',
                'where': Q(pk=profile.pk),
            },
            {
                'annotations': {'__count': Count('*')},
                'model': User,
                'num_joins': 1,
                'tables': {
                    'auth_user',
                    'site_localsite_users',
                },
                'where': Q(local_site=local_site) & Q(is_active=True),
            },
            {
                'distinct': True,
                'limit': 2,
                'model': User,
                'num_joins': 1,
                'order_by': ('username',),
                'tables': {
                    'auth_user',
                    'site_localsite_users',
                },
                'values_select': ('pk',),
                'where': Q(local_site=local_site) & Q(is_active=True),
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
        assert datagrid is not None

        self.assertEqual(len(datagrid.rows), 2)

        for row in datagrid.rows:
            row_user = row['object']
            self.assertInHTML('<a href="/s/local-site-2/users/%s/">%s</a>'
                              % (row_user.username,
                                 row_user.get_full_name()),
                              row['cells'][0])

    def _test_with_access(
        self,
        *,
        with_local_site: bool = False,
        local_sites_in_db: bool = False,
    ) -> None:
        """Common tests for a user with access to the datagrid.

        This accesses the users datagrid as a logged-in user with access
        to the global site or Local Site (depending on the test), checking
        queries and datagrid row results.

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

        for i in range(5):
            self.create_user(username='test-user-%s' % (i + 1))

        all_users = User.objects.in_bulk()

        if local_site:
            local_site.users.add(*all_users.keys())

        self._prefetch_cached(local_site=local_site,
                              user=user)

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
                    'extra': {
                        'a': ('1', []),
                    },
                    'limit': 1,
                    'model': User,
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
            {
                'model': Profile,
                'type': 'UPDATE',
                'where': Q(pk=profile.pk),
            },
        ]

        if local_site:
            queries += [
                {
                    'annotations': {'__count': Count('*')},
                    'model': User,
                    'num_joins': 1,
                    'tables': {
                        'auth_user',
                        'site_localsite_users',
                    },
                    'where': (Q(local_site=local_site) &
                              Q(is_active=True)),
                },
                {
                    'distinct': True,
                    'limit': 9,
                    'model': User,
                    'num_joins': 1,
                    'order_by': ('username',),
                    'tables': {
                        'auth_user',
                        'site_localsite_users',
                    },
                    'values_select': ('pk',),
                    'where': (Q(local_site=local_site) &
                              Q(is_active=True)),
                },
            ]
        else:
            queries += [
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
                    'limit': 9,
                },
            ]

        queries += [
            {
                'model': User,
                'select_related': {'profile'},
                'where': Q(pk__in=[1, 2, 3, 4, 5, 6, 7, 8, 9]),
            },
        ]

        # NOTE: The following represent performance bugs due to bad
        #       queries. It's being tracked and will be resolved in a
        #       future change.
        for i in range(len(all_users)):
            query_user = all_users[i + 1]

            if (query_user.username == 'dopey' or
                query_user.username.startswith('test-user')):
                queries += [
                    {
                        'model': Profile,
                        'where': Q(user=query_user),
                    },
                    {
                        'model': Profile,
                        'type': 'INSERT',
                    },
                ]

            queries += [
                {
                    'model': ReviewRequest,
                    'num_joins': 1,
                    'tables': {
                        'reviews_reviewrequest',
                        'reviews_reviewrequest_target_people',
                    },
                    'annotations': {'__count': Count('*')},
                    'where': (Q(target_people__id=i + 1) &
                              Q(public=True) &
                              Q(status='P')),
                },
            ]

        with self.assertQueries(queries):
            response = self.client.get(
                self.get_datagrid_url(local_site=local_site))

        self.assertEqual(response.status_code, 200)

        datagrid = self._get_context_var(response, 'datagrid')
        assert datagrid is not None
        self.assertEqual(len(datagrid.rows), 9)
        self.assertEqual(datagrid.rows[0]['object'].username, 'admin')
        self.assertEqual(datagrid.rows[1]['object'].username, 'doc')
        self.assertEqual(datagrid.rows[2]['object'].username, 'dopey')
        self.assertEqual(datagrid.rows[3]['object'].username, 'grumpy')
        self.assertEqual(datagrid.rows[4]['object'].username, 'test-user-1')
        self.assertEqual(datagrid.rows[5]['object'].username, 'test-user-2')
        self.assertEqual(datagrid.rows[6]['object'].username, 'test-user-3')
        self.assertEqual(datagrid.rows[7]['object'].username, 'test-user-4')
        self.assertEqual(datagrid.rows[8]['object'].username, 'test-user-5')

    def _test_with_access_with_letter(
        self,
        *,
        with_local_site: bool = False,
        local_sites_in_db: bool = False,
    ) -> None:
        """Common tests for paginating by letter for a user with access.

        This accesses the users datagrid as a logged-in user with access
        to the global site or Local Site (depending on the test), checking
        queries and datagrid row results when filtering by a letter.

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

        matched_users = [
            self.create_user(username='aa'),
            self.create_user(username='ab'),
            self.create_user(username='ac'),
            User.objects.get(username='admin'),
        ]

        self.create_user(username='da')
        self.create_user(username='db')

        all_users = User.objects.in_bulk()

        if local_site:
            local_site.users.add(*all_users.keys())

        self._prefetch_cached(local_site=local_site,
                              user=user)

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
                    'where': (Q(local_site__id=local_site.pk) &
                              Q(pk=user.pk)),
                },
            ]

        queries += [
            {
                'type': 'UPDATE',
                'model': Profile,
                'where': Q(pk=profile.pk),
            },
        ]

        if local_site:
            queries += [
                {
                    'annotations': {'__count': Count('*')},
                    'model': User,
                    'num_joins': 1,
                    'tables': {
                        'auth_user',
                        'site_localsite_users',
                    },
                    'where': (Q(local_site=local_site) &
                              Q(username__istartswith='A') &
                              Q(is_active=True)),
                },
                {
                    'distinct': True,
                    'limit': 4,
                    'model': User,
                    'num_joins': 1,
                    'order_by': ('username',),
                    'tables': {
                        'auth_user',
                        'site_localsite_users',
                    },
                    'values_select': ('pk',),
                    'where': (Q(local_site=local_site) &
                              Q(username__istartswith='A') &
                              Q(is_active=True)),
                },
            ]
        else:
            queries += [
                {
                    'annotations': {'__count': Count('*')},
                    'model': User,
                    'where': (Q(username__istartswith='A') &
                              Q(is_active=True)),
                },
                {
                    'distinct': True,
                    'limit': 4,
                    'model': User,
                    'order_by': ('username',),
                    'values_select': ('pk',),
                    'where': (Q(username__istartswith='A') &
                              Q(is_active=True)),
                },
            ]

        queries += [
            {
                'model': User,
                'select_related': {'profile'},
                'where': Q(pk__in=[5, 6, 7, 1]),
            },
        ]

        # NOTE: The following represent performance bugs due to bad
        #       queries. It's being tracked and will be resolved in a
        #       future change.
        for query_user in matched_users:
            if query_user.username != 'admin':
                queries += [
                    {
                        'model': Profile,
                        'where': Q(user=query_user),
                    },
                    {
                        'model': Profile,
                        'type': 'INSERT',
                    },
                ]

            queries += [
                {
                    'model': ReviewRequest,
                    'num_joins': 1,
                    'tables': {
                        'reviews_reviewrequest',
                        'reviews_reviewrequest_target_people',
                    },
                    'annotations': {'__count': Count('*')},
                    'where': (Q(target_people__id=query_user.pk) &
                              Q(public=True) &
                              Q(status='P')),
                },
            ]

        with self.assertQueries(queries):
            response = self.client.get(
                '%s?letter=A' % self.get_datagrid_url(local_site=local_site))

        self.assertEqual(response.status_code, 200)

        datagrid = self._get_context_var(response, 'datagrid')
        assert datagrid is not None
        self.assertEqual(len(datagrid.rows), 4)
        self.assertEqual(datagrid.rows[0]['object'].username, 'aa')
        self.assertEqual(datagrid.rows[1]['object'].username, 'ab')
        self.assertEqual(datagrid.rows[2]['object'].username, 'ac')
        self.assertEqual(datagrid.rows[3]['object'].username, 'admin')

    def _test_all_profiles_public(
        self,
        *,
        with_local_site: bool = False,
        local_sites_in_db: bool = False,
    ) -> None:
        """Common tests for access when all profiles are public.

        This accesses the users datagrid as a logged-in user with access
        to the global site or Local Site (depending on the test), checking
        queries and datagrid row results and ensuring public profiles can
        be read.

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

        datagrid_url = self.get_datagrid_url(local_site=local_site)

        Profile.objects.create(user_id=3)
        self.client.login(username='doc', password='doc')

        if local_site:
            local_site.users.add(*User.objects.all())

        user = User.objects.get(username='doc')
        profile = user.get_profile()

        self._prefetch_cached(local_site=local_site,
                              user=user)

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
                    'where': (Q(local_site__id=local_site.pk) &
                              Q(pk=user.pk)),
                },
            ]

        queries += [
            {
                'type': 'UPDATE',
                'model': Profile,
                'where': Q(pk=profile.pk),
            },
        ]

        if local_site:
            queries += [
                {
                    'annotations': {'__count': Count('*')},
                    'model': User,
                    'num_joins': 1,
                    'tables': {
                        'auth_user',
                        'site_localsite_users',
                    },
                    'where': (Q(local_site=local_site) &
                              Q(is_active=True)),
                },
                {
                    'distinct': True,
                    'limit': 4,
                    'model': User,
                    'num_joins': 1,
                    'order_by': ('username',),
                    'tables': {
                        'auth_user',
                        'site_localsite_users',
                    },
                    'values_select': ('pk',),
                    'where': (Q(local_site=local_site) &
                              Q(is_active=True)),
                },
            ]
        else:
            queries += [
                {
                    'annotations': {'__count': Count('*')},
                    'model': User,
                    'where': Q(is_active=True),
                },
                {
                    'distinct': True,
                    'limit': 4,
                    'model': User,
                    'order_by': ('username',),
                    'values_select': ('pk',),
                    'where': Q(is_active=True),
                },
            ]

        queries += [
            {
                'model': User,
                'select_related': ('profile',),
                'where': Q(pk__in=[1, 2, 3, 4]),
            },
        ]

        with self.assertQueries(queries):
            response = self.client.get(f'{datagrid_url}?columns=fullname')

        self.assertEqual(response.status_code, 200)
        datagrid = self._get_context_var(response, 'datagrid')
        assert datagrid is not None

        self.assertEqual(len(datagrid.rows), 4)

        for row in datagrid.rows:
            row_user = row['object']
            self.assertInHTML('<a href="%s%s/">%s</a>'
                              % (datagrid_url,
                                 row_user.username,
                                 row_user.get_full_name()),
                              row['cells'][0])

    def _test_all_profiles_public_anonymous(
        self,
        *,
        with_local_site: bool = False,
        local_sites_in_db: bool = False,
    ) -> None:
        """Common tests for anonymous access with all public profiles.

        This accesses the users datagrid as an anonymous user with access
        to the global site or a public Local Site (depending on the test),
        checking queries and datagrid row results and ensuring public profiles
        can be read.

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

        datagrid_url = self.get_datagrid_url(local_site=local_site)

        Profile.objects.create(user_id=3)
        self.client.logout()

        if local_site:
            local_site.public = True
            local_site.save(update_fields=('public',))

            local_site.users.add(*User.objects.all())

        self._prefetch_cached(local_site=local_site)

        queries = []

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
                    'annotations': {'__count': Count('*')},
                    'model': User,
                    'num_joins': 1,
                    'tables': {
                        'auth_user',
                        'site_localsite_users',
                    },
                    'where': (Q(local_site=local_site) &
                              Q(is_active=True)),
                },
                {
                    'distinct': True,
                    'limit': 4,
                    'model': User,
                    'num_joins': 1,
                    'order_by': ('username',),
                    'tables': {
                        'auth_user',
                        'site_localsite_users',
                    },
                    'values_select': ('pk',),
                    'where': (Q(local_site=local_site) &
                              Q(is_active=True)),
                },
            ]
        else:
            queries += [
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
            ]

        queries += [
            {
                'model': User,
                'select_related': ('profile',),
                'where': Q(pk__in=[1, 2, 3, 4]),
            },
        ]

        with self.assertQueries(queries):
            response = self.client.get(f'{datagrid_url}?columns=fullname')

        self.assertEqual(response.status_code, 200)
        datagrid = self._get_context_var(response, 'datagrid')
        assert datagrid is not None

        self.assertEqual(len(datagrid.rows), 4)

        for row in datagrid.rows:
            row_user = row['object']
            self.assertInHTML('<a href="%s%s/"></a>' % (datagrid_url,
                                                        row_user.username),
                              row['cells'][0])

    def _test_profile_not_exists(
        self,
        *,
        with_local_site: bool = False,
        local_sites_in_db: bool = False,
    ) -> None:
        """Common tests for access and not all user profiles existing.

        This accesses the users datagrid as a logged-in user with access to the
        global site or a Local Site (depending on the test), checking queries
        and datagrid row results and ensuring missing profiles return the
        expected results.

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

        datagrid_url = self.get_datagrid_url(local_site=local_site)

        Profile.objects.all().update(is_private=True)
        self.client.login(username='doc', password='doc')

        user = User.objects.get(username='doc')
        profile = user.get_profile()

        dopey = User.objects.get(username='dopey')

        # Remove doc's admin status from other test Local Sites, so he's
        # never an admin for any other users. We want to test with minimal
        # visibility.
        user.local_site_admins.clear()

        if local_site:
            local_site.users.add(*User.objects.all())

        self._prefetch_cached(local_site=local_site,
                              user=user)

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
                    'where': Q(name=local_site.name),
                },
                {
                    'extra': {
                        'a': ('1', []),
                    },
                    'limit': 1,
                    'model': User,
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
            {
                'model': Profile,
                'type': 'UPDATE',
                'where': Q(pk=profile.pk),
            },
        ]

        if local_site:
            queries += [
                {
                    'annotations': {'__count': Count('*')},
                    'model': User,
                    'num_joins': 1,
                    'tables': {
                        'auth_user',
                        'site_localsite_users',
                    },
                    'where': (Q(local_site=local_site) &
                              Q(is_active=True)),
                },
                {
                    'distinct': True,
                    'limit': 4,
                    'model': User,
                    'num_joins': 1,
                    'order_by': ('username',),
                    'tables': {
                        'auth_user',
                        'site_localsite_users',
                    },
                    'values_select': ('pk',),
                    'where': (Q(local_site=local_site) &
                              Q(is_active=True)),
                },
            ]
        else:
            queries += [
                {
                    'annotations': {'__count': Count('*')},
                    'model': User,
                    'where': Q(is_active=True),
                },
                {
                    'distinct': True,
                    'limit': 4,
                    'model': User,
                    'order_by': ('username',),
                    'values_select': ('pk',),
                    'where': Q(is_active=True),
                },
            ]

        queries += [
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
                'model': Profile,
                'type': 'INSERT',
            },
        ]

        with self.assertQueries(queries):
            response = self.client.get(f'{datagrid_url}?columns=fullname')

        self.assertEqual(response.status_code, 200)

        datagrid = self._get_context_var(response, 'datagrid')
        assert datagrid is not None

        self.assertEqual(len(datagrid.rows), 4)

        rows_by_username = {
            row['object'].username: row
            for row in datagrid.rows
        }

        self.assertHTMLEqual(
            rows_by_username['admin']['cells'][0],
            f'<td class="has-link" colspan="2">'
            f' <a href="{datagrid_url}admin/"></a>'
            f'</td>')
        self.assertHTMLEqual(
            rows_by_username['doc']['cells'][0],
            f'<td class="has-link" colspan="2">'
            f' <a href="{datagrid_url}doc/">Doc Dwarf</a>'
            f'</td>')
        self.assertHTMLEqual(
            rows_by_username['dopey']['cells'][0],
            f'<td class="has-link" colspan="2">'
            f' <a href="{datagrid_url}dopey/">Dopey Dwarf</a>'
            f'</td>')
        self.assertHTMLEqual(
            rows_by_username['grumpy']['cells'][0],
            f'<td class="has-link" colspan="2">'
            f' <a href="{datagrid_url}grumpy/"></a>'
            f'</td>')

    def _test_all_profiles_private(
        self,
        *,
        with_local_site: bool = False,
        local_sites_in_db: bool = False,
    ) -> None:
        """Common tests for access and all private user profiles.

        This accesses the users datagrid as a logged-in user with access to the
        global site or a Local Site (depending on the test), checking queries
        and datagrid row results and that no private user profile data (aside
        from the user's) can be read.

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

        datagrid_url = self.get_datagrid_url(local_site=local_site)

        Profile.objects.create(user_id=3)
        Profile.objects.all().update(is_private=True)

        self.client.login(username='doc', password='doc')

        user = User.objects.get(username='doc')
        profile = user.get_profile()

        # Remove doc's admin status from other test Local Sites, so he's
        # never an admin for any other users. We want to test with minimal
        # visibility.
        user.local_site_admins.clear()

        if local_site:
            local_site.users.add(*User.objects.all())

        self._prefetch_cached(local_site=local_site,
                              user=user)

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
                    'where': Q(name=local_site.name),
                },
                {
                    'extra': {
                        'a': ('1', []),
                    },
                    'limit': 1,
                    'model': User,
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
            {
                'model': Profile,
                'type': 'UPDATE',
                'where': Q(pk=profile.pk),
            },
        ]

        if local_site:
            queries += [
                {
                    'annotations': {'__count': Count('*')},
                    'model': User,
                    'num_joins': 1,
                    'tables': {
                        'auth_user',
                        'site_localsite_users',
                    },
                    'where': (Q(local_site=local_site) &
                              Q(is_active=True)),
                },
                {
                    'distinct': True,
                    'limit': 4,
                    'model': User,
                    'num_joins': 1,
                    'order_by': ('username',),
                    'tables': {
                        'auth_user',
                        'site_localsite_users',
                    },
                    'values_select': ('pk',),
                    'where': (Q(local_site=local_site) &
                              Q(is_active=True)),
                },
            ]
        else:
            queries += [
                {
                    'annotations': {'__count': Count('*')},
                    'model': User,
                    'where': Q(is_active=True),
                },
                {
                    'distinct': True,
                    'limit': 4,
                    'model': User,
                    'order_by': ('username',),
                    'values_select': ('pk',),
                    'where': Q(is_active=True),
                },
            ]

        queries += [
            {
                'model': User,
                'select_related': ('profile',),
                'where': Q(pk__in=[1, 2, 3, 4]),
            },
        ]

        with self.assertQueries(queries):
            response = self.client.get(f'{datagrid_url}?columns=fullname')

        self.assertEqual(response.status_code, 200)

        datagrid = self._get_context_var(response, 'datagrid')
        assert datagrid is not None

        self.assertEqual(len(datagrid.rows), 4)

        rows_by_username = {
            row['object'].username: row
            for row in datagrid.rows
        }

        self.assertHTMLEqual(
            rows_by_username['admin']['cells'][0],
            f'<td class="has-link" colspan="2">'
            f' <a href="{datagrid_url}admin/"></a>'
            f'</td>')
        self.assertHTMLEqual(
            rows_by_username['doc']['cells'][0],
            f'<td class="has-link" colspan="2">'
            f' <a href="{datagrid_url}doc/">Doc Dwarf</a>'
            f'</td>')
        self.assertHTMLEqual(
            rows_by_username['dopey']['cells'][0],
            f'<td class="has-link" colspan="2">'
            f' <a href="{datagrid_url}dopey/"></a>'
            f'</td>')
        self.assertHTMLEqual(
            rows_by_username['grumpy']['cells'][0],
            f'<td class="has-link" colspan="2">'
            f' <a href="{datagrid_url}grumpy/"></a>'
            f'</td>')

    def _test_all_profiles_private_anonymous(
        self,
        *,
        with_local_site: bool = False,
        local_sites_in_db: bool = False,
    ) -> None:
        """Common tests for anonymous access and all private user profiles.

        This accesses the users datagrid as an anonymous user with access to
        the global site or a public Local Site (depending on the test),
        checking queries and datagrid row results and that no private user
        profile data can be read.

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

        datagrid_url = self.get_datagrid_url(local_site=local_site)

        Profile.objects.create(user_id=3)
        Profile.objects.all().update(is_private=True)
        self.client.logout()

        if local_site:
            local_site.public = True
            local_site.save(update_fields=('public',))
            local_site.users.add(*User.objects.all())

        self._prefetch_cached(local_site=local_site)

        queries = []

        if local_site:
            queries += [
                {
                    'model': LocalSite,
                    'where': Q(name=local_site.name),
                },
                {
                    'annotations': {'__count': Count('*')},
                    'model': User,
                    'num_joins': 1,
                    'tables': {
                        'auth_user',
                        'site_localsite_users',
                    },
                    'where': (Q(local_site=local_site) &
                              Q(is_active=True)),
                },
                {
                    'distinct': True,
                    'limit': 4,
                    'model': User,
                    'num_joins': 1,
                    'order_by': ('username',),
                    'tables': {
                        'auth_user',
                        'site_localsite_users',
                    },
                    'values_select': ('pk',),
                    'where': (Q(local_site=local_site) &
                              Q(is_active=True)),
                },
            ]
        else:
            queries += [
                {
                    'annotations': {'__count': Count('*')},
                    'model': User,
                    'where': Q(is_active=True),
                },
                {
                    'distinct': True,
                    'limit': 4,
                    'model': User,
                    'order_by': ('username',),
                    'values_select': ('pk',),
                    'where': Q(is_active=True),
                },
            ]

        queries += [
            {
                'model': User,
                'select_related': ('profile',),
                'where': Q(pk__in=[1, 2, 3, 4]),
            },
        ]

        with self.assertQueries(queries):
            response = self.client.get(f'{datagrid_url}?columns=fullname')

        self.assertEqual(response.status_code, 200)
        datagrid = self._get_context_var(response, 'datagrid')
        assert datagrid is not None

        self.assertEqual(len(datagrid.rows), 4)

        for row in datagrid.rows:
            row_user = row['object']
            self.assertInHTML('<a href="%s%s/"></a>' % (datagrid_url,
                                                        row_user.username),
                              row['cells'][0])

    def _test_all_profiles_private_admin(
        self,
        *,
        with_local_site: bool = False,
        local_sites_in_db: bool = False,
    ) -> None:
        """Common tests for admin access and all private user profiles.

        This accesses the users datagrid as an admin user, checking queries
        and datagrid row results and ensuring all private profiles can be
        read.

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

        datagrid_url = self.get_datagrid_url(local_site=local_site)

        Profile.objects.create(user_id=3)
        Profile.objects.all().update(is_private=True)
        self.client.login(username='admin', password='admin')

        user = User.objects.get(username='admin')
        profile = user.get_profile()

        if local_site:
            local_site.users.add(*User.objects.all())

        self._prefetch_cached(local_site=local_site,
                              user=user)

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
                    'where': Q(name=local_site.name),
                },
            ]

        queries += [
            {
                'model': Profile,
                'type': 'UPDATE',
                'where': Q(pk=profile.pk),
            },
        ]

        if local_site:
            queries += [
                {
                    'annotations': {'__count': Count('*')},
                    'model': User,
                    'num_joins': 1,
                    'tables': {
                        'auth_user',
                        'site_localsite_users',
                    },
                    'where': (Q(local_site=local_site) &
                              Q(is_active=True)),
                },
                {
                    'distinct': True,
                    'limit': 4,
                    'model': User,
                    'num_joins': 1,
                    'order_by': ('username',),
                    'tables': {
                        'auth_user',
                        'site_localsite_users',
                    },
                    'values_select': ('pk',),
                    'where': (Q(local_site=local_site) &
                              Q(is_active=True)),
                },
            ]
        else:
            queries += [
                {
                    'annotations': {'__count': Count('*')},
                    'model': User,
                    'where': Q(is_active=True),
                },
                {
                    'distinct': True,
                    'limit': 4,
                    'model': User,
                    'order_by': ('username',),
                    'values_select': ('pk',),
                    'where': Q(is_active=True),
                },
            ]

        queries += [
            {
                'model': User,
                'select_related': ('profile',),
                'where': Q(pk__in=[1, 2, 3, 4]),
            },
        ]

        with self.assertQueries(queries):
            response = self.client.get(f'{datagrid_url}?columns=fullname')

        self.assertEqual(response.status_code, 200)
        datagrid = self._get_context_var(response, 'datagrid')
        assert datagrid is not None

        self.assertEqual(len(datagrid.rows), 4)

        for row in datagrid.rows:
            row_user = row['object']
            self.assertInHTML('<a href="%s%s/">%s</a>'
                              % (datagrid_url,
                                 row_user.username,
                                 row_user.get_full_name()),
                              row['cells'][0])
