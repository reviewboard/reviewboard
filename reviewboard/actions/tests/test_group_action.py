"""Unit tests for reviewboard.actions.base.BaseGroupAction.

Version Added:
    7.1
"""

from __future__ import annotations

from django.template import Context
from django.utils.safestring import SafeString

from reviewboard.actions.renderers import DefaultActionGroupRenderer
from reviewboard.actions.tests.base import (
    TestActionsRegistry,
    TestGroupAction,
    TestGroupItemAction1,
    TestGroupItemAction2,
    TestGroupItemAction3,
)
from reviewboard.testing import TestCase


class BaseGroupActionTests(TestCase):
    """Unit tests for BaseGroupAction.

    Version Added:
        7.1
    """

    ######################
    # Instance variables #
    ######################

    #: A BaseGroupAction instance for testing.
    group_action: TestGroupAction

    #: Item 1's action, for testing.
    item1_action: TestGroupItemAction1

    #: Item 2's action, for testing.
    item2_action: TestGroupItemAction2

    #: Item 3's action, for testing.
    item3_action: TestGroupItemAction3

    #: An empty actions registry for testing.
    registry: TestActionsRegistry

    def setUp(self) -> None:
        """Set up state for a test."""
        super().setUp()

        group_action = TestGroupAction()
        item1_action = TestGroupItemAction1()
        item2_action = TestGroupItemAction2()
        item3_action = TestGroupItemAction3()

        registry = TestActionsRegistry()
        registry.register(group_action)
        registry.register(item1_action)
        registry.register(item2_action)
        registry.register(item3_action)

        self.registry = registry
        self.group_action = group_action
        self.item1_action = item1_action
        self.item2_action = item2_action
        self.item3_action = item3_action

    def tearDown(self) -> None:
        """Tear down state for a test."""

        del self.group_action
        del self.item1_action
        del self.item2_action
        del self.item3_action
        del self.registry

        super().tearDown()

    def test_get_extra_context(self) -> None:
        """Testing BaseGroupAction.get_extra_context"""
        request = self.create_http_request()
        context = Context({
            'request': request,
        })

        self.assertEqual(
            self.group_action.get_extra_context(request=request,
                                                context=context),
            {
                'id': 'group-action',
                'label': 'Test Group',
                'url': '#',
                'verbose_label': None,
                'visible': True,
            })

    def test_js_model_data(self) -> None:
        """Testing BaseGroupAction.js_model_data"""
        request = self.create_http_request()
        context = Context({
            'request': request,
        })

        self.assertEqual(
            self.group_action.get_js_model_data(context=context),
            {
                'id': 'group-action',
                'children': {
                    'review-request': [
                        'group-item-2-action',
                        'group-item-1-action',
                        'group-item-3-action',
                    ],
                },
                'label': 'Test Group',
                'url': '#',
                'visible': True,
            })

    def test_render_with_default_renderer(self) -> None:
        """Testing BaseGroupAction.render with default renderer"""
        request = self.create_http_request()
        context = Context({
            'request': request,
        })

        html = self.group_action.render(
            request=request,
            context=context,
            fallback_renderer=DefaultActionGroupRenderer,
        )

        self.assertIsInstance(html, SafeString)
        self.assertHTMLEqual(
            html,
            """
            <li class="rb-c-actions__action"
                id="action-review-request-group-action"
                role="group">
             <a id="action-review-request-group-item-1-action"
                role="button"
                hidden
                style="display: none;"
                href="#">
              Group Item 1
             </a>
             <a id="action-review-request-group-item-2-action"
                role="button"
                hidden
                style="display: none;"
                href="#">
              Group Item 2
             </a>
             <a id="action-review-request-group-item-3-action"
                role="button"
                hidden
                style="display: none;"
                href="#">
              Group Item 3
             </a>
            </li>
            """)

    def test_render_js_with_default_renderer(self) -> None:
        """Testing BaseGroupAction.render_js with default renderer"""
        request = self.create_http_request()
        context = Context({
            'request': request,
        })

        js = self.group_action.render_js(
            request=request,
            context=context,
            fallback_renderer=DefaultActionGroupRenderer,
        )

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
