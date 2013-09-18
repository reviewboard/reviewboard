from django.contrib.auth.models import User
from djblets.testing.decorators import add_fixtures
from djblets.webapi.errors import PERMISSION_DENIED

from reviewboard.reviews.models import Comment
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import (
    review_diff_comment_item_mimetype,
    review_diff_comment_list_mimetype)
from reviewboard.webapi.tests.urls import (
    get_review_diff_comment_item_url,
    get_review_diff_comment_list_url)


class BaseResourceTestCase(BaseWebAPITestCase):
    def _common_post_interdiff_comments(self, comment_text):
        review_request, filediff = self._create_diff_review_request()
        diffset = filediff.diffset

        # Post the second diff.
        interdiffset = self.create_diffset(review_request)
        interfilediff = self.create_filediff(diffset)

        review = self.create_review(review_request, user=self.user)
        comment = self.create_diff_comment(review, filediff, interfilediff,
                                           text=comment_text)

        return comment, review_request, review, interdiffset.revision

    def _create_diff_review_with_issue(self, publish=False, comment_text=None):
        """Sets up a review for a diff that includes a comment with an issue.

        If `publish` is True, the review is published. The review request is
        always published.

        Returns the response from posting the comment, the review object, and
        the review request object.
        """
        if not comment_text:
            comment_text = 'Test diff comment with an opened issue'

        review_request, filediff = self._create_diff_review_request()
        review = self.create_review(review_request, user=self.user,
                                    publish=publish)
        comment = self.create_diff_comment(review, filediff, text=comment_text,
                                           issue_opened=True)

        return comment, review, review_request

    def _create_diff_review_request(self, with_local_site=False):
        review_request = self.create_review_request(
            create_repository=True,
            submitter=self.user,
            with_local_site=with_local_site,
            publish=True)
        diffset = self.create_diffset(review_request)
        filediff = self.create_filediff(diffset)

        return review_request, filediff

    def _create_diff_review(self):
        review_request, filediff = self._create_diff_review_request()

        review = self.create_review(review_request, publish=True)
        self.create_diff_comment(review, filediff)

        return review


class ResourceListTests(BaseResourceTestCase):
    """Testing the ReviewCommentResource list APIs."""
    fixtures = ['test_users', 'test_scmtools']

    #
    # HTTP GET tests
    #

    def test_get_diff_comments(self):
        """Testing the
        GET review-requests/<id>/reviews/<id>/diff-comments/ API
        """
        review = self._create_diff_review()

        rsp = self.apiGet(get_review_diff_comment_list_url(review),
                          expected_mimetype=review_diff_comment_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['diff_comments']), review.comments.count())

    def test_get_diff_comments_with_counts_only(self):
        """Testing the
        GET review-requests/<id>/reviews/<id>/diff-comments/?counts-only=1 API
        """
        review = self._create_diff_review()

        rsp = self.apiGet(get_review_diff_comment_list_url(review), {
            'counts-only': 1,
        }, expected_mimetype=review_diff_comment_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['count'], review.comments.count())

    def test_get_diff_comments_with_interdiff(self):
        """Testing the GET review-requests/<id>/reviews/<id>/diff-comments/ API
        with interdiff
        """
        comment_text = "Test diff comment"

        comment, review_request, review, interdiff_revision = \
            self._common_post_interdiff_comments(comment_text)

        rsp = self.apiGet(get_review_diff_comment_list_url(review), {
            'interdiff-revision': interdiff_revision,
        }, expected_mimetype=review_diff_comment_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('diff_comments' in rsp)
        self.assertEqual(len(rsp['diff_comments']), 1)
        self.assertEqual(rsp['diff_comments'][0]['text'], comment_text)

    @add_fixtures(['test_site'])
    def test_get_diff_comments_with_site(self):
        """Testing the GET review-requests/<id>/reviews/<id>/diff-comments/ API
        with a local site
        """
        review = self.test_post_diff_comments_with_site()

        rsp = self.apiGet(
            get_review_diff_comment_list_url(review, self.local_site_name),
            expected_mimetype=review_diff_comment_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['diff_comments']), review.comments.count())

    @add_fixtures(['test_site'])
    def test_get_diff_comments_with_site_no_access(self):
        """Testing the GET review-requests/<id>/reviews/<id>/diff-comments/ API
        with a local site and Permission Denied error
        """
        review = self.test_post_diff_comments_with_site()

        self._login_user()

        rsp = self.apiGet(
            get_review_diff_comment_list_url(review, self.local_site_name),
            expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    #
    # HTTP POST tests
    #

    def test_post_diff_comments(self):
        """Testing the
        POST review-requests/<id>/reviews/<id>/diff-comments/ API
        """
        review_request = self.create_review_request(create_repository=True,
                                                    publish=True)
        diffset = self.create_diffset(review_request)
        filediff = self.create_filediff(diffset)
        review = self.create_review(review_request, user=self.user)
        comment = self.create_diff_comment(review, filediff)

        rsp = self.apiGet(get_review_diff_comment_list_url(review),
                          expected_mimetype=review_diff_comment_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('diff_comments' in rsp)
        self.assertEqual(len(rsp['diff_comments']), 1)
        self.assertEqual(rsp['diff_comments'][0]['text'], comment.text)

    def test_post_diff_comments_with_issue(self):
        """Testing the
        POST review-requests/<id>/reviews/<id>/diff-comments/ API
        with an issue
        """
        diff_comment_text = 'Test diff comment with an opened issue'
        comment, review, review_request = self._create_diff_review_with_issue(
            publish=False, comment_text=diff_comment_text)

        rsp = self.apiGet(get_review_diff_comment_list_url(review),
                          expected_mimetype=review_diff_comment_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('diff_comments' in rsp)
        self.assertEqual(len(rsp['diff_comments']), 1)
        self.assertEqual(rsp['diff_comments'][0]['text'], diff_comment_text)
        self.assertTrue(rsp['diff_comments'][0]['issue_opened'])

    @add_fixtures(['test_site'])
    def test_post_diff_comments_with_site(self):
        """Testing the
        POST review-requests/<id>/reviews/<id>/diff-comments/ API
        with a local site
        """
        review_request, filediff = \
            self._create_diff_review_request(with_local_site=True)
        user = self._login_user(local_site=True)
        review = self.create_review(review_request, user=user)
        comment = self.create_diff_comment(review, filediff)

        rsp = self.apiGet(
            get_review_diff_comment_list_url(review, self.local_site_name),
            expected_mimetype=review_diff_comment_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('diff_comments' in rsp)
        self.assertEqual(len(rsp['diff_comments']), 1)
        self.assertEqual(rsp['diff_comments'][0]['text'], comment.text)

        return review

    @add_fixtures(['test_site'])
    def test_post_diff_comments_with_site_no_access(self):
        """Testing the
        POST review-requests/<id>/reviews/<id>/diff-comments/ API
        with a local site and Permission Denied error
        """
        review_request = self.create_review_request(with_local_site=True,
                                                    publish=True)
        review = self.create_review(review_request, user='doc', publish=True)

        rsp = self.apiPost(
            get_review_diff_comment_list_url(review, self.local_site_name),
            {},
            expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')

    def test_post_diff_comments_with_interdiff(self):
        """Testing the
        POST review-requests/<id>/reviews/<id>/diff-comments/ API
        with interdiff
        """
        comment_text = "Test diff comment"

        comment, review_request, review, interdiff_revision = \
            self._common_post_interdiff_comments(comment_text)

        rsp = self.apiGet(get_review_diff_comment_list_url(review),
                          expected_mimetype=review_diff_comment_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('diff_comments' in rsp)
        self.assertEqual(len(rsp['diff_comments']), 1)
        self.assertEqual(rsp['diff_comments'][0]['text'], comment_text)


class ResourceItemTests(BaseResourceTestCase):
    """Testing the ReviewCommentResource item APIs."""
    fixtures = ['test_users', 'test_scmtools']

    #
    # HTTP DELETE tests
    #

    def test_delete_diff_comment_with_interdiff(self):
        """Testing the
        DELETE review-requests/<id>/reviews/<id>/diff-comments/<id>/ API
        """
        comment_text = "This is a test comment."

        comment, review_request, review, interdiff_revision = \
            self._common_post_interdiff_comments(comment_text)

        self.apiDelete(get_review_diff_comment_item_url(review, comment.pk))

        rsp = self.apiGet(get_review_diff_comment_list_url(review),
                          expected_mimetype=review_diff_comment_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('diff_comments' in rsp)
        self.assertEqual(len(rsp['diff_comments']), 0)

    @add_fixtures(['test_site'])
    def test_delete_diff_comment_with_site(self):
        """Testing the
        DELETE review-requests/<id>/reviews/<id>/diff-comments/<id>/ API
        with a local site
        """
        review_request, filediff = \
            self._create_diff_review_request(with_local_site=True)
        user = self._login_user(local_site=True)
        review = self.create_review(review_request, user=user)
        comment = self.create_diff_comment(review, filediff)

        self.assertEqual(review.comments.count(), 1)

        self.apiDelete(get_review_diff_comment_item_url(review, comment.pk,
                                                        self.local_site_name))

        self.assertEqual(review.comments.count(), 0)

    @add_fixtures(['test_site'])
    def test_delete_diff_comment_with_site_no_access(self):
        """Testing the
        DELETE review-requests/<id>/reviews/<id>/diff-comments/<id>/ API
        with a local site and Permission Denied error
        """
        review_request, filediff = \
            self._create_diff_review_request(with_local_site=True)
        user = self._login_user(local_site=True)
        review = self.create_review(review_request, user=user)
        comment = self.create_diff_comment(review, filediff)

        self._login_user()

        rsp = self.apiDelete(
            get_review_diff_comment_item_url(review, comment.id,
                                             self.local_site_name),
            expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    #
    # HTTP GET tests
    #

    def test_get_diff_comment_not_modified(self):
        """Testing the
        GET review-requests/<id>/reviews/<id>/diff-comments/<id>/ API
        with Not Modified response
        """
        review = self._create_diff_review()
        comment = Comment.objects.all()[0]

        self._testHttpCaching(
            get_review_diff_comment_item_url(review, comment.id),
            check_last_modified=True)

    #
    # HTTP PUT tests
    #

    def test_put_diff_comment_with_issue(self):
        """Testing the
        PUT review-requests/<id>/reviews/<id>/diff-comments/<id>/ API,
        removing issue_opened
        """
        comment, review, review_request = self._create_diff_review_with_issue()

        rsp = self.apiPut(
            get_review_diff_comment_item_url(review, comment.id),
            {'issue_opened': False},
            expected_mimetype=review_diff_comment_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertFalse(rsp['diff_comment']['issue_opened'])

    def test_put_diff_comment_issue_status_before_publish(self):
        """Testing the
        PUT review-requests/<id>/reviews/<id>/diff-comments/<id>/ API
        with an issue, before review is published
        """
        comment, review, review_request = self._create_diff_review_with_issue()

        # The issue_status should not be able to be changed while the review is
        # unpublished.
        rsp = self.apiPut(
            get_review_diff_comment_item_url(review, comment.id),
            {'issue_status': 'resolved'},
            expected_mimetype=review_diff_comment_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')

        # The issue_status should still be "open"
        self.assertEqual(rsp['diff_comment']['issue_status'], 'open')

    def test_put_diff_comment_issue_status_after_publish(self):
        """Testing the
        PUT review-requests/<id>/reviews/<id>/diff-comments/<id>/ API
        with an issue, after review is published
        """
        comment, review, review_request = self._create_diff_review_with_issue(
            publish=True)

        rsp = self.apiPut(
            get_review_diff_comment_item_url(review, comment.id),
            {'issue_status': 'resolved'},
            expected_mimetype=review_diff_comment_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['diff_comment']['issue_status'], 'resolved')

    def test_put_diff_comment_issue_status_by_issue_creator(self):
        """Testing the
        PUT review-requests/<id>/reviews/<id>/diff-comments/<id>/ API
        permissions for issue creator
        """
        comment, review, review_request = self._create_diff_review_with_issue(
            publish=True)

        # Change the owner of the review request so that it's not owned by
        # self.user.
        review_request.submitter = User.objects.get(username='doc')
        review_request.save()

        # The review/comment (and therefore issue) is still owned by self.user,
        # so we should be able to change the issue status.
        rsp = self.apiPut(
            get_review_diff_comment_item_url(review, comment.id),
            {'issue_status': 'dropped'},
            expected_mimetype=review_diff_comment_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['diff_comment']['issue_status'], 'dropped')

    def test_put_diff_comment_issue_status_by_uninvolved_user(self):
        """Testing the
        PUT review-requests/<id>/reviews/<id>/diff-comments/<id>/ API
        permissions for an uninvolved user
        """
        comment, review, review_request = self._create_diff_review_with_issue(
            publish=True)

        # Change the owner of the review request and review so that they're
        # not owned by self.user.
        new_owner = User.objects.get(username='doc')
        review_request.submitter = new_owner
        review_request.save()
        review.user = new_owner
        review.save()

        rsp = self.apiPut(
            get_review_diff_comment_item_url(review, comment.id),
            {'issue_status': 'dropped'},
            expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    def test_put_with_remove_issue_opened(self):
        """Testing the
        PUT review-requests/<id>/reviews/<id>/diff-comments/<id>/ API,
        removing the issue_opened state
        """
        comment, review, review_request = self._create_diff_review_with_issue()

        rsp = self.apiPut(
            get_review_diff_comment_item_url(review, comment.id),
            {'issue_opened': False},
            expected_mimetype=review_diff_comment_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['diff_comment']['issue_status'], '')
