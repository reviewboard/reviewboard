"""Unit tests for reviewboard.datagrids.columns.DiffUpdatedSinceColumn.

Version Added:
    7.1
"""

from __future__ import annotations

from django.utils import timezone

from reviewboard.datagrids.columns import DiffUpdatedSinceColumn
from reviewboard.datagrids.tests.base import BaseColumnTestCase


class DiffUpdatedSinceColumnTests(BaseColumnTestCase):
    """Unit tests for reviewboard.datagrids.columns.DiffUpdatedSinceColumn.

    Version Added:
        7.1
    """

    column = DiffUpdatedSinceColumn()
    fixtures = ['test_users', 'test_scmtools']

    def test_render_data_with_diff(self) -> None:
        """Testing DiffUpdatedSinceColumn.render_data with a diff"""
        review_request = self.create_review_request(
            create_repository=True,
            publish=True)
        self.create_diffset(review_request)

        # This is normally set by augmenting the queryset when the diff is
        # added to the history.
        review_request.diffset_history.last_diff_updated = timezone.now()

        result = self.column.render_data(self.stateful_column, review_request)

        self.assertIn('<time class="timesince"', result)

    def test_render_data_without_diff(self) -> None:
        """Testing DiffUpdatedSinceColumn.render_data without a diff"""
        review_request = self.create_review_request(publish=True)

        # This is normally populated when a diff is added.
        review_request.diffset_history.last_diff_updated = None

        value = self.column.render_data(self.stateful_column, review_request)

        self.assertEqual(value, '')
