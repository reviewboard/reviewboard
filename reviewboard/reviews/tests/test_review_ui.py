"""Unit tests for reviewboard.reviews.ui.base.FileAttachmentReviewUI."""
from __future__ import unicode_literals

from django.utils.safestring import SafeText
from kgb import SpyAgency

from reviewboard.reviews.models import FileAttachmentComment
from reviewboard.reviews.ui.base import ReviewUI
from reviewboard.testing import TestCase


class DummyReviewableObject(object):
    pass


class MyReviewUI(ReviewUI):
    """A basic file attachment Review UI used for testing."""

    supported_mimetypes = ['application/rbtest']
    supports_diffing = True
    js_model_class = 'RB.Test.ReviewUI'
    js_view_class = 'RB.Test.ReviewUIView'

    def get_caption(self, draft=None):
        return 'Test Caption'

    def get_comments(self):
        return FileAttachmentComment.objects.order_by('pk')

    def get_page_cover_image_url(self):
        return '/cover-image.png'

    def get_extra_context(self, request):
        return {
            'custom_key': '123',
        }


class FileAttachmentReviewUITests(SpyAgency, TestCase):
    """Unit tests for reviewboard.reviews.ui.base.FileAttachmentReviewUI."""

    fixtures = ['test_users']

    def setUp(self):
        super(FileAttachmentReviewUITests, self).setUp()

        self.review_request = self.create_review_request()
        self.attachment = self.create_file_attachment(self.review_request)
        self.review = self.create_review(self.review_request, public=False)
        self.create_file_attachment_comment(self.review,
                                            self.attachment,
                                            text='Comment 1')
        self.create_file_attachment_comment(self.review,
                                            self.attachment,
                                            text='Comment 2',
                                            issue_opened=True)

    def test_build_render_context(self):
        """Testing ReviewUI.build_render_context"""
        reviewable_obj1 = DummyReviewableObject()
        reviewable_obj2 = DummyReviewableObject()

        review_ui = MyReviewUI(review_request=self.review_request,
                               obj=reviewable_obj2)
        review_ui.set_diff_against(reviewable_obj1)

        request = self.create_http_request(user=self.review.user)
        context = review_ui.build_render_context(request=request)

        self.assertEqual(context['base_template'], 'reviews/ui/base.html')
        self.assertEqual(context['caption'], 'Test Caption')
        self.assertEqual(context['social_page_image_url'], '/cover-image.png')
        self.assertEqual(context['social_page_title'],
                         'Reviewable for Review Request #1: Test Caption')
        self.assertEqual(context['review_request'], self.review_request)
        self.assertEqual(context['review_request_details'],
                         self.review_request)
        self.assertEqual(context['review'], self.review)
        self.assertFalse(context['review_ui_inline'])
        self.assertFalse(context['draft'])
        self.assertIs(context['review_ui'], review_ui)
        self.assertIs(context['obj'], reviewable_obj2)
        self.assertIs(context['diff_against_obj'], reviewable_obj1)
        self.assertIn('close_description', context)
        self.assertIn('close_description_rich_text', context)
        self.assertIn('last_activity_time', context)
        self.assertIn('review_ui_uuid', context)
        self.assertEqual(context['custom_key'], '123')

        self.assertEqual(len(context['comments']), 2)
        self.assertEqual(context['comments'][0].text, 'Comment 1')
        self.assertEqual(context['comments'][1].text, 'Comment 2')

    def test_build_render_context_with_inline_true(self):
        """Testing ReviewUI.build_render_context"""
        reviewable_obj1 = DummyReviewableObject()
        reviewable_obj2 = DummyReviewableObject()

        review_ui = MyReviewUI(review_request=self.review_request,
                               obj=reviewable_obj2)
        review_ui.set_diff_against(reviewable_obj1)

        request = self.create_http_request()
        context = review_ui.build_render_context(request=request,
                                                 inline=True)

        self.assertEqual(context['base_template'],
                         'reviews/ui/base_inline.html')
        self.assertEqual(context['caption'], 'Test Caption')
        self.assertEqual(context['social_page_image_url'], '/cover-image.png')
        self.assertEqual(context['social_page_title'],
                         'Reviewable for Review Request #1: Test Caption')
        self.assertEqual(context['review_request'], self.review_request)
        self.assertEqual(context['review_request_details'],
                         self.review_request)
        self.assertTrue(context['review_ui_inline'])
        self.assertFalse(context['draft'])
        self.assertIs(context['review_ui'], review_ui)
        self.assertIs(context['obj'], reviewable_obj2)
        self.assertIs(context['diff_against_obj'], reviewable_obj1)
        self.assertIn('close_description', context)
        self.assertIn('close_description_rich_text', context)
        self.assertIn('last_activity_time', context)
        self.assertIn('social_page_image_url', context)
        self.assertIn('review_ui_uuid', context)
        self.assertNotIn('review', context)
        self.assertEqual(context['custom_key'], '123')

        self.assertEqual(len(context['comments']), 2)
        self.assertEqual(context['comments'][0].text, 'Comment 1')
        self.assertEqual(context['comments'][1].text, 'Comment 2')

    def test_get_comments_json(self):
        """Testing ReviewUI.get_comments_json"""
        review_ui = MyReviewUI(review_request=self.review_request,
                               obj=DummyReviewableObject())
        review_ui.request = self.create_http_request(user=self.review.user)

        comments_json = review_ui.get_comments_json()

        self.assertEqual(
            comments_json,
            '['
            '{"comment_id": 1,'
            ' "html": "Comment 1",'
            ' "issue_opened": false,'
            ' "issue_status": "",'
            ' "localdraft": true,'
            ' "review_id": 1,'
            ' "review_request_id": 1,'
            ' "rich_text": false,'
            ' "text": "Comment 1",'
            ' "url": "/r/1/#fcomment1",'
            ' "user": {"name": "Dopey Dwarf", "username": "dopey"}'
            '}, '
            '{"comment_id": 2,'
            ' "html": "Comment 2",'
            ' "issue_opened": true,'
            ' "issue_status": "open",'
            ' "localdraft": true,'
            ' "review_id": 1,'
            ' "review_request_id": 1,'
            ' "rich_text": false,'
            ' "text": "Comment 2",'
            ' "url": "/r/1/#fcomment2",'
            ' "user": {"name": "Dopey Dwarf", "username": "dopey"}'
            '}]'
        )

    def test_render_to_response_with_inline_false(self):
        """Testing ReviewUI.render_to_response with inline=0"""
        review_ui = MyReviewUI(review_request=self.review_request,
                               obj=DummyReviewableObject())
        request = self.create_http_request(data={
            'inline': '0',
        })

        response = review_ui.render_to_response(request)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'model: new RB.Test.ReviewUI(',
                      response.content)
        self.assertIn(b'view = new RB.Test.ReviewUIView(',
                      response.content)
        self.assertIn(b'renderedInline: false', response.content)

    def test_render_to_response_with_inline_true(self):
        """Testing ReviewUI.render_to_response with inline=1"""
        review_ui = MyReviewUI(review_request=self.review_request,
                               obj=DummyReviewableObject())
        request = self.create_http_request(data={
            'inline': '1',
        })

        response = review_ui.render_to_response(request)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'model: new RB.Test.ReviewUI(',
                      response.content)
        self.assertIn(b'view = new RB.Test.ReviewUIView(',
                      response.content)
        self.assertIn(b'renderedInline: true', response.content)

    def test_render_to_string_with_inline_false(self):
        """Testing ReviewUI.render_to_string with inline=False"""
        review_ui = MyReviewUI(review_request=self.review_request,
                               obj=DummyReviewableObject())
        request = self.create_http_request()

        content = review_ui.render_to_string(request, inline=False)
        self.assertIsInstance(content, SafeText)
        self.assertIn('model: new RB.Test.ReviewUI(', content)
        self.assertIn('view = new RB.Test.ReviewUIView(', content)
        self.assertIn('renderedInline: false', content)

    def test_render_to_string_with_inline_true(self):
        """Testing ReviewUI.render_to_string with inline=True"""
        review_ui = MyReviewUI(review_request=self.review_request,
                               obj=DummyReviewableObject())
        request = self.create_http_request()

        content = review_ui.render_to_string(request, inline=True)
        self.assertIsInstance(content, SafeText)
        self.assertIn('model: new RB.Test.ReviewUI(', content)
        self.assertIn('view = new RB.Test.ReviewUIView(', content)
        self.assertIn('renderedInline: true', content)

    def test_serialize_comments(self):
        """Testing ReviewUI.serialize_comments"""
        # Note that this test is factoring in both the user-owned draft
        # review created in setUp() and the ones created in this test.
        #
        # Comments from review1 and review2 will be included in the results.
        review1 = self.review

        review2 = self.create_review(self.review_request)
        self.create_file_attachment_comment(review2, self.attachment,
                                            text='Comment 3')

        # This will not be included.
        review3 = self.create_review(self.review_request,
                                     user=self.create_user('user2'),
                                     public=False)
        self.create_file_attachment_comment(review3, self.attachment,
                                            text='Comment 4')

        review_ui = MyReviewUI(review_request=self.review_request,
                               obj=DummyReviewableObject())
        review_ui.request = self.create_http_request(user=review1.user)

        comments = review_ui.serialize_comments(review_ui.get_comments())

        self.assertEqual(len(comments), 3)
        self.assertEqual(comments[0]['text'], 'Comment 1')
        self.assertEqual(comments[1]['text'], 'Comment 2')
        self.assertEqual(comments[2]['text'], 'Comment 3')

    def test_serialize_comment(self):
        """Testing ReviewUI.serialize_comment"""
        review_ui = MyReviewUI(review_request=self.review_request,
                               obj=DummyReviewableObject())
        review_ui.request = self.create_http_request(user=self.review.user)

        self.assertEqual(
            review_ui.serialize_comment(review_ui.get_comments()[0]),
            {
                'comment_id': 1,
                'html': 'Comment 1',
                'issue_opened': False,
                'issue_status': '',
                'localdraft': True,
                'review_id': 1,
                'review_request_id': 1,
                'rich_text': False,
                'text': 'Comment 1',
                'url': '/r/1/#fcomment1',
                'user': {'name': 'Dopey Dwarf', 'username': 'dopey'}
            })
