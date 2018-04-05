"""Unit tests for the FogBugz hosting service."""

from __future__ import unicode_literals

from reviewboard.hostingsvcs.tests.testcases import ServiceTests


class FogBugzTests(ServiceTests):
    """Unit tests for the FogBugz hosting service."""

    service_name = 'fogbugz'
    fixtures = ['test_scmtools']

    def test_service_support(self):
        """Testing FogBugz service support capabilities"""
        self.assertTrue(self.service_class.supports_bug_trackers)
        self.assertFalse(self.service_class.supports_repositories)

    def test_get_bug_tracker_field(self):
        """Testing FogBugz.get_bug_tracker_field"""
        self.assertFalse(
            self.service_class.get_bug_tracker_requires_username())
        self.assertEqual(
            self.service_class.get_bug_tracker_field(None, {
                'fogbugz_account_domain': 'mydomain',
            }),
            'https://mydomain.fogbugz.com/f/cases/%s')
