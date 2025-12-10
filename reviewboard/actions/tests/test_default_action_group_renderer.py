"""Unit tests for reviewboard.actions.renderers.DefaultActionGroupRenderer.

Version Added:
    7.1
"""

from __future__ import annotations

from django.template import Context
from django.utils.safestring import SafeString

from reviewboard.actions.renderers import DefaultActionGroupRenderer
from reviewboard.actions.tests.base import (TestActionsRegistry,
                                            TestGroupAction,
                                            TestGroupActionWithSubgroups,
                                            TestGroupItemAction1,
                                            TestGroupItemAction2,
                                            TestSubgroupAction)
from reviewboard.deprecation import RemovedInReviewBoard90Warning
from reviewboard.testing import TestCase


class DefaultActionGroupRendererTests(TestCase):
    """Unit tests for DefaultActionGroupRenderer.

    Version Added:
        7.1
    """

    def test_render(self) -> None:
        """Testing DefaultActionGroupRenderer.render"""
        action = TestGroupAction()
        placement = action.get_placement('review-request')

        item_action_1 = TestGroupItemAction1()
        item_action_2 = TestGroupItemAction2()

        registry = TestActionsRegistry()
        registry.register(action)
        registry.register(item_action_1)
        registry.register(item_action_2)

        renderer = DefaultActionGroupRenderer(action=action,
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
                id="action-review-request-group-action"
                role="group">
             <a id="action-review-request-group-item-1-action"
                href="#"
                role="button"
                hidden
                style="display: none;">
              Group Item 1
             </a>
             <a id="action-review-request-group-item-2-action"
                href="#"
                role="button"
                hidden
                style="display: none;">
              Group Item 2
             </a>
            </li>
            """)

    def test_render_with_subgroups(self) -> None:
        """Testing DefaultActionGroupRenderer.render with subgroups"""
        # This renderer does not support subgroups.
        action = TestGroupActionWithSubgroups()
        placement = action.get_placement('header')

        item_action_1 = TestGroupItemAction1()
        item_action_2 = TestGroupItemAction2()
        subgroup = TestSubgroupAction()

        registry = TestActionsRegistry()
        registry.register(action)
        registry.register(subgroup)
        registry.register(item_action_1)
        registry.register(item_action_2)

        renderer = DefaultActionGroupRenderer(action=action,
                                              placement=placement)
        request = self.create_http_request()
        context = Context({
            'request': request,
        })

        with self.assertLogs() as logs:
            html = renderer.render(request=request,
                                   context=context)

        self.assertEqual(
            logs.output,
            [
                "ERROR:reviewboard.actions.renderers:Could not render "
                "action 'subgroup-action' inside of group action "
                "'group-with-subgroups-action' in attachment point "
                "'header'. This location does not allow for nesting of "
                "groups.",
            ])

        self.assertIsInstance(html, SafeString)
        self.assertHTMLEqual(
            html,
            """
            <li class="rb-c-actions__action"
                id="action-header-group-with-subgroups-action"
                role="group">
             <a id="action-header-group-item-1-action"
                href="#"
                role="button"
                hidden
                style="display: none;">
              Group Item 1
             </a>
            </li>
            """)

    def test_render_with_action_template(self) -> None:
        """Testing DefaultActionGroupRenderer.render with action.template_name
        set
        """
        class MyAction(TestGroupAction):
            template_name = 'actions/button_action.html'

        # We already test for the deprecation warning message in the action
        # tests. This just suppresses warning output for the test run.
        with self.assertWarns(RemovedInReviewBoard90Warning):
            action = MyAction()

        placement = action.get_placement('review-request')

        registry = TestActionsRegistry()
        registry.register(action)

        renderer = DefaultActionGroupRenderer(action=action,
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
                role="presentation">
             <button aria-label="Test Group"
                     class="ink-c-button"
                     id="action-review-request-group-action"
                     type="button">
              <label class="ink-c-button__label">
               Test Group
              </label>
             </button>
            </li>
            """)

    def test_render_js(self) -> None:
        """Testing DefaultActionGroupRenderer.render_js"""
        action = TestGroupAction()
        placement = action.get_placement('review-request')

        registry = TestActionsRegistry()
        registry.register(action)

        renderer = DefaultActionGroupRenderer(action=action,
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
                "attachmentPointID": "review-request",
                el: $('#action-review-request-group-action'),
                model: page.getAction("group-action"),
            }));
            """)
