from django.contrib.auth.models import User
from djblets.testing.decorators import add_fixtures

from reviewboard.reviews.models import ScreenshotComment
from reviewboard.site.models import LocalSite
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import (
    review_reply_screenshot_comment_item_mimetype,
    review_reply_screenshot_comment_list_mimetype)
from reviewboard.webapi.tests.urls import (
    get_review_reply_screenshot_comment_list_url)


class ReviewReplyScreenshotCommentResourceTests(BaseWebAPITestCase):
    """Testing the ReviewReplyScreenshotCommentResource APIs."""
    fixtures = ['test_users']

    @add_fixtures(['test_scmtools'])
    def test_post_reply_with_screenshot_comment(self):
        """Testing the POST review-requests/<id>/reviews/<id>/replies/<id>/screenshot-comments/ API"""
        comment_text = "My Comment Text"
        x, y, w, h = 10, 10, 20, 20

        review_request = self.create_review_request(publish=True)
        screenshot = self.create_screenshot(review_request)
        review = self.create_review(review_request, user=self.user,
                                    publish=True)
        comment = self.create_screenshot_comment(review, screenshot)
        reply = self.create_reply(review, user=self.user)

        comments_url = get_review_reply_screenshot_comment_list_url(reply)

        rsp = self.apiPost(
            comments_url,
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

        return rsp, comment, comments_url

    @add_fixtures(['test_site'])
    def test_post_reply_with_screenshot_comment_and_local_site(self):
        """Testing the POST review-requests/<id>/reviews/<id>/replies/<id>/screenshot-comments/ API with a local site"""
        comment_text = "My Comment Text"
        x, y, w, h = 10, 10, 20, 20

        user = self._login_user(local_site=True)

        review_request = self.create_review_request(with_local_site=True,
                                                    publish=True)
        screenshot = self.create_screenshot(review_request)
        review = self.create_review(review_request, user=user, publish=True)
        comment = self.create_screenshot_comment(review, screenshot)
        reply = self.create_reply(review, user=user)

        screenshot_comments_url = \
            get_review_reply_screenshot_comment_list_url(reply,
                                                         self.local_site_name)

        post_data = {
            'reply_to_id': comment.id,
            'text': comment_text,
        }

        rsp = self.apiPost(
            screenshot_comments_url, post_data,
            expected_mimetype=review_reply_screenshot_comment_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')

        reply_comment = ScreenshotComment.objects.get(
            pk=rsp['screenshot_comment']['id'])
        self.assertEqual(reply_comment.text, comment_text)

        return rsp, comment, screenshot_comments_url

    @add_fixtures(['test_scmtools'])
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
            expected_mimetype=review_reply_screenshot_comment_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')

        reply_comment = ScreenshotComment.objects.get(
            pk=rsp['screenshot_comment']['id'])
        self.assertEqual(reply_comment.text, comment_text)

    @add_fixtures(['test_scmtools'])
    def test_delete_screenshot_comment(self):
        """Testing the DELETE review-requests/<id>/reviews/<id>/replies/<id>/screenshot-comments/<id>/ API"""
        rsp, comment, screenshot_comments_url = \
            self.test_post_reply_with_screenshot_comment()

        self.apiDelete(rsp['screenshot_comment']['links']['self']['href'])

        rsp = self.apiGet(
            screenshot_comments_url,
            expected_mimetype=review_reply_screenshot_comment_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('screenshot_comments' in rsp)
        self.assertEqual(len(rsp['screenshot_comments']), 0)

    @add_fixtures(['test_site'])
    def test_delete_screenshot_comment_with_local_site(self):
        """Testing the DELETE review-requests/<id>/reviews/<id>/replies/<id>/screenshot-comments/<id>/ API with a local site"""
        rsp, comment, screenshot_comments_url = \
            self.test_post_reply_with_screenshot_comment_and_local_site()

        self.apiDelete(rsp['screenshot_comment']['links']['self']['href'])

        rsp = self.apiGet(
            screenshot_comments_url,
            expected_mimetype=review_reply_screenshot_comment_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('screenshot_comments' in rsp)
        self.assertEqual(len(rsp['screenshot_comments']), 0)

    @add_fixtures(['test_scmtools'])
    def test_delete_screenshot_comment_no_access(self):
        """Testing the DELETE review-requests/<id>/reviews/<id>/replies/<id>/screenshot-comments/<id>/ API and Permission Denied"""
        rsp, comment, screenshot_comments_url = \
            self.test_post_reply_with_screenshot_comment()

        self.client.login(username="doc", password="doc")

        self.apiDelete(rsp['screenshot_comment']['links']['self']['href'],
                       expected_status=403)

    @add_fixtures(['test_site'])
    def test_delete_screenshot_comment_with_local_site_no_access(self):
        """Testing the DELETE review-requests/<id>/reviews/<id>/replies/<id>/screenshot-comments/<id>/ API with a local site and Permission Denied"""
        rsp, comment, screenshot_comments_url = \
            self.test_post_reply_with_screenshot_comment_and_local_site()

        local_site = LocalSite.objects.get(name=self.local_site_name)
        local_site.users.add(User.objects.get(username='grumpy'))

        self.client.login(username="grumpy", password="grumpy")

        self.apiDelete(rsp['screenshot_comment']['links']['self']['href'],
                       expected_status=403)
