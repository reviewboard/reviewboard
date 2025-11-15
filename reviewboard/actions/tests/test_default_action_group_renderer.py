"""Unit tests for reviewboard.actions.renderers.DefaultActionGroupRenderer.

Version Added:
    7.1
"""

from __future__ import annotations

from django.template import Context
from django.utils.safestring import SafeString

from reviewboard.actions.renderers import DefaultActionGroupRenderer
from reviewboard.actions.tests.base import TestActionsRegistry, TestGroupAction
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

        registry = TestActionsRegistry()
        registry.register(action)

        renderer = DefaultActionGroupRenderer(action=action)
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
                id="action-group-action"
                role="group">
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

        registry = TestActionsRegistry()
        registry.register(action)

        renderer = DefaultActionGroupRenderer(action=action)
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
                     id="action-group-action"
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

        registry = TestActionsRegistry()
        registry.register(action)

        renderer = DefaultActionGroupRenderer(action=action)
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
                el: $('#action-group-action'),
                model: page.addAction(new RB.Actions.GroupAction(
                    {"id": "group-action",
                     "visible": true,
                     "domID": "action-group-action",
                     "label": "Test Group",
                     "url": "#",
                     "children": []},
                    { parse: true }
                ))
            }));
            """)
