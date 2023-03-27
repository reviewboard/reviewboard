from typing import Optional, TYPE_CHECKING

from django.contrib.auth.models import AnonymousUser, User
from django.template import Context
from django.test.client import RequestFactory
from django.urls.resolvers import ResolverMatch
from djblets.features.testing import override_feature_check
from djblets.siteconfig.models import SiteConfiguration
from djblets.testing.decorators import add_fixtures

from reviewboard.actions import actions_registry
from reviewboard.deprecation import RemovedInReviewBoard70Warning
from reviewboard.reviews.actions import (BaseReviewRequestAction,
                                         BaseReviewRequestMenuAction)
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
from reviewboard.reviews.features import unified_banner_feature
from reviewboard.reviews.models import ReviewRequest
from reviewboard.testing import TestCase


if TYPE_CHECKING:
    MixinParent = TestCase
else:
    MixinParent = object


class FooAction(BaseReviewRequestAction):
    action_id = 'foo-action'
    label = 'Foo Action'


class BarAction(BaseReviewRequestMenuAction):
    def __init__(self, action_id, child_actions=None):
        self.action_id = 'bar-' + action_id
        super().__init__(child_actions)


class TopLevelMenuAction(BaseReviewRequestMenuAction):
    action_id = 'top-level-menu-action'
    label = 'Top Level Menu Action'


class PoorlyCodedAction(BaseReviewRequestAction):
    def get_label(self, context):
        raise Exception


class ActionsTestCase(TestCase):
    """Test case for unit tests dealing with actions."""

    def tearDown(self) -> None:
        """Tear down the test case."""
        super().tearDown()
        actions_registry.reset()


class ReadOnlyActionTestsMixin(MixinParent):
    """Mixin for Review Board actions-related unit tests with read-only mode.

    This mixin is used to add read-only mode tests to action test cases.Using
    this mixin is especially important for actions that change visibility
    based on whether read-only mode is active. Actions that should always be
    visible can also be tested by setting ``read_only_always_show``.
    """

    def setUp(self) -> None:
        """Set up the test case."""
        super(ReadOnlyActionTestsMixin, self).setUp()

        self.request = RequestFactory().request()
        self.siteconfig = SiteConfiguration.objects.get_current()

    def shortDescription(self) -> str:
        """Return an updated description for a particular test.

        If the test has an ``action`` attribute set and contains ``<ACTION>``
        in the docstring, then ACTION will be replaced by the ``action_id``
        attribute of the
        :py:class:`~reviewboard.reviews.actions.BaseReviewRequestAction`.

        Returns:
            str:
            The description of the test.
        """
        desc = super(ReadOnlyActionTestsMixin, self).shortDescription()

        if self.action and getattr(self, self._testMethodName, False):
            desc = desc.replace('<ACTION>', type(self.action).__name__)

        return desc

    def _create_request_context(self, *args, **kwargs) -> Context:
        """Create and return objects for use in the request context.

        Args:
            *args (tuple):
                Positional arguments for use in subclasses.

            **kwargs (dict):
                Keyword arguments for use in subclasses.

        Returns:
            django.template.Context:
            Additional context to use when testing read-only actions.
        """
        return Context()

    def test_should_render_with_user_in_read_only(self) -> None:
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

        with override_feature_check(unified_banner_feature.feature_id, False):
            with self.siteconfig_settings(settings):
                if getattr(self, 'read_only_always_show', False):
                    self.assertTrue(
                        self.action.should_render(context=request_context))
                else:
                    self.assertFalse(
                        self.action.should_render(context=request_context))

    def test_should_render_with_superuser_in_read_only(self) -> None:
        """Testing <ACTION>.should_render with superuser in read-only mode"""
        self.request.user = User.objects.get(username='admin')

        # Turning on read-only mode prevents creation of some objects so call
        # _create_request_context first.
        request_context = self._create_request_context(user=self.request.user)

        settings = {
            'site_read_only': True,
        }

        with override_feature_check(unified_banner_feature.feature_id, False):
            with self.siteconfig_settings(settings):
                self.assertTrue(
                    self.action.should_render(context=request_context))


class ActionRegistrationTests(ActionsTestCase):
    """Unit tests for legacy action registration.

    Deprecated:
        6.0:
        This can go away once we remove the legacy actions.
    """

    deprecation_message = (
        'BaseReviewRequestAction is deprecated and will be removed in '
        'Review Board 7.0. Please update your code to use '
        'reviewboard.actions.base.BaseAction')

    def test_action_register_methods(self) -> None:
        """Testing BaseReviewRequestAction.register and unregister"""
        with self.assertWarns(RemovedInReviewBoard70Warning,
                              self.deprecation_message):
            foo_action = FooAction()
            foo_action.register()

        self.assertEqual(actions_registry.get('action_id', 'foo-action'),
                         foo_action)

        foo_action.unregister()

        self.assertIsNone(actions_registry.get('action_id', 'foo-action'))

    def test_action_register_methods_with_parent(self) -> None:
        """Testing BaseReviewRequestAction.register and unregister with
        parent
        """
        with self.assertWarns(RemovedInReviewBoard70Warning,
                              self.deprecation_message):
            bar_action = BarAction('action-1')
            foo_action = FooAction()

        bar_action.register()
        foo_action.register(bar_action)

        self.assertEqual(actions_registry.get('action_id', 'foo-action'),
                         foo_action)
        self.assertEqual(foo_action.parent_action, bar_action)
        self.assertEqual(bar_action.child_actions, [foo_action])

        foo_action.unregister()

        self.assertIsNone(actions_registry.get('action_id', 'foo-action'))
        self.assertIsNone(foo_action.parent_action)
        self.assertEqual(bar_action.child_actions, [])

    def test_menuaction_register_methods(self) -> None:
        """Testing BaseReviewRequestMenuAction.register and unregister"""
        with self.assertWarns(RemovedInReviewBoard70Warning,
                              self.deprecation_message):
            foo_action = FooAction()
            bar_action = BarAction('action-1', [foo_action])

        bar_action.register()

        self.assertEqual(actions_registry.get('action_id', 'foo-action'),
                         foo_action)
        self.assertEqual(actions_registry.get('action_id', 'bar-action-1'),
                         bar_action)
        self.assertEqual(foo_action.parent_action, bar_action)
        self.assertEqual(bar_action.child_actions, [foo_action])

        bar_action.unregister()

        self.assertIsNone(actions_registry.get('action_id', 'foo-action'))
        self.assertIsNone(actions_registry.get('action_id', 'bar-action-1'))
        self.assertIsNone(foo_action.parent_action)
        self.assertEqual(bar_action.child_actions, [])

    def test_menuaction_register_methods_with_parent(self) -> None:
        """Testing BaseReviewRequestMenuAction.register and unregister with
        parent
        """
        with self.assertWarns(RemovedInReviewBoard70Warning,
                              self.deprecation_message):
            foo_action = FooAction()
            bar_action = BarAction('action-1', [foo_action])
            toplevel_action = TopLevelMenuAction()

        toplevel_action.register()

        bar_action.register(toplevel_action)

        self.assertEqual(actions_registry.get('action_id', 'foo-action'),
                         foo_action)
        self.assertEqual(actions_registry.get('action_id', 'bar-action-1'),
                         bar_action)
        self.assertEqual(toplevel_action.child_actions, [bar_action])
        self.assertEqual(bar_action.parent_action, toplevel_action)
        self.assertEqual(foo_action.parent_action, bar_action)
        self.assertEqual(bar_action.child_actions, [foo_action])

        bar_action.unregister()

        self.assertIsNone(actions_registry.get('action_id', 'foo-action'))
        self.assertIsNone(actions_registry.get('action_id', 'bar-action-1'))
        self.assertIsNone(foo_action.parent_action)
        self.assertEqual(bar_action.child_actions, [])
        self.assertEqual(toplevel_action.child_actions, [])
        self.assertIsNone(bar_action.parent_action)

    def test_register_max_depth_exceeded(self) -> None:
        """Testing BaseReviewRequestAction.register with max depth exceeded"""
        with self.assertWarns(RemovedInReviewBoard70Warning,
                              self.deprecation_message):
            foo_action = FooAction()
            bar_action1 = BarAction('action-1', [foo_action])
            bar_action2 = BarAction('action-2', [bar_action1])
            bar_action3 = BarAction('action-3', [bar_action2])

        with self.assertRaises(DepthLimitExceededError):
            bar_action3.register()


class AddGeneralCommentActionTests(ReadOnlyActionTestsMixin, ActionsTestCase):
    """Unit tests for AddGeneralCommentAction."""

    action = AddGeneralCommentAction()
    fixtures = ['test_users']

    def _create_request_context(
        self,
        user: Optional[User] = None,
        url_name: str = 'review-request-detail',
        *args,
        **kwargs,
    ) -> Context:
        """Create and return objects for use in the request context.

        Args:
            user (django.contrib.auth.models.User, optional):
                The user to run the request.

            url_name (str, optional):
                The URL name to fake on the resolver.

            *args (tuple):
                Positional arguments (unused).

            **kwargs (dict):
                Keyword arguments (unused).

        Returns:
            django.template.Context:
            Additional context to use when testing read-only actions.
        """
        self.request.resolver_match = ResolverMatch(
            lambda: None, tuple(), {}, url_name=url_name)

        return Context({
            'request': self.create_http_request(user=user, url_name=url_name),
        })

    def test_should_render_with_authenticated(self) -> None:
        """Testing AddGeneralCommentAction.should_render with authenticated
        user
        """
        with override_feature_check(unified_banner_feature.feature_id, False):
            self.request.user = User.objects.get(username='doc')
            self.assertTrue(
                self.action.should_render(
                    context=self._create_request_context(
                        User.objects.get(username='doc'))))

    def test_should_render_with_anonymous(self) -> None:
        """Testing AddGeneralCommentAction.should_render with authenticated
        user
        """
        with override_feature_check(unified_banner_feature.feature_id, False):
            self.assertFalse(
                self.action.should_render(context=self._create_request_context()))


class CloseMenuActionTests(ReadOnlyActionTestsMixin, ActionsTestCase):
    """Unit tests for CloseMenuAction."""

    action = CloseMenuAction()
    fixtures = ['test_users']

    def _create_request_context(
        self,
        url_name: str = 'review-request-detail',
        can_change_status: bool = True,
        public: bool = True,
        status: str = ReviewRequest.PENDING_REVIEW,
        user: Optional[User] = None,
    ) -> Context:
        """Create and return objects for use in the request context.

        Args:
            url_name (str, optional):
                The URL name to fake on the resolver.

            can_change_status (bool, optional):
                Whether the ``can_change_status`` permission should be set.

            public (bool, optional):
                Whether the review request should be public.

            status (str, optional):
                The status for the review request.

            user (django.contrib.auth.models.User, optional):
                An optional user to set as the owner of the request.

            *args (tuple):
                Additional positional arguments (unused).

            **kwargs (dict):
                Additional keyword arguments (unused).

        Returns:
            django.template.Context:
            Additional context to use when testing read-only actions.
        """
        review_request = self.create_review_request(
            public=public, status=status)
        request = self.create_http_request(
            user=user or review_request.submitter,
            url_name=url_name)

        return Context({
            'review_request': review_request,
            'request': request,
            'perms': {
                'reviews': {
                    'can_change_status': can_change_status,
                },
            },
        })

    def test_should_render_for_owner(self) -> None:
        """Testing CloseMenuAction.should_render for owner of review request"""
        self.assertTrue(self.action.should_render(
            context=self._create_request_context()))

    def test_should_render_for_owner_unpublished(self) -> None:
        """Testing CloseMenuAction.should_render for owner of review
        unpublished review request
        """
        self.assertTrue(self.action.should_render(
            context=self._create_request_context(
                public=False)))

    def test_should_render_for_user(self) -> None:
        """Testing CloseMenuAction.should_render for normal user"""
        self.assertFalse(self.action.should_render(
            context=self._create_request_context(
                can_change_status=False,
                user=self.create_user())))

    def test_should_render_user_with_can_change_status(self) -> None:
        """Testing CloseMenuAction.should_render for user with
        can_change_status permission
        """
        self.assertTrue(self.action.should_render(
            context=self._create_request_context(
                can_change_status=True,
                user=self.create_user())))

    def test_should_render_user_with_can_change_status_and_unpublished(
        self,
    ) -> None:
        """Testing CloseMenuAction.should_render for user with
        can_change_status permission and unpublished review request
        """
        self.assertFalse(self.action.should_render(
            context=self._create_request_context(
                can_change_status=True,
                public=False,
                user=self.create_user())))

    def test_should_render_with_discarded(self) -> None:
        """Testing CloseMenuAction.should_render with discarded review request
        """
        self.assertFalse(self.action.should_render(
            context=self._create_request_context(
                status=ReviewRequest.DISCARDED)))

    def test_should_render_with_submitted(self) -> None:
        """Testing CloseMenuAction.should_render with submitted review request
        """
        self.assertFalse(self.action.should_render(
            context=self._create_request_context(
                status=ReviewRequest.SUBMITTED)))


class DeleteActionTests(ReadOnlyActionTestsMixin, ActionsTestCase):
    """Unit tests for DeleteAction."""

    fixtures = ['test_users']
    action = DeleteAction()

    def _create_request_context(
        self,
        user: Optional[User] = None,
        url_name: str = 'review-request-detail',
        delete_reviewrequest: bool = True,
        *args,
        **kwargs,
    ) -> Context:
        """Create and return objects for use in the request context.

        Args:
            user (django.contrib.auth.models.User, optional):
                The user to run the request.

            url_name (str, optional):
                The URL name to fake on the resolver.

            delete_reviewrequest (bool, optional):
                Whether the resulting context should include the
                ``delete_reviewrequest`` permission.

            *args (tuple):
                Positional arguments (unused).

            **kwargs (dict):
                Keyword arguments (unused).

        Returns:
            django.template.Context:
            Additional context to use when testing read-only actions.
        """
        return Context({
            'request': self.create_http_request(user=user, url_name=url_name),
            'perms': {
                'reviews': {
                    'delete_reviewrequest': delete_reviewrequest,
                },
            },
        })

    def test_should_render_with_published(self) -> None:
        """Testing DeleteAction.should_render with standard user"""
        self.assertFalse(self.action.should_render(
            context=self._create_request_context(
                user=self.create_user(),
                delete_reviewrequest=False)))

    def test_should_render_with_permission(self) -> None:
        """Testing SubmitAction.should_render with delete_reviewrequest
        permission
        """
        self.assertTrue(self.action.should_render(
            context=self._create_request_context(
                user=self.create_user())))


class DownloadDiffActionTests(ReadOnlyActionTestsMixin, ActionsTestCase):
    """Unit tests for DownloadDiffAction."""

    action = DownloadDiffAction()
    fixtures = ['test_users']
    read_only_always_show = True

    def _create_request_context(
        self,
        review_request: Optional[ReviewRequest] = None,
        url_name: str = 'view-diff',
        with_local_site: bool = False,
        *args,
        **kwargs,
    ) -> Context:
        """Create and return objects for use in the request context.

        Args:
            review_request (reviewboard.reviews.models.review_request.
                            ReviewRequest, optional):
                The review request to use. If not specified, one will be
                created.

            url_name (str, optional):
                The URL name to fake on the resolver.

            with_local_site (bool, optional):
                Whether to use a local site.

            *args (tuple):
                Positional arguments (unused).

            **kwargs (dict):
                Keyword arguments (unused).

        Returns:
            django.template.Context:
            Additional context to use when testing read-only actions.
        """
        if not review_request:
            review_request = self.create_review_request(
                with_local_site=with_local_site)

        return Context({
            'request': self.create_http_request(
                user=self.create_user(),
                with_local_site=with_local_site,
                url_name=url_name),
            'review_request': review_request,
        })

    def test_get_url_on_diff_viewer(self) -> None:
        """Testing DownloadDiffAction.get_url on diff viewer page"""
        self.assertEqual(
            self.action.get_url(context=self._create_request_context()),
            'raw/')

    def test_get_url_on_interdiff(self) -> None:
        """Testing DownloadDiffAction.get_url on diff viewer interdiff page"""
        self.assertEqual(
            self.action.get_url(context=self._create_request_context(
                url_name='view-interdiff')),
            'raw/')

    def test_get_url_on_diff_viewer_revision(self) -> None:
        """Testing DownloadDiffAction.get_url on diff viewer revision page"""
        self.assertEqual(
            self.action.get_url(context=self._create_request_context(
                url_name='view-diff-revision')),
            'raw/')

    def test_get_url_on_review_request(self) -> None:
        """Testing DownloadDiffAction.get_url on review request page"""
        review_request = self.create_review_request()

        self.assertEqual(
            self.action.get_url(context=self._create_request_context(
                review_request=review_request,
                url_name='review-request-detail')),
            '/r/%s/diff/raw/' % review_request.display_id)

    @add_fixtures(['test_site'])
    def test_get_url_on_review_request_with_local_site(self) -> None:
        """Testing DownloadDiffAction.get_url on review request page with
        LocalSite
        """
        review_request = self.create_review_request(id=123,
                                                    with_local_site=True)

        self.assertEqual(
            self.action.get_url(context=self._create_request_context(
                review_request=review_request,
                url_name='review-request-detail',
                with_local_site=True)),
            '/s/%s/r/%s/diff/raw/' % (self.local_site_name,
                                      review_request.display_id))

    def test_get_hidden_on_diff_viewer(self) -> None:
        """Testing DownloadDiffAction.get_visible on diff viewer page"""
        self.assertTrue(self.action.get_visible(
            context=self._create_request_context(url_name='view-diff')))

    def test_get_hidden_on_interdiff(self) -> None:
        """Testing DownloadDiffAction.get_visible on diff viewer interdiff page
        """
        self.assertFalse(self.action.get_visible(
            context=self._create_request_context(url_name='view-interdiff')))

    def test_get_hidden_on_diff_viewer_revision(self) -> None:
        """Testing DownloadDiffAction.get_visible on diff viewer revision page
        """
        self.assertTrue(self.action.get_visible(
            context=self._create_request_context(
                url_name='view-diff-revision')))

    def test_get_hidden_on_review_request(self) -> None:
        """Testing DownloadDiffAction.get_visible on diff viewer revision page
        """
        self.assertTrue(self.action.get_visible(
            context=self._create_request_context(
                url_name='review-request-detail')))

    def test_should_render_on_diff_viewer(self) -> None:
        """Testing DownloadDiffAction.should_render on diff viewer page"""
        self.assertTrue(self.action.should_render(
            context=self._create_request_context(
                url_name='view-diff')))

    def test_should_render_on_interdiff(self) -> None:
        """Testing DownloadDiffAction.should_render on diff viewer interdiff
        page
        """
        self.assertTrue(self.action.should_render(
            context=self._create_request_context(
                url_name='view-diff-revision')))

    def test_should_render_on_diff_viewer_revision(self) -> None:
        """Testing DownloadDiffAction.should_render on diff viewer revision
        page
        """
        self.assertTrue(self.action.should_render(
            context=self._create_request_context(
                url_name='view-diff-revision')))

    @add_fixtures(['test_scmtools'])
    def test_should_render_on_review_request_with_repository(self) -> None:
        """Testing DownloadDiffAction.should_render on review request page
        with repository but no diff
        """
        review_request = self.create_review_request(create_repository=True)

        self.assertFalse(self.action.should_render(
            context=self._create_request_context(
                review_request=review_request,
                url_name='review-request-detail')))

    @add_fixtures(['test_scmtools'])
    def test_should_render_on_review_request_with_repository_and_diff(
        self,
    ) -> None:
        """Testing DownloadDiffAction.should_render on review request page
        with repository and diff history
        """
        review_request = self.create_review_request(create_repository=True)
        self.create_diffset(review_request)

        self.assertTrue(self.action.should_render(
            context=self._create_request_context(
                review_request=review_request,
                url_name='review-request-detail')))

    @add_fixtures(['test_scmtools'])
    def test_should_render_on_review_request_without_repository(self) -> None:
        """Testing DownloadDiffAction.should_render on review request page
        without repository
        """
        self.assertFalse(self.action.should_render(
            context=self._create_request_context(
                url_name='review-request-detail')))


class EditReviewActionTests(ReadOnlyActionTestsMixin, ActionsTestCase):
    """Unit tests for EditReviewAction."""

    action = EditReviewAction()
    fixtures = ['test_users']

    def _create_request_context(
        self,
        url_name: str = 'review-request-detail',
        user: Optional[User] = None,
        *args,
        **kwargs,
    ) -> Context:
        """Create and return objects for use in the request context.

        Args:
            url_name (str, optional):
                The URL name to fake on the resolver.

            user (django.contrib.auth.models.User, optional):
                The user to set on the request.

            *args (tuple):
                Positional arguments (unused).

            **kwargs (dict):
                Keyword arguments (unused).

        Returns:
            django.template.Context:
            Additional context to use when testing read-only actions.
        """
        return Context({
            'request': self.create_http_request(url_name=url_name,
                                                user=user),
        })

    def test_should_render_with_authenticated(self) -> None:
        """Testing EditReviewAction.should_render with authenticated user"""
        with override_feature_check(unified_banner_feature.feature_id, False):
            self.assertTrue(self.action.should_render(
                context=self._create_request_context(
                    user=User.objects.get(username='doc'))))

    def test_should_render_with_anonymous(self) -> None:
        """Testing EditReviewAction.should_render with authenticated user"""
        with override_feature_check(unified_banner_feature.feature_id, False):
            self.assertFalse(self.action.should_render(
                context=self._create_request_context()))

    def test_should_render_with_user_in_read_only(self) -> None:
        """Testing EditReviewAction.should_render with authenticated user in
        read-only mode
        """
        with override_feature_check(unified_banner_feature.feature_id, False):
            super().test_should_render_with_user_in_read_only()

    def test_should_render_with_superuser_in_read_only(self) -> None:
        """Testing EditReviewAction.should_render with superuser in read-only
        mode
        """
        with override_feature_check(unified_banner_feature.feature_id, False):
            super().test_should_render_with_superuser_in_read_only()


class ShipItActionTests(ReadOnlyActionTestsMixin, ActionsTestCase):
    """Unit tests for ShipItAction."""

    action = ShipItAction()
    fixtures = ['test_users']

    def _create_request_context(
        self,
        url_name: str = 'review-request-detail',
        user: Optional[User] = None,
        *args,
        **kwargs,
    ) -> Context:
        """Create and return objects for use in the request context.

        Args:
            url_name (str, optional):
                The URL name to fake on the resolver.

            user (django.contrib.auth.models.User, optional):
                The user to set on the request.

            *args (tuple):
                Positional arguments (unused).

            **kwargs (dict):
                Keyword arguments (unused).

        Returns:
            django.template.Context:
            Additional context to use when testing read-only actions.
        """
        return Context({
            'request': self.create_http_request(url_name=url_name,
                                                user=user),
        })

    def test_should_render_with_authenticated(self) -> None:
        """Testing ShipItAction.should_render with authenticated user"""
        with override_feature_check(unified_banner_feature.feature_id, False):
            self.assertTrue(self.action.should_render(
                context=self._create_request_context(
                    user=User.objects.get(username='doc'))))

    def test_should_render_with_anonymous(self) -> None:
        """Testing ShipItAction.should_render with authenticated user"""
        with override_feature_check(unified_banner_feature.feature_id, False):
            self.assertFalse(self.action.should_render(
                context=self._create_request_context()))

    def test_should_render_with_user_in_read_only(self) -> None:
        """Testing ShipItAction.should_render with authenticated user in
        read-only mode
        """
        with override_feature_check(unified_banner_feature.feature_id, False):
            super().test_should_render_with_user_in_read_only()

    def test_should_render_with_superuser_in_read_only(self) -> None:
        """Testing ShipItAction.should_render with superuser in read-only
        mode
        """
        with override_feature_check(unified_banner_feature.feature_id, False):
            super().test_should_render_with_superuser_in_read_only()


class SubmitActionTests(ReadOnlyActionTestsMixin, ActionsTestCase):
    """Unit tests for SubmitAction."""

    action = SubmitAction()
    fixtures = ['test_users']

    def _create_request_context(
        self,
        url_name: str = 'review-request-detail',
        public: bool = True,
        user: Optional[User] = None,
        *args,
        **kwargs,
    ) -> Context:
        """Create and return objects for use in the request context.

        Args:
            url_name (str, optional):
                The URL name to fake on the resolver.

            public (bool, optional):
                Whether the review request should be public.

            user (django.contrib.auth.models.User, optional):
                The user to check visibility for.

            *args (tuple):
                Positional arguments (unused).

            **kwargs (dict):
                Keyword arguments (unused).

        Returns:
            django.template.Context:
            Additional context to use when testing read-only actions.
        """
        review_request = self.create_review_request(public=public)

        return Context({
            'request': self.create_http_request(
                user=user or review_request.submitter,
                url_name=url_name),
            'review_request': review_request,
        })

    def test_should_render_with_published(self) -> None:
        """Testing SubmitAction.should_render with published review request"""
        self.assertTrue(self.action.should_render(
            context=self._create_request_context(public=True)))

    def test_should_render_with_unpublished(self) -> None:
        """Testing SubmitAction.should_render with unpublished review request
        """
        self.assertFalse(self.action.should_render(
            context=self._create_request_context(public=False)))


class UpdateMenuActionTests(ReadOnlyActionTestsMixin, ActionsTestCase):
    """Unit tests for UpdateMenuAction."""

    action = UpdateMenuAction()
    fixtures = ['test_users']

    def _create_request_context(
        self,
        url_name: str = 'review-request-detail',
        public: bool = True,
        status: str = ReviewRequest.PENDING_REVIEW,
        user: Optional[User] = None,
        can_edit_reviewrequest: bool = True,
        *args,
        **kwargs,
    ) -> Context:
        """Create and return objects for use in the request context.

        Args:
            url_name (str, optional):
                The URL name to fake on the resolver.

            public (bool, optional):
                Whether the review request should be public.

            status (str, optional):
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
            django.template.Context:
            Additional context to use when testing read-only actions.
        """
        review_request = self.create_review_request(public=public,
                                                    status=status)

        return Context({
            'review_request': review_request,
            'request': self.create_http_request(
                user=user or review_request.submitter,
                url_name=url_name),
            'perms': {
                'reviews': {
                    'can_edit_reviewrequest': can_edit_reviewrequest,
                },
            },
        })

    def test_should_render_for_owner(self) -> None:
        """Testing UpdateMenuAction.should_render for owner of review request
        """
        self.assertTrue(self.action.should_render(
            context=self._create_request_context(
                can_edit_reviewrequest=False)))

    def test_should_render_for_user(self) -> None:
        """Testing UpdateMenuAction.should_render for normal user"""
        self.assertFalse(self.action.should_render(
            context=self._create_request_context(
                user=self.create_user(),
                can_edit_reviewrequest=False)))

    def test_should_render_user_with_can_edit_reviewrequest(self) -> None:
        """Testing UpdateMenuAction.should_render for user with
        can_edit_reviewrequest permission
        """
        self.assertTrue(self.action.should_render(
            context=self._create_request_context(user=self.create_user())))

    def test_should_render_with_discarded(self) -> None:
        """Testing UpdateMenuAction.should_render with discarded review request
        """
        self.assertFalse(self.action.should_render(
            context=self._create_request_context(
                status=ReviewRequest.DISCARDED,
                can_edit_reviewrequest=False)))

    def test_should_render_with_submitted(self) -> None:
        """Testing UpdateMenuAction.should_render with submitted review request
        """
        self.assertFalse(self.action.should_render(
            context=self._create_request_context(
                status=ReviewRequest.SUBMITTED,
                can_edit_reviewrequest=False)))


class UploadDiffActionTests(ReadOnlyActionTestsMixin, ActionsTestCase):
    """Unit tests for UploadDiffAction."""

    action = UploadDiffAction()
    fixtures = ['test_users', 'test_scmtools']

    def _create_request_context(
        self,
        url_name: str = 'review-request-detail',
        can_edit_reviewrequest: bool = True,
        create_repository: bool = True,
        user: Optional[User] = None,
        *args,
        **kwargs,
    ) -> Context:
        """Create and return objects for use in the request context.

        Args:
            url_name (str, optional):
                The URL name to fake on the resolver.

            create_repository (bool, optional):
                Whether to create a repository for the review request.

            user (django.contrib.auth.models.User, optional):
                The user to check visibility for.

            *args (tuple):
                Positional arguments (unused).

            **kwargs (dict):
                Keyword arguments (unused).

        Returns:
            django.template.Context:
            Additional context to use when testing read-only actions.
        """
        review_request = self.create_review_request(
            create_repository=create_repository)

        return Context({
            'review_request': review_request,
            'request': self.create_http_request(
                user=user or review_request.submitter,
                url_name=url_name),
            'perms': {
                'reviews': {
                    'can_edit_reviewrequest': can_edit_reviewrequest,
                },
            },
        })

    def test_get_label_with_no_diffs(self) -> None:
        """Testing UploadDiffAction.get_label with no diffs"""
        review_request = self.create_review_request()
        self.request.user = review_request.submitter

        self.assertEqual(
            self.action.get_label(context=Context({
                'review_request': review_request,
                'request': self.request,
            })),
            'Upload Diff')

    def test_get_label_with_diffs(self) -> None:
        """Testing UploadDiffAction.get_label with diffs"""
        review_request = self.create_review_request(create_repository=True)
        self.create_diffset(review_request)

        self.request.user = review_request.submitter

        self.assertEqual(
            self.action.get_label(context=Context({
                'review_request': review_request,
                'request': self.request,
            })),
            'Update Diff')

    def test_should_render_with_repository(self) -> None:
        """Testing UploadDiffAction.should_render with repository"""
        self.assertTrue(self.action.should_render(
            context=self._create_request_context()))

    def test_should_render_without_repository(self) -> None:
        """Testing UploadDiffAction.should_render without repository"""
        self.assertFalse(self.action.should_render(
            context=self._create_request_context(create_repository=False)))
