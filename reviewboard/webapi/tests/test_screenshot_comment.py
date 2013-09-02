from django.contrib.auth.models import User
from djblets.testing.decorators import add_fixtures
from djblets.webapi.errors import PERMISSION_DENIED

from reviewboard.reviews.models import (Review, ReviewRequest, Screenshot,
                                        ScreenshotComment)
from reviewboard.scmtools.models import Repository
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import screenshot_comment_list_mimetype


class ScreenshotCommentResourceTests(BaseWebAPITestCase):
    """Testing the ScreenshotCommentResource APIs."""
    fixtures = ['test_users', 'test_scmtools']

    def test_get_screenshot_comments(self):
        """Testing the GET review-requests/<id>/screenshots/<id>/comments/ API"""
        comment_text = "This is a test comment."
        x, y, w, h = (2, 2, 10, 10)

        # Post the review request
        rsp = self._postNewReviewRequest()
        review_request = ReviewRequest.objects.get(
            pk=rsp['review_request']['id'])

        # Post the screenshot.
        rsp = self._postNewScreenshot(review_request)
        screenshot = Screenshot.objects.get(pk=rsp['screenshot']['id'])
        self.assertTrue('links' in rsp['screenshot'])
        self.assertTrue('screenshot_comments' in rsp['screenshot']['links'])
        comments_url = rsp['screenshot']['links']['screenshot_comments']['href']

        # Make these public.
        review_request.publish(self.user)

        # Post the review.
        rsp = self._postNewReview(review_request)
        review = Review.objects.get(pk=rsp['review']['id'])

        self._postNewScreenshotComment(review_request, review.id, screenshot,
                                       comment_text, x, y, w, h)

        rsp = self.apiGet(comments_url,
                          expected_mimetype=screenshot_comment_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')

        comments = ScreenshotComment.objects.filter(screenshot=screenshot)
        rsp_comments = rsp['screenshot_comments']
        self.assertEqual(len(rsp_comments), comments.count())

        for i in range(0, len(comments)):
            self.assertEqual(rsp_comments[i]['text'], comments[i].text)
            self.assertEqual(rsp_comments[i]['x'], comments[i].x)
            self.assertEqual(rsp_comments[i]['y'], comments[i].y)
            self.assertEqual(rsp_comments[i]['w'], comments[i].w)
            self.assertEqual(rsp_comments[i]['h'], comments[i].h)

    @add_fixtures(['test_site'])
    def test_get_screenshot_comments_with_site(self):
        """Testing the GET review-requests/<id>/screenshots/<id>/comments/ API with a local site"""
        comment_text = 'This is a test comment.'
        x, y, w, h = (2, 2, 10, 10)

        self._login_user(local_site=True)

        # Post the review request.
        repo = Repository.objects.get(name='Review Board Git')
        rsp = self._postNewReviewRequest(local_site_name=self.local_site_name,
                                         repository=repo)
        self.assertEqual(rsp['stat'], 'ok')
        review_request = ReviewRequest.objects.get(
            local_site__name=self.local_site_name,
            local_id=rsp['review_request']['id'])

        # Post the screenshot.
        rsp = self._postNewScreenshot(review_request)
        screenshot = Screenshot.objects.get(pk=rsp['screenshot']['id'])
        self.assertTrue('links' in rsp['screenshot'])
        self.assertTrue('screenshot_comments' in rsp['screenshot']['links'])
        comments_url = rsp['screenshot']['links']['screenshot_comments']['href']

        # Make these public.
        review_request.publish(User.objects.get(username='doc'))

        # Post the review.
        rsp = self._postNewReview(review_request)
        review = Review.objects.get(pk=rsp['review']['id'])

        self._postNewScreenshotComment(review_request, review.id, screenshot,
                                       comment_text, x, y, w, h)

        rsp = self.apiGet(comments_url,
                          expected_mimetype=screenshot_comment_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')

        comments = ScreenshotComment.objects.filter(screenshot=screenshot)
        rsp_comments = rsp['screenshot_comments']
        self.assertEqual(len(rsp_comments), comments.count())

        for i in range(0, len(comments)):
            self.assertEqual(rsp_comments[i]['text'], comments[i].text)
            self.assertEqual(rsp_comments[i]['x'], comments[i].x)
            self.assertEqual(rsp_comments[i]['y'], comments[i].y)
            self.assertEqual(rsp_comments[i]['w'], comments[i].w)
            self.assertEqual(rsp_comments[i]['h'], comments[i].h)

    @add_fixtures(['test_site'])
    def test_get_screenshot_comments_with_site_no_access(self):
        """Testing the GET review-requests/<id>/screenshots/<id>/comments/ API with a local site and Permission Denied error"""
        comment_text = 'This is a test comment.'
        x, y, w, h = (2, 2, 10, 10)

        self._login_user(local_site=True)

        # Post the review request.
        repo = Repository.objects.get(name='Review Board Git')
        rsp = self._postNewReviewRequest(local_site_name=self.local_site_name,
                                         repository=repo)
        self.assertEqual(rsp['stat'], 'ok')
        review_request = ReviewRequest.objects.get(
            local_site__name=self.local_site_name,
            local_id=rsp['review_request']['id'])

        # Post the screenshot.
        rsp = self._postNewScreenshot(review_request)
        screenshot = Screenshot.objects.get(pk=rsp['screenshot']['id'])
        self.assertTrue('links' in rsp['screenshot'])
        self.assertTrue('screenshot_comments' in rsp['screenshot']['links'])
        comments_url = rsp['screenshot']['links']['screenshot_comments']['href']

        # Make these public.
        review_request.publish(User.objects.get(username='doc'))

        # Post the review.
        rsp = self._postNewReview(review_request)
        review = Review.objects.get(pk=rsp['review']['id'])

        self._postNewScreenshotComment(review_request, review.id, screenshot,
                                       comment_text, x, y, w, h)

        self._login_user()

        rsp = self.apiGet(comments_url, expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)
