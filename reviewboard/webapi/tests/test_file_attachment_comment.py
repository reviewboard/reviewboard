from djblets.testing.decorators import add_fixtures
from djblets.webapi.errors import PERMISSION_DENIED

from reviewboard.reviews.models import FileAttachmentComment
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import (
    file_attachment_comment_item_mimetype,
    file_attachment_comment_list_mimetype)
from reviewboard.webapi.tests.urls import (
    get_review_file_attachment_comment_item_url,
    get_file_attachment_comment_list_url)


class FileAttachmentCommentResourceTests(BaseWebAPITestCase):
    """Testing the FileAttachmentCommentResource APIs."""
    fixtures = ['test_users', 'test_scmtools']

    #
    # List tests
    #

    def test_get_file_attachment_comments(self):
        """Testing the
        GET review-requests/<id>/file-attachments/<id>/comments/ API
        """
        comment_text = "This is a test comment."

        # Post the review request.
        review_request = self.create_review_request(submitter=self.user,
                                                    publish=True)
        file_attachment = self.create_file_attachment(review_request)

        # Post the review.
        review = self.create_review(review_request, user=self.user)

        self._postNewFileAttachmentComment(review_request, review.id,
                                           file_attachment, comment_text)

        rsp = self.apiGet(
            get_file_attachment_comment_list_url(file_attachment),
            expected_mimetype=file_attachment_comment_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')

        comments = FileAttachmentComment.objects.filter(
            file_attachment=file_attachment)
        rsp_comments = rsp['file_attachment_comments']
        self.assertEqual(len(rsp_comments), comments.count())

        for i in range(0, len(comments)):
            self.assertEqual(rsp_comments[i]['text'], comments[i].text)

    @add_fixtures(['test_site'])
    def test_get_file_attachment_comments_with_site(self):
        """Testing the
        GET review-requests/<id>/file-attachments/<id>/comments/ API
        with a local site
        """
        user = self._login_user(local_site=True)

        # Post the review request.
        review_request = self.create_review_request(submitter=user,
                                                    with_local_site=True,
                                                    publish=True)
        file_attachment = self.create_file_attachment(review_request)

        # Post the review.
        review = self.create_review(review_request, user=user, publish=True)
        comment = self.create_file_attachment_comment(review, file_attachment)

        rsp = self.apiGet(
            get_file_attachment_comment_list_url(file_attachment,
                                                 self.local_site_name),
            expected_mimetype=file_attachment_comment_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')

        rsp_comments = rsp['file_attachment_comments']
        self.assertEqual(len(rsp_comments), 1)
        self.assertEqual(rsp_comments[0]['text'], comment.text)

    @add_fixtures(['test_site'])
    def test_get_file_attachment_comments_with_site_no_access(self):
        """Testing the
        GET review-requests/<id>/file-attachments/<id>/comments/ API
        with a local site and Permission Denied error
        """
        user = self._login_user(local_site=True)

        # Post the review request.
        review_request = self.create_review_request(submitter=user,
                                                    with_local_site=True,
                                                    publish=True)
        file_attachment = self.create_file_attachment(review_request)

        # Post the review.
        review = self.create_review(review_request, user=user)
        self.create_file_attachment_comment(review, file_attachment)

        # Switch users.
        self._login_user()

        rsp = self.apiGet(
            get_file_attachment_comment_list_url(file_attachment,
                                                 self.local_site_name),
            expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    def test_post_file_attachment_comments_with_extra_fields(self):
        """Testing the
        POST review-requests/<id>/file-attachments/<id>/comments/ API
        with extra fields
        """
        comment_text = "This is a test comment."
        extra_fields = {
            'extra_data.foo': '123',
            'extra_data.bar': '456',
            'extra_data.baz': '',
            'ignored': 'foo',
        }

        # Post the review request.
        review_request = self.create_review_request(submitter=self.user,
                                                    publish=True)
        file_attachment = self.create_file_attachment(review_request)

        # Post the review.
        review = self.create_review(review_request, user=self.user)

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
        """Testing the
        POST review-requests/<id>/file-attachments/<id>/comments/ API
        with diffed file attachments
        """
        comment_text = "This is a test comment."

        # Post the review request.
        review_request = self.create_review_request(submitter=self.user,
                                                    publish=True)
        file_attachment1 = self.create_file_attachment(review_request)
        file_attachment2 = self.create_file_attachment(review_request)

        # Post the review.
        review = self.create_review(review_request, user=self.user)

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

    #
    # Item tests
    #

    def test_put_file_attachment_comments_with_extra_fields(self):
        """Testing the
        PUT review-requests/<id>/file-attachments/<id>/comments/<id>/ API
        with extra fields
        """
        extra_fields = {
            'extra_data.foo': 'abc',
            'extra_data.bar': '',
            'ignored': 'foo',
        }

        comment_text = "This is a test comment."

        review_request = self.create_review_request(submitter=self.user,
                                                    publish=True)
        file_attachment = self.create_file_attachment(review_request)
        review = self.create_review(review_request, user=self.user)
        comment = self.create_file_attachment_comment(
            review, file_attachment, text=comment_text,
            extra_fields={
                'foo': '123',
                'bar': '456',
            })

        rsp = self.apiPut(
            get_review_file_attachment_comment_item_url(review, comment.pk),
            extra_fields,
            expected_mimetype=file_attachment_comment_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')

        comment = FileAttachmentComment.objects.get(
            pk=rsp['file_attachment_comment']['id'])

        self.assertTrue('foo' in comment.extra_data)
        self.assertFalse('bar' in comment.extra_data)
        self.assertFalse('ignored' in comment.extra_data)
        self.assertEqual(len(comment.extra_data.keys()), 1)
        self.assertEqual(comment.extra_data['foo'],
                         extra_fields['extra_data.foo'])
