"""Tests for the DiffContextResource."""

from __future__ import unicode_literals

from django.utils import six
from djblets.webapi.testing.decorators import webapi_test_template

from reviewboard.webapi.resources import resources
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import diff_context_mimetype
from reviewboard.webapi.tests.mixins import (BaseReviewRequestChildMixin,
                                             BasicTestsMetaclass)
from reviewboard.webapi.tests.urls import get_diff_context_url


@six.add_metaclass(BasicTestsMetaclass)
class ResourceTests(BaseWebAPITestCase, BaseReviewRequestChildMixin):
    """Testing the DiffContextResource APIs."""

    resource = resources.diff_context
    test_http_methods = ('GET',)

    sample_api_url = 'review-requests/<id>/diff-context/'

    fixtures = ['test_scmtools', 'test_users']

    def compare_item(self, item_rsp, obj):
        review_request, diffset, interdiffset = obj

        self.assertIn('revision', item_rsp)
        revision_info = item_rsp['revision']

        self.assertIn('interdiff_revision', revision_info)
        self.assertIn('is_draft_diff', revision_info)
        self.assertIn('is_draft_interdiff', revision_info)
        self.assertIn('is_interdiff', revision_info)
        self.assertIn('latest_revision', revision_info)
        self.assertIn('revision', revision_info)

        self.assertEqual(revision_info['is_draft_diff'], None)
        self.assertEqual(revision_info['is_draft_interdiff'], None)
        self.assertEqual(revision_info['is_interdiff'],
                         interdiffset is not None)
        self.assertEqual(revision_info['latest_revision'],
                         review_request.get_latest_diffset().revision)
        self.assertEqual(revision_info['revision'], diffset.revision)

        self.assertIn('num_diffs', item_rsp)

        if interdiffset:
            self.assertEqual(revision_info['interdiff_revision'],
                             interdiffset.revision)
            self.assertEqual(item_rsp['num_diffs'], 2)
        else:
            self.assertEqual(revision_info['interdiff_revision'],
                             None)
            self.assertEqual(item_rsp['num_diffs'], 1)

    #
    # HTTP GET tests
    #

    def setup_basic_get_test(self, user, with_local_site, local_site_name,
                             with_interdiff=False):
        repository = self.create_repository(with_local_site=with_local_site,)
        review_request = self.create_review_request(with_local_site,
                                                    repository=repository,
                                                    public=True,
                                                    submitter=user)

        diffset = self.create_diffset(review_request=review_request,
                                      repository=repository)
        self.create_filediff(diffset)

        if with_interdiff:
            interdiffset = diffset

            diffset = self.create_diffset(review_request,
                                          repository=repository,
                                          revision=2)
            self.create_filediff(diffset)
        else:
            interdiffset = None

        return (
            get_diff_context_url(
                review_request_id=review_request.display_id,
                local_site_name=local_site_name),
            diff_context_mimetype,
            (review_request, diffset, interdiffset)
        )

    def setup_review_request_child_test(self, review_request):
        """Set up the review request child tests.

        Args:
            review_request (reviewboard.reviews.models.review_request.
                            ReviewRequest):
                The test review request.

        Returns:
            tuple:
            A tuple of the API list URL and list mimetype to run tests on.
        """
        review_request.repository = self.create_repository()
        diffset = self.create_diffset(review_request)
        self.create_filediff(diffset)

        return (
            get_diff_context_url(review_request_id=review_request.display_id),
            diff_context_mimetype)

    @webapi_test_template
    def test_get_interdiff(self):
        """Testing the GET <URL> API with an interdiff"""
        url, mimetype, (review_request, diffset, interdiffset) = \
            self.setup_basic_get_test(user=self.user,
                                      with_local_site=False,
                                      local_site_name=None,
                                      with_interdiff=True)

        rsp = self.api_get(
            url,
            {
                'revision': diffset.revision,
                'interdiff-revision': interdiffset.revision,
            },
            expected_mimetype=mimetype)

        self.assertIn('stat', rsp)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertIn(self.resource.item_result_key, rsp)
        self.compare_item(rsp[self.resource.item_result_key],
                          (review_request, diffset, interdiffset))
