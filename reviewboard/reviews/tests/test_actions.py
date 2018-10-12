from __future__ import unicode_literals

from django.contrib.auth.models import AnonymousUser, User
from django.template import Context
from django.test.client import RequestFactory
from django.utils import six
from djblets.siteconfig.models import SiteConfiguration
from djblets.testing.decorators import add_fixtures
from mock import Mock

from reviewboard.reviews.actions import (BaseReviewRequestAction,
                                         BaseReviewRequestMenuAction,
                                         MAX_DEPTH_LIMIT,
                                         clear_all_actions,
                                         get_top_level_actions,
                                         register_actions,
                                         unregister_actions)
from reviewboard.reviews.default_actions import (AddGeneralCommentAction,
                                                 CloseMenuAction,
                                                 DeleteAction,
                                                 DownloadDiffAction,
                                                 EditReviewAction,
                                                 ShipItAction,
                                                 SubmitAction,
                                                 UpdateMenuAction,
                                                 UploadDiffAction)
from reviewboard.reviews.errors import DepthLimitExceededError
from reviewboard.reviews.models import ReviewRequest
from reviewboard.testing import TestCase


class FooAction(BaseReviewRequestAction):
    action_id = 'foo-action'
    label = 'Foo Action'


class BarAction(BaseReviewRequestMenuAction):
    def __init__(self, action_id, child_actions=None):
        super(BarAction, self).__init__(child_actions)

        self.action_id = 'bar-' + action_id


class TopLevelMenuAction(BaseReviewRequestMenuAction):
    action_id = 'top-level-menu-action'
    label = 'Top Level Menu Action'


class PoorlyCodedAction(BaseReviewRequestAction):
    def get_label(self, context):
        raise Exception


class ActionsTestCase(TestCase):
    """Test case for unit tests dealing with actions."""

    def tearDown(self):
        super(ActionsTestCase, self).tearDown()

        # This prevents registered/unregistered/modified actions from leaking
        # between different unit tests.
        clear_all_actions()

    def make_nested_actions(self, depth):
        """Return a nested list of actions to register.

        This returns a list of actions, each entry nested within the prior
        entry, of the given length. The resulting list is intended to be
        registered.

        Args:
            depth (int):
                The nested depth for the actions.

        Returns:
            list of reviewboard.reviews.actions.BaseReviewRequestAction:
            The list of actions.
        """
        actions = [None] * depth
        actions[0] = BarAction('0')

        for i in range(1, depth):
            actions[i] = BarAction(six.text_type(i), [actions[i - 1]])

        return actions

class ReadOnlyActionTestsMixin(object):
    """Mixin for Review Board actions-related unit tests with read-only mode.

    This mixin is used to add read-only mode tests to action test cases.Using
    this mixin is especially important for actions that change visibility
    based on whether read-only mode is active. Actions that should always be
    visible can also be tested by setting ``read_only_always_show``.
    """

    def setUp(self):
        """Set up the test case."""
        super(ReadOnlyActionTestsMixin, self).setUp()

        self.request = RequestFactory().request()
        self.siteconfig = SiteConfiguration.objects.get_current()

    def shortDescription(self):
        """Return an updated description for a particular test.

        If the test has an ``action`` attribute set and contains ``<ACTION>``
        in the docstring, then ACTION will be replaced by the ``action_id``
        attribute of the
        :py:class:`~reviewboard.reviews.actions.BaseReviewRequestAction`.

        Returns:
            unicode:
            The description of the test.
        """
        desc = super(ReadOnlyActionTestsMixin, self).shortDescription()

        if self.action and getattr(self, self._testMethodName, False):
            desc = desc.replace('<ACTION>', type(self.action).__name__)

        return desc

    def _create_request_context(self, *args, **kwargs):
        """Create and return objects for use in the request context.

        Args:
            *args (tuple):
                Positional arguments for use in subclasses.

            **kwargs (dict):
                Keyword arguments for use in subclasses.

        Returns:
            dict:
            Additional context to use when testing read-only actions.
        """
        return {}

    def test_should_render_with_user_in_read_only(self):
        """Testing <ACTION>.should_render with authenticated user in read-only
        mode
        """
        self.request.user = User.objects.get(username='doc')

        # Turning on read-only mode prevents creation of some objects so call
        # _create_request_context first.
        request_context = self._create_request_context(user=self.request.user)

        settings = {
            'site_read_only': True,
        }

        with self.siteconfig_settings(settings):
            if getattr(self, 'read_only_always_show', False):
                self.assertTrue(self.action.should_render(request_context))
            else:
                self.assertFalse(self.action.should_render(request_context))

    def test_should_render_with_superuser_in_read_only(self):
        """Testing <ACTION>.should_render with superuser in read-only mode"""
        self.request.user = User.objects.get(username='admin')

        # Turning on read-only mode prevents creation of some objects so call
        # _create_request_context first.
        request_context = self._create_request_context(user=self.request.user)

        settings = {
            'site_read_only': True,
        }

        with self.siteconfig_settings(settings):
            self.assertTrue(self.action.should_render(request_context))


class ActionRegistryTests(ActionsTestCase):
    """Unit tests for the review request actions registry."""

    def test_register_actions_with_invalid_parent_id(self):
        """Testing register_actions with an invalid parent ID"""
        foo_action = FooAction()

        message = (
            'bad-id does not correspond to a registered review request action'
        )

        foo_action.register()

        with self.assertRaisesMessage(KeyError, message):
            register_actions([foo_action], 'bad-id')

    def test_register_actions_with_already_registered_action(self):
        """Testing register_actions with an already registered action"""
        foo_action = FooAction()

        message = (
            '%s already corresponds to a registered review request action'
            % foo_action.action_id
        )

        foo_action.register()

        with self.assertRaisesMessage(KeyError, message):
            register_actions([foo_action])

    def test_register_actions_with_max_depth(self):
        """Testing register_actions with max_depth"""
        actions = self.make_nested_actions(MAX_DEPTH_LIMIT)
        extra_action = BarAction('extra')
        foo_action = FooAction()

        for d, action in enumerate(actions):
            self.assertEquals(action.max_depth, d)

        register_actions([extra_action], actions[0].action_id)
        actions = [extra_action] + actions

        for d, action in enumerate(actions):
            self.assertEquals(action.max_depth, d)

        register_actions([foo_action])
        self.assertEquals(foo_action.max_depth, 0)

    def test_register_actions_with_too_deep(self):
        """Testing register_actions with exceeding max depth"""
        actions = self.make_nested_actions(MAX_DEPTH_LIMIT + 1)
        invalid_action = BarAction(str(len(actions)), [actions[-1]])

        error_message = (
            '%s exceeds the maximum depth limit of %d'
            % (invalid_action.action_id, MAX_DEPTH_LIMIT)
        )

        with self.assertRaisesMessage(DepthLimitExceededError, error_message):
            register_actions([invalid_action])

    def test_unregister_actions(self):
        """Testing unregister_actions"""

        orig_action_ids = {
            action.action_id
            for action in get_top_level_actions()
        }
        self.assertIn('update-review-request-action', orig_action_ids)
        self.assertIn('review-action', orig_action_ids)

        unregister_actions(['update-review-request-action', 'review-action'])

        new_action_ids = {
            action.action_id
            for action in get_top_level_actions()
        }
        self.assertEqual(len(orig_action_ids), len(new_action_ids) + 2)
        self.assertNotIn('update-review-request-action', new_action_ids)
        self.assertNotIn('review-action', new_action_ids)

    def test_unregister_actions_with_child_action(self):
        """Testing unregister_actions with child action"""
        menu_action = TopLevelMenuAction([
            FooAction()
        ])

        self.assertEqual(len(menu_action.child_actions), 1)
        unregister_actions([FooAction.action_id])
        self.assertEqual(len(menu_action.child_actions), 0)

    def test_unregister_actions_with_unregistered_action(self):
        """Testing unregister_actions with unregistered action"""
        foo_action = FooAction()
        error_message = (
            '%s does not correspond to a registered review request action'
            % foo_action.action_id
        )

        with self.assertRaisesMessage(KeyError, error_message):
            unregister_actions([foo_action.action_id])

    def test_unregister_actions_with_max_depth(self):
        """Testing unregister_actions with max_depth"""
        actions = self.make_nested_actions(MAX_DEPTH_LIMIT + 1)

        unregister_actions([actions[0].action_id])
        extra_action = BarAction(str(len(actions)), [actions[-1]])
        extra_action.register()
        self.assertEquals(extra_action.max_depth, MAX_DEPTH_LIMIT)


class BaseReviewRequestActionTests(ActionsTestCase):
    """Unit tests for BaseReviewRequestAction."""

    def test_register_then_unregister(self):
        """Testing BaseReviewRequestAction.register then unregister for
        actions
        """
        foo_action = FooAction()
        foo_action.register()

        self.assertIn(foo_action.action_id, (
            action.action_id
            for action in get_top_level_actions()
        ))

        foo_action.unregister()

        self.assertNotIn(foo_action.action_id, (
            action.action_id
            for action in get_top_level_actions()
        ))

    def test_register_with_already_registered(self):
        """Testing BaseReviewRequestAction.register with already registered
        action
        """
        foo_action = FooAction()
        error_message = (
            '%s already corresponds to a registered review request action'
            % foo_action.action_id
        )

        foo_action.register()

        with self.assertRaisesMessage(KeyError, error_message):
            foo_action.register()

    def test_register_with_too_deep(self):
        """Testing BaseReviewRequestAction.register with exceeding max depth"""
        actions = self.make_nested_actions(MAX_DEPTH_LIMIT + 1)
        invalid_action = BarAction(str(len(actions)), [actions[-1]])
        error_message = (
            '%s exceeds the maximum depth limit of %d'
            % (invalid_action.action_id, MAX_DEPTH_LIMIT)
        )

        with self.assertRaisesMessage(DepthLimitExceededError, error_message):
            invalid_action.register()

    def test_unregister_with_unregistered_action(self):
        """Testing BaseReviewRequestAction.unregister with unregistered
        action
        """
        foo_action = FooAction()

        message = (
            '%s does not correspond to a registered review request action'
            % foo_action.action_id
        )

        with self.assertRaisesMessage(KeyError, message):
            foo_action.unregister()

    def test_unregister_with_max_depth(self):
        """Testing BaseReviewRequestAction.unregister with max_depth"""
        actions = self.make_nested_actions(MAX_DEPTH_LIMIT + 1)
        actions[0].unregister()
        extra_action = BarAction(str(len(actions)), [actions[-1]])

        extra_action.register()
        self.assertEquals(extra_action.max_depth, MAX_DEPTH_LIMIT)

    def test_init_already_registered_in_menu(self):
        """Testing BaseReviewRequestAction.__init__ for already registered
        action when nested in a menu action
        """
        foo_action = FooAction()
        error_message = ('%s already corresponds to a registered review '
                         'request action') % foo_action.action_id

        foo_action.register()

        with self.assertRaisesMessage(KeyError, error_message):
            TopLevelMenuAction([
                foo_action,
            ])

    def test_render_pops_context_even_after_error(self):
        """Testing BaseReviewRequestAction.render pops the context after an
        error
        """
        context = Context({'comment': 'this is a comment'})
        old_dict_count = len(context.dicts)
        poorly_coded_action = PoorlyCodedAction()

        with self.assertRaises(Exception):
            poorly_coded_action.render(context)

        new_dict_count = len(context.dicts)
        self.assertEquals(old_dict_count, new_dict_count)


class AddGeneralCommentActionTests(ReadOnlyActionTestsMixin, ActionsTestCase):
    """Unit tests for AddGeneralCommentAction."""

    action = AddGeneralCommentAction()
    fixtures = ['test_users']

    def _create_request_context(self, *args, **kwargs):
        """Create and return objects for use in the request context.

        Args:
            *args (tuple):
                Positional arguments (unused).

            **kwargs (dict):
                Keyword arguments (unused).

        Returns:
            dict:
            Additional context to use when testing read-only actions.
        """
        return {
            'request': self.request,
        }

    def test_should_render_with_authenticated(self):
        """Testing AddGeneralCommentAction.should_render with authenticated
        user
        """
        self.request.user = User.objects.get(username='doc')
        self.assertTrue(
            self.action.should_render(self._create_request_context()))

    def test_should_render_with_anonymous(self):
        """Testing AddGeneralCommentAction.should_render with authenticated
        user
        """
        self.request.user = AnonymousUser()
        self.assertFalse(
            self.action.should_render(self._create_request_context()))


class CloseMenuActionTests(ReadOnlyActionTestsMixin, ActionsTestCase):
    """Unit tests for CloseMenuAction."""

    action = CloseMenuAction()
    fixtures = ['test_users']

    def _create_request_context(self, can_change_status=True, public=True,
                                status=ReviewRequest.PENDING_REVIEW,
                                user=None):
        """Create and return objects for use in the request context.

        Args:
            can_change_status (bool, optional):
                Whether the ``can_change_status`` permission should be set.

            public (bool, optional):
                Whether the review request should be public.

            status (unicode, optional):
                The status for the review request.

            user (django.contrib.auth.models.User, optional):
                An optional user to set as the owner of the request.

            *args (tuple):
                Additional positional arguments (unused).

            **kwargs (dict):
                Additional keyword arguments (unused).

        Returns:
            dict:
            Additional context to use when testing read-only actions.
        """
        review_request = self.create_review_request(
            public=public, status=status)
        self.request.user = user or review_request.submitter

        return {
            'review_request': review_request,
            'request': self.request,
            'perms': {
                'reviews': {
                    'can_change_status': can_change_status,
                },
            },
        }

    def test_should_render_for_owner(self):
        """Testing CloseMenuAction.should_render for owner of review request"""
        self.assertTrue(self.action.should_render(
            self._create_request_context()))

    def test_should_render_for_owner_unpublished(self):
        """Testing CloseMenuAction.should_render for owner of review
        unpublished review request
        """
        self.assertTrue(self.action.should_render(
            self._create_request_context(public=False)))

    def test_should_render_for_user(self):
        """Testing CloseMenuAction.should_render for normal user"""
        self.assertFalse(self.action.should_render(
            self._create_request_context(
                can_change_status=False,
                user=User.objects.create_user(username='test-user',
                                              email='user@example.com'))))

    def test_should_render_user_with_can_change_status(self):
        """Testing CloseMenuAction.should_render for user with
        can_change_status permission
        """
        self.assertTrue(self.action.should_render(
            self._create_request_context(
                can_change_status=True,
                user=User.objects.create_user(username='test-user',
                                              email='user@example.com'))))

    def test_should_render_user_with_can_change_status_and_unpublished(self):
        """Testing CloseMenuAction.should_render for user with
        can_change_status permission and unpublished review request
        """
        self.assertFalse(self.action.should_render(
            self._create_request_context(
                can_change_status=True,
                public=False,
                user=User.objects.create_user(username='test-user',
                                              email='user@example.com'))))

    def test_should_render_with_discarded(self):
        """Testing CloseMenuAction.should_render with discarded review request
        """
        self.assertFalse(self.action.should_render(
            self._create_request_context(status=ReviewRequest.DISCARDED)))

    def test_should_render_with_submitted(self):
        """Testing CloseMenuAction.should_render with submitted review request
        """
        self.assertFalse(self.action.should_render(
            self._create_request_context(status=ReviewRequest.SUBMITTED)))


class DeleteActionTests(ReadOnlyActionTestsMixin, ActionsTestCase):
    """Unit tests for DeleteAction."""

    fixtures = ['test_users']
    action = DeleteAction()

    def _create_request_context(self, delete_reviewrequest=True,
                                *args, **kwargs):
        """Create and return objects for use in the request context.

        Args:
            delete_reviewrequest (bool, optional):
                Whether the resulting context should include the
                ``delete_reviewrequest`` permission.

            *args (tuple):
                Positional arguments (unused).

            **kwargs (dict):
                Keyword arguments (unused).

        Returns:
            dict:
            Additional context to use when testing read-only actions.
        """
        return {
            'request': self.request,
            'perms': {
                'reviews': {
                    'delete_reviewrequest': delete_reviewrequest,
                },
            },
        }

    def test_should_render_with_published(self):
        """Testing DeleteAction.should_render with standard user"""
        self.request.user = User()
        self.assertFalse(self.action.should_render(
            self._create_request_context(delete_reviewrequest=False)))

    def test_should_render_with_permission(self):
        """Testing SubmitAction.should_render with delete_reviewrequest
        permission
        """
        self.request.user = User()
        self.assertTrue(self.action.should_render(
            self._create_request_context()))


class DownloadDiffActionTests(ReadOnlyActionTestsMixin, ActionsTestCase):
    """Unit tests for DownloadDiffAction."""

    action = DownloadDiffAction()
    fixtures = ['test_users']
    read_only_always_show=True

    def _create_request_context(self, review_request=None,
                                url_name='view-diff',
                                *args, **kwargs):
        """Create and return objects for use in the request context.

        Args:
            review_request (reviewboard.reviews.models.review_request.
                            ReviewRequest, optional):
                The review request to use. If not specified, one will be
                created.

            url_name (unicode, optional):
                The URL name to fake on the resolver.

            *args (tuple):
                Positional arguments (unused).

            **kwargs (dict):
                Keyword arguments (unused).

        Returns:
            dict:
            Additional context to use when testing read-only actions.
        """
        self.request.resolver_match = Mock()
        self.request.resolver_match.url_name = url_name

        if not review_request:
            review_request = self.create_review_request()

        return {
            'request': self.request,
            'review_request': review_request,
        }

    def test_get_url_on_diff_viewer(self):
        """Testing DownloadDiffAction.get_url on diff viewer page"""
        self.request.resolver_match = Mock()
        self.request.resolver_match.url_name = 'view-diff'

        self.assertEqual(self.action.get_url({'request': self.request}),
                         'raw/')

    def test_get_url_on_interdiff(self):
        """Testing DownloadDiffAction.get_url on diff viewer interdiff page"""
        self.request.resolver_match = Mock()
        self.request.resolver_match.url_name = 'view-interdiff'

        self.assertEqual(self.action.get_url({'request': self.request}),
                         'raw/')

    def test_get_url_on_diff_viewer_revision(self):
        """Testing DownloadDiffAction.get_url on diff viewer revision page"""
        self.request.resolver_match = Mock()
        self.request.resolver_match.url_name = 'view-diff-revision'

        self.assertEqual(self.action.get_url({'request': self.request}),
                         'raw/')

    def test_get_url_on_review_request(self):
        """Testing DownloadDiffAction.get_url on review request page"""
        self.request.resolver_match = Mock()
        self.request.resolver_match.url_name = 'review-request-detail'

        review_request = self.create_review_request()

        self.assertEqual(
            self.action.get_url({
                'request': self.request,
                'review_request': review_request,
            }),
            '/r/%s/diff/raw/' % review_request.display_id)

    @add_fixtures(['test_site'])
    def test_get_url_on_review_request_with_local_site(self):
        """Testing DownloadDiffAction.get_url on review request page with
        LocalSite
        """
        self.request.resolver_match = Mock()
        self.request.resolver_match.url_name = 'review-request-detail'
        self.request._local_site_name = self.local_site_name

        review_request = self.create_review_request(id=123,
                                                    with_local_site=True)

        self.assertEqual(
            self.action.get_url({
                'request': self.request,
                'review_request': review_request,
            }),
            '/s/%s/r/%s/diff/raw/' % (self.local_site_name,
                                      review_request.display_id))

    def test_get_hidden_on_diff_viewer(self):
        """Testing DownloadDiffAction.get_hidden on diff viewer page"""
        self.request.resolver_match = Mock()
        self.request.resolver_match.url_name = 'view-diff'

        self.assertFalse(self.action.get_hidden({'request': self.request}))

    def test_get_hidden_on_interdiff(self):
        """Testing DownloadDiffAction.get_hidden on diff viewer interdiff page
        """
        self.request.resolver_match = Mock()
        self.request.resolver_match.url_name = 'view-interdiff'

        self.assertTrue(self.action.get_hidden({'request': self.request}))

    def test_get_hidden_on_diff_viewer_revision(self):
        """Testing DownloadDiffAction.get_hdiden on diff viewer revision page
        """
        self.request.resolver_match = Mock()
        self.request.resolver_match.url_name = 'view-diff-revision'

        self.assertFalse(self.action.get_hidden({'request': self.request}))

    def test_get_hidden_on_review_request(self):
        """Testing DownloadDiffAction.get_hdiden on diff viewer revision page
        """
        self.request.resolver_match = Mock()
        self.request.resolver_match.url_name = 'review-request-detail'

        review_request = self.create_review_request()

        self.assertFalse(self.action.get_hidden({
            'request': self.request,
            'review_request': review_request,
        }))

    def test_should_render_on_diff_viewer(self):
        """Testing DownloadDiffAction.should_render on diff viewer page"""
        self.request.resolver_match = Mock()
        self.request.resolver_match.url_name = 'view-diff'

        review_request = self.create_review_request()

        self.assertTrue(self.action.should_render({
            'request': self.request,
            'review_request': review_request,
        }))

    def test_should_render_on_interdiff(self):
        """Testing DownloadDiffAction.should_render on diff viewer interdiff
        page
        """
        self.request.resolver_match = Mock()
        self.request.resolver_match.url_name = 'view-interdiff'

        review_request = self.create_review_request()

        self.assertTrue(self.action.should_render({
            'request': self.request,
            'review_request': review_request,
        }))

    def test_should_render_on_diff_viewer_revision(self):
        """Testing DownloadDiffAction.should_render on diff viewer revision
        page
        """
        self.request.resolver_match = Mock()
        self.request.resolver_match.url_name = 'view-diff-revision'

        review_request = self.create_review_request()

        self.assertTrue(self.action.should_render({
            'request': self.request,
            'review_request': review_request,
        }))

    @add_fixtures(['test_scmtools'])
    def test_should_render_on_review_request_with_repository(self):
        """Testing DownloadDiffAction.should_render on review request page
        with repository
        """
        self.request.resolver_match = Mock()
        self.request.resolver_match.url_name = 'review-request-detail'

        review_request = self.create_review_request(create_repository=True)

        self.assertTrue(self.action.should_render({
            'request': self.request,
            'review_request': review_request,
        }))

    @add_fixtures(['test_scmtools'])
    def test_should_render_on_review_request_without_repository(self):
        """Testing DownloadDiffAction.should_render on review request page
        without repository
        """
        self.request.resolver_match = Mock()
        self.request.resolver_match.url_name = 'review-request-detail'

        review_request = self.create_review_request()

        self.assertFalse(self.action.should_render({
            'request': self.request,
            'review_request': review_request,
        }))


class EditReviewActionTests(ReadOnlyActionTestsMixin, ActionsTestCase):
    """Unit tests for EditReviewAction."""

    action = EditReviewAction()
    fixtures = ['test_users']

    def _create_request_context(self, *args, **kwargs):
        """Create and return objects for use in the request context.

        Args:
            *args (tuple):
                Positional arguments (unused).

            **kwargs (dict):
                Keyword arguments (unused).

        Returns:
            dict:
            Additional context to use when testing read-only actions.
        """
        return {
            'request': self.request,
        }

    def test_should_render_with_authenticated(self):
        """Testing EditReviewAction.should_render with authenticated user"""
        self.request.user = User.objects.get(username='doc')
        self.assertTrue(self.action.should_render(
            self._create_request_context()))

    def test_should_render_with_anonymous(self):
        """Testing EditReviewAction.should_render with authenticated user"""
        self.request.user = AnonymousUser()
        self.assertFalse(self.action.should_render(
            self._create_request_context()))


class ShipItActionTests(ReadOnlyActionTestsMixin, ActionsTestCase):
    """Unit tests for ShipItAction."""

    action = ShipItAction()
    fixtures = ['test_users']

    def _create_request_context(self, *args, **kwargs):
        """Create and return objects for use in the request context.

        Args:
            *args (tuple):
                Positional arguments (unused).

            **kwargs (dict):
                Keyword arguments (unused).

        Returns:
            dict:
            Additional context to use when testing read-only actions.
        """
        return {
            'request': self.request,
        }

    def test_should_render_with_authenticated(self):
        """Testing ShipItAction.should_render with authenticated user"""
        self.request.user = User.objects.get(username='doc')
        self.assertTrue(self.action.should_render(
            self._create_request_context()))

    def test_should_render_with_anonymous(self):
        """Testing ShipItAction.should_render with authenticated user"""
        self.request.user = AnonymousUser()
        self.assertFalse(self.action.should_render(
            self._create_request_context()))


class SubmitActionTests(ReadOnlyActionTestsMixin, ActionsTestCase):
    """Unit tests for SubmitAction."""

    action = SubmitAction()
    fixtures = ['test_users']

    def _create_request_context(self, public=True, user=None, *args, **kwargs):
        """Create and return objects for use in the request context.

        Args:
            public (bool, optional):
                Whether the review request should be public.

            user (django.contrib.auth.models.User, optional):
                The user to check visibility for.

            *args (tuple):
                Positional arguments (unused).

            **kwargs (dict):
                Keyword arguments (unused).

        Returns:
            dict:
            Additional context to use when testing read-only actions.
        """
        review_request = self.create_review_request(public=public)
        self.request.user = user or review_request.submitter

        return {
            'request': self.request,
            'review_request': review_request,
        }

    def test_should_render_with_published(self):
        """Testing SubmitAction.should_render with published review request"""
        self.assertTrue(self.action.should_render(
            self._create_request_context(public=True)))

    def test_should_render_with_unpublished(self):
        """Testing SubmitAction.should_render with unpublished review request
        """
        self.assertFalse(self.action.should_render(
            self._create_request_context(public=False)))


class UpdateMenuActionTests(ReadOnlyActionTestsMixin, ActionsTestCase):
    """Unit tests for UpdateMenuAction."""

    action = UpdateMenuAction()
    fixtures = ['test_users']

    def _create_request_context(self,
                                public=True,
                                status=ReviewRequest.PENDING_REVIEW,
                                user=None,
                                can_edit_reviewrequest=True,
                                *args, **kwargs):
        """Create and return objects for use in the request context.

        Args:
            public (bool, optional):
                Whether the review request should be public.

            status (unicode, optional):
                Review request status.

            user (django.contrib.auth.models.User, optional):
                The user to check visibility for.

            can_edit_reviewrequest (bool, optional):
                Whether the ``can_edit_reviewrequest`` permission should be
                set.

            *args (tuple):
                Positional arguments (unused).

            **kwargs (dict):
                Keyword arguments (unused).

        Returns:
            dict:
            Additional context to use when testing read-only actions.
        """
        review_request = self.create_review_request(public=public,
                                                    status=status)
        self.request.user = user or review_request.submitter

        return {
            'review_request': review_request,
            'request': self.request,
            'perms': {
                'reviews': {
                    'can_edit_reviewrequest': can_edit_reviewrequest,
                },
            },
        }

    def test_should_render_for_owner(self):
        """Testing UpdateMenuAction.should_render for owner of review request
        """
        self.assertTrue(self.action.should_render(
            self._create_request_context(can_edit_reviewrequest=False)))

    def test_should_render_for_user(self):
        """Testing UpdateMenuAction.should_render for normal user"""
        self.assertFalse(self.action.should_render(
            self._create_request_context(
                user=User.objects.create_user(username='test-user',
                                              email='user@example.com'),
                can_edit_reviewrequest=False)))

    def test_should_render_user_with_can_edit_reviewrequest(self):
        """Testing UpdateMenuAction.should_render for user with
        can_edit_reviewrequest permission
        """
        self.assertTrue(self.action.should_render(
            self._create_request_context(
                user=User.objects.create_user(username='test-user',
                                              email='user@example.com'))))

    def test_should_render_with_discarded(self):
        """Testing UpdateMenuAction.should_render with discarded review request
        """
        self.assertFalse(self.action.should_render(
            self._create_request_context(
                status=ReviewRequest.DISCARDED,
                can_edit_reviewrequest=False)))

    def test_should_render_with_submitted(self):
        """Testing UpdateMenuAction.should_render with submitted review request
        """
        self.assertFalse(self.action.should_render(
            self._create_request_context(
                status=ReviewRequest.SUBMITTED,
                can_edit_reviewrequest=False)))


class UploadDiffActionTests(ReadOnlyActionTestsMixin, ActionsTestCase):
    """Unit tests for UploadDiffAction."""

    action = UploadDiffAction()
    fixtures = ['test_users', 'test_scmtools']

    def _create_request_context(self, create_repository=True, user=None,
                                *args, **kwargs):
        """Create and return objects for use in the request context.

        Args:
            create_repository (bool, optional):
                Whether to create a repository for the review request.

            user (django.contrib.auth.models.User, optional):
                The user to check visibility for.

            *args (tuple):
                Positional arguments (unused).

            **kwargs (dict):
                Keyword arguments (unused).

        Returns:
            dict:
            Additional context to use when testing read-only actions.
        """
        review_request = self.create_review_request(
            create_repository=create_repository)
        self.request.user = user or review_request.submitter

        return {
            'review_request': review_request,
            'request': self.request,
        }

    def test_get_label_with_no_diffs(self):
        """Testing UploadDiffAction.get_label with no diffs"""
        review_request = self.create_review_request()
        self.request.user = review_request.submitter

        self.assertEqual(
            self.action.get_label({
                'review_request': review_request,
                'request': self.request,
            }),
            'Upload Diff')

    def test_get_label_with_diffs(self):
        """Testing UploadDiffAction.get_label with diffs"""
        review_request = self.create_review_request(create_repository=True)
        self.create_diffset(review_request)

        self.request.user = review_request.submitter

        self.assertEqual(
            self.action.get_label({
                'review_request': review_request,
                'request': self.request,
            }),
            'Update Diff')

    def test_should_render_with_repository(self):
        """Testing UploadDiffAction.should_render with repository"""
        self.assertTrue(self.action.should_render(
            self._create_request_context()))

    def test_should_render_without_repository(self):
        """Testing UploadDiffAction.should_render without repository"""
        self.assertFalse(self.action.should_render(
            self._create_request_context(create_repository=False)))
