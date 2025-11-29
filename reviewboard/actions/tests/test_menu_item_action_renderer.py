"""Unit tests for reviewboard.actions.renderers.MenuItemActionRenderer.

Version Added:
    7.1
"""

from __future__ import annotations

from django.template import Context
from django.utils.safestring import SafeString

from reviewboard.actions.renderers import MenuItemActionRenderer
from reviewboard.actions.tests.base import (TestActionsRegistry,
                                            TestMenuItemAction)
from reviewboard.deprecation import RemovedInReviewBoard90Warning
from reviewboard.testing import TestCase


class MenuItemActionRendererTests(TestCase):
    """Unit tests for MenuItemActionRenderer.

    Version Added:
        7.1
    """

    def test_render(self) -> None:
        """Testing MenuItemActionRenderer.render"""
        action = TestMenuItemAction()
        placement = action.get_placement('review-request')

        registry = TestActionsRegistry()
        registry.register(action)

        renderer = MenuItemActionRenderer(action=action,
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
            <a id="action-review-request-menu-item-action"
               role="button"
               href="#"
               hidden
               style="display: none;">
             <span class="my-icon"/>
             Menu Item Action 1
            </a>
            """)

    def test_render_with_action_template(self) -> None:
        """Testing MenuItemActionRenderer.render with action.template_name set
        """
        class MyAction(TestMenuItemAction):
            template_name = 'actions/button_action.html'

        # We already test for the deprecation warning message in the action
        # tests. This just suppresses warning output for the test run.
        with self.assertWarns(RemovedInReviewBoard90Warning):
            action = MyAction()

        placement = action.get_placement('review-request')

        registry = TestActionsRegistry()
        registry.register(action)

        renderer = MenuItemActionRenderer(action=action,
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
            <button class="ink-c-button"
                    id="action-review-request-menu-item-action"
                    type="button"
                    aria-label="Verbose Menu Item Action 1"
                    title="Menu Item 1 description."
                    hidden
                    style="display: none;">
             <span class="ink-c-button__icon my-icon"/>
             <label class="ink-c-button__label">
              Menu Item Action 1
             </label>
            </button>
            """)

    def test_render_js(self) -> None:
        """Testing MenuItemActionRenderer.render_js"""
        action = TestMenuItemAction()
        placement = action.get_placement('review-request')

        registry = TestActionsRegistry()
        registry.register(action)

        renderer = MenuItemActionRenderer(action=action,
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
            page.addActionView(new RB.Actions.MenuItemActionView({
                "attachmentPointID": "review-request",
                el: $('#action-review-request-menu-item-action'),
                model: page.getAction("menu-item-action"),
            }));
            """)
