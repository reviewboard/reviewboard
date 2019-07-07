"""Unit tests for the Redmine hosting service."""

from __future__ import unicode_literals

from reviewboard.hostingsvcs.testing import HostingServiceTestCase


class RedmineTests(HostingServiceTestCase):
    """Unit tests for the Redmine hosting service."""

    service_name = 'redmine'
    fixtures = ['test_scmtools']

    def test_service_support(self):
        """Testing Redmine service support capabilities"""
        self.assertTrue(self.service_class.supports_bug_trackers)
        self.assertFalse(self.service_class.supports_repositories)

    def test_get_bug_tracker_field(self):
        """Testing Redmine.get_bug_tracker_field"""
        self.assertFalse(
            self.service_class.get_bug_tracker_requires_username())
        self.assertEqual(
            self.service_class.get_bug_tracker_field(None, {
                'redmine_url': 'http://redmine.example.com',
            }),
            'http://redmine.example.com/issues/%s')
