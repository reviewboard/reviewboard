from djblets.testing.decorators import add_fixtures
from djblets.webapi.errors import DOES_NOT_EXIST, PERMISSION_DENIED

from reviewboard.accounts.models import Profile
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import (
    watched_review_request_item_mimetype,
    watched_review_request_list_mimetype)
from reviewboard.webapi.tests.urls import (
    get_watched_review_request_item_url,
    get_watched_review_request_list_url)


class ResourceListTests(BaseWebAPITestCase):
    """Testing the WatchedReviewRequestResource list API tests."""
    fixtures = ['test_users']

    #
    # HTTP GET tests
    #

    def test_get(self):
        """Testing the GET users/<username>/watched/review_request/ API"""
        review_request = self.create_review_request(publish=True)
        profile = Profile.objects.get(user=self.user)
        profile.starred_review_requests.add(review_request)

        rsp = self.apiGet(
            get_watched_review_request_list_url(self.user.username),
            expected_mimetype=watched_review_request_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')

        watched = profile.starred_review_requests.all()
        apiwatched = rsp['watched_review_requests']

        self.assertEqual(len(watched), len(apiwatched))

        for i in range(len(watched)):
            self.assertEqual(watched[i].id,
                             apiwatched[i]['watched_review_request']['id'])
            self.assertEqual(
                watched[i].summary,
                apiwatched[i]['watched_review_request']['summary'])

    @add_fixtures(['test_site'])
    def test_get_with_site(self):
        """Testing the GET users/<username>/watched/review_request/ API
        with a local site
        """
        user = self._login_user(local_site=True)

        review_request = self.create_review_request(with_local_site=True,
                                                    publish=True)
        profile = Profile.objects.get(user=user)
        profile.starred_review_requests.add(review_request)

        rsp = self.apiGet(
            get_watched_review_request_list_url(user.username,
                                                self.local_site_name),
            expected_mimetype=watched_review_request_list_mimetype)

        watched = profile.starred_review_requests.filter(
            local_site__name=self.local_site_name)
        apiwatched = rsp['watched_review_requests']

        self.assertEqual(len(watched), len(apiwatched))
        for i in range(len(watched)):
            self.assertEqual(watched[i].display_id,
                             apiwatched[i]['watched_review_request']['id'])
            self.assertEqual(
                watched[i].summary,
                apiwatched[i]['watched_review_request']['summary'])

    @add_fixtures(['test_site'])
    def test_get_with_site_no_access(self):
        """Testing the GET users/<username>/watched/review_request/ API
        with a local site and Permission Denied error
        """
        rsp = self.apiGet(
            get_watched_review_request_list_url(self.user.username,
                                                self.local_site_name),
            expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    @add_fixtures(['test_site'])
    def test_get_with_site_does_not_exist(self):
        """Testing the GET users/<username>/watched/review_request/ API
        with a local site and Does Not Exist error
        """
        self._login_user(local_site=True)
        rsp = self.apiGet(
            get_watched_review_request_list_url(self.user.username,
                                                self.local_site_name),
            expected_status=404)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], DOES_NOT_EXIST.code)

    #
    # HTTP POST tests
    #

    def test_post(self):
        """Testing the POST users/<username>/watched/review-request/ API"""
        review_request = self.create_review_request(publish=True)
        rsp = self.apiPost(
            get_watched_review_request_list_url(self.user.username),
            {'object_id': review_request.display_id},
            expected_mimetype=watched_review_request_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        profile = Profile.objects.get(user=self.user)
        self.assertTrue(review_request in
                        profile.starred_review_requests.all())

    def test_post_with_does_not_exist_error(self):
        """Testing the POST users/<username>/watched/review_request/
        with Does Not Exist error
        """
        rsp = self.apiPost(
            get_watched_review_request_list_url(self.user.username),
            {'object_id': 999},
            expected_status=404)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], DOES_NOT_EXIST.code)

    @add_fixtures(['test_site'])
    def test_post_with_site(self):
        """Testing the POST users/<username>/watched/review_request/ API
        with a local site
        """
        user = self._login_user(local_site=True)
        review_request = self.create_review_request(with_local_site=True,
                                                    publish=True)

        rsp = self.apiPost(
            get_watched_review_request_list_url(user.username,
                                                self.local_site_name),
            {'object_id': review_request.display_id},
            expected_mimetype=watched_review_request_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')

        profile = Profile.objects.get(user=user)
        self.assertTrue(review_request in
                        profile.starred_review_requests.all())

        return review_request

    @add_fixtures(['test_site'])
    def test_post_with_site_does_not_exist_error(self):
        """Testing the POST users/<username>/watched/review_request/ API
        with a local site and Does Not Exist error
        """
        user = self._login_user(local_site=True)

        rsp = self.apiPost(
            get_watched_review_request_list_url(user.username,
                                                self.local_site_name),
            {'object_id': 10},
            expected_status=404)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], DOES_NOT_EXIST.code)

    @add_fixtures(['test_site'])
    def test_post_with_site_no_access(self):
        """Testing the POST users/<username>/watched/review_request/ API
        with a local site and Permission Denied error
        """
        rsp = self.apiPost(
            get_watched_review_request_list_url(self.user.username,
                                                self.local_site_name),
            {'object_id': 10},
            expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)


class ResourceItemTests(BaseWebAPITestCase):
    """Testing the WatchedReviewRequestResource item API tests."""
    fixtures = ['test_users']

    #
    # HTTP DELETE tests
    #

    def test_delete(self):
        """Testing the DELETE users/<username>/watched/review_request/ API"""
        # First, star it.
        review_request = self.create_review_request(publish=True)
        profile = self.user.get_profile()
        profile.starred_review_requests.add(review_request)

        review_request = self.create_review_request(publish=True)
        self.apiDelete(
            get_watched_review_request_item_url(self.user.username,
                                                review_request.display_id))

        profile = Profile.objects.get(user=self.user)
        self.assertTrue(review_request not in
                        profile.starred_review_requests.all())

    def test_delete_with_does_not_exist_error(self):
        """Testing the DELETE users/<username>/watched/review_request/ API
        with Does Not Exist error
        """
        rsp = self.apiDelete(
            get_watched_review_request_item_url(self.user.username, 999),
            expected_status=404)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], DOES_NOT_EXIST.code)

    @add_fixtures(['test_site'])
    def test_delete_with_site(self):
        """Testing the DELETE users/<username>/watched/review_request/ API
        with a local site
        """
        user = self._login_user(local_site=True)
        review_request = self.create_review_request(with_local_site=True,
                                                    publish=True)
        profile = Profile.objects.get(user=user)
        profile.starred_review_requests.add(review_request)

        self.apiDelete(get_watched_review_request_item_url(
            user.username, review_request.display_id, self.local_site_name))
        self.assertTrue(review_request not in
                        profile.starred_review_requests.all())

    @add_fixtures(['test_site'])
    def test_delete_with_site_no_access(self):
        """Testing the DELETE users/<username>/watched/review_request/ API
        with a local site and Permission Denied error
        """
        rsp = self.apiDelete(
            get_watched_review_request_item_url(self.user.username, 1,
                                                self.local_site_name),
            expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)
