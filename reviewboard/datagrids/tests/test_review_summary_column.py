"""Unit tests for reviewboard.datagrids.columns.ReviewSummaryColumn.

Version Added:
    8.0
"""

from __future__ import annotations

from django.utils.safestring import SafeString

from reviewboard.datagrids.columns import ReviewSummaryColumn
from reviewboard.datagrids.tests.base import BaseColumnTestCase


class ReviewSummaryColumnTests(BaseColumnTestCase):
    """Unit tests for reviewboard.datagrids.columns.ReviewSummaryColumn.

    Version Added:
        8.0
    """

    column = ReviewSummaryColumn()

    def test_render_data(self) -> None:
        """Testing ReviewSummaryColumn.render_data"""
        review_request = self.create_review_request(
            summary='Test Summary',
            publish=True)
        review = self.create_review(review_request)

        value = self.column.render_data(self.stateful_column, review)

        self.assertIsInstance(value, SafeString)
        self.assertEqual(value, 'Test Summary')

    def test_render_data_with_special_chars(self) -> None:
        """Testing ReviewSummaryColumn.render_data with special HTML chars"""
        review_request = self.create_review_request(
            summary='<script>xss</script>',
            publish=True)
        review = self.create_review(review_request)

        value = self.column.render_data(self.stateful_column, review)

        self.assertIsInstance(value, SafeString)
        self.assertEqual(value, '&lt;script&gt;xss&lt;/script&gt;')

    def test_render_data_with_empty_summary(self) -> None:
        """Testing ReviewSummaryColumn.render_data with empty summary"""
        review_request = self.create_review_request(
            summary='',
            publish=True)
        review = self.create_review(review_request)

        value = self.column.render_data(self.stateful_column, review)

        self.assertIsInstance(value, SafeString)
        self.assertEqual(value, '')

    def test_to_json(self) -> None:
        """Testing ReviewSummaryColumn.to_json"""
        review_request = self.create_review_request(
            summary='Test Summary',
            publish=True)
        review = self.create_review(review_request)

        self.assertEqual(
            self.column.to_json(self.stateful_column, review),
            'Test Summary')

    def test_to_json_does_not_escape_html(self) -> None:
        """Testing ReviewSummaryColumn.to_json does not escape HTML"""
        review_request = self.create_review_request(
            summary='<script>xss</script>',
            publish=True)
        review = self.create_review(review_request)

        self.assertEqual(
            self.column.to_json(self.stateful_column, review),
            '<script>xss</script>')

    def test_to_json_with_empty_summary(self) -> None:
        """Testing ReviewSummaryColumn.to_json with empty summary"""
        review_request = self.create_review_request(
            summary='',
            publish=True)
        review = self.create_review(review_request)

        self.assertEqual(
            self.column.to_json(self.stateful_column, review),
            '')
