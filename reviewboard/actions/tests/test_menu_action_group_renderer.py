"""Unit tests for reviewboard.actions.renderers.MenuActionGroupRenderer.

Version Added:
    7.1
"""

from __future__ import annotations

from django.template import Context
from django.utils.safestring import SafeString

from reviewboard.actions.renderers import MenuActionGroupRenderer
from reviewboard.actions.tests.base import TestActionsRegistry, TestMenuAction
from reviewboard.deprecation import RemovedInReviewBoard90Warning
from reviewboard.testing import TestCase


class MenuActionGroupRendererTests(TestCase):
    """Unit tests for MenuActionGroupRenderer.

    Version Added:
        7.1
    """

    def test_render(self) -> None:
        """Testing MenuActionGroupRenderer.render"""
        action = TestMenuAction()

        registry = TestActionsRegistry()
        registry.register(action)

        renderer = MenuActionGroupRenderer(action=action)
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
                id="action-menu-action"
                role="menuitem">
             <a aria-label="Test Menu"
                href="#"
                role="presentation">
              <label class="rb-c-actions__action-label">
               Test Menu
              </label>
              <span class="ink-i-dropdown"/>
             </a>
            </li>
            """)

    def test_render_with_action_template(self) -> None:
        """Testing MenuActionGroupRenderer.render with action.template_name
        set
        """
        class MyAction(TestMenuAction):
            template_name = 'actions/button_action.html'

        # We already test for the deprecation warning message in the action
        # tests. This just suppresses warning output for the test run.
        with self.assertWarns(RemovedInReviewBoard90Warning):
            action = MyAction()

        registry = TestActionsRegistry()
        registry.register(action)

        renderer = MenuActionGroupRenderer(action=action)
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
            <li class="rb-c-actions__action" role="presentation">
             <button aria-label="Test Menu"
                     class="ink-c-button"
                     id="action-menu-action"
                     type="button">
              <label class="ink-c-button__label">
               Test Menu
              </label>
             </button>
            </li>
            """)

    def test_render_js(self) -> None:
        """Testing MenuActionGroupRenderer.render_js"""
        action = TestMenuAction()

        registry = TestActionsRegistry()
        registry.register(action)

        renderer = MenuActionGroupRenderer(action=action)
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
            page.addActionView(new RB.Actions.MenuActionView({
                "attachmentPointID": "review-request",
                el:  $('#action-menu-action'),
                model: page.getAction("menu-action"),
            }));
            """)
