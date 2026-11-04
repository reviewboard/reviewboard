"""Unit tests for the Trac hosting service."""

from __future__ import annotations

from reviewboard.hostingsvcs.testing import HostingServiceTestCase
from reviewboard.hostingsvcs.trac import Trac


class TracTests(HostingServiceTestCase[Trac]):
    """Unit tests for the Trac hosting service."""

    service_name = 'trac'
    fixtures = ['test_scmtools']

    def test_service_support(self) -> None:
        """Testing Trac service support capabilities"""
        self.assertTrue(self.service_class.supports_bug_trackers)
        self.assertFalse(self.service_class.supports_repositories)

    def test_get_bug_tracker_field(self) -> None:
        """Testing Trac.get_bug_tracker_field"""
        self.assertFalse(
            self.service_class.get_bug_tracker_requires_username())
        self.assertEqual(
            self.service_class.get_bug_tracker_field(None, {
                'trac_url': 'http://trac.example.com',
            }),
            'http://trac.example.com/ticket/%s')

    def test_get_bug_url(self) -> None:
        """Testing Trac.get_bug_url with a bug tracker configuration"""
        config = self.create_bug_tracker(
            service_name='trac',
            settings={
                'trac_url': 'http://trac.example.com',
            })

        self.assertEqual(config.get_bug_url('123'),
                         'http://trac.example.com/ticket/123')
