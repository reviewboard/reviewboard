from djblets.testing.decorators import add_fixtures

from reviewboard.reviews.models import ScreenshotComment
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import (
    review_reply_screenshot_comment_item_mimetype)
from reviewboard.webapi.tests.urls import (
    get_review_reply_screenshot_comment_item_url,
    get_review_reply_screenshot_comment_list_url)


class ResourceListTests(BaseWebAPITestCase):
    """Testing the ReviewReplyScreenshotCommentResource list APIs."""
    fixtures = ['test_users']

    #
    # HTTP POST tests
    #

    def test_post_with_screenshot_comment(self):
        """Testing the POST
        review-requests/<id>/reviews/<id>/replies/<id>/screenshot-comments/ API
        """
        comment_text = "My Comment Text"
        x, y, w, h = 10, 10, 20, 20

        review_request = self.create_review_request(publish=True)
        screenshot = self.create_screenshot(review_request)
        review = self.create_review(review_request, user=self.user,
                                    publish=True)
        comment = self.create_screenshot_comment(review, screenshot)
        reply = self.create_reply(review, user=self.user)

        rsp = self.apiPost(
            get_review_reply_screenshot_comment_list_url(reply),
            {
                'reply_to_id': comment.id,
                'text': comment_text,
            },
            expected_mimetype=review_reply_screenshot_comment_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')

        reply_comment = ScreenshotComment.objects.get(
            pk=rsp['screenshot_comment']['id'])
        self.assertEqual(reply_comment.text, comment_text)
        self.assertEqual(reply_comment.reply_to, comment)

    @add_fixtures(['test_site'])
    def test_post_with_screenshot_comment_and_local_site(self):
        """Testing the POST
        review-requests/<id>/reviews/<id>/replies/<id>/screenshot-comments/ API
        with a local site
        """
        comment_text = "My Comment Text"
        x, y, w, h = 10, 10, 20, 20

        user = self._login_user(local_site=True)

        review_request = self.create_review_request(with_local_site=True,
                                                    publish=True)
        screenshot = self.create_screenshot(review_request)
        review = self.create_review(review_request, user=user, publish=True)
        comment = self.create_screenshot_comment(review, screenshot)
        reply = self.create_reply(review, user=user)

        rsp = self.apiPost(
            get_review_reply_screenshot_comment_list_url(
                reply, self.local_site_name),
            {
                'reply_to_id': comment.id,
                'text': comment_text,
            },
            expected_mimetype=review_reply_screenshot_comment_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')

        reply_comment = ScreenshotComment.objects.get(
            pk=rsp['screenshot_comment']['id'])
        self.assertEqual(reply_comment.text, comment_text)
        self.assertEqual(reply_comment.reply_to, comment)

    def test_post_with_screenshot_comment_http_303(self):
        """Testing the POST
        review-requests/<id>/reviews/<id>/replies/<id>/screenshot-comments/ API
        """
        comment_text = "My Comment Text"

        review_request = self.create_review_request(publish=True)
        screenshot = self.create_screenshot(review_request)
        review = self.create_review(review_request, user=self.user,
                                    publish=True)
        comment = self.create_screenshot_comment(review, screenshot)
        reply = self.create_reply(review, user=self.user)
        reply_comment = self.create_screenshot_comment(reply, screenshot,
                                                       reply_to=comment)

        # Now post another reply to the same comment in the same review.
        rsp = self.apiPost(
            get_review_reply_screenshot_comment_list_url(reply),
            {
                'reply_to_id': comment.pk,
                'text': comment_text
            },
            expected_status=303,
            expected_mimetype=review_reply_screenshot_comment_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')

        reply_comment = ScreenshotComment.objects.get(
            pk=rsp['screenshot_comment']['id'])
        self.assertEqual(reply_comment.text, comment_text)


class ResourceItemTests(BaseWebAPITestCase):
    """Testing the ReviewReplyScreenshotCommentResource item APIs."""
    fixtures = ['test_users']

    #
    # HTTP DELETE tests
    #

    def test_delete(self):
        """Testing the DELETE
        review-requests/<id>/reviews/<id>/replies/<id>/screenshot-comments/<id>/
        API
        """
        review_request = self.create_review_request(publish=True)
        screenshot = self.create_screenshot(review_request)
        review = self.create_review(review_request, user=self.user,
                                    publish=True)
        comment = self.create_screenshot_comment(review, screenshot)
        reply = self.create_reply(review, user=self.user)
        reply_comment = self.create_screenshot_comment(reply, screenshot,
                                                       reply_to=comment)

        self.apiDelete(get_review_reply_screenshot_comment_item_url(
            reply, reply_comment.pk))

        replies = ScreenshotComment.objects.filter(review=reply,
                                                   reply_to=comment)
        self.assertEqual(replies.count(), 0)

    @add_fixtures(['test_site'])
    def test_delete_with_local_site(self):
        """Testing the DELETE
        review-requests/<id>/reviews/<id>/replies/<id>/screenshot-comments/<id>/
        API with a local site
        """
        user = self._login_user(local_site=True)
        review_request = self.create_review_request(submitter=user,
                                                    with_local_site=True,
                                                    publish=True)
        screenshot = self.create_screenshot(review_request)
        review = self.create_review(review_request, publish=True)
        comment = self.create_screenshot_comment(review, screenshot)
        reply = self.create_reply(review, user=user)
        reply_comment = self.create_screenshot_comment(reply, screenshot,
                                                       reply_to=comment)

        self.apiDelete(get_review_reply_screenshot_comment_item_url(
            reply, reply_comment.pk, self.local_site_name))

        replies = ScreenshotComment.objects.filter(review=reply,
                                                   reply_to=comment)
        self.assertEqual(replies.count(), 0)

    def test_delete_no_access(self):
        """Testing the DELETE
        review-requests/<id>/reviews/<id>/replies/<id>/screenshot-comments/<id>/
        API and Permission Denied
        """
        review_request = self.create_review_request(publish=True)
        screenshot = self.create_screenshot(review_request)
        review = self.create_review(review_request, user=self.user,
                                    publish=True)
        comment = self.create_screenshot_comment(review, screenshot)
        reply = self.create_reply(review, user=self.user)
        reply_comment = self.create_screenshot_comment(reply, screenshot,
                                                       reply_to=comment)

        self.client.login(username="doc", password="doc")

        self.apiDelete(
            get_review_reply_screenshot_comment_item_url(
                reply, reply_comment.pk),
            expected_status=403)

    @add_fixtures(['test_site'])
    def test_delete_with_local_site_no_access(self):
        """Testing the DELETE
        review-requests/<id>/reviews/<id>/replies/<id>/screenshot-comments/<id>/
        API with a local site and Permission Denied
        """
        review_request = self.create_review_request(with_local_site=True,
                                                    publish=True)
        screenshot = self.create_screenshot(review_request)
        review = self.create_review(review_request, user=self.user,
                                    publish=True)
        comment = self.create_screenshot_comment(review, screenshot)
        reply = self.create_reply(review, user=self.user)
        reply_comment = self.create_screenshot_comment(reply, screenshot,
                                                       reply_to=comment)

        self._login_user(local_site=True)

        self.apiDelete(
            get_review_reply_screenshot_comment_item_url(
                reply, reply_comment.pk, self.local_site_name),
            expected_status=403)
