"""Unit tests for reviewboard.actions.base.ActionAttachmentPoint.

Version Added:
    7.1
"""

from __future__ import annotations

from django.template import Context

from reviewboard.actions.base import ActionAttachmentPoint, BaseAction
from reviewboard.actions.renderers import ButtonActionRenderer
from reviewboard.actions.tests.base import (
    SpecialButtonActionRenderer,
    TestAction,
    TestActionsRegistry,
    TestGroupAction,
    TestGroupItemAction1,
    TestMenuAction,
    TestMenuItemAction,
)
from reviewboard.testing import TestCase


class _MyGroupItemAction1(TestGroupItemAction1):
    attachment = 'test-point'
    label = 'My Group'
    parent_id = TestGroupAction.action_id


class _MyMenuItemAction1(TestMenuItemAction):
    attachment = 'test-point'
    parent_id = TestMenuAction.action_id


class _MyRegisteredAction(BaseAction):
    action_id = 'new-action'
    attachment = 'test-point'
    label = 'New Action'


class _MyActionAttachmentPoint(ActionAttachmentPoint):
    actions = [
        TestAction.action_id,
        TestGroupAction.action_id,
        TestMenuAction.action_id,
    ]
    attachment_point_id = 'test-point'
    default_action_renderer_cls = SpecialButtonActionRenderer


class ActionAttachmentPointTests(TestCase):
    """Unit tests for ActionAttachmentPoint.

    Version Added:
        7.1
    """

    #: The actions registry used to test against.
    actions_registry: TestActionsRegistry

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()

        actions_registry = TestActionsRegistry()
        actions_registry.register(_MyRegisteredAction())
        actions_registry.register(TestAction())
        actions_registry.register(TestGroupAction())
        actions_registry.register(_MyGroupItemAction1())
        actions_registry.register(TestMenuAction())
        actions_registry.register(_MyMenuItemAction1())
        cls.actions_registry = actions_registry

    @classmethod
    def tearDownClass(cls) -> None:
        cls.actions_registry = None  # type: ignore

        super().tearDownClass()

    def test_init_with_args(self) -> None:
        """Testing ActionAttachmentPoint.__init__ with arguments"""
        attachment_point = ActionAttachmentPoint(
            attachment_point_id='test-point',
            actions=[
                TestAction.action_id,
                TestGroupAction.action_id,
            ],
            default_action_renderer_cls=SpecialButtonActionRenderer,
        )

        self.assertEqual(attachment_point.attachment_point_id, 'test-point')
        self.assertEqual(attachment_point.actions, [
            TestAction.action_id,
            TestGroupAction.action_id,
        ])
        self.assertIs(attachment_point.default_action_renderer_cls,
                      SpecialButtonActionRenderer)

    def test_init_with_class_attrs(self) -> None:
        """Testing ActionAttachmentPoint.__init__ with class attributes"""
        attachment_point = _MyActionAttachmentPoint()

        self.assertEqual(attachment_point.attachment_point_id, 'test-point')
        self.assertEqual(attachment_point.actions, [
            TestAction.action_id,
            TestGroupAction.action_id,
            TestMenuAction.action_id,
        ])
        self.assertIs(attachment_point.default_action_renderer_cls,
                      SpecialButtonActionRenderer)

    def test_init_with_args_and_class_attrs(self) -> None:
        """Testing ActionAttachmentPoint.__init__ with arguments and class
        attributes
        """
        class MyActionAttachmentPoint(ActionAttachmentPoint):
            attachment_point_id = 'old-test-point'
            actions = [
                TestGroupAction.action_id,
            ]
            default_action_renderer_cls = ButtonActionRenderer

        attachment_point = MyActionAttachmentPoint(
            attachment_point_id='test-point',
            actions=[
                TestAction.action_id,
                TestGroupAction.action_id,
            ],
            default_action_renderer_cls=SpecialButtonActionRenderer,
        )

        self.assertEqual(attachment_point.attachment_point_id, 'test-point')
        self.assertEqual(attachment_point.actions, [
            TestAction.action_id,
            TestGroupAction.action_id,
        ])
        self.assertIs(attachment_point.default_action_renderer_cls,
                      SpecialButtonActionRenderer)

    def test_init_with_no_id(self) -> None:
        """Testing ActionAttachmentPoint.__init__ with no ID"""
        message = (
            'attachment_point_id must be provided as an argument or a class '
            'attribute.'
        )

        with self.assertRaisesMessage(AttributeError, message):
            ActionAttachmentPoint()

    def test_iter_actions(self) -> None:
        """Testing ActionAttachmentPoint.iter_actions"""
        actions_registry = self.actions_registry
        attachment_point = _MyActionAttachmentPoint(
            actions_registry=actions_registry,
        )

        self.assertEqual(
            list(attachment_point.iter_actions()),
            [
                actions_registry.get_action(TestAction.action_id),
                actions_registry.get_action(TestGroupAction.action_id),
                actions_registry.get_action(TestMenuAction.action_id),
                actions_registry.get_action(_MyRegisteredAction.action_id),
            ])

    def test_iter_actions_with_include_children(self) -> None:
        """Testing ActionAttachmentPoint.iter_actions with
        include_children=True
        """
        actions_registry = self.actions_registry
        attachment_point = _MyActionAttachmentPoint(
            actions_registry=actions_registry,
        )

        self.assertEqual(
            list(attachment_point.iter_actions(include_children=True)),
            [
                actions_registry.get_action(TestAction.action_id),
                actions_registry.get_action(TestGroupAction.action_id),
                actions_registry.get_action(TestMenuAction.action_id),
                actions_registry.get_action(_MyRegisteredAction.action_id),
                actions_registry.get_action(_MyGroupItemAction1.action_id),
                actions_registry.get_action(_MyMenuItemAction1.action_id),
            ])

    def test_render(self) -> None:
        """Testing ActionAttachmentPoint.render"""
        actions_registry = self.actions_registry
        attachment_point = _MyActionAttachmentPoint(
            actions_registry=actions_registry,
        )

        request = self.create_http_request()
        context = Context({
            'request': request,
        })

        self.assertHTMLEqual(
            attachment_point.render(request=request,
                                    context=context),
            """
            <li class="rb-c-actions__action"
                role="presentation">
             <button aria-label="Test Action 1"
                     class="ink-c-button"
                     id="action-review-request-test"
                     type="button">
              <label class="ink-c-button__label">
               Test Action 1
              </label>
             </button>
            </li>

            <li class="rb-c-actions__action"
                role="group"
                id="action-review-request-group-action">
             <a id="action-test-point-group-item-1-action"
                hidden
                style="display: none;"
                href="#"
                role="button">
               My Group
             </a>
            </li>

            <li class="rb-c-actions__action"
                role="menuitem"
                id="action-review-request-menu-action">
             <a href="#"
                role="presentation"
                aria-label="Test Menu">
              <label class="rb-c-actions__action-label">
               Test Menu
              </label>
              <span class="ink-i-dropdown"/>
             </a>

             <a id="action-test-point-menu-item-action"
                role="button"
                href="#"
                hidden
                style="display: none;">
              <span class="my-icon"/>
              Menu Item Action 1
             </a>
            </li>

            <li class="rb-c-actions__action"
                role="presentation">
             <button aria-label="New Action"
                     class="ink-c-button"
                     id="action-test-point-new-action"
                     type="button">
              <label class="ink-c-button__label">
               New Action
              </label>
             </button>
            </li>
            """)

    def test_render_js(self) -> None:
        """Testing ActionAttachmentPoint.render_js"""
        actions_registry = self.actions_registry
        attachment_point = _MyActionAttachmentPoint(
            actions_registry=actions_registry,
        )

        request = self.create_http_request()
        context = Context({
            'request': request,
        })

        self.assertHTMLEqual(
            attachment_point.render_js(request=request,
                                       context=context),
            """
            page.addActionView(new SpecialButtonActionView({
                "attachmentPointID": "review-request",
                "label": "~~Test Action 1~~",
                "specialKey": [123, 456],
                el: $('#action-review-request-test'),
                model: page.getAction("test"),
            }));

            page.addActionView(new RB.Actions.ActionView({
                "attachmentPointID": "review-request",
                el: $('#action-review-request-group-action'),
                model: page.getAction("group-action"),
            }));

            page.addActionView(new RB.Actions.MenuActionView({
                "attachmentPointID": "review-request",
                el: $('#action-review-request-menu-action'),
                model: page.getAction("menu-action"),
            }));

            page.addActionView(new SpecialButtonActionView({
                "attachmentPointID": "test-point",
                "label": "~~New Action~~",
                "specialKey": [123, 456],
                el: $('#action-test-point-new-action'),
                model: page.getAction("new-action"),
            }));

            page.addActionView(new SpecialButtonActionView({
                "attachmentPointID": "test-point",
                "label": "~~My Group~~",
                "specialKey": [123, 456],
                el: $('#action-test-point-group-item-1-action'),
                model: page.getAction("group-item-1-action"),
            }));

            page.addActionView(new SpecialButtonActionView({
                "attachmentPointID": "test-point",
                "label": "~~Menu Item Action 1~~",
                "specialKey": [123, 456],
                el: $('#action-test-point-menu-item-action'),
                model: page.getAction("menu-item-action"),
            }));
            """)
