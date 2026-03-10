"""Unit tests for reviewboard.datagrids.columns.ReviewRequestCheckboxColumn.

Version Added:
    7.1
"""

from __future__ import annotations

import kgb

from reviewboard.datagrids.columns import ReviewRequestCheckboxColumn
from reviewboard.datagrids.tests.base import BaseColumnTestCase


class ReviewRequestCheckboxColumnTests(kgb.SpyAgency, BaseColumnTestCase):
    """Unit tests for ReviewRequestCheckboxColumn.

    Version Added:
        7.1
    """

    column = ReviewRequestCheckboxColumn()

    def test_render_data_with_selectable_unselected(self) -> None:
        """Testing ReviewRequestCheckboxColumn.render_data when selectable
        and unselected
        """
        review_request = self.create_review_request(publish=True)

        column = self.column
        assert isinstance(column, ReviewRequestCheckboxColumn)

        self.spy_on(column.is_selectable,
                    op=kgb.SpyOpReturn(True))
        self.spy_on(column.is_selected,
                    op=kgb.SpyOpReturn(False))

        value = column.render_data(self.stateful_column, review_request)

        self.assertHTMLEqual(
            value,
            '<input type="checkbox"'
            ' data-object-id="1"'
            ' data-checkbox-name="select">')

    def test_render_data_with_not_selectable(self) -> None:
        """Testing ReviewRequestCheckboxColumn.render_data when not
        selectable
        """
        review_request = self.create_review_request(publish=True)

        column = self.column
        assert isinstance(column, ReviewRequestCheckboxColumn)

        self.spy_on(column.is_selectable,
                    op=kgb.SpyOpReturn(False))

        value = column.render_data(self.stateful_column, review_request)

        self.assertEqual(value, '')

    def test_render_data_with_selectable_selected(self) -> None:
        """Testing ReviewRequestCheckboxColumn.render_data when selectable
        and selected
        """
        review_request = self.create_review_request(publish=True)

        column = self.column
        assert isinstance(column, ReviewRequestCheckboxColumn)

        self.spy_on(column.is_selectable,
                    op=kgb.SpyOpReturn(True))
        self.spy_on(column.is_selected,
                    op=kgb.SpyOpReturn(True))

        value = column.render_data(self.stateful_column, review_request)

        self.assertHTMLEqual(
            value,
            '<input type="checkbox"'
            ' data-object-id="1"'
            ' data-checkbox-name="select"'
            ' checked="true">')
