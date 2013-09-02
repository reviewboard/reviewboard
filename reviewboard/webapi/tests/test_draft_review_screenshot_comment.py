from django.contrib.auth.models import User
from djblets.testing.decorators import add_fixtures

from reviewboard.reviews.models import Review, ReviewRequest, Screenshot
from reviewboard.site.urlresolvers import local_site_reverse
from reviewboard.webapi.tests.base import BaseWebAPITestCase, _build_mimetype
from reviewboard.webapi.tests.test_review import ReviewResourceTests


class DraftReviewScreenshotCommentResourceTests(BaseWebAPITestCase):
    """Testing the ReviewScreenshotCommentResource APIs."""
    fixtures = ['test_users', 'test_scmtools']

    list_mimetype = _build_mimetype('screenshot-comments')
    item_mimetype = _build_mimetype('screenshot-comment')

    def test_get_review_screenshot_comments(self):
        """Testing the GET review-requests/<id>/reviews/draft/screenshot-comments/ API"""
        screenshot_comment_text = "Test screenshot comment"
        x, y, w, h = 2, 2, 10, 10

        # Post the review request
        rsp = self._postNewReviewRequest()
        review_request = ReviewRequest.objects.get(
            pk=rsp['review_request']['id'])

        # Post the screenshot.
        rsp = self._postNewScreenshot(review_request)
        screenshot = Screenshot.objects.get(pk=rsp['screenshot']['id'])

        # Make these public.
        review_request.publish(self.user)

        rsp = self.apiPost(ReviewResourceTests.get_list_url(review_request),
                           expected_mimetype=ReviewResourceTests.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('review' in rsp)
        review_id = rsp['review']['id']
        review = Review.objects.get(pk=review_id)

        self._postNewScreenshotComment(review_request, review_id, screenshot,
                                       screenshot_comment_text, x, y, w, h)

        rsp = self.apiGet(self.get_list_url(review),
                          expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('screenshot_comments' in rsp)
        self.assertEqual(len(rsp['screenshot_comments']), 1)
        self.assertEqual(rsp['screenshot_comments'][0]['text'],
                         screenshot_comment_text)

    @add_fixtures(['test_reviewrequests', 'test_site'])
    def test_get_review_screenshot_comments_with_site(self):
        """Testing the GET review-requests/<id>/reviews/draft/screenshot-comments/ APIs with a local site"""
        screenshot_comment_text = "Test screenshot comment"
        x, y, w, h = 2, 2, 10, 10

        self._login_user(local_site=True)

        review_request = ReviewRequest.objects.filter(
            local_site__name=self.local_site_name)[0]

        rsp = self._postNewScreenshot(review_request)
        screenshot = Screenshot.objects.get(pk=rsp['screenshot']['id'])
        review_request.publish(User.objects.get(username='doc'))

        rsp = self.apiPost(
            ReviewResourceTests.get_list_url(review_request,
                                             self.local_site_name),
            expected_mimetype=ReviewResourceTests.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('review' in rsp)
        review_id = rsp['review']['id']
        review = Review.objects.get(pk=review_id)

        self._postNewScreenshotComment(review_request, review_id, screenshot,
                                       screenshot_comment_text, x, y, w, h)

        rsp = self.apiGet(self.get_list_url(review, self.local_site_name),
                          expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('screenshot_comments' in rsp)
        self.assertEqual(len(rsp['screenshot_comments']), 1)
        self.assertEqual(rsp['screenshot_comments'][0]['text'],
                         screenshot_comment_text)

    @classmethod
    def get_list_url(self, review, local_site_name=None):
        return local_site_reverse(
            'screenshot-comments-resource',
            local_site_name=local_site_name,
            kwargs={
                'review_request_id': review.review_request.display_id,
                'review_id': review.pk,
            })

    def get_item_url(self, review, comment_id, local_site_name=None):
        return local_site_reverse(
            'screenshot-comment-resource',
            local_site_name=local_site_name,
            kwargs={
                'review_request_id': review.review_request.display_id,
                'review_id': review.pk,
                'comment_id': comment_id,
            })
