from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.utils import six
from djblets.webapi.errors import PERMISSION_DENIED

from reviewboard.reviews.models import Comment
from reviewboard.webapi.resources import resources
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import (
    review_diff_comment_item_mimetype,
    review_diff_comment_list_mimetype)
from reviewboard.webapi.tests.mixins import (
    BasicTestsMetaclass,
    ReviewRequestChildItemMixin,
    ReviewRequestChildListMixin)
from reviewboard.webapi.tests.mixins_comment import (
    CommentItemMixin,
    CommentListMixin)
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

    def _create_diff_review_with_issue(self, publish=False, comment_text=None,
                                       expected_status=201):
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


@six.add_metaclass(BasicTestsMetaclass)
class ResourceListTests(CommentListMixin, ReviewRequestChildListMixin,
                        BaseResourceTestCase):
    """Testing the ReviewDiffCommentResource list APIs."""
    fixtures = ['test_users', 'test_scmtools']
    sample_api_url = 'review-requests/<id>/reviews/<id>/diff-comments/'
    resource = resources.review_diff_comment

    def setup_review_request_child_test(self, review_request):
        if not review_request.repository_id:
            # The group tests don't create a repository by default.
            review_request.repository = self.create_repository()
            review_request.save()

        diffset = self.create_diffset(review_request)
        self.create_filediff(diffset)
        review = self.create_review(review_request, publish=True)

        return (get_review_diff_comment_list_url(review),
                review_diff_comment_list_mimetype)

    def compare_item(self, item_rsp, comment):
        self.assertEqual(item_rsp['id'], comment.pk)
        self.assertEqual(item_rsp['text'], comment.text)
        self.assertEqual(item_rsp['issue_opened'], comment.issue_opened)
        self.assertEqual(item_rsp['first_line'], comment.first_line)
        self.assertEqual(item_rsp['num_lines'], comment.num_lines)
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
            create_repository=True,
            with_local_site=with_local_site,
            submitter=user,
            publish=True)
        diffset = self.create_diffset(review_request)
        filediff = self.create_filediff(diffset)
        review = self.create_review(review_request, publish=True)

        if populate_items:
            items = [self.create_diff_comment(review, filediff)]
        else:
            items = []

        return (get_review_diff_comment_list_url(review, local_site_name),
                review_diff_comment_list_mimetype,
                items)

    def test_get_with_counts_only(self):
        """Testing the
        GET review-requests/<id>/reviews/<id>/diff-comments/?counts-only=1 API
        """
        review = self._create_diff_review()

        rsp = self.api_get(get_review_diff_comment_list_url(review), {
            'counts-only': 1,
        }, expected_mimetype=review_diff_comment_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['count'], review.comments.count())

    def test_get_with_interdiff(self):
        """Testing the GET review-requests/<id>/reviews/<id>/diff-comments/ API
        with interdiff
        """
        comment_text = "Test diff comment"

        comment, review_request, review, interdiff_revision = \
            self._common_post_interdiff_comments(comment_text)

        rsp = self.api_get(get_review_diff_comment_list_url(review), {
            'interdiff-revision': interdiff_revision,
        }, expected_mimetype=review_diff_comment_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertIn('diff_comments', rsp)
        self.assertEqual(len(rsp['diff_comments']), 1)
        self.assertEqual(rsp['diff_comments'][0]['text'], comment_text)

    #
    # HTTP POST tests
    #

    def setup_basic_post_test(self, user, with_local_site, local_site_name,
                              post_valid_data):
        review_request = self.create_review_request(
            create_repository=True,
            with_local_site=with_local_site,
            submitter=user,
            publish=True)
        diffset = self.create_diffset(review_request)
        filediff = self.create_filediff(diffset)
        review = self.create_review(review_request, user=user)

        return (get_review_diff_comment_list_url(review, local_site_name),
                review_diff_comment_item_mimetype,
                {
                    'filediff_id': filediff.pk,
                    'text': 'My new text',
                    'first_line': 1,
                    'num_lines': 2,
                },
                [review])

    def check_post_result(self, user, rsp, review):
        comment_rsp = rsp['diff_comment']
        self.assertEqual(comment_rsp['text'], 'My new text')
        self.assertEqual(comment_rsp['text_type'], 'plain')

        comment = Comment.objects.get(pk=comment_rsp['id'])
        self.compare_item(comment_rsp, comment)

    def test_post_with_issue(self):
        """Testing the
        POST review-requests/<id>/reviews/<id>/diff-comments/ API
        with an issue
        """
        diff_comment_text = 'Test diff comment with an opened issue'

        review_request, filediff = self._create_diff_review_request()
        review = self.create_review(review_request, user=self.user)
        rsp = self.api_post(
            get_review_diff_comment_list_url(review),
            {
                'filediff_id': filediff.pk,
                'issue_opened': True,
                'first_line': 1,
                'num_lines': 5,
                'text': diff_comment_text,
            },
            expected_mimetype=review_diff_comment_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertIn('diff_comment', rsp)
        self.assertEqual(rsp['diff_comment']['text'], diff_comment_text)
        self.assertTrue(rsp['diff_comment']['issue_opened'])

    def test_post_with_interdiff(self):
        """Testing the
        POST review-requests/<id>/reviews/<id>/diff-comments/ API
        with interdiff
        """
        comment_text = "Test diff comment"

        review_request, filediff = self._create_diff_review_request()

        # Post the second diff.
        interdiffset = self.create_diffset(review_request)
        interfilediff = self.create_filediff(interdiffset)

        review = self.create_review(review_request, user=self.user)

        rsp = self.api_post(
            get_review_diff_comment_list_url(review),
            {
                'filediff_id': filediff.pk,
                'interfilediff_id': interfilediff.pk,
                'issue_opened': True,
                'first_line': 1,
                'num_lines': 5,
                'text': comment_text,
            },
            expected_mimetype=review_diff_comment_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertIn('diff_comment', rsp)
        self.assertEqual(rsp['diff_comment']['text'], comment_text)

        comment = Comment.objects.get(pk=rsp['diff_comment']['id'])
        self.assertEqual(comment.filediff_id, filediff.pk)
        self.assertEqual(comment.interfilediff_id, interfilediff.pk)


@six.add_metaclass(BasicTestsMetaclass)
class ResourceItemTests(CommentItemMixin, ReviewRequestChildItemMixin,
                        BaseResourceTestCase):
    """Testing the ReviewDiffCommentResource item APIs."""
    fixtures = ['test_users', 'test_scmtools']
    sample_api_url = 'review-requests/<id>/reviews/<id>/diff-comments/'
    resource = resources.review_diff_comment

    def setup_review_request_child_test(self, review_request):
        if not review_request.repository_id:
            # The group tests don't create a repository by default.
            review_request.repository = self.create_repository()
            review_request.save()

        diffset = self.create_diffset(review_request)
        filediff = self.create_filediff(diffset)
        review = self.create_review(review_request, publish=True)
        comment = self.create_diff_comment(review, filediff)

        return (get_review_diff_comment_item_url(review, comment.pk),
                review_diff_comment_item_mimetype)

    def compare_item(self, item_rsp, comment):
        self.assertEqual(item_rsp['id'], comment.pk)
        self.assertEqual(item_rsp['text'], comment.text)
        self.assertEqual(item_rsp['issue_opened'], comment.issue_opened)
        self.assertEqual(item_rsp['first_line'], comment.first_line)
        self.assertEqual(item_rsp['num_lines'], comment.num_lines)
        self.assertEqual(item_rsp['extra_data'], comment.extra_data)

        if comment.rich_text:
            self.assertEqual(item_rsp['text_type'], 'markdown')
        else:
            self.assertEqual(item_rsp['text_type'], 'plain')

    #
    # HTTP DELETE tests
    #

    def setup_basic_delete_test(self, user, with_local_site, local_site_name):
        review_request = self.create_review_request(
            create_repository=True,
            with_local_site=with_local_site,
            submitter=user,
            publish=True)
        diffset = self.create_diffset(review_request)
        filediff = self.create_filediff(diffset)
        review = self.create_review(review_request, user=user)
        comment = self.create_diff_comment(review, filediff)

        return (get_review_diff_comment_item_url(review, comment.pk,
                                                 local_site_name),
                [comment, review])

    def check_delete_result(self, user, comment, review):
        self.assertNotIn(comment, review.comments.all())

    def test_delete_with_interdiff(self):
        """Testing the
        DELETE review-requests/<id>/reviews/<id>/diff-comments/<id>/ API
        """
        comment_text = "This is a test comment."

        comment, review_request, review, interdiff_revision = \
            self._common_post_interdiff_comments(comment_text)

        self.api_delete(get_review_diff_comment_item_url(review, comment.pk))

        rsp = self.api_get(get_review_diff_comment_list_url(review),
                           expected_mimetype=review_diff_comment_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertIn('diff_comments', rsp)
        self.assertEqual(len(rsp['diff_comments']), 0)

    #
    # HTTP GET tests
    #

    def setup_basic_get_test(self, user, with_local_site, local_site_name):
        review_request = self.create_review_request(
            create_repository=True,
            with_local_site=with_local_site,
            submitter=user,
            publish=True)
        diffset = self.create_diffset(review_request)
        filediff = self.create_filediff(diffset)
        review = self.create_review(review_request, user=user)
        comment = self.create_diff_comment(review, filediff)

        return (get_review_diff_comment_item_url(review, comment.pk,
                                                 local_site_name),
                review_diff_comment_item_mimetype,
                comment)

    def test_get_not_modified(self):
        """Testing the
        GET review-requests/<id>/reviews/<id>/diff-comments/<id>/ API
        with Not Modified response
        """
        review = self._create_diff_review()
        comment = Comment.objects.all()[0]

        self._testHttpCaching(
            get_review_diff_comment_item_url(review, comment.id),
            check_etags=True)

    #
    # HTTP PUT tests
    #

    def setup_basic_put_test(self, user, with_local_site, local_site_name,
                             put_valid_data):
        review_request = self.create_review_request(
            create_repository=True,
            with_local_site=with_local_site,
            submitter=user,
            publish=True)
        diffset = self.create_diffset(review_request)
        filediff = self.create_filediff(diffset)
        review = self.create_review(review_request, user=user)
        comment = self.create_diff_comment(review, filediff)

        return (get_review_diff_comment_item_url(review, comment.pk,
                                                 local_site_name),
                review_diff_comment_item_mimetype,
                {'text': 'My new text'},
                comment,
                [])

    def check_put_result(self, user, item_rsp, comment, *args):
        self.assertEqual(item_rsp['id'], comment.pk)
        self.assertEqual(item_rsp['text'], 'My new text')
        self.assertEqual(item_rsp['text_type'], 'plain')
        self.compare_item(item_rsp, Comment.objects.get(pk=comment.pk))

    def test_put_with_issue(self):
        """Testing the
        PUT review-requests/<id>/reviews/<id>/diff-comments/<id>/ API,
        removing issue_opened
        """
        comment, review, review_request = self._create_diff_review_with_issue()

        rsp = self.api_put(
            get_review_diff_comment_item_url(review, comment.id),
            {'issue_opened': False},
            expected_mimetype=review_diff_comment_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertFalse(rsp['diff_comment']['issue_opened'])

    def test_put_issue_status_before_publish(self):
        """Testing the
        PUT review-requests/<id>/reviews/<id>/diff-comments/<id>/ API
        with an issue, before review is published
        """
        comment, review, review_request = self._create_diff_review_with_issue()

        # The issue_status should not be able to be changed while the review is
        # unpublished.
        rsp = self.api_put(
            get_review_diff_comment_item_url(review, comment.id),
            {'issue_status': 'resolved'},
            expected_mimetype=review_diff_comment_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')

        # The issue_status should still be "open"
        self.assertEqual(rsp['diff_comment']['issue_status'], 'open')

    def test_put_issue_status_after_publish(self):
        """Testing the
        PUT review-requests/<id>/reviews/<id>/diff-comments/<id>/ API
        with an issue, after review is published
        """
        comment, review, review_request = self._create_diff_review_with_issue(
            publish=True)

        rsp = self.api_put(
            get_review_diff_comment_item_url(review, comment.id),
            {'issue_status': 'resolved'},
            expected_mimetype=review_diff_comment_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['diff_comment']['issue_status'], 'resolved')

    def test_put_issue_status_by_issue_creator(self):
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
        rsp = self.api_put(
            get_review_diff_comment_item_url(review, comment.id),
            {'issue_status': 'dropped'},
            expected_mimetype=review_diff_comment_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['diff_comment']['issue_status'], 'dropped')

    def test_put_issue_status_by_uninvolved_user(self):
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

        rsp = self.api_put(
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

        rsp = self.api_put(
            get_review_diff_comment_item_url(review, comment.id),
            {'issue_opened': False},
            expected_mimetype=review_diff_comment_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['diff_comment']['issue_status'], '')
