"""Tests for reviewboard.hostingsvcs.custom_bug_tracker.

Version Added:
    9.0
"""

from __future__ import annotations

from reviewboard.hostingsvcs.base import hosting_service_registry
from reviewboard.hostingsvcs.custom_bug_tracker import CustomBugTracker
from reviewboard.hostingsvcs.models import ConfiguredBugTracker
from reviewboard.testing import TestCase


class CustomBugTrackerTests(TestCase):
    """Unit tests for CustomBugTracker.

    Version Added:
        9.0
    """

    def test_registered(self) -> None:
        """Testing CustomBugTracker is registered"""
        self.assertIs(
            hosting_service_registry.get_hosting_service(
                'custom-bug-tracker'),
            CustomBugTracker)

    def test_get_bug_url(self) -> None:
        """Testing CustomBugTracker.get_bug_url with a %s template"""
        config = ConfiguredBugTracker.objects.create(
            name='Tracker',
            service_name='custom-bug-tracker',
            settings={
                'url_template': 'https://bugs.example.com/show?id=%s',
            })

        self.assertEqual(config.get_bug_url('123'),
                         'https://bugs.example.com/show?id=123')

    def test_get_bug_url_without_placeholder(self) -> None:
        """Testing CustomBugTracker.get_bug_url without a %s placeholder"""
        config = ConfiguredBugTracker.objects.create(
            name='Tracker',
            service_name='custom-bug-tracker',
            settings={
                'url_template': 'https://bugs.example.com/',
            })

        self.assertIsNone(config.get_bug_url('123'))

    def test_get_bug_url_without_template(self) -> None:
        """Testing CustomBugTracker.get_bug_url without a template"""
        config = ConfiguredBugTracker.objects.create(
            name='Tracker',
            service_name='custom-bug-tracker')

        self.assertIsNone(config.get_bug_url('123'))

    def test_not_in_repository_form(self) -> None:
        """Testing CustomBugTracker stays out of the repository form"""
        from reviewboard.scmtools.forms import RepositoryForm

        # The repository form has its own custom URL pseudo-choice, and
        # this service has no bug_tracker_field template for the legacy
        # flow. Building the form must neither offer the service nor log
        # a service load error, even though the service is visible.
        with self.assertNoLogs('reviewboard.scmtools.forms', 'ERROR'):
            form = RepositoryForm()

        self.assertNotIn('custom-bug-tracker',
                         form.hosting_bug_tracker_forms)
        self.assertNotIn(
            'custom-bug-tracker',
            {
                choice[0]
                for choice in form.fields['bug_tracker_type'].choices
            })
