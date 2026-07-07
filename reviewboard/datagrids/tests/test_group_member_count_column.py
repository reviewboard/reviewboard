"""Unit tests for reviewboard.datagrids.columns.GroupMemberCountColumn.

Version Added:
    8.0
"""

from __future__ import annotations

from django.contrib.auth.models import User
from django.db.models import Count
from django.utils.safestring import SafeString

from reviewboard.datagrids.columns import GroupMemberCountColumn
from reviewboard.datagrids.tests.base import BaseColumnTestCase
from reviewboard.reviews.models import Group


class GroupMemberCountColumnTests(BaseColumnTestCase):
    """Unit tests for reviewboard.datagrids.columns.GroupMemberCountColumn.

    Version Added:
        8.0
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

    def test_augment_queryset_for_data(self) -> None:
        """Testing GroupMemberCountColumn.augment_queryset_for_data"""
        group = self.create_review_group()
        user1 = User.objects.get(username='doc')
        user2 = User.objects.get(username='grumpy')
        group.users.add(user1, user2)

        qs = self.column.augment_queryset_for_data(
            self.stateful_column,
            Group.objects.filter(pk=group.pk))

        result = qs.get(pk=group.pk)
        self.assertEqual(result.column_group_member_count, 2)

    def test_augment_queryset_for_data_with_other_m2m_annotation(
        self,
    ) -> None:
        """Testing GroupMemberCountColumn.augment_queryset_for_data does not
        produce inflated counts when combined with another M2M annotation
        """
        # Regression test: when multiple M2M Count() annotations are applied
        # to the same queryset simultaneously, a Cartesian product inflates
        # all counts.  distinct=True prevents this.
        group = self.create_review_group()
        user1 = User.objects.get(username='doc')
        user2 = User.objects.get(username='grumpy')
        group.users.add(user1, user2)

        for _ in range(3):
            self.create_review_request(
                submitter=user1,
                target_groups=[group],
                publish=True)

        qs = Group.objects.filter(pk=group.pk)
        qs = self.column.augment_queryset_for_data(self.stateful_column, qs)

        # Simulate a second M2M annotation on the same queryset (as would
        # occur when PendingCountColumn is also active).
        qs = qs.annotate(
            test_review_request_count=Count('review_requests', distinct=True))

        result = qs.get(pk=group.pk)

        # Without distinct=True both values would be inflated to 2*3=6.
        self.assertEqual(result.column_group_member_count, 2)
        self.assertEqual(result.test_review_request_count, 3)
