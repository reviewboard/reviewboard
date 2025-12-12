"""Unit tests for reviewboard.actions.renderers.SidebarActionGroupRenderer.

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
from reviewboard.actions.renderers import SidebarActionGroupRenderer
from reviewboard.actions.tests.base import TestActionsRegistry
from reviewboard.testing import TestCase


class _MySidebarGroupAction(BaseGroupAction):
    action_id = 'test-sidebar-group'
    label = 'My Group'

    placements = [
        ActionPlacement(attachment=AttachmentPoint.HEADER)
    ]


class _MySidebarItem1(BaseAction):
    action_id = 'test-sidebar-item1'
    label = 'Item 1'

    placements = [
        ActionPlacement(attachment=AttachmentPoint.HEADER,
                        parent_id=_MySidebarGroupAction.action_id),
    ]


class _MySidebarSubGroup1Action(BaseGroupAction):
    action_id = 'test-sidebar-subgroup1'
    label = 'My Sub-Group 1'

    placements = [
        ActionPlacement(attachment=AttachmentPoint.HEADER,
                        parent_id=_MySidebarGroupAction.action_id),
    ]


class _MySidebarItem2(BaseAction):
    action_id = 'test-sidebar-item2'
    label = 'Item 2'

    placements = [
        ActionPlacement(attachment=AttachmentPoint.HEADER,
                        parent_id=_MySidebarSubGroup1Action.action_id),
    ]


class _MySidebarSubGroup2Action(BaseGroupAction):
    action_id = 'test-sidebar-subgroup2'
    label = 'My Sub-Group 2'

    placements = [
        ActionPlacement(attachment=AttachmentPoint.HEADER,
                        parent_id=_MySidebarGroupAction.action_id),
    ]


class _MySidebarItem3(BaseAction):
    action_id = 'test-sidebar-item3'
    label = 'Item 3'

    placements = [
        ActionPlacement(attachment=AttachmentPoint.HEADER,
                        parent_id=_MySidebarSubGroup2Action.action_id),
    ]


class SidebarActionGroupRendererTests(TestCase):
    """Unit tests for SidebarActionGroupRenderer.

    Version Added:
        7.1
    """

    def test_render(self) -> None:
        """Testing SidebarActionGroupRenderer.render"""
        group_action = _MySidebarGroupAction()
        subgroup1_action = _MySidebarSubGroup1Action()
        subgroup2_action = _MySidebarSubGroup2Action()
        item1_action = _MySidebarItem1()
        item2_action = _MySidebarItem2()
        item3_action = _MySidebarItem3()

        placement = group_action.get_placement(AttachmentPoint.HEADER)

        registry = TestActionsRegistry()
        registry.register(group_action)
        registry.register(item1_action)
        registry.register(subgroup1_action)
        registry.register(subgroup2_action)
        registry.register(item2_action)
        registry.register(item3_action)

        renderer = SidebarActionGroupRenderer(action=group_action,
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
            <li class="rb-c-actions__action rb-c-sidebar__section"
                id="action-header-test-sidebar-group"
                aria-labelledby="test-sidebar-group__label"
                role="group">
             <header class="rb-c-sidebar__section-header"
                     id="test-sidebar-group__label">
              My Group
             </header>
             <ul class="rb-c-sidebar__items">
              <li class="rb-c-sidebar__nav-item"
                  id="action-header-test-sidebar-item1">
               <a class="rb-c-sidebar__item-label">
                Item 1
               </a>
              </li>
              <li class="rb-c-actions__action rb-c-sidebar__section"
                  id="action-header-test-sidebar-subgroup1"
                  aria-labelledby="test-sidebar-subgroup1__label"
                  role="group">
               <header class="rb-c-sidebar__section-header"
                       id="test-sidebar-subgroup1__label">
                My Sub-Group 1
               </header>
               <ul class="rb-c-sidebar__items">
                <li class="rb-c-sidebar__nav-item"
                    id="action-header-test-sidebar-item2">
                 <a class="rb-c-sidebar__item-label">
                  Item 2
                 </a>
                </li>
               </ul>
              </li>
              <li class="rb-c-actions__action rb-c-sidebar__section"
                  id="action-header-test-sidebar-subgroup2"
                  aria-labelledby="test-sidebar-subgroup2__label"
                  role="group">
               <header class="rb-c-sidebar__section-header"
                       id="test-sidebar-subgroup2__label">
                My Sub-Group 2
               </header>
               <ul class="rb-c-sidebar__items">
                <li class="rb-c-sidebar__nav-item"
                    id="action-header-test-sidebar-item3">
                 <a class="rb-c-sidebar__item-label">
                  Item 3
                 </a>
                </li>
               </ul>
              </li>
             </ul>
            </li>
            """)

    def test_render_js(self) -> None:
        """Testing SidebarActionGroupRenderer.render_js"""
        group_action = _MySidebarGroupAction()
        subgroup1_action = _MySidebarSubGroup1Action()
        subgroup2_action = _MySidebarSubGroup2Action()
        item1_action = _MySidebarItem1()
        item2_action = _MySidebarItem2()
        item3_action = _MySidebarItem3()
        placement = group_action.get_placement(AttachmentPoint.HEADER)

        registry = TestActionsRegistry()
        registry.register(group_action)
        registry.register(item1_action)
        registry.register(subgroup1_action)
        registry.register(subgroup2_action)
        registry.register(item2_action)
        registry.register(item3_action)

        renderer = SidebarActionGroupRenderer(action=group_action,
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
                el: $('#action-header-test-sidebar-group'),
                model: page.getAction("test-sidebar-group"),
            }));
            """)
