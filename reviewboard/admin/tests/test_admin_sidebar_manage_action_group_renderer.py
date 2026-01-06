"""Unit tests for AdminSidebarManageActionGroupRenderer.

Version Added:
    7.1
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import kgb
from django.contrib.auth.models import User
from django.core.cache import cache
from django.db.models import Count
from django.template import Context
from django_assert_queries import assert_queries
from djblets.cache.backend import make_cache_key

from reviewboard.actions.base import ActionPlacement, BaseGroupAction
from reviewboard.actions.tests.base import TestActionsRegistry
from reviewboard.admin.actions import (AdminManageNavGroupAction,
                                       AdminSidebarManageActionGroupRenderer,
                                       BaseAdminSidebarManageItemAction)
from reviewboard.testing.testcase import TestCase

if TYPE_CHECKING:
    from django.db.models import Model


class BaseAdminSidebarManageItemActionTests(kgb.SpyAgency, TestCase):
    """Unit tests for AdminSidebarManageActionGroupRenderer.

    Version Added:
        7.1
    """

    def test_get_extra_context(self) -> None:
        """Testing AdminSidebarManageActionGroupRenderer.get_extra_context"""
        class MyManageGroupAction(BaseGroupAction):
            action_id = 'my-group'
            label = 'My Group'

            placements = [
                ActionPlacement(attachment='test'),
            ]

        class MyManageItemAction(BaseAdminSidebarManageItemAction):
            action_id = 'my-action'
            label = 'My Action'
            add_item_url_name = 'admin:auth_user_add'
            item_queryset = User.objects.all()

            placements = [
                ActionPlacement(attachment='test',
                                parent_id=MyManageGroupAction.action_id),
            ]

        group_action = MyManageGroupAction()
        item_action = MyManageItemAction()

        test_registry = TestActionsRegistry()
        test_registry.register(group_action)
        test_registry.register(item_action)

        self.create_user(username='test')

        request = self.create_http_request()
        placement = group_action.get_placement('test')
        renderer = AdminSidebarManageActionGroupRenderer(
            action=group_action,
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
                context=Context({
                    'request': request,
                }))

        self.assertEqual(
            extra_context,
            {
                'action': group_action,
                'action_renderer': renderer,
                'add_item_urls': {
                    'my-action': '/admin/db/auth/user/add/',
                },
                'attachment_point_id': 'test',
                'children': [
                    item_action,
                ],
                'dom_element_id': 'action-test-my-group',
                'has_parent': False,
                'id': 'my-group',
                'is_toplevel': True,
                'item_counts': {
                    'my-action': 1,
                },
                'label': 'My Group',
                'placement': placement,
                'url': '#',
                'verbose_label': None,
                'visible': True,
            })

        self.assertEqual(
            cache.get(make_cache_key('admin-sidebar-manage-state')),
            {
                'add_item_urls': {
                    'my-action': '/admin/db/auth/user/add/',
                },
                'item_counts': {
                    'my-action': 1,
                },
            })

        # A second call should reuse cache.
        with self.assertNumQueries(0):
            extra_context = renderer.get_extra_context(
                request=request,
                context=Context({
                    'request': request,
                }))

        self.assertEqual(
            extra_context,
            {
                'action': group_action,
                'action_renderer': renderer,
                'add_item_urls': {
                    'my-action': '/admin/db/auth/user/add/',
                },
                'attachment_point_id': 'test',
                'children': [
                    item_action,
                ],
                'dom_element_id': 'action-test-my-group',
                'has_parent': False,
                'id': 'my-group',
                'is_toplevel': True,
                'item_counts': {
                    'my-action': 1,
                },
                'label': 'My Group',
                'placement': placement,
                'url': '#',
                'verbose_label': None,
                'visible': True,
            })

    def test_cache_invalidate_after_save_new_managed(self) -> None:
        """Testing AdminSidebarManageActionGroupRenderer item counts cache
        invalidates after saving new managed model
        """
        self._patch_managed_models({User})

        key = make_cache_key('admin-sidebar-manage-state')

        cache.add(
            key,
            {
                'add_item_urls': {
                    'my-action': '/admin/db/auth/user/add/',
                },
                'item_counts': {
                    'my-action': 1,
                },
            })

        # Save a new object.
        self.create_user(username='test1')

        self.assertIsNone(cache.get(key))

    def test_cache_invalidate_after_save_new_unmanaged(self) -> None:
        """Testing AdminSidebarManageActionGroupRenderer item counts cache
        does not invalidate after saving new unmanaged model
        """
        key = make_cache_key('admin-sidebar-manage-state')

        cache.add(
            key,
            {
                'add_item_urls': {
                    'my-action': '/admin/db/auth/user/add/',
                },
                'item_counts': {
                    'my-action': 1,
                },
            })

        # Save a new object.
        self.create_user(username='test1')

        self.assertEqual(
            cache.get(key),
            {
                'add_item_urls': {
                    'my-action': '/admin/db/auth/user/add/',
                },
                'item_counts': {
                    'my-action': 1,
                },
            })

    def test_cache_invalidate_after_delete_managed(self) -> None:
        """Testing AdminSidebarManageActionGroupRenderer item counts cache
        invalidates after delete of managed model
        """
        self._patch_managed_models({User})

        user = self.create_user(username='test1')

        key = make_cache_key('admin-sidebar-manage-state')

        cache.add(
            key,
            {
                'add_item_urls': {
                    'my-action': '/admin/db/auth/user/add/',
                },
                'item_counts': {
                    'my-action': 1,
                },
            })

        # Delete the object.
        user.delete()

        self.assertIsNone(cache.get(key))

    def test_cache_invalidate_after_delete_unmanaged(self) -> None:
        """Testing AdminSidebarManageActionGroupRenderer item counts cache
        does not invalidate after delete of unmanaged model
        """
        user = self.create_user(username='test1')

        key = make_cache_key('admin-sidebar-manage-state')

        cache.add(
            key,
            {
                'add_item_urls': {
                    'my-action': '/admin/db/auth/user/add/',
                },
                'item_counts': {
                    'my-action': 1,
                },
            })

        # Delete the object.
        user.delete()

        self.assertEqual(
            cache.get(key),
            {
                'add_item_urls': {
                    'my-action': '/admin/db/auth/user/add/',
                },
                'item_counts': {
                    'my-action': 1,
                },
            })

    def test_cache_preserves_after_save_update_managed(self) -> None:
        """Testing AdminSidebarManageActionGroupRenderer item counts cache
        does not invalidate after saving an existing managed model
        """
        self._patch_managed_models({User})

        user = self.create_user(username='test1')

        key = make_cache_key('admin-sidebar-manage-state')

        cache.add(
            key,
            {
                'add_item_urls': {
                    'my-action': '/admin/db/auth/user/add/',
                },
                'item_counts': {
                    'my-action': 1,
                },
            })

        # Update the object.
        user.save()

        self.assertEqual(
            cache.get(key),
            {
                'add_item_urls': {
                    'my-action': '/admin/db/auth/user/add/',
                },
                'item_counts': {
                    'my-action': 1,
                },
            })

    def test_cache_preserves_after_save_update_unmanaged(self) -> None:
        """Testing AdminSidebarManageActionGroupRenderer item counts cache
        does not invalidate after saving an existing unmanaged model
        """
        user = self.create_user(username='test1')

        key = make_cache_key('admin-sidebar-manage-state')

        cache.add(
            key,
            {
                'add_item_urls': {
                    'my-action': '/admin/db/auth/user/add/',
                },
                'item_counts': {
                    'my-action': 1,
                },
            })

        # Update the object.
        user.save()

        self.assertEqual(
            cache.get(key),
            {
                'add_item_urls': {
                    'my-action': '/admin/db/auth/user/add/',
                },
                'item_counts': {
                    'my-action': 1,
                },
            })

    def _patch_managed_models(
        self,
        models: set[type[Model]],
    ) -> None:
        """Patch managed models into the manage group state.

        These will be cleaned up when the test ends.

        Args:
            models (set of type):
                The models to patch in as managed models.
        """
        setattr(AdminManageNavGroupAction, '_managed_models', models)
        self.addCleanup(lambda: delattr(AdminManageNavGroupAction,
                                        '_managed_models'))
