from djblets.testing.decorators import add_fixtures

from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import (
    file_attachment_comment_list_mimetype)
from reviewboard.webapi.tests.urls import (
    get_review_file_attachment_comment_list_url)


class DraftReviewFileAttachmentCommentResourceTests(BaseWebAPITestCase):
    """Testing the ReviewFileAttachmentCommentResource APIs."""
    fixtures = ['test_users', 'test_scmtools']

    def test_get_review_file_attachment_comments(self):
        """Testing the GET review-requests/<id>/reviews/draft/file-attachment-comments/ API"""
        review_request = self.create_review_request(publish=True)
        file_attachment = self.create_file_attachment(review_request)
        review = self.create_review(review_request, user=self.user)
        comment = self.create_file_attachment_comment(review, file_attachment)

        rsp = self.apiGet(
            get_review_file_attachment_comment_list_url(review),
            expected_mimetype=file_attachment_comment_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('file_attachment_comments' in rsp)
        self.assertEqual(len(rsp['file_attachment_comments']), 1)
        self.assertEqual(rsp['file_attachment_comments'][0]['text'],
                         comment.text)

    @add_fixtures(['test_site'])
    def test_get_review_file_attachment_comments_with_site(self):
        """Testing the GET review-requests/<id>/reviews/draft/file-attachment-comments/ APIs with a local site"""
        user = self._login_user(local_site=True)

        review_request = self.create_review_request(with_local_site=True,
                                                    publish=True)
        file_attachment = self.create_file_attachment(review_request)
        review = self.create_review(review_request, user=user)
        comment = self.create_file_attachment_comment(review, file_attachment)

        rsp = self.apiGet(
            get_review_file_attachment_comment_list_url(review,
                                                        self.local_site_name),
            expected_mimetype=file_attachment_comment_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('file_attachment_comments' in rsp)
        self.assertEqual(len(rsp['file_attachment_comments']), 1)
        self.assertEqual(rsp['file_attachment_comments'][0]['text'],
                         comment.text)
