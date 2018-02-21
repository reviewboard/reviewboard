from __future__ import unicode_literals

from django.utils import six

from reviewboard.webapi.resources import resources
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import (filediff_item_mimetype,
                                                filediff_list_mimetype)
from reviewboard.webapi.tests.mixins import (BasicTestsMetaclass,
                                             ReviewRequestChildItemMixin,
                                             ReviewRequestChildListMixin)
from reviewboard.webapi.tests.mixins_extra_data import ExtraDataItemMixin
from reviewboard.webapi.tests.urls import (get_filediff_item_url,
                                           get_filediff_list_url)


def _compare_item(self, item_rsp, filediff):
    self.assertEqual(item_rsp['id'], filediff.pk)
    self.assertEqual(item_rsp['extra_data'], filediff.extra_data)
    self.assertEqual(item_rsp['source_file'], filediff.source_file)
    self.assertEqual(item_rsp['dest_file'], filediff.dest_file)
    self.assertEqual(item_rsp['source_revision'], filediff.source_revision)
    self.assertEqual(item_rsp['dest_detail'], filediff.dest_detail)
    self.assertEqual(item_rsp['status'], filediff.status_string)


@six.add_metaclass(BasicTestsMetaclass)
class ResourceListTests(ReviewRequestChildListMixin, BaseWebAPITestCase):
    """Testing the FileDiffResource list APIs."""

    resource = resources.filediff
    sample_api_url = \
        '/api/review-requests/<review-request-id>/diffs/<revision>/files/'

    compare_item = _compare_item
    fixtures = ['test_users', 'test_scmtools']
    test_http_methods = ('GET',)

    #
    # HTTP GET Tests
    #
    def setup_basic_get_test(self, user, with_local_site, local_site_name,
                             populate_items):
        repository = self.create_repository(with_local_site)
        review_request = self.create_review_request(
            with_local_site=with_local_site,
            repository=repository,
            submitter=user,
            publish=True)

        diffset = self.create_diffset(review_request)
        items = []

        if populate_items:
            items.append(self.create_filediff(diffset))

        return (get_filediff_list_url(diffset, review_request,
                                      local_site_name),
                filediff_list_mimetype,
                items)

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
        return (get_filediff_list_url(diffset, review_request),
                filediff_list_mimetype)


@six.add_metaclass(BasicTestsMetaclass)
class ResourceItemTests(ExtraDataItemMixin, ReviewRequestChildItemMixin,
                        BaseWebAPITestCase):
    """Testing the FileDiffResource item APIs."""

    resource = resources.filediff
    sample_api_url = (
        '/api/review-requests/<review-request-id>/diffs/<revision>/files/'
        '<file-id>/'
    )

    compare_item = _compare_item
    fixtures = ['test_users', 'test_scmtools']
    test_http_methods = ('GET',)
    basic_put_use_admin = False

    #
    # HTTP GET Tests
    #

    def setup_basic_get_test(self, user, with_local_site, local_site_name):
        repository = self.create_repository(with_local_site)
        review_request = self.create_review_request(
            with_local_site=with_local_site,
            repository=repository,
            submitter=user,
            publish=True)

        diffset = self.create_diffset(review_request)
        filediff = self.create_filediff(diffset)

        return (get_filediff_item_url(filediff, review_request,
                                      local_site_name),
                filediff_item_mimetype,
                filediff)

    #
    # HTTP PUT Tests
    #

    def setup_basic_put_test(self, user, with_local_site, local_site_name,
                             put_valid_data):
        repository = self.create_repository(with_local_site)
        review_request = self.create_review_request(
            with_local_site=with_local_site,
            repository=repository,
            submitter=user,
            publish=True)

        diffset = self.create_diffset(review_request)
        filediff = self.create_filediff(diffset)

        return (
            get_filediff_item_url(filediff, review_request,
                                  local_site_name),
            filediff_item_mimetype,
            {
                'extra_data.test': 'foo',
            },
            filediff,
            [])

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
        return (get_filediff_list_url(diffset, review_request),
                filediff_list_mimetype)
