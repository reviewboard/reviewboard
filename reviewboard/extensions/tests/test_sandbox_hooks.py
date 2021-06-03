"""Unit tests for extension hook sandboxing."""

from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.template import Context, Template
from django.test.client import RequestFactory
from djblets.extensions.models import RegisteredExtension

from reviewboard.extensions.base import Extension
from reviewboard.extensions.hooks import (CommentDetailDisplayHook,
                                          DiffViewerActionHook,
                                          HeaderActionHook,
                                          HeaderDropdownActionHook,
                                          NavigationBarHook,
                                          ReviewRequestActionHook,
                                          ReviewRequestApprovalHook,
                                          ReviewRequestDropdownActionHook,
                                          ReviewRequestFieldSetsHook,
                                          UserInfoboxHook)
from reviewboard.extensions.tests.testcases import ExtensionManagerMixin
from reviewboard.reviews.fields import (BaseReviewRequestField,
                                        BaseReviewRequestFieldSet)
from reviewboard.reviews.models import ReviewRequest
from reviewboard.site.urlresolvers import local_site_reverse
from reviewboard.testing.testcase import TestCase


class SandboxExtension(Extension):
    registration = RegisteredExtension()
    metadata = {
        'Name': 'Sandbox Extension',
    }
    id = 'reviewboard.extensions.tests.SandboxExtension'


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
        is_approved function throws an error
        """
        SandboxReviewRequestApprovalTestHook(extension=self.extension)
        review = ReviewRequest()
        review._calculate_approval()

    def test_get_entries(self):
        """Testing sandboxing NavigationBarHook when get_entries function
        throws an error
        """
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
        render_review_comment_detail throws an error
        """
        SandboxCommentDetailDisplayTestHook(extension=self.extension)

        context = Context({'comment': 'this is a comment'})

        t = Template(
            "{% load rb_extensions %}"
            "{% comment_detail_display_hook comment 'review'%}")

        t.render(context).strip()

    def test_email_review_comment_details(self):
        """Testing sandboxing CommentDetailDisplayHook when
        render_email_comment_detail throws an error
        """
        SandboxCommentDetailDisplayTestHook(extension=self.extension)

        context = Context({'comment': 'this is a comment'})

        t = Template(
            "{% load rb_extensions %}"
            "{% comment_detail_display_hook comment 'html-email'%}")

        t.render(context).strip()

    def test_action_hooks_diff_viewer_hook(self):
        """Testing sandboxing DiffViewerActionHook when action_hooks throws
        an error
        """
        SandboxDiffViewerActionTestHook(extension=self.extension)

        context = Context({'comment': 'this is a comment'})

        template = Template(
            '{% load reviewtags %}'
            '{% review_request_actions %}')

        template.render(context)

    def test_action_hooks_header_hook(self):
        """Testing sandboxing HeaderActionHook when action_hooks throws an
        error
        """
        SandboxHeaderActionTestHook(extension=self.extension)

        context = Context({'comment': 'this is a comment'})

        t = Template(
            "{% load rb_extensions %}"
            "{% header_action_hooks %}")

        t.render(context).strip()

    def test_action_hooks_header_dropdown_hook(self):
        """Testing sandboxing HeaderDropdownActionHook when action_hooks
        throws an error
        """
        SandboxHeaderDropdownActionTestHook(extension=self.extension)

        context = Context({'comment': 'this is a comment'})

        t = Template(
            "{% load rb_extensions %}"
            "{% header_dropdown_action_hooks %}")

        t.render(context).strip()

    def test_action_hooks_review_request_hook(self):
        """Testing sandboxing ReviewRequestActionHook when action_hooks
        throws an error
        """
        SandboxReviewRequestActionTestHook(extension=self.extension)

        context = Context({'comment': 'this is a comment'})

        template = Template(
            '{% load reviewtags %}'
            '{% review_request_actions %}')

        template.render(context)

    def test_action_hooks_review_request_dropdown_hook(self):
        """Testing sandboxing ReviewRequestDropdownActionHook when
        action_hooks throws an error
        """
        SandboxReviewRequestDropdownActionTestHook(extension=self.extension)

        context = Context({'comment': 'this is a comment'})

        template = Template(
            '{% load reviewtags %}'
            '{% review_request_actions %}')

        template.render(context)

    def test_is_empty_review_request_fieldset(self):
        """Testing sandboxing ReviewRequestFieldset is_empty function in
        for_review_request_fieldset
        """
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
        for_review_request_field
        """
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
        for_review_request_fieldset
        """
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
        for_review_request_field
        """
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
