from __future__ import unicode_literals

from django.utils import six
from djblets.testing.decorators import add_fixtures
from djblets.webapi.errors import DOES_NOT_EXIST, PERMISSION_DENIED

from reviewboard.webapi.resources import resources
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import (
    watched_review_group_item_mimetype,
    watched_review_group_list_mimetype)
from reviewboard.webapi.tests.mixins import BasicTestsMetaclass
from reviewboard.webapi.tests.urls import (
    get_review_group_item_url,
    get_watched_review_group_item_url,
    get_watched_review_group_list_url)


@six.add_metaclass(BasicTestsMetaclass)
class ResourceListTests(BaseWebAPITestCase):
    """Testing the WatchedReviewGroupResource list API tests."""
    fixtures = ['test_users']
    sample_api_url = 'users/<username>/watched/review-groups/'
    resource = resources.watched_review_group

    def compare_item(self, item_rsp, obj):
        watched_rsp = item_rsp['watched_review_group']
        self.assertEqual(watched_rsp['id'], obj.pk)
        self.assertEqual(watched_rsp['name'], obj.name)

    #
    # HTTP GET tests
    #

    def setup_basic_get_test(self, user, with_local_site, local_site_name,
                             populate_items):
        if populate_items:
            group = self.create_review_group(with_local_site=with_local_site)
            profile = user.get_profile()
            profile.starred_groups.add(group)
            items = [group]
        else:
            items = []

        return (get_watched_review_group_list_url(user.username,
                                                  local_site_name),
                watched_review_group_list_mimetype,
                items)

    #
    # HTTP POST tests
    #

    def setup_basic_post_test(self, user, with_local_site, local_site_name,
                              post_valid_data):
        group = self.create_review_group(with_local_site=with_local_site)

        if post_valid_data:
            post_data = {
                'object_id': group.name,
            }
        else:
            post_data = {}

        return (get_watched_review_group_list_url(user.username,
                                                  local_site_name),
                watched_review_group_item_mimetype,
                post_data,
                [group])

    def check_post_result(self, user, rsp, group):
        profile = user.get_profile()
        self.assertIn(group, profile.starred_groups.all())

    def test_post_with_does_not_exist_error(self):
        """Testing the POST users/<username>/watched/review-groups/ API
        with Does Not Exist error
        """
        rsp = self.api_post(
            get_watched_review_group_list_url(self.user.username),
            {'object_id': 'invalidgroup'},
            expected_status=404)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], DOES_NOT_EXIST.code)

    @add_fixtures(['test_site'])
    def test_post_with_site_does_not_exist_error(self):
        """Testing the POST users/<username>/watched/review-groups/ API
        with a local site and Does Not Exist error
        """
        user = self._login_user(local_site=True)
        rsp = self.api_post(
            get_watched_review_group_list_url(user.username,
                                              self.local_site_name),
            {'object_id': 'devgroup'},
            expected_status=404)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], DOES_NOT_EXIST.code)


@six.add_metaclass(BasicTestsMetaclass)
class ResourceItemTests(BaseWebAPITestCase):
    """Testing the WatchedReviewGroupResource item API tests."""
    fixtures = ['test_users']
    test_http_methods = ('DELETE', 'PUT')
    sample_api_url = 'users/<username>/watched/review-groups/<id>/'
    resource = resources.watched_review_group

    def setup_http_not_allowed_item_test(self, user):
        return get_watched_review_group_item_url(user.username, 'my-group')

    #
    # HTTP DELETE tests
    #

    def setup_basic_delete_test(self, user, with_local_site, local_site_name):
        group = self.create_review_group(with_local_site=with_local_site)
        profile = user.get_profile()
        profile.starred_groups.add(group)

        return (get_watched_review_group_item_url(user.username, group.name,
                                                  local_site_name),
                [profile, group])

    def check_delete_result(self, user, profile, group):
        self.assertNotIn(group, profile.starred_groups.all())

    def test_delete_with_does_not_exist_error(self):
        """Testing the DELETE users/<username>/watched/review-groups/<id>/ API
        with Does Not Exist error
        """
        rsp = self.api_delete(
            get_watched_review_group_item_url(self.user.username,
                                              'invalidgroup'),
            expected_status=404)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], DOES_NOT_EXIST.code)

    #
    # HTTP GET tests
    #

    def test_get(self):
        """Testing the GET users/<username>/watched/review-groups/<id>/ API"""
        group = self.create_review_group()
        profile = self.user.get_profile()
        profile.starred_groups.add(group)

        expected_url = self.base_url + get_review_group_item_url(group.name)

        self.api_get(
            get_watched_review_group_item_url(self.user.username, group.pk),
            expected_status=302,
            expected_headers={
                'Location': expected_url,
            })

    @add_fixtures(['test_site'])
    def test_get_with_site(self):
        """Testing the GET users/<username>/watched/review-groups/<id>/ API
        with access to a local site
        """
        user = self._login_user(local_site=True)

        group = self.create_review_group(with_local_site=True)
        profile = user.get_profile()
        profile.starred_groups.add(group)

        expected_url = (
            self.base_url +
            get_review_group_item_url(group.name, self.local_site_name))

        self.api_get(
            get_watched_review_group_item_url(user.username, group.pk,
                                              self.local_site_name),
            expected_status=302,
            expected_headers={
                'Location': expected_url,
            })

    @add_fixtures(['test_site'])
    def test_get_with_site_no_access(self):
        """Testing the GET users/<username>/watched/review-groups/<id>/ API
        without access to a local site
        """
        group = self.create_review_group(with_local_site=True)
        profile = self.user.get_profile()
        profile.starred_groups.add(group)

        rsp = self.api_get(
            get_watched_review_group_item_url(self.user.username, group.pk,
                                              self.local_site_name),
            expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)
