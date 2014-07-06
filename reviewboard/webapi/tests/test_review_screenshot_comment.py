from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.utils import six
from djblets.webapi.errors import PERMISSION_DENIED

from reviewboard.reviews.models import ScreenshotComment
from reviewboard.webapi.resources import resources
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import (
    screenshot_comment_item_mimetype,
    screenshot_comment_list_mimetype)
from reviewboard.webapi.tests.mixins import (
    BasicTestsMetaclass,
    ReviewRequestChildItemMixin,
    ReviewRequestChildListMixin)
from reviewboard.webapi.tests.mixins_comment import (
    CommentItemMixin,
    CommentListMixin)
from reviewboard.webapi.tests.urls import (
    get_review_screenshot_comment_item_url,
    get_review_screenshot_comment_list_url)


class BaseTestCase(BaseWebAPITestCase):
    fixtures = ['test_users']

    def _create_screenshot_review_with_issue(self, publish=False,
                                             comment_text=None):
        """Sets up a review for a screenshot that includes an open issue.

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
        review = self.create_review(review_request, user=self.user,
                                    publish=publish)
        comment = self.create_screenshot_comment(review, screenshot,
                                                 comment_text,
                                                 issue_opened=True)

        return comment, review, review_request


@six.add_metaclass(BasicTestsMetaclass)
class ResourceListTests(CommentListMixin, ReviewRequestChildListMixin,
                        BaseTestCase):
    """Testing the ReviewScreenshotCommentResource list APIs."""
    sample_api_url = 'review-requests/<id>/reviews/<id>/screenshot-comments/'
    resource = resources.review_screenshot_comment

    def setup_review_request_child_test(self, review_request):
        self.create_screenshot(review_request)
        review = self.create_review(review_request, user=self.user)

        return (get_review_screenshot_comment_list_url(review),
                screenshot_comment_list_mimetype)

    def compare_item(self, item_rsp, comment):
        self.assertEqual(item_rsp['id'], comment.pk)
        self.assertEqual(item_rsp['text'], comment.text)
        self.assertEqual(item_rsp['x'], comment.x)
        self.assertEqual(item_rsp['y'], comment.y)
        self.assertEqual(item_rsp['w'], comment.w)
        self.assertEqual(item_rsp['h'], comment.h)
        self.assertEqual(item_rsp['extra_data'], comment.extra_data)

        if comment.rich_text:
            self.assertEqual(item_rsp['text_type'], 'markdown')
        else:
            self.assertEqual(item_rsp['text_type'], 'plain')

    #
    # HTTP GET tests
    #

    def setup_basic_get_test(self, user, with_local_site, local_site_name,
                             populate_items):
        review_request = self.create_review_request(
            with_local_site=with_local_site,
            submitter=user,
            publish=True)
        screenshot = self.create_screenshot(review_request)
        review = self.create_review(review_request, user=user)

        if populate_items:
            items = [self.create_screenshot_comment(review, screenshot)]
        else:
            items = []

        return (get_review_screenshot_comment_list_url(review,
                                                       local_site_name),
                screenshot_comment_list_mimetype,
                items)

    #
    # HTTP POST tests
    #

    def setup_basic_post_test(self, user, with_local_site, local_site_name,
                              post_valid_data):
        review_request = self.create_review_request(
            with_local_site=with_local_site,
            submitter=user,
            publish=True)
        screenshot = self.create_screenshot(review_request)
        review = self.create_review(review_request, user=user)

        return (get_review_screenshot_comment_list_url(review,
                                                       local_site_name),
                screenshot_comment_item_mimetype,
                {
                    'screenshot_id': screenshot.pk,
                    'text': 'Test comment',
                    'x': 2,
                    'y': 2,
                    'w': 10,
                    'h': 10,
                },
                [review, screenshot])

    def check_post_result(self, user, rsp, review, screenshot):
        comment = \
            ScreenshotComment.objects.get(pk=rsp['screenshot_comment']['id'])
        self.compare_item(rsp['screenshot_comment'], comment)

    def test_post_with_issue(self):
        """Testing the
        POST review-requests/<id>/reviews/<id>/screenshot-comments/ API
        with an issue
        """
        comment_text = "Test screenshot comment with an opened issue"
        comment, review, review_request = \
            self._create_screenshot_review_with_issue(
                publish=False, comment_text=comment_text)

        rsp = self.api_get(
            get_review_screenshot_comment_list_url(review),
            expected_mimetype=screenshot_comment_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertIn('screenshot_comments', rsp)
        self.assertEqual(len(rsp['screenshot_comments']), 1)
        self.assertEqual(rsp['screenshot_comments'][0]['text'], comment_text)
        self.assertTrue(rsp['screenshot_comments'][0]['issue_opened'])


@six.add_metaclass(BasicTestsMetaclass)
class ResourceItemTests(CommentItemMixin, ReviewRequestChildItemMixin,
                        BaseTestCase):
    """Testing the ReviewScreenshotCommentResource item APIs."""
    fixtures = ['test_users']
    sample_api_url = \
        'review-requests/<id>/reviews/<id>/screenshot-comments/<id>/'
    resource = resources.review_screenshot_comment

    def compare_item(self, item_rsp, comment):
        self.assertEqual(item_rsp['id'], comment.pk)
        self.assertEqual(item_rsp['text'], comment.text)
        self.assertEqual(item_rsp['x'], comment.x)
        self.assertEqual(item_rsp['y'], comment.y)
        self.assertEqual(item_rsp['w'], comment.w)
        self.assertEqual(item_rsp['h'], comment.h)
        self.assertEqual(item_rsp['extra_data'], comment.extra_data)

        if comment.rich_text:
            self.assertEqual(item_rsp['text_type'], 'markdown')
        else:
            self.assertEqual(item_rsp['text_type'], 'plain')

    def setup_review_request_child_test(self, review_request):
        screenshot = self.create_screenshot(review_request)
        review = self.create_review(review_request, user=self.user)
        comment = self.create_screenshot_comment(review, screenshot)

        return (get_review_screenshot_comment_item_url(review, comment.pk),
                screenshot_comment_item_mimetype)

    #
    # HTTP DELETE tests
    #

    def setup_basic_delete_test(self, user, with_local_site, local_site_name):
        review_request = self.create_review_request(
            with_local_site=with_local_site,
            submitter=user,
            publish=True)
        screenshot = self.create_screenshot(review_request)
        review = self.create_review(review_request, user=user)
        comment = self.create_screenshot_comment(review, screenshot)

        return (get_review_screenshot_comment_item_url(review, comment.pk,
                                                       local_site_name),
                [comment, review])

    def check_delete_result(self, user, comment, review):
        self.assertNotIn(comment, review.screenshot_comments.all())

    def test_delete_with_does_not_exist_error(self):
        """Testing the
        DELETE review-requests/<id>/reviews/<id>/screenshot-comments/<id>/ API
        with Does Not Exist error
        """
        review_request = self.create_review_request(publish=True)
        self.create_screenshot(review_request)
        review = self.create_review(review_request, user=self.user)

        self.api_delete(get_review_screenshot_comment_item_url(review, 123),
                        expected_status=404)

    #
    # HTTP GET tests
    #

    def setup_basic_get_test(self, user, with_local_site, local_site_name):
        review_request = self.create_review_request(
            with_local_site=with_local_site,
            submitter=user,
            publish=True)
        screenshot = self.create_screenshot(review_request)
        review = self.create_review(review_request, user=user)
        comment = self.create_screenshot_comment(review, screenshot)

        return (get_review_screenshot_comment_item_url(review, comment.pk,
                                                       local_site_name),
                screenshot_comment_item_mimetype,
                comment)

    #
    # HTTP PUT tests
    #

    def setup_basic_put_test(self, user, with_local_site, local_site_name,
                             put_valid_data):
        review_request = self.create_review_request(
            with_local_site=with_local_site,
            submitter=user,
            publish=True)
        screenshot = self.create_screenshot(review_request)
        review = self.create_review(review_request, user=user)
        comment = self.create_screenshot_comment(review, screenshot)

        return (get_review_screenshot_comment_item_url(review, comment.pk,
                                                       local_site_name),
                screenshot_comment_item_mimetype,
                {
                    'text': 'Test comment',
                },
                comment,
                [])

    def check_put_result(self, user, item_rsp, comment, *args):
        comment = ScreenshotComment.objects.get(pk=comment.pk)
        self.assertEqual(item_rsp['text_type'], 'plain')
        self.assertEqual(item_rsp['text'], 'Test comment')
        self.compare_item(item_rsp, comment)

    def test_put_with_issue(self):
        """Testing the
        PUT review-requests/<id>/reviews/<id>/screenshot-comments/<id>/ API
        with an issue, removing issue_opened
        """
        comment, review, review_request = \
            self._create_screenshot_review_with_issue()

        rsp = self.api_put(
            get_review_screenshot_comment_item_url(review, comment.pk),
            {'issue_opened': False},
            expected_mimetype=screenshot_comment_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertFalse(rsp['screenshot_comment']['issue_opened'])

    def test_put_issue_status_before_publish(self):
        """Testing the
        PUT review-requests/<id>/reviews/<id>/screenshot-comments/<id> API
        with an issue, before review is published
        """
        comment, review, review_request = \
            self._create_screenshot_review_with_issue()

        # The issue_status should not be able to be changed while the review is
        # unpublished.
        rsp = self.api_put(
            get_review_screenshot_comment_item_url(review, comment.pk),
            {'issue_status': 'resolved'},
            expected_mimetype=screenshot_comment_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')

        # The issue_status should still be "open"
        self.assertEqual(rsp['screenshot_comment']['issue_status'], 'open')

    def test_put_issue_status_after_publish(self):
        """Testing the
        PUT review-requests/<id>/reviews/<id>/screenshot-comments/<id>/ API
        with an issue, after review is published
        """
        comment, review, review_request = \
            self._create_screenshot_review_with_issue(publish=True)

        rsp = self.api_put(
            get_review_screenshot_comment_item_url(review, comment.pk),
            {'issue_status': 'resolved'},
            expected_mimetype=screenshot_comment_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['screenshot_comment']['issue_status'], 'resolved')

    def test_put_issue_status_by_issue_creator(self):
        """Testing the
        PUT review-requests/<id>/reviews/<id>/screenshot-comments/<id>/ API
        permissions for issue creator
        """
        comment, review, review_request = \
            self._create_screenshot_review_with_issue(publish=True)

        # Change the owner of the review request so that it's not owned by
        # self.user
        review_request.submitter = User.objects.get(username='doc')
        review_request.save()

        # The review/comment (and therefore issue) is still owned by self.user,
        # so we should be able to change the issue status.
        rsp = self.api_put(
            get_review_screenshot_comment_item_url(review, comment.pk),
            {'issue_status': 'dropped'},
            expected_mimetype=screenshot_comment_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['screenshot_comment']['issue_status'], 'dropped')

    def test_put_issue_status_by_uninvolved_user(self):
        """Testing the
        PUT review-requests/<id>/reviews/<id>/screenshot-comments/<id>/ API
        permissions for an uninvolved user
        """
        comment, review, review_request = \
            self._create_screenshot_review_with_issue(publish=True)

        # Change the owner of the review request and review so that they're not
        # owned by self.user.
        new_owner = User.objects.get(username='doc')
        review_request.submitter = new_owner
        review_request.save()
        review.user = new_owner
        review.save()

        rsp = self.api_put(
            get_review_screenshot_comment_item_url(review, comment.pk),
            {'issue_status': 'dropped'},
            expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    def test_put_deleted_screenshot_comment_issue_status(self):
        """Testing the
        PUT review-requests/<id>/reviews/<id>/screenshot-comments/<id>
        API with an issue and a deleted screenshot
        """
        comment_text = "Test screenshot comment with an opened issue"
        x, y, w, h = (2, 2, 10, 10)

        review_request = self.create_review_request(publish=True,
                                                    submitter=self.user)
        screenshot = self.create_screenshot(review_request)
        review = self.create_review(review_request, user=self.user)
        comment = self.create_screenshot_comment(review, screenshot,
                                                 comment_text, x, y, w, h,
                                                 issue_opened=True)

        # First, let's ensure that the user that has created the comment
        # cannot alter the issue_status while the review is unpublished.
        rsp = self.api_put(
            get_review_screenshot_comment_item_url(review, comment.pk),
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

        rsp = self.api_put(
            rsp['screenshot_comment']['links']['self']['href'],
            {'issue_status': 'resolved'},
            expected_mimetype=screenshot_comment_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['screenshot_comment']['issue_status'], 'resolved')

        # Delete the screenshot.
        self._delete_screenshot(review_request, screenshot)
        review_request.publish(review_request.submitter)

        # Try altering the issue_status. This should be allowed.
        rsp = self.api_put(
            rsp['screenshot_comment']['links']['self']['href'],
            {'issue_status': 'open'},
            expected_mimetype=screenshot_comment_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['screenshot_comment']['issue_status'], 'open')
