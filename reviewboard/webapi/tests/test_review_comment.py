from django.contrib.auth.models import User
from djblets.testing.decorators import add_fixtures
from djblets.webapi.errors import PERMISSION_DENIED

from reviewboard.diffviewer.models import DiffSet
from reviewboard.reviews.models import Comment, Review, ReviewRequest
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import (
    review_item_mimetype,
    review_diff_comment_item_mimetype,
    review_diff_comment_list_mimetype)
from reviewboard.webapi.tests.urls import (
    get_review_list_url,
    get_review_diff_comment_item_url,
    get_review_diff_comment_list_url)


class ReviewCommentResourceTests(BaseWebAPITestCase):
    """Testing the ReviewCommentResource APIs."""
    fixtures = ['test_users', 'test_scmtools']

    @add_fixtures(['test_reviewrequests'])
    def test_get_diff_comments(self):
        """Testing the GET review-requests/<id>/reviews/<id>/diff-comments/ API"""
        review = Review.objects.filter(comments__pk__gt=0)[0]

        rsp = self.apiGet(get_review_diff_comment_list_url(review),
                          expected_mimetype=review_diff_comment_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['diff_comments']), review.comments.count())

    @add_fixtures(['test_reviewrequests'])
    def test_get_diff_comments_with_counts_only(self):
        """Testing the GET review-requests/<id>/reviews/<id>/diff-comments/?counts-only=1 API"""
        review = Review.objects.filter(comments__pk__gt=0)[0]

        rsp = self.apiGet(get_review_diff_comment_list_url(review), {
            'counts-only': 1,
        }, expected_mimetype=review_diff_comment_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['count'], review.comments.count())

    @add_fixtures(['test_reviewrequests', 'test_site'])
    def test_get_diff_comments_with_site(self):
        """Testing the GET review-requests/<id>/reviews/<id>/diff-comments/ API with a local site"""
        review_id = self.test_post_diff_comments_with_site()
        review = Review.objects.get(pk=review_id)

        rsp = self.apiGet(
            get_review_diff_comment_list_url(review, self.local_site_name),
            expected_mimetype=review_diff_comment_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['diff_comments']), review.comments.count())

    @add_fixtures(['test_reviewrequests', 'test_site'])
    def test_get_diff_comments_with_site_no_access(self):
        """Testing the GET review-requests/<id>/reviews/<id>/diff-comments/ API with a local site and Permission Denied error"""
        review_id = self.test_post_diff_comments_with_site()
        review = Review.objects.get(pk=review_id)

        self._login_user()

        rsp = self.apiGet(
            get_review_diff_comment_list_url(review, self.local_site_name),
            expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    @add_fixtures(['test_reviewrequests'])
    def test_get_diff_comment_not_modified(self):
        """Testing the GET review-requests/<id>/reviews/<id>/diff-comments/<id>/ API with Not Modified response"""
        comment = Comment.objects.all()[0]
        self._testHttpCaching(
            get_review_diff_comment_item_url(comment.review.get(), comment.id),
            check_last_modified=True)

    def test_post_diff_comments(self):
        """Testing the POST review-requests/<id>/reviews/<id>/diff-comments/ API"""
        diff_comment_text = "Test diff comment"

        # Post the review request
        rsp = self._postNewReviewRequest()
        review_request = ReviewRequest.objects.get(
            pk=rsp['review_request']['id'])

        # Post the diff.
        rsp = self._postNewDiff(review_request)
        DiffSet.objects.get(pk=rsp['diff']['id'])

        # Make these public.
        review_request.publish(self.user)

        rsp = self.apiPost(get_review_list_url(review_request),
                           expected_mimetype=review_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('review' in rsp)
        review_id = rsp['review']['id']

        self._postNewDiffComment(review_request, review_id, diff_comment_text)
        review = Review.objects.get(pk=review_id)

        rsp = self.apiGet(get_review_diff_comment_list_url(review),
                          expected_mimetype=review_diff_comment_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('diff_comments' in rsp)
        self.assertEqual(len(rsp['diff_comments']), 1)
        self.assertEqual(rsp['diff_comments'][0]['text'], diff_comment_text)

    @add_fixtures(['test_reviewrequests', 'test_site'])
    def test_post_diff_comments_with_site(self):
        """Testing the POST review-requests/<id>/reviews/<id>/diff-comments/ API with a local site"""
        diff_comment_text = "Test diff comment"
        review_request = ReviewRequest.objects.filter(
            local_site__name=self.local_site_name)[0]

        self._login_user(local_site=True)

        rsp = self.apiPost(
            get_review_list_url(review_request,
                                             self.local_site_name),
            expected_mimetype=review_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('review' in rsp)
        review_id = rsp['review']['id']

        self._postNewDiffComment(review_request, review_id, diff_comment_text)
        review = Review.objects.get(pk=review_id)

        rsp = self.apiGet(
            get_review_diff_comment_list_url(review, self.local_site_name),
            expected_mimetype=review_diff_comment_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('diff_comments' in rsp)
        self.assertEqual(len(rsp['diff_comments']), 1)
        self.assertEqual(rsp['diff_comments'][0]['text'], diff_comment_text)

        return review_id

    @add_fixtures(['test_reviewrequests', 'test_site'])
    def test_post_diff_comments_with_site_no_access(self):
        """Testing the POST review-requests/<id>/reviews/<id>/diff-comments/ API with a local site and Permission Denied error"""
        review_request = ReviewRequest.objects.filter(
            local_site__name=self.local_site_name)[0]

        review = Review()
        review.review_request = review_request
        review.user = User.objects.get(username='doc')
        review.save()

        rsp = self.apiPost(
            get_review_diff_comment_list_url(review, self.local_site_name),
            {},
            expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')

    def test_post_diff_comments_with_interdiff(self):
        """Testing the POST review-requests/<id>/reviews/<id>/diff-comments/ API with interdiff"""
        comment_text = "Test diff comment"

        rsp, review_request_id, review_id, interdiff_revision = \
            self._common_post_interdiff_comments(comment_text)

        review = Review.objects.get(pk=review_id)

        rsp = self.apiGet(get_review_diff_comment_list_url(review),
                          expected_mimetype=review_diff_comment_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('diff_comments' in rsp)
        self.assertEqual(len(rsp['diff_comments']), 1)
        self.assertEqual(rsp['diff_comments'][0]['text'], comment_text)

    def test_get_diff_comments_with_interdiff(self):
        """Testing the GET review-requests/<id>/reviews/<id>/diff-comments/ API with interdiff"""
        comment_text = "Test diff comment"

        rsp, review_request_id, review_id, interdiff_revision = \
            self._common_post_interdiff_comments(comment_text)

        review = Review.objects.get(pk=review_id)

        rsp = self.apiGet(get_review_diff_comment_list_url(review), {
            'interdiff-revision': interdiff_revision,
        }, expected_mimetype=review_diff_comment_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('diff_comments' in rsp)
        self.assertEqual(len(rsp['diff_comments']), 1)
        self.assertEqual(rsp['diff_comments'][0]['text'], comment_text)

    def test_delete_diff_comment_with_interdiff(self):
        """Testing the DELETE review-requests/<id>/reviews/<id>/diff-comments/<id>/ API"""
        comment_text = "This is a test comment."

        rsp, review_request_id, review_id, interdiff_revision = \
            self._common_post_interdiff_comments(comment_text)

        rsp = self.apiDelete(rsp['diff_comment']['links']['self']['href'])

        review = Review.objects.get(pk=review_id)

        rsp = self.apiGet(get_review_diff_comment_list_url(review),
                          expected_mimetype=review_diff_comment_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('diff_comments' in rsp)
        self.assertEqual(len(rsp['diff_comments']), 0)

    @add_fixtures(['test_reviewrequests', 'test_site'])
    def test_delete_diff_comment_with_site(self):
        """Testing the DELETE review-requests/<id>/reviews/<id>/diff-comments/<id>/ API with a local site"""
        review_id = self.test_post_diff_comments_with_site()
        review = Review.objects.get(pk=review_id)
        comment = review.comments.all()[0]
        comment_count = review.comments.count()

        self.apiDelete(get_review_diff_comment_item_url(review, comment.id,
                                                        self.local_site_name))

        self.assertEqual(review.comments.count(), comment_count - 1)

    @add_fixtures(['test_reviewrequests', 'test_site'])
    def test_delete_diff_comment_with_site_no_access(self):
        """Testing the DELETE review-requests/<id>/reviews/<id>/diff-comments/<id>/ API with a local site and Permission Denied error"""
        review_id = self.test_post_diff_comments_with_site()
        review = Review.objects.get(pk=review_id)
        comment = review.comments.all()[0]

        self._login_user()

        rsp = self.apiDelete(
            get_review_diff_comment_item_url(review, comment.id,
                                             self.local_site_name),
            expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    def test_post_diff_comments_with_issue(self):
        """Testing the POST review-requests/<id>/reviews/<id>/diff-comments/ API with an issue"""
        diff_comment_text = 'Test diff comment with an opened issue'
        rsp, review, review_request = self._create_diff_review_with_issue(
            publish=False, comment_text=diff_comment_text)

        rsp = self.apiGet(get_review_diff_comment_list_url(review),
                          expected_mimetype=review_diff_comment_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('diff_comments' in rsp)
        self.assertEqual(len(rsp['diff_comments']), 1)
        self.assertEqual(rsp['diff_comments'][0]['text'], diff_comment_text)
        self.assertTrue(rsp['diff_comments'][0]['issue_opened'])

    def test_update_diff_comment_with_issue(self):
        """Testing the PUT review-requests/<id>/reviews/<id>/diff-comments/<id>/ API, removing issue_opened"""
        rsp, review, review_request = self._create_diff_review_with_issue()

        rsp = self.apiPut(
            rsp['diff_comment']['links']['self']['href'],
            {'issue_opened': False},
            expected_mimetype=review_diff_comment_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertFalse(rsp['diff_comment']['issue_opened'])

    def test_update_diff_comment_issue_status_before_publish(self):
        """Testing the PUT review-requests/<id>/reviews/<id>/diff-comments/<id>/ API with an issue, before review is published"""
        rsp, review, review_request = self._create_diff_review_with_issue()

        # The issue_status should not be able to be changed while the review is
        # unpublished.
        rsp = self.apiPut(
            rsp['diff_comment']['links']['self']['href'],
            {'issue_status': 'resolved'},
            expected_mimetype=review_diff_comment_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')

        # The issue_status should still be "open"
        self.assertEqual(rsp['diff_comment']['issue_status'], 'open')

    def test_update_diff_comment_issue_status_after_publish(self):
        """Testing the PUT review-requests/<id>/reviews/<id>/diff-comments/<id>/ API with an issue, after review is published"""
        rsp, review, review_request = self._create_diff_review_with_issue(
            publish=True)

        rsp = self.apiPut(
            rsp['diff_comment']['links']['self']['href'],
            {'issue_status': 'resolved'},
            expected_mimetype=review_diff_comment_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['diff_comment']['issue_status'], 'resolved')

    def test_update_diff_comment_issue_status_by_issue_creator(self):
        """Testing the PUT review-requests/<id>/reviews/<id>/diff-comments/<id>/ API permissions for issue creator"""
        rsp, review, review_request = self._create_diff_review_with_issue(
            publish=True)

        # Change the owner of the review request so that it's not owned by
        # self.user.
        review_request.submitter = User.objects.get(username='doc')
        review_request.save()

        # The review/comment (and therefore issue) is still owned by self.user,
        # so we should be able to change the issue status.
        rsp = self.apiPut(
            rsp['diff_comment']['links']['self']['href'],
            {'issue_status': 'dropped'},
            expected_mimetype=review_diff_comment_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['diff_comment']['issue_status'], 'dropped')

    def test_update_diff_comment_issue_status_by_uninvolved_user(self):
        """Testing the PUT review-requests/<id>/reviews/<id>/diff-comments/<id>/ API permissions for an uninvolved user"""
        rsp, review, review_request = self._create_diff_review_with_issue(
            publish=True)

        # Change the owner of the review request and review so that they're
        # not owned by self.user.
        new_owner = User.objects.get(username='doc')
        review_request.submitter = new_owner
        review_request.save()
        review.user = new_owner
        review.save()

        rsp = self.apiPut(
            rsp['diff_comment']['links']['self']['href'],
            {'issue_status': 'dropped'},
            expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    def test_remove_issue_opened(self):
        """Testing the PUT review-requests/<id>/reviews/<id>/diff-comments/<id>/ API, removing the issue_opened state"""
        rsp, review, review_request = self._create_diff_review_with_issue()

        self.assertEqual(rsp['diff_comment']['issue_status'], 'open')

        rsp = self.apiPut(
            rsp['diff_comment']['links']['self']['href'],
            {'issue_opened': False},
            expected_mimetype=review_diff_comment_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['diff_comment']['issue_status'], '')

    def _common_post_interdiff_comments(self, comment_text):
        # Post the review request
        rsp = self._postNewReviewRequest()
        review_request = ReviewRequest.objects.get(
            pk=rsp['review_request']['id'])

        # Post the diff.
        rsp = self._postNewDiff(review_request)
        review_request.publish(self.user)
        diffset = DiffSet.objects.get(pk=rsp['diff']['id'])
        filediff = diffset.files.all()[0]

        # Post the second diff.
        rsp = self._postNewDiff(review_request)
        review_request.publish(self.user)
        interdiffset = DiffSet.objects.get(pk=rsp['diff']['id'])
        interfilediff = interdiffset.files.all()[0]

        rsp = self.apiPost(get_review_list_url(review_request),
                           expected_mimetype=review_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('review' in rsp)
        review_id = rsp['review']['id']

        rsp = self._postNewDiffComment(review_request, review_id,
                                       comment_text,
                                       filediff_id=filediff.id,
                                       interfilediff_id=interfilediff.id)

        return rsp, review_request.id, review_id, interdiffset.revision

    def _create_diff_review_with_issue(self, publish=False, comment_text=None):
        """Sets up a review for a diff that includes a comment with an issue.

        If `publish` is True, the review is published. The review request is
        always published.

        Returns the response from posting the comment, the review object, and the
        review request object.
        """
        if not comment_text:
            comment_text = 'Test diff comment with an opened issue'

        # Post the review request
        rsp = self._postNewReviewRequest()
        review_request = ReviewRequest.objects.get(
            pk=rsp['review_request']['id'])

        # Post the diff
        rsp = self._postNewDiff(review_request)
        DiffSet.objects.get(pk=rsp['diff']['id'])

        # Make these public
        review_request.publish(self.user)

        # Create a review
        rsp = self.apiPost(get_review_list_url(review_request),
                           expected_mimetype=review_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('review' in rsp)
        review_id = rsp['review']['id']
        review = Review.objects.get(pk=review_id)

        # Create a diff comment
        rsp = self._postNewDiffComment(review_request, review_id,
                                       comment_text, issue_opened=True)

        if publish:
            review.public = True
            review.save()

        return rsp, review, review_request
