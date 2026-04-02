"""Unit tests for reviewboard.datagrids.columns.NewUpdatesColumn.

Version Added:
    8.0
"""

from __future__ import annotations

from django.utils.safestring import SafeString

from reviewboard.datagrids.columns import NewUpdatesColumn
from reviewboard.datagrids.tests.base import BaseColumnTestCase


class NewUpdatesColumnTests(BaseColumnTestCase):
    """Unit tests for reviewboard.datagrids.columns.NewUpdatesColumn.

    Version Added:
        8.0
    """

    column = NewUpdatesColumn()

    def test_render_data_with_no_updates(self) -> None:
        """Testing NewUpdatesColumn.render_data with no updates"""
        review_request = self.create_review_request(publish=True)

        # This is normally set by the column's augment_queryset().
        review_request.new_review_count = 0

        value = self.column.render_data(self.stateful_column, review_request)

        self.assertIsInstance(value, SafeString)
        self.assertEqual(value, '')

    def test_render_data_with_updates(self) -> None:
        """Testing NewUpdatesColumn.render_data with updates"""
        review_request = self.create_review_request(publish=True)

        # This is normally set by the column's augment_queryset().
        review_request.new_review_count = 3

        value = self.column.render_data(self.stateful_column, review_request)

        self.assertIsInstance(value, SafeString)
        self.assertHTMLEqual(
            value,
            '<div class="rb-icon rb-icon-new-updates" title="New Updates">'
            '</div>')

    def test_to_json_with_no_updates(self) -> None:
        """Testing NewUpdatesColumn.to_json with no updates"""
        review_request = self.create_review_request(publish=True)

        # This is normally set by the column's augment_queryset().
        review_request.new_review_count = 0

        self.assertEqual(
            self.column.to_json(self.stateful_column, review_request),
            0)

    def test_to_json_with_updates(self) -> None:
        """Testing NewUpdatesColumn.to_json with updates"""
        review_request = self.create_review_request(publish=True)

        # This is normally set by the column's augment_queryset().
        review_request.new_review_count = 3

        self.assertEqual(
            self.column.to_json(self.stateful_column, review_request),
            3)
