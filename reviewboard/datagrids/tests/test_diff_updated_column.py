"""Unit tests for reviewboard.datagrids.columns.DiffUpdatedColumn.

Version Added:
    7.1
"""

from __future__ import annotations

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
        review_request.diffset_history.last_diff_updated = timezone.now()

        value = self.column.render_data(self.stateful_column, review_request)

        self.assertIs(type(value), str)
        self.assertNotEqual(value, '')

    def test_render_data_without_diff(self) -> None:
        """Testing DiffUpdatedColumn.render_data without a diff"""
        review_request = self.create_review_request(publish=True)

        # This is normally populated when a diff is added.
        review_request.diffset_history.last_diff_updated = None

        value = self.column.render_data(self.stateful_column, review_request)

        self.assertIs(type(value), str)
        self.assertEqual(value, '')
