from django.contrib.auth.models import User
from djblets.webapi.errors import DOES_NOT_EXIST, PERMISSION_DENIED

from reviewboard.reviews.models import ReviewRequest
from reviewboard.site.models import LocalSite
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import (
    watched_review_request_item_mimetype,
    watched_review_request_list_mimetype)
from reviewboard.webapi.tests.urls import (
    get_watched_review_request_item_url,
    get_watched_review_request_list_url)


class WatchedReviewRequestResourceTests(BaseWebAPITestCase):
    """Testing the WatchedReviewRequestResource API tests."""
    fixtures = ['test_users', 'test_scmtools', 'test_reviewrequests',
                'test_site']

    def test_post_watched_review_request(self):
        """Testing the POST users/<username>/watched/review-request/ API"""
        review_request = ReviewRequest.objects.public()[0]
        rsp = self.apiPost(
            get_watched_review_request_list_url(self.user.username),
            {'object_id': review_request.display_id},
            expected_mimetype=watched_review_request_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assert_(review_request in
                     self.user.get_profile().starred_review_requests.all())

    def test_post_watched_review_request_with_does_not_exist_error(self):
        """Testing the POST users/<username>/watched/review_request/ with Does Not Exist error"""
        rsp = self.apiPost(
            get_watched_review_request_list_url(self.user.username),
            {'object_id': 999},
            expected_status=404)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], DOES_NOT_EXIST.code)

    def test_post_watched_review_request_with_site(self):
        """Testing the POST users/<username>/watched/review_request/ API with a local site"""
        self._login_user(local_site=True)

        username = 'doc'
        user = User.objects.get(username=username)

        local_site = LocalSite.objects.get(name=self.local_site_name)
        review_request = ReviewRequest.objects.public(local_site=local_site)[0]

        rsp = self.apiPost(
            get_watched_review_request_list_url(username,
                                                self.local_site_name),
            {'object_id': review_request.display_id},
            expected_mimetype=watched_review_request_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue(review_request in
                        user.get_profile().starred_review_requests.all())

    def test_post_watched_review_request_with_site_does_not_exist_error(self):
        """Testing the POST users/<username>/watched/review_request/ API with a local site and Does Not Exist error"""
        self._login_user(local_site=True)
        rsp = self.apiPost(
            get_watched_review_request_list_url('doc', self.local_site_name),
            {'object_id': 10},
            expected_status=404)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], DOES_NOT_EXIST.code)

    def test_post_watched_review_request_with_site_no_access(self):
        """Testing the POST users/<username>/watched/review_request/ API with a local site and Permission Denied error"""
        rsp = self.apiPost(
            get_watched_review_request_list_url('doc', self.local_site_name),
            {'object_id': 10},
            expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    def test_delete_watched_review_request(self):
        """Testing the DELETE users/<username>/watched/review_request/ API"""
        # First, star it.
        self.test_post_watched_review_request()

        review_request = ReviewRequest.objects.public()[0]
        self.apiDelete(
            get_watched_review_request_item_url(self.user.username,
                                                review_request.display_id))
        self.assertTrue(review_request not in
                        self.user.get_profile().starred_review_requests.all())

    def test_delete_watched_review_request_with_does_not_exist_error(self):
        """Testing the DELETE users/<username>/watched/review_request/ API with Does Not Exist error"""
        rsp = self.apiDelete(
            get_watched_review_request_item_url(self.user.username, 999),
            expected_status=404)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], DOES_NOT_EXIST.code)

    def test_delete_watched_review_request_with_site(self):
        """Testing the DELETE users/<username>/watched/review_request/ API with a local site"""
        self.test_post_watched_review_request_with_site()

        user = User.objects.get(username='doc')
        review_request = ReviewRequest.objects.get(
            local_id=1, local_site__name=self.local_site_name)

        self.apiDelete(get_watched_review_request_item_url(
            user.username, review_request.display_id, self.local_site_name))
        self.assertTrue(review_request not in
                        user.get_profile().starred_review_requests.all())

    def test_delete_watched_review_request_with_site_no_access(self):
        """Testing the DELETE users/<username>/watched/review_request/ API with a local site and Permission Denied error"""
        rsp = self.apiDelete(
            get_watched_review_request_item_url(self.user.username, 1,
                                                self.local_site_name),
            expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    def test_get_watched_review_requests(self):
        """Testing the GET users/<username>/watched/review_request/ API"""
        self.test_post_watched_review_request()

        rsp = self.apiGet(
            get_watched_review_request_list_url(self.user.username),
            expected_mimetype=watched_review_request_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')

        watched = self.user.get_profile().starred_review_requests.all()
        apiwatched = rsp['watched_review_requests']

        self.assertEqual(len(watched), len(apiwatched))
        for i in range(len(watched)):
            self.assertEqual(watched[i].id,
                             apiwatched[i]['watched_review_request']['id'])
            self.assertEqual(
                watched[i].summary,
                apiwatched[i]['watched_review_request']['summary'])

    def test_get_watched_review_requests_with_site(self):
        """Testing the GET users/<username>/watched/review_request/ API with a local site"""
        username = 'doc'
        user = User.objects.get(username=username)

        self.test_post_watched_review_request_with_site()

        rsp = self.apiGet(
            get_watched_review_request_list_url(username,
                                                self.local_site_name),
            expected_mimetype=watched_review_request_list_mimetype)

        watched = user.get_profile().starred_review_requests.filter(
            local_site__name=self.local_site_name)
        apiwatched = rsp['watched_review_requests']

        self.assertEqual(len(watched), len(apiwatched))
        for i in range(len(watched)):
            self.assertEqual(watched[i].display_id,
                             apiwatched[i]['watched_review_request']['id'])
            self.assertEqual(
                watched[i].summary,
                apiwatched[i]['watched_review_request']['summary'])

    def test_get_watched_review_requests_with_site_no_access(self):
        """Testing the GET users/<username>/watched/review_request/ API with a local site and Permission Denied error"""
        rsp = self.apiGet(
            get_watched_review_request_list_url(self.user.username,
                                                self.local_site_name),
            expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    def test_get_watched_review_requests_with_site_does_not_exist(self):
        """Testing the GET users/<username>/watched/review_request/ API with a local site and Does Not Exist error"""
        self._login_user(local_site=True)
        rsp = self.apiGet(
            get_watched_review_request_list_url(self.user.username,
                                                self.local_site_name),
            expected_status=404)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], DOES_NOT_EXIST.code)
