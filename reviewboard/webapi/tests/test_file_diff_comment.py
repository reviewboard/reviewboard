from djblets.testing.decorators import add_fixtures
from djblets.webapi.errors import PERMISSION_DENIED

from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import filediff_comment_list_mimetype
from reviewboard.webapi.tests.urls import get_filediff_comment_list_url


class ResourceListTests(BaseWebAPITestCase):
    """Testing the FileDiffCommentResource list APIs."""
    fixtures = ['test_users', 'test_scmtools']

    #
    # HTTP GET tests
    #

    def test_get(self):
        """Testing the
        GET review-requests/<id>/diffs/<revision>/files/<id>/diff-comments/ API
        """
        diff_comment_text = 'Sample comment.'

        review_request = self.create_review_request(create_repository=True,
                                                    publish=True)
        diffset = self.create_diffset(review_request)
        filediff = self.create_filediff(diffset)

        review = self.create_review(review_request, publish=True)
        comment = self.create_diff_comment(review, filediff,
                                           text=diff_comment_text)

        rsp = self.apiGet(get_filediff_comment_list_url(filediff),
                          expected_mimetype=filediff_comment_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['diff_comments']), 1)
        self.assertEqual(rsp['diff_comments'][0]['text'], comment.text)

    def test_get_as_anonymous(self):
        """Testing the
        GET review-requests/<id>/diffs/<revision>/files/<id>/diff-comments/ API
        as an anonymous user
        """
        diff_comment_text = 'Sample comment.'

        review_request = self.create_review_request(create_repository=True,
                                                    publish=True)
        diffset = self.create_diffset(review_request)
        filediff = self.create_filediff(diffset)

        review = self.create_review(review_request, publish=True)
        comment = self.create_diff_comment(review, filediff,
                                           text=diff_comment_text)

        self.client.logout()

        rsp = self.apiGet(get_filediff_comment_list_url(filediff),
                          expected_mimetype=filediff_comment_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['diff_comments']), 1)
        self.assertEqual(rsp['diff_comments'][0]['text'], comment.text)

    @add_fixtures(['test_site'])
    def test_get_with_site(self):
        """Testing the
        GET review-requests/<id>/diffs/<revision>/files/<id>/diff-comments/ API
        with a local site
        """
        diff_comment_text = 'Sample comment.'

        self._login_user(local_site=True)

        review_request = self.create_review_request(with_local_site=True,
                                                    create_repository=True,
                                                    publish=True)
        diffset = self.create_diffset(review_request)
        filediff = self.create_filediff(diffset)

        review = self.create_review(review_request, publish=True)
        comment = self.create_diff_comment(review, filediff,
                                           text=diff_comment_text)

        rsp = self.apiGet(
            get_filediff_comment_list_url(filediff, self.local_site_name),
            expected_mimetype=filediff_comment_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['diff_comments']), 1)
        self.assertEqual(rsp['diff_comments'][0]['text'], comment.text)

    @add_fixtures(['test_site'])
    def test_get_with_site_no_access(self):
        """Testing the
        GET review-requests/<id>/diffs/<revision>/files/<id>/diff-comments/ API
        with a local site and Permission Denied error
        """
        diff_comment_text = 'Sample comment.'

        self._login_user(local_site=True)

        review_request = self.create_review_request(with_local_site=True,
                                                    create_repository=True,
                                                    publish=True)
        diffset = self.create_diffset(review_request)
        filediff = self.create_filediff(diffset)

        review = self.create_review(review_request, publish=True)
        self.create_diff_comment(review, filediff, text=diff_comment_text)

        self._login_user()

        rsp = self.apiGet(
            get_filediff_comment_list_url(filediff, self.local_site_name),
            expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    def test_get_with_line(self):
        """Testing the
        GET review-requests/<id>/diffs/<revision>/files/<id>/diff-comments/ API
        with ?line=
        """
        diff_comment_text = 'Sample comment.'
        diff_comment_line = 10

        review_request = self.create_review_request(create_repository=True,
                                                    publish=True)
        diffset = self.create_diffset(review_request)
        filediff = self.create_filediff(diffset)

        review = self.create_review(review_request, publish=True)
        self.create_diff_comment(review, filediff,
                                 text=diff_comment_text,
                                 first_line=diff_comment_line)
        self.create_diff_comment(review, filediff,
                                 first_line=diff_comment_line + 1)

        rsp = self.apiGet(get_filediff_comment_list_url(filediff), {
            'line': diff_comment_line,
        }, expected_mimetype=filediff_comment_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')

        self.assertEqual(len(rsp['diff_comments']), 1)
        self.assertEqual(rsp['diff_comments'][0]['text'], diff_comment_text)
        self.assertEqual(rsp['diff_comments'][0]['first_line'],
                         diff_comment_line)
