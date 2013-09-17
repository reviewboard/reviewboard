from django.contrib.auth.models import User
from djblets.testing.decorators import add_fixtures
from djblets.webapi.errors import DOES_NOT_EXIST, PERMISSION_DENIED

from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import (
    watched_review_group_item_mimetype,
    watched_review_group_list_mimetype)
from reviewboard.webapi.tests.urls import (
    get_watched_review_group_item_url,
    get_watched_review_group_list_url)


class WatchedReviewGroupResourceTests(BaseWebAPITestCase):
    """Testing the WatchedReviewGroupResource API tests."""
    fixtures = ['test_users']

    def test_post_watched_review_group(self):
        """Testing the POST users/<username>/watched/review-groups/ API"""
        group = self.create_review_group()

        rsp = self.apiPost(
            get_watched_review_group_list_url(self.user.username),
            {'object_id': group.name},
            expected_mimetype=watched_review_group_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assert_(group in self.user.get_profile().starred_groups.all())

        return group

    def test_post_watched_review_group_with_does_not_exist_error(self):
        """Testing the POST users/<username>/watched/review-groups/ API
        with Does Not Exist error
        """
        rsp = self.apiPost(
            get_watched_review_group_list_url(self.user.username),
            {'object_id': 'invalidgroup'},
            expected_status=404)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], DOES_NOT_EXIST.code)

    @add_fixtures(['test_site'])
    def test_post_watched_review_group_with_site(self):
        """Testing the POST users/<username>/watched/review-groups/ API
        with a local site
        """
        self._login_user(local_site=True)

        username = 'doc'
        user = User.objects.get(username=username)
        group = self.create_review_group(with_local_site=True)

        rsp = self.apiPost(
            get_watched_review_group_list_url(username, self.local_site_name),
            {'object_id': group.name},
            expected_mimetype=watched_review_group_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue(group in user.get_profile().starred_groups.all())

        return group

    @add_fixtures(['test_site'])
    def test_post_watched_review_group_with_site_does_not_exist_error(self):
        """Testing the POST users/<username>/watched/review-groups/ API
        with a local site and Does Not Exist error
        """
        username = 'doc'

        self._login_user(local_site=True)
        rsp = self.apiPost(
            get_watched_review_group_list_url(username, self.local_site_name),
            {'object_id': 'devgroup'},
            expected_status=404)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], DOES_NOT_EXIST.code)

    @add_fixtures(['test_site'])
    def test_post_watched_review_group_with_site_no_access(self):
        """Testing the POST users/<username>/watched/review-groups/ API
        with a local site and Permission Denied error
        """
        rsp = self.apiPost(
            get_watched_review_group_list_url(self.user.username,
                                              self.local_site_name),
            {'object_id': 'devgroup'},
            expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    def test_delete_watched_review_group(self):
        """Testing the DELETE users/<username>/watched/review-groups/<id>/ API
        """
        # First, star it.
        group = self.test_post_watched_review_group()

        self.apiDelete(
            get_watched_review_group_item_url(self.user.username, group.name))
        self.assertFalse(group in
                         self.user.get_profile().starred_groups.all())

    def test_delete_watched_review_group_with_does_not_exist_error(self):
        """Testing the DELETE users/<username>/watched/review-groups/<id>/ API
        with Does Not Exist error
        """
        rsp = self.apiDelete(
            get_watched_review_group_item_url(self.user.username,
                                              'invalidgroup'),
            expected_status=404)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], DOES_NOT_EXIST.code)

    @add_fixtures(['test_site'])
    def test_delete_watched_review_group_with_site(self):
        """Testing the DELETE users/<username>/watched/review-groups/<id>/ API
        with a local site
        """
        group = self.test_post_watched_review_group_with_site()
        user = User.objects.get(username='doc')

        self.apiDelete(
            get_watched_review_group_item_url(user.username, group.name,
                                              self.local_site_name))
        self.assertFalse(group in user.get_profile().starred_groups.all())

    @add_fixtures(['test_site'])
    def test_delete_watched_review_group_with_site_no_access(self):
        """Testing the DELETE users/<username>/watched/review-groups/<id>/ API
        with a local site and Permission Denied error
        """
        rsp = self.apiDelete(
            get_watched_review_group_item_url(self.user.username, 'group',
                                              self.local_site_name),
            expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    def test_get_watched_review_groups(self):
        """Testing the GET users/<username>/watched/review-groups/ API"""
        self.test_post_watched_review_group()

        rsp = self.apiGet(
            get_watched_review_group_list_url(self.user.username),
            expected_mimetype=watched_review_group_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')

        watched = self.user.get_profile().starred_groups.all()
        apigroups = rsp['watched_review_groups']

        self.assertEqual(len(apigroups), len(watched))

        for id in range(len(watched)):
            self.assertEqual(apigroups[id]['watched_review_group']['name'],
                             watched[id].name)

    @add_fixtures(['test_site'])
    def test_get_watched_review_groups_with_site(self):
        """Testing the GET users/<username>/watched/review-groups/ API
        with a local site
        """
        self.test_post_watched_review_group_with_site()

        rsp = self.apiGet(
            get_watched_review_group_list_url('doc', self.local_site_name),
            expected_mimetype=watched_review_group_list_mimetype)

        watched = self.user.get_profile().starred_groups.filter(
            local_site__name=self.local_site_name)
        apigroups = rsp['watched_review_groups']

        self.assertEqual(rsp['stat'], 'ok')

        for id in range(len(watched)):
            self.assertEqual(apigroups[id]['watched_review_group']['name'],
                             watched[id].name)

    @add_fixtures(['test_site'])
    def test_get_watched_review_groups_with_site_no_access(self):
        """Testing the GET users/<username>/watched/review-groups/ API
        with a local site and Permission Denied error
        """
        rsp = self.apiGet(
            get_watched_review_group_list_url(self.user.username,
                                              self.local_site_name),
            expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)
