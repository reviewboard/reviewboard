from django.contrib.auth.models import User
from djblets.testing.decorators import add_fixtures

from reviewboard.reviews.models import FileAttachmentComment
from reviewboard.site.models import LocalSite
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import (
    review_reply_file_attachment_comment_item_mimetype,
    review_reply_file_attachment_comment_list_mimetype,
    review_reply_item_mimetype)
from reviewboard.webapi.tests.urls import get_review_reply_list_url


class ReviewReplyFileAttachmentCommentResourceTests(BaseWebAPITestCase):
    """Testing the ReviewReplyFileAttachmentCommentResource APIs."""
    fixtures = ['test_users', 'test_scmtools', 'test_reviewrequests']

    def test_post_reply_with_file_attachment_comment(self):
        """Testing the POST review-requests/<id>/reviews/<id>/replies/<id>/file-attachment-comments/ API"""
        comment_text = "My Comment Text"

        comment = FileAttachmentComment.objects.all()[0]
        review = comment.review.get()

        # Create the reply
        rsp = self.apiPost(
            get_review_reply_list_url(review),
            expected_mimetype=review_reply_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')

        self.assertTrue('reply' in rsp)
        self.assertNotEqual(rsp['reply'], None)
        self.assertTrue('links' in rsp['reply'])
        self.assertTrue('diff_comments' in rsp['reply']['links'])
        comments_url = \
            rsp['reply']['links']['file_attachment_comments']['href']

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

        return rsp, comment, comments_url

    @add_fixtures(['test_site'])
    def test_post_reply_with_file_attachment_comment_and_local_site(self):
        """Testing the POST review-requests/<id>/reviews/<id>/replies/<id>/file-attachment-comments/ API with a local site"""
        comment_text = "My Comment Text"

        comment = FileAttachmentComment.objects.all()[0]
        review = comment.review.get()
        review_request = review.review_request

        review.user = User.objects.get(username='doc')
        review.save()

        review_request.local_site = \
            LocalSite.objects.get(name=self.local_site_name)
        review_request.local_id = 42
        review_request.save()

        self._login_user(local_site=True)

        # Create the reply
        rsp = self.apiPost(
            get_review_reply_list_url(review, self.local_site_name),
            expected_mimetype=review_reply_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')

        self.assertTrue('reply' in rsp)
        self.assertNotEqual(rsp['reply'], None)
        self.assertTrue('links' in rsp['reply'])
        self.assertTrue('diff_comments' in rsp['reply']['links'])
        comments_url = \
            rsp['reply']['links']['file_attachment_comments']['href']

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

        return rsp, comment, comments_url

    def test_post_reply_with_inactive_file_attachment_comment(self):
        """Testing the POST review-requests/<id>/reviews/<id>/replies/<id>/file-attachment-comments/ API with inactive file attachment"""
        comment_text = "My Comment Text"

        comment = FileAttachmentComment.objects.all()[0]
        review = comment.review.get()

        # Create the reply
        rsp = self.apiPost(
            get_review_reply_list_url(review),
            expected_mimetype=review_reply_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')

        self.assertTrue('reply' in rsp)
        self.assertNotEqual(rsp['reply'], None)
        self.assertTrue('links' in rsp['reply'])
        self.assertTrue('diff_comments' in rsp['reply']['links'])
        comments_url = \
            rsp['reply']['links']['file_attachment_comments']['href']

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

        return rsp, comment, comments_url

    def test_post_reply_with_file_attachment_comment_http_303(self):
        """Testing the POST review-requests/<id>/reviews/<id>/replies/<id>/file-attachment-comments/ API and 303 See Other"""
        comment_text = "My New Comment Text"

        rsp, comment, comments_url = \
            self.test_post_reply_with_file_attachment_comment()

        # Now do it again.
        rsp = self.apiPost(
            comments_url,
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

    def test_put_reply_with_file_attachment_comment(self):
        """Testing the PUT review-requests/<id>/reviews/<id>/replies/<id>/file-attachment-comments/ API"""
        new_comment_text = 'My new comment text'

        # First, create a comment that we can update.
        rsp = self.test_post_reply_with_file_attachment_comment()[0]

        reply_comment = FileAttachmentComment.objects.get(
            pk=rsp['file_attachment_comment']['id'])

        rsp = self.apiPut(
            rsp['file_attachment_comment']['links']['self']['href'],
            {'text': new_comment_text},
            expected_mimetype=(
                review_reply_file_attachment_comment_item_mimetype))
        self.assertEqual(rsp['stat'], 'ok')

        reply_comment = FileAttachmentComment.objects.get(
            pk=rsp['file_attachment_comment']['id'])
        self.assertEqual(reply_comment.text, new_comment_text)

    def test_delete_file_attachment_comment(self):
        """Testing the DELETE review-requests/<id>/reviews/<id>/replies/<id>/file-attachment-comments/<id>/ API"""
        rsp, comment, file_attachment_comments_url = \
            self.test_post_reply_with_file_attachment_comment()

        self.apiDelete(rsp['file_attachment_comment']['links']['self']['href'])

        rsp = self.apiGet(
            file_attachment_comments_url,
            expected_mimetype=(
                review_reply_file_attachment_comment_list_mimetype))
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('file_attachment_comments' in rsp)
        self.assertEqual(len(rsp['file_attachment_comments']), 0)

    @add_fixtures(['test_reviewrequests', 'test_site'])
    def test_delete_file_attachment_comment_with_local_site(self):
        """Testing the DELETE review-requests/<id>/reviews/<id>/replies/<id>/file-attachment-comments/<id>/ API with a local site"""
        rsp, comment, file_attachment_comments_url = \
            self.test_post_reply_with_file_attachment_comment_and_local_site()

        self.apiDelete(rsp['file_attachment_comment']['links']['self']['href'])

        rsp = self.apiGet(
            file_attachment_comments_url,
            expected_mimetype=(
                review_reply_file_attachment_comment_list_mimetype))
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('file_attachment_comments' in rsp)
        self.assertEqual(len(rsp['file_attachment_comments']), 0)

    def test_delete_file_attachment_comment_no_access(self):
        """Testing the DELETE review-requests/<id>/reviews/<id>/replies/<id>/file-attachment-comments/<id>/ API and Permission Denied"""
        rsp, comment, file_attachment_comments_url = \
            self.test_post_reply_with_file_attachment_comment()

        self.client.login(username="doc", password="doc")

        self.apiDelete(rsp['file_attachment_comment']['links']['self']['href'],
                       expected_status=403)

    @add_fixtures(['test_reviewrequests', 'test_site'])
    def test_delete_file_attachment_comment_with_local_site_no_access(self):
        """Testing the DELETE review-requests/<id>/reviews/<id>/replies/<id>/file-attachment-comments/<id>/ API with a local site and Permission Denied"""
        rsp, comment, file_attachment_comments_url = \
            self.test_post_reply_with_file_attachment_comment_and_local_site()

        local_site = LocalSite.objects.get(name=self.local_site_name)
        local_site.users.add(User.objects.get(username='grumpy'))

        self.client.login(username="grumpy", password="grumpy")

        self.apiDelete(rsp['file_attachment_comment']['links']['self']['href'],
                       expected_status=403)
