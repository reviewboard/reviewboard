"""Unit tests for additions to django.contrib.auth.models.User."""

from django.contrib.auth.models import AnonymousUser, User
from djblets.testing.decorators import add_fixtures

from reviewboard.accounts.models import Profile
from reviewboard.site.models import LocalSite
from reviewboard.testing import TestCase


class UserTests(TestCase):
    """Unit tests for additions to django.contrib.auth.models.User."""

    fixtures = ['test_users']

    def test_get_profile(self):
        """Testing User.get_profile"""
        user = self.create_user(username='test1')
        profile = Profile.objects.create(user=user)

        # 1 query:
        #
        # 1. Fetch profile
        with self.assertNumQueries(1):
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
        with self.assertNumQueries(4):
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
        with self.assertNumQueries(2):
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
        with self.assertNumQueries(1):
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
        with self.assertNumQueries(1):
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

        with self.assertNumQueries(1):
            self.assertFalse(user.is_admin_for_user(user))

        with self.assertNumQueries(0):
            self.assertFalse(user.is_admin_for_user(user))

    @add_fixtures(['test_site'])
    def test_is_admin_for_user_localsite_admin_vs_localsite_user(self):
        """Testing User.is_admin_for_user for a LocalSite admin when the user
        is a member of that LocalSite
        """
        site_admin = User.objects.get(username='doc')
        site_user = User.objects.get(username='admin')

        with self.assertNumQueries(1):
            self.assertTrue(site_admin.is_admin_for_user(site_user))

        with self.assertNumQueries(0):
            self.assertTrue(site_admin.is_admin_for_user(site_user))

    @add_fixtures(['test_site'])
    def test_is_admin_for_user_localsite_admin_vs_other_localsite_user(self):
        """Testing User.is_admin_for_user for a LocalSite admin when the user
        is a member of another LocalSite
        """
        site_admin = User.objects.get(username='doc')
        site_user = User.objects.get(username='grumpy')
        site = LocalSite.objects.create(name='local-site-3')
        site.users.add(site_admin)
        site.users.add(site_user)

        with self.assertNumQueries(1):
            self.assertFalse(site_admin.is_admin_for_user(site_user))

        with self.assertNumQueries(0):
            self.assertFalse(site_admin.is_admin_for_user(site_user))
