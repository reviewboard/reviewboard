"""Unit tests for reviewboard.accounts.models.Profile."""

from __future__ import unicode_literals

from django.contrib.auth.models import AnonymousUser, User
from djblets.testing.decorators import add_fixtures

from reviewboard.accounts.models import LocalSiteProfile
from reviewboard.site.models import LocalSite
from reviewboard.testing import TestCase


class ProfileTests(TestCase):
    """Unit tests for reviewboard.accounts.models.Profile."""

    fixtures = ['test_users']

    @add_fixtures(['test_scmtools', 'test_site'])
    def test_is_star_unstar_updating_count_correctly(self):
        """Testing if star, unstar affect review request counts correctly"""
        user1 = User.objects.get(username='admin')
        profile1 = user1.get_profile()
        review_request = self.create_review_request(publish=True)

        site_profile = profile1.site_profiles.get(local_site=None)

        profile1.star_review_request(review_request)
        site_profile = LocalSiteProfile.objects.get(pk=site_profile.pk)

        self.assertTrue(review_request in
                        profile1.starred_review_requests.all())
        self.assertEqual(site_profile.starred_public_request_count, 1)

        profile1.unstar_review_request(review_request)
        site_profile = LocalSiteProfile.objects.get(pk=site_profile.pk)

        self.assertFalse(review_request in
                         profile1.starred_review_requests.all())
        self.assertEqual(site_profile.starred_public_request_count, 0)

    def test_get_display_name_unauthenticated_public(self):
        """Testing Profile.get_display_name with a public profile"""
        user = User.objects.get(username='doc')
        profile = user.get_profile()
        profile.is_private = False

        self.assertEqual(profile.get_display_name(AnonymousUser()),
                         user.username)

    def test_get_display_name_unauthenticated_private(self):
        """Testing Profile.get_display_name for an unauthenticated user viewing
        a private profile
        """
        user = User.objects.get(username='doc')
        profile = user.get_profile()
        profile.is_private = True

        self.assertEqual(profile.get_display_name(AnonymousUser()),
                         user.username)

    def test_get_display_name_public(self):
        """Testing Profile.get_display_name for an authenticated user viewing a
        public profile
        """
        user = User.objects.get(username='doc')
        profile = user.get_profile()
        profile.is_private = False

        self.assertEqual(
            profile.get_display_name(User.objects.get(username='grumpy')),
            user.get_full_name())

    def test_get_display_name_private(self):
        """Testing Profile.get_display_name for an authenticated user viewing a
        private profile
        """
        user = User.objects.get(username='doc')
        profile = user.get_profile()
        profile.is_private = True

        self.assertEqual(
            profile.get_display_name(User.objects.get(username='grumpy')),
            user.username)

    def test_get_display_name_admin_private(self):
        """Testing Profile.get_display_name for an admin viewing a private
        profile
        """
        user = User.objects.get(username='doc')
        profile = user.get_profile()
        profile.is_private = True

        self.assertEqual(
            profile.get_display_name(User.objects.get(username='admin')),
            user.get_full_name())

    @add_fixtures(['test_site'])
    def test_get_display_name_localsite_member_private(self):
        """Testing Profile.get_display_name for a LocalSite member viewing
        a LocalSite member with a private profile
        """
        user = User.objects.get(username='doc')
        profile = user.get_profile()
        profile.is_private = True

        viewer = User.objects.get(username='grumpy')
        site = LocalSite.objects.get(pk=1)
        site.users.add(viewer)

        self.assertEqual(profile.get_display_name(viewer), user.username)

    @add_fixtures(['test_site'])
    def test_get_display_name_localsite_admin_private(self):
        """Testing Profile.get_display_name for a LocalSite admin viewing
        a LocalSite member with a private profile
        """
        user = User.objects.get(username='admin')
        profile = user.get_profile()
        profile.is_private = True

        self.assertEqual(
            profile.get_display_name(User.objects.get(username='doc')),
            user.get_full_name())

    @add_fixtures(['test_site'])
    def test_get_display_name_localsite_admin_private_other_site(self):
        """Testing Profile.get_display_name for a LocalSite admin viewing a
        member of another LocalSite with a private profile
        """
        user = User.objects.get(username='doc')
        profile = user.get_profile()
        profile.is_private = True

        viewer = User.objects.get(username='grumpy')
        site = LocalSite.objects.create(name='site-3')
        site.users.add(viewer)
        site.admins.add(viewer)

        self.assertEqual(profile.get_display_name(viewer), user.username)

    def test_get_display_name_self_private(self):
        """Testing Profile.get_display_name for a user viewing themselves with
        a private profile
        """
        user = User.objects.get(username='doc')
        profile = user.get_profile()
        profile.is_private = True

        self.assertEqual(profile.get_display_name(user), user.get_full_name())
