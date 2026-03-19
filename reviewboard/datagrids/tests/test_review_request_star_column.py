"""Unit tests for reviewboard.datagrids.columns.ReviewRequestStarColumn.

Version Added:
    7.1
"""

from __future__ import annotations

from django.contrib.auth.models import AnonymousUser
from django.utils.safestring import SafeString

from reviewboard.datagrids.columns import ReviewRequestStarColumn
from reviewboard.datagrids.tests.base import BaseColumnTestCase


class ReviewRequestStarColumnTests(BaseColumnTestCase):
    """Unit tests for reviewboard.datagrids.columns.ReviewRequestStarColumn.

    Version Added:
        7.1
    """

    column = ReviewRequestStarColumn()

    def test_render_data_with_not_starred(self) -> None:
        """Testing ReviewRequestStarColumn.render_data when not starred"""
        review_request = self.create_review_request(publish=True)

        value = self.column.render_data(self.stateful_column, review_request)

        self.assertIsInstance(value, SafeString)
        self.assertHTMLEqual(
            value,
            '<div class="rb-icon star rb-icon-star-off"'
            ' data-starred="0"'
            ' data-object-type="reviewrequests"'
            ' data-object-id="1"></div>')

    def test_render_data_with_starred(self) -> None:
        """Testing ReviewRequestStarColumn.render_data when starred"""
        review_request = self.create_review_request(publish=True)

        profile = self.request.user.get_profile()
        profile.star_review_request(review_request)

        value = self.column.render_data(self.stateful_column, review_request)

        self.assertIsInstance(value, SafeString)
        self.assertHTMLEqual(
            value,
            '<div class="rb-icon star rb-icon-star-on"'
            ' data-starred="1"'
            ' data-object-type="reviewrequests"'
            ' data-object-id="1"></div>')

    def test_render_data_as_anonymous(self) -> None:
        """Testing ReviewRequestStarColumn.render_data as anonymous user"""
        review_request = self.create_review_request(publish=True)
        self.request.user = AnonymousUser()

        value = self.column.render_data(self.stateful_column, review_request)

        self.assertIsInstance(value, SafeString)
        self.assertEqual(value, '')

    def test_to_json_with_not_starred(self) -> None:
        """Testing ReviewRequestStarColumn.to_json when not starred"""
        review_request = self.create_review_request(publish=True)

        self.assertIs(
            self.column.to_json(self.stateful_column, review_request),
            False)

    def test_to_json_with_starred(self) -> None:
        """Testing ReviewRequestStarColumn.to_json when starred"""
        review_request = self.create_review_request(publish=True)

        profile = self.request.user.get_profile()
        profile.star_review_request(review_request)

        self.assertIs(
            self.column.to_json(self.stateful_column, review_request),
            True)

    def test_to_json_as_anonymous(self) -> None:
        """Testing ReviewRequestStarColumn.to_json as anonymous user"""
        review_request = self.create_review_request(publish=True)
        self.request.user = AnonymousUser()

        self.assertIs(
            self.column.to_json(self.stateful_column, review_request),
            False)
