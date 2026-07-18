"""Unit tests for reviewboard.scmtools.admin.RepositoryAdmin.

Version Added:
    9.0
"""

from __future__ import annotations

from django.urls import reverse

from reviewboard.testing.testcase import TestCase


class RepositoryAdminTests(TestCase):
    """Unit tests for RepositoryAdmin."""

    fixtures = ['test_users', 'test_scmtools']

    def setUp(self) -> None:
        """Set up the test case."""
        super().setUp()

        self.client.login(username='admin', password='admin')

    def test_change_page(self) -> None:
        """Testing RepositoryAdmin change page renders the bug tracker widget
        """
        repository = self.create_repository()

        url = reverse('admin:scmtools_repository_change',
                      args=(repository.pk,))

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'id_bug_tracker_configs_widget', response.content)
        self.assertIn(b'rb-c-repo-bug-trackers-fieldset', response.content)
        self.assertIn(b'RB.Admin.RepositoryBugTrackersView',
                      response.content)
        self.assertIn(b'Issue Tracking', response.content)

        # The legacy fields stay on the form for the widget to drive.
        self.assertIn(b'id_bug_tracker_use_hosting', response.content)
        self.assertIn(b'id_default_bug_tracker', response.content)
