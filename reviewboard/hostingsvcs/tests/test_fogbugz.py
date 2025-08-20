"""Unit tests for the FogBugz hosting service."""

from __future__ import annotations

from reviewboard.hostingsvcs.fogbugz import FogBugz
from reviewboard.hostingsvcs.testing import HostingServiceTestCase


class FogBugzTests(HostingServiceTestCase[FogBugz]):
    """Unit tests for the FogBugz hosting service."""

    service_name = 'fogbugz'
    fixtures = ['test_scmtools']

    def test_service_support(self) -> None:
        """Testing FogBugz service support capabilities"""
        self.assertTrue(self.service_class.supports_bug_trackers)
        self.assertFalse(self.service_class.supports_repositories)

    def test_get_bug_tracker_field(self) -> None:
        """Testing FogBugz.get_bug_tracker_field"""
        self.assertFalse(
            self.service_class.get_bug_tracker_requires_username())
        self.assertEqual(
            self.service_class.get_bug_tracker_field(None, {
                'fogbugz_account_domain': 'mydomain',
            }),
            'https://mydomain.fogbugz.com/f/cases/%s')
