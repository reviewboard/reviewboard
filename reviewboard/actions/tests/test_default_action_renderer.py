"""Unit tests for reviewboard.actions.renderers.DefaultActionRenderer.

Version Added:
    7.1
"""

from __future__ import annotations

from django.template import Context
from django.utils.safestring import SafeString

from reviewboard.actions.renderers import DefaultActionRenderer
from reviewboard.actions.tests.base import TestAction, TestActionsRegistry
from reviewboard.deprecation import RemovedInReviewBoard90Warning
from reviewboard.testing import TestCase


class DefaultActionRendererTests(TestCase):
    """Unit tests for DefaultActionRenderer.

    Version Added:
        7.1
    """

    def test_get_js_view_data(self) -> None:
        """Testing DefaultActionRenderer.get_js_view_data"""
        action = TestAction()

        registry = TestActionsRegistry()
        registry.register(action)

        renderer = DefaultActionRenderer(action=action)

        self.assertEqual(renderer.get_js_view_data(context=Context()),
                         {})

    def test_render(self) -> None:
        """Testing DefaultActionRenderer.render"""
        action = TestAction()

        registry = TestActionsRegistry()
        registry.register(action)

        renderer = DefaultActionRenderer(action=action)
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
             <a href="#" id="action-review-request-test" role="button">
              Test Action 1
             </a>
            </li>
            """)

    def test_render_with_action_template(self) -> None:
        """Testing DefaultActionRenderer.render with action.template_name set
        """
        class MyAction(TestAction):
            template_name = 'actions/button_action.html'

        # We already test for the deprecation warning message in the action
        # tests. This just suppresses warning output for the test run.
        with self.assertWarns(RemovedInReviewBoard90Warning):
            action = MyAction()

        registry = TestActionsRegistry()
        registry.register(action)

        renderer = DefaultActionRenderer(action=action)
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
             <button aria-label="Test Action 1"
                     class="ink-c-button"
                     id="action-review-request-test"
                     type="button">
              <label class="ink-c-button__label">
               Test Action 1
              </label>
             </button>
            </li>
            """)

    def test_render_js(self) -> None:
        """Testing DefaultActionRenderer.render_js"""
        action = TestAction()

        registry = TestActionsRegistry()
        registry.register(action)

        renderer = DefaultActionRenderer(action=action)
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
                el: $('#action-review-request-test'),
                model: page.getAction("test"),
            }));
            """)
