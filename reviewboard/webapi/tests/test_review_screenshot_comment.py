from django.contrib.auth.models import User
from djblets.testing.decorators import add_fixtures
from djblets.webapi.errors import PERMISSION_DENIED

from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import (
    screenshot_comment_item_mimetype,
    screenshot_comment_list_mimetype)
from reviewboard.webapi.tests.urls import (
    get_review_screenshot_comment_item_url,
    get_review_screenshot_comment_list_url)


class ReviewScreenshotCommentResourceTests(BaseWebAPITestCase):
    """Testing the ReviewScreenshotCommentResource APIs."""
    fixtures = ['test_users', 'test_scmtools']

    #
    # List tests
    #

    def test_post_screenshot_comments(self):
        """Testing the
        POST review-requests/<id>/reviews/<id>/screenshot-comments/ API
        """
        comment_text = "This is a test comment."
        x, y, w, h = (2, 2, 10, 10)

        review_request = self.create_review_request(publish=True)
        screenshot = self.create_screenshot(review_request)
        review = self.create_review(review_request, user=self.user)

        rsp = self._postNewScreenshotComment(review_request, review.id,
                                             screenshot, comment_text,
                                             x, y, w, h)

        self.assertEqual(rsp['screenshot_comment']['text'], comment_text)
        self.assertEqual(rsp['screenshot_comment']['x'], x)
        self.assertEqual(rsp['screenshot_comment']['y'], y)
        self.assertEqual(rsp['screenshot_comment']['w'], w)
        self.assertEqual(rsp['screenshot_comment']['h'], h)

    @add_fixtures(['test_site'])
    def test_post_screenshot_comments_with_site(self):
        """Testing the
        POST review-requests/<id>/reviews/<id>/screenshot-comments/ API
        with a local site
        """
        comment_text = 'This is a test comment.'
        x, y, w, h = (2, 2, 10, 10)

        user = self._login_user(local_site=True)

        review_request = self.create_review_request(with_local_site=True,
                                                    publish=True)
        screenshot = self.create_screenshot(review_request)
        review = self.create_review(review_request, user=user)

        rsp = self._postNewScreenshotComment(review_request, review.id,
                                             screenshot, comment_text,
                                             x, y, w, h)

        self.assertEqual(rsp['screenshot_comment']['text'], comment_text)
        self.assertEqual(rsp['screenshot_comment']['x'], x)
        self.assertEqual(rsp['screenshot_comment']['y'], y)
        self.assertEqual(rsp['screenshot_comment']['w'], w)
        self.assertEqual(rsp['screenshot_comment']['h'], h)

    def test_post_screenshot_comment_with_issue(self):
        """Testing the
        POST review-requests/<id>/reviews/<id>/screenshot-comments/ API
        with an issue
        """
        comment_text = "Test screenshot comment with an opened issue"
        rsp, review, review_request = \
            self._create_screenshot_review_with_issue(
                publish=False, comment_text=comment_text)

        rsp = self.apiGet(
            get_review_screenshot_comment_list_url(review),
            expected_mimetype=screenshot_comment_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('screenshot_comments' in rsp)
        self.assertEqual(len(rsp['screenshot_comments']), 1)
        self.assertEqual(rsp['screenshot_comments'][0]['text'], comment_text)
        self.assertTrue(rsp['screenshot_comments'][0]['issue_opened'])

    @add_fixtures(['test_site'])
    def test_post_screenshot_comments_with_site_no_access(self):
        """Testing the
        POST review-requests/<id>/reviews/<id>/screenshot-comments/ API
        with a local site and Permission Denied error
        """
        x, y, w, h = (2, 2, 10, 10)

        user = self._login_user(local_site=True)

        review_request = self.create_review_request(with_local_site=True,
                                                    create_repository=True,
                                                    publish=True)
        screenshot = self.create_screenshot(review_request)
        review = self.create_review(review_request, user=user)

        self._login_user()

        rsp = self.apiPost(
            get_review_screenshot_comment_list_url(review,
                                                   self.local_site_name),
            {'screenshot_id': screenshot.id},
            expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    #
    # Item tests
    #

    def test_delete_screenshot_comment(self):
        """Testing the
        DELETE review-requests/<id>/reviews/<id>/screenshot-comments/<id>/ API
        """
        comment_text = "This is a test comment."
        x, y, w, h = (2, 2, 10, 10)

        review_request = self.create_review_request(publish=True)
        screenshot = self.create_screenshot(review_request)
        review = self.create_review(review_request, user=self.user)

        rsp = self._postNewScreenshotComment(review_request, review.id,
                                             screenshot, comment_text,
                                             x, y, w, h)

        self.apiDelete(rsp['screenshot_comment']['links']['self']['href'])

        rsp = self.apiGet(
            get_review_screenshot_comment_list_url(review),
            expected_mimetype=screenshot_comment_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('screenshot_comments' in rsp)
        self.assertEqual(len(rsp['screenshot_comments']), 0)

    @add_fixtures(['test_site'])
    def test_delete_screenshot_comment_with_local_site(self):
        """Testing the
        DELETE review-requests/<id>/reviews/<id>/screenshot-comments/<id> API
        with a local site
        """
        comment_text = 'This is a test comment.'
        x, y, w, h = (2, 2, 10, 10)

        user = self._login_user(local_site=True)

        review_request = self.create_review_request(with_local_site=True,
                                                    publish=True)
        screenshot = self.create_screenshot(review_request)
        review = self.create_review(review_request, user=user)

        rsp = self._postNewScreenshotComment(review_request, review.id,
                                             screenshot, comment_text,
                                             x, y, w, h)

        self.apiDelete(rsp['screenshot_comment']['links']['self']['href'])

        rsp = self.apiGet(
            get_review_screenshot_comment_list_url(review,
                                                   self.local_site_name),
            expected_mimetype=screenshot_comment_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('screenshot_comments' in rsp)
        self.assertEqual(len(rsp['screenshot_comments']), 0)

    @add_fixtures(['test_site'])
    def test_delete_screenshot_comment_with_local_site_no_access(self):
        """Testing the
        DELETE review-requests/<id>/reviews/<id>/screenshot-comments/<id> API
        with a local site and Permission Denied error
        """
        comment_text = 'This is a test comment.'
        x, y, w, h = (2, 2, 10, 10)

        user = self._login_user(local_site=True)

        review_request = self.create_review_request(with_local_site=True,
                                                    publish=True)
        screenshot = self.create_screenshot(review_request)
        review = self.create_review(review_request, user=user)

        rsp = self._postNewScreenshotComment(review_request, review.id,
                                             screenshot, comment_text,
                                             x, y, w, h)

        self._login_user()

        rsp = self.apiDelete(rsp['screenshot_comment']['links']['self']['href'],
                             expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    def test_delete_screenshot_comment_with_does_not_exist_error(self):
        """Testing the
        DELETE review-requests/<id>/reviews/<id>/screenshot-comments/<id>/ API
        with Does Not Exist error
        """
        x, y, w, h = (2, 2, 10, 10)

        review_request = self.create_review_request(publish=True)
        self.create_screenshot(review_request)
        review = self.create_review(review_request, user=self.user)

        self.apiDelete(get_review_screenshot_comment_item_url(review, 123),
                       expected_status=404)

    def test_put_screenshot_comment_with_issue(self):
        """Testing the
        PUT review-requests/<id>/reviews/<id>/screenshot-comments/<id>/ API
        with an issue, removing issue_opened
        """
        rsp, review, review_request = \
            self._create_screenshot_review_with_issue()

        rsp = self.apiPut(
            rsp['screenshot_comment']['links']['self']['href'],
            {'issue_opened': False},
            expected_mimetype=screenshot_comment_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertFalse(rsp['screenshot_comment']['issue_opened'])

    def test_put_screenshot_comment_issue_status_before_publish(self):
        """Testing the
        PUT review-requests/<id>/reviews/<id>/screenshot-comments/<id> API
        with an issue, before review is published
        """
        rsp, review, review_request = \
            self._create_screenshot_review_with_issue()

        # The issue_status should not be able to be changed while the review is
        # unpublished.
        rsp = self.apiPut(
            rsp['screenshot_comment']['links']['self']['href'],
            {'issue_status': 'resolved'},
            expected_mimetype=screenshot_comment_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')

        # The issue_status should still be "open"
        self.assertEqual(rsp['screenshot_comment']['issue_status'], 'open')

    def test_put_screenshot_comment_issue_status_after_publish(self):
        """Testing the
        PUT review-requests/<id>/reviews/<id>/screenshot-comments/<id>/ API
        with an issue, after review is published
        """
        rsp, review, review_request = \
            self._create_screenshot_review_with_issue(publish=True)

        rsp = self.apiPut(
            rsp['screenshot_comment']['links']['self']['href'],
            {'issue_status': 'resolved'},
            expected_mimetype=screenshot_comment_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['screenshot_comment']['issue_status'], 'resolved')

    def test_put_screenshot_comment_issue_status_by_issue_creator(self):
        """Testing the
        PUT review-requests/<id>/reviews/<id>/screenshot-comments/<id>/ API
        permissions for issue creator
        """
        rsp, review, review_request = \
            self._create_screenshot_review_with_issue(publish=True)

        # Change the owner of the review request so that it's not owned by
        # self.user
        review_request.submitter = User.objects.get(username='doc')
        review_request.save()

        # The review/comment (and therefore issue) is still owned by self.user,
        # so we should be able to change the issue status.
        rsp = self.apiPut(
            rsp['screenshot_comment']['links']['self']['href'],
            {'issue_status': 'dropped'},
            expected_mimetype=screenshot_comment_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['screenshot_comment']['issue_status'], 'dropped')

    def test_put_screenshot_comment_issue_status_by_uninvolved_user(self):
        """Testing the
        PUT review-requests/<id>/reviews/<id>/screenshot-comments/<id>/ API
        permissions for an uninvolved user
        """
        rsp, review, review_request = \
            self._create_screenshot_review_with_issue(publish=True)

        # Change the owner of the review request and review so that they're not
        # owned by self.user.
        new_owner = User.objects.get(username='doc')
        review_request.submitter = new_owner
        review_request.save()
        review.user = new_owner
        review.save()

        rsp = self.apiPut(
            rsp['screenshot_comment']['links']['self']['href'],
            {'issue_status': 'dropped'},
            expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    def test_put_deleted_screenshot_comment_issue_status(self):
        """Testing the PUT review-requests/<id>/reviews/<id>/screenshot-comments/<id>
        API with an issue and a deleted screenshot
        """
        comment_text = "Test screenshot comment with an opened issue"
        x, y, w, h = (2, 2, 10, 10)

        review_request = self.create_review_request(publish=True,
                                                    submitter=self.user)
        screenshot = self.create_screenshot(review_request)
        review = self.create_review(review_request, user=self.user)

        rsp = self._postNewScreenshotComment(review_request, review.pk,
                                             screenshot, comment_text,
                                             x, y, w, h, issue_opened=True)

        # First, let's ensure that the user that has created the comment
        # cannot alter the issue_status while the review is unpublished.
        rsp = self.apiPut(
            rsp['screenshot_comment']['links']['self']['href'],
            {'issue_status': 'resolved'},
            expected_mimetype=screenshot_comment_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')

        # The issue_status should still be "open"
        self.assertEqual(rsp['screenshot_comment']['issue_status'], 'open')

        # Next, let's publish the review, and try altering the issue_status.
        # This should be allowed, since the review request was made by the
        # current user.
        review.public = True
        review.save()

        rsp = self.apiPut(
            rsp['screenshot_comment']['links']['self']['href'],
            {'issue_status': 'resolved'},
            expected_mimetype=screenshot_comment_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['screenshot_comment']['issue_status'], 'resolved')

        # Delete the screenshot.
        self._delete_screenshot(review_request, screenshot)
        review_request.publish(review_request.submitter)

        # Try altering the issue_status. This should be allowed.
        rsp = self.apiPut(
            rsp['screenshot_comment']['links']['self']['href'],
            {'issue_status': 'open'},
            expected_mimetype=screenshot_comment_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['screenshot_comment']['issue_status'], 'open')

    def _create_screenshot_review_with_issue(self, publish=False,
                                             comment_text=None):
        """Sets up a review for a screenshot that includes a comment with an issue.

        If `publish` is True, the review is published. The review request is
        always published.

        Returns the response from posting the comment, the review object, and
        the review request object.
        """
        if not comment_text:
            comment_text = 'Test screenshot comment with an opened issue'

        review_request = self.create_review_request(publish=True,
                                                    submitter=self.user)
        screenshot = self.create_screenshot(review_request)
        review = self.create_review(review_request, user=self.user)

        # Create the comment
        x, y, w, h = (2, 2, 10, 10)
        rsp = self._postNewScreenshotComment(review_request, review.pk,
                                             screenshot, comment_text,
                                             x, y, w, h, issue_opened=True)
        self.assertEqual(rsp['stat'], 'ok')

        if publish:
            review.public = True
            review.save()

        return rsp, review, review_request
