"""Unit tests for reviewboard.admin.actions.BaseAdminSidebarManageItemAction.

Version Added:
    7.1
"""

from __future__ import annotations

from django.contrib.auth.models import User
from django.urls import NoReverseMatch

from reviewboard.admin.actions import BaseAdminSidebarManageItemAction
from reviewboard.testing.testcase import TestCase


class BaseAdminSidebarManageItemActionTests(TestCase):
    """Unit tests for BaseAdminSidebarManageItemAction.

    Version Added:
        7.1
    """

    def test_get_add_item_url_with_result(self) -> None:
        """Testing BaseAdminSidebarManageItemAction.get_add_item_url with
        add_item_url_name
        """
        class MyManageItemAction(BaseAdminSidebarManageItemAction):
            action_id = 'my-action'
            add_item_url_name = 'admin:auth_user_add'

        action = MyManageItemAction()

        self.assertEqual(action.get_add_item_url(),
                         '/admin/db/auth/user/add/')

    def test_get_add_item_url_with_unset(self) -> None:
        """Testing BaseAdminSidebarManageItemAction.get_add_item_url with
        add_item_url_name not set
        """
        class MyManageItemAction(BaseAdminSidebarManageItemAction):
            action_id = 'my-action'

        action = MyManageItemAction()

        self.assertIsNone(action.get_add_item_url())

    def test_get_add_item_url_with_error(self) -> None:
        """Testing BaseAdminSidebarManageItemAction.get_add_item_url with
        exception
        """
        class MyManageItemAction(BaseAdminSidebarManageItemAction):
            action_id = 'my-action'
            add_item_url_name = 'xxx-bad-url'

        action = MyManageItemAction()

        message = (
            "Reverse for 'xxx-bad-url' not found. 'xxx-bad-url' is not "
            "a valid view function or pattern name."
        )

        with self.assertRaisesMessage(NoReverseMatch, message):
            action.get_add_item_url()

    def test_get_item_count_with_result(self) -> None:
        """Testing BaseAdminSidebarManageItemAction.get_item_count with
        item_queryset
        """
        class MyManageItemAction(BaseAdminSidebarManageItemAction):
            action_id = 'my-action'
            item_queryset = User.objects.all()

        self.create_user(username='user1')
        self.create_user(username='user2')

        action = MyManageItemAction()

        self.assertEqual(action.get_item_count(), 2)

    def test_get_item_count_with_result_0(self) -> None:
        """Testing BaseAdminSidebarManageItemAction.get_item_count with
        item_queryset and no items
        """
        class MyManageItemAction(BaseAdminSidebarManageItemAction):
            action_id = 'my-action'
            item_queryset = User.objects.all()

        action = MyManageItemAction()

        self.assertEqual(action.get_item_count(), 0)

    def test_get_item_count_with_unset(self) -> None:
        """Testing BaseAdminSidebarManageItemAction.get_item_count with
        item_queryset unset
        """
        class MyManageItemAction(BaseAdminSidebarManageItemAction):
            action_id = 'my-action'

        self.create_user(username='user1')

        action = MyManageItemAction()

        self.assertIsNone(action.get_item_count())
