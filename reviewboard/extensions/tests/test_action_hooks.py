"""Unit tests for reviewboard.extensions.hooks.ActionHook and subclasses."""

from django.template import Context, Template
from djblets.features.testing import override_feature_check
from mock import Mock

from reviewboard.extensions.hooks import (BaseReviewRequestActionHook,
                                          DiffViewerActionHook,
                                          HeaderActionHook,
                                          HeaderDropdownActionHook,
                                          ReviewRequestActionHook,
                                          ReviewRequestDropdownActionHook)
from reviewboard.extensions.tests.testcases import BaseExtensionHookTestCase
from reviewboard.reviews.actions import (BaseReviewRequestAction,
                                         BaseReviewRequestMenuAction,
                                         clear_all_actions)
from reviewboard.reviews.features import ClassBasedActionsFeature
from reviewboard.reviews.models import ReviewRequest


class ActionHookTests(BaseExtensionHookTestCase):
    """Tests the action hooks in reviewboard.extensions.hooks."""

    class _TestAction(BaseReviewRequestAction):
        action_id = 'test-action'
        label = 'Test Action'

    class _TestMenuAction(BaseReviewRequestMenuAction):
        action_id = 'test-menu-instance-action'
        label = 'Menu Instance'

    def tearDown(self):
        super(ActionHookTests, self).tearDown()

        clear_all_actions()

    def test_review_request_action_hook(self):
        """Testing ReviewRequestActionHook renders on a review request page but
        not on a file attachment or a diff viewer page
        """
        with override_feature_check(ClassBasedActionsFeature.feature_id,
                                    enabled=True):
            self._test_base_review_request_action_hook(
                'review-request-detail', ReviewRequestActionHook, True)
            self._test_base_review_request_action_hook(
                'file-attachment', ReviewRequestActionHook, False)
            self._test_base_review_request_action_hook(
                'view-diff', ReviewRequestActionHook, False)

    def test_diffviewer_action_hook(self):
        """Testing DiffViewerActionHook renders on a diff viewer page but not
        on a review request page or a file attachment page
        """
        with override_feature_check(ClassBasedActionsFeature.feature_id,
                                    enabled=True):
            self._test_base_review_request_action_hook(
                'review-request-detail', DiffViewerActionHook, False)
            self._test_base_review_request_action_hook(
                'file-attachment', DiffViewerActionHook, False)
            self._test_base_review_request_action_hook(
                'view-diff', DiffViewerActionHook, True)

    def test_review_request_dropdown_action_hook(self):
        """Testing ReviewRequestDropdownActionHook renders on a review request
        page but not on a file attachment or a diff viewer page
        """
        with override_feature_check(ClassBasedActionsFeature.feature_id,
                                    enabled=True):
            self._test_review_request_dropdown_action_hook(
                'review-request-detail', ReviewRequestDropdownActionHook, True)
            self._test_review_request_dropdown_action_hook(
                'file-attachment', ReviewRequestDropdownActionHook, False)
            self._test_review_request_dropdown_action_hook(
                'view-diff', ReviewRequestDropdownActionHook, False)

    def test_action_hook_init_raises_key_error(self):
        """Testing ActionHook.__init__ with raised KeyError"""
        missing_url_action = {
            'id': 'missing-url-action',
            'label': 'This action dict is missing a mandatory URL key.',
        }
        missing_key = 'url'
        error_message = ('ActionHook-style dicts require a %s key'
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

    def test_action_hook_init_raises_value_error(self):
        """Testing ActionHook.__init__ with raised ValueError"""
        unsupported_type_action = [{
            'id': 'unsupported-type-action',
            'label': 'This action is a list, which is an unsupported type.',
            'url': '#',
        }]
        error_message = ('Only BaseReviewRequestAction and dict instances are '
                         'supported')
        action_hook_classes = [
            BaseReviewRequestActionHook,
            ReviewRequestActionHook,
            DiffViewerActionHook,
            ReviewRequestDropdownActionHook,
        ]

        with override_feature_check(ClassBasedActionsFeature.feature_id,
                                    enabled=True):
            for hook_cls in action_hook_classes:
                with self.assertRaisesMessage(ValueError, error_message):
                    hook_cls(extension=self.extension, actions=[
                        unsupported_type_action,
                    ])

    def test_dropdown_action_hook_init_raises_key_error(self):
        """Testing ReviewRequestDropdownActionHook.__init__ with raiseed
        KeyError
        """
        missing_items_menu_action = {
            'id': 'missing-items-menu-action',
            'label': 'This menu action dict is missing a mandatory items key.',
        }
        missing_key = 'items'
        error_message = ('ReviewRequestDropdownActionHook-style dicts require '
                         'a %s key' % repr(missing_key))

        with self.assertRaisesMessage(KeyError, error_message):
            ReviewRequestDropdownActionHook(extension=self.extension, actions=[
                missing_items_menu_action,
            ])

    def test_header_hooks(self):
        """Testing HeaderActionHook"""
        self._test_action_hook('header_action_hooks', HeaderActionHook)

    def test_header_dropdown_action_hook(self):
        """Testing HeaderDropdownActionHook"""
        self._test_dropdown_action_hook('header_dropdown_action_hooks',
                                        HeaderDropdownActionHook)

    def _test_base_review_request_action_hook(self, url_name, hook_cls,
                                              should_render):
        """Test if the action hook renders or not at the given URL.

        Args:
            url_name (unicode):
                The name of the URL where each action is to be rendered.

            hook_cls (class):
                The class of the action hook to be tested.

            should_render (bool):
                The expected rendering behaviour.
        """
        hook = hook_cls(extension=self.extension, actions=[
            {
                'id': 'with-id-action',
                'label': 'Yes ID',
                'url': 'with-id-url',
            },
            self._TestAction(),
            {
                'label': 'No ID',
                'url': 'without-id-url',
            },
        ])

        try:
            context = self._get_context(url_name=url_name)
            entries = hook.get_actions(context)
            self.assertEqual(len(entries), 3)
            self.assertEqual(entries[0].action_id, 'with-id-action')
            self.assertEqual(entries[1].action_id, 'test-action')
            self.assertEqual(entries[2].action_id, 'no-id-dict-action')

            template = Template(
                '{% load reviewtags %}'
                '{% review_request_actions %}'
            )
            content = template.render(context)
            self.assertNotIn('action', context)
            self.assertEqual(should_render, 'href="with-id-url"' in content)
            self.assertIn('>Test Action<', content)
            self.assertEqual(should_render,
                             'id="no-id-dict-action"' in content)
        finally:
            hook.disable_hook()

        content = template.render(context)
        self.assertNotIn('href="with-id-url"', content)
        self.assertNotIn('>Test Action<', content)
        self.assertNotIn('id="no-id-dict-action"', content)

    def _test_review_request_dropdown_action_hook(self, url_name, hook_cls,
                                                  should_render):
        """Test if the dropdown action hook renders or not at the given URL.

        Args:
            url_name (unicode):
                The name of the URL where each action is to be rendered.

            hook_cls (class):
                The class of the dropdown action hook to be tested.

            should_render (bool):
                The expected rendering behaviour.
        """
        hook = hook_cls(extension=self.extension, actions=[
            self._TestMenuAction([
                self._TestAction(),
            ]),
            {
                'id': 'test-menu-dict-action',
                'label': 'Menu Dict',
                'items': [
                    {
                        'id': 'with-id-action',
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
            self.assertEqual(len(entries), 2)
            self.assertEqual(entries[0].action_id, 'test-menu-instance-action')
            self.assertEqual(entries[1].action_id, 'test-menu-dict-action')

            dropdown_icon_html = \
                '<span class="rb-icon rb-icon-dropdown-arrow"></span>'

            template = Template(
                '{% load reviewtags %}'
                '{% review_request_actions %}'
            )
            content = template.render(context)
            self.assertNotIn('action', context)
            self.assertInHTML('<a href="#" id="test-action">Test Action</a>',
                              content)
            self.assertInHTML(
                ('<a class="menu-title" href="#"'
                 ' id="test-menu-instance-action">'
                 'Menu Instance %s</a>'
                 % dropdown_icon_html),
                content)

            for s in (('id="test-menu-dict-action"',
                       'href="with-id-url"',
                       'id="no-id-dict-action"')):
                if should_render:
                    self.assertIn(s, content)
                else:
                    self.assertNotIn(s, content)

            if should_render:
                self.assertInHTML(
                    ('<a class="menu-title" href="#"'
                     ' id="test-menu-dict-action">'
                     'Menu Dict %s</a>'
                     % dropdown_icon_html),
                    content)
            else:
                self.assertNotIn('Menu Dict', content)
        finally:
            hook.disable_hook()

        content = template.render(context)
        self.assertNotIn('Test Action', content)
        self.assertNotIn('Menu Instance', content)
        self.assertNotIn('id="test-menu-dict-action"', content)
        self.assertNotIn('href="with-id-url"', content)
        self.assertNotIn('id="no-id-dict-action"', content)

    def _test_action_hook(self, template_tag_name, hook_cls):
        action = {
            'label': 'Test Action',
            'id': 'test-action',
            'image': 'test-image',
            'image_width': 42,
            'image_height': 42,
            'url': 'foo-url',
        }

        hook = hook_cls(extension=self.extension, actions=[action])

        context = Context({})
        entries = hook.get_actions(context)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0], action)

        t = Template(
            "{% load rb_extensions %}"
            "{% " + template_tag_name + " %}")

        self.assertEqual(t.render(context).strip(),
                         self._build_action_template(action))

    def _test_dropdown_action_hook(self, template_tag_name, hook_cls):
        action = {
            'id': 'test-menu',
            'label': 'Test Menu',
            'items': [
                {
                    'id': 'test-action',
                    'label': 'Test Action',
                    'url': 'foo-url',
                    'image': 'test-image',
                    'image_width': 42,
                    'image_height': 42
                }
            ]
        }

        hook = hook_cls(extension=self.extension,
                        actions=[action])

        context = Context({})
        entries = hook.get_actions(context)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0], action)

        t = Template(
            "{% load rb_extensions %}"
            "{% " + template_tag_name + " %}")

        content = t.render(context).strip()

        self.assertIn(('id="%s"' % action['id']), content)
        self.assertInHTML(
            ('<a href="#" id="test-menu">%s '
             '<span class="rb-icon rb-icon-dropdown-arrow"></span></a>'
             % action['label']),
            content)
        self.assertInHTML(self._build_action_template(action['items'][0]),
                          content)

    def _build_action_template(self, action):
        return ('<li><a id="%(id)s" href="%(url)s">'
                '<img src="%(image)s" width="%(image_width)s" '
                'height="%(image_height)s" border="0" alt="" />'
                '%(label)s</a></li>' % action)

    def _get_context(self, user_pk='123', is_authenticated=True,
                     url_name='review-request-detail', local_site_name=None,
                     status=ReviewRequest.PENDING_REVIEW, submitter_id='456',
                     is_public=True, display_id='789', has_diffs=True,
                     can_change_status=True, can_edit_reviewrequest=True,
                     delete_reviewrequest=True):
        request = Mock()
        request.resolver_match = Mock()
        request.resolver_match.url_name = url_name
        request.user = Mock()
        request.user.pk = user_pk
        request.user.is_authenticated.return_value = is_authenticated
        request._local_site_name = local_site_name

        review_request = Mock()
        review_request.status = status
        review_request.submitter_id = submitter_id
        review_request.public = is_public
        review_request.display_id = display_id

        if not has_diffs:
            review_request.get_draft.return_value = None
            review_request.get_diffsets.return_value = None

        context = Context({
            'request': request,
            'review_request': review_request,
            'perms': {
                'reviews': {
                    'can_change_status': can_change_status,
                    'can_edit_reviewrequest': can_edit_reviewrequest,
                    'delete_reviewrequest': delete_reviewrequest,
                },
            },
        })

        return context
