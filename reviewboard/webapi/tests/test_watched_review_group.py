from djblets.testing.decorators import add_fixtures
from djblets.webapi.errors import DOES_NOT_EXIST, PERMISSION_DENIED

from reviewboard.accounts.models import Profile
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import (
    watched_review_group_item_mimetype,
    watched_review_group_list_mimetype)
from reviewboard.webapi.tests.urls import (
    get_watched_review_group_item_url,
    get_watched_review_group_list_url)


class ResourceListTests(BaseWebAPITestCase):
    """Testing the WatchedReviewGroupResource list API tests."""
    fixtures = ['test_users']

    #
    # HTTP GET tests
    #

    def test_get_watched_review_groups(self):
        """Testing the GET users/<username>/watched/review-groups/ API"""
        group = self.create_review_group()
        profile = Profile.objects.get(user=self.user)
        profile.starred_groups.add(group)

        rsp = self.apiGet(
            get_watched_review_group_list_url(self.user.username),
            expected_mimetype=watched_review_group_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')

        watched = profile.starred_groups.all()
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
        user = self._login_user(local_site=True)
        group = self.create_review_group(with_local_site=True)
        profile = Profile.objects.get(user=user)
        profile.starred_groups.add(group)

        rsp = self.apiGet(
            get_watched_review_group_list_url(user.username,
                                              self.local_site_name),
            expected_mimetype=watched_review_group_list_mimetype)

        watched = profile.starred_groups.filter(
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

    #
    # HTTP POST tests
    #

    def test_post_watched_review_group(self):
        """Testing the POST users/<username>/watched/review-groups/ API"""
        group = self.create_review_group()

        rsp = self.apiPost(
            get_watched_review_group_list_url(self.user.username),
            {'object_id': group.name},
            expected_mimetype=watched_review_group_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        profile = Profile.objects.get(user=self.user)
        self.assertTrue(group in profile.starred_groups.all())

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
        user = self._login_user(local_site=True)
        group = self.create_review_group(with_local_site=True)

        rsp = self.apiPost(
            get_watched_review_group_list_url(user.username,
                                              self.local_site_name),
            {'object_id': group.name},
            expected_mimetype=watched_review_group_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        profile = Profile.objects.get(user=user)
        self.assertTrue(group in profile.starred_groups.all())

        return group

    @add_fixtures(['test_site'])
    def test_post_watched_review_group_with_site_does_not_exist_error(self):
        """Testing the POST users/<username>/watched/review-groups/ API
        with a local site and Does Not Exist error
        """
        user = self._login_user(local_site=True)
        rsp = self.apiPost(
            get_watched_review_group_list_url(user.username,
                                              self.local_site_name),
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


class ResourceItemTests(BaseWebAPITestCase):
    """Testing the WatchedReviewGroupResource item API tests."""
    fixtures = ['test_users']

    #
    # HTTP DELETE tests
    #

    def test_delete_watched_review_group(self):
        """Testing the DELETE users/<username>/watched/review-groups/<id>/ API
        """
        # First, star it.
        group = self.create_review_group()
        profile = Profile.objects.get(user=self.user)
        profile.starred_groups.add(group)

        self.apiDelete(
            get_watched_review_group_item_url(self.user.username, group.name))

        self.assertFalse(group in profile.starred_groups.all())

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
        user = self._login_user(local_site=True)
        group = self.create_review_group(with_local_site=True)
        profile = Profile.objects.get(user=user)
        profile.starred_groups.add(group)

        self.apiDelete(
            get_watched_review_group_item_url(user.username, group.name,
                                              self.local_site_name))
        self.assertFalse(group in profile.starred_groups.all())

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
