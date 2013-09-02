from django.contrib.auth.models import User
from djblets.testing.decorators import add_fixtures

from reviewboard.reviews.models import Review, ReviewRequest, Screenshot
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import (
    review_item_mimetype,
    screenshot_comment_list_mimetype)
from reviewboard.webapi.tests.urls import (get_review_list_url,
                                           get_screenshot_comment_list_url)


class DraftReviewScreenshotCommentResourceTests(BaseWebAPITestCase):
    """Testing the ReviewScreenshotCommentResource APIs."""
    fixtures = ['test_users', 'test_scmtools']

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

        rsp = self.apiPost(get_review_list_url(review_request),
                           expected_mimetype=review_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('review' in rsp)
        review_id = rsp['review']['id']
        review = Review.objects.get(pk=review_id)

        self._postNewScreenshotComment(review_request, review_id, screenshot,
                                       screenshot_comment_text, x, y, w, h)

        rsp = self.apiGet(get_screenshot_comment_list_url(review),
                          expected_mimetype=screenshot_comment_list_mimetype)
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
            get_review_list_url(review_request, self.local_site_name),
            expected_mimetype=review_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('review' in rsp)
        review_id = rsp['review']['id']
        review = Review.objects.get(pk=review_id)

        self._postNewScreenshotComment(review_request, review_id, screenshot,
                                       screenshot_comment_text, x, y, w, h)

        rsp = self.apiGet(
            get_screenshot_comment_list_url(review, self.local_site_name),
            expected_mimetype=screenshot_comment_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('screenshot_comments' in rsp)
        self.assertEqual(len(rsp['screenshot_comments']), 1)
        self.assertEqual(rsp['screenshot_comments'][0]['text'],
                         screenshot_comment_text)
