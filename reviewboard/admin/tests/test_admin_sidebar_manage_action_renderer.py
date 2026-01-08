"""Unit tests for reviewboard.admin.actions.AdminSidebarManageActionRenderer.

Version Added:
    7.1
"""

from __future__ import annotations

import kgb
from django.contrib.auth.models import User
from django.db.models import Count
from django.template import Context
from django_assert_queries import assert_queries

from reviewboard.actions.base import ActionPlacement
from reviewboard.admin.actions import (AdminSidebarManageActionRenderer,
                                       BaseAdminSidebarManageItemAction)
from reviewboard.testing.testcase import TestCase


class BaseAdminSidebarManageItemActionTests(kgb.SpyAgency, TestCase):
    """Unit tests for AdminSidebarManageActionRenderer.

    Version Added:
        7.1
    """

    def test_get_extra_context_with_cache(self) -> None:
        """Testing AdminSidebarManageActionRenderer.get_extra_context
        with cached state in context
        """
        class MyManageItemAction(BaseAdminSidebarManageItemAction):
            action_id = 'my-action'
            label = 'My Action'
            model = User

            placements = [
                ActionPlacement(attachment='test'),
            ]

        action = MyManageItemAction()
        request = self.create_http_request()
        placement = action.get_placement('test')
        renderer = AdminSidebarManageActionRenderer(action=action,
                                                    placement=placement)

        with self.assertNumQueries(0):
            extra_context = renderer.get_extra_context(
                request=request,
                context=Context({
                    'add_item_urls': {
                        'my-action': '/my-action-url/',
                    },
                    'item_counts': {
                        'my-action': 123,
                    },
                }))

        self.assertEqual(
            extra_context,
            {
                'action': action,
                'action_renderer': renderer,
                'add_item_title': 'Add a new user',
                'add_item_url': '/my-action-url/',
                'attachment_point_id': 'test',
                'dom_element_id': 'action-test-my-action',
                'has_parent': False,
                'id': 'my-action',
                'is_active': False,
                'is_toplevel': True,
                'item_count': 123,
                'label': 'My Action',
                'placement': placement,
                'url': '/admin/db/auth/user/',
                'verbose_label': None,
                'visible': True,
            })

    def test_get_extra_context_with_missing(self) -> None:
        """Testing AdminSidebarManageActionRenderer.get_extra_context
        with missing state from cache
        """
        class MyManageItemAction(BaseAdminSidebarManageItemAction):
            action_id = 'my-action'
            label = 'My Action'
            model = User

            placements = [
                ActionPlacement(attachment='test'),
            ]

        self.create_user(username='test')

        action = MyManageItemAction()
        request = self.create_http_request()
        placement = action.get_placement('test')
        renderer = AdminSidebarManageActionRenderer(action=action,
                                                    placement=placement)

        equeries = [
            {
                'annotations': {
                    '__count': Count('*'),
                },
                'model': User,
            },
        ]

        with assert_queries(equeries):
            extra_context = renderer.get_extra_context(
                request=request,
                context=Context())

        self.assertEqual(
            extra_context,
            {
                'action': action,
                'action_renderer': renderer,
                'add_item_title': 'Add a new user',
                'add_item_url': '/admin/db/auth/user/add/',
                'attachment_point_id': 'test',
                'dom_element_id': 'action-test-my-action',
                'has_parent': False,
                'id': 'my-action',
                'is_active': False,
                'is_toplevel': True,
                'item_count': 1,
                'label': 'My Action',
                'placement': placement,
                'url': '/admin/db/auth/user/',
                'verbose_label': None,
                'visible': True,
            })

    def test_get_extra_context_with_missing_and_item_url_error(self) -> None:
        """Testing AdminSidebarManageActionRenderer.get_extra_context
        with missing state from cache and exception generating item URL
        """
        class MyManageItemAction(BaseAdminSidebarManageItemAction):
            action_id = 'my-action'
            label = 'My Action'
            add_item_url_name = 'xxx-bad-url'
            model = User

            placements = [
                ActionPlacement(attachment='test'),
            ]

        self.create_user(username='test')

        action = MyManageItemAction()
        request = self.create_http_request()
        placement = action.get_placement('test')
        renderer = AdminSidebarManageActionRenderer(action=action,
                                                    placement=placement)

        equeries = [
            {
                'annotations': {
                    '__count': Count('*'),
                },
                'model': User,
            },
        ]

        with assert_queries(equeries), \
             self.assertLogs() as logs:
            extra_context = renderer.get_extra_context(
                request=request,
                context=Context())

        self.assertEqual(len(logs.output), 1)
        self.assertTrue(logs.output[0].startswith(
            'ERROR:reviewboard.admin.actions:Unexpected error getting '
            'Add Item URL for action "my-action": Reverse for '
            '\'xxx-bad-url\' not found. \'xxx-bad-url\' is not a valid '
            'view function or pattern name.\n'
            'Traceback (most recent call last):\n'
        ))

        self.assertEqual(
            extra_context,
            {
                'action': action,
                'action_renderer': renderer,
                'add_item_url': None,
                'add_item_title': None,
                'attachment_point_id': 'test',
                'dom_element_id': 'action-test-my-action',
                'has_parent': False,
                'id': 'my-action',
                'is_active': False,
                'is_toplevel': True,
                'item_count': 1,
                'label': 'My Action',
                'placement': placement,
                'url': '/admin/db/auth/user/',
                'verbose_label': None,
                'visible': True,
            })

    def test_get_extra_context_with_missing_and_count_error(self) -> None:
        """Testing AdminSidebarManageActionRenderer.get_extra_context
        with missing state from cache and exception generating item count
        """
        class MyManageItemAction(BaseAdminSidebarManageItemAction):
            action_id = 'my-action'
            label = 'My Action'
            model = User

            placements = [
                ActionPlacement(attachment='test'),
            ]

        self.create_user(username='test')

        action = MyManageItemAction()

        self.spy_on(action.get_item_count,
                    op=kgb.SpyOpRaise(Exception('oh no')))

        request = self.create_http_request()
        placement = action.get_placement('test')
        renderer = AdminSidebarManageActionRenderer(action=action,
                                                    placement=placement)

        with self.assertNumQueries(0), \
             self.assertLogs() as logs:
            extra_context = renderer.get_extra_context(
                request=request,
                context=Context())

        self.assertEqual(len(logs.output), 1)
        self.assertTrue(logs.output[0].startswith(
            'ERROR:reviewboard.admin.actions:Unexpected error querying '
            'item count for action "my-action": oh no\n'
            'Traceback (most recent call last):\n'
        ))

        self.assertEqual(
            extra_context,
            {
                'action': action,
                'action_renderer': renderer,
                'add_item_title': 'Add a new user',
                'add_item_url': '/admin/db/auth/user/add/',
                'attachment_point_id': 'test',
                'dom_element_id': 'action-test-my-action',
                'has_parent': False,
                'id': 'my-action',
                'is_active': False,
                'is_toplevel': True,
                'item_count': None,
                'label': 'My Action',
                'placement': placement,
                'url': '/admin/db/auth/user/',
                'verbose_label': None,
                'visible': True,
            })

    def test_get_extra_context_with_custom_attrs(self) -> None:
        """Testing AdminSidebarManageActionRenderer.get_extra_context
        with custom attributes on action
        """
        class MyManageItemAction(BaseAdminSidebarManageItemAction):
            action_id = 'my-action'
            label = 'My Action'
            model = User
            add_item_title = 'XXX My Title'
            add_item_url_name = 'root'
            url_name = 'dashboard'
            item_queryset = User.objects.filter(is_active=False)

            placements = [
                ActionPlacement(attachment='test'),
            ]

        self.create_user(username='test')

        action = MyManageItemAction()
        request = self.create_http_request()
        placement = action.get_placement('test')
        renderer = AdminSidebarManageActionRenderer(action=action,
                                                    placement=placement)

        equeries = [
            {
                'annotations': {
                    '__count': Count('*'),
                },
                'model': User,
            },
        ]

        with assert_queries(equeries):
            extra_context = renderer.get_extra_context(
                request=request,
                context=Context())

        self.assertEqual(
            extra_context,
            {
                'action': action,
                'action_renderer': renderer,
                'add_item_title': 'XXX My Title',
                'add_item_url': '/',
                'attachment_point_id': 'test',
                'dom_element_id': 'action-test-my-action',
                'has_parent': False,
                'id': 'my-action',
                'is_active': False,
                'is_toplevel': True,
                'item_count': 0,
                'label': 'My Action',
                'placement': placement,
                'url': '/dashboard/',
                'verbose_label': None,
                'visible': True,
            })
