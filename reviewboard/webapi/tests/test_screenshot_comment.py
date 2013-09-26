from djblets.testing.decorators import add_fixtures
from djblets.webapi.errors import PERMISSION_DENIED

from reviewboard.reviews.models import ScreenshotComment
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import screenshot_comment_list_mimetype
from reviewboard.webapi.tests.urls import get_screenshot_comment_list_url


class ResourceListTests(BaseWebAPITestCase):
    """Testing the ScreenshotCommentResource list APIs."""
    fixtures = ['test_users']

    #
    # HTTP GET tests
    #

    def test_get(self):
        """Testing the
        GET review-requests/<id>/screenshots/<id>/comments/ API
        """
        comment_text = "This is a test comment."
        x, y, w, h = (2, 2, 10, 10)

        review_request = self.create_review_request(publish=True)
        screenshot = self.create_screenshot(review_request)
        review = self.create_review(review_request, user=self.user)

        self._postNewScreenshotComment(review_request, review.id, screenshot,
                                       comment_text, x, y, w, h)

        rsp = self.apiGet(
            get_screenshot_comment_list_url(review),
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
    def test_get_with_site(self):
        """Testing the GET review-requests/<id>/screenshots/<id>/comments/ API
        with a local site
        """
        comment_text = 'This is a test comment.'
        x, y, w, h = (2, 2, 10, 10)

        user = self._login_user(local_site=True)

        review_request = self.create_review_request(with_local_site=True,
                                                    publish=True)
        screenshot = self.create_screenshot(review_request)
        review = self.create_review(review_request, user=user)

        self._postNewScreenshotComment(review_request, review.id, screenshot,
                                       comment_text, x, y, w, h)

        rsp = self.apiGet(
            get_screenshot_comment_list_url(review, self.local_site_name),
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
    def test_get_with_site_no_access(self):
        """Testing the GET review-requests/<id>/screenshots/<id>/comments/ API
        with a local site and Permission Denied error
        """
        comment_text = 'This is a test comment.'
        x, y, w, h = (2, 2, 10, 10)

        user = self._login_user(local_site=True)

        review_request = self.create_review_request(with_local_site=True,
                                                    publish=True)
        screenshot = self.create_screenshot(review_request)
        review = self.create_review(review_request, user=user)

        self._postNewScreenshotComment(review_request, review.id, screenshot,
                                       comment_text, x, y, w, h)

        self._login_user()

        rsp = self.apiGet(
            get_screenshot_comment_list_url(review, self.local_site_name),
            expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)


class ResourceItemTests(BaseWebAPITestCase):
    """Testing the ScreenshotCommentResource item APIs."""
    fixtures = ['test_users']
