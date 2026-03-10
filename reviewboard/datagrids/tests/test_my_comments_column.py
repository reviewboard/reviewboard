"""Unit tests for reviewboard.datagrids.columns.MyCommentsColumn.

Version Added:
    7.1
"""

from __future__ import annotations

from django.contrib.auth.models import AnonymousUser

from reviewboard.datagrids.columns import MyCommentsColumn
from reviewboard.datagrids.tests.base import BaseColumnTestCase


class MyCommentsColumnTests(BaseColumnTestCase):
    """Unit tests for reviewboard.datagrids.columns.MyCommentsColumn.

    Version Added:
        7.1
    """

    column = MyCommentsColumn()

    def test_render_data_as_anonymous(self) -> None:
        """Testing MyCommentsColumn.render_data as anonymous user"""
        review_request = self.create_review_request(publish=True)
        self.request.user = AnonymousUser()

        value = self.column.render_data(self.stateful_column, review_request)

        self.assertEqual(value, '')

    def test_render_data_with_no_reviews(self) -> None:
        """Testing MyCommentsColumn.render_data with no reviews"""
        review_request = self.create_review_request(publish=True)

        # These are normally set by the column's augment_queryset().
        review_request.mycomments_my_reviews = 0
        review_request.mycomments_private_reviews = 0
        review_request.mycomments_shipit_reviews = 0

        value = self.column.render_data(self.stateful_column, review_request)

        self.assertEqual(value, '')

    def test_render_data_with_published_review(self) -> None:
        """Testing MyCommentsColumn.render_data with published review"""
        review_request = self.create_review_request(publish=True)

        # These are normally set by the column's augment_queryset().
        review_request.mycomments_my_reviews = 1
        review_request.mycomments_private_reviews = 0
        review_request.mycomments_shipit_reviews = 0

        value = self.column.render_data(self.stateful_column, review_request)

        self.assertHTMLEqual(
            value,
            '<div class="rb-icon rb-icon-datagrid-comment"'
            ' title="Comments published"></div>')

    def test_render_data_with_draft_review(self) -> None:
        """Testing MyCommentsColumn.render_data with draft review"""
        review_request = self.create_review_request(publish=True)

        # These are normally set by the column's augment_queryset().
        review_request.mycomments_my_reviews = 1
        review_request.mycomments_private_reviews = 1
        review_request.mycomments_shipit_reviews = 0

        value = self.column.render_data(self.stateful_column, review_request)

        self.assertHTMLEqual(
            value,
            '<div class="rb-icon rb-icon-datagrid-comment-draft"'
            ' title="Comments drafted"></div>')

    def test_render_data_with_ship_it(self) -> None:
        """Testing MyCommentsColumn.render_data with Ship It"""
        review_request = self.create_review_request(publish=True)

        # These are normally set by the column's augment_queryset().
        review_request.mycomments_my_reviews = 1
        review_request.mycomments_private_reviews = 0
        review_request.mycomments_shipit_reviews = 1

        value = self.column.render_data(self.stateful_column, review_request)

        self.assertHTMLEqual(
            value,
            '<div class="rb-icon rb-icon-datagrid-comment-shipit"'
            ' title="Comments published. Ship it!"></div>')

    def test_render_data_draft_prioritized_over_ship_it(self) -> None:
        """Testing MyCommentsColumn.render_data with draft prioritized over
        Ship It
        """
        review_request = self.create_review_request(publish=True)

        # These are normally set by the column's augment_queryset().
        review_request.mycomments_my_reviews = 2
        review_request.mycomments_private_reviews = 1
        review_request.mycomments_shipit_reviews = 1

        value = self.column.render_data(self.stateful_column, review_request)

        self.assertHTMLEqual(
            value,
            '<div class="rb-icon rb-icon-datagrid-comment-draft"'
            ' title="Comments drafted"></div>')
