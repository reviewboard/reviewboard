"""Unit tests for the VersionOne hosting service."""

from __future__ import annotations

from reviewboard.hostingsvcs.testing import HostingServiceTestCase
from reviewboard.hostingsvcs.versionone import VersionOne


class VersionOneTests(HostingServiceTestCase[VersionOne]):
    """Unit tests for the VersionOne hosting service."""

    service_name = 'versionone'
    fixtures = ['test_scmtools']

    def test_service_support(self) -> None:
        """Testing VersionOne service support capabilities"""
        self.assertTrue(self.service_class.supports_bug_trackers)
        self.assertFalse(self.service_class.supports_repositories)

    def test_get_bug_tracker_field(self) -> None:
        """Testing VersionOne.get_bug_tracker_field"""
        self.assertFalse(
            self.service_class.get_bug_tracker_requires_username())
        self.assertEqual(
            self.service_class.get_bug_tracker_field(None, {
                'versionone_url': 'http://versionone.example.com',
            }),
            'http://versionone.example.com/assetdetail.v1?Number=%s')
