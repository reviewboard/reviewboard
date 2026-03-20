"""Unit tests for reviewboard.datagrids.columns.ToMeColumn.

Version Added:
    7.1
"""

from __future__ import annotations

from django.utils.safestring import SafeString

from reviewboard.datagrids.columns import ToMeColumn
from reviewboard.datagrids.tests.base import BaseColumnTestCase


class ToMeColumnTests(BaseColumnTestCase):
    """Unit tests for reviewboard.datagrids.columns.ToMeColumn.

    Version Added:
        7.1
    """

    column = ToMeColumn()

    def test_render_data_with_directed_to_user(self) -> None:
        """Testing ToMeColumn.render_data when directed to user"""
        review_request = self.create_review_request(publish=True)

        # This is normally set by the column's augment_queryset().
        self.stateful_column.extra_data['all_to_me'] = {review_request.pk}

        value = self.column.render_data(self.stateful_column, review_request)

        self.assertIsInstance(value, SafeString)
        self.assertHTMLEqual(value, '<div title="To Me"><b>\u00bb</b></div>')

    def test_render_data_with_not_directed_to_user(self) -> None:
        """Testing ToMeColumn.render_data when not directed to user"""
        review_request = self.create_review_request(publish=True)

        # This is normally set by the column's augment_queryset().
        self.stateful_column.extra_data['all_to_me'] = set()

        value = self.column.render_data(self.stateful_column, review_request)

        self.assertIsInstance(value, SafeString)
        self.assertEqual(value, '')

    def test_to_json_with_directed_to_user(self) -> None:
        """Testing ToMeColumn.to_json when directed to user"""
        review_request = self.create_review_request(publish=True)

        # This is normally set by the column's augment_queryset().
        self.stateful_column.extra_data['all_to_me'] = {review_request.pk}

        self.assertTrue(
            self.column.to_json(self.stateful_column, review_request))

    def test_to_json_with_not_directed_to_user(self) -> None:
        """Testing ToMeColumn.to_json when not directed to user"""
        review_request = self.create_review_request(publish=True)

        # This is normally set by the column's augment_queryset().
        self.stateful_column.extra_data['all_to_me'] = set()

        self.assertFalse(
            self.column.to_json(self.stateful_column, review_request))
