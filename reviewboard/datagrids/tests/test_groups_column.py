"""Unit tests for reviewboard.datagrids.columns.GroupsColumn.

Version Added:
    7.1
"""

from __future__ import annotations

from reviewboard.datagrids.columns import GroupsColumn
from reviewboard.datagrids.tests.base import BaseColumnTestCase


class GroupsColumnTests(BaseColumnTestCase):
    """Unit tests for reviewboard.datagrids.columns.GroupsColumn.

    Version Added:
        7.1
    """

    column = GroupsColumn()

    def test_render_data_with_no_groups(self) -> None:
        """Testing GroupsColumn.render_data with no groups"""
        review_request = self.create_review_request(publish=True)

        value = self.column.render_data(self.stateful_column, review_request)

        self.assertIs(type(value), str)
        self.assertEqual(value, '')

    def test_render_data_with_one_group(self) -> None:
        """Testing GroupsColumn.render_data with one group"""
        review_request = self.create_review_request(publish=True)
        group = self.create_review_group(name='group1')
        review_request.target_groups.add(group)

        value = self.column.render_data(self.stateful_column, review_request)

        self.assertIs(type(value), str)
        self.assertEqual(value, 'group1 ')

    def test_render_data_with_multiple_groups(self) -> None:
        """Testing GroupsColumn.render_data with multiple groups"""
        review_request = self.create_review_request(publish=True)
        group1 = self.create_review_group(name='group1')
        group2 = self.create_review_group(name='group2')
        review_request.target_groups.add(group1, group2)

        value = self.column.render_data(self.stateful_column, review_request)

        self.assertIs(type(value), str)
        self.assertEqual(value, 'group1 group2 ')
