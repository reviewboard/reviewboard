"""Unit tests for reviewboard.actions.renderers.BaseActionRenderer.

Version Added:
    7.1
"""

from __future__ import annotations

from django.template import Context
from django.utils.safestring import SafeString

from reviewboard.actions.renderers import BaseActionRenderer
from reviewboard.actions.tests.base import TestAction, TestActionsRegistry
from reviewboard.deprecation import RemovedInReviewBoard90Warning
from reviewboard.testing import TestCase


class BaseActionRendererTests(TestCase):
    """Unit tests for BaseActionRenderer.

    Version Added:
        7.1
    """

    def test_get_js_view_data(self) -> None:
        """Testing BaseActionRenderer.get_js_view_data"""
        renderer = BaseActionRenderer(action=TestAction())

        self.assertEqual(renderer.get_js_view_data(context=Context()),
                         {})

    def test_get_extra_context(self) -> None:
        """Testing BaseActionRenderer.get_extra_context"""
        action = TestAction()

        registry = TestActionsRegistry()
        registry.register(action)

        renderer = BaseActionRenderer(action=action)
        request = self.create_http_request()
        context = Context()

        # This should just call out to the action's get_extra_context().
        self.assertEqual(
            renderer.get_extra_context(request=request,
                                       context=context),
            {
                'action': action,
                'action_renderer': renderer,
                'attachment_point_id': 'review-request',
                'dom_element_id': 'action-test',
                'has_parent': False,
                'id': 'test',
                'label': 'Test Action 1',
                'url': '#',
                'verbose_label': None,
                'visible': True,
            })

    def test_render(self) -> None:
        """Testing BaseActionRenderer.render"""
        action = TestAction()

        registry = TestActionsRegistry()
        registry.register(action)

        renderer = BaseActionRenderer(action=action)
        request = self.create_http_request()
        context = Context({
            'request': request,
        })

        html = renderer.render(request=request,
                               context=context)

        self.assertIsInstance(html, SafeString)
        self.assertEqual(html, '')

    def test_render_with_action_template(self) -> None:
        """Testing BaseActionRenderer.render with action.template_name set"""
        class MyAction(TestAction):
            template_name = 'actions/button_action.html'

        # We already test for the deprecation warning message in the action
        # tests. This just suppresses warning output for the test run.
        with self.assertWarns(RemovedInReviewBoard90Warning):
            action = MyAction()

        registry = TestActionsRegistry()
        registry.register(action)

        renderer = BaseActionRenderer(action=action)
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
                     id="action-test"
                     type="button">
              <label class="ink-c-button__label">
               Test Action 1
              </label>
             </button>
            </li>
            """)

    def test_render_js(self) -> None:
        """Testing BaseActionRenderer.render_js"""
        action = TestAction()

        registry = TestActionsRegistry()
        registry.register(action)

        renderer = BaseActionRenderer(action=action)
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
                el: $('#action-test'),
                model: page.getAction("test"),
            }));
            """)
