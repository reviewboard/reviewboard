"""Unit tests for additions to django.contrib.auth.models.User."""

from uuid import UUID, uuid4

import kgb
from django.contrib.auth.models import AnonymousUser, User
from django.db.models import Q
from djblets.testing.decorators import add_fixtures

from reviewboard.accounts.models import Profile
from reviewboard.site.models import LocalSite
from reviewboard.testing import TestCase


class UserTests(kgb.SpyAgency, TestCase):
    """Unit tests for additions to django.contrib.auth.models.User."""

    fixtures = ['test_users']

    def test_get_profile(self):
        """Testing User.get_profile"""
        user = self.create_user(username='test1')
        profile = Profile.objects.create(user=user)

        # 1 query:
        #
        # 1. Fetch profile
        queries = [
            {
                'model': Profile,
                'where': Q(user=user),
            },
        ]

        with self.assertQueries(queries):
            new_profile = user.get_profile()

        self.assertEqual(new_profile, profile)
        self.assertIsNot(new_profile, profile)
        self.assertIs(new_profile.user, user)

        # A second call should hit cache.
        with self.assertNumQueries(0):
            self.assertIs(user.get_profile(), new_profile)

    def test_get_profile_with_no_profile(self):
        """Testing User.get_profile with no existing profile"""
        user = self.create_user(username='test1')

        # 4 queries:
        #
        # 1. Attempt to fetch profile
        # 2. Create savepoint
        # 3. Create Profile
        # 4. Release savepoint
        queries = [
            {
                'model': Profile,
                'where': Q(user=user),
            },
            {
                'model': Profile,
                'type': 'INSERT',
            },
        ]

        with self.assertQueries(queries, num_statements=4):
            new_profile = user.get_profile()

        self.assertIs(new_profile.user, user)
        self.assertIsNotNone(new_profile.pk)

        # A second call should hit cache.
        with self.assertNumQueries(0):
            self.assertIs(user.get_profile(), new_profile)

    def test_get_profile_with_prefetch_related(self):
        """Testing User.get_profile with prefetch_related"""
        user = self.create_user(username='test1')
        Profile.objects.create(user=user)

        # Now re-fetch.
        #
        # 2 queries:
        #
        # 1. Fetch users
        # 2. Fetch profiles for fetched user IDs
        queries = [
            {
                'model': User,
                'where': Q(username='test1'),
            },
            {
                'model': Profile,
                'where': Q(user__in=[user]),
            },
        ]

        with self.assertQueries(queries):
            user = list(
                User.objects
                .filter(username='test1')
                .prefetch_related('profile_set')
            )[0]

        with self.assertNumQueries(0):
            profile = user.get_profile()

        self.assertIs(profile.user, user)
        self.assertIsNotNone(profile.pk)

    def test_get_profile_with_select_related(self):
        """Testing User.get_profile with select_related"""
        user = self.create_user(username='test1')
        Profile.objects.create(user=user)

        # Now re-fetch.
        #
        # 1 query:
        #
        # 1. Fetch users + profiles
        queries = [
            {
                'model': User,
                'select_related': {'profile'},
                'where': Q(username='test1'),
            },
        ]

        with self.assertQueries(queries):
            user = list(
                User.objects
                .filter(username='test1')
                .select_related('profile')
            )[0]

        with self.assertNumQueries(0):
            profile = user.get_profile()

        self.assertIs(profile.user, user)
        self.assertIsNotNone(profile.pk)

    def test_get_profile_with_no_profile_and_create_if_missing_false(self):
        """Testing User.get_profile with no existing profile and
        create_if_missing=False
        """
        user = self.create_user(username='test1')

        # 1 query:
        #
        # 1. Attempt to fetch profile
        queries = [
            {
                'model': Profile,
                'where': Q(user=user),
            },
        ]

        with self.assertQueries(queries):
            with self.assertRaises(Profile.DoesNotExist):
                user.get_profile(create_if_missing=False)

    def test_get_profile_with_cached_only_and_in_cache(self):
        """Testing User.get_profile with cached_only=True and profile already
        in object cache
        """
        user = self.create_user(username='test1')
        profile = user.get_profile()

        with self.assertNumQueries(0):
            new_profile = user.get_profile(cached_only=True)

        self.assertIs(new_profile, profile)

    def test_get_profile_with_cached_only_and_not_in_cache(self):
        """Testing User.get_profile with cached_only=True and profile not
        in object cache
        """
        user = self.create_user(username='test1')
        Profile.objects.create(user=user)

        with self.assertNumQueries(0):
            self.assertIsNone(user.get_profile(cached_only=True))

    def test_get_profile_with_return_is_new_and_new(self):
        """Testing User.get_profile with return_is_new=True and profile is new
        """
        user = self.create_user(username='test1')
        result = user.get_profile(return_is_new=True)

        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)
        self.assertIsInstance(result[0], Profile)
        self.assertTrue(result[1])

    def test_get_profile_with_return_is_new_and_not_new(self):
        """Testing User.get_profile with return_is_new=True and profile is new
        """
        user = self.create_user(username='test1')
        Profile.objects.create(user=user)

        result = user.get_profile(return_is_new=True)

        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)
        self.assertIsInstance(result[0], Profile)
        self.assertFalse(result[1])

    def test_is_profile_visible_with_public(self):
        """Testing User.is_profile_visible with public profiles"""
        user1 = User.objects.get(username='admin')
        user2 = User.objects.get(username='doc')

        self.assertTrue(user1.is_profile_visible(user2))

    def test_is_profile_visible_with_private(self):
        """Testing User.is_profile_visible with private profiles"""
        user1 = User.objects.get(username='admin')
        user2 = User.objects.get(username='doc')

        profile = user1.get_profile()
        profile.is_private = True
        profile.save(update_fields=('is_private',))

        self.assertFalse(user1.is_profile_visible(user2))
        self.assertTrue(user1.is_profile_visible(user1))

        user2.is_staff = True
        self.assertTrue(user1.is_profile_visible(user2))

    def test_is_profile_visible_unauthenticated(self):
        """Testing User.is_profile_visible with an unauthenticated user"""
        user = User.objects.get(username='doc')

        self.assertFalse(user.is_profile_visible(AnonymousUser()))

    def test_is_profile_visible_no_user(self):
        """Testing User.is_profile_visible with no user"""
        user = User.objects.get(username='doc')

        self.assertFalse(user.is_profile_visible(None))

    def test_is_profile_visible_staff(self):
        """Testing User.is_profile_public with a staff user"""
        user = User.objects.get(username='doc')
        admin = User.objects.get(username='admin')

        profile = user.get_profile()
        profile.is_private = True
        profile.save(update_fields=('is_private',))

        self.assertTrue(user.is_profile_visible(admin))

    def test_is_profile_visible_owner(self):
        """Testing User.is_profile_visible for the profile owner"""
        user = User.objects.get(username='doc')
        profile = user.get_profile()
        profile.is_private = True
        profile.save(update_fields=('is_private',))

        self.assertTrue(user.is_profile_visible(user))

    def test_is_profile_visible_local_site_member(self):
        """Testing User.is_profile_visible for a LocalSite member viewing a
        LocalSite member with a public profile
        """
        to_view = User.objects.get(username='doc')
        viewer = User.objects.get(username='grumpy')

        site = LocalSite.objects.create()
        site.users.add(to_view, viewer)

        self.assertTrue(to_view.is_profile_visible(viewer))

    def test_is_profile_visible_local_site_member_private(self):
        """Testing User.is_profile_visible for a LocalSite member viewing a
        LocalSite member with a private profile
        """
        to_view = User.objects.get(username='doc')
        viewer = User.objects.get(username='grumpy')

        profile = to_view.get_profile()
        profile.is_private = True
        profile.save(update_fields=('is_private',))

        site = LocalSite.objects.create()
        site.users.add(to_view, viewer)

        self.assertFalse(to_view.is_profile_visible(viewer))

    def test_is_profile_visible_local_site_admin(self):
        """Testing user.is_profile_visible for a LocalSite admin viewing a
        LocalSite member with a public profile
        """
        to_view = User.objects.get(username='doc')
        viewer = User.objects.get(username='grumpy')

        site = LocalSite.objects.create()
        site.users.add(to_view, viewer)
        site.admins.add(viewer)

        self.assertTrue(to_view.is_profile_visible(viewer))

    def test_is_profile_visible_local_site_admin_private(self):
        """Testing user.is_profile_visible for a LocalSite admin viewing a
        LocalSite member with a private profile
        """
        to_view = User.objects.get(username='doc')
        viewer = User.objects.get(username='grumpy')

        profile = to_view.get_profile()
        profile.is_private = True
        profile.save(update_fields=('is_private',))

        site = LocalSite.objects.create()
        site.users.add(to_view, viewer)
        site.admins.add(viewer)

        self.assertTrue(to_view.is_profile_visible(viewer))

    def test_is_admin_for_user_admin_vs_user(self):
        """Testing User.is_admin_for_user for an admin"""
        admin = User.objects.get(username='admin')
        user = User.objects.get(username='doc')

        with self.assertNumQueries(0):
            self.assertTrue(admin.is_admin_for_user(user))

    def test_is_admin_for_user_admin_vs_none(self):
        """Testing User.is_admin_for_user for an admin when the user is None"""
        admin = User.objects.get(username='admin')

        with self.assertNumQueries(0):
            self.assertTrue(admin.is_admin_for_user(None))

    def test_is_admin_for_user_admin_vs_anonymous(self):
        """Testing User.is_admin_for_user for an admin when the user is
        anonymous
        """
        admin = User.objects.get(username='admin')

        with self.assertNumQueries(0):
            self.assertTrue(admin.is_admin_for_user(AnonymousUser()))

    def test_is_admin_for_user_user_vs_user(self):
        """Testing User.is_admin_for_user for a regular user"""
        user = User.objects.get(username='doc')

        # This has the side-effect of pre-fetching stats, so they don't
        # interfere with query counts below.
        self.assertFalse(LocalSite.objects.has_local_sites())

        with self.assertNumQueries(0):
            self.assertFalse(user.is_admin_for_user(user))

    def test_is_admin_for_user_localsite_admin_vs_localsite_user(self):
        """Testing User.is_admin_for_user for a LocalSite admin when the user
        is a member of that LocalSite
        """
        site_admin = self.create_user(username='site_admin')
        site_user1 = self.create_user(username='user1')
        site_user2 = self.create_user(username='user2')

        local_site = LocalSite.objects.create()
        local_site.admins.add(site_admin)
        local_site.users.add(site_admin, site_user1, site_user2)

        # This has the side-effect of pre-fetching stats, so they don't
        # interfere with query counts below.
        self.assertTrue(LocalSite.objects.has_local_sites())

        # 4 queries (all from get_local_site_stats() calls):
        #
        # 1. Fetch LocalSite IDs for site_admin user membership.
        # 2. Fetch LocalSite IDs for site_admin admin membership.
        # 3. Fetch LocalSite IDs for site_user1 user membership.
        # 4. Fetch LocalSite IDs for site_user1 admin membership.
        queries = [
            {
                'model': LocalSite.users.through,
                'values_select': ('localsite_id',),
                'where': Q(user=site_admin),
            },
            {
                'model': LocalSite.admins.through,
                'values_select': ('localsite_id',),
                'where': Q(user=site_admin),
            },
            {
                'model': LocalSite.users.through,
                'values_select': ('localsite_id',),
                'where': Q(user=site_user1),
            },
            {
                'model': LocalSite.admins.through,
                'values_select': ('localsite_id',),
                'where': Q(user=site_user1),
            },
        ]

        with self.assertQueries(queries):
            self.assertTrue(site_admin.is_admin_for_user(site_user1))

        # A second call should reuse cached stats.
        with self.assertNumQueries(0):
            self.assertTrue(site_admin.is_admin_for_user(site_user1))

        # For another user, get_local_site_stats() will be called again, but
        # only for that user.
        #
        # 2 queries (all from get_local_site_stats() calls):
        #
        # 1. Fetch LocalSite IDs for site_user2 user membership.
        # 2. Fetch LocalSite IDs for site_user2 admin membership.
        queries = [
            {
                'model': LocalSite.users.through,
                'values_select': ('localsite_id',),
                'where': Q(user=site_user2),
            },
            {
                'model': LocalSite.admins.through,
                'values_select': ('localsite_id',),
                'where': Q(user=site_user2),
            },
        ]

        with self.assertQueries(queries):
            self.assertTrue(site_admin.is_admin_for_user(site_user2))

    @add_fixtures(['test_site'])
    def test_is_admin_for_user_localsite_admin_vs_other_localsite_user(self):
        """Testing User.is_admin_for_user for a LocalSite admin when the user
        is a member of another LocalSite
        """
        site1_admin = self.create_user(username='site1_admin')
        site1_user1 = self.create_user(username='site1_user1')
        site2_user1 = self.create_user(username='site2_user1')
        site2_user2 = self.create_user(username='site2_user2')

        local_site1 = LocalSite.objects.create(name='site1')
        local_site1.admins.add(site1_admin)
        local_site1.users.add(site1_admin, site1_user1)

        local_site2 = LocalSite.objects.create(name='site2')
        local_site2.users.add(site2_user1, site2_user2)

        # This has the side-effect of pre-fetching stats, so they don't
        # interfere with query counts below.
        self.assertTrue(LocalSite.objects.has_local_sites())

        # 4 queries (all from get_local_site_stats() calls):
        #
        # 1. Fetch LocalSite IDs for site1_admin user membership.
        # 2. Fetch LocalSite IDs for site1_admin admin membership.
        # 3. Fetch LocalSite IDs for site2_user1 user membership.
        # 4. Fetch LocalSite IDs for site2_user1 admin membership.
        queries = [
            {
                'model': LocalSite.users.through,
                'values_select': ('localsite_id',),
                'where': Q(user=site1_admin),
            },
            {
                'model': LocalSite.admins.through,
                'values_select': ('localsite_id',),
                'where': Q(user=site1_admin),
            },
            {
                'model': LocalSite.users.through,
                'values_select': ('localsite_id',),
                'where': Q(user=site2_user1),
            },
            {
                'model': LocalSite.admins.through,
                'values_select': ('localsite_id',),
                'where': Q(user=site2_user1),
            },
        ]

        with self.assertQueries(queries):
            self.assertFalse(site1_admin.is_admin_for_user(site2_user1))

        # A second call should reuse cached stats.
        with self.assertNumQueries(0):
            self.assertFalse(site1_admin.is_admin_for_user(site2_user1))

        # For another user, get_local_site_stats() will be called again, but
        # only for that user.
        #
        # 2 queries (all from get_local_site_stats() calls):
        #
        # 1. Fetch LocalSite IDs for site2_user2 user membership.
        # 2. Fetch LocalSite IDs for site2_user2 admin membership.
        queries = [
            {
                'model': LocalSite.users.through,
                'values_select': ('localsite_id',),
                'where': Q(user=site2_user2),
            },
            {
                'model': LocalSite.admins.through,
                'values_select': ('localsite_id',),
                'where': Q(user=site2_user2),
            },
        ]

        with self.assertQueries(queries):
            self.assertFalse(site1_admin.is_admin_for_user(site2_user2))

    def test_get_local_site_stats(self):
        """Testing User.get_local_site_stats"""
        self.spy_on(uuid4, op=kgb.SpyOpReturnInOrder([
            # First will be for LocalSite.objects.get_stats().
            UUID('00000000-0000-0000-0000-000000000001'),

            # Second will be for User.get_local_site_stats().
            UUID('00000000-0000-0000-0000-000000000002'),
        ]))

        user = self.create_user(username='site1_admin')

        local_site1 = LocalSite.objects.create(name='site1')
        local_site1.admins.add(user)
        local_site1.users.add(user)

        local_site2 = LocalSite.objects.create(name='site2')
        local_site2.users.add(user)

        local_site3 = LocalSite.objects.create(name='site3')
        local_site3.admins.add(user)

        # Pre-fetch the global LocalSite stats, so it doesn't impact the
        # query count below.
        LocalSite.objects.get_stats()

        # 2 queries:
        #
        # 1. User LocalSite membership count
        # 2. User LocalSite admined count
        queries = [
            {
                'model': LocalSite.users.through,
                'values_select': ('localsite_id',),
                'where': Q(user=user),
            },
            {
                'model': LocalSite.admins.through,
                'values_select': ('localsite_id',),
                'where': Q(user=user),
            },
        ]

        with self.assertQueries(queries):
            self.assertEqual(
                user.get_local_site_stats(),
                {
                    'admined_local_site_ids': [local_site1.pk, local_site3.pk],
                    'local_site_ids': [local_site1.pk, local_site2.pk],
                    'state_uuid': '00000000-0000-0000-0000-000000000002',
                })

        # A second call should hit cache.
        with self.assertNumQueries(0):
            self.assertEqual(
                user.get_local_site_stats(),
                {
                    'admined_local_site_ids': [local_site1.pk, local_site3.pk],
                    'local_site_ids': [local_site1.pk, local_site2.pk],
                    'state_uuid': '00000000-0000-0000-0000-000000000002',
                })

    def test_get_local_site_stats_after_state_uuid_change(self):
        """Testing User.get_local_site_stats after
        LocalSite.objects.get_stats() state_uuid change
        """
        self.spy_on(uuid4, op=kgb.SpyOpReturnInOrder([
            # First will be for LocalSite.objects.get_stats().
            UUID('00000000-0000-0000-0000-000000000001'),

            # Second will be for User.get_local_site_stats().
            UUID('00000000-0000-0000-0000-000000000002'),

            # Third will be LocalSite.objects.get_stats() again.
            UUID('00000000-0000-0000-0000-000000000003'),

            # Fourth will be for User.get_local_site_stats() again.
            UUID('00000000-0000-0000-0000-000000000004'),
        ]))

        user = self.create_user(username='site1_admin')

        local_site1 = LocalSite.objects.create(name='site1')
        local_site1.admins.add(user)
        local_site1.users.add(user)

        local_site2 = LocalSite.objects.create(name='site2')
        local_site2.users.add(user)

        local_site3 = LocalSite.objects.create(name='site3')
        local_site3.admins.add(user)

        # Pre-fetch the global LocalSite stats, so it doesn't impact the
        # query count below.
        LocalSite.objects.get_stats()

        # 2 queries:
        #
        # 1. User LocalSite membership count
        # 2. User LocalSite admined count
        queries = [
            {
                'model': LocalSite.users.through,
                'values_select': ('localsite_id',),
                'where': Q(user=user),
            },
            {
                'model': LocalSite.admins.through,
                'values_select': ('localsite_id',),
                'where': Q(user=user),
            },
        ]

        with self.assertQueries(queries):
            self.assertEqual(
                user.get_local_site_stats(),
                {
                    'admined_local_site_ids': [local_site1.pk, local_site3.pk],
                    'local_site_ids': [local_site1.pk, local_site2.pk],
                    'state_uuid': '00000000-0000-0000-0000-000000000002',
                })

        # This should impact LocalSite stats.
        self.create_local_site(name='site4')
        LocalSite.objects.get_stats()

        # A second call should not hit cache.
        with self.assertQueries(queries):
            self.assertEqual(
                user.get_local_site_stats(),
                {
                    'admined_local_site_ids': [local_site1.pk, local_site3.pk],
                    'local_site_ids': [local_site1.pk, local_site2.pk],
                    'state_uuid': '00000000-0000-0000-0000-000000000004',
                })

    def test_get_local_site_stats_with_no_local_sites(self):
        """Testing User.get_local_site_stats with no LocalSites in database"""
        self.spy_on(uuid4, op=kgb.SpyOpReturnInOrder([
            # This will be for LocalSite.objects.get_stats().
            UUID('00000000-0000-0000-0000-000000000001'),
        ]))

        user = self.create_user(username='site1_admin')

        # Pre-fetch the global LocalSite stats, so it doesn't impact the
        # query count below.
        LocalSite.objects.get_stats()

        with self.assertNumQueries(0):
            self.assertEqual(
                user.get_local_site_stats(),
                {
                    'admined_local_site_ids': [],
                    'local_site_ids': [],
                    'state_uuid': '00000000-0000-0000-0000-000000000001',
                })
