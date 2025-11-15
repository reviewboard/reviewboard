"""Unit tests for reviewboard.actions.base.BaseAction.

Version Added:
    7.1
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.template import Context
from django.utils.safestring import SafeString

from reviewboard.actions.base import BaseAction
from reviewboard.actions.errors import MissingActionRendererError
from reviewboard.actions.renderers import ButtonActionRenderer
from reviewboard.actions.tests.base import SpecialButtonActionRenderer
from reviewboard.deprecation import RemovedInReviewBoard90Warning
from reviewboard.testing import TestCase

if TYPE_CHECKING:
    from djblets.testing.testcases import ExpectedWarning


class BaseActionTests(TestCase):
    """Unit tests for BaseAction.

    Version Added:
        7.1
    """

    def test_init(self) -> None:
        """Testing BaseAction.__init__"""
        class MyAction(BaseAction):
            action_id = 'test-action'

        with self.assertNoWarnings():
            MyAction()

    def test_init_with_deprecations(self) -> None:
        """Testing BaseAction.__init__ with deprecations"""
        class MyAction(BaseAction):
            action_id = 'test-action'
            template_name = 'my-action.html'
            js_view_class = 'My.Action'

            def get_js_view_data(
                self,
                *,
                context: Context,
            ) -> dict:
                return {}

        warning_list: list[ExpectedWarning] = [
            {
                'cls': RemovedInReviewBoard90Warning,
                'message': (
                    'MyAction.template_name is deprecated and support will '
                    'be removed in Review Board 9. Please move any custom '
                    'rendering to a reviewboard.actions.renderers.'
                    'BaseActionRenderer subclass instead.'
                ),
            },
            {
                'cls': RemovedInReviewBoard90Warning,
                'message': (
                    'MyAction.js_view_class is deprecated and support will '
                    'be removed in Review Board 9. Please move any custom '
                    'rendering to a reviewboard.actions.renderers.'
                    'BaseActionRenderer subclass instead.'
                ),
            },
            {
                'cls': RemovedInReviewBoard90Warning,
                'message': (
                    'MyAction.get_js_view_data is deprecated and support will '
                    'be removed in Review Board 9. Please move any custom '
                    'rendering to a reviewboard.actions.renderers.'
                    'BaseActionRenderer subclass instead.'
                ),
            },
        ]

        with self.assertWarnings(warning_list):
            MyAction()

    def test_render_with_default_renderer(self) -> None:
        """Testing BaseAction.render with default renderer"""
        class MyAction(BaseAction):
            action_id = 'test-action'
            label = 'My Label'

        request = self.create_http_request()
        context = Context({
            'request': request,
        })

        html = MyAction().render(request=request,
                                 context=context)

        self.assertIsInstance(html, SafeString)
        self.assertHTMLEqual(
            html,
            """
            <li class="rb-c-actions__action" role="presentation">
             <a href="#" id="action-test-action" role="button">
              My Label
             </a>
            </li>
            """)

    def test_render_with_custom_default_renderer(self) -> None:
        """Testing BaseAction.render with custom default_renderer_cls"""
        class MyAction(BaseAction):
            action_id = 'test-action'
            default_renderer_cls = ButtonActionRenderer
            label = 'My Label'

        request = self.create_http_request()
        context = Context({
            'request': request,
        })

        html = MyAction().render(request=request,
                                 context=context)

        self.assertIsInstance(html, SafeString)
        self.assertHTMLEqual(
            html,
            """
            <li class="rb-c-actions__action" role="presentation">
             <button aria-label="My Label"
                     class="ink-c-button"
                     id="action-test-action"
                     type="button">
              <label class="ink-c-button__label">My Label</label>
             </button>
            </li>
            """)

    def test_render_with_renderer(self) -> None:
        """Testing BaseAction.render with provided renderer="""
        class MyAction(BaseAction):
            action_id = 'test-action'
            label = 'My Label'

        request = self.create_http_request()
        context = Context({
            'request': request,
        })

        html = MyAction().render(request=request,
                                 context=context,
                                 renderer=ButtonActionRenderer)

        self.assertIsInstance(html, SafeString)
        self.assertHTMLEqual(
            html,
            """
            <li class="rb-c-actions__action" role="presentation">
             <button aria-label="My Label"
                     class="ink-c-button"
                     id="action-test-action"
                     type="button">
              <label class="ink-c-button__label">My Label</label>
             </button>
            </li>
            """)

    def test_render_with_no_renderer(self) -> None:
        """Testing BaseAction.render with no renderer"""
        class MyAction(BaseAction):
            action_id = 'test-action'
            label = 'My Label'
            default_renderer_cls = None

        request = self.create_http_request()
        context = Context({
            'request': request,
        })

        message = (
            "A renderer must be explicitly provided when rendering action "
            "<class 'reviewboard.actions.tests.test_base_action."
            "BaseActionTests.test_render_with_no_renderer.<locals>."
            "MyAction'>."
        )

        with self.assertRaisesMessage(MissingActionRendererError, message):
            MyAction().render(request=request,
                              context=context)

    def test_render_with_should_render_false(self) -> None:
        """Testing BaseAction.render with should_render() returning False"""
        class MyAction(BaseAction):
            action_id = 'test-action'
            label = 'My Label'

            def should_render(
                self,
                *,
                context: Context,
            ) -> bool:
                return False

        request = self.create_http_request()
        context = Context({
            'request': request,
        })

        html = MyAction().render(request=request,
                                 context=context)

        self.assertIsInstance(html, SafeString)
        self.assertEqual(html, '')

    def test_render_js_with_default_renderer(self) -> None:
        """Testing BaseAction.render_js with default renderer"""
        class MyAction(BaseAction):
            action_id = 'test-action'
            label = 'My Label'

        request = self.create_http_request()
        context = Context({
            'request': request,
        })

        js = MyAction().render_js(request=request,
                                  context=context)

        self.assertIsInstance(js, SafeString)
        self.assertHTMLEqual(
            js,
            """
            page.addActionView(new RB.Actions.ActionView({
                el: $('#action-test-action'),
                model: page.addAction(new RB.Actions.Action(
                    {"id": "test-action",
                     "visible": true,
                     "domID": "action-test-action",
                     "label": "My Label",
                     "url": "#"},
                    { parse: true }
                ))
            }));
            """)

    def test_render_js_with_custom_default_renderer(self) -> None:
        """Testing BaseAction.render_js with custom default_renderer_cls"""
        class MyAction(BaseAction):
            action_id = 'test-action'
            default_renderer_cls = ButtonActionRenderer
            label = 'My Label'

        request = self.create_http_request()
        context = Context({
            'request': request,
        })

        js = MyAction().render_js(request=request,
                                  context=context)

        self.assertIsInstance(js, SafeString)
        self.assertHTMLEqual(
            js,
            """
            page.addActionView(new RB.Actions.ActionView({
                el: $('#action-test-action'),
                model: page.addAction(new RB.Actions.Action(
                    {"id": "test-action",
                     "visible": true,
                     "domID": "action-test-action",
                     "label": "My Label",
                     "url": "#"},
                    { parse: true }
                ))
            }));
            """)

    def test_render_js_with_renderer(self) -> None:
        """Testing BaseAction.render_js with provided renderer="""
        class MyAction(BaseAction):
            action_id = 'test-action'
            label = 'My Label'

        request = self.create_http_request()
        context = Context({
            'request': request,
        })

        js = MyAction().render_js(request=request,
                                  context=context,
                                  renderer=SpecialButtonActionRenderer)

        self.assertIsInstance(js, SafeString)
        self.assertHTMLEqual(
            js,
            """
            page.addActionView(new SpecialButtonActionView({
                "label": "~~My Label~~",
                "specialKey": [123, 456],
                el: $('#action-test-action'),
                model: page.addAction(new RB.Actions.Action(
                    {"id": "test-action",
                     "visible": true,
                     "domID": "action-test-action",
                     "label": "My Label",
                     "url": "#"},
                    { parse: true }
                ))
            }));
            """)

    def test_render_js_with_no_renderer(self) -> None:
        """Testing BaseAction.render_js with no renderer"""
        class MyAction(BaseAction):
            action_id = 'test-action'
            label = 'My Label'
            default_renderer_cls = None

        request = self.create_http_request()
        context = Context({
            'request': request,
        })

        message = (
            "A renderer must be explicitly provided when rendering "
            "JavaScript for action <class 'reviewboard.actions.tests."
            "test_base_action.BaseActionTests.test_render_js_with_no_renderer."
            "<locals>.MyAction'>."
        )

        with self.assertRaisesMessage(MissingActionRendererError, message):
            MyAction().render_js(request=request,
                                 context=context)

    def test_render_js_with_should_render_false(self) -> None:
        """Testing BaseAction.render_js with should_render() returning False"""
        class MyAction(BaseAction):
            action_id = 'test-action'
            label = 'My Label'

            def should_render(
                self,
                *,
                context: Context,
            ) -> bool:
                return False

        request = self.create_http_request()
        context = Context({
            'request': request,
        })

        js = MyAction().render_js(request=request,
                                  context=context)

        self.assertIsInstance(js, SafeString)
        self.assertEqual(js, '')
