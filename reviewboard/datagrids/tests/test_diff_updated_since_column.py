"""Unit tests for reviewboard.datagrids.columns.DiffUpdatedSinceColumn.

Version Added:
    8.0
"""

from __future__ import annotations

from django.utils import timezone
from django.utils.safestring import SafeString

from reviewboard.datagrids.columns import DiffUpdatedSinceColumn
from reviewboard.datagrids.tests.base import BaseColumnTestCase


class DiffUpdatedSinceColumnTests(BaseColumnTestCase):
    """Unit tests for reviewboard.datagrids.columns.DiffUpdatedSinceColumn.

    Version Added:
        8.0
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

        self.assertIsInstance(result, SafeString)
        self.assertIn('<time class="timesince"', result)

    def test_render_data_without_diff(self) -> None:
        """Testing DiffUpdatedSinceColumn.render_data without a diff"""
        review_request = self.create_review_request(publish=True)

        # This is normally populated when a diff is added.
        review_request.diffset_history.last_diff_updated = None

        value = self.column.render_data(self.stateful_column, review_request)

        self.assertIsInstance(value, SafeString)
        self.assertEqual(value, '')

    def test_to_json_with_diff(self) -> None:
        """Testing DiffUpdatedSinceColumn.to_json with a diff"""
        review_request = self.create_review_request(
            create_repository=True,
            publish=True)
        self.create_diffset(review_request)

        # This is normally set by augmenting the queryset when the diff is
        # added to the history.
        review_request.diffset_history.last_diff_updated = timezone.now()

        result = self.column.to_json(self.stateful_column, review_request)

        self.assertIsNotNone(result)

    def test_to_json_without_diff(self) -> None:
        """Testing DiffUpdatedSinceColumn.to_json without a diff"""
        review_request = self.create_review_request(publish=True)

        # This is normally populated when a diff is added.
        review_request.diffset_history.last_diff_updated = None

        self.assertIsNone(
            self.column.to_json(self.stateful_column, review_request))
