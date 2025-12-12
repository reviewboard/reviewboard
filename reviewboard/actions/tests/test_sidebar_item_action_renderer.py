"""Unit tests for reviewboard.actions.renderers.SidebarItemActionRenderer.

Version Added:
    7.1
"""

from __future__ import annotations

from django.template import Context
from django.utils.safestring import SafeString

from reviewboard.actions.base import (ActionPlacement,
                                      AttachmentPoint,
                                      BaseAction,
                                      BaseGroupAction)
from reviewboard.actions.renderers import SidebarItemActionRenderer
from reviewboard.actions.tests.base import TestActionsRegistry
from reviewboard.testing import TestCase


class _MySidebarGroupAction(BaseGroupAction):
    action_id = 'test-sidebar-group'
    label = 'My Group'

    placements = [
        ActionPlacement(attachment=AttachmentPoint.HEADER)
    ]


class _MySidebarItem(BaseAction):
    action_id = 'test-sidebar-item'
    label = 'Item 1'
    url_name = 'dashboard'

    placements = [
        ActionPlacement(attachment=AttachmentPoint.HEADER,
                        parent_id=_MySidebarGroupAction.action_id),
    ]


class SidebarItemActionRendererTests(TestCase):
    """Unit tests for SidebarItemActionRenderer.

    Version Added:
        7.1
    """

    def test_render(self) -> None:
        """Testing SidebarItemActionRenderer.render"""
        group_action = _MySidebarGroupAction()
        item_action = _MySidebarItem()
        placement = item_action.get_placement(AttachmentPoint.HEADER)

        registry = TestActionsRegistry()
        registry.register(group_action)
        registry.register(item_action)

        renderer = SidebarItemActionRenderer(action=item_action,
                                             placement=placement)
        request = self.create_http_request()
        context = Context({
            'request': request,
        })

        html = renderer.render(request=request,
                               context=context)

        self.assertIsInstance(html, SafeString)
        self.assertHTMLEqual(
            html,
            """
            <li class="rb-c-sidebar__nav-item"
                id="action-header-test-sidebar-item">
             <a class="rb-c-sidebar__item-label"
                href="/dashboard/">
              Item 1
             </a>
            </li>
            """)

    def test_render_with_current_url(self) -> None:
        """Testing SidebarItemActionRenderer.render with URL as current page
        """
        group_action = _MySidebarGroupAction()
        item_action = _MySidebarItem()
        placement = item_action.get_placement(AttachmentPoint.HEADER)

        registry = TestActionsRegistry()
        registry.register(group_action)
        registry.register(item_action)

        renderer = SidebarItemActionRenderer(action=item_action,
                                             placement=placement)
        request = self.create_http_request(path='/dashboard/',
                                           url_name='dashboard')
        context = Context({
            'request': request,
        })

        html = renderer.render(request=request,
                               context=context)

        self.assertIsInstance(html, SafeString)
        self.assertHTMLEqual(
            html,
            """
            <li class="rb-c-sidebar__nav-item"
                id="action-header-test-sidebar-item"
                aria-current="page">
             <a class="rb-c-sidebar__item-label"
                href="/dashboard/">
              Item 1
             </a>
            </li>
            """)

    def test_render_js(self) -> None:
        """Testing SidebarItemActionRenderer.render_js"""
        group_action = _MySidebarGroupAction()
        item_action = _MySidebarItem()
        placement = item_action.get_placement(AttachmentPoint.HEADER)

        registry = TestActionsRegistry()
        registry.register(group_action)
        registry.register(item_action)

        renderer = SidebarItemActionRenderer(action=item_action,
                                             placement=placement)
        request = self.create_http_request()
        context = Context({
            'request': request,
        })

        js = renderer.render_js(request=request,
                                context=context)

        self.assertIsInstance(js, SafeString)
        self.assertHTMLEqual(
            js,
            """
            page.addActionView(new RB.Actions.ActionView({
                "attachmentPointID": "header",
                el: $('#action-header-test-sidebar-item'),
                model: page.getAction("test-sidebar-item"),
            }));
            """)
