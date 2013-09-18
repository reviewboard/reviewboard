from djblets.testing.decorators import add_fixtures
from djblets.webapi.errors import PERMISSION_DENIED

from reviewboard.reviews.models import Comment
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import (
    review_reply_diff_comment_item_mimetype)
from reviewboard.webapi.tests.urls import (
    get_review_reply_diff_comment_item_url,
    get_review_reply_diff_comment_list_url)


class ReviewReplyDiffCommentResourceTests(BaseWebAPITestCase):
    """Testing the ReviewReplyDiffCommentResource APIs."""
    fixtures = ['test_users', 'test_scmtools']

    #
    # List tests
    #

    def test_post_reply_with_diff_comment(self):
        """Testing the
        POST review-requests/<id>/reviews/<id>/replies/<id>/diff-comments/ API
        """
        comment_text = "My Comment Text"

        review_request = self.create_review_request(create_repository=True,
                                                    submitter=self.user)
        diffset = self.create_diffset(review_request)
        filediff = self.create_filediff(diffset)
        review_request.publish(review_request.submitter)

        review = self.create_review(review_request, publish=True)
        comment = self.create_diff_comment(review, filediff)
        reply = self.create_reply(review, user=self.user)

        diff_comments_url = get_review_reply_diff_comment_list_url(reply)

        rsp = self.apiPost(
            diff_comments_url,
            {
                'reply_to_id': comment.id,
                'text': comment_text,
            },
            expected_mimetype=review_reply_diff_comment_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')

        reply_comment = Comment.objects.get(pk=rsp['diff_comment']['id'])
        self.assertEqual(reply_comment.text, comment_text)

        return rsp, comment, diff_comments_url

    @add_fixtures(['test_site'])
    def test_post_reply_with_diff_comment_and_local_site(self, badlogin=False):
        """Testing the
        POST review-requests/<id>/reviews/<id>/replies/<id>/diff-comments/ API
        with a local site
        """
        comment_text = 'My Comment Text'

        user = self._login_user(local_site=True)

        review_request = self.create_review_request(create_repository=True,
                                                    submitter=self.user,
                                                    with_local_site=True)
        diffset = self.create_diffset(review_request)
        filediff = self.create_filediff(diffset)
        review_request.publish(review_request.submitter)

        review = self.create_review(review_request, publish=True)
        comment = self.create_diff_comment(review, filediff)

        reply = self.create_reply(review, user=user)

        diff_comments_url = \
            get_review_reply_diff_comment_list_url(reply, self.local_site_name)

        post_data = {
            'reply_to_id': comment.pk,
            'text': comment_text,
        }

        if badlogin:
            self._login_user()
            rsp = self.apiPost(diff_comments_url,
                               post_data,
                               expected_status=403)
            self.assertEqual(rsp['stat'], 'fail')
            self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)
        else:
            rsp = self.apiPost(
                diff_comments_url,
                post_data,
                expected_mimetype=review_reply_diff_comment_item_mimetype)
            self.assertEqual(rsp['stat'], 'ok')

            reply_comment = Comment.objects.get(pk=rsp['diff_comment']['id'])
            self.assertEqual(reply_comment.text, comment_text)

        return rsp, comment, diff_comments_url

    @add_fixtures(['test_site'])
    def test_post_reply_with_diff_comment_and_local_site_no_access(self):
        """Testing the
        POST review-requests/<id>/reviews/<id>/replies/<id>/diff-comments/ API
        with a local site and Permission Denied error
        """
        self.test_post_reply_with_diff_comment_and_local_site(True)

    def test_post_reply_with_diff_comment_http_303(self):
        """Testing the
        POST review-requests/<id>/reviews/<id>/replies/<id>/diff-comments/ API
        and 303 See Other
        """
        comment_text = "My New Comment Text"

        rsp, comment, comments_url = self.test_post_reply_with_diff_comment()

        # Now do it again.
        rsp = self.apiPost(
            comments_url,
            {
                'reply_to_id': comment.pk,
                'text': comment_text
            },
            expected_status=303,
            expected_mimetype=review_reply_diff_comment_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')

        reply_comment = Comment.objects.get(pk=rsp['diff_comment']['id'])
        self.assertEqual(reply_comment.text, comment_text)

    #
    # Item tests
    #

    def test_delete_diff_comment(self):
        """Testing the DELETE
        review-requests/<id>/reviews/<id>/replies/<id>/diff-comments/<id>/ API
        """
        review_request = self.create_review_request(submitter=self.user,
                                                    create_repository=True,
                                                    publish=True)
        diffset = self.create_diffset(review_request)
        filediff = self.create_filediff(diffset)
        review = self.create_review(review_request)
        comment = self.create_diff_comment(review, filediff)
        reply = self.create_reply(review, user=self.user)
        reply_comment = self.create_diff_comment(
            reply, filediff, reply_to=comment)

        self.apiDelete(get_review_reply_diff_comment_item_url(
            reply, reply_comment.pk))

        comments = Comment.objects.filter(review=reply, reply_to=comment)
        self.assertEqual(comments.count(), 0)

    @add_fixtures(['test_site'])
    def test_delete_diff_comment_with_local_site(self):
        """Testing the DELETE
        review-requests/<id>/reviews/<id>/replies/<id>/diff-comments/<id>/ API
        with a local site
        """
        user = self._login_user(local_site=True)
        review_request = self.create_review_request(submitter=self.user,
                                                    create_repository=True,
                                                    with_local_site=True,
                                                    publish=True)
        diffset = self.create_diffset(review_request)
        filediff = self.create_filediff(diffset)
        review = self.create_review(review_request)
        comment = self.create_diff_comment(review, filediff)
        reply = self.create_reply(review, user=user)
        reply_comment = self.create_diff_comment(
            reply, filediff, reply_to=comment)

        self.apiDelete(get_review_reply_diff_comment_item_url(
            reply, reply_comment.pk, self.local_site_name))

        comments = Comment.objects.filter(review=reply, reply_to=comment)
        self.assertEqual(comments.count(), 0)

    def test_delete_diff_comment_no_access(self):
        """Testing the DELETE
        review-requests/<id>/reviews/<id>/replies/<id>/diff-comments/<id>/ API
        and Permission Denied
        """
        review_request = self.create_review_request(submitter=self.user,
                                                    create_repository=True,
                                                    publish=True)
        diffset = self.create_diffset(review_request)
        filediff = self.create_filediff(diffset)
        review = self.create_review(review_request)
        comment = self.create_diff_comment(review, filediff)
        reply = self.create_reply(review, user='doc')
        reply_comment = self.create_diff_comment(
            reply, filediff, reply_to=comment)

        self.apiDelete(
            get_review_reply_diff_comment_item_url(reply, reply_comment.pk),
            expected_status=403)

    @add_fixtures(['test_site'])
    def test_delete_diff_comment_with_local_site_no_access(self):
        """Testing the DELETE
        review-requests/<id>/reviews/<id>/replies/<id>/diff-comments/<id>/ API
        with a local site and Permission Denied
        """
        review_request = self.create_review_request(submitter=self.user,
                                                    create_repository=True,
                                                    with_local_site=True,
                                                    publish=True)
        diffset = self.create_diffset(review_request)
        filediff = self.create_filediff(diffset)
        review = self.create_review(review_request)
        comment = self.create_diff_comment(review, filediff)
        reply = self.create_reply(review, user=self.user)
        reply_comment = self.create_diff_comment(
            reply, filediff, reply_to=comment)

        self._login_user(local_site=True)

        self.apiDelete(
            get_review_reply_diff_comment_item_url(
                reply, reply_comment.pk, self.local_site_name),
            expected_status=403)

    def test_put_reply_with_diff_comment(self):
        """Testing the
        PUT review-requests/<id>/reviews/<id>/replies/<id>/diff-comments/ API
        """
        new_comment_text = 'My new comment text'

        # First, create a comment that we can update.
        review_request = self.create_review_request(submitter=self.user,
                                                    create_repository=True,
                                                    publish=True)
        diffset = self.create_diffset(review_request)
        filediff = self.create_filediff(diffset)
        review = self.create_review(review_request)
        comment = self.create_diff_comment(review, filediff)
        reply = self.create_reply(review, user=self.user)
        reply_comment = self.create_diff_comment(
            reply, filediff, reply_to=comment)

        rsp = self.apiPut(
            get_review_reply_diff_comment_item_url(reply, reply_comment.pk),
            {'text': new_comment_text},
            expected_mimetype=review_reply_diff_comment_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')

        reply_comment = Comment.objects.get(pk=rsp['diff_comment']['id'])
        self.assertEqual(reply_comment.text, new_comment_text)

    @add_fixtures(['test_site'])
    def test_put_reply_with_diff_comment_and_local_site(self):
        """Testing the
        PUT review-requests/<id>/reviews/<id>/replies/<id>/diff-comments/ API
        with a local site
        """
        new_comment_text = 'My new comment text'
        user = self._login_user(local_site=True)
        review_request = self.create_review_request(submitter=self.user,
                                                    create_repository=True,
                                                    with_local_site=True,
                                                    publish=True)
        diffset = self.create_diffset(review_request)
        filediff = self.create_filediff(diffset)
        review = self.create_review(review_request)
        comment = self.create_diff_comment(review, filediff)
        reply = self.create_reply(review, user=user)
        reply_comment = self.create_diff_comment(
            reply, filediff, reply_to=comment)

        rsp = self.apiPut(
            get_review_reply_diff_comment_item_url(
                reply, reply_comment.pk, self.local_site_name),
            {'text': new_comment_text},
            expected_mimetype=review_reply_diff_comment_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')

        reply_comment = Comment.objects.get(pk=rsp['diff_comment']['id'])
        self.assertEqual(reply_comment.text, new_comment_text)

    @add_fixtures(['test_site'])
    def test_put_reply_with_diff_comment_and_local_site_no_access(self):
        """Testing the
        PUT review-requests/<id>/reviews/<id>/replies/<id>/diff-comments/ API
        with a local site and Permission Denied error
        """
        review_request = self.create_review_request(submitter=self.user,
                                                    create_repository=True,
                                                    with_local_site=True,
                                                    publish=True)
        diffset = self.create_diffset(review_request)
        filediff = self.create_filediff(diffset)
        review = self.create_review(review_request)
        comment = self.create_diff_comment(review, filediff)
        reply = self.create_reply(review, user=self.user)
        reply_comment = self.create_diff_comment(
            reply, filediff, reply_to=comment)

        self._login_user()

        rsp = self.apiPut(
            get_review_reply_diff_comment_item_url(
                reply, reply_comment.pk, self.local_site_name),
            {'text': 'My new comment text'},
            expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)
