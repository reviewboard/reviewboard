"""Unit tests for reviewboard.site.models.LocalSite."""

from django.contrib.auth.models import User

from reviewboard.site.models import LocalSite
from reviewboard.testing.testcase import TestCase


class LocalSiteTests(TestCase):
    """Unit tests for LocalSite."""

    fixtures = ['test_users', 'test_site']

    def test_access(self):
        """Test LocalSite.is_accessible_by"""
        doc = User.objects.get(username="doc")
        dopey = User.objects.get(username="dopey")
        site = LocalSite.objects.get(name="local-site-1")

        self.assertTrue(site.is_accessible_by(doc))
        self.assertFalse(site.is_accessible_by(dopey))

    def test_access_with_public(self):
        """Test LocalSite.is_accessible_by with public LocalSites"""
        doc = User.objects.get(username="doc")
        dopey = User.objects.get(username="dopey")
        site = LocalSite.objects.get(name="local-site-1")
        site.public = True

        self.assertTrue(site.is_accessible_by(doc))
        self.assertTrue(site.is_accessible_by(dopey))


class PermissionTests(TestCase):
    """Unit tests for Django-provided permissions for LocalSite."""

    fixtures = ['test_users', 'test_site']

    def setUp(self):
        super().setUp()

        self.user = User.objects.get(username='doc')
        self.assertFalse(self.user.is_superuser)

        self.local_site = LocalSite.objects.get(name=self.local_site_name)
        self.local_site.admins.add(self.user)

    def test_assigned_permissions(self):
        """Testing LocalSite assigned admin permissions"""
        self.assertTrue(self.user.has_perm(
            'hostingsvcs.change_hostingserviceaccount', self.local_site))
        self.assertTrue(self.user.has_perm(
            'hostingsvcs.create_hostingserviceaccount', self.local_site))
        self.assertTrue(self.user.has_perm(
            'reviews.can_change_status', self.local_site))
        self.assertTrue(self.user.has_perm(
            'reviews.can_edit_reviewrequest', self.local_site))
        self.assertTrue(self.user.has_perm(
            'reviews.can_submit_as_another_user', self.local_site))
        self.assertTrue(self.user.has_perm(
            'reviews.change_default_reviewer', self.local_site))
        self.assertTrue(self.user.has_perm(
            'reviews.add_group', self.local_site))
        self.assertTrue(self.user.has_perm(
            'reviews.change_group', self.local_site))
        self.assertTrue(self.user.has_perm(
            'reviews.delete_file', self.local_site))
        self.assertTrue(self.user.has_perm(
            'reviews.delete_screenshot', self.local_site))
        self.assertTrue(self.user.has_perm(
            'scmtools.add_repository', self.local_site))
        self.assertTrue(self.user.has_perm(
            'scmtools.change_repository', self.local_site))

    def test_invalid_permissions(self):
        """Testing LocalSite invalid admin permissions"""
        self.assertFalse(self.user.has_perm(
            'reviews.delete_reviewrequest', self.local_site))
        self.assertFalse(self.user.has_perm(
            'dummy.permission', self.local_site))
