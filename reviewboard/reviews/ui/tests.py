from __future__ import unicode_literals

import os

from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory
from kgb import SpyAgency

from reviewboard.attachments.models import FileAttachment
from reviewboard.reviews.models import (ReviewRequest,
                                        ReviewRequestDraft,
                                        Review)
from reviewboard.reviews.ui.base import (FileAttachmentReviewUI,
                                         register_ui,
                                         unregister_ui)
from reviewboard.testing import TestCase


class InitReviewUI(FileAttachmentReviewUI):
    supported_mimetypes = ['image/jpg']

    def __init__(self, review_request, obj):
        raise Exception


class SandboxReviewUI(FileAttachmentReviewUI):
    supported_mimetypes = ['image/png']

    def is_enabled_for(self, user=None, review_request=None,
                       file_attachment=None, **kwargs):
        raise Exception

    def get_comment_thumbnail(self, comment):
        raise Exception

    def get_comment_link_url(self, comment):
        raise Exception

    def get_comment_link_text(self, comment):
        raise Exception

    def get_extra_context(self, request):
        raise Exception

    def get_js_view_data(self):
        raise Exception


class ConflictFreeReviewUI(FileAttachmentReviewUI):
    supported_mimetypes = ['image/gif']

    def serialize_comment(self, comment):
        raise Exception

    def get_js_model_data(self):
        raise Exception


class SandboxTests(SpyAgency, TestCase):
    """Testing sandboxing extensions."""
    fixtures = ['test_users']

    def setUp(self):
        super(SandboxTests, self).setUp()

        register_ui(InitReviewUI)
        register_ui(SandboxReviewUI)
        register_ui(ConflictFreeReviewUI)

        self.factory = RequestFactory()

        filename = os.path.join(settings.STATIC_ROOT,
                                'rb', 'images', 'trophy.png')

        with open(filename, 'r') as f:
            self.file = SimpleUploadedFile(f.name, f.read(),
                                           content_type='image/png')

        self.user = User.objects.get(username='doc')
        self.review_request = ReviewRequest.objects.create(self.user, None)
        self.file_attachment1 = FileAttachment.objects.create(
            mimetype='image/jpg',
            file=self.file)
        self.file_attachment2 = FileAttachment.objects.create(
            mimetype='image/png',
            file=self.file)
        self.file_attachment3 = FileAttachment.objects.create(
            mimetype='image/gif',
            file=self.file)
        self.review_request.file_attachments.add(self.file_attachment1)
        self.review_request.file_attachments.add(self.file_attachment2)
        self.review_request.file_attachments.add(self.file_attachment3)
        self.draft = ReviewRequestDraft.create(self.review_request)

    def tearDown(self):
        super(SandboxTests, self).tearDown()

        unregister_ui(InitReviewUI)
        unregister_ui(SandboxReviewUI)
        unregister_ui(ConflictFreeReviewUI)

    def test_init_review_ui(self):
        """Testing FileAttachmentReviewUI sandboxes __init__"""
        self.spy_on(InitReviewUI.__init__)

        self.file_attachment1.review_ui

        self.assertTrue(InitReviewUI.__init__.called)

    def test_is_enabled_for(self):
        """Testing FileAttachmentReviewUI sandboxes is_enabled_for"""
        comment = "Comment"

        self.spy_on(SandboxReviewUI.is_enabled_for)

        review = Review.objects.create(review_request=self.review_request,
                                       user=self.user)
        review.file_attachment_comments.create(
            file_attachment=self.file_attachment2,
            text=comment)

        self.client.login(username='doc', password='doc')
        response = self.client.get('/r/%d/' % self.review_request.pk)
        self.assertEqual(response.status_code, 200)

        self.assertTrue(SandboxReviewUI.is_enabled_for.called)

    def test_get_comment_thumbnail(self):
        """Testing FileAttachmentReviewUI sandboxes get_comment_thumbnail"""
        comment = "Comment"

        review = Review.objects.create(review_request=self.review_request,
                                       user=self.user)
        file_attachment_comment = review.file_attachment_comments.create(
            file_attachment=self.file_attachment2,
            text=comment)

        review_ui = file_attachment_comment.review_ui
        self.spy_on(review_ui.get_comment_thumbnail)

        file_attachment_comment.thumbnail

        self.assertTrue(review_ui.get_comment_thumbnail.called)

    def test_get_comment_link_url(self):
        """Testing FileAttachmentReviewUI sandboxes get_comment_link_url"""
        comment = "Comment"

        review = Review.objects.create(review_request=self.review_request,
                                       user=self.user)
        file_attachment_comment = review.file_attachment_comments.create(
            file_attachment=self.file_attachment2,
            text=comment)

        review_ui = file_attachment_comment.review_ui
        self.spy_on(review_ui.get_comment_link_url)

        file_attachment_comment.get_absolute_url()

        self.assertTrue(review_ui.get_comment_link_url.called)

    def test_get_comment_link_text(self):
        """Testing FileAttachmentReviewUI sandboxes get_comment_link_text"""
        comment = "Comment"

        review = Review.objects.create(review_request=self.review_request,
                                       user=self.user)
        file_attachment_comment = review.file_attachment_comments.create(
            file_attachment=self.file_attachment2,
            text=comment)

        review_ui = file_attachment_comment.review_ui
        self.spy_on(review_ui.get_comment_link_text)

        file_attachment_comment.get_link_text()

        self.assertTrue(review_ui.get_comment_link_text.called)

    def test_get_extra_context(self):
        """Testing FileAttachmentReviewUI sandboxes get_extra_context"""
        review_ui = self.file_attachment2.review_ui
        request = self.factory.get('test')
        request.user = self.user

        self.spy_on(review_ui.get_extra_context)

        review_ui.render_to_string(request=request)

        self.assertTrue(review_ui.get_extra_context.called)

    def test_get_js_model_data(self):
        """Testing FileAttachmentReviewUI sandboxes get_js_model_data"""
        review_ui = self.file_attachment3.review_ui
        request = self.factory.get('test')
        request.user = self.user

        self.spy_on(review_ui.get_js_model_data)

        review_ui.render_to_response(request=request)

        self.assertTrue(review_ui.get_js_model_data.called)

    def test_get_js_view_data(self):
        """Testing FileAttachmentReviewUI sandboxes get_js_view_data"""
        review_ui = self.file_attachment2.review_ui
        request = self.factory.get('test')
        request.user = self.user

        self.spy_on(review_ui.get_js_view_data)

        review_ui.render_to_response(request=request)

        self.assertTrue(review_ui.get_js_view_data.called)

    def test_serialize_comments(self):
        """Testing FileAttachmentReviewUI sandboxes serialize_comments"""
        review_ui = self.file_attachment2.review_ui

        self.spy_on(review_ui.serialize_comments)

        review_ui.get_comments_json()

        self.assertTrue(review_ui.serialize_comments.called)

    def test_serialize_comment(self):
        """Testing FileAttachmentReviewUI sandboxes serialize_comment"""
        comment = 'comment'

        review_ui = self.file_attachment3.review_ui
        request = self.factory.get('test')
        request.user = self.user
        review_ui.request = request

        review = Review.objects.create(review_request=self.review_request,
                                       user=self.user, public=True)
        file_attachment_comment = review.file_attachment_comments.create(
            file_attachment=self.file_attachment3,
            text=comment)

        self.spy_on(review_ui.serialize_comment)

        serial_comments = review_ui.serialize_comments(
            comments=[file_attachment_comment])
        self.assertEqual(len(serial_comments), 0)

        self.assertTrue(review_ui.serialize_comment.called)
