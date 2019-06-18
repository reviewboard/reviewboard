from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.utils import six
from djblets.features.testing import override_feature_check
from djblets.webapi.errors import INVALID_FORM_DATA, PERMISSION_DENIED
from djblets.webapi.testing.decorators import webapi_test_template
from kgb import SpyAgency

from reviewboard.diffviewer.features import dvcs_feature
from reviewboard.diffviewer.models import FileDiff
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

    def _create_diff_review_request(self, with_local_site=False,
                                    with_history=False):
        review_request = self.create_review_request(
            create_repository=True,
            submitter=self.user,
            with_local_site=with_local_site,
            create_with_history=with_history,
            publish=True)
        diffset = self.create_diffset(review_request)

        if with_history:
            commit = self.create_diffcommit(diffset=diffset)
        else:
            commit = None

        filediff = self.create_filediff(diffset=diffset, commit=commit)

        return review_request, filediff

    def _create_diff_review(self):
        review_request, filediff = self._create_diff_review_request()

        review = self.create_review(review_request, publish=True)
        self.create_diff_comment(review, filediff)

        return review


def _compare_item(self, item_rsp, comment):
    """Compare the API response with the object that was serialized.

    Args:
        item_rsp (dict):
            The serialized comment.

        comment (reviewboard.reviews.models.diff_comment.Comment):
            The comment that was serialized.

    Raises:
        AssertionError:
            The API response was not equivalent to the object.
    """
    self.assertEqual(item_rsp['id'], comment.pk)
    self.assertEqual(item_rsp['text'], comment.text)
    self.assertEqual(item_rsp['issue_opened'], comment.issue_opened)
    self.assertEqual(item_rsp['first_line'], comment.first_line)
    self.assertEqual(item_rsp['num_lines'], comment.num_lines)

    self.assertEqual(item_rsp['extra_data'],
                     self.resource._strip_private_data(comment.extra_data))

    if comment.rich_text:
        self.assertEqual(item_rsp['text_type'], 'markdown')
    else:
        self.assertEqual(item_rsp['text_type'], 'plain')


@six.add_metaclass(BasicTestsMetaclass)
class ResourceListTests(SpyAgency, CommentListMixin,
                        ReviewRequestChildListMixin, BaseResourceTestCase):
    """Testing the ReviewDiffCommentResource list APIs."""
    fixtures = ['test_users', 'test_scmtools']
    sample_api_url = 'review-requests/<id>/reviews/<id>/diff-comments/'
    resource = resources.review_diff_comment

    compare_item = _compare_item

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

    @webapi_test_template
    def test_post_with_interfilediff_same_filediff(self):
        """Testing the POST <URL> API with interfilediff_id == filediff_id"""
        review_request, filediff = self._create_diff_review_request()
        review = self.create_review(review_request, user=self.user)

        rsp = self.api_post(
            get_review_diff_comment_list_url(review),
            {
                'filediff_id': filediff.pk,
                'interfilediff_id': filediff.pk,
                'issue_opened': True,
                'first_line': 1,
                'num_lines': 5,
                'text': 'foo',
            },
            expected_status=400)

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], INVALID_FORM_DATA.code)
        self.assertEqual(rsp['fields'], {
            'interfilediff_id': ['This cannot be the same as filediff_id.'],
        })

    @webapi_test_template
    def test_post_with_interfilediff_outside_diffset_history(self):
        """Testing the POST <URL> API with interfilediff_id corresponding to a
        FileDiff outside the current DiffSetHistory
        """
        review_request, filediff = self._create_diff_review_request()
        review = self.create_review(review_request, user=self.user)

        other_filediff = self._create_diff_review_request()[1]

        rsp = self.api_post(
            get_review_diff_comment_list_url(review),
            {
                'filediff_id': filediff.pk,
                'interfilediff_id': other_filediff.pk,
                'issue_opened': True,
                'first_line': 1,
                'num_lines': 5,
                'text': 'foo',
            },
            expected_status=400)

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], INVALID_FORM_DATA.code)
        self.assertEqual(rsp['fields'], {
            'interfilediff_id': ['This is not a valid interfilediff ID.'],
        })

    @webapi_test_template
    def test_post_with_base_filediff_dvcs_enabled_with_history(self):
        """Testing the POST <URL> API with base_filediff_id with DVCS enabled
        on a review reqest created with commit history
        """
        with override_feature_check(dvcs_feature.feature_id, enabled=True):
            review_request = self.create_review_request(
                create_repository=True,
                create_with_history=True,
                publish=True)

            diffset = self.create_diffset(review_request)

            commits = [
                self.create_diffcommit(diffset=diffset, commit_id='r1',
                                       parent_id='r0'),
                self.create_diffcommit(diffset=diffset, commit_id='r2',
                                       parent_id='r1'),
            ]

            filediffs = [
                self.create_filediff(diffset=diffset, commit=commits[0],
                                     source_file='/foo', source_revision='1',
                                     dest_file='/foo', dest_detail='2'),
                self.create_filediff(diffset=diffset, commit=commits[1],
                                     source_file='/foo', source_revision='2',
                                     dest_file='/foo', dest_detail='3'),
            ]
            review = self.create_review(review_request, user=self.user)

            rsp = self.api_post(
                get_review_diff_comment_list_url(review),
                {
                    'filediff_id': filediffs[1].pk,
                    'base_filediff_id': filediffs[0].pk,
                    'issue_opened': True,
                    'first_line': 1,
                    'num_lines': 5,
                    'text': 'foo',
                },
                expected_mimetype=review_diff_comment_item_mimetype)

            self.assertEqual(rsp['stat'], 'ok')
            self.assertIn('diff_comment', rsp)

            item_rsp = rsp['diff_comment']
            comment = Comment.objects.get(pk=item_rsp['id'])

            self.compare_item(item_rsp, comment)

    @webapi_test_template
    def test_post_with_base_filediff_dvcs_disabled(self):
        """Testing the POST <URL> API with base_filediff_id when DVCS feature
        disabled
        """
        with override_feature_check(dvcs_feature.feature_id, enabled=False):
            review_request, filediff = self._create_diff_review_request()
            review = self.create_review(review_request, user=self.user)

            rsp = self.api_post(
                get_review_diff_comment_list_url(review),
                {
                    'filediff_id': filediff.pk,
                    'base_filediff_id': filediff.pk,
                    'issue_opened': True,
                    'first_line': 1,
                    'num_lines': 5,
                    'text': 'foo',
                },
                expected_mimetype=review_diff_comment_item_mimetype)

            self.assertEqual(rsp['stat'], 'ok')
            self.assertIn('diff_comment', rsp)

            item_rsp = rsp['diff_comment']
            comment = Comment.objects.get(pk=item_rsp['id'])

            self.compare_item(item_rsp, comment)

    @webapi_test_template
    def test_post_with_base_filediff_dvcs_enabled_no_history(self):
        """Testing the POST <URL> API with base_filediff_id when DVCS feature
        enabled and review request not created with commit history
        """
        with override_feature_check(dvcs_feature.feature_id, enabled=True):
            review_request, filediff = self._create_diff_review_request()
            review = self.create_review(review_request, user=self.user)

            rsp = self.api_post(
                get_review_diff_comment_list_url(review),
                {
                    'filediff_id': filediff.pk,
                    'base_filediff_id': filediff.pk,
                    'issue_opened': True,
                    'first_line': 1,
                    'num_lines': 5,
                    'text': 'foo',
                },
                expected_status=400)

            self.assertEqual(rsp['stat'], 'fail')
            self.assertEqual(rsp['err']['code'], INVALID_FORM_DATA.code)
            self.assertEqual(
                rsp['fields']['base_filediff_id'],
                ['This field cannot be specified on review requests created '
                 'without history support.'])

    @webapi_test_template
    def test_post_with_base_filediff_dvcs_enabled_with_history_same_id(self):
        """Testing the POST <URL> API with base_filediff_id=filediff_id"""
        with override_feature_check(dvcs_feature.feature_id, enabled=True):
            review_request, filediff = self._create_diff_review_request(
                with_history=True)
            review = self.create_review(review_request, user=self.user)

            rsp = self.api_post(
                get_review_diff_comment_list_url(review),
                {
                    'filediff_id': filediff.pk,
                    'base_filediff_id': filediff.pk,
                    'issue_opened': True,
                    'first_line': 1,
                    'num_lines': 5,
                    'text': 'foo',
                },
                expected_status=400)

            self.assertEqual(rsp, {
                'stat': 'fail',
                'err': {
                    'code': INVALID_FORM_DATA.code,
                    'msg': INVALID_FORM_DATA.msg,
                },
                'fields': {
                    'base_filediff_id': [
                        'This cannot be the same as filediff_id.',
                    ],
                },
            })

    @webapi_test_template
    def test_post_with_base_filediff_interdiff_dvcs_disabled(self):
        """Testing the POST <URL> API with base_filediff_id and interdiff_id
        when DVCS feature disabled
        """
        with override_feature_check(dvcs_feature.feature_id, enabled=False):
            review_request, filediff = self._create_diff_review_request()
            review = self.create_review(review_request, user=self.user)

            interdiffset = self.create_diffset(review_request)
            interfilediff = self.create_filediff(interdiffset)

            rsp = self.api_post(
                get_review_diff_comment_list_url(review),
                {
                    'filediff_id': filediff.pk,
                    'base_filediff_id': filediff.pk,
                    'interfilediff_id': interfilediff.pk,
                    'issue_opened': True,
                    'first_line': 1,
                    'num_lines': 5,
                    'text': 'foo',
                },
                expected_mimetype=review_diff_comment_item_mimetype)

            self.assertEqual(rsp['stat'], 'ok')
            self.assertIn('diff_comment', rsp)

            item_rsp = rsp['diff_comment']
            comment = Comment.objects.get(pk=item_rsp['id'])

            self.compare_item(item_rsp, comment)

    @webapi_test_template
    def test_post_with_base_filediff_interdiff_dvcs_enabled_with_history(self):
        """Testing the POST <URL> API with base_filediff_id and
        interfilediff_id when DVCS feature enabled
        """
        with override_feature_check(dvcs_feature.feature_id, enabled=True):
            review_request, filediff = self._create_diff_review_request(
                with_history=True)
            review = self.create_review(review_request, user=self.user)

            interdiffset = self.create_diffset(review_request)
            interfilediff = self.create_filediff(interdiffset)

            rsp = self.api_post(
                get_review_diff_comment_list_url(review),
                {
                    'filediff_id': filediff.pk,
                    'base_filediff_id': filediff.pk,
                    'interfilediff_id': interfilediff.pk,
                    'issue_opened': True,
                    'first_line': 1,
                    'num_lines': 5,
                    'text': 'foo',
                },
                expected_status=400)

            self.assertEqual(rsp['stat'], 'fail')
            self.assertEqual(rsp['err']['code'], INVALID_FORM_DATA.code)
            self.assertEqual(rsp['fields'], {
                'base_filediff_id': [
                    'This field cannot be specified with interfilediff_id.',
                ],
                'interfilediff_id': [
                    'This field cannot be specified with base_filediff_id.',
                ],
            })

    @webapi_test_template
    def test_post_with_base_filediff_newer(self):
        """Testing the POST <URL> API with base_filediff_id newer than
        filediff_id
        """
        self.spy_on(FileDiff.get_ancestors,
                    owner=FileDiff)

        with override_feature_check(dvcs_feature.feature_id, enabled=True):
            review_request = self.create_review_request(
                create_repository=True,
                create_with_history=True,
                publish=True)

            diffset = self.create_diffset(review_request)

            commits = [
                self.create_diffcommit(diffset=diffset, commit_id='r1',
                                       parent_id='r0'),
                self.create_diffcommit(diffset=diffset, commit_id='r2',
                                       parent_id='r1'),
            ]

            filediffs = [
                self.create_filediff(diffset=diffset, commit=commit)
                for commit in commits
            ]
            review = self.create_review(review_request, user=self.user)

            rsp = self.api_post(
                get_review_diff_comment_list_url(review),
                {
                    'filediff_id': filediffs[0].pk,
                    'base_filediff_id': filediffs[1].pk,
                    'issue_opened': True,
                    'first_line': 1,
                    'num_lines': 5,
                    'text': 'foo',
                },
                expected_status=400)

            self.assertEqual(rsp['stat'], 'fail')
            self.assertEqual(rsp['err']['code'], INVALID_FORM_DATA.code)
            self.assertEqual(rsp['fields'], {
                'base_filediff_id': [
                    'This is not a valid base filediff ID.',
                ],
            })

        self.assertFalse(FileDiff.get_ancestors.called)

    @webapi_test_template
    def test_post_with_base_filediff_same_commit(self):
        """Testing the POST <URL> API with base_filediff_id belonging to a
        different FileDiff in the same commit
        """
        self.spy_on(FileDiff.get_ancestors,
                    owner=FileDiff)

        with override_feature_check(dvcs_feature.feature_id, enabled=True):
            review_request = self.create_review_request(
                create_repository=True,
                create_with_history=True,
                publish=True)

            diffset = self.create_diffset(review_request)
            commit = self.create_diffcommit(diffset=diffset)
            filediffs = [
                self.create_filediff(diffset=diffset, commit=commit),
                self.create_filediff(diffset=diffset, commit=commit),
            ]
            review = self.create_review(review_request, user=self.user)

            rsp = self.api_post(
                get_review_diff_comment_list_url(review),
                {
                    'filediff_id': filediffs[0].pk,
                    'base_filediff_id': filediffs[1].pk,
                    'issue_opened': True,
                    'first_line': 1,
                    'num_lines': 5,
                    'text': 'foo',
                },
                expected_status=400)

            self.assertEqual(rsp['stat'], 'fail')
            self.assertEqual(rsp['err']['code'], INVALID_FORM_DATA.code)
            self.assertEqual(rsp['fields'], {
                'base_filediff_id': [
                    'This is not a valid base filediff ID.',
                ]
            })

        self.assertFalse(FileDiff.get_ancestors.called)

    @webapi_test_template
    def test_post_with_base_filediff_not_exists(self):
        """Testing the POST <URL> API with base_filediff_id set to a
        non-existant ID
        """
        self.spy_on(FileDiff.get_ancestors,
                    owner=FileDiff)

        with override_feature_check(dvcs_feature.feature_id, enabled=True):
            review_request, filediff = self._create_diff_review_request(
                with_history=True)
            review = self.create_review(review_request, user=self.user)

            rsp = self.api_post(
                get_review_diff_comment_list_url(review),
                {
                    'filediff_id': filediff.pk,
                    'base_filediff_id': 12321,
                    'issue_opened': True,
                    'first_line': 1,
                    'num_lines': 5,
                    'text': 'foo',
                },
                expected_status=400)

            self.assertEqual(rsp['stat'], 'fail')
            self.assertEqual(rsp['err']['code'], INVALID_FORM_DATA.code)
            self.assertEqual(rsp['fields'], {
                'base_filediff_id': [
                    'This is not a valid base filediff ID.',
                ]
            })

        self.assertFalse(FileDiff.get_ancestors.called)

    @webapi_test_template
    def test_post_with_base_filediff_outside_diffset(self):
        """Testing the POST <URL> API with base_filediff_id belonging to a
        different DiffSet
        """
        self.spy_on(FileDiff.get_ancestors,
                    owner=FileDiff)

        with override_feature_check(dvcs_feature.feature_id, enabled=True):
            review_request = self.create_review_request(
                create_repository=True,
                create_with_history=True,
                publish=True)

            diffsets = [
                self.create_diffset(review_request, revision=1),
                self.create_diffset(review_request, revision=2)
            ]

            commits = [
                self.create_diffcommit(diffset=diffsets[0], commit_id='r1',
                                       parent_id='r0'),
                self.create_diffcommit(diffset=diffsets[1], commit_id='r2',
                                       parent_id='r1'),
            ]

            filediffs = [
                self.create_filediff(diffset=diffset, commit=commit)
                for diffset, commit in zip(diffsets, commits)
            ]
            review = self.create_review(review_request, user=self.user)

            rsp = self.api_post(
                get_review_diff_comment_list_url(review),
                {
                    'filediff_id': filediffs[1].pk,
                    'base_filediff_id': filediffs[0].pk,
                    'issue_opened': True,
                    'first_line': 1,
                    'num_lines': 5,
                    'text': 'foo',
                },
                expected_status=400)

            self.assertEqual(rsp['stat'], 'fail')
            self.assertEqual(rsp['err']['code'], INVALID_FORM_DATA.code)
            self.assertEqual(rsp['fields'], {
                'base_filediff_id': [
                    'This is not a valid base filediff ID.',
                ],
            })

        self.assertFalse(FileDiff.get_ancestors.called)

    @webapi_test_template
    def test_post_with_base_filediff_outside_history(self):
        """Testing the POST <URL> API with base_filediff_id not belonging to
        the FileDiff's set of ancestors
        """
        self.spy_on(FileDiff.get_ancestors,
                    owner=FileDiff)

        with override_feature_check(dvcs_feature.feature_id, enabled=True):
            review_request = self.create_review_request(
                create_repository=True,
                create_with_history=True,
                publish=True)

            diffset = self.create_diffset(review_request)

            commits = [
                self.create_diffcommit(diffset=diffset, commit_id='r1',
                                       parent_id='r0'),
                self.create_diffcommit(diffset=diffset, commit_id='r2',
                                       parent_id='r1'),
            ]

            filediffs = [
                self.create_filediff(diffset=diffset, commit=commits[0],
                                     source_file='/foo', dest_file='/foo'),
                self.create_filediff(diffset=diffset, commit=commits[1],
                                     source_file='/bar', dest_file='/bar'),
            ]
            review = self.create_review(review_request, user=self.user)

            rsp = self.api_post(
                get_review_diff_comment_list_url(review),
                {
                    'filediff_id': filediffs[1].pk,
                    'base_filediff_id': filediffs[0].pk,
                    'issue_opened': True,
                    'first_line': 1,
                    'num_lines': 5,
                    'text': 'foo',
                },
                expected_status=400)

            self.assertEqual(rsp['stat'], 'fail')
            self.assertEqual(rsp['err']['code'], INVALID_FORM_DATA.code)
            self.assertEqual(rsp['fields'], {
                'base_filediff_id': [
                    'This is not a valid base filediff ID.',
                ],
            })

        self.assertTrue(FileDiff.get_ancestors.called)

    @webapi_test_template
    def test_post_with_base_filediff_ancestor(self):
        """Testing the POST <URL> API with base_filediff_id belonging to
        the FileDiff's set of ancestors
        """
        self.spy_on(FileDiff.get_ancestors,
                    owner=FileDiff)

        with override_feature_check(dvcs_feature.feature_id, enabled=True):
            review_request = self.create_review_request(
                create_repository=True,
                create_with_history=True,
                publish=True)

            diffset = self.create_diffset(review_request)

            commits = [
                self.create_diffcommit(diffset=diffset, commit_id='r1',
                                       parent_id='r0'),
                self.create_diffcommit(diffset=diffset, commit_id='r2',
                                       parent_id='r1'),
            ]

            filediffs = [
                self.create_filediff(diffset=diffset, commit=commits[0],
                                     source_revision='123', dest_detail='124'),
                self.create_filediff(diffset=diffset, commit=commits[1],
                                     source_revision='124', dest_detail='125'),
            ]
            review = self.create_review(review_request, user=self.user)

            rsp = self.api_post(
                get_review_diff_comment_list_url(review),
                {
                    'filediff_id': filediffs[1].pk,
                    'base_filediff_id': filediffs[0].pk,
                    'issue_opened': True,
                    'first_line': 1,
                    'num_lines': 5,
                    'text': 'foo',
                },
                expected_mimetype=review_diff_comment_item_mimetype)

            self.assertEqual(rsp['stat'], 'ok')
            self.assertIn('diff_comment', rsp)

            item_rsp = rsp['diff_comment']
            comment = Comment.objects.get(pk=item_rsp['id'])

            self.compare_item(item_rsp, comment)

        self.assertTrue(FileDiff.get_ancestors.called)

@six.add_metaclass(BasicTestsMetaclass)
class ResourceItemTests(CommentItemMixin, ReviewRequestChildItemMixin,
                        BaseResourceTestCase):
    """Testing the ReviewDiffCommentResource item APIs."""
    fixtures = ['test_users', 'test_scmtools']
    sample_api_url = 'review-requests/<id>/reviews/<id>/diff-comments/'
    resource = resources.review_diff_comment

    compare_item = _compare_item

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

    @webapi_test_template
    def test_get_with_dvcs_disabled(self):
        """Testing the GET <URL> API when DVCS feature disabled"""
        with override_feature_check(dvcs_feature.feature_id, enabled=False):
            review_request = self.create_review_request(
                create_repository=True,
                publish=True)

            diffset = self.create_diffset(review_request)
            commit = self.create_diffcommit(diffset=diffset)

            filediff = self.create_filediff(diffset=diffset, commit=commit)

            review = self.create_review(review_request, user=self.user)
            comment = self.create_diff_comment(review, filediff)

            rsp = self.api_get(
                get_review_diff_comment_item_url(review, comment.pk),
                expected_mimetype=review_diff_comment_item_mimetype)

            self.assertEqual(rsp['stat'], 'ok')
            self.assertIn('diff_comment', rsp)

            item_rsp = rsp['diff_comment']
            self.compare_item(item_rsp, comment)

    @webapi_test_template
    def test_get_with_dvcs_enabled(self):
        """Testing the GET <URL> API when DVCS feature enabled"""
        with override_feature_check(dvcs_feature.feature_id, enabled=True):
            review_request = self.create_review_request(
                create_repository=True,
                publish=True)

            diffset = self.create_diffset(review_request)
            commit = self.create_diffcommit(diffset=diffset)

            filediff = self.create_filediff(diffset=diffset, commit=commit)

            review = self.create_review(review_request, user=self.user)
            comment = self.create_diff_comment(review, filediff)

            rsp = self.api_get(
                get_review_diff_comment_item_url(review, comment.pk),
                expected_mimetype=review_diff_comment_item_mimetype)

            self.assertEqual(rsp['stat'], 'ok')
            self.assertIn('diff_comment', rsp)

            item_rsp = rsp['diff_comment']
            self.compare_item(item_rsp, comment)

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
