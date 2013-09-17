from djblets.testing.decorators import add_fixtures

from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import screenshot_comment_list_mimetype
from reviewboard.webapi.tests.urls import get_screenshot_comment_list_url


class DraftReviewScreenshotCommentResourceTests(BaseWebAPITestCase):
    """Testing the ReviewScreenshotCommentResource APIs."""
    fixtures = ['test_users', 'test_scmtools']

    #
    # List tests
    #

    def test_get_review_screenshot_comments(self):
        """Testing the
        GET review-requests/<id>/reviews/draft/screenshot-comments/ API
        """
        review_request = self.create_review_request(publish=True)
        screenshot = self.create_screenshot(review_request)
        review = self.create_review(review_request, user=self.user)
        comment = self.create_screenshot_comment(review, screenshot)

        rsp = self.apiGet(get_screenshot_comment_list_url(review),
                          expected_mimetype=screenshot_comment_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('screenshot_comments' in rsp)
        self.assertEqual(len(rsp['screenshot_comments']), 1)
        self.assertEqual(rsp['screenshot_comments'][0]['text'], comment.text)

    @add_fixtures(['test_site'])
    def test_get_review_screenshot_comments_with_site(self):
        """Testing the
        GET review-requests/<id>/reviews/draft/screenshot-comments/ APIs
        with a local site
        """
        user = self._login_user(local_site=True)

        review_request = self.create_review_request(with_local_site=True,
                                                    publish=True)
        screenshot = self.create_screenshot(review_request)
        review = self.create_review(review_request, user=user)
        comment = self.create_screenshot_comment(review, screenshot)

        rsp = self.apiGet(
            get_screenshot_comment_list_url(review, self.local_site_name),
            expected_mimetype=screenshot_comment_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('screenshot_comments' in rsp)
        self.assertEqual(len(rsp['screenshot_comments']), 1)
        self.assertEqual(rsp['screenshot_comments'][0]['text'], comment.text)
