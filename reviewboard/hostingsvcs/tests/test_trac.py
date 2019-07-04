"""Unit tests for the Trac hosting service."""

from __future__ import unicode_literals

from reviewboard.hostingsvcs.testing import HostingServiceTestCase


class TracTests(HostingServiceTestCase):
    """Unit tests for the Trac hosting service."""

    service_name = 'trac'
    fixtures = ['test_scmtools']

    def test_service_support(self):
        """Testing Trac service support capabilities"""
        self.assertTrue(self.service_class.supports_bug_trackers)
        self.assertFalse(self.service_class.supports_repositories)

    def test_get_bug_tracker_field(self):
        """Testing Trac.get_bug_tracker_field"""
        self.assertFalse(
            self.service_class.get_bug_tracker_requires_username())
        self.assertEqual(
            self.service_class.get_bug_tracker_field(None, {
                'trac_url': 'http://trac.example.com',
            }),
            'http://trac.example.com/ticket/%s')
