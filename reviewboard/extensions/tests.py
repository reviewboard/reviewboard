from __future__ import unicode_literals

from contextlib import contextmanager

from django.contrib.auth.models import User
from django.core import mail
from django.template import Context, Template
from django.test.client import RequestFactory
from django.utils import six
from djblets.extensions.manager import ExtensionManager
from djblets.extensions.models import RegisteredExtension
from djblets.siteconfig.models import SiteConfiguration
from kgb import SpyAgency

from reviewboard.admin.siteconfig import load_site_config
from reviewboard.extensions.base import Extension
from reviewboard.extensions.hooks import (CommentDetailDisplayHook,
                                          DiffViewerActionHook,
                                          EmailHook,
                                          HeaderActionHook,
                                          HeaderDropdownActionHook,
                                          HostingServiceHook,
                                          NavigationBarHook,
                                          ReviewPublishedEmailHook,
                                          ReviewRequestActionHook,
                                          ReviewRequestApprovalHook,
                                          ReviewRequestClosedEmailHook,
                                          ReviewRequestDropdownActionHook,
                                          ReviewRequestFieldSetsHook,
                                          ReviewRequestPublishedEmailHook,
                                          ReviewReplyPublishedEmailHook)
from reviewboard.hostingsvcs.service import (get_hosting_service,
                                             HostingService)
from reviewboard.notifications.email import get_email_address_for_user
from reviewboard.testing.testcase import TestCase
from reviewboard.reviews.models.review_request import ReviewRequest
from reviewboard.reviews.fields import (BaseReviewRequestField,
                                        BaseReviewRequestFieldSet)
from reviewboard.reviews.signals import (review_request_published,
                                         review_published, reply_published,
                                         review_request_closed)


@contextmanager
def set_siteconfig_settings(settings):
    """A context manager to toggle site configuration settings.

    Args:
        settings (dict):
            The new site configuration settings.
    """
    siteconfig = SiteConfiguration.objects.get_current()

    old_settings = {}

    for setting, value in six.iteritems(settings):
        old_settings[setting] = siteconfig.get(setting)
        siteconfig.set(setting, value)

    siteconfig.save()
    load_site_config()

    try:
        yield
    finally:
        for setting, value in six.iteritems(old_settings):
            siteconfig.set(setting, value)

        siteconfig.save()
        load_site_config()



class DummyExtension(Extension):
    registration = RegisteredExtension()


class HookTests(TestCase):
    """Tests the extension hooks."""
    def setUp(self):
        super(HookTests, self).setUp()

        manager = ExtensionManager('')
        self.extension = DummyExtension(extension_manager=manager)

    def tearDown(self):
        super(HookTests, self).tearDown()

        self.extension.shutdown()

    def test_diffviewer_action_hook(self):
        """Testing diff viewer action extension hooks"""
        self._test_action_hook('diffviewer_action_hooks', DiffViewerActionHook)

    def test_review_request_action_hook(self):
        """Testing review request action extension hooks"""
        self._test_action_hook('review_request_action_hooks',
                               ReviewRequestActionHook)

    def test_review_request_dropdown_action_hook(self):
        """Testing review request drop-down action extension hooks"""
        self._test_dropdown_action_hook('review_request_dropdown_action_hooks',
                                        ReviewRequestDropdownActionHook)

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
        self.assertIn((">%s &#9662;" % action['label']), content)
        self.assertIn(self._build_action_template(action['items'][0]),
                      content)

    def _build_action_template(self, action):
        return ('<li><a id="%(id)s" href="%(url)s">'
                '<img src="%(image)s" width="%(image_width)s" '
                'height="%(image_height)s" border="0" alt="" />'
                '%(label)s</a></li>' % action)

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

    def test_navigation_bar_hooks_with_is_enabled_for_legacy(self):
        """Testing NavigationBarHook.is_enabled_for and legacy argument
        format
        """
        def is_enabled_for(user):
            self.assertEqual(user, request.user)

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

        self.assertEqual(t.render(context).strip(),
                         '<li><a href="%(url)s">%(label)s</a></li>' % {
                             'label': entry['label'],
                             'url': '/dashboard/',
                         })

    def test_header_hooks(self):
        """Testing header action extension hooks"""
        self._test_action_hook('header_action_hooks', HeaderActionHook)

    def test_header_dropdown_action_hook(self):
        """Testing header drop-down action extension hooks"""
        self._test_dropdown_action_hook('header_dropdown_action_hooks',
                                        HeaderDropdownActionHook)


class TestService(HostingService):
    name = 'test-service'


class HostingServiceHookTests(TestCase):
    """Testing HostingServiceHook."""
    def setUp(self):
        super(HostingServiceHookTests, self).setUp()

        manager = ExtensionManager('')
        self.extension = DummyExtension(extension_manager=manager)

    def tearDown(self):
        super(HostingServiceHookTests, self).tearDown()

        self.extension.shutdown()

    def test_register(self):
        """Testing HostingServiceHook initializing"""
        HostingServiceHook(extension=self.extension, service_cls=TestService)

        self.assertNotEqual(None, get_hosting_service(TestService.name))

    def test_unregister(self):
        """Testing HostingServiceHook uninitializing"""
        hook = HostingServiceHook(extension=self.extension,
                                  service_cls=TestService)

        hook.shutdown()

        self.assertEqual(None, get_hosting_service(TestService.name))


class SandboxExtension(Extension):
    registration = RegisteredExtension()
    metadata = {
        'Name': 'Sandbox Extension',
    }

    def __init__(self, *args, **kwargs):
        super(SandboxExtension, self).__init__(*args, **kwargs)


class ReviewRequestApprovalTestHook(ReviewRequestApprovalHook):
    def is_approved(self, review_request, prev_approved, prev_failure):
        raise Exception


class NavigationBarTestHook(NavigationBarHook):
    def get_entries(self, context):
        raise Exception


class DiffViewerActionTestHook(DiffViewerActionHook):
    def get_actions(self, context):
        raise Exception


class HeaderActionTestHook(HeaderActionHook):
    def get_actions(self, context):
        raise Exception


class HeaderDropdownActionTestHook(HeaderDropdownActionHook):
    def get_actions(self, context):
        raise Exception


class ReviewRequestActionTestHook(ReviewRequestActionHook):
    def get_actions(self, context):
        raise Exception


class ReviewRequestDropdownActionTestHook(ReviewRequestDropdownActionHook):
    def get_actions(self, context):
        raise Exception


class CommentDetailDisplayTestHook(CommentDetailDisplayHook):
    def render_review_comment_detail(self, comment):
        raise Exception

    def render_email_comment_detail(self, comment, is_html):
        raise Exception


class BaseReviewRequestTestShouldRenderField(BaseReviewRequestField):
    field_id = 'should_render'

    def should_render(self, value):
        raise Exception


class BaseReviewRequestTestInitField(BaseReviewRequestField):
    field_id = 'init_field'

    def __init__(self, review_request_details):
        raise Exception


class TestIsEmptyField(BaseReviewRequestField):
    field_id = 'is_empty'


class TestInitField(BaseReviewRequestField):
    field_id = 'test_init'


class TestInitFieldset(BaseReviewRequestFieldSet):
    fieldset_id = 'test_init'
    field_classes = [BaseReviewRequestTestInitField]


class TestShouldRenderFieldset(BaseReviewRequestFieldSet):
    fieldset_id = 'test_should_render'
    field_classes = [BaseReviewRequestTestShouldRenderField]


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


class SandboxTests(TestCase):
    """Testing extension sandboxing"""
    def setUp(self):
        super(SandboxTests, self).setUp()

        manager = ExtensionManager('')
        self.extension = SandboxExtension(extension_manager=manager)

        self.factory = RequestFactory()
        self.user = User.objects.create_user(username='reviewboard', email='',
                                             password='password')

    def tearDown(self):
        super(SandboxTests, self).tearDown()

        self.extension.shutdown()

    def test_is_approved_sandbox(self):
        """Testing sandboxing ReviewRequestApprovalHook when
        is_approved function throws an error"""
        ReviewRequestApprovalTestHook(extension=self.extension)
        review = ReviewRequest()
        review._calculate_approval()

    def test_get_entries(self):
        """Testing sandboxing NavigationBarHook when get_entries function
        throws an error"""
        entry = {
            'label': 'Test get_entries Function',
            'url': '/dashboard/',
        }

        NavigationBarTestHook(extension=self.extension, entries=[entry])

        context = Context({})

        t = Template(
            "{% load rb_extensions %}"
            "{% navigation_bar_hooks %}")

        t.render(context).strip()

    def test_render_review_comment_details(self):
        """Testing sandboxing CommentDetailDisplayHook when
        render_review_comment_detail throws an error"""
        CommentDetailDisplayTestHook(extension=self.extension)

        context = Context({'comment': 'this is a comment'})

        t = Template(
            "{% load rb_extensions %}"
            "{% comment_detail_display_hook comment 'review'%}")

        t.render(context).strip()

    def test_email_review_comment_details(self):
        """Testing sandboxing CommentDetailDisplayHook when
        render_email_comment_detail throws an error"""
        CommentDetailDisplayTestHook(extension=self.extension)

        context = Context({'comment': 'this is a comment'})

        t = Template(
            "{% load rb_extensions %}"
            "{% comment_detail_display_hook comment 'html-email'%}")

        t.render(context).strip()

    def test_action_hooks_diff_viewer_hook(self):
        """Testing sandboxing DiffViewerActionHook when
        action_hooks throws an error"""
        DiffViewerActionTestHook(extension=self.extension)

        context = Context({'comment': 'this is a comment'})

        t = Template(
            "{% load rb_extensions %}"
            "{% diffviewer_action_hooks %}")

        t.render(context).strip()

    def test_action_hooks_header_hook(self):
        """Testing sandboxing HeaderActionHook when
        action_hooks throws an error"""
        HeaderActionTestHook(extension=self.extension)

        context = Context({'comment': 'this is a comment'})

        t = Template(
            "{% load rb_extensions %}"
            "{% header_action_hooks %}")

        t.render(context).strip()

    def test_action_hooks_header_dropdown_hook(self):
        """Testing sandboxing HeaderDropdownActionHook when
        action_hooks throws an error"""
        HeaderDropdownActionTestHook(extension=self.extension)

        context = Context({'comment': 'this is a comment'})

        t = Template(
            "{% load rb_extensions %}"
            "{% header_dropdown_action_hooks %}")

        t.render(context).strip()

    def test_action_hooks_review_request_hook(self):
        """Testing sandboxing ReviewRequestActionHook when
        action_hooks throws an error"""
        ReviewRequestActionTestHook(extension=self.extension)

        context = Context({'comment': 'this is a comment'})

        t = Template(
            "{% load rb_extensions %}"
            "{% review_request_action_hooks %}")

        t.render(context).strip()

    def test_action_hooks_review_request_dropdown_hook(self):
        """Testing sandboxing ReviewRequestDropdownActionHook when
        action_hooks throws an error"""
        ReviewRequestDropdownActionTestHook(extension=self.extension)

        context = Context({'comment': 'this is a comment'})

        t = Template(
            "{% load rb_extensions %}"
            "{% review_request_dropdown_action_hooks %}")

        t.render(context).strip()

    def test_is_empty_review_request_fieldset(self):
        """Testing sandboxing ReivewRequestFieldset is_empty function in
        for_review_request_fieldset"""
        fieldset = [BaseReviewRequestTestIsEmptyFieldset]
        ReviewRequestFieldSetsHook(extension=self.extension, fieldsets=fieldset)

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
        ReviewRequestFieldSetsHook(extension=self.extension, fieldsets=fieldset)

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
        ReviewRequestFieldSetsHook(extension=self.extension, fieldsets=fieldset)

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
        ReviewRequestFieldSetsHook(extension=self.extension, fieldsets=fieldset)

        review = ReviewRequest()
        context = Context({
            'review_request_details': review,
            'fieldset': TestShouldRenderFieldset
        })

        t = Template(
            "{% load reviewtags %}"
            "{% for_review_request_field review_request_details 'test_should_render' %}"
            "{% end_for_review_request_field %}")

        t.render(context).strip()


class EmailHookTests(SpyAgency, TestCase):
    """Testing the e-mail recipient filtering capacity of EmailHooks."""

    fixtures = ['test_users']

    def setUp(self):
        super(EmailHookTests, self).setUp()

        manager = ExtensionManager('')
        self.extension = DummyExtension(extension_manager=manager)

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

        with set_siteconfig_settings({'mail_send_review_mail': True}):
            review_request.publish(admin)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to,
                         [get_email_address_for_user(admin)])
        self.assertTrue(hook.get_to_field.spy.called)
        self.assertEqual(hook.get_to_field.spy.calls[0].kwargs, call_kwargs)
        self.assertTrue(hook.get_cc_field.spy.called)
        self.assertEqual(hook.get_cc_field.spy.calls[0].kwargs, call_kwargs)

    def test_review_published_email_hook(self):
        """Testing the ReviewPublishedEmailHook"""
        class DummyHook(ReviewPublishedEmailHook):
            def get_to_field(self, to_field, review, user, review_request):
                return set([user])

            def get_cc_field(self, cc_field, review, user, review_request):
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
        }

        with set_siteconfig_settings({'mail_send_review_mail': True}):
            review.publish(admin)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to,
                         [get_email_address_for_user(admin)])
        self.assertTrue(hook.get_to_field.spy.called)
        self.assertEqual(hook.get_to_field.spy.calls[0].kwargs, call_kwargs)
        self.assertTrue(hook.get_cc_field.spy.called)
        self.assertEqual(hook.get_cc_field.spy.calls[0].kwargs, call_kwargs)

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

        with set_siteconfig_settings({'mail_send_review_mail': True}):
            reply.publish(admin)

        self.assertEqual(len(mail.outbox), 1)
        self.assertTrue(hook.get_to_field.spy.called)
        self.assertEqual(hook.get_to_field.spy.calls[0].kwargs, call_kwargs)
        self.assertTrue(hook.get_cc_field.spy.called)
        self.assertEqual(hook.get_cc_field.spy.calls[0].kwargs, call_kwargs)

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

        with set_siteconfig_settings({'mail_send_review_close_mail': True}):
            review_request.close(ReviewRequest.SUBMITTED, admin)

        self.assertEqual(len(mail.outbox), 1)
        self.assertTrue(hook.get_to_field.spy.called)
        self.assertEqual(hook.get_to_field.spy.calls[0].kwargs, call_kwargs)
        self.assertTrue(hook.get_cc_field.spy.called)
        self.assertEqual(hook.get_cc_field.spy.calls[0].kwargs, call_kwargs)

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

        with set_siteconfig_settings({'mail_send_review_close_mail': True}):
            review_request.close(ReviewRequest.DISCARDED, admin)

        self.assertEqual(len(mail.outbox), 1)
        self.assertTrue(hook.get_to_field.spy.called)
        self.assertEqual(hook.get_to_field.spy.calls[0].kwargs, call_kwargs)
        self.assertTrue(hook.get_cc_field.spy.called)
        self.assertEqual(hook.get_cc_field.spy.calls[0].kwargs, call_kwargs)

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

        review_request = self.create_review_request(public=True)
        review = self.create_review(review_request)
        reply = self.create_reply(review)

        siteconfig_settings = {
            'mail_send_review_mail': True,
            'mail_send_review_close_mail': True,
        }

        with set_siteconfig_settings(siteconfig_settings):
            self.assertEqual(len(mail.outbox), 0)

            review.publish()
            call_kwargs = {
                'user': review.user,
                'review': review,
                'review_request': review_request
            }

            self.assertEqual(len(mail.outbox), 1)
            self.assertEqual(len(hook.get_to_field.spy.calls), 1)
            self.assertEqual(len(hook.get_cc_field.spy.calls), 1)
            self.assertEqual(hook.get_to_field.spy.calls[-1].kwargs,
                             call_kwargs)
            self.assertEqual(hook.get_cc_field.spy.calls[-1].kwargs,
                             call_kwargs)

            reply.publish(reply.user)
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
                'user': None,
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
            call_kwargs['user'] = None
            call_kwargs['close_type'] = ReviewRequest.SUBMITTED

            self.assertEqual(len(mail.outbox), 5)
            self.assertEqual(len(hook.get_to_field.spy.calls), 5)
            self.assertEqual(len(hook.get_cc_field.spy.calls), 5)
            self.assertEqual(hook.get_to_field.spy.calls[-1].kwargs,
                             call_kwargs)
            self.assertEqual(hook.get_cc_field.spy.calls[-1].kwargs,
                             call_kwargs)
