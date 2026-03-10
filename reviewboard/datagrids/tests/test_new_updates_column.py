"""Unit tests for reviewboard.datagrids.columns.NewUpdatesColumn.

Version Added:
    7.1
"""

from __future__ import annotations

from reviewboard.datagrids.columns import NewUpdatesColumn
from reviewboard.datagrids.tests.base import BaseColumnTestCase


class NewUpdatesColumnTests(BaseColumnTestCase):
    """Unit tests for reviewboard.datagrids.columns.NewUpdatesColumn.

    Version Added:
        7.1
    """

    column = NewUpdatesColumn()

    def test_render_data_with_no_updates(self) -> None:
        """Testing NewUpdatesColumn.render_data with no updates"""
        review_request = self.create_review_request(publish=True)

        # This is normally set by the column's augment_queryset().
        review_request.new_review_count = 0

        value = self.column.render_data(self.stateful_column, review_request)

        self.assertEqual(value, '')

    def test_render_data_with_updates(self) -> None:
        """Testing NewUpdatesColumn.render_data with updates"""
        review_request = self.create_review_request(publish=True)

        # This is normally set by the column's augment_queryset().
        review_request.new_review_count = 3

        value = self.column.render_data(self.stateful_column, review_request)

        self.assertHTMLEqual(
            value,
            '<div class="rb-icon rb-icon-new-updates" title="New Updates">'
            '</div>')
