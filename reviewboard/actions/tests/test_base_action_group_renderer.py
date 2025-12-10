"""Unit tests for reviewboard.actions.renderers.BaseActionGroupRenderer.

Version Added:
    7.1
"""

from __future__ import annotations

from django.template import Context
from django.utils.safestring import SafeString

from reviewboard.actions.renderers import (BaseActionGroupRenderer,
                                           ButtonActionRenderer,
                                           DefaultActionGroupRenderer,
                                           MenuActionGroupRenderer)
from reviewboard.actions.tests.base import (TestActionsRegistry,
                                            TestGroupAction,
                                            TestGroupActionWithSubgroups,
                                            TestGroupItemAction1,
                                            TestGroupItemAction2,
                                            TestSubgroupAction)
from reviewboard.testing import TestCase


class BaseActionGroupRendererTests(TestCase):
    """Unit tests for BaseActionGroupRenderer.

    Version Added:
        7.1
    """

    def test_get_js_view_data(self) -> None:
        """Testing BaseActionGroupRenderer.get_js_view_data"""
        action = TestGroupAction()
        placement = action.get_placement('review-request')

        renderer = BaseActionGroupRenderer(action=action,
                                           placement=placement)

        self.assertEqual(renderer.get_js_view_data(context=Context()),
                         {})

    def test_get_extra_context(self) -> None:
        """Testing BaseActionGroupRenderer.get_extra_context"""
        action = TestGroupAction()
        placement = action.get_placement('review-request')

        item_action_1 = TestGroupItemAction1()
        item_action_2 = TestGroupItemAction2()

        registry = TestActionsRegistry()
        registry.register(action)
        registry.register(item_action_1)
        registry.register(item_action_2)

        renderer = BaseActionGroupRenderer(action=action,
                                           placement=placement)
        request = self.create_http_request()
        context = Context({
            'request': request,
        })

        # This should just call out to the action's get_extra_context().
        self.assertEqual(
            renderer.get_extra_context(request=request,
                                       context=context),
            {
                'action': action,
                'action_renderer': renderer,
                'attachment_point_id': 'review-request',
                'children': [
                    item_action_1,
                    item_action_2,
                ],
                'dom_element_id': 'action-review-request-group-action',
                'has_parent': False,
                'id': 'group-action',
                'is_toplevel': True,
                'label': 'Test Group',
                'placement': placement,
                'url': '#',
                'verbose_label': None,
                'visible': True,
            })

    def test_render(self) -> None:
        """Testing BaseActionGroupRenderer.render"""
        action = TestGroupAction()
        placement = action.get_placement('review-request')

        item_action_1 = TestGroupItemAction1()
        item_action_2 = TestGroupItemAction2()

        registry = TestActionsRegistry()
        registry.register(action)
        registry.register(item_action_1)
        registry.register(item_action_2)

        renderer = BaseActionGroupRenderer(action=action,
                                           placement=placement)
        request = self.create_http_request()
        context = Context({
            'request': request,
        })

        html = renderer.render(request=request,
                               context=context)

        # There's no template on the base renderer, so this should be empty.
        self.assertIsInstance(html, SafeString)
        self.assertEqual(html, '')

    def test_render_with_subgroup_renderer(self) -> None:
        """Testing BaseActionGroupRenderer.render with subclass using
        subgroup renderer
        """
        class MyActionGroupRenderer(DefaultActionGroupRenderer):
            default_item_renderer_cls = ButtonActionRenderer
            default_subgroup_renderer_cls = MenuActionGroupRenderer

        action = TestGroupActionWithSubgroups()
        placement = action.get_placement('header')

        item_action_1 = TestGroupItemAction1()
        item_action_2 = TestGroupItemAction2()
        subgroup = TestSubgroupAction()

        registry = TestActionsRegistry()
        registry.register(action)
        registry.register(item_action_1)
        registry.register(item_action_2)
        registry.register(subgroup)

        renderer = MyActionGroupRenderer(action=action,
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
            <li class="rb-c-actions__action"
                role="group">
             <button class="ink-c-button"
                     id="action-header-group-item-1-action"
                     aria-label="Group Item 1"
                     type="button">
              <label class="ink-c-button__label">
               Group Item 1
              </label>
             </button>
             <span id="action-header-subgroup-action"
                   role="presentation">
              <a aria-label="Subgroup"
                 href="#"
                 role="presentation">
               Subgroup
               <span class="ink-i-dropdown"></span>
              </a>
              <div hidden
                   style="display: none;">
               <a id="action-header-group-item-2-action"
                  href="#"
                  role="button">
                Group Item 2
               </a>
              </div>
             </span>
            </li>
            """)

    def test_render_with_subgroup_renderer_self(self) -> None:
        """Testing BaseActionGroupRenderer.render with subclass using self
        as subgroup renderer
        """
        class MyActionGroupRenderer(DefaultActionGroupRenderer):
            default_subgroup_renderer_cls = 'self'

        action = TestGroupActionWithSubgroups()
        placement = action.get_placement('header')

        item_action_1 = TestGroupItemAction1()
        item_action_2 = TestGroupItemAction2()
        subgroup = TestSubgroupAction()

        registry = TestActionsRegistry()
        registry.register(action)
        registry.register(item_action_1)
        registry.register(item_action_2)
        registry.register(subgroup)

        renderer = MyActionGroupRenderer(action=action,
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
            <li class="rb-c-actions__action"
                role="group">
             <a id="action-header-group-item-1-action"
                role="button"
                href="#">
              Group Item 1
             </a>
             <a id="action-header-group-item-2-action"
                href="#"
                role="button">
              Group Item 2
             </a>
            </li>
            """)

    def test_render_js(self) -> None:
        """Testing BaseActionGroupRenderer.render_js"""
        action = TestGroupAction()
        placement = action.get_placement('review-request')

        registry = TestActionsRegistry()
        registry.register(action)

        renderer = BaseActionGroupRenderer(action=action,
                                           placement=placement)
        request = self.create_http_request()
        context = Context({
            'request': request,
        })

        html = renderer.render_js(request=request,
                                  context=context)

        self.assertIsInstance(html, SafeString)
        self.assertHTMLEqual(
            html,
            """
            page.addActionView(new RB.Actions.ActionView({
                "attachmentPointID": "review-request",
                el: $('#action-review-request-group-action'),
                model: page.getAction("group-action"),
            }));
            """)
