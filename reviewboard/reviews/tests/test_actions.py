from __future__ import unicode_literals

from django.template import Context, Template
from mock import Mock
from kgb import SpyAgency

from reviewboard.reviews.actions import (BaseReviewRequestAction,
                                         BaseReviewRequestMenuAction,
                                         clear_all_actions,
                                         MAX_DEPTH_LIMIT,
                                         register_actions,
                                         unregister_actions)
from reviewboard.reviews.errors import DepthLimitExceededError
from reviewboard.reviews.models import ReviewRequest
from reviewboard.testing import TestCase


class ActionTests(TestCase):
    """Tests the actions in reviewboard.reviews.actions."""

    fixtures = ['test_users']

    class _FooAction(BaseReviewRequestAction):
        action_id = 'foo-action'
        label = 'Foo Action'

    class _BarAction(BaseReviewRequestAction):
        action_id = 'bar-action'
        label = 'Bar Action'

    class _BazAction(BaseReviewRequestMenuAction):
        def __init__(self, action_id, child_actions=None):
            super(ActionTests._BazAction, self).__init__(child_actions)

            self.action_id = 'baz-' + action_id

    class _TopLevelMenuAction(BaseReviewRequestMenuAction):
        action_id = 'top-level-menu-action'
        label = 'Top Level Menu Action'

    class _PoorlyCodedAction(BaseReviewRequestAction):
        def get_label(self, context):
            raise Exception

    def _get_content(self, user_pk='123', is_authenticated=True,
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

        template = Template(
            '{% load reviewtags %}'
            '{% review_request_actions %}'
        )

        return template.render(context)

    def _get_long_action_list(self, length):
        actions = [None] * length
        actions[0] = self._BazAction('0')

        for d in range(1, len(actions)):
            actions[d] = self._BazAction(str(d), [actions[d - 1]])

        return actions

    def tearDown(self):
        super(ActionTests, self).tearDown()

        # This prevents registered/unregistered/modified actions from leaking
        # between different unit tests.
        clear_all_actions()

    def test_register_then_unregister(self):
        """Testing register then unregister for actions"""
        foo_action = self._FooAction()
        menu_action = self._TopLevelMenuAction([
            self._BarAction(),
        ])

        self.assertEqual(len(menu_action.child_actions), 1)
        bar_action = menu_action.child_actions[0]

        content = self._get_content()
        self.assertEqual(content.count('id="%s"' % foo_action.action_id), 0)
        self.assertEqual(content.count('>%s<' % foo_action.label), 0)
        self.assertEqual(content.count('id="%s"' % menu_action.action_id), 0)
        self.assertEqual(content.count('>%s &#9662;<' % menu_action.label), 0)
        self.assertEqual(content.count('id="%s"' % bar_action.action_id), 0)
        self.assertEqual(content.count('>%s<' % bar_action.label), 0)

        foo_action.register()

        content = self._get_content()
        self.assertEqual(content.count('id="%s"' % foo_action.action_id), 1)
        self.assertEqual(content.count('>%s<' % foo_action.label), 1)
        self.assertEqual(content.count('id="%s"' % menu_action.action_id), 0)
        self.assertEqual(content.count('>%s &#9662;<' % menu_action.label), 0)
        self.assertEqual(content.count('id="%s"' % bar_action.action_id), 0)
        self.assertEqual(content.count('>%s<' % bar_action.label), 0)

        menu_action.register()

        content = self._get_content()
        self.assertEqual(content.count('id="%s"' % foo_action.action_id), 1)
        self.assertEqual(content.count('>%s<' % foo_action.label), 1)
        self.assertEqual(content.count('id="%s"' % menu_action.action_id), 1)
        self.assertEqual(content.count('>%s &#9662;<' % menu_action.label), 1)
        self.assertEqual(content.count('id="%s"' % bar_action.action_id), 1)
        self.assertEqual(content.count('>%s<' % bar_action.label), 1)

        foo_action.unregister()

        content = self._get_content()
        self.assertEqual(content.count('id="%s"' % foo_action.action_id), 0)
        self.assertEqual(content.count('>%s<' % foo_action.label), 0)
        self.assertEqual(content.count('id="%s"' % menu_action.action_id), 1)
        self.assertEqual(content.count('>%s &#9662;<' % menu_action.label), 1)
        self.assertEqual(content.count('id="%s"' % bar_action.action_id), 1)
        self.assertEqual(content.count('>%s<' % bar_action.label), 1)

        menu_action.unregister()

        content = self._get_content()
        self.assertEqual(content.count('id="%s"' % foo_action.action_id), 0)
        self.assertEqual(content.count('>%s<' % foo_action.label), 0)
        self.assertEqual(content.count('id="%s"' % menu_action.action_id), 0)
        self.assertEqual(content.count('>%s &#9662;<' % menu_action.label), 0)
        self.assertEqual(content.count('id="%s"' % bar_action.action_id), 0)
        self.assertEqual(content.count('>%s<' % bar_action.label), 0)

    def test_unregister_actions_with_register_actions(self):
        """Testing unregister_actions with register_actions"""
        foo_action = self._FooAction()
        unregistered_ids = [
            'discard-review-request-action',
            'update-review-request-action',
            'ship-it-action',
        ]
        removed_ids = unregistered_ids + [
            'upload-diff-action',
            'upload-file-action',
        ]
        added_ids = [
            foo_action.action_id
        ]

        # Test that foo_action really does render as a child of the parent
        # Close menu (and not any other menu).
        new_close_menu_html = '\n'.join([
            '<li class="review-request-action has-menu">',
            ' <a class="menu-title" id="close-review-request-action"',
            '    href="#">Close &#9662;</a>',
            ' <ul class="menu">',
            '<li class="review-request-action">',
            ' <a id="submit-review-request-action" href="#">Submitted</a>',
            '</li>',
            '<li class="review-request-action">',
            (' <a id="delete-review-request-action" href="#">Delete '
             'Permanently</a>'),
            '</li>',
            '<li class="review-request-action">',
            (' <a id="%s" href="%s">%s</a>'
             % (foo_action.action_id, foo_action.url, foo_action.label)),
            '</li>',
        ])

        content = self._get_content()

        for action_id in added_ids:
            self.assertEqual(content.count('id="%s"' % action_id), 0,
                             '%s should not have rendered' % action_id)

        for action_id in removed_ids:
            self.assertEqual(content.count('id="%s"' % action_id), 1,
                             '%s should\'ve rendered exactly once' % action_id)

        unregister_actions(unregistered_ids)
        content = self._get_content()

        for action_id in added_ids + removed_ids:
            self.assertEqual(content.count('id="%s"' % action_id), 0,
                             '%s should not have rendered' % action_id)

        register_actions([foo_action], 'close-review-request-action')
        content = self._get_content()

        for action_id in removed_ids:
            self.assertEqual(content.count('id="%s"' % action_id), 0,
                             '%s should not have rendered' % action_id)

        for action_id in added_ids:
            self.assertEqual(content.count('id="%s"' % action_id), 1,
                             '%s should\'ve rendered exactly once' % action_id)

        self.assertEqual(content.count(new_close_menu_html), 1)

    def test_register_raises_key_error(self):
        """Testing that register raises a KeyError"""
        foo_action = self._FooAction()
        error_message = ('%s already corresponds to a registered review '
                         'request action') % foo_action.action_id

        foo_action.register()

        with self.assertRaisesMessage(KeyError, error_message):
            foo_action.register()

    def test_register_raises_depth_limit_exceeded_error(self):
        """Testing that register raises a DepthLimitExceededError"""
        actions = self._get_long_action_list(MAX_DEPTH_LIMIT + 1)
        invalid_action = self._BazAction(str(len(actions)), [actions[-1]])
        error_message = ('%s exceeds the maximum depth limit of %d'
                         % (invalid_action.action_id, MAX_DEPTH_LIMIT))

        with self.assertRaisesMessage(DepthLimitExceededError, error_message):
            invalid_action.register()

    def test_unregister_raises_key_error(self):
        """Testing that unregister raises a KeyError"""
        foo_action = self._FooAction()
        menu_action = self._TopLevelMenuAction([
            self._BarAction(),
        ])
        foo_message = ('%s does not correspond to a registered review '
                       'request action') % foo_action.action_id
        menu_message = ('%s does not correspond to a registered review '
                        'request action') % menu_action.action_id

        with self.assertRaisesMessage(KeyError, foo_message):
            foo_action.unregister()

        with self.assertRaisesMessage(KeyError, menu_message):
            menu_action.unregister()

    def test_unregister_with_max_depth(self):
        """Testing unregister with max_depth"""
        actions = self._get_long_action_list(MAX_DEPTH_LIMIT + 1)
        actions[0].unregister()
        extra_action = self._BazAction(str(len(actions)), [actions[-1]])

        extra_action.register()
        self.assertEquals(extra_action.max_depth, MAX_DEPTH_LIMIT)

    def test_init_raises_key_error(self):
        """Testing that __init__ raises a KeyError"""
        foo_action = self._FooAction()
        error_message = ('%s already corresponds to a registered review '
                         'request action') % foo_action.action_id

        foo_action.register()

        with self.assertRaisesMessage(KeyError, error_message):
            self._TopLevelMenuAction([
                foo_action,
            ])

    def test_register_actions_raises_key_errors(self):
        """Testing that register_actions raises KeyErrors"""
        foo_action = self._FooAction()
        bar_action = self._BarAction()
        missing_message = ('%s does not correspond to a registered review '
                           'request action') % bar_action.action_id
        second_message = ('%s already corresponds to a registered review '
                          'request action') % foo_action.action_id
        foo_action.register()

        with self.assertRaisesMessage(KeyError, missing_message):
            register_actions([foo_action], bar_action.action_id)

        with self.assertRaisesMessage(KeyError, second_message):
            register_actions([foo_action])

    def test_register_actions_raises_depth_limit_exceeded_error(self):
        """Testing that register_actions raises a DepthLimitExceededError"""
        actions = self._get_long_action_list(MAX_DEPTH_LIMIT + 1)
        invalid_action = self._BazAction(str(len(actions)), [actions[-1]])
        error_message = ('%s exceeds the maximum depth limit of %d'
                         % (invalid_action.action_id, MAX_DEPTH_LIMIT))

        with self.assertRaisesMessage(DepthLimitExceededError, error_message):
            register_actions([invalid_action])

    def test_register_actions_with_max_depth(self):
        """Testing register_actions with max_depth"""
        actions = self._get_long_action_list(MAX_DEPTH_LIMIT)
        extra_action = self._BazAction('extra')
        foo_action = self._FooAction()

        for d, action in enumerate(actions):
            self.assertEquals(action.max_depth, d)

        register_actions([extra_action], actions[0].action_id)
        actions = [extra_action] + actions

        for d, action in enumerate(actions):
            self.assertEquals(action.max_depth, d)

        register_actions([foo_action])
        self.assertEquals(foo_action.max_depth, 0)

    def test_unregister_actions_raises_key_error(self):
        """Testing that unregister_actions raises a KeyError"""
        foo_action = self._FooAction()
        error_message = ('%s does not correspond to a registered review '
                         'request action') % foo_action.action_id

        with self.assertRaisesMessage(KeyError, error_message):
            unregister_actions([foo_action.action_id])

    def test_unregister_actions_with_max_depth(self):
        """Testing unregister_actions with max_depth"""
        actions = self._get_long_action_list(MAX_DEPTH_LIMIT + 1)

        unregister_actions([actions[0].action_id])
        extra_action = self._BazAction(str(len(actions)), [actions[-1]])
        extra_action.register()
        self.assertEquals(extra_action.max_depth, MAX_DEPTH_LIMIT)

    def test_render_pops_context_even_after_error(self):
        """Testing that render pops the context even after an error"""
        context = Context({'comment': 'this is a comment'})
        old_dict_count = len(context.dicts)
        poorly_coded_action = self._PoorlyCodedAction()

        with self.assertRaises(Exception):
            poorly_coded_action.render(context)

        new_dict_count = len(context.dicts)
        self.assertEquals(old_dict_count, new_dict_count)


class DefaultActionTests(SpyAgency, TestCase):
    """Tests for default actions in reviewboard.reviews.default_actions"""

    fixtures = ['test_users']

    def _get_content(self, user_pk='123', is_authenticated=True,
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
            review_request.repository_id = None

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

        template = Template(
            '{% load reviewtags %}'
            '{% review_request_actions %}'
        )

        return template.render(context)

    def test_should_render_when_user_is_submitter(self):
        """Testing should_render when user is the submitter"""
        same_user = '1234'
        other_user = '5678'
        user_is_submitter_action_ids = [
            'close-review-request-action',
            'submit-review-request-action',
            'discard-review-request-action',
            'delete-review-request-action',
            'update-review-request-action',
            'upload-diff-action',
            'upload-file-action',
        ]

        content = self._get_content(user_pk=same_user, submitter_id=same_user,
                                    can_change_status=False,
                                    can_edit_reviewrequest=False)

        for action_id in user_is_submitter_action_ids:
            self.assertEqual(content.count('id="%s"' % action_id), 1,
                             '%s should\'ve rendered exactly once' % action_id)

        content = self._get_content(user_pk=same_user, submitter_id=other_user,
                                    can_change_status=False,
                                    can_edit_reviewrequest=False)

        for action_id in user_is_submitter_action_ids:
            self.assertEqual(content.count('id="%s"' % action_id), 0,
                             '%s should not have rendered' % action_id)

    def test_should_render_when_user_is_authenticated(self):
        """Testing should_render when user is authenticated"""
        authenticated_only_action_ids = [
            'review-action',
            'ship-it-action',
        ]

        content = self._get_content(is_authenticated=True)

        for action_id in authenticated_only_action_ids:
            self.assertEqual(content.count('id="%s"' % action_id), 1,
                             '%s should\'ve rendered exactly once' % action_id)

        content = self._get_content(is_authenticated=False)

        for action_id in authenticated_only_action_ids:
            self.assertEqual(content.count('id="%s"' % action_id), 0,
                             '%s should not have rendered' % action_id)

    def test_should_render_when_pending_review(self):
        """Testing should_render when the review request is pending review"""
        same_user = '1234'
        pending_review_action_ids = [
            'close-review-request-action',
            'submit-review-request-action',
            'discard-review-request-action',
            'delete-review-request-action',
            'update-review-request-action',
            'upload-diff-action',
            'upload-file-action',
        ]

        content = self._get_content(status=ReviewRequest.PENDING_REVIEW,
                                    user_pk=same_user, submitter_id=same_user)

        for action_id in pending_review_action_ids:
            self.assertEqual(content.count('id="%s"' % action_id), 1,
                             '%s should\'ve rendered exactly once' % action_id)

        content = self._get_content(status=ReviewRequest.SUBMITTED,
                                    user_pk=same_user, submitter_id=same_user)

        for action_id in pending_review_action_ids:
            self.assertEqual(content.count('id="%s"' % action_id), 0,
                             '%s should not have rendered' % action_id)

    def test_should_render_with_public_review_requests(self):
        """Testing should_render with public review requests"""
        same_user = '1234'
        public_only_action_ids = [
            'submit-review-request-action',
        ]
        always_render_action_ids = [
            'close-review-request-action',
            'discard-review-request-action',
            'delete-review-request-action',
        ]

        content = self._get_content(is_public=True, user_pk=same_user,
                                    submitter_id=same_user)

        for action_id in public_only_action_ids + always_render_action_ids:
            self.assertEqual(content.count('id="%s"' % action_id), 1,
                             '%s should\'ve rendered exactly once' % action_id)

        content = self._get_content(is_public=False, user_pk=same_user,
                                    submitter_id=same_user)

        for action_id in public_only_action_ids:
            self.assertEqual(content.count('id="%s"' % action_id), 0,
                             '%s should not have rendered' % action_id)

        for action_id in always_render_action_ids:
            self.assertEqual(content.count('id="%s"' % action_id), 1,
                             '%s should\'ve rendered exactly once' % action_id)

    def test_get_label_and_should_render_when_review_request_has_diffs(self):
        """Testing get_label and should_ render when diffs exist"""
        update_diff_label = 'Update Diff'
        upload_diff_label = 'Upload Diff'
        download_diff_action_id = 'download-diff-action'

        content = self._get_content(has_diffs=True)
        self.assertEqual(content.count('>%s<' % update_diff_label), 1)
        self.assertEqual(content.count('>%s<' % upload_diff_label), 0)
        self.assertEqual(content.count('id="%s"' % download_diff_action_id), 1)

        content = self._get_content(has_diffs=False)
        self.assertEqual(content.count('>%s<' % update_diff_label), 0)
        self.assertEqual(content.count('>%s<' % upload_diff_label), 0)
        self.assertEqual(content.count('id="%s"' % download_diff_action_id), 0)

    def test_get_hidden_when_viewing_interdiff(self):
        """Testing get_hidden when viewing an interdiff"""
        hidden_download_diff = 'style="display: none;">Download Diff<'
        hidden_url_names = [
            'view-interdiff',
        ]
        visible_url_names = [
            'view-diff',
            'file-attachment',
            'review-request-detail',
        ]

        for url_name in hidden_url_names:
            content = self._get_content(url_name=url_name)
            self.assertEqual(content.count(hidden_download_diff), 1,
                             '%s should\'ve been hidden' % url_name)

        for url_name in visible_url_names:
            content = self._get_content(url_name=url_name)
            self.assertEqual(content.count(hidden_download_diff), 0,
                             '%s should\'ve been visible' % url_name)

    def test_should_render_with_can_change_status(self):
        """Testing should_render with reviews.can_change_status"""
        can_change_action_ids = [
            'close-review-request-action',
            'submit-review-request-action',
            'discard-review-request-action',
            'delete-review-request-action',
        ]

        content = self._get_content(can_change_status=True)

        for action_id in can_change_action_ids:
            self.assertEqual(content.count('id="%s"' % action_id), 1,
                             '%s should\'ve rendered exactly once' % action_id)

        content = self._get_content(can_change_status=False)

        for action_id in can_change_action_ids:
            self.assertEqual(content.count('id="%s"' % action_id), 0,
                             '%s should not have rendered' % action_id)

    def test_should_render_with_can_edit_reviewrequest(self):
        """Testing should_render with reviews.can_edit_reviewrequest"""
        can_edit_action_ids = [
            'update-review-request-action',
            'upload-diff-action',
            'upload-file-action',
        ]

        content = self._get_content(can_edit_reviewrequest=True)

        for action_id in can_edit_action_ids:
            self.assertEqual(content.count('id="%s"' % action_id), 1,
                             '%s should\'ve rendered exactly once' % action_id)

        content = self._get_content(can_edit_reviewrequest=False)

        for action_id in can_edit_action_ids:
            self.assertEqual(content.count('id="%s"' % action_id), 0,
                             '%s should not have rendered' % action_id)

    def test_should_render_with_delete_reviewrequest(self):
        """Testing should_render with reviews.delete_reviewrequest"""
        can_delete_action_ids = [
            'delete-review-request-action',
        ]

        content = self._get_content(delete_reviewrequest=True)

        for action_id in can_delete_action_ids:
            self.assertEqual(content.count('id="%s"' % action_id), 1,
                             '%s should\'ve rendered exactly once' % action_id)

        content = self._get_content(delete_reviewrequest=False)

        for action_id in can_delete_action_ids:
            self.assertEqual(content.count('id="%s"' % action_id), 0,
                             '%s should not have rendered' % action_id)
