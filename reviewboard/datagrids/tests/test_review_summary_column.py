"""Unit tests for reviewboard.datagrids.columns.ReviewSummaryColumn.

Version Added:
    7.1
"""

from __future__ import annotations

from reviewboard.datagrids.columns import ReviewSummaryColumn
from reviewboard.datagrids.tests.base import BaseColumnTestCase


class ReviewSummaryColumnTests(BaseColumnTestCase):
    """Unit tests for reviewboard.datagrids.columns.ReviewSummaryColumn.

    Version Added:
        7.1
    """

    column = ReviewSummaryColumn()

    def test_render_data(self) -> None:
        """Testing ReviewSummaryColumn.render_data"""
        review_request = self.create_review_request(
            summary='Test Summary',
            publish=True)
        review = self.create_review(review_request)

        value = self.column.render_data(self.stateful_column, review)

        self.assertEqual(value, 'Test Summary')

    def test_render_data_with_special_chars(self) -> None:
        """Testing ReviewSummaryColumn.render_data with special HTML chars"""
        review_request = self.create_review_request(
            summary='<script>xss</script>',
            publish=True)
        review = self.create_review(review_request)

        value = self.column.render_data(self.stateful_column, review)

        self.assertEqual(value, '&lt;script&gt;xss&lt;/script&gt;')

    def test_render_data_with_empty_summary(self) -> None:
        """Testing ReviewSummaryColumn.render_data with empty summary"""
        review_request = self.create_review_request(
            summary='',
            publish=True)
        review = self.create_review(review_request)

        value = self.column.render_data(self.stateful_column, review)

        self.assertEqual(value, '')
