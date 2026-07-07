"""Unit tests for reviewboard.actions.renderers.BaseActionRenderer.

Version Added:
    8.0
"""

from __future__ import annotations

from django.template import Context
from django.utils.safestring import SafeString

from reviewboard.actions import ActionPlacement, AttachmentPoint
from reviewboard.actions.renderers import BaseActionRenderer
from reviewboard.actions.tests.base import TestAction, TestActionsRegistry
from reviewboard.deprecation import RemovedInReviewBoard10_0Warning
from reviewboard.testing import TestCase


class BaseActionRendererTests(TestCase):
    """Unit tests for BaseActionRenderer.

    Version Added:
        8.0
    """

    def test_get_js_view_data(self) -> None:
        """Testing BaseActionRenderer.get_js_view_data"""
        action = TestAction()
        placement = action.get_placement('review-request')

        renderer = BaseActionRenderer(action=action,
                                      placement=placement)

        self.assertEqual(renderer.get_js_view_data(context=Context()),
                         {})

    def test_get_js_view_data_with_action_override(self) -> None:
        """Testing BaseActionRenderer.get_js_view_data forwards a legacy
        action's get_js_view_data
        """
        class MyAction(TestAction):
            action_id = 'js-data-test'

            def get_js_view_data(self, *, context):
                return {'foo': 'bar'}

        with self.assertWarns(RemovedInReviewBoard10_0Warning):
            action = MyAction()

        placement = action.get_placement('review-request')

        renderer = BaseActionRenderer(action=action, placement=placement)

        self.assertEqual(renderer.get_js_view_data(context=Context()),
                         {'foo': 'bar'})

    def test_get_extra_context(self) -> None:
        """Testing BaseActionRenderer.get_extra_context"""
        action = TestAction()
        placement = action.get_placement('review-request')

        registry = TestActionsRegistry()
        registry.register(action)

        renderer = BaseActionRenderer(action=action,
                                      placement=placement)
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
                'dom_element_id': 'action-review-request-test',
                'has_parent': False,
                'id': 'test',
                'is_toplevel': True,
                'label': 'Test Action 1',
                'placement': placement,
                'url': '#',
                'verbose_label': None,
                'visible': True,
            })

    def test_get_extra_context_with_dom_element_id_override(self) -> None:
        """Testing BaseActionRenderer.get_extra_context with a
        get_dom_element_id override
        """
        class MyAction(TestAction):
            action_id = 'override-test'

            def get_dom_element_id(self) -> str:
                return 'override-id'

        with self.assertWarns(RemovedInReviewBoard10_0Warning):
            action = MyAction()

        placement = action.get_placement('review-request')

        registry = TestActionsRegistry()
        registry.register(action)

        renderer = BaseActionRenderer(action=action, placement=placement)

        extra_context = renderer.get_extra_context(
            request=self.create_http_request(),
            context=Context())

        self.assertEqual(extra_context['dom_element_id'], 'override-id')

    def test_get_extra_context_with_placement_dom_element_id(self) -> None:
        """Testing BaseActionRenderer.get_extra_context with
        placement.dom_element_id
        """
        class MyAction(TestAction):
            action_id = 'placement-test'
            placements = [
                ActionPlacement(attachment=AttachmentPoint.REVIEW_REQUEST,
                                dom_element_id='placement-id'),
            ]

        action = MyAction()
        placement = action.get_placement('review-request')

        registry = TestActionsRegistry()
        registry.register(action)

        renderer = BaseActionRenderer(action=action, placement=placement)

        extra_context = renderer.get_extra_context(
            request=self.create_http_request(),
            context=Context())

        self.assertEqual(extra_context['dom_element_id'],
                         'placement-id')

    def test_get_extra_context_with_multiple_placements(self) -> None:
        """Testing BaseActionRenderer.get_extra_context with multiple
        placements produces unique DOM element IDs
        """
        class MyAction(TestAction):
            action_id = 'multi-placement-test'
            placements = [
                ActionPlacement(attachment=AttachmentPoint.HEADER),
                ActionPlacement(attachment=AttachmentPoint.REVIEW_REQUEST),
            ]

        action = MyAction()

        registry = TestActionsRegistry()
        registry.register(action)

        request = self.create_http_request()
        context = Context()

        header_context = BaseActionRenderer(
            action=action,
            placement=action.get_placement('header'),
        ).get_extra_context(request=request, context=context)

        review_request_context = BaseActionRenderer(
            action=action,
            placement=action.get_placement('review-request'),
        ).get_extra_context(request=request, context=context)

        # Each placement gets its own attachment-qualified ID, so the same
        # action placed in multiple attachment points never produces duplicate
        # DOM element IDs.
        self.assertEqual(header_context['dom_element_id'],
                         'action-header-multi-placement-test')
        self.assertEqual(review_request_context['dom_element_id'],
                         'action-review-request-multi-placement-test')

    def test_render(self) -> None:
        """Testing BaseActionRenderer.render"""
        action = TestAction()
        placement = action.get_placement('review-request')

        registry = TestActionsRegistry()
        registry.register(action)

        renderer = BaseActionRenderer(action=action,
                                      placement=placement)
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
        with self.assertWarns(RemovedInReviewBoard10_0Warning):
            action = MyAction()

        placement = action.get_placement('review-request')

        registry = TestActionsRegistry()
        registry.register(action)

        renderer = BaseActionRenderer(action=action,
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
        """Testing BaseActionRenderer.render_js"""
        action = TestAction()
        placement = action.get_placement('review-request')

        registry = TestActionsRegistry()
        registry.register(action)

        renderer = BaseActionRenderer(action=action,
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
                el: $('#action-review-request-test'),
                model: page.getAction("test"),
            }));
            """)
