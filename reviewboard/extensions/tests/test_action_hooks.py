"""Unit tests for reviewboard.extensions.hooks.ActionHook and subclasses."""

from typing import Any, Dict, Type

from django.template import Context, Template

from reviewboard.actions import BaseAction, BaseMenuAction, actions_registry
from reviewboard.deprecation import RemovedInReviewBoard70Warning
from reviewboard.extensions.hooks import (ActionHook,
                                          DiffViewerActionHook,
                                          HeaderActionHook,
                                          HeaderDropdownActionHook,
                                          HideActionHook,
                                          ReviewRequestActionHook,
                                          ReviewRequestDropdownActionHook)
from reviewboard.extensions.hooks.actions import BaseReviewRequestActionHook
from reviewboard.extensions.tests.testcases import BaseExtensionHookTestCase
from reviewboard.reviews.actions import (BaseReviewRequestAction,
                                         BaseReviewRequestMenuAction)


class ActionHookTests(BaseExtensionHookTestCase):
    """Tests for modern ActionHook usage."""

    fixtures = ['test_users']

    class _TestAction(BaseAction):
        action_id = 'test'
        label = 'Test Action'

    class _TestMenuAction(BaseMenuAction):
        action_id = 'test-menu'
        label = 'Test Menu'

    class _TestMenuInstance(BaseAction):
        action_id = 'test-menu-item'
        label = 'Test Menu Item'
        parent_id = 'test-menu'

    def tearDown(self) -> None:
        """Tear down the test case."""
        super().tearDown()
        actions_registry.reset()

    def test_action_hook(self) -> None:
        """Testing ActionHook registration"""
        test_action = self._TestAction()
        test_menu_action = self._TestMenuAction()
        test_menu_instance = self._TestMenuInstance()

        hook = ActionHook(extension=self.extension, actions=[
            test_action,
            test_menu_action,
            test_menu_instance,
        ])

        try:
            self.assertEqual(
                actions_registry.get('action_id', 'test'),
                test_action)
            self.assertEqual(
                actions_registry.get('action_id', 'test-menu'),
                test_menu_action)
            self.assertEqual(
                actions_registry.get('action_id', 'test-menu-item'),
                test_menu_instance)

            self.assertEqual(test_menu_instance.parent_action,
                             test_menu_action)
            self.assertEqual(test_menu_action.child_actions,
                             [test_menu_instance])
        finally:
            hook.disable_hook()

        self.assertIsNone(actions_registry.get('action_id', 'test'))
        self.assertIsNone(actions_registry.get('action_id', 'test-menu'))
        self.assertIsNone(actions_registry.get('action_id', 'test-menu-item'))
        self.assertIsNone(test_menu_instance.parent_action)
        self.assertEqual(test_menu_action.child_actions, [])


class LegacyActionHookTests(BaseExtensionHookTestCase):
    """Tests for the legacy action hooks in reviewboard.extensions.hooks."""

    fixtures = ['test_users']

    class _TestAction(BaseReviewRequestAction):
        action_id = 'test-action'
        label = 'Test Action'

    class _TestMenuAction(BaseReviewRequestMenuAction):
        action_id = 'test-menu-instance'
        label = 'Menu Instance'

    def tearDown(self) -> None:
        """Tear down the test case."""
        super().tearDown()

        actions_registry.reset()

    def test_review_request_action_hook(self) -> None:
        """Testing ReviewRequestActionHook renders on a review request page but
        not on a file attachment or a diff viewer page
        """
        deprecation_message = (
            'ReviewRequestActionHook is deprecated and will be removed in '
            'Review Board 7.0. Your extension '
            '"reviewboard.extensions.tests.testcases.DummyExtension" '
            'will need to be updated to derive actions from '
            'reviewboard.actions.BaseAction and use ActionHook.'
        )

        with self.assertWarns(RemovedInReviewBoard70Warning,
                              deprecation_message):
            self._test_base_review_request_action_hook(
                'review-request-detail', ReviewRequestActionHook, True)

        with self.assertWarns(RemovedInReviewBoard70Warning,
                              deprecation_message):
            self._test_base_review_request_action_hook(
                'file-attachment', ReviewRequestActionHook, False)

        with self.assertWarns(RemovedInReviewBoard70Warning,
                              deprecation_message):
            self._test_base_review_request_action_hook(
                'view-diff', ReviewRequestActionHook, False)

    def test_diffviewer_action_hook(self) -> None:
        """Testing DiffViewerActionHook renders on a diff viewer page but not
        on a review request page or a file attachment page
        """
        deprecation_message = (
            'DiffViewerActionHook is deprecated and will be removed in '
            'Review Board 7.0. Your extension '
            '"reviewboard.extensions.tests.testcases.DummyExtension" '
            'will need to be updated to derive actions from '
            'reviewboard.actions.BaseAction and use ActionHook.'
        )

        with self.assertWarns(RemovedInReviewBoard70Warning,
                              deprecation_message):
            self._test_base_review_request_action_hook(
                'review-request-detail', DiffViewerActionHook, False)

        with self.assertWarns(RemovedInReviewBoard70Warning,
                              deprecation_message):
            self._test_base_review_request_action_hook(
                'file-attachment', DiffViewerActionHook, False)

        with self.assertWarns(RemovedInReviewBoard70Warning,
                              deprecation_message):
            self._test_base_review_request_action_hook(
                'view-diff', DiffViewerActionHook, True)

    def test_review_request_dropdown_action_hook(self) -> None:
        """Testing ReviewRequestDropdownActionHook renders on a review request
        page but not on a file attachment or a diff viewer page
        """
        deprecation_message = (
            'ReviewRequestDropdownActionHook is deprecated and will be '
            'removed in Review Board 7.0. Your extension '
            '"reviewboard.extensions.tests.testcases.DummyExtension" '
            'will need to be updated to derive actions from '
            'reviewboard.actions.BaseAction and use ActionHook.'
        )

        with self.assertWarns(RemovedInReviewBoard70Warning,
                              deprecation_message):
            self._test_review_request_dropdown_action_hook(
                'review-request-detail', ReviewRequestDropdownActionHook)

        with self.assertWarns(RemovedInReviewBoard70Warning,
                              deprecation_message):
            self._test_review_request_dropdown_action_hook(
                'file-attachment', ReviewRequestDropdownActionHook)

        with self.assertWarns(RemovedInReviewBoard70Warning,
                              deprecation_message):
            self._test_review_request_dropdown_action_hook(
                'view-diff', ReviewRequestDropdownActionHook)

    def test_action_hook_init_raises_key_error(self) -> None:
        """Testing ActionHook.__init__ with raised KeyError"""
        missing_url_action = {
            'id': 'missing-url-action',
            'label': 'This action dict is missing a mandatory URL key.',
        }
        missing_key = 'url'
        error_message = ('Action dictionaries require a %s key'
                         % repr(missing_key))
        action_hook_classes = [
            BaseReviewRequestActionHook,
            ReviewRequestActionHook,
            DiffViewerActionHook,
        ]

        for hook_cls in action_hook_classes:
            with self.assertRaisesMessage(KeyError, error_message):
                hook_cls(extension=self.extension, actions=[
                    missing_url_action,
                ])

    def test_action_hook_init_raises_value_error(self) -> None:
        """Testing ActionHook.__init__ with raised ValueError"""
        unsupported_type_action = [{
            'id': 'unsupported-type-action',
            'label': 'This action is a list, which is an unsupported type.',
            'url': '#',
        }]
        error_message = 'Action definitions must be dictionaries.'
        action_hook_classes = [
            BaseReviewRequestActionHook,
            ReviewRequestActionHook,
            DiffViewerActionHook,
            ReviewRequestDropdownActionHook,
        ]

        for hook_cls in action_hook_classes:
            with self.assertRaisesMessage(ValueError, error_message):
                hook_cls(extension=self.extension, actions=[
                    unsupported_type_action,
                ])

    def test_dropdown_action_hook_init_raises_key_error(self) -> None:
        """Testing ReviewRequestDropdownActionHook.__init__ with raiseed
        KeyError
        """
        missing_items_menu_action = {
            'id': 'missing-items-menu-action',
            'label': 'This menu action dict is missing a mandatory items key.',
        }

        with self.assertRaisesMessage(KeyError, 'items'):
            ReviewRequestDropdownActionHook(extension=self.extension, actions=[
                missing_items_menu_action,
            ])

    def test_header_hooks(self) -> None:
        """Testing HeaderActionHook"""
        action = {
            'id': 'test',
            'image': 'test-image',
            'image_height': 42,
            'image_width': 42,
            'label': 'Test Action',
            'url': 'foo-url',
        }

        deprecation_message = (
            'HeaderActionHook is deprecated and will be removed in Review '
            'Board 7.0. Your extension '
            '"reviewboard.extensions.tests.testcases.DummyExtension" '
            'will need to be updated to derive actions from '
            'reviewboard.actions.BaseAction and use ActionHook.'
        )

        with self.assertWarns(RemovedInReviewBoard70Warning,
                              deprecation_message):
            hook = HeaderActionHook(extension=self.extension, actions=[action])

        context = self._get_context()
        entries = hook.get_actions(context)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].action_id, 'test')

        t = Template(
            '{% load actions %}'
            '{% actions_html "header" %}')

        content = t.render(context).strip()

        self.assertIn('id="%s-action"' % action['id'], content)

    def test_header_dropdown_action_hook(self) -> None:
        """Testing HeaderDropdownActionHook"""
        action = {
            'id': 'test-menu',
            'label': 'Test Menu',
            'items': [
                {
                    'id': 'test-action',
                    'image': 'test-image',
                    'image_height': 42,
                    'image_width': 42,
                    'label': 'Test Action',
                    'url': 'foo-url',
                }
            ]
        }

        deprecation_message = (
            'HeaderDropdownActionHook is deprecated and will be removed in '
            'Review Board 7.0. Your extension '
            '"reviewboard.extensions.tests.testcases.DummyExtension" '
            'will need to be updated to derive actions from '
            'reviewboard.actions.BaseAction and use ActionHook.'
        )

        with self.assertWarns(RemovedInReviewBoard70Warning,
                              deprecation_message):
            hook = HeaderDropdownActionHook(extension=self.extension,
                                            actions=[action])

        context = self._get_context()
        entries = hook.get_actions(context)
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0].action_id, 'test-menu')
        self.assertEqual(entries[1].action_id, 'test-action')

        t = Template(
            '{% load actions %}'
            '{% actions_html "header" %}')

        content = t.render(context).strip()

        self.assertIn(('id="action-%s"' % action['id']), content)
        self.assertInHTML(
            ('<a href="#" role="presentation" aria-label="%s">%s '
             '<span class="rb-icon rb-icon-dropdown-arrow"></span></a>'
             % (action['label'], action['label'])),
            content)

    def _test_base_review_request_action_hook(
        self,
        url_name: str,
        hook_cls: Type[ActionHook],
        should_render: bool,
    ) -> None:
        """Test if the action hook renders or not at the given URL.

        Args:
            url_name (str):
                The name of the URL where each action is to be rendered.

            hook_cls (class):
                The class of the action hook to be tested.

            should_render (bool):
                The expected rendering behaviour.
        """
        hook = hook_cls(extension=self.extension, actions=[
            {
                'id': 'with-id',
                'label': 'Yes ID',
                'url': 'with-id-url',
            },
            {
                'label': 'No ID',
                'url': 'without-id-url',
            },
        ])

        try:
            context = self._get_context(url_name=url_name)

            entries = hook.get_actions(context)
            self.assertEqual(len(entries), 2)
            self.assertEqual(entries[0].action_id, 'with-id')
            self.assertEqual(entries[1].action_id, 'no-id')

            template = Template(
                '{% load actions %}'
                '{% actions_html "review-request" %}'
            )
            content = template.render(context)
            self.assertEqual(should_render, 'href="with-id-url"' in content)
            self.assertEqual(should_render, 'Yes ID' in content)
            self.assertEqual(should_render,
                             'id="no-id-action"' in content)
        finally:
            hook.disable_hook()

        content = template.render(context)
        self.assertNotIn('href="with-id-url"', content)
        self.assertNotIn('Yes ID', content)
        self.assertNotIn('id="action-no-id-dict"', content)

    def _test_review_request_dropdown_action_hook(
        self,
        url_name: str,
        hook_cls: Type[ActionHook],
    ) -> None:
        """Test if the dropdown action hook renders or not at the given URL.

        Args:
            url_name (str):
                The name of the URL where each action is to be rendered.

            hook_cls (class):
                The class of the dropdown action hook to be tested.
        """
        hook = hook_cls(extension=self.extension, actions=[
            {
                'id': 'test-menu-dict',
                'label': 'Menu Dict',
                'items': [
                    {
                        'id': 'with-id',
                        'label': 'Yes ID',
                        'url': 'with-id-url',
                    },
                    {
                        'label': 'No ID',
                        'url': 'without-id-url',
                    },
                ]
            },
        ])

        try:
            context = self._get_context(url_name=url_name)
            entries = hook.get_actions(context)
            self.assertEqual(len(entries), 3)
            self.assertEqual(entries[0].action_id, 'test-menu-dict')
            self.assertEqual(entries[1].action_id, 'with-id')
            self.assertEqual(entries[2].action_id, 'no-id')

            dropdown_icon_html = \
                '<span class="rb-icon rb-icon-dropdown-arrow"></span>'

            template = Template(
                '{% load actions %}'
                '{% actions_html "review-request" %}'
            )
            content = template.render(context)

            self.assertIn('Yes ID', content)
            self.assertInHTML(
                ('<a href="#" role="presentation" aria-label="Menu Dict">'
                 'Menu Dict %s</a>'
                 % dropdown_icon_html),
                content)

            self.assertIn('id="action-test-menu-dict"', content)
            self.assertIn('href="with-id-url"', content)
            self.assertIn('id="no-id-action"', content)
        finally:
            hook.disable_hook()

        content = template.render(context)
        self.assertNotIn('Test Action', content)
        self.assertNotIn('Menu Instance', content)
        self.assertNotIn('id="test-menu-dict-action"', content)
        self.assertNotIn('href="with-id-url"', content)
        self.assertNotIn('id="no-id-dict-action"', content)

    def _build_action_template(
        self,
        action: Dict[str, Any],
    ) -> str:
        """Create HTML rendering of an action.

        Args:
            action (dict):
                Data about the action for rendering.

        Returns:
            str:
            HTML for the action rendering.
        """
        return ('<li><a id="%(id)s" href="%(url)s">'
                '<img src="%(image)s" width="%(image_width)s" '
                'height="%(image_height)s" border="0" alt="" />'
                '%(label)s</a></li>' % action)

    def _get_context(
        self,
        url_name: str = 'review-request-detail',
    ) -> Context:
        """Create a template rendering context.

        Args:
            url_name (str):
                The URL name to set on the request.

        Returns:
            django.template.Context:
            A rendering context to use for tests.
        """
        request = self.create_http_request(url_name=url_name)
        review_request = self.create_review_request(public=True)

        return Context({
            'request': request,
            'review_request': review_request,
            'perms': {
                'reviews': {
                    'can_change_status': True,
                    'can_edit_reviewrequest': True,
                    'delete_reviewrequest': True,
                },
            },
        })


class HideActionHookTests(BaseExtensionHookTestCase):
    """Tests for HideActionHook."""

    def test_hide_action_hook(self) -> None:
        """Testing HideActionHook"""
        HideActionHook(extension=self.extension,
                       action_ids=['support-menu'])

        action = actions_registry.get('action_id', 'support-menu')

        request = self.create_http_request()
        context = Context({
            'request': request,
        })

        self.assertFalse(action.should_render(context=context))
