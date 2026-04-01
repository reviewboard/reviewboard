"""Unit tests for reviewboard.datagrids.columns.ReviewGroupStarColumn.

Version Added:
    8.0
"""

from __future__ import annotations

from django.contrib.auth.models import AnonymousUser
from django.utils.safestring import SafeString

from reviewboard.datagrids.columns import ReviewGroupStarColumn
from reviewboard.datagrids.tests.base import BaseColumnTestCase


class ReviewGroupStarColumnTests(BaseColumnTestCase):
    """Unit tests for reviewboard.datagrids.columns.ReviewGroupStarColumn.

    Version Added:
        8.0
    """

    column = ReviewGroupStarColumn()

    def test_render_data_not_starred(self) -> None:
        """Testing ReviewGroupStarColumn.render_data when not starred"""
        group = self.create_review_group()

        value = self.column.render_data(self.stateful_column, group)

        self.assertIsInstance(value, SafeString)
        self.assertHTMLEqual(
            value,
            '<div class="rb-icon star rb-icon-star-off"'
            ' data-starred="0"'
            ' data-object-type="groups"'
            ' data-object-id="test-group"></div>')

    def test_render_data_starred(self) -> None:
        """Testing ReviewGroupStarColumn.render_data when starred"""
        group = self.create_review_group()

        profile = self.request.user.get_profile()
        profile.star_review_group(group)

        value = self.column.render_data(self.stateful_column, group)

        self.assertIsInstance(value, SafeString)
        self.assertHTMLEqual(
            value,
            '<div class="rb-icon star rb-icon-star-on"'
            ' data-starred="1"'
            ' data-object-type="groups"'
            ' data-object-id="test-group"></div>')

    def test_render_data_as_anonymous(self) -> None:
        """Testing ReviewGroupStarColumn.render_data as anonymous user"""
        group = self.create_review_group()
        self.request.user = AnonymousUser()

        value = self.column.render_data(self.stateful_column, group)

        self.assertIsInstance(value, SafeString)
        self.assertEqual(value, '')

    def test_to_json_not_starred(self) -> None:
        """Testing ReviewGroupStarColumn.to_json when not starred"""
        group = self.create_review_group()

        self.assertIs(self.column.to_json(self.stateful_column, group),
                      False)

    def test_to_json_starred(self) -> None:
        """Testing ReviewGroupStarColumn.to_json when starred"""
        group = self.create_review_group()

        profile = self.request.user.get_profile()
        profile.star_review_group(group)

        self.assertIs(self.column.to_json(self.stateful_column, group),
                      True)
