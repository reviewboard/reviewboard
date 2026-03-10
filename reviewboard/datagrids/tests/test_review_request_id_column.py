"""Unit tests for reviewboard.datagrids.columns.ReviewRequestIDColumn.

Version Added:
    7.1
"""

from __future__ import annotations

from djblets.testing.decorators import add_fixtures

from reviewboard.datagrids.columns import ReviewRequestIDColumn
from reviewboard.datagrids.tests.base import BaseColumnTestCase


class ReviewRequestIDColumnTests(BaseColumnTestCase):
    """Unit tests for reviewboard.datagrids.columns.ReviewRequestIDColumn.

    Version Added:
        7.1
    """

    column = ReviewRequestIDColumn()

    def test_render_data(self) -> None:
        """Testing ReviewRequestIDColumn.render_data"""
        review_request = self.create_review_request(publish=True)

        value = self.column.render_data(self.stateful_column, review_request)

        self.assertEqual(value, 1)

    @add_fixtures(['test_site'])
    def test_render_data_with_local_site(self) -> None:
        """Testing ReviewRequestIDColumn.render_data with LocalSite"""
        review_request = self.create_review_request(
            publish=True,
            with_local_site=True)

        value = self.column.render_data(self.stateful_column, review_request)

        self.assertEqual(value, 1001)
