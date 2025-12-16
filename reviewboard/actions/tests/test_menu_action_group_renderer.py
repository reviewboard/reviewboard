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
        placement = action.get_placement('review-request')

        registry = TestActionsRegistry()
        registry.register(action)

        renderer = MenuActionGroupRenderer(action=action,
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
                role="menuitem">
             <span id="action-review-request-menu-action"
                   role="presentation">
              <a aria-label="Test Menu"
                 href="#"
                 role="presentation">
               Test Menu
               <span class="ink-i-dropdown"/>
              </a>
              <div hidden style="display: none;"></div>
             </span>
            </li>
            """)

    def test_render_with_icon_only(self) -> None:
        """Testing MenuActionGroupRenderer.render with icon only"""
        class MyTestMenuAction(TestMenuAction):
            icon_class = 'my-icon'
            label = ''
            verbose_label = 'My menu'

        action = MyTestMenuAction()
        placement = action.get_placement('review-request')

        registry = TestActionsRegistry()
        registry.register(action)

        renderer = MenuActionGroupRenderer(action=action,
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
            <li class="rb-c-actions__action -is-icon"
                role="menuitem">
             <span id="action-review-request-menu-action"
                   role="presentation">
              <a aria-label="My menu"
                 href="#"
                 role="presentation">
               <span class="my-icon"></span>
              </a>
              <div hidden style="display: none;"></div>
             </span>
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

        placement = action.get_placement('review-request')

        registry = TestActionsRegistry()
        registry.register(action)

        renderer = MenuActionGroupRenderer(action=action,
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
            <li class="rb-c-actions__action" role="presentation">
             <button aria-label="Test Menu"
                     class="ink-c-button"
                     id="action-review-request-menu-action"
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
        placement = action.get_placement('review-request')

        registry = TestActionsRegistry()
        registry.register(action)

        renderer = MenuActionGroupRenderer(action=action,
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
            page.addActionView(new RB.Actions.MenuActionView({
                "attachmentPointID": "review-request",
                el:  $('#action-review-request-menu-action'),
                model: page.getAction("menu-action"),
            }));
            """)
