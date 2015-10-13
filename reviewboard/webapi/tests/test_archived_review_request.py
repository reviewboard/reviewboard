from __future__ import unicode_literals

from django.utils import six
from djblets.testing.decorators import add_fixtures
from djblets.webapi.errors import DOES_NOT_EXIST

from reviewboard.accounts.models import ReviewRequestVisit
from reviewboard.webapi.resources import resources
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import archived_item_mimetype
from reviewboard.webapi.tests.mixins import BasicTestsMetaclass
from reviewboard.webapi.tests.urls import (
    get_archived_review_request_item_url,
    get_archived_review_request_list_url)


@six.add_metaclass(BasicTestsMetaclass)
class ResourceListTests(BaseWebAPITestCase):
    """Testing the ArchivedReviewRequestResource list API tests"""

    fixtures = ['test_users']
    test_http_methods = ('POST',)
    sample_api_url = 'users/<username>/archived-review-requests/'
    resource = resources.archived_review_request

    def compare_item(self, item_rsp, obj):
        self.assertEqual(item_rsp['id'], obj.display_id)

    #
    # HTTP POST tests
    #

    def setup_basic_post_test(self, user, with_local_site, local_site_name,
                              post_valid_data):
        review_request = self.create_review_request(
            with_local_site=with_local_site,
            publish=True)

        if post_valid_data:
            post_data = {
                'object_id': review_request.display_id,
            }
        else:
            post_data = {}

        return (get_archived_review_request_list_url(user.username,
                                                     local_site_name),
                archived_item_mimetype,
                post_data,
                [review_request])

    def check_post_result(self, user, rsp, review_request):
        visit = review_request.visits.get(user=user)
        self.assertEqual(visit.visibility, ReviewRequestVisit.ARCHIVED)
        self.compare_item(rsp['archived_review_request'], review_request)

    def test_post_with_does_not_exist_error(self):
        """Testing the POST users/<username>/archived-review-requests/
        with Does Not Exist error
        """
        rsp = self.api_post(
            get_archived_review_request_list_url(self.user.username),
            {'object_id': 999},
            expected_status=404)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], DOES_NOT_EXIST.code)

    @add_fixtures(['test_site'])
    def test_post_with_site_does_not_exist_error(self):
        """Testing the POST users/<username>/archived-review-requests/ API
        with a local site and Does Not Exist error
        """
        user = self._login_user(local_site=True)

        rsp = self.api_post(
            get_archived_review_request_list_url(user.username,
                                                 self.local_site_name),
            {'object_id': 10},
            expected_status=404)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], DOES_NOT_EXIST.code)


@six.add_metaclass(BasicTestsMetaclass)
class ResourceItemTests(BaseWebAPITestCase):
    """Testing the ArchivedReviewRequestResource item API tests."""

    fixtures = ['test_users']
    test_http_methods = ('DELETE',)
    sample_api_url = 'users/<username>/archived-review-requests/<id>/'
    resource = resources.archived_review_request

    def setup_http_not_allowed_item_test(self, user):
        return get_archived_review_request_item_url(user.username, 1)

    #
    # HTTP DELETE tests
    #

    def setup_basic_delete_test(self, user, with_local_site, local_site_name):
        review_request = self.create_review_request(
            with_local_site=with_local_site,
            publish=True)
        self.create_visit(review_request,
                          visibility=ReviewRequestVisit.ARCHIVED, user=user)

        return (get_archived_review_request_item_url(user.username,
                                                     review_request.display_id,
                                                     local_site_name),
                [review_request])

    def check_delete_result(self, user, review_request):
        visit = review_request.visits.get(user=user)
        self.assertEqual(visit.visibility, ReviewRequestVisit.VISIBLE)

    def test_delete_with_does_not_exist_error(self):
        """Testing the DELETE users/<username>/archived_review_request/<id>/
        API with Does Not Exist error
        """
        rsp = self.api_delete(
            get_archived_review_request_item_url(self.user.username, 999),
            expected_status=404)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], DOES_NOT_EXIST.code)
