from django.contrib.auth.models import User
from djblets.testing.decorators import add_fixtures
from djblets.webapi.errors import PERMISSION_DENIED

from reviewboard.attachments.models import FileAttachment
from reviewboard.reviews.models import (FileAttachmentComment, ReviewRequest,
                                        Review)
from reviewboard.scmtools.models import Repository
from reviewboard.webapi.tests.base import BaseWebAPITestCase, _build_mimetype


class FileAttachmentCommentResourceTests(BaseWebAPITestCase):
    """Testing the FileAttachmentCommentResource APIs."""
    fixtures = ['test_users', 'test_scmtools']

    list_mimetype = _build_mimetype('file-attachment-comments')
    item_mimetype = _build_mimetype('file-attachment-comment')

    def test_get_file_attachment_comments(self):
        """Testing the GET review-requests/<id>/file-attachments/<id>/comments/ API"""
        comment_text = "This is a test comment."

        # Post the review request
        rsp = self._postNewReviewRequest()
        review_request = ReviewRequest.objects.get(
            pk=rsp['review_request']['id'])

        # Post the file_attachment.
        rsp = self._postNewFileAttachment(review_request)
        file_attachment = FileAttachment.objects.get(
            pk=rsp['file_attachment']['id'])
        self.assertTrue('links' in rsp['file_attachment'])
        self.assertTrue('file_attachment_comments' in
                        rsp['file_attachment']['links'])
        comments_url = \
            rsp['file_attachment']['links']['file_attachment_comments']['href']

        # Make these public.
        review_request.publish(self.user)

        # Post the review.
        rsp = self._postNewReview(review_request)
        review = Review.objects.get(pk=rsp['review']['id'])

        self._postNewFileAttachmentComment(review_request, review.id,
                                           file_attachment, comment_text)

        rsp = self.apiGet(comments_url,
                          expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')

        comments = FileAttachmentComment.objects.filter(
            file_attachment=file_attachment)
        rsp_comments = rsp['file_attachment_comments']
        self.assertEqual(len(rsp_comments), comments.count())

        for i in range(0, len(comments)):
            self.assertEqual(rsp_comments[i]['text'], comments[i].text)

    @add_fixtures(['test_site'])
    def test_get_file_attachment_comments_with_site(self):
        """Testing the GET review-requests/<id>/file-attachments/<id>/comments/ API with a local site"""
        comment_text = 'This is a test comment.'

        self._login_user(local_site=True)

        # Post the review request.
        repo = Repository.objects.get(name='Review Board Git')
        rsp = self._postNewReviewRequest(local_site_name=self.local_site_name,
                                         repository=repo)
        self.assertEqual(rsp['stat'], 'ok')
        review_request = ReviewRequest.objects.get(
            local_site__name=self.local_site_name,
            local_id=rsp['review_request']['id'])

        # Post the file_attachment.
        rsp = self._postNewFileAttachment(review_request)
        file_attachment = FileAttachment.objects.get(
            pk=rsp['file_attachment']['id'])
        self.assertTrue('links' in rsp['file_attachment'])
        self.assertTrue('file_attachment_comments' in
                        rsp['file_attachment']['links'])
        comments_url = \
            rsp['file_attachment']['links']['file_attachment_comments']['href']

        # Make these public.
        review_request.publish(User.objects.get(username='doc'))

        # Post the review.
        rsp = self._postNewReview(review_request)
        review = Review.objects.get(pk=rsp['review']['id'])

        self._postNewFileAttachmentComment(review_request, review.id,
                                           file_attachment, comment_text)

        rsp = self.apiGet(comments_url,
                          expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')

        comments = FileAttachmentComment.objects.filter(
            file_attachment=file_attachment)
        rsp_comments = rsp['file_attachment_comments']
        self.assertEqual(len(rsp_comments), comments.count())

        for i in range(0, len(comments)):
            self.assertEqual(rsp_comments[i]['text'], comments[i].text)

    @add_fixtures(['test_site'])
    def test_get_file_attachment_comments_with_site_no_access(self):
        """Testing the GET review-requests/<id>/file-attachments/<id>/comments/ API with a local site and Permission Denied error"""
        comment_text = 'This is a test comment.'

        self._login_user(local_site=True)

        # Post the review request.
        repo = Repository.objects.get(name='Review Board Git')
        rsp = self._postNewReviewRequest(local_site_name=self.local_site_name,
                                         repository=repo)
        self.assertEqual(rsp['stat'], 'ok')
        review_request = ReviewRequest.objects.get(
            local_site__name=self.local_site_name,
            local_id=rsp['review_request']['id'])

        # Post the file_attachment.
        rsp = self._postNewFileAttachment(review_request)
        file_attachment = FileAttachment.objects.get(
            pk=rsp['file_attachment']['id'])
        self.assertTrue('links' in rsp['file_attachment'])
        self.assertTrue('file_attachment_comments' in
                        rsp['file_attachment']['links'])
        comments_url = \
            rsp['file_attachment']['links']['file_attachment_comments']['href']

        # Make these public.
        review_request.publish(User.objects.get(username='doc'))

        # Post the review.
        rsp = self._postNewReview(review_request)
        review = Review.objects.get(pk=rsp['review']['id'])

        self._postNewFileAttachmentComment(review_request, review.id,
                                           file_attachment, comment_text)

        self._login_user()

        rsp = self.apiGet(comments_url, expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    def test_post_file_attachment_comments_with_extra_fields(self):
        """Testing the POST review-requests/<id>/file-attachments/<id>/comments/ API with extra fields"""
        comment_text = "This is a test comment."
        extra_fields = {
            'extra_data.foo': '123',
            'extra_data.bar': '456',
            'extra_data.baz': '',
            'ignored': 'foo',
        }

        rsp = self._postNewReviewRequest()
        review_request = ReviewRequest.objects.get(
            pk=rsp['review_request']['id'])

        # Post the file_attachment.
        rsp = self._postNewFileAttachment(review_request)
        file_attachment = FileAttachment.objects.get(
            pk=rsp['file_attachment']['id'])
        self.assertTrue('links' in rsp['file_attachment'])
        self.assertTrue('file_attachment_comments' in
                        rsp['file_attachment']['links'])

        # Make these public.
        review_request.publish(self.user)

        # Post the review.
        rsp = self._postNewReview(review_request)
        review = Review.objects.get(pk=rsp['review']['id'])

        rsp = self._postNewFileAttachmentComment(review_request, review.id,
                                                 file_attachment, comment_text,
                                                 extra_fields=extra_fields)

        comment = FileAttachmentComment.objects.get(
            pk=rsp['file_attachment_comment']['id'])

        self.assertTrue('foo' in comment.extra_data)
        self.assertTrue('bar' in comment.extra_data)
        self.assertFalse('baz' in comment.extra_data)
        self.assertFalse('ignored' in comment.extra_data)
        self.assertEqual(comment.extra_data['foo'],
                         extra_fields['extra_data.foo'])
        self.assertEqual(comment.extra_data['bar'],
                         extra_fields['extra_data.bar'])

        return rsp

    def test_post_file_attachment_comments_with_diff(self):
        """Testing the POST review-requests/<id>/file-attachments/<id>/comments/ API with diffed file attachments"""
        comment_text = "This is a test comment."

        rsp = self._postNewReviewRequest()
        review_request = ReviewRequest.objects.get(
            pk=rsp['review_request']['id'])

        # Post the first file_attachment.
        rsp = self._postNewFileAttachment(review_request)
        file_attachment1 = FileAttachment.objects.get(
            pk=rsp['file_attachment']['id'])
        self.assertTrue('links' in rsp['file_attachment'])
        self.assertTrue('file_attachment_comments' in
                        rsp['file_attachment']['links'])

        # Post the second file_attachment.
        rsp = self._postNewFileAttachment(review_request)
        file_attachment2 = FileAttachment.objects.get(
            pk=rsp['file_attachment']['id'])
        self.assertTrue('links' in rsp['file_attachment'])
        self.assertTrue('file_attachment_comments' in
                        rsp['file_attachment']['links'])

        # Make these public.
        review_request.publish(self.user)

        # Post the review.
        rsp = self._postNewReview(review_request)
        review = Review.objects.get(pk=rsp['review']['id'])

        extra_fields = {
            'diff_against_file_attachment_id': file_attachment1.pk,
        }

        rsp = self._postNewFileAttachmentComment(review_request, review.id,
                                                 file_attachment2,
                                                 comment_text,
                                                 extra_fields=extra_fields)

        comment = FileAttachmentComment.objects.get(
            pk=rsp['file_attachment_comment']['id'])

        self.assertEqual(comment.file_attachment_id, file_attachment2.pk)
        self.assertEqual(comment.diff_against_file_attachment_id,
                         file_attachment1.pk)

        return rsp

    def test_put_file_attachment_comments_with_extra_fields(self):
        """Testing the PUT review-requests/<id>/file-attachments/<id>/comments/<id>/ API with extra fields"""
        extra_fields = {
            'extra_data.foo': 'abc',
            'extra_data.bar': '',
            'ignored': 'foo',
        }

        rsp = self.test_post_file_attachment_comments_with_extra_fields()

        rsp = self.apiPut(
            rsp['file_attachment_comment']['links']['self']['href'],
            extra_fields,
            expected_mimetype=self.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')

        comment = FileAttachmentComment.objects.get(
            pk=rsp['file_attachment_comment']['id'])

        self.assertTrue('foo' in comment.extra_data)
        self.assertFalse('bar' in comment.extra_data)
        self.assertFalse('ignored' in comment.extra_data)
        self.assertEqual(len(comment.extra_data.keys()), 1)
        self.assertEqual(comment.extra_data['foo'],
                         extra_fields['extra_data.foo'])

