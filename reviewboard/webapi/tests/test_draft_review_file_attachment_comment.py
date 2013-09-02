from django.contrib.auth.models import User
from djblets.testing.decorators import add_fixtures

from reviewboard.attachments.models import FileAttachment
from reviewboard.reviews.models import ReviewRequest, Review
from reviewboard.site.urlresolvers import local_site_reverse
from reviewboard.webapi.tests.base import BaseWebAPITestCase, _build_mimetype
from reviewboard.webapi.tests.test_review import ReviewResourceTests


class DraftReviewFileAttachmentCommentResourceTests(BaseWebAPITestCase):
    """Testing the ReviewFileAttachmentCommentResource APIs."""
    fixtures = ['test_users', 'test_scmtools']

    list_mimetype = _build_mimetype('file-attachment-comments')
    item_mimetype = _build_mimetype('file-attachment-comment')

    def test_get_review_file_attachment_comments(self):
        """Testing the GET review-requests/<id>/reviews/draft/file-attachment-comments/ API"""
        file_attachment_comment_text = "Test file attachment comment"

        # Post the review request
        rsp = self._postNewReviewRequest()
        review_request = ReviewRequest.objects.get(
            pk=rsp['review_request']['id'])

        # Post the file_attachment.
        rsp = self._postNewFileAttachment(review_request)
        file_attachment = \
            FileAttachment.objects.get(pk=rsp['file_attachment']['id'])

        # Make these public.
        review_request.publish(self.user)

        rsp = self.apiPost(ReviewResourceTests.get_list_url(review_request),
                           expected_mimetype=ReviewResourceTests.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('review' in rsp)
        review_id = rsp['review']['id']
        review = Review.objects.get(pk=review_id)

        self._postNewFileAttachmentComment(review_request, review_id,
                                           file_attachment,
                                           file_attachment_comment_text)

        rsp = self.apiGet(self.get_list_url(review),
                          expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('file_attachment_comments' in rsp)
        self.assertEqual(len(rsp['file_attachment_comments']), 1)
        self.assertEqual(rsp['file_attachment_comments'][0]['text'],
                         file_attachment_comment_text)

    @add_fixtures(['test_reviewrequests', 'test_site'])
    def test_get_review_file_attachment_comments_with_site(self):
        """Testing the GET review-requests/<id>/reviews/draft/file-attachment-comments/ APIs with a local site"""
        file_attachment_comment_text = "Test file_attachment comment"

        self._login_user(local_site=True)

        review_request = ReviewRequest.objects.filter(
            local_site__name=self.local_site_name)[0]

        rsp = self._postNewFileAttachment(review_request)
        file_attachment = \
            FileAttachment.objects.get(pk=rsp['file_attachment']['id'])
        review_request.publish(User.objects.get(username='doc'))

        rsp = self.apiPost(
            ReviewResourceTests.get_list_url(review_request,
                                             self.local_site_name),
            expected_mimetype=ReviewResourceTests.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('review' in rsp)
        review_id = rsp['review']['id']
        review = Review.objects.get(pk=review_id)

        self._postNewFileAttachmentComment(review_request, review_id,
                                           file_attachment,
                                           file_attachment_comment_text)

        rsp = self.apiGet(self.get_list_url(review, self.local_site_name),
                          expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('file_attachment_comments' in rsp)
        self.assertEqual(len(rsp['file_attachment_comments']), 1)
        self.assertEqual(rsp['file_attachment_comments'][0]['text'],
                         file_attachment_comment_text)

    @classmethod
    def get_list_url(self, review, local_site_name=None):
        return local_site_reverse(
            'file-attachment-comments-resource',
            local_site_name=local_site_name,
            kwargs={
                'review_request_id': review.review_request.display_id,
                'review_id': review.pk,
            })

    def get_item_url(self, review, comment_id, local_site_name=None):
        return local_site_reverse(
            'file-attachment-comment-resource',
            local_site_name=local_site_name,
            kwargs={
                'review_request_id': review.review_request.display_id,
                'review_id': review.pk,
                'comment_id': comment_id,
            })
