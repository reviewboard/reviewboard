"""Unit tests for reviewboard.site.context_processors."""

from django.contrib.auth.models import Permission
from djblets.testing.decorators import add_fixtures

from reviewboard.site.context_processors import AllPermsWrapper
from reviewboard.site.models import LocalSite
from reviewboard.testing.testcase import TestCase


class AllPermsWrapperTests(TestCase):
    """Unit tests for AllPermsWrapper."""

    def setUp(self):
        super().setUp()

        self.user = self.create_user()

    @add_fixtures(['test_users', 'test_site'])
    def test_lookup_global_permission(self):
        """Testing AllPermsWrapper with global permission lookup"""
        self.user.user_permissions.add(
            Permission.objects.get(codename='delete_reviewrequest'))

        perms = AllPermsWrapper(self.user, self.local_site_name)

        self.assertIn('reviews.delete_reviewrequest', perms)
        self.assertNotIn('reviews.fake_permission', perms)

    @add_fixtures(['test_users', 'test_site'])
    def test_lookup_site_permission(self):
        """Testing AllPermsWrapper with site permission lookup"""
        local_site = LocalSite.objects.get(name=self.local_site_name)

        local_site_profile = self.user.get_site_profile(local_site)
        local_site_profile.permissions['reviews.can_change_status'] = True
        local_site_profile.save(update_fields=('permissions',))

        perms = AllPermsWrapper(self.user, self.local_site_name)

        self.assertIn('reviews.can_change_status', perms)
        self.assertNotIn('reviews.fake_permission', perms)
