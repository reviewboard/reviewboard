"""Tests for reviewboard.hostingsvcs.base.hosting_service.

Version Added:
    9.0
"""

from __future__ import annotations

from reviewboard.hostingsvcs.base.bug_tracker import BaseBugTracker
from reviewboard.hostingsvcs.base.hosting_service import BaseHostingService
from reviewboard.hostingsvcs.github.service import GitHub
from reviewboard.hostingsvcs.gitlab import GitLab
from reviewboard.testing import TestCase


class _LabeledService(BaseHostingService, BaseBugTracker):
    """A hosting service with its own bug tracker label."""

    name = 'Labeled'
    bug_tracker_label = 'Labeled Issues'


class _DefaultLabelService(BaseHostingService, BaseBugTracker):
    """A hosting service inheriting the default bug tracker label."""

    name = 'Default Label'


class _PlainService(BaseHostingService):
    """A hosting service that is not a bug tracker."""

    name = 'Plain'


class GetBugTrackerNameTests(TestCase):
    """Unit tests for BaseHostingService.get_bug_tracker_name.

    Version Added:
        9.0
    """

    def test_with_label(self) -> None:
        """Testing BaseHostingService.get_bug_tracker_name with a service
        that sets its own bug_tracker_label
        """
        self.assertEqual(_LabeledService.get_bug_tracker_name(),
                         'Labeled Issues')

    def test_with_default_label(self) -> None:
        """Testing BaseHostingService.get_bug_tracker_name with a service
        that inherits the default bug_tracker_label
        """
        self.assertEqual(str(_DefaultLabelService.get_bug_tracker_name()),
                         'Default Label bug tracker')

    def test_without_label(self) -> None:
        """Testing BaseHostingService.get_bug_tracker_name with a service
        that has no bug_tracker_label
        """
        self.assertEqual(str(_PlainService.get_bug_tracker_name()),
                         'Plain bug tracker')

    def test_with_github_and_gitlab(self) -> None:
        """Testing BaseHostingService.get_bug_tracker_name with GitHub and
        GitLab
        """
        self.assertEqual(str(GitHub.get_bug_tracker_name()), 'GitHub Issues')
        self.assertEqual(str(GitLab.get_bug_tracker_name()), 'GitLab Issues')
