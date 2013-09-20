from djblets.testing.decorators import add_fixtures

from reviewboard.reviews.models import FileAttachmentComment
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import (
    review_reply_file_attachment_comment_item_mimetype)
from reviewboard.webapi.tests.urls import (
    get_review_reply_file_attachment_comment_item_url,
    get_review_reply_file_attachment_comment_list_url)


class ResourceListTests(BaseWebAPITestCase):
    """Testing the ReviewReplyFileAttachmentCommentResource list APIs."""
    fixtures = ['test_users']

    #
    # HTTP POST tests
    #

    def test_post_with_file_attachment_comment(self):
        """Testing the POST
        review-requests/<id>/reviews/<id>/replies/<id>/file-attachment-comments/
        API
        """
        comment_text = "My Comment Text"

        review_request = self.create_review_request(submitter=self.user)
        file_attachment = self.create_file_attachment(review_request)
        review_request.publish(review_request.submitter)
        review = self.create_review(review_request)
        comment = self.create_file_attachment_comment(review, file_attachment)
        reply = self.create_reply(review, user=self.user)


        rsp = self.apiPost(
            get_review_reply_file_attachment_comment_list_url(reply),
            {
                'reply_to_id': comment.id,
                'text': comment_text,
            },
            expected_mimetype=(
                review_reply_file_attachment_comment_item_mimetype))
        self.assertEqual(rsp['stat'], 'ok')

        reply_comment = FileAttachmentComment.objects.get(
            pk=rsp['file_attachment_comment']['id'])
        self.assertEqual(reply_comment.text, comment_text)

    @add_fixtures(['test_site'])
    def test_post_with_file_attachment_comment_and_local_site(self):
        """Testing the POST
        review-requests/<id>/reviews/<id>/replies/<id>/file-attachment-comments/
        API with a local site
        """
        comment_text = "My Comment Text"

        review_request = self.create_review_request(submitter=self.user,
                                                    with_local_site=True,
                                                    publish=True)
        file_attachment = self.create_file_attachment(review_request)
        review = self.create_review(review_request, username='doc')
        comment = self.create_file_attachment_comment(review, file_attachment)

        user = self._login_user(local_site=True)
        reply = self.create_reply(review, user=user)

        rsp = self.apiPost(
            get_review_reply_file_attachment_comment_list_url(
                reply, self.local_site_name),
            {
                'reply_to_id': comment.id,
                'text': comment_text,
            },
            expected_mimetype=(
                review_reply_file_attachment_comment_item_mimetype))
        self.assertEqual(rsp['stat'], 'ok')

        reply_comment = FileAttachmentComment.objects.get(
            pk=rsp['file_attachment_comment']['id'])
        self.assertEqual(reply_comment.text, comment_text)

    def test_post_with_inactive_file_attachment_comment(self):
        """Testing the POST
        review-requests/<id>/reviews/<id>/replies/<id>/file-attachment-comments/
        API with inactive file attachment
        """
        comment_text = "My Comment Text"

        review_request = self.create_review_request(submitter=self.user)
        file_attachment = self.create_file_attachment(review_request)
        review_request.publish(review_request.submitter)

        review = self.create_review(review_request, username='doc')
        comment = self.create_file_attachment_comment(review, file_attachment)
        reply = self.create_reply(review, user=self.user)

        comments_url = get_review_reply_file_attachment_comment_list_url(reply)

        # Make the file attachment inactive.
        file_attachment = comment.file_attachment
        review_request = file_attachment.review_request.get()
        review_request.inactive_file_attachments.add(file_attachment)
        review_request.file_attachments.remove(file_attachment)

        # Now make the reply.
        rsp = self.apiPost(
            comments_url,
            {
                'reply_to_id': comment.id,
                'text': comment_text,
            },
            expected_mimetype=(
                review_reply_file_attachment_comment_item_mimetype))
        self.assertEqual(rsp['stat'], 'ok')

        reply_comment = FileAttachmentComment.objects.get(
            pk=rsp['file_attachment_comment']['id'])
        self.assertEqual(reply_comment.text, comment_text)

    def test_post_with_file_attachment_comment_http_303(self):
        """Testing the POST
        review-requests/<id>/reviews/<id>/replies/<id>/file-attachment-comments/
        API and 303 See Other
        """
        comment_text = "My New Comment Text"

        review_request = self.create_review_request(submitter=self.user,
                                                    publish=True)
        file_attachment = self.create_file_attachment(review_request)
        review = self.create_review(review_request)
        comment = self.create_file_attachment_comment(review, file_attachment)
        reply = self.create_reply(review, user=self.user)
        reply_comment = self.create_file_attachment_comment(
            reply, file_attachment, reply_to=comment)

        # Now post another reply to the same comment in the same review.
        rsp = self.apiPost(
            get_review_reply_file_attachment_comment_list_url(reply),
            {
                'reply_to_id': comment.pk,
                'text': comment_text
            },
            expected_status=303,
            expected_mimetype=(
                review_reply_file_attachment_comment_item_mimetype))

        self.assertEqual(rsp['stat'], 'ok')

        reply_comment = FileAttachmentComment.objects.get(
            pk=rsp['file_attachment_comment']['id'])
        self.assertEqual(reply_comment.text, comment_text)


class ResourceItemTests(BaseWebAPITestCase):
    """Testing the ReviewReplyFileAttachmentCommentResource item APIs."""
    fixtures = ['test_users']

    #
    # HTTP DELETE tests
    #

    def test_delete(self):
        """Testing the DELETE
        review-requests/<id>/reviews/<id>/replies/<id>/file-attachment-comments/<id>/
        API
        """
        review_request = self.create_review_request(submitter=self.user,
                                                    publish=True)
        file_attachment = self.create_file_attachment(review_request)
        review = self.create_review(review_request)
        comment = self.create_file_attachment_comment(review, file_attachment)
        reply = self.create_reply(review, user=self.user)
        reply_comment = self.create_file_attachment_comment(
            reply, file_attachment, reply_to=comment)

        self.apiDelete(get_review_reply_file_attachment_comment_item_url(
            reply, reply_comment.pk))

        comments = FileAttachmentComment.objects.filter(review=reply,
                                                        reply_to=comment)
        self.assertEqual(comments.count(), 0)

    @add_fixtures(['test_site'])
    def test_delete_with_local_site(self):
        """Testing the DELETE
        review-requests/<id>/reviews/<id>/replies/<id>/file-attachment-comments/<id>/
        API with a local site
        """
        review_request = self.create_review_request(submitter=self.user,
                                                    with_local_site=True,
                                                    publish=True)
        file_attachment = self.create_file_attachment(review_request)
        review = self.create_review(review_request)
        comment = self.create_file_attachment_comment(review, file_attachment)
        reply = self.create_reply(review, user=self.user)
        reply_comment = self.create_file_attachment_comment(
            reply, file_attachment, reply_to=comment)

        self.apiDelete(get_review_reply_file_attachment_comment_item_url(
            reply, reply_comment.pk, self.local_site_name))

        comments = FileAttachmentComment.objects.filter(review=reply,
                                                        reply_to=comment)
        self.assertEqual(comments.count(), 0)

    def test_delete_no_access(self):
        """Testing the DELETE
        review-requests/<id>/reviews/<id>/replies/<id>/file-attachment-comments/<id>/
        API and Permission Denied
        """
        review_request = self.create_review_request(submitter=self.user,
                                                    publish=True)
        file_attachment = self.create_file_attachment(review_request)
        review = self.create_review(review_request)
        comment = self.create_file_attachment_comment(review, file_attachment)
        reply = self.create_reply(review, user=self.user)
        reply_comment = self.create_file_attachment_comment(
            reply, file_attachment, reply_to=comment)

        self.client.login(username="doc", password="doc")

        self.apiDelete(
            get_review_reply_file_attachment_comment_item_url(
                reply, reply_comment.pk),
            expected_status=403)

    @add_fixtures(['test_site'])
    def test_delete_with_local_site_no_access(self):
        """Testing the DELETE
        review-requests/<id>/reviews/<id>/replies/<id>/file-attachment-comments/<id>/
        API with a local site and Permission Denied
        """
        review_request = self.create_review_request(submitter=self.user,
                                                    with_local_site=True,
                                                    publish=True)
        file_attachment = self.create_file_attachment(review_request)
        review = self.create_review(review_request)
        comment = self.create_file_attachment_comment(review, file_attachment)
        reply = self.create_reply(review, user=self.user)
        reply_comment = self.create_file_attachment_comment(
            reply, file_attachment, reply_to=comment)

        self._login_user(local_site=True)

        self.apiDelete(
            get_review_reply_file_attachment_comment_item_url(
                reply, reply_comment.pk, self.local_site_name),
            expected_status=403)

    #
    # HTTP PUT tests
    #

    def test_put_with_file_attachment_comment(self):
        """Testing the PUT
        review-requests/<id>/reviews/<id>/replies/<id>/file-attachment-comments/
        API
        """
        new_comment_text = 'My new comment text'

        review_request = self.create_review_request(submitter=self.user,
                                                    publish=True)
        file_attachment = self.create_file_attachment(review_request)
        review = self.create_review(review_request)
        comment = self.create_file_attachment_comment(review, file_attachment)
        reply = self.create_reply(review, user=self.user)
        reply_comment = self.create_file_attachment_comment(
            reply, file_attachment, reply_to=comment)

        rsp = self.apiPut(
            get_review_reply_file_attachment_comment_item_url(
                reply, reply_comment.pk),
            {'text': new_comment_text},
            expected_mimetype=(
                review_reply_file_attachment_comment_item_mimetype))
        self.assertEqual(rsp['stat'], 'ok')

        reply_comment = FileAttachmentComment.objects.get(
            pk=rsp['file_attachment_comment']['id'])
        self.assertEqual(reply_comment.text, new_comment_text)
