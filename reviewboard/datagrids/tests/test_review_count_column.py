"""Unit tests for reviewboard.datagrids.columns.ReviewCountColumn.

Version Added:
    8.0
"""

from __future__ import annotations

from django.utils.safestring import SafeString

from reviewboard.datagrids.columns import ReviewCountColumn
from reviewboard.datagrids.tests.base import BaseColumnTestCase


class ReviewCountColumnTests(BaseColumnTestCase):
    """Unit tests for reviewboard.datagrids.columns.ReviewCountColumn.

    Version Added:
        8.0
    """

    column = ReviewCountColumn()

    def test_render_data_with_zero_reviews(self) -> None:
        """Testing ReviewCountColumn.render_data with zero reviews"""
        review_request = self.create_review_request(publish=True)

        # This is normally set by the column's augment_queryset().
        review_request.publicreviewcount_count = 0

        value = self.column.render_data(self.stateful_column, review_request)

        self.assertIsInstance(value, SafeString)
        self.assertEqual(value, '0')

    def test_render_data_with_reviews(self) -> None:
        """Testing ReviewCountColumn.render_data with reviews"""
        review_request = self.create_review_request(publish=True)

        # This is normally set by the column's augment_queryset().
        review_request.publicreviewcount_count = 3

        value = self.column.render_data(self.stateful_column, review_request)

        self.assertIsInstance(value, SafeString)
        self.assertEqual(value, '3')

    def test_to_json_with_zero_reviews(self) -> None:
        """Testing ReviewCountColumn.to_json with zero reviews"""
        review_request = self.create_review_request(publish=True)

        # This is normally set by the column's augment_queryset().
        review_request.publicreviewcount_count = 0

        self.assertEqual(
            self.column.to_json(self.stateful_column, review_request),
            0)

    def test_to_json_with_reviews(self) -> None:
        """Testing ReviewCountColumn.to_json with reviews"""
        review_request = self.create_review_request(publish=True)

        # This is normally set by the column's augment_queryset().
        review_request.publicreviewcount_count = 3

        self.assertEqual(
            self.column.to_json(self.stateful_column, review_request),
            3)
