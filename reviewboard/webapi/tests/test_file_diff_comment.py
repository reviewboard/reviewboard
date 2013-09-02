from djblets.webapi.errors import PERMISSION_DENIED

from reviewboard.reviews.models import Comment, Review, ReviewRequest
from reviewboard.site.urlresolvers import local_site_reverse
from reviewboard.webapi.tests.base import BaseWebAPITestCase, _build_mimetype
from reviewboard.webapi.tests.test_review import ReviewResourceTests


class FileDiffCommentResourceTests(BaseWebAPITestCase):
    """Testing the FileDiffCommentResource APIs."""
    fixtures = ['test_users', 'test_scmtools', 'test_reviewrequests',
                'test_site']

    list_mimetype = _build_mimetype('file-diff-comments')
    item_mimetype = _build_mimetype('file-diff-comment')

    def test_get_comments(self):
        """Testing the GET review-requests/<id>/diffs/<revision>/files/<id>/diff-comments/ API"""
        diff_comment_text = 'Sample comment.'

        review_request = ReviewRequest.objects.public()[0]
        diffset = review_request.diffset_history.diffsets.latest()
        filediff = diffset.files.all()[0]

        rsp = self.apiPost(ReviewResourceTests.get_list_url(review_request),
                           expected_mimetype=ReviewResourceTests.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('review' in rsp)
        review_id = rsp['review']['id']

        self._postNewDiffComment(review_request, review_id, diff_comment_text)

        rsp = self.apiGet(self.get_list_url(filediff),
                          expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')

        comments = Comment.objects.filter(filediff=filediff)
        self.assertEqual(len(rsp['diff_comments']), comments.count())

        for i in range(0, len(rsp['diff_comments'])):
            self.assertEqual(rsp['diff_comments'][i]['text'], comments[i].text)

    def test_get_comments_as_anonymous(self):
        """Testing the GET review-requests/<id>/diffs/<revision>/files/<id>/diff-comments/ API as an anonymous user"""
        diff_comment_text = 'Sample comment.'

        review_request = ReviewRequest.objects.public()[0]
        diffset = review_request.diffset_history.diffsets.latest()
        filediff = diffset.files.all()[0]

        rsp = self.apiPost(ReviewResourceTests.get_list_url(review_request),
                           expected_mimetype=ReviewResourceTests.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('review' in rsp)
        review_id = rsp['review']['id']

        self._postNewDiffComment(review_request, review_id, diff_comment_text)
        review = Review.objects.get(pk=review_id)
        review.publish()

        self.client.logout()

        rsp = self.apiGet(self.get_list_url(filediff),
                          expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')

        comments = Comment.objects.filter(filediff=filediff)
        self.assertEqual(len(rsp['diff_comments']), comments.count())

        for i in range(0, len(rsp['diff_comments'])):
            self.assertEqual(rsp['diff_comments'][i]['text'], comments[i].text)

    def test_get_comments_with_site(self):
        """Testing the GET review-requests/<id>/diffs/<revision>/files/<id>/diff-comments/ API with a local site"""
        diff_comment_text = 'Sample comment.'

        self._login_user(local_site=True)

        review_request = ReviewRequest.objects.filter(
            local_site__name=self.local_site_name)[0]
        diffset = review_request.diffset_history.diffsets.latest()
        filediff = diffset.files.all()[0]

        rsp = self.apiPost(
            ReviewResourceTests.get_list_url(review_request,
                                             self.local_site_name),
            expected_mimetype=ReviewResourceTests.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('review' in rsp)
        review_id = rsp['review']['id']

        self._postNewDiffComment(review_request, review_id, diff_comment_text)

        rsp = self.apiGet(self.get_list_url(filediff, self.local_site_name),
                          expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')

        comments = Comment.objects.filter(filediff=filediff)
        self.assertEqual(len(rsp['diff_comments']), comments.count())

        for i in range(0, len(rsp['diff_comments'])):
            self.assertEqual(rsp['diff_comments'][i]['text'], comments[i].text)

    def test_get_comments_with_site_no_access(self):
        """Testing the GET review-requests/<id>/diffs/<revision>/files/<id>/diff-comments/ API with a local site and Permission Denied error"""
        diff_comment_text = 'Sample comment.'

        self._login_user(local_site=True)

        review_request = ReviewRequest.objects.filter(
            local_site__name=self.local_site_name)[0]
        diffset = review_request.diffset_history.diffsets.latest()
        filediff = diffset.files.all()[0]

        rsp = self.apiPost(
            ReviewResourceTests.get_list_url(review_request,
                                             self.local_site_name),
            expected_mimetype=ReviewResourceTests.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('review' in rsp)
        review_id = rsp['review']['id']

        self._postNewDiffComment(review_request, review_id, diff_comment_text)

        self._login_user()

        rsp = self.apiGet(self.get_list_url(filediff, self.local_site_name),
                          expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    def test_get_comments_with_line(self):
        """Testing the GET review-requests/<id>/diffs/<revision>/files/<id>/diff-comments/?line= API"""
        diff_comment_text = 'Sample comment.'
        diff_comment_line = 10

        review_request = ReviewRequest.objects.public()[0]
        diffset = review_request.diffset_history.diffsets.latest()
        filediff = diffset.files.all()[0]

        rsp = self.apiPost(ReviewResourceTests.get_list_url(review_request),
                           expected_mimetype=ReviewResourceTests.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('review' in rsp)
        review_id = rsp['review']['id']

        self._postNewDiffComment(review_request, review_id, diff_comment_text,
                                 first_line=diff_comment_line)

        self._postNewDiffComment(review_request, review_id, diff_comment_text,
                                 first_line=diff_comment_line + 1)

        rsp = self.apiGet(self.get_list_url(filediff), {
            'line': diff_comment_line,
        }, expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')

        comments = Comment.objects.filter(filediff=filediff,
                                          first_line=diff_comment_line)
        self.assertEqual(len(rsp['diff_comments']), comments.count())

        for i in range(0, len(rsp['diff_comments'])):
            self.assertEqual(rsp['diff_comments'][i]['text'], comments[i].text)
            self.assertEqual(rsp['diff_comments'][i]['first_line'],
                             comments[i].first_line)

    def get_list_url(self, filediff, local_site_name=None):
        diffset = filediff.diffset
        review_request = diffset.history.review_request.get()

        return local_site_reverse(
            'diff-comments-resource',
            local_site_name=local_site_name,
            kwargs={
                'review_request_id': review_request.display_id,
                'diff_revision': filediff.diffset.revision,
                'filediff_id': filediff.pk,
            })
