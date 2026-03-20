"""Unit tests for reviewboard.datagrids.columns.GroupMemberCountColumn.

Version Added:
    7.1
"""

from __future__ import annotations

from django.utils.safestring import SafeString

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

        self.assertIsInstance(value, SafeString)
        self.assertEqual(value, '0')

    def test_render_data_with_members(self) -> None:
        """Testing GroupMemberCountColumn.render_data with members"""
        group = self.create_review_group()

        # This is normally set by the column's augment_queryset_for_data().
        group.column_group_member_count = 5

        value = self.column.render_data(self.stateful_column, group)

        self.assertIsInstance(value, SafeString)
        self.assertEqual(value, '5')

    def test_to_json_with_zero_members(self) -> None:
        """Testing GroupMemberCountColumn.to_json with zero members"""
        group = self.create_review_group()

        # This is normally set by the column's augment_queryset_for_data().
        group.column_group_member_count = 0

        self.assertEqual(
            self.column.to_json(self.stateful_column, group),
            0)

    def test_to_json_with_members(self) -> None:
        """Testing GroupMemberCountColumn.to_json with members"""
        group = self.create_review_group()

        # This is normally set by the column's augment_queryset_for_data().
        group.column_group_member_count = 5

        self.assertEqual(
            self.column.to_json(self.stateful_column, group),
            5)
