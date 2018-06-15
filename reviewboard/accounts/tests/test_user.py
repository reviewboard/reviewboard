"""Unit tests for additions to django.contrib.auth.models.User."""

from __future__ import unicode_literals

from django.contrib.auth.models import AnonymousUser, User
from djblets.testing.decorators import add_fixtures

from reviewboard.site.models import LocalSite
from reviewboard.testing import TestCase


class UserTests(TestCase):
    """Unit tests for additions to django.contrib.auth.models.User."""

    fixtures = ['test_users']

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
        profile.save()

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
        profile.save()

        self.assertTrue(user.is_profile_visible(admin))

    def test_is_profile_visible_owner(self):
        """Testing User.is_profile_visible for the profile owner"""
        user = User.objects.get(username='doc')
        profile = user.get_profile()
        profile.is_private = True
        profile.save()

        self.assertTrue(user.is_profile_visible(user))

    def test_is_profile_visible_local_site_member(self):
        """Testing User.is_profile_visible for a LocalSite member viewing a
        LocalSite member with a public profile
        """
        to_view = User.objects.get(username='doc')
        viewer = User.objects.get(username='grumpy')

        site = LocalSite.objects.create()
        site.users = [to_view, viewer]

        self.assertTrue(to_view.is_profile_visible(viewer))

    def test_is_profile_visible_local_site_member_private(self):
        """Testing User.is_profile_visible for a LocalSite member viewing a
        LocalSite member with a private profile
        """
        to_view = User.objects.get(username='doc')
        viewer = User.objects.get(username='grumpy')

        profile = to_view.get_profile()
        profile.is_private = True
        profile.save()

        site = LocalSite.objects.create()
        site.users = [to_view, viewer]

        self.assertFalse(to_view.is_profile_visible(viewer))

    def test_is_profile_visible_local_site_admin(self):
        """Testing user.is_profile_visible for a LocalSite admin viewing a
        LocalSite member with a public profile
        """
        to_view = User.objects.get(username='doc')
        viewer = User.objects.get(username='grumpy')

        site = LocalSite.objects.create()
        site.users = [to_view, viewer]
        site.admins = [viewer]

        self.assertTrue(to_view.is_profile_visible(viewer))

    def test_is_profile_visible_local_site_admin_private(self):
        """Testing user.is_profile_visible for a LocalSite admin viewing a
        LocalSite member with a private profile
        """
        to_view = User.objects.get(username='doc')
        viewer = User.objects.get(username='grumpy')

        profile = to_view.get_profile()
        profile.is_private = True
        profile.save()

        site = LocalSite.objects.create()
        site.users = [to_view, viewer]
        site.admins = [viewer]

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
