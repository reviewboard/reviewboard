from django.contrib.auth.models import User
from djblets.testing.decorators import add_fixtures

from reviewboard.reviews.models import (Screenshot, ScreenshotComment,
                                        Review, ReviewRequest)
from reviewboard.site.models import LocalSite
from reviewboard.webapi.tests.base import BaseWebAPITestCase, _build_mimetype
from reviewboard.webapi.tests.test_review_reply import ReviewReplyResourceTests


class ReviewReplyScreenshotCommentResourceTests(BaseWebAPITestCase):
    """Testing the ReviewReplyScreenshotCommentResource APIs."""
    fixtures = ['test_users', 'test_scmtools']

    list_mimetype = _build_mimetype('review-reply-screenshot-comments')
    item_mimetype = _build_mimetype('review-reply-screenshot-comment')

    def test_post_reply_with_screenshot_comment(self):
        """Testing the POST review-requests/<id>/reviews/<id>/replies/<id>/screenshot-comments/ API"""
        comment_text = "My Comment Text"
        x, y, w, h = 10, 10, 20, 20

        rsp = self._postNewReviewRequest()
        review_request = \
            ReviewRequest.objects.get(pk=rsp['review_request']['id'])

        rsp = self._postNewScreenshot(review_request)
        screenshot = Screenshot.objects.get(pk=rsp['screenshot']['id'])
        review_request.publish(self.user)

        rsp = self._postNewReview(review_request)
        review = Review.objects.get(pk=rsp['review']['id'])
        replies_url = rsp['review']['links']['replies']['href']

        rsp = self._postNewScreenshotComment(review_request, review.id,
                                             screenshot, comment_text,
                                             x, y, w, h)

        self.assertTrue('screenshot_comment' in rsp)
        self.assertEqual(rsp['screenshot_comment']['text'], comment_text)
        self.assertEqual(rsp['screenshot_comment']['x'], x)
        self.assertEqual(rsp['screenshot_comment']['y'], y)
        self.assertEqual(rsp['screenshot_comment']['w'], w)
        self.assertEqual(rsp['screenshot_comment']['h'], h)

        comment = ScreenshotComment.objects.get(
            pk=rsp['screenshot_comment']['id'])

        rsp = self.apiPost(
            replies_url,
            expected_mimetype=ReviewReplyResourceTests.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('reply' in rsp)
        self.assertNotEqual(rsp['reply'], None)
        self.assertTrue('links' in rsp['reply'])
        self.assertTrue('screenshot_comments' in rsp['reply']['links'])

        screenshot_comments_url = \
            rsp['reply']['links']['screenshot_comments']['href']

        rsp = self.apiPost(
            screenshot_comments_url,
            {
                'reply_to_id': comment.id,
                'text': comment_text,
            },
            expected_mimetype=self.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')

        reply_comment = ScreenshotComment.objects.get(
            pk=rsp['screenshot_comment']['id'])
        self.assertEqual(reply_comment.text, comment_text)
        self.assertEqual(reply_comment.reply_to, comment)

        return rsp, comment, screenshot_comments_url

    @add_fixtures(['test_reviewrequests', 'test_site'])
    def test_post_reply_with_screenshot_comment_and_local_site(self):
        """Testing the POST review-requests/<id>/reviews/<id>/replies/<id>/screenshot-comments/ API with a local site"""
        comment_text = "My Comment Text"
        x, y, w, h = 10, 10, 20, 20

        user = self._login_user(local_site=True)

        review_request = ReviewRequest.objects.filter(
            local_site__name=self.local_site_name)[0]

        rsp = self._postNewScreenshot(review_request)
        screenshot = Screenshot.objects.get(pk=rsp['screenshot']['id'])
        review_request.publish(user)

        rsp = self._postNewReview(review_request)
        review = Review.objects.get(pk=rsp['review']['id'])
        replies_url = rsp['review']['links']['replies']['href']

        rsp = self._postNewScreenshotComment(review_request, review.id,
                                             screenshot, comment_text,
                                             x, y, w, h)

        self.assertTrue('screenshot_comment' in rsp)
        self.assertEqual(rsp['screenshot_comment']['text'], comment_text)
        self.assertEqual(rsp['screenshot_comment']['x'], x)
        self.assertEqual(rsp['screenshot_comment']['y'], y)
        self.assertEqual(rsp['screenshot_comment']['w'], w)
        self.assertEqual(rsp['screenshot_comment']['h'], h)

        comment = ScreenshotComment.objects.get(
            pk=rsp['screenshot_comment']['id'])

        rsp = self.apiPost(
            replies_url,
            expected_mimetype=ReviewReplyResourceTests.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('reply' in rsp)
        self.assertNotEqual(rsp['reply'], None)
        self.assertTrue('links' in rsp['reply'])
        self.assertTrue('screenshot_comments' in rsp['reply']['links'])

        screenshot_comments_url = \
            rsp['reply']['links']['screenshot_comments']['href']

        post_data = {
            'reply_to_id': comment.id,
            'text': comment_text,
        }

        rsp = self.apiPost(screenshot_comments_url, post_data,
                           expected_mimetype=self.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')

        reply_comment = ScreenshotComment.objects.get(
            pk=rsp['screenshot_comment']['id'])
        self.assertEqual(reply_comment.text, comment_text)

        return rsp, comment, screenshot_comments_url

    def test_post_reply_with_screenshot_comment_http_303(self):
        """Testing the POST review-requests/<id>/reviews/<id>/replies/<id>/screenshot-comments/ API"""
        comment_text = "My Comment Text"

        rsp, comment, comments_url = \
            self.test_post_reply_with_screenshot_comment()

        # Now do it again.
        rsp = self.apiPost(
            comments_url,
            {
                'reply_to_id': comment.pk,
                'text': comment_text
            },
            expected_status=303,
            expected_mimetype=self.item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')

        reply_comment = ScreenshotComment.objects.get(
            pk=rsp['screenshot_comment']['id'])
        self.assertEqual(reply_comment.text, comment_text)

    def test_delete_screenshot_comment(self):
        """Testing the DELETE review-requests/<id>/reviews/<id>/replies/<id>/screenshot-comments/<id>/ API"""
        rsp, comment, screenshot_comments_url = \
            self.test_post_reply_with_screenshot_comment()

        self.apiDelete(rsp['screenshot_comment']['links']['self']['href'])

        rsp = self.apiGet(screenshot_comments_url,
                          expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('screenshot_comments' in rsp)
        self.assertEqual(len(rsp['screenshot_comments']), 0)

    @add_fixtures(['test_reviewrequests', 'test_site'])
    def test_delete_screenshot_comment_with_local_site(self):
        """Testing the DELETE review-requests/<id>/reviews/<id>/replies/<id>/screenshot-comments/<id>/ API with a local site"""
        rsp, comment, screenshot_comments_url = \
            self.test_post_reply_with_screenshot_comment_and_local_site()

        self.apiDelete(rsp['screenshot_comment']['links']['self']['href'])

        rsp = self.apiGet(screenshot_comments_url,
                          expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('screenshot_comments' in rsp)
        self.assertEqual(len(rsp['screenshot_comments']), 0)

    def test_delete_screenshot_comment_no_access(self):
        """Testing the DELETE review-requests/<id>/reviews/<id>/replies/<id>/screenshot-comments/<id>/ API and Permission Denied"""
        rsp, comment, screenshot_comments_url = \
            self.test_post_reply_with_screenshot_comment()

        self.client.login(username="doc", password="doc")

        self.apiDelete(rsp['screenshot_comment']['links']['self']['href'],
                       expected_status=403)

    @add_fixtures(['test_reviewrequests', 'test_site'])
    def test_delete_screenshot_comment_with_local_site_no_access(self):
        """Testing the DELETE review-requests/<id>/reviews/<id>/replies/<id>/screenshot-comments/<id>/ API with a local site and Permission Denied"""
        rsp, comment, screenshot_comments_url = \
            self.test_post_reply_with_screenshot_comment_and_local_site()

        local_site = LocalSite.objects.get(name=self.local_site_name)
        local_site.users.add(User.objects.get(username='grumpy'))

        self.client.login(username="grumpy", password="grumpy")

        self.apiDelete(rsp['screenshot_comment']['links']['self']['href'],
                       expected_status=403)
