"""Unit tests for reviewboard.datagrids.columns.DiffUpdatedColumn.

Version Added:
    7.1
"""

from __future__ import annotations

from datetime import UTC, datetime

from django.utils import timezone

from reviewboard.datagrids.columns import DiffUpdatedColumn
from reviewboard.datagrids.tests.base import BaseColumnTestCase


class DiffUpdatedColumnTests(BaseColumnTestCase):
    """Unit tests for reviewboard.datagrids.columns.DiffUpdatedColumn.

    Version Added:
        7.1
    """

    column = DiffUpdatedColumn()
    fixtures = ['test_users', 'test_scmtools']

    def test_render_data_with_diff(self) -> None:
        """Testing DiffUpdatedColumn.render_data with a diff"""
        review_request = self.create_review_request(
            create_repository=True,
            publish=True)
        self.create_diffset(review_request)

        # This is normally set by augmenting the queryset when the diff is
        # added to the history.
        assert review_request.diffset_history is not None

        review_request.diffset_history.last_diff_updated = \
            datetime(2026, 1, 1, 12, 30, 40, tzinfo=UTC)

        value = self.column.render_data(self.stateful_column, review_request)

        self.assertIsInstance(value, str)
        self.assertEqual(value, 'Jan. 1, 2026')

    def test_render_data_without_diff(self) -> None:
        """Testing DiffUpdatedColumn.render_data without a diff"""
        review_request = self.create_review_request(publish=True)

        # This is normally populated when a diff is added.
        review_request.diffset_history.last_diff_updated = None

        value = self.column.render_data(self.stateful_column, review_request)

        self.assertIsInstance(value, str)
        self.assertEqual(value, '')

    def test_to_json_with_diff(self) -> None:
        """Testing DiffUpdatedColumn.to_json with a diff"""
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
        """Testing DiffUpdatedColumn.to_json without a diff"""
        review_request = self.create_review_request(publish=True)

        # This is normally populated when a diff is added.
        review_request.diffset_history.last_diff_updated = None

        self.assertIsNone(
            self.column.to_json(self.stateful_column, review_request))
