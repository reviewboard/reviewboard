"""Unit tests for reviewboard.datagrids.columns.PendingCountColumn.

Version Added:
    7.1
"""

from __future__ import annotations

from reviewboard.datagrids.columns import PendingCountColumn
from reviewboard.datagrids.tests.base import BaseColumnTestCase


class PendingCountColumnTests(BaseColumnTestCase):
    """Unit tests for reviewboard.datagrids.columns.PendingCountColumn.

    Version Added:
        7.1
    """

    column = PendingCountColumn()

    def test_render_data_with_zero_pending(self) -> None:
        """Testing PendingCountColumn.render_data with zero pending"""
        group = self.create_review_group()

        # This is normally set by the column's augment_queryset_for_data().
        group.column_pending_review_request_count = 0

        value = self.column.render_data(self.stateful_column, group)

        self.assertIs(type(value), str)
        self.assertEqual(value, '0')

    def test_render_data_with_pending(self) -> None:
        """Testing PendingCountColumn.render_data with pending"""
        group = self.create_review_group()

        # This is normally set by the column's augment_queryset_for_data().
        group.column_pending_review_request_count = 4

        value = self.column.render_data(self.stateful_column, group)

        self.assertIs(type(value), str)
        self.assertEqual(value, '4')
