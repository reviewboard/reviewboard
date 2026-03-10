"""Unit tests for reviewboard.datagrids.columns.GroupMemberCountColumn.

Version Added:
    7.1
"""

from __future__ import annotations

from reviewboard.datagrids.columns import GroupMemberCountColumn
from reviewboard.datagrids.tests.base import BaseColumnTestCase


class GroupMemberCountColumnTests(BaseColumnTestCase):
    """Unit tests for reviewboard.datagrids.columns.GroupMemberCountColumn.

    Version Added:
        7.1
    """

    column = GroupMemberCountColumn()

    def test_render_data_with_zero_members(self) -> None:
        """Testing GroupMemberCountColumn.render_data with zero members"""
        group = self.create_review_group()

        # This is normally set by the column's augment_queryset_for_data().
        group.column_group_member_count = 0

        value = self.column.render_data(self.stateful_column, group)

        self.assertIs(type(value), str)
        self.assertEqual(value, '0')

    def test_render_data_with_members(self) -> None:
        """Testing GroupMemberCountColumn.render_data with members"""
        group = self.create_review_group()

        # This is normally set by the column's augment_queryset_for_data().
        group.column_group_member_count = 5

        value = self.column.render_data(self.stateful_column, group)

        self.assertIs(type(value), str)
        self.assertEqual(value, '5')
