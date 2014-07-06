from __future__ import unicode_literals

from django.utils import six
from djblets.testing.decorators import add_fixtures
from djblets.webapi.errors import DOES_NOT_EXIST, PERMISSION_DENIED

from reviewboard.webapi.resources import resources
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import (
    watched_review_request_item_mimetype,
    watched_review_request_list_mimetype)
from reviewboard.webapi.tests.mixins import BasicTestsMetaclass
from reviewboard.webapi.tests.urls import (
    get_review_request_item_url,
    get_watched_review_request_item_url,
    get_watched_review_request_list_url)


@six.add_metaclass(BasicTestsMetaclass)
class ResourceListTests(BaseWebAPITestCase):
    """Testing the WatchedReviewRequestResource list API tests."""
    fixtures = ['test_users']
    test_http_methods = ('GET', 'POST')
    sample_api_url = 'users/<username>/watched/review-requests/'
    resource = resources.watched_review_request

    def compare_item(self, item_rsp, obj):
        watched_rsp = item_rsp['watched_review_request']
        self.assertEqual(watched_rsp['id'], obj.display_id)
        self.assertEqual(watched_rsp['summary'], obj.summary)

    #
    # HTTP GET tests
    #

    def setup_basic_get_test(self, user, with_local_site, local_site_name,
                             populate_items):
        if populate_items:
            review_request = self.create_review_request(
                with_local_site=with_local_site,
                publish=True)

            profile = user.get_profile()
            profile.starred_review_requests.add(review_request)
            items = [review_request]
        else:
            items = []

        return (get_watched_review_request_list_url(user.username,
                                                    local_site_name),
                watched_review_request_list_mimetype,
                items)

    @add_fixtures(['test_site'])
    def test_get_with_site_does_not_exist(self):
        """Testing the GET users/<username>/watched/review-requests/ API
        with a local site and Does Not Exist error
        """
        self._login_user(local_site=True)
        rsp = self.api_get(
            get_watched_review_request_list_url(self.user.username,
                                                self.local_site_name),
            expected_status=404)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], DOES_NOT_EXIST.code)

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

        return (get_watched_review_request_list_url(user.username,
                                                    local_site_name),
                watched_review_request_item_mimetype,
                post_data,
                [review_request])

    def check_post_result(self, user, rsp, review_request):
        profile = user.get_profile()
        self.assertTrue(review_request in
                        profile.starred_review_requests.all())

    def test_post_with_does_not_exist_error(self):
        """Testing the POST users/<username>/watched/review-requests/
        with Does Not Exist error
        """
        rsp = self.api_post(
            get_watched_review_request_list_url(self.user.username),
            {'object_id': 999},
            expected_status=404)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], DOES_NOT_EXIST.code)

    @add_fixtures(['test_site'])
    def test_post_with_site_does_not_exist_error(self):
        """Testing the POST users/<username>/watched/review-requests/ API
        with a local site and Does Not Exist error
        """
        user = self._login_user(local_site=True)

        rsp = self.api_post(
            get_watched_review_request_list_url(user.username,
                                                self.local_site_name),
            {'object_id': 10},
            expected_status=404)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], DOES_NOT_EXIST.code)


@six.add_metaclass(BasicTestsMetaclass)
class ResourceItemTests(BaseWebAPITestCase):
    """Testing the WatchedReviewRequestResource item API tests."""
    fixtures = ['test_users']
    test_http_methods = ('DELETE', 'PUT')
    sample_api_url = 'users/<username>/watched/review-requests/<id>/'
    resource = resources.watched_review_request

    def setup_http_not_allowed_item_test(self, user):
        return get_watched_review_request_item_url(user.username, 1)

    #
    # HTTP DELETE tests
    #

    def setup_basic_delete_test(self, user, with_local_site, local_site_name):
        review_request = self.create_review_request(
            with_local_site=with_local_site,
            publish=True)
        profile = user.get_profile()
        profile.starred_review_requests.add(review_request)

        return (get_watched_review_request_item_url(user.username,
                                                    review_request.display_id,
                                                    local_site_name),
                [profile, review_request])

    def check_delete_result(self, user, profile, review_request):
        self.assertFalse(review_request in
                         profile.starred_review_requests.all())

    def test_delete_with_does_not_exist_error(self):
        """Testing the DELETE users/<username>/watched/review_request/<id>/ API
        with Does Not Exist error
        """
        rsp = self.api_delete(
            get_watched_review_request_item_url(self.user.username, 999),
            expected_status=404)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], DOES_NOT_EXIST.code)

    #
    # HTTP GET tests
    #

    def test_get(self):
        """Testing the GET users/<username>/watched/review-requests/<id>/ API
        """
        review_request = self.create_review_request(publish=True)
        profile = self.user.get_profile()
        profile.starred_review_requests.add(review_request)

        expected_url = (self.base_url +
                        get_review_request_item_url(review_request.display_id))

        self.api_get(
            get_watched_review_request_item_url(self.user.username,
                                                review_request.display_id),
            expected_status=302,
            expected_headers={
                'Location': expected_url,
            })

    @add_fixtures(['test_site'])
    def test_get_with_site(self):
        """Testing the GET users/<username>/watched/review-requests/<id>/ API
        with access to a local site
        """
        user = self._login_user(local_site=True)

        review_request = self.create_review_request(with_local_site=True,
                                                    publish=True)
        profile = user.get_profile()
        profile.starred_review_requests.add(review_request)

        expected_url = (self.base_url +
                        get_review_request_item_url(review_request.display_id,
                                                    self.local_site_name))

        self.api_get(
            get_watched_review_request_item_url(user.username,
                                                review_request.display_id,
                                                self.local_site_name),
            expected_status=302,
            expected_headers={
                'Location': expected_url,
            })

    @add_fixtures(['test_site'])
    def test_get_with_site_no_access(self):
        """Testing the GET users/<username>/watched/review-requests/<id>/ API
        without access to a local site
        """
        review_request = self.create_review_request(with_local_site=True,
                                                    publish=True)
        profile = self.user.get_profile()
        profile.starred_review_requests.add(review_request)

        rsp = self.api_get(
            get_watched_review_request_item_url(self.user.username,
                                                review_request.display_id,
                                                self.local_site_name),
            expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)
