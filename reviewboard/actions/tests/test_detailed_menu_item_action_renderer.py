"""Unit tests for reviewboard.actions.renderers.DetailedMenuItemActionRenderer.

Version Added:
    7.1
"""

from __future__ import annotations

from django.template import Context
from django.utils.safestring import SafeString

from reviewboard.actions.renderers import DetailedMenuItemActionRenderer
from reviewboard.actions.tests.base import (TestActionsRegistry,
                                            TestMenuItemAction)
from reviewboard.deprecation import RemovedInReviewBoard90Warning
from reviewboard.testing import TestCase


class DetailedMenuItemActionRendererTests(TestCase):
    """Unit tests for DetailedMenuItemActionRenderer.

    Version Added:
        7.1
    """

    def test_render(self) -> None:
        """Testing DetailedMenuItemActionRenderer.render"""
        action = TestMenuItemAction()

        registry = TestActionsRegistry()
        registry.register(action)

        renderer = DetailedMenuItemActionRenderer(action=action)
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
            <a
               id="action-menu-item-action"
               role="menuitem"
               data-custom-rendered="true"
               href="#"
               hidden
               style="display: none;">
             <h4>
              <span class="my-icon"/>
              Verbose Menu Item Action 1
             </h4>
             <p>
              Menu Item 1 description.
             </p>
            </a>
            """)

    def test_render_with_action_template(self) -> None:
        """Testing DetailedMenuItemActionRenderer.render with
        action.template_name set
        """
        class MyAction(TestMenuItemAction):
            template_name = 'actions/button_action.html'

        # We already test for the deprecation warning message in the action
        # tests. This just suppresses warning output for the test run.
        with self.assertWarns(RemovedInReviewBoard90Warning):
            action = MyAction()

        registry = TestActionsRegistry()
        registry.register(action)

        renderer = DetailedMenuItemActionRenderer(action=action)
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
                    id="action-menu-item-action"
                    aria-label="Verbose Menu Item Action 1"
                    title="Menu Item 1 description."
                    type="button"
                    hidden
                    style="display: none;">
             <span class="ink-c-button__icon my-icon"/>
             <label class="ink-c-button__label">
              Menu Item Action 1
             </label>
            </button>
            """)

    def test_render_js(self) -> None:
        """Testing DetailedMenuItemActionRenderer.render_js"""
        action = TestMenuItemAction()

        registry = TestActionsRegistry()
        registry.register(action)

        renderer = DetailedMenuItemActionRenderer(action=action)
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
                attachmentPointID: "review-request",
                el: $('#action-menu-item-action'),
                model: page.addAction(new RB.Actions.Action(
                    {"id": "menu-item-action",
                     "visible": true,
                     "domID": "action-menu-item-action",
                     "iconClass": "my-icon",
                     "label": "Menu Item Action 1",
                     "verboseLabel": "Verbose Menu Item Action 1",
                     "url": "#"},
                    { parse: true }
                ))
            }));
            """)
