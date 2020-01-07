from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.core import mail
from django.template import Context, Template
from django.test.client import RequestFactory
from djblets.avatars.tests import DummyAvatarService
from djblets.extensions.extension import ExtensionInfo
from djblets.extensions.manager import ExtensionManager
from djblets.extensions.models import RegisteredExtension
from djblets.features.testing import override_feature_check
from djblets.mail.utils import build_email_address_for_user
from djblets.registries.errors import AlreadyRegisteredError, RegistrationError
from kgb import SpyAgency
from mock import Mock

from reviewboard.admin.widgets import (BaseAdminWidget,
                                       Widget,
                                       admin_widgets_registry)
from reviewboard.avatars import avatar_services
from reviewboard.deprecation import RemovedInReviewBoard50Warning
from reviewboard.extensions.base import Extension
from reviewboard.extensions.hooks import (AdminWidgetHook,
                                          APIExtraDataAccessHook,
                                          AvatarServiceHook,
                                          BaseReviewRequestActionHook,
                                          CommentDetailDisplayHook,
                                          DiffViewerActionHook,
                                          EmailHook,
                                          HeaderActionHook,
                                          HeaderDropdownActionHook,
                                          HostingServiceHook,
                                          NavigationBarHook,
                                          ReviewPublishedEmailHook,
                                          ReviewReplyPublishedEmailHook,
                                          ReviewRequestActionHook,
                                          ReviewRequestApprovalHook,
                                          ReviewRequestClosedEmailHook,
                                          ReviewRequestDropdownActionHook,
                                          ReviewRequestFieldSetsHook,
                                          ReviewRequestPublishedEmailHook,
                                          UserInfoboxHook,
                                          WebAPICapabilitiesHook)
from reviewboard.hostingsvcs.service import (get_hosting_service,
                                             HostingService)
from reviewboard.reviews.actions import (BaseReviewRequestAction,
                                         BaseReviewRequestMenuAction,
                                         clear_all_actions)
from reviewboard.scmtools.errors import FileNotFoundError
from reviewboard.reviews.features import ClassBasedActionsFeature
from reviewboard.reviews.models.review_request import ReviewRequest
from reviewboard.reviews.fields import (BaseReviewRequestField,
                                        BaseReviewRequestFieldSet)
from reviewboard.reviews.signals import (review_request_published,
                                         review_published, reply_published,
                                         review_request_closed)
from reviewboard.site.urlresolvers import local_site_reverse
from reviewboard.testing.testcase import TestCase
from reviewboard.webapi.base import ExtraDataAccessLevel, WebAPIResource
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import root_item_mimetype
from reviewboard.webapi.tests.urls import get_root_url


class ExtensionManagerMixin(object):
    """Mixin used to setup a default ExtensionManager for tests."""

    def setUp(self):
        super(ExtensionManagerMixin, self).setUp()
        self.manager = ExtensionManager('')


class DummyExtension(Extension):
    registration = RegisteredExtension()


class ActionHookTests(ExtensionManagerMixin, TestCase):
    """Tests the action hooks in reviewboard.extensions.hooks."""

    class _TestAction(BaseReviewRequestAction):
        action_id = 'test-action'
        label = 'Test Action'

    class _TestMenuAction(BaseReviewRequestMenuAction):
        action_id = 'test-menu-instance-action'
        label = 'Menu Instance'

    def setUp(self):
        super(ActionHookTests, self).setUp()

        self.extension = DummyExtension(extension_manager=self.manager)

    def tearDown(self):
        super(ActionHookTests, self).tearDown()

        self.extension.shutdown()
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
        """Testing that action hook __init__ raises a KeyError"""
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
        """Testing that BaseReviewRequestActionHook __init__ raises a
        ValueError"""
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
        """Testing that ReviewRequestDropdownActionHook __init__ raises a
        KeyError"""
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
                ('<a class="menu-title" href="#" id="test-menu-instance-action">'
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
                    ('<a class="menu-title" href="#" id="test-menu-dict-action">'
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

    def test_header_hooks(self):
        """Testing HeaderActionHook"""
        self._test_action_hook('header_action_hooks', HeaderActionHook)

    def test_header_dropdown_action_hook(self):
        """Testing HeaderDropdownActionHook"""
        self._test_dropdown_action_hook('header_dropdown_action_hooks',
                                        HeaderDropdownActionHook)

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


class NavigationBarHookTests(TestCase):
    """Tests the navigation bar hooks."""
    def setUp(self):
        super(NavigationBarHookTests, self).setUp()

        manager = ExtensionManager('')
        self.extension = DummyExtension(extension_manager=manager)

    def tearDown(self):
        super(NavigationBarHookTests, self).tearDown()

        self.extension.shutdown()

    def test_navigation_bar_hooks(self):
        """Testing navigation entry extension hooks"""
        entry = {
            'label': 'Test Nav Entry',
            'url': 'foo-url',
        }

        hook = NavigationBarHook(extension=self.extension, entries=[entry])

        request = self.client.request()
        request.user = User(username='text')

        context = Context({
            'request': request,
            'local_site_name': 'test-site',
        })
        entries = hook.get_entries(context)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0], entry)

        t = Template(
            '{% load rb_extensions %}'
            '{% navigation_bar_hooks %}')

        self.assertEqual(t.render(context).strip(),
                         '<li><a href="%(url)s">%(label)s</a></li>' % entry)

    def test_navigation_bar_hooks_with_is_enabled_for_true(self):
        """Testing NavigationBarHook.is_enabled_for and returns true"""
        def is_enabled_for(**kwargs):
            self.assertEqual(kwargs['user'], request.user)
            self.assertEqual(kwargs['request'], request)
            self.assertEqual(kwargs['local_site_name'], 'test-site')

            return True

        entry = {
            'label': 'Test Nav Entry',
            'url': 'foo-url',
        }

        hook = NavigationBarHook(extension=self.extension, entries=[entry],
                                 is_enabled_for=is_enabled_for)

        request = self.client.request()
        request.user = User(username='text')

        context = Context({
            'request': request,
            'local_site_name': 'test-site',
        })
        entries = hook.get_entries(context)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0], entry)

        t = Template(
            '{% load rb_extensions %}'
            '{% navigation_bar_hooks %}')

        self.assertEqual(t.render(context).strip(),
                         '<li><a href="%(url)s">%(label)s</a></li>' % entry)

    def test_navigation_bar_hooks_with_is_enabled_for_false(self):
        """Testing NavigationBarHook.is_enabled_for and returns false"""
        def is_enabled_for(**kwargs):
            self.assertEqual(kwargs['user'], request.user)
            self.assertEqual(kwargs['request'], request)
            self.assertEqual(kwargs['local_site_name'], 'test-site')

            return False

        entry = {
            'label': 'Test Nav Entry',
            'url': 'foo-url',
        }

        hook = NavigationBarHook(extension=self.extension, entries=[entry],
                                 is_enabled_for=is_enabled_for)

        request = self.client.request()
        request.user = User(username='text')

        context = Context({
            'request': request,
            'local_site_name': 'test-site',
        })
        entries = hook.get_entries(context)
        self.assertEqual(len(entries), 0)

        t = Template(
            '{% load rb_extensions %}'
            '{% navigation_bar_hooks %}')

        self.assertEqual(t.render(context).strip(), '')

    def test_navigation_bar_hooks_with_url_name(self):
        "Testing navigation entry extension hooks with url names"""
        entry = {
            'label': 'Test Nav Entry',
            'url_name': 'dashboard',
        }

        hook = NavigationBarHook(extension=self.extension, entries=[entry])

        request = self.client.request()
        request.user = User(username='text')

        context = Context({
            'request': request,
            'local_site_name': 'test-site',
        })
        entries = hook.get_entries(context)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0], entry)

        t = Template(
            '{% load rb_extensions %}'
            '{% navigation_bar_hooks %}')

        self.assertEqual(
            t.render(context).strip(),
            '<li><a href="%(url)s">%(label)s</a></li>' % {
                'label': entry['label'],
                'url': '/dashboard/',
            })


class TestService(HostingService):
    hosting_service_id = 'test-service'
    name = 'Test Service'

    def get_file(self, repository, path, revision, *args, **kwargs):
        """Return the specified file from the repository.

        If the given file path is ``/invalid-path``, the file will be assumed
        to not exist and
        :py:exc:`reviewboard.scmtools.errors.FileNotFoundError` will be raised.

        Args:
            repository (reviewboard.scmtools.models.Repository):
                The repository the file belongs to.

            path (unicode):
                The file path.

            revision (unicode):
                The file revision.

            *args (tuple):
                Additional positional arguments.

            **kwargs (dict):
                Additional keyword arguments.

        Returns:
            unicode: The file data.

        Raises:
            reviewboard.scmtools.errors.FileNotFoundError:
                Raised if the file does not exist.
        """
        if path == '/invalid-path':
            raise FileNotFoundError(path, revision)

        return super(TestService, self).get_file(repository, path, revision,
                                                 *args, **kwargs)

    def get_file_exists(self, repository, path, revision, *args, **kwargs):
        """Return the specified file from the repository.

        If the given file path is ``/invalid-path``, the file will
        be assumed to not exist.

        Args:
            repository (reviewboard.scmtools.models.Repository):
                The repository the file belongs to.

            path (unicode):
                The file path.

            revision (unicode):
                The file revision.

            *args (tuple):
                Additional positional arguments.

            **kwargs (dict):
                Additional keyword arguments.

        Returns:
            bool: Whether or not the file exists.
        """
        if path == '/invalid-path':
            return False

        return super(TestService, self).get_file_exists(
            repository, path, revision, *args, **kwargs)


class HostingServiceHookTests(ExtensionManagerMixin, TestCase):
    """Testing HostingServiceHook."""

    def setUp(self):
        super(HostingServiceHookTests, self).setUp()

        self.extension = DummyExtension(extension_manager=self.manager)

    def tearDown(self):
        super(HostingServiceHookTests, self).tearDown()

        self.extension.shutdown()

    def test_register(self):
        """Testing HostingServiceHook initializing"""
        HostingServiceHook(self.extension, TestService)

        self.assertEqual(get_hosting_service('test-service'),
                         TestService)

    def test_register_without_hosting_service_id(self):
        """Testing HostingServiceHook initializing without hosting_service_id
        """
        class TestServiceWithoutID(TestService):
            hosting_service_id = None

        message = 'TestServiceWithoutID.hosting_service_id must be set.'

        with self.assertRaisesMessage(ValueError, message):
            HostingServiceHook(self.extension, TestServiceWithoutID)

    def test_unregister(self):
        """Testing HostingServiceHook uninitializing"""
        hook = HostingServiceHook(self.extension, TestService)
        hook.disable_hook()

        self.assertIsNone(get_hosting_service('test-service'))


class MyLegacyAdminWidget(Widget):
    widget_id = 'legacy-test-widget'
    title = 'Legacy Testing Widget'


class MyAdminWidget(BaseAdminWidget):
    widget_id = 'test-widget'
    name = 'Testing Widget'


class AdminWidgetHookTests(ExtensionManagerMixin, TestCase):
    """Testing AdminWidgetHook."""

    def setUp(self):
        super(AdminWidgetHookTests, self).setUp()

        self.extension = DummyExtension(extension_manager=self.manager)

    def tearDown(self):
        super(AdminWidgetHookTests, self).tearDown()

        self.extension.shutdown()

    def test_initialize(self):
        """Testing AdminWidgetHook.initialize"""
        AdminWidgetHook(self.extension, MyAdminWidget)

        self.assertIn(MyAdminWidget, admin_widgets_registry)

    def test_initialize_with_legacy_widget(self):
        """Testing AdminWidgetHook.initialize with legacy Widget subclass"""
        message = (
            "AdminWidgetHook's support for legacy "
            "reviewboard.admin.widgets.Widget subclasses is deprecated "
            "and will be removed in Review Board 5.0. Rewrite %r "
            "to subclass the modern "
            "reviewboard.admin.widgets.baseAdminWidget instead. This "
            "will require a full rewrite of the widget's functionality."
            % MyLegacyAdminWidget
        )

        with self.assertWarns(RemovedInReviewBoard50Warning, message):
            AdminWidgetHook(self.extension, MyLegacyAdminWidget)

        self.assertIn(MyLegacyAdminWidget, admin_widgets_registry)

    def test_shutdown(self):
        """Testing AdminWidgetHook.shutdown"""
        hook = AdminWidgetHook(self.extension, MyAdminWidget)
        hook.disable_hook()

        self.assertNotIn(MyAdminWidget, admin_widgets_registry)


class WebAPICapabilitiesExtension(Extension):
    registration = RegisteredExtension()
    metadata = {
        'Name': 'Web API Capabilities Extension',
    }
    id = 'WebAPICapabilitiesExtension'

    def __init__(self, *args, **kwargs):
        super(WebAPICapabilitiesExtension, self).__init__(*args, **kwargs)


class WebAPICapabilitiesHookTests(ExtensionManagerMixin, BaseWebAPITestCase):
    """Testing WebAPICapabilitiesHook."""
    def setUp(self):
        super(WebAPICapabilitiesHookTests, self).setUp()

        self.extension = WebAPICapabilitiesExtension(
            extension_manager=self.manager)
        self.url = get_root_url()

    def tearDown(self):
        super(WebAPICapabilitiesHookTests, self).tearDown()

    def test_register(self):
        """Testing WebAPICapabilitiesHook initializing"""
        WebAPICapabilitiesHook(
            extension=self.extension,
            caps={
                'sandboxed': True,
                'thorough': True,
            })

        rsp = self.api_get(path=self.url,
                           expected_mimetype=root_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertIn('capabilities', rsp)

        caps = rsp['capabilities']
        self.assertIn('WebAPICapabilitiesExtension', caps)

        extension_caps = caps[self.extension.id]
        self.assertTrue(extension_caps['sandboxed'])
        self.assertTrue(extension_caps['thorough'])

        self.extension.shutdown()

    def test_register_fails_no_id(self):
        """Testing WebAPICapabilitiesHook initializing with ID of None"""
        self.extension.id = None

        self.assertRaisesMessage(
            ValueError,
            'The capabilities_id attribute must not be None',
            WebAPICapabilitiesHook,
            self.extension,
            {
                'sandboxed': True,
                'thorough': True,
            })

        rsp = self.api_get(path=self.url,
                           expected_mimetype=root_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertIn('capabilities', rsp)

        caps = rsp['capabilities']
        self.assertNotIn('WebAPICapabilitiesExtension', caps)
        self.assertNotIn(None, caps)

        # Note that the hook failed to enable, so there's no need to test
        # shutdown().

    def test_register_fails_default_capability(self):
        """Testing WebAPICapabilitiesHook initializing with default key"""
        self.extension.id = 'diffs'

        self.assertRaisesMessage(
            KeyError,
            '"diffs" is reserved for the default set of capabilities',
            WebAPICapabilitiesHook,
            self.extension,
            {
                'base_commit_ids': False,
                'moved_files': False,
            })

        rsp = self.api_get(path=self.url,
                           expected_mimetype=root_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertIn('capabilities', rsp)

        caps = rsp['capabilities']
        self.assertIn('diffs', caps)

        diffs_caps = caps['diffs']
        self.assertTrue(diffs_caps['base_commit_ids'])
        self.assertTrue(diffs_caps['moved_files'])

        # Note that the hook failed to enable, so there's no need to test
        # shutdown().

    def test_unregister(self):
        """Testing WebAPICapabilitiesHook uninitializing"""
        hook = WebAPICapabilitiesHook(
            extension=self.extension,
            caps={
                'sandboxed': True,
                'thorough': True,
            })

        hook.disable_hook()

        rsp = self.api_get(path=self.url,
                           expected_mimetype=root_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertIn('capabilities', rsp)

        caps = rsp['capabilities']
        self.assertNotIn('WebAPICapabilitiesExtension', caps)

        self.extension.shutdown()


class GenericTestResource(WebAPIResource):
    name = 'test'
    uri_object_key = 'test_id'
    extra_data = {}
    item_mimetype = 'application/vnd.reviewboard.org.test+json'

    fields = {
        'extra_data': {
            'type': dict,
            'description': 'Extra data as part of the test resource. '
                           'This can be set by the API or extensions.',
        },
    }

    allowed_methods = ('GET', 'PUT')

    def get(self, *args, **kwargs):
        return 200, {
            'test': {
                'extra_data': self.serialize_extra_data_field(self)
            }
        }

    def put(self, request, *args, **kwargs):
        fields = request.POST.dict()
        self.import_extra_data(self, self.extra_data, fields)

        return 200, {
            'test': self.extra_data
        }

    def has_access_permissions(self, request, obj, *args, **kwargs):
        return True


class APIExtraDataAccessHookTests(ExtensionManagerMixin, SpyAgency,
                                  BaseWebAPITestCase):
    """Testing APIExtraDataAccessHook."""

    fixtures = ['test_users']

    class EverythingPrivateHook(APIExtraDataAccessHook):
        """Hook which overrides callable to return all fields as private."""

        def get_extra_data_state(self, key_path):
            self.called = True
            return ExtraDataAccessLevel.ACCESS_STATE_PRIVATE

    class InvalidCallableHook(APIExtraDataAccessHook):
        """Hook which implements an invalid callable"""

        get_extra_data_state = 'not a callable'

    def setUp(self):
        super(APIExtraDataAccessHookTests, self).setUp()

        self.resource_class = GenericTestResource
        self.resource = self.resource_class()

        class DummyExtension(Extension):
            resources = [self.resource]
            registration = RegisteredExtension()

        self.extension_class = DummyExtension

        entry_point = Mock()
        entry_point.load = lambda: self.extension_class
        entry_point.dist = Mock()
        entry_point.dist.project_name = 'TestProjectName'
        entry_point.dist.get_metadata_lines = lambda *args: [
            'Name: Resource Test Extension',
        ]

        self.manager._entrypoint_iterator = lambda: [entry_point]

        self.manager.load()
        self.extension = self.manager.enable_extension(self.extension_class.id)
        self.registered = True

        self.extension_class.info = ExtensionInfo.create_from_entrypoint(
            entry_point, self.extension_class)

        self.url = self.resource.get_item_url(test_id=1)
        self.resource.extra_data = {
            'public': 'foo',
            'private': 'secret',
            'readonly': 'bar',
        }

    def tearDown(self):
        super(APIExtraDataAccessHookTests, self).tearDown()

        if self.registered is True:
            self.manager.disable_extension(self.extension_class.id)

    def test_register(self):
        """Testing APIExtraDataAccessHook registration"""
        APIExtraDataAccessHook(
            self.extension,
            self.resource,
            [
                (('public',), ExtraDataAccessLevel.ACCESS_STATE_PUBLIC)
            ])

        self.assertNotEqual(set(),
                            set(self.resource.extra_data_access_callbacks))

    def test_register_overridden_hook(self):
        """Testing overridden APIExtraDataAccessHook registration"""
        self.EverythingPrivateHook(self.extension, self.resource, [])

        self.assertNotEqual(set(),
                            set(self.resource.extra_data_access_callbacks))

    def test_overridden_hook_get(self):
        """Testing overridden APIExtraDataAccessHook get"""
        hook = self.EverythingPrivateHook(self.extension, self.resource, [])

        rsp = self.api_get(self.url,
                           expected_mimetype=self.resource.item_mimetype)

        # Since the hook registers the callback function on initialization,
        # which stores a pointer to the method, we can't use SpyAgency after
        # the hook has already been initialized. Since SpyAgency's spy_on
        # function requires an instance of a class, we also cannot spy on the
        # hook function before initialization. Therefore, as a workaround,
        # we're setting a variable in the function to ensure that it is in
        # fact being called.
        self.assertTrue(hook.called)
        self.assertNotIn('public', rsp['test']['extra_data'])
        self.assertNotIn('readonly', rsp['test']['extra_data'])
        self.assertNotIn('private', rsp['test']['extra_data'])

    def test_overridden_hook_put(self):
        """Testing overridden APIExtraDataAccessHook put"""
        hook = self.EverythingPrivateHook(self.extension, self.resource, [])

        original_value = self.resource.extra_data['readonly']
        modified_extra_fields = {
            'extra_data.public': 'modified',
        }

        rsp = self.api_put(self.url, modified_extra_fields,
                           expected_mimetype=self.resource.item_mimetype)

        # Since the hook registers the callback function on initialization,
        # which stores a pointer to the method, we can't use SpyAgency after
        # the hook has already been initialized. Since SpyAgency's spy_on
        # function requires an instance of a class, we also cannot spy on the
        # hook function before initialization. Therefore, as a workaround,
        # we're setting a variable in the function to ensure that it is in
        # fact being called.
        self.assertTrue(hook.called)
        self.assertEqual(original_value, rsp['test']['readonly'])

    def test_register_invalid_hook(self):
        """Testing hook registration with invalid hook"""
        self.registered = False

        with self.assertRaises(RegistrationError):
            self.InvalidCallableHook(self.extension, self.resource, [])

        self.assertSetEqual(set(),
                            set(self.resource.extra_data_access_callbacks))

    def test_register_hook_already_registered(self):
        """Testing hook registration with already registered callback"""
        hook = APIExtraDataAccessHook(
            self.extension,
            self.resource,
            [
                (('public',), ExtraDataAccessLevel.ACCESS_STATE_PUBLIC)
            ])

        with self.assertRaises(AlreadyRegisteredError):
            hook.resource.extra_data_access_callbacks.register(
                hook.get_extra_data_state)

        self.assertNotEqual(set(),
                            set(self.resource.extra_data_access_callbacks))

    def test_public_state_get(self):
        """Testing APIExtraDataAccessHook public state GET"""
        APIExtraDataAccessHook(
            self.extension,
            self.resource,
            [
                (('public',), ExtraDataAccessLevel.ACCESS_STATE_PUBLIC)
            ])

        rsp = self.api_get(self.url,
                           expected_mimetype=self.resource.item_mimetype)

        self.assertIn('public', rsp['test']['extra_data'])

    def test_public_state_put(self):
        """Testing APIExtraDataAccessHook public state PUT"""
        APIExtraDataAccessHook(
            self.extension,
            self.resource,
            [
                (('public',), ExtraDataAccessLevel.ACCESS_STATE_PUBLIC)
            ])

        modified_extra_fields = {
            'extra_data.public': 'modified',
        }

        rsp = self.api_put(self.url, modified_extra_fields,
                           expected_mimetype=self.resource.item_mimetype)

        self.assertEqual(modified_extra_fields['extra_data.public'],
                         rsp['test']['public'])

    def test_readonly_state_get(self):
        """Testing APIExtraDataAccessHook readonly state get"""
        APIExtraDataAccessHook(
            self.extension,
            self.resource,
            [
                (('readonly',),
                 ExtraDataAccessLevel.ACCESS_STATE_PUBLIC_READONLY)
            ])

        rsp = self.api_get(self.url,
                           expected_mimetype=self.resource.item_mimetype)

        self.assertIn('readonly', rsp['test']['extra_data'])

    def test_readonly_state_put(self):
        """Testing APIExtraDataAccessHook readonly state put"""
        APIExtraDataAccessHook(
            self.extension,
            self.resource,
            [
                (('readonly',),
                 ExtraDataAccessLevel.ACCESS_STATE_PUBLIC_READONLY)
            ])

        original_value = self.resource.extra_data['readonly']
        modified_extra_fields = {
            'extra_data.readonly': 'modified',
        }

        rsp = self.api_put(self.url, modified_extra_fields,
                           expected_mimetype=self.resource.item_mimetype)

        self.assertEqual(original_value, rsp['test']['readonly'])

    def test_private_state_get(self):
        """Testing APIExtraDataAccessHook private state get"""
        APIExtraDataAccessHook(
            self.extension,
            self.resource,
            [
                (('private',), ExtraDataAccessLevel.ACCESS_STATE_PRIVATE)
            ])

        rsp = self.api_get(self.url,
                           expected_mimetype=self.resource.item_mimetype)

        self.assertNotIn('private', rsp['test']['extra_data'])

    def test_private_state_put(self):
        """Testing APIExtraDataAccessHook private state put"""
        APIExtraDataAccessHook(
            self.extension,
            self.resource,
            [
                (('private',), ExtraDataAccessLevel.ACCESS_STATE_PRIVATE)
            ])

        original_value = self.resource.extra_data['private']
        modified_extra_fields = {
            'extra_data.private': 'modified',
        }

        rsp = self.api_put(self.url, modified_extra_fields,
                           expected_mimetype=self.resource.item_mimetype)

        self.assertEqual(original_value, rsp['test']['private'])

    def test_unregister(self):
        """Testing APIExtraDataAccessHook unregistration"""
        hook = APIExtraDataAccessHook(
            self.extension,
            self.resource,
            [
                (('public',), ExtraDataAccessLevel.ACCESS_STATE_PUBLIC)
            ])

        hook.shutdown()

        self.assertSetEqual(set(),
                            set(self.resource.extra_data_access_callbacks))


class SandboxExtension(Extension):
    registration = RegisteredExtension()
    metadata = {
        'Name': 'Sandbox Extension',
    }
    id = 'reviewboard.extensions.tests.SandboxExtension'

    def __init__(self, *args, **kwargs):
        super(SandboxExtension, self).__init__(*args, **kwargs)


class SandboxReviewRequestApprovalTestHook(ReviewRequestApprovalHook):
    def is_approved(self, review_request, prev_approved, prev_failure):
        raise Exception


class SandboxNavigationBarTestHook(NavigationBarHook):
    def get_entries(self, context):
        raise Exception


class SandboxDiffViewerActionTestHook(DiffViewerActionHook):
    def get_actions(self, context):
        raise Exception


class SandboxHeaderActionTestHook(HeaderActionHook):
    def get_actions(self, context):
        raise Exception


class SandboxHeaderDropdownActionTestHook(HeaderDropdownActionHook):
    def get_actions(self, context):
        raise Exception


class SandboxReviewRequestActionTestHook(ReviewRequestActionHook):
    def get_actions(self, context):
        raise Exception


class SandboxReviewRequestDropdownActionTestHook(
        ReviewRequestDropdownActionHook):
    def get_actions(self, context):
        raise Exception


class SandboxCommentDetailDisplayTestHook(CommentDetailDisplayHook):
    def render_review_comment_detail(self, comment):
        raise Exception

    def render_email_comment_detail(self, comment, is_html):
        raise Exception


class SandboxBaseReviewRequestTestShouldRenderField(BaseReviewRequestField):
    field_id = 'should_render'

    def should_render(self, value):
        raise Exception


class SandboxBaseReviewRequestTestInitField(BaseReviewRequestField):
    field_id = 'init_field'

    def __init__(self, review_request_details):
        raise Exception


class SandboxUserInfoboxHook(UserInfoboxHook):
    def get_etag_data(self, user, request, local_site):
        raise Exception

    def render(self, user, request, local_site):
        raise Exception


class TestIsEmptyField(BaseReviewRequestField):
    field_id = 'is_empty'


class TestInitField(BaseReviewRequestField):
    field_id = 'test_init'


class TestInitFieldset(BaseReviewRequestFieldSet):
    fieldset_id = 'test_init'
    field_classes = [SandboxBaseReviewRequestTestInitField]


class TestShouldRenderFieldset(BaseReviewRequestFieldSet):
    fieldset_id = 'test_should_render'
    field_classes = [SandboxBaseReviewRequestTestShouldRenderField]


class BaseReviewRequestTestIsEmptyFieldset(BaseReviewRequestFieldSet):
    fieldset_id = 'is_empty'
    field_classes = [TestIsEmptyField]

    @classmethod
    def is_empty(cls):
        raise Exception


class BaseReviewRequestTestInitFieldset(BaseReviewRequestFieldSet):
    fieldset_id = 'init_fieldset'
    field_classes = [TestInitField]

    def __init__(self, review_request_details):
        raise Exception


class SandboxTests(ExtensionManagerMixin, TestCase):
    """Testing extension sandboxing"""
    def setUp(self):
        super(SandboxTests, self).setUp()

        self.extension = SandboxExtension(extension_manager=self.manager)

        self.factory = RequestFactory()
        self.user = User.objects.create_user(username='reviewboard',
                                             email='reviewboard@example.com',
                                             password='password')

    def tearDown(self):
        super(SandboxTests, self).tearDown()

        self.extension.shutdown()

    def test_is_approved_sandbox(self):
        """Testing sandboxing ReviewRequestApprovalHook when
        is_approved function throws an error"""
        SandboxReviewRequestApprovalTestHook(extension=self.extension)
        review = ReviewRequest()
        review._calculate_approval()

    def test_get_entries(self):
        """Testing sandboxing NavigationBarHook when get_entries function
        throws an error"""
        entry = {
            'label': 'Test get_entries Function',
            'url': '/dashboard/',
        }

        SandboxNavigationBarTestHook(extension=self.extension, entries=[entry])

        context = Context({})

        t = Template(
            "{% load rb_extensions %}"
            "{% navigation_bar_hooks %}")

        t.render(context).strip()

    def test_render_review_comment_details(self):
        """Testing sandboxing CommentDetailDisplayHook when
        render_review_comment_detail throws an error"""
        SandboxCommentDetailDisplayTestHook(extension=self.extension)

        context = Context({'comment': 'this is a comment'})

        t = Template(
            "{% load rb_extensions %}"
            "{% comment_detail_display_hook comment 'review'%}")

        t.render(context).strip()

    def test_email_review_comment_details(self):
        """Testing sandboxing CommentDetailDisplayHook when
        render_email_comment_detail throws an error"""
        SandboxCommentDetailDisplayTestHook(extension=self.extension)

        context = Context({'comment': 'this is a comment'})

        t = Template(
            "{% load rb_extensions %}"
            "{% comment_detail_display_hook comment 'html-email'%}")

        t.render(context).strip()

    def test_action_hooks_diff_viewer_hook(self):
        """Testing sandboxing DiffViewerActionHook when
        action_hooks throws an error"""
        SandboxDiffViewerActionTestHook(extension=self.extension)

        context = Context({'comment': 'this is a comment'})

        template = Template(
            '{% load reviewtags %}'
            '{% review_request_actions %}')

        template.render(context)

    def test_action_hooks_header_hook(self):
        """Testing sandboxing HeaderActionHook when
        action_hooks throws an error"""
        SandboxHeaderActionTestHook(extension=self.extension)

        context = Context({'comment': 'this is a comment'})

        t = Template(
            "{% load rb_extensions %}"
            "{% header_action_hooks %}")

        t.render(context).strip()

    def test_action_hooks_header_dropdown_hook(self):
        """Testing sandboxing HeaderDropdownActionHook when
        action_hooks throws an error"""
        SandboxHeaderDropdownActionTestHook(extension=self.extension)

        context = Context({'comment': 'this is a comment'})

        t = Template(
            "{% load rb_extensions %}"
            "{% header_dropdown_action_hooks %}")

        t.render(context).strip()

    def test_action_hooks_review_request_hook(self):
        """Testing sandboxing ReviewRequestActionHook when
        action_hooks throws an error"""
        SandboxReviewRequestActionTestHook(extension=self.extension)

        context = Context({'comment': 'this is a comment'})

        template = Template(
            '{% load reviewtags %}'
            '{% review_request_actions %}')

        template.render(context)

    def test_action_hooks_review_request_dropdown_hook(self):
        """Testing sandboxing ReviewRequestDropdownActionHook when
        action_hooks throws an error"""
        SandboxReviewRequestDropdownActionTestHook(extension=self.extension)

        context = Context({'comment': 'this is a comment'})

        template = Template(
            '{% load reviewtags %}'
            '{% review_request_actions %}')

        template.render(context)

    def test_is_empty_review_request_fieldset(self):
        """Testing sandboxing ReviewRequestFieldset is_empty function in
        for_review_request_fieldset"""
        fieldset = [BaseReviewRequestTestIsEmptyFieldset]
        ReviewRequestFieldSetsHook(extension=self.extension,
                                   fieldsets=fieldset)

        review = ReviewRequest()

        request = self.factory.get('test')
        request.user = self.user
        context = Context({
            'review_request_details': review,
            'request': request
        })

        t = Template(
            "{% load reviewtags %}"
            "{% for_review_request_fieldset review_request_details %}"
            "{% end_for_review_request_fieldset %}")

        t.render(context).strip()

    def test_field_cls_review_request_field(self):
        """Testing sandboxing ReviewRequestFieldset init function in
        for_review_request_field"""
        fieldset = [TestInitFieldset]
        ReviewRequestFieldSetsHook(extension=self.extension,
                                   fieldsets=fieldset)

        review = ReviewRequest()
        context = Context({
            'review_request_details': review,
            'fieldset': TestInitFieldset
        })

        t = Template(
            "{% load reviewtags %}"
            "{% for_review_request_field review_request_details 'test_init' %}"
            "{% end_for_review_request_field %}")

        t.render(context).strip()

    def test_fieldset_cls_review_request_fieldset(self):
        """Testing sandboxing ReviewRequestFieldset init function in
        for_review_request_fieldset"""
        fieldset = [BaseReviewRequestTestInitFieldset]
        ReviewRequestFieldSetsHook(extension=self.extension,
                                   fieldsets=fieldset)

        review = ReviewRequest()
        request = self.factory.get('test')
        request.user = self.user
        context = Context({
            'review_request_details': review,
            'request': request
        })

        t = Template(
            "{% load reviewtags %}"
            "{% for_review_request_fieldset review_request_details %}"
            "{% end_for_review_request_fieldset %}")

        t.render(context).strip()

    def test_should_render_review_request_field(self):
        """Testing sandboxing ReviewRequestFieldset should_render function in
        for_review_request_field"""
        fieldset = [TestShouldRenderFieldset]
        ReviewRequestFieldSetsHook(extension=self.extension,
                                   fieldsets=fieldset)

        review = ReviewRequest()
        context = Context({
            'review_request_details': review,
            'fieldset': TestShouldRenderFieldset
        })

        t = Template(
            "{% load reviewtags %}"
            "{% for_review_request_field review_request_details"
            " 'test_should_render' %}"
            "{% end_for_review_request_field %}")

        t.render(context).strip()

    def test_user_infobox_hook(self):
        """Testing sandboxing of the UserInfoboxHook"""
        SandboxUserInfoboxHook(self.extension, 'template.html')

        self.client.get(
            local_site_reverse('user-infobox', kwargs={
                'username': self.user.username,
            }))


class EmailHookTests(ExtensionManagerMixin, SpyAgency, TestCase):
    """Testing the e-mail recipient filtering capacity of EmailHooks."""

    fixtures = ['test_users']

    def setUp(self):
        super(EmailHookTests, self).setUp()

        self.extension = DummyExtension(extension_manager=self.manager)

        mail.outbox = []

    def tearDown(self):
        super(EmailHookTests, self).tearDown()

        self.extension.shutdown()

    def test_review_request_published_email_hook(self):
        """Testing the ReviewRequestPublishedEmailHook"""
        class DummyHook(ReviewRequestPublishedEmailHook):
            def get_to_field(self, to_field, review_request, user):
                return set([user])

            def get_cc_field(self, cc_field, review_request, user):
                return set([user])

        hook = DummyHook(self.extension)

        self.spy_on(hook.get_to_field)
        self.spy_on(hook.get_cc_field)

        review_request = self.create_review_request()
        admin = User.objects.get(username='admin')

        call_kwargs = {
            'user': admin,
            'review_request': review_request,
        }

        with self.siteconfig_settings({'mail_send_review_mail': True}):
            review_request.publish(admin)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to,
                         [build_email_address_for_user(admin)])
        self.assertTrue(hook.get_to_field.called)
        self.assertTrue(hook.get_to_field.called_with(**call_kwargs))
        self.assertTrue(hook.get_cc_field.called)
        self.assertTrue(hook.get_cc_field.called_with(**call_kwargs))

    def test_review_published_email_hook(self):
        """Testing the ReviewPublishedEmailHook"""
        class DummyHook(ReviewPublishedEmailHook):
            def get_to_field(self, to_field, review, user, review_request,
                             to_owner_only):
                return set([user])

            def get_cc_field(self, cc_field, review, user, review_request,
                             to_owner_only):
                return set([user])

        hook = DummyHook(self.extension)

        self.spy_on(hook.get_to_field)
        self.spy_on(hook.get_cc_field)

        admin = User.objects.get(username='admin')
        review_request = self.create_review_request(public=True)
        review = self.create_review(review_request)

        call_kwargs = {
            'user': admin,
            'review_request': review_request,
            'review': review,
            'to_owner_only': False,
        }

        with self.siteconfig_settings({'mail_send_review_mail': True}):
            review.publish(admin)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to,
                         [build_email_address_for_user(admin)])
        self.assertTrue(hook.get_to_field.called)
        self.assertTrue(hook.get_to_field.called_with(**call_kwargs))
        self.assertTrue(hook.get_cc_field.called)
        self.assertTrue(hook.get_cc_field.called_with(**call_kwargs))

    def test_review_reply_published_email_hook(self):
        """Testing the ReviewReplyPublishedEmailHook"""
        class DummyHook(ReviewReplyPublishedEmailHook):
            def get_to_field(self, to_field, reply, user, review,
                             review_request):
                return set([user])

            def get_cc_field(self, cc_field, reply, user, review,
                             review_request):
                return set([user])

        hook = DummyHook(self.extension)

        self.spy_on(hook.get_to_field)
        self.spy_on(hook.get_cc_field)

        admin = User.objects.get(username='admin')
        review_request = self.create_review_request(public=True)
        review = self.create_review(review_request)
        reply = self.create_reply(review)

        call_kwargs = {
            'user': admin,
            'review_request': review_request,
            'review': review,
            'reply': reply,
        }

        with self.siteconfig_settings({'mail_send_review_mail': True}):
            reply.publish(admin)

        self.assertEqual(len(mail.outbox), 1)
        self.assertTrue(hook.get_to_field.called)
        self.assertTrue(hook.get_to_field.called_with(**call_kwargs))
        self.assertTrue(hook.get_cc_field.called)
        self.assertTrue(hook.get_cc_field.called_with(**call_kwargs))

    def test_review_request_closed_email_hook_submitted(self):
        """Testing the ReviewRequestClosedEmailHook for a review request being
        submitted
        """
        class DummyHook(ReviewRequestClosedEmailHook):
            def get_to_field(self, to_field, review_request, user, close_type):
                return set([user])

            def get_cc_field(self, cc_field, review_request, user, close_type):
                return set([user])

        hook = DummyHook(self.extension)

        self.spy_on(hook.get_to_field)
        self.spy_on(hook.get_cc_field)

        admin = User.objects.get(username='admin')
        review_request = self.create_review_request(public=True)

        call_kwargs = {
            'user': admin,
            'review_request': review_request,
            'close_type': ReviewRequest.SUBMITTED,
        }

        with self.siteconfig_settings({'mail_send_review_close_mail': True}):
            review_request.close(ReviewRequest.SUBMITTED, admin)

        self.assertEqual(len(mail.outbox), 1)
        self.assertTrue(hook.get_to_field.called)
        self.assertTrue(hook.get_to_field.called_with(**call_kwargs))
        self.assertTrue(hook.get_cc_field.called)
        self.assertTrue(hook.get_cc_field.called_with(**call_kwargs))

    def test_review_request_closed_email_hook_discarded(self):
        """Testing the ReviewRequestClosedEmailHook for a review request being
        discarded
        """
        class DummyHook(ReviewRequestClosedEmailHook):
            def get_to_field(self, to_field, review_request, user, close_type):
                return set([user])

            def get_cc_field(self, cc_field, review_request, user, close_type):
                return set([user])

        hook = DummyHook(self.extension)

        self.spy_on(hook.get_to_field)
        self.spy_on(hook.get_cc_field)

        admin = User.objects.get(username='admin')
        review_request = self.create_review_request(public=True)

        call_kwargs = {
            'user': admin,
            'review_request': review_request,
            'close_type': ReviewRequest.DISCARDED,
        }

        with self.siteconfig_settings({'mail_send_review_close_mail': True}):
            review_request.close(ReviewRequest.DISCARDED, admin)

        self.assertEqual(len(mail.outbox), 1)
        self.assertTrue(hook.get_to_field.called)
        self.assertTrue(hook.get_to_field.called_with(**call_kwargs))
        self.assertTrue(hook.get_cc_field.called)
        self.assertTrue(hook.get_cc_field.called_with(**call_kwargs))

    def test_generic_hook(self):
        """Testing that a generic e-mail hook works for all e-mail signals"""
        hook = EmailHook(self.extension,
                         signals=[
                             review_request_published,
                             review_published,
                             reply_published,
                             review_request_closed,
                         ])

        self.spy_on(hook.get_to_field)
        self.spy_on(hook.get_cc_field)

        user = User.objects.create_user(username='testuser')
        review_request = self.create_review_request(public=True,
                                                    target_people=[user])
        review = self.create_review(review_request)
        reply = self.create_reply(review)

        siteconfig_settings = {
            'mail_send_review_mail': True,
            'mail_send_review_close_mail': True,
        }

        with self.siteconfig_settings(siteconfig_settings):
            self.assertEqual(len(mail.outbox), 0)

            review.publish()
            call_kwargs = {
                'user': review.user,
                'review': review,
                'review_request': review_request,
                'to_owner_only': False,
            }

            self.assertEqual(len(mail.outbox), 1)
            self.assertEqual(len(hook.get_to_field.spy.calls), 1)
            self.assertEqual(len(hook.get_cc_field.spy.calls), 1)
            self.assertEqual(hook.get_to_field.spy.calls[-1].kwargs,
                             call_kwargs)
            self.assertEqual(hook.get_cc_field.spy.calls[-1].kwargs,
                             call_kwargs)

            reply.publish(reply.user)

            call_kwargs.pop('to_owner_only')
            call_kwargs['reply'] = reply
            call_kwargs['user'] = reply.user

            self.assertEqual(len(mail.outbox), 2)
            self.assertEqual(len(hook.get_to_field.spy.calls), 2)
            self.assertEqual(len(hook.get_cc_field.spy.calls), 2)
            self.assertEqual(hook.get_to_field.spy.calls[-1].kwargs,
                             call_kwargs)
            self.assertEqual(hook.get_cc_field.spy.calls[-1].kwargs,
                             call_kwargs)

            review_request.close(ReviewRequest.DISCARDED)
            call_kwargs = {
                'review_request': review_request,
                'user': review_request.submitter,
                'close_type': ReviewRequest.DISCARDED,
            }

            self.assertEqual(len(mail.outbox), 3)
            self.assertEqual(len(hook.get_to_field.spy.calls), 3)
            self.assertEqual(len(hook.get_cc_field.spy.calls), 3)
            self.assertEqual(hook.get_to_field.spy.calls[-1].kwargs,
                             call_kwargs)
            self.assertEqual(hook.get_cc_field.spy.calls[-1].kwargs,
                             call_kwargs)

            review_request.reopen()
            review_request.publish(review_request.submitter)
            call_kwargs = {
                'review_request': review_request,
                'user': review_request.submitter,
            }

            self.assertEqual(len(mail.outbox), 4)
            self.assertEqual(len(hook.get_to_field.spy.calls), 4)
            self.assertEqual(len(hook.get_cc_field.spy.calls), 4)
            self.assertEqual(hook.get_to_field.spy.calls[-1].kwargs,
                             call_kwargs)
            self.assertEqual(hook.get_cc_field.spy.calls[-1].kwargs,
                             call_kwargs)

            review_request.close(ReviewRequest.SUBMITTED)
            call_kwargs['close_type'] = ReviewRequest.SUBMITTED

            self.assertEqual(len(mail.outbox), 5)
            self.assertEqual(len(hook.get_to_field.spy.calls), 5)
            self.assertEqual(len(hook.get_cc_field.spy.calls), 5)
            self.assertEqual(hook.get_to_field.spy.calls[-1].kwargs,
                             call_kwargs)
            self.assertEqual(hook.get_cc_field.spy.calls[-1].kwargs,
                             call_kwargs)


class AvatarServiceHookTests(ExtensionManagerMixin, TestCase):
    """Test for reviewboard.extensions.hooks.AvatarServiceHook."""

    @classmethod
    def setUpClass(cls):
        super(AvatarServiceHookTests, cls).setUpClass()
        avatar_services.reset()

    def setUp(self):
        super(AvatarServiceHookTests, self).setUp()
        self.extension = DummyExtension(extension_manager=self.manager)

    def tearDown(self):
        super(AvatarServiceHookTests, self).tearDown()
        self.extension.shutdown()
        avatar_services.reset()

    def test_register(self):
        """Testing AvatarServiceHook registers services"""
        self.assertNotIn(DummyAvatarService, avatar_services)
        AvatarServiceHook(self.extension, DummyAvatarService,
                          start_enabled=True)
        self.assertIn(DummyAvatarService, avatar_services)

        avatar_services.enable_service(DummyAvatarService, save=False)
        self.assertTrue(avatar_services.is_enabled(DummyAvatarService))

    def test_unregister(self):
        """Testing AvatarServiceHook unregisters services on shutdown"""
        self.assertNotIn(DummyAvatarService, avatar_services)
        AvatarServiceHook(self.extension, DummyAvatarService,
                          start_enabled=True)
        self.assertIn(DummyAvatarService, avatar_services)

        self.extension.shutdown()
        self.assertNotIn(DummyAvatarService, avatar_services)
