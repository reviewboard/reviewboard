"""Unit tests for reviewboard.reviews.ui.base.FileAttachmentReviewUI."""
from __future__ import unicode_literals

from djblets.testing.decorators import add_fixtures
from kgb import SpyAgency

from reviewboard.reviews.ui.base import (FileAttachmentReviewUI,
                                         register_ui,
                                         unregister_ui)
from reviewboard.testing import TestCase


class MyReviewUI(FileAttachmentReviewUI):
    """A basic file attachment Review UI used for testing."""

    supported_mimetypes = ['application/rbtest']
    supports_diffing = True


class FileAttachmentReviewUITests(SpyAgency, TestCase):
    """Unit tests for reviewboard.reviews.ui.base.FileAttachmentReviewUI."""

    fixtures = ['test_users']

    @classmethod
    def setUpClass(cls):
        super(FileAttachmentReviewUITests, cls).setUpClass()

        register_ui(MyReviewUI)

    @classmethod
    def tearDownClass(cls):
        super(FileAttachmentReviewUITests, cls).tearDownClass()

        unregister_ui(MyReviewUI)

    def setUp(self):
        super(FileAttachmentReviewUITests, self).setUp()

        self.review_request = self.create_review_request()

    def test_for_type(self):
        """Testing FileAttachmentReviewUI.for_type with match"""

    def test_for_type_with_exception(self):
        """Testing FileAttachmentReviewUI.for_type sandboxes ReviewUI
        instantiation
        """
        class BrokenReviewUI(FileAttachmentReviewUI):
            supported_mimetypes = ['image/broken']

            def __init__(self, *args, **kwargs):
                raise Exception('Oh no')

        self.spy_on(BrokenReviewUI.__init__,
                    owner=BrokenReviewUI)
        register_ui(BrokenReviewUI)

        try:
            attachment = self.create_file_attachment(self.review_request,
                                                     mimetype='image/broken')

            review_ui = FileAttachmentReviewUI.for_type(attachment)

            self.assertIsNone(review_ui)
            self.assertTrue(BrokenReviewUI.__init__.called_with(
                self.review_request,
                attachment))
        finally:
            unregister_ui(BrokenReviewUI)

    def test_build_render_context_with_inline_true(self):
        """Testing FileAttachmentReviewUI.build_render_context with inline=True
        """
        self.create_file_attachment(
            self.review_request,
            mimetype='application/rbtest',
            caption='My Attachment 1')
        attachment = self.create_file_attachment(
            self.review_request,
            mimetype='application/rbtest',
            caption='My Attachment 2')
        self.create_file_attachment(
            self.review_request,
            mimetype='application/rbtest',
            caption='My Attachment 3')

        review_ui = attachment.review_ui
        request = self.create_http_request(path='/r/1/file/2/')

        self.assertIsInstance(review_ui, MyReviewUI)

        context = review_ui.build_render_context(request=request, inline=True)
        self.assertEqual(context['base_template'],
                         'reviews/ui/base_inline.html')
        self.assertEqual(context['caption'], 'My Attachment 2')
        self.assertNotIn('prev_file_attachment', context)
        self.assertNotIn('next_file_attachment', context)

    def test_build_render_context_with_inline_false(self):
        """Testing FileAttachmentReviewUI.build_render_context with
        inline=False
        """
        attachment1 = self.create_file_attachment(
            self.review_request,
            mimetype='application/rbtest',
            caption='My Attachment 1')
        attachment2 = self.create_file_attachment(
            self.review_request,
            mimetype='application/rbtest',
            caption='My Attachment 2')
        attachment3 = self.create_file_attachment(
            self.review_request,
            mimetype='application/rbtest',
            caption='My Attachment 3')

        review_ui = attachment2.review_ui
        request = self.create_http_request(path='/r/1/file/2/')

        self.assertIsInstance(review_ui, MyReviewUI)

        context = review_ui.build_render_context(request=request, inline=False)
        self.assertEqual(context['base_template'], 'reviews/ui/base.html')
        self.assertEqual(context['caption'], 'My Attachment 2')
        self.assertEqual(context['social_page_title'],
                         'Attachment for Review Request #1: My Attachment 2')
        self.assertEqual(context['prev_file_attachment'], attachment1)
        self.assertEqual(context['next_file_attachment'], attachment3)
        self.assertEqual(
            context['tabs'],
            [
                {
                    'url': '/r/1/',
                    'text': 'Reviews',
                },
                {
                    'url': '/r/1/file/2/',
                    'text': 'File',
                },
            ])

    def test_get_caption(self):
        """Testing FileAttachmentReviewUI.get_caption"""
        attachment = self.create_file_attachment(
            self.review_request,
            mimetype='application/rbtest',
            caption='My Published Caption',
            draft_caption='My Draft Caption')
        review_ui = attachment.review_ui

        self.assertIsInstance(review_ui, MyReviewUI)
        self.assertEqual(review_ui.get_caption(), 'My Published Caption')

    def test_get_caption_with_draft(self):
        """Testing FileAttachmentReviewUI.get_caption with draft"""
        draft = self.create_review_request_draft(self.review_request)
        attachment = self.create_file_attachment(
            self.review_request,
            mimetype='application/rbtest',
            caption='My Published Caption',
            draft_caption='My Draft Caption',
            draft=True)
        review_ui = attachment.review_ui

        self.assertIsInstance(review_ui, MyReviewUI)
        self.assertEqual(review_ui.get_caption(draft), 'My Draft Caption')

    def test_get_comments(self):
        """Testing FileAttachmentReviewUI.get_comments"""
        attachment1 = self.create_file_attachment(
            self.review_request,
            mimetype='application/rbtest')
        attachment2 = self.create_file_attachment(
            self.review_request,
            mimetype='application/rbtest')

        review1 = self.create_review(self.review_request)
        review2 = self.create_review(self.review_request)

        # These will show up.
        comment1 = self.create_file_attachment_comment(
            review1,
            attachment1,
            text='Comment 1')
        comment2 = self.create_file_attachment_comment(
            review1,
            attachment1,
            text='Comment 2')
        comment3 = self.create_file_attachment_comment(
            review2,
            attachment1,
            text='Comment 3')

        # These will not.
        self.create_file_attachment_comment(
            review2,
            attachment2,
            text='Comment 4')
        self.create_file_attachment_comment(
            review2,
            attachment2,
            diff_against_file_attachment=attachment1,
            text='Comment 5')

        review_ui = attachment1.review_ui
        self.assertIsInstance(review_ui, MyReviewUI)

        comments = review_ui.get_comments()
        self.assertEqual(list(comments), [comment1, comment2, comment3])

    def test_get_comments_with_diff(self):
        """Testing FileAttachmentReviewUI.get_comments with diff"""
        attachment1 = self.create_file_attachment(
            self.review_request,
            mimetype='application/rbtest')
        attachment2 = self.create_file_attachment(
            self.review_request,
            mimetype='application/rbtest')

        review1 = self.create_review(self.review_request)
        review2 = self.create_review(self.review_request)

        # These will show up.
        comment1 = self.create_file_attachment_comment(
            review1,
            attachment2,
            diff_against_file_attachment=attachment1,
            text='Comment 1')
        comment2 = self.create_file_attachment_comment(
            review1,
            attachment2,
            diff_against_file_attachment=attachment1,
            text='Comment 2')
        comment3 = self.create_file_attachment_comment(
            review2,
            attachment2,
            diff_against_file_attachment=attachment1,
            text='Comment 3')

        # These will not.
        self.create_file_attachment_comment(
            review2,
            attachment1,
            text='Comment 4')
        self.create_file_attachment_comment(
            review2,
            attachment2,
            text='Comment 5')

        review_ui = attachment2.review_ui
        self.assertIsInstance(review_ui, MyReviewUI)
        review_ui.set_diff_against(attachment1)

        comments = review_ui.get_comments()
        self.assertEqual(list(comments), [comment1, comment2, comment3])

    def test_get_comment_link_text(self):
        """Testing FileAttachmentReviewUI.get_comment_link_text"""
        attachment = self.create_file_attachment(
            self.review_request,
            mimetype='application/rbtest',
            caption='Test Caption')
        review_ui = attachment.review_ui

        self.assertIsInstance(review_ui, MyReviewUI)

        review = self.create_review(self.review_request)
        comment = self.create_file_attachment_comment(review, attachment)

        self.assertEqual(review_ui.get_comment_link_text(comment),
                         'Test Caption')

    def test_get_comment_link_url(self):
        """Testing FileAttachmentReviewUI.get_comment_link_url"""
        attachment = self.create_file_attachment(self.review_request,
                                                 mimetype='application/rbtest')
        review_ui = attachment.review_ui

        self.assertIsInstance(review_ui, MyReviewUI)

        review = self.create_review(self.review_request)
        comment = self.create_file_attachment_comment(review, attachment)

        self.assertEqual(review_ui.get_comment_link_url(comment),
                         '/r/1/file/1/')

    @add_fixtures(['test_site'])
    def test_get_comment_link_url_with_local_site(self):
        """Testing FileAttachmentReviewUI.get_comment_link_url with LocalSite
        """
        review_request = self.create_review_request(with_local_site=True)
        attachment = self.create_file_attachment(review_request,
                                                 mimetype='application/rbtest')
        review_ui = attachment.review_ui

        self.assertIsInstance(review_ui, MyReviewUI)

        review = self.create_review(review_request)
        comment = self.create_file_attachment_comment(review, attachment)

        self.assertEqual(review_ui.get_comment_link_url(comment),
                         '/s/local-site-1/r/1001/file/1/')

    def test_get_js_model_data(self):
        """Testing FileAttachmentReviewUI.get_js_model_data"""
        attachment = self.create_file_attachment(
            self.review_request,
            mimetype='application/rbtest',
            orig_filename='filename.txt')
        review_ui = attachment.review_ui

        self.assertIsInstance(review_ui, MyReviewUI)
        self.assertEqual(
            review_ui.get_js_model_data(),
            {
                'fileAttachmentID': 1,
                'fileRevision': 0,
                'filename': 'filename.txt',
            })

    def test_get_js_model_data_with_history(self):
        """Testing FileAttachmentReviewUI.get_js_model_data with
        FileAttachmentHistory
        """
        attachment_history = self.create_file_attachment_history(
            self.review_request)
        attachment1 = self.create_file_attachment(
            self.review_request,
            attachment_history=attachment_history,
            attachment_revision=0,
            mimetype='application/rbtest',
            orig_filename='filename.txt')
        attachment2 = self.create_file_attachment(
            self.review_request,
            attachment_history=attachment_history,
            attachment_revision=1,
            mimetype='application/rbtest',
            orig_filename='filename.txt')
        review_ui = attachment2.review_ui

        self.assertIsInstance(review_ui, MyReviewUI)
        self.assertEqual(
            review_ui.get_js_model_data(),
            {
                'attachmentRevisionIDs': [attachment1.pk, attachment2.pk],
                'fileAttachmentID': attachment2.pk,
                'fileRevision': 1,
                'filename': 'filename.txt',
                'numRevisions': 2,
            })

    def test_get_js_model_data_with_diff(self):
        """Testing FileAttachmentReviewUI.get_js_model_data with diff"""
        attachment_history = self.create_file_attachment_history(
            self.review_request)
        attachment1 = self.create_file_attachment(
            self.review_request,
            attachment_history=attachment_history,
            attachment_revision=0,
            mimetype='application/rbtest',
            orig_filename='filename.txt',
            caption='My attachment 1')
        attachment2 = self.create_file_attachment(
            self.review_request,
            attachment_history=attachment_history,
            attachment_revision=1,
            mimetype='application/rbtest',
            orig_filename='filename.txt',
            caption='My attachment 2')

        review_ui = attachment2.review_ui
        review_ui.set_diff_against(attachment1)

        self.assertIsInstance(review_ui, MyReviewUI)
        self.assertEqual(
            review_ui.get_js_model_data(),
            {
                'attachmentRevisionIDs': [attachment1.pk, attachment2.pk],
                'diffAgainstFileAttachmentID': attachment1.pk,
                'diffCaption': 'My attachment 1',
                'diffRevision': 0,
                'fileAttachmentID': attachment2.pk,
                'fileRevision': 1,
                'filename': 'filename.txt',
                'numRevisions': 2,
            })

    def test_get_js_model_data_with_diff_type_mismatch(self):
        """Testing FileAttachmentReviewUI.get_js_model_data with diff type
        mismatch
        """
        attachment_history = self.create_file_attachment_history(
            self.review_request)
        attachment1 = self.create_file_attachment(
            self.review_request,
            attachment_history=attachment_history,
            attachment_revision=0,
            mimetype='image/png',
            orig_filename='filename.png',
            caption='My attachment 1')
        attachment2 = self.create_file_attachment(
            self.review_request,
            attachment_history=attachment_history,
            attachment_revision=1,
            mimetype='application/rbtest',
            orig_filename='filename.txt',
            caption='My attachment 2')

        review_ui = attachment2.review_ui
        review_ui.set_diff_against(attachment1)

        self.assertIsInstance(review_ui, MyReviewUI)
        self.assertEqual(
            review_ui.get_js_model_data(),
            {
                'attachmentRevisionIDs': [attachment1.pk, attachment2.pk],
                'diffAgainstFileAttachmentID': attachment1.pk,
                'diffCaption': 'My attachment 1',
                'diffRevision': 0,
                'diffTypeMismatch': True,
                'fileAttachmentID': attachment2.pk,
                'fileRevision': 1,
                'filename': 'filename.txt',
                'numRevisions': 2,
            })

    def test_serialize_comment(self):
        """Testing FileAttachmentReviewUI.serialize_comment"""
        attachment = self.create_file_attachment(self.review_request,
                                                 mimetype='application/rbtest')
        review_ui = attachment.review_ui
        review_ui.request = self.create_http_request()

        self.assertIsInstance(review_ui, MyReviewUI)

        review = self.create_review(self.review_request)
        comment = self.create_file_attachment_comment(
            review,
            attachment,
            text='My **test** comment',
            rich_text=True)

        self.assertEqual(
            review_ui.serialize_comment(comment),
            {
                'comment_id': 1,
                'html': '<p>My <strong>test</strong> comment</p>',
                'issue_opened': False,
                'issue_status': '',
                'localdraft': False,
                'review_id': 1,
                'review_request_id': 1,
                'rich_text': True,
                'text': 'My **test** comment',
                'url': '/r/1/#fcomment1',
                'user': {
                    'name': 'dopey',
                    'username': 'dopey',
                },
            })
