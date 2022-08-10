"""Unit tests for the RepositoryGroupResource.

Version Added:
    4.0.11
"""

from djblets.testing.decorators import add_fixtures
from djblets.webapi.errors import PERMISSION_DENIED
from djblets.webapi.testing.decorators import webapi_test_template

from reviewboard.webapi.errors import INVALID_GROUP
from reviewboard.webapi.resources import resources
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import (
    repository_group_item_mimetype,
    repository_group_list_mimetype)
from reviewboard.webapi.tests.mixins import BasicTestsMetaclass
from reviewboard.webapi.tests.urls import (get_repository_group_item_url,
                                           get_repository_group_list_url,
                                           get_review_group_item_url)


class ResourceListTests(BaseWebAPITestCase, metaclass=BasicTestsMetaclass):
    """Unit tests for the RepositoryGroupResource list API.

    Version Added:
        4.0.11
    """

    fixtures = ['test_users', 'test_scmtools']
    sample_api_url = 'repositories/<id>/groups/'
    resource = resources.repository_group
    basic_get_use_admin = True
    basic_post_use_admin = True

    def compare_item(self, item_rsp, group):
        """Compare an item in the results.

        Args:
            item_rsp (dict):
                The response object.

            group (reviewboard.reviews.models.group.Group):
                The group to compare against.
        """
        self.assertEqual(item_rsp['id'], group.pk)
        self.assertEqual(item_rsp['name'], group.name)
        self.assertEqual(item_rsp['display_name'], group.display_name)

    #
    # HTTP GET tests
    #

    def setup_basic_get_test(self, user, with_local_site, local_site_name,
                             populate_items):
        """Set up data for GET tests.

        Args:
            user (django.contrib.auth.models.User, unused):
                The user for the test.

            with_local_site (bool):
                Whether to set up the test with a local site.

            local_site_name (unicode):
                The name of the local site to use, if appropriate.

            populate_items (bool):
                Whether to populate the list with items.

        Returns:
            tuple:
            A 3-tuple containing the resource URL, the expected mimetype, and
            the list of items.
        """
        repository = self.create_repository(with_local_site=with_local_site)

        if populate_items:
            items = [
                self.create_review_group(name='test-group-1',
                                         with_local_site=with_local_site,
                                         invite_only=True),
                self.create_review_group(name='test-group-2',
                                         with_local_site=with_local_site,
                                         invite_only=True),
            ]
            repository.review_groups.add(*items)
        else:
            items = []

        return (get_repository_group_list_url(repository, local_site_name),
                repository_group_list_mimetype,
                items)

    @webapi_test_template
    def test_get_with_no_access(self):
        """Testing the GET <URL> API with Permission Denied"""
        repository = self.create_repository()
        rsp = self.api_get(get_repository_group_list_url(repository),
                           expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    #
    # HTTP POST tests
    #

    def setup_basic_post_test(self, user, with_local_site, local_site_name,
                              post_valid_data):
        """Set up data for POST tests.

        Args:
            user (django.contrib.auth.models.User, unused):
                The user for the test.

            with_local_site (bool):
                Whether to set up the test with a local site.

            local_site_name (unicode):
                The name of the local site to use, if appropriate.

            post_valid_data (bool):
                Whether to send valid data for the post.

        Returns:
            tuple:
            A 4-tuple containing the resource URL, the expected mimetype, the
            data to post, and the items to use for the tests.
        """
        repository = self.create_repository(with_local_site=with_local_site)
        group = self.create_review_group(with_local_site=with_local_site,
                                         invite_only=True)

        if post_valid_data:
            post_data = {
                'group_name': group.name,
            }
        else:
            post_data = {}

        return (get_repository_group_list_url(repository, local_site_name),
                repository_group_item_mimetype,
                post_data,
                [repository])

    def check_post_result(self, user, rsp, repository):
        """Check the result of a POST operation.

        Args:
            user (django.contrib.auth.models.User, unused):
                The user making the request.

            rsp (dict):
                The request from the API.

            repository (reviewboard.scmtools.models.Repository):
                The repository being changed.
        """
        groups = list(repository.review_groups.all())
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0].name, 'test-group')
        self.compare_item(rsp['group'], groups[0])

    @webapi_test_template
    def test_post_with_no_access(self):
        """Testing the POST <URL> API with Permission Denied"""
        repository = self.create_repository()
        group = self.create_review_group(invite_only=True)

        rsp = self.api_post(
            get_repository_group_list_url(repository),
            {'group_name': group.name},
            expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')

    @webapi_test_template
    def test_post_with_invalid_group(self):
        """Testing the POST <URL> API with invalid group"""
        self._login_user(admin=True)

        repository = self.create_repository()

        rsp = self.api_post(
            get_repository_group_list_url(repository),
            {'group_name': 'oops'},
            expected_status=400)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], INVALID_GROUP.code)

    @webapi_test_template
    def test_post_with_non_invite_only_group(self):
        """Testing the POST <URL> API with a group that is not invite only"""
        self._login_user(admin=True)

        repository = self.create_repository()
        group = self.create_review_group(invite_only=False)

        rsp = self.api_post(
            get_repository_group_list_url(repository),
            {'group_name': group.name},
            expected_status=400)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], INVALID_GROUP.code)

    @add_fixtures(['test_site'])
    @webapi_test_template
    def test_post_with_site(self):
        """Testing the POST <URL> API with a local site"""
        self._login_user(admin=True)

        repository = self.create_repository(with_local_site=True)
        group = self.create_review_group(with_local_site=True,
                                         invite_only=True)

        rsp = self.api_post(
            get_repository_group_list_url(repository, self.local_site_name),
            {'group_name': group.name},
            expected_mimetype=repository_group_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')

        groups = list(repository.review_groups.all())
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0], group)

    @add_fixtures(['test_site'])
    @webapi_test_template
    def test_post_with_site_non_member(self):
        """Testing the POST <URL> API with a local site and a group that is not
        in that site
        """
        self._login_user(admin=True)

        repository = self.create_repository(with_local_site=True)
        group = self.create_review_group(with_local_site=False,
                                         invite_only=True)

        rsp = self.api_post(
            get_repository_group_list_url(repository, self.local_site_name),
            {'group_name': group.name},
            expected_status=400)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], INVALID_GROUP.code)


class ResourceItemTests(BaseWebAPITestCase, metaclass=BasicTestsMetaclass):
    """Unit tests for the RepositoryGroupResource item API."""

    fixtures = ['test_users', 'test_scmtools']
    sample_api_url = 'repositories/<id>/groups/<group_id>/'
    resource = resources.repository_group
    basic_delete_use_admin = True
    basic_get_use_admin = True
    basic_put_use_admin = True

    def setup_http_not_allowed_item_test(self, user):
        """Set up the HTTP not allowed test.

        Args:
            user (django.contrib.auth.models.User, unused):
                The user to set up the test for.

        Returns:
            unicode:
            The URL to fetch for the test.
        """
        repository = self.create_repository()
        return get_repository_group_list_url(repository)

    def compare_item(self, item_rsp, group):
        """Compare an item in the results.

        Args:
            item_rsp (dict):
                The response object.

            group (reviewboard.reviews.models.group.Group):
                The group to compare against.
        """
        self.assertEqual(item_rsp['id'], group.pk)
        self.assertEqual(item_rsp['name'], group.name)
        self.assertEqual(item_rsp['display_name'], group.display_name)

    #
    # HTTP DELETE tests
    #

    def setup_basic_delete_test(self, user, with_local_site, local_site_name):
        """Set up data for DELETE tests.

        Args:
            user (django.contrib.auth.models.User, unused):
                The user to run the test as.

            with_local_site (bool):
                Whether to use a local site.

            local_site_name (unicode):
                The name of the local site to test with, if available.

        Returns:
            tuple:
            A 2-tuple containing the resource URL, and a list of objects to
            use.
        """
        repository = self.create_repository(with_local_site=with_local_site)
        group = self.create_review_group(with_local_site=with_local_site,
                                         invite_only=True)
        repository.review_groups.add(group)

        return (get_repository_group_item_url(repository, group.name,
                                              local_site_name),
                [repository, group])

    def check_delete_result(self, user, repository, group):
        """Check the result of an HTTP DELETE.

        Args:
            user (django.contrib.auth.models.User, unused):
                The user to run the test as.

            repository (reviewboard.scmtools.models.Repository):
                The repository being tested.

            group (reviewboard.reviews.models.group.Group):
                The group being removed from the repository.
        """
        self.assertNotIn(group, repository.review_groups.all())

    #
    # HTTP GET tests
    #

    def setup_basic_get_test(self, user, with_local_site, local_site_name):
        """Set up data for GET tests.

        Args:
            user (django.contrib.auth.models.User, unused):
                The user for the test.

            with_local_site (bool):
                Whether to set up the test with a local site.

            local_site_name (unicode):
                The name of the local site to use, if appropriate.

        Returns:
            tuple:
            A 3-tuple containing the resources URL, the expected mimetype, and
            the item to compare.
        """
        repository = self.create_repository(with_local_site=with_local_site)
        group = self.create_review_group(with_local_site=with_local_site,
                                         invite_only=True)
        repository.review_groups.add(group)

        return (get_repository_group_item_url(repository, group.name,
                                              local_site_name),
                repository_group_item_mimetype,
                group)

    @webapi_test_template
    def test_get_delete_link(self):
        """Testing the GET <URL> API contains the correct DELETE link"""
        self._login_user(admin=True)

        repository = self.create_repository()
        group = self.create_review_group(invite_only=True)
        repository.review_groups.add(group)

        rsp = self.api_get(
            get_repository_group_item_url(repository, group.name),
            expected_mimetype=repository_group_item_mimetype)

        delete_href = \
            rsp['group']['links']['delete']['href'][len(self.base_url):]

        self.assertEqual(
            delete_href,
            get_repository_group_item_url(repository, group.name))
        self.assertNotEqual(delete_href, get_review_group_item_url(group.name))

    @add_fixtures(['test_site'])
    @webapi_test_template
    def test_get_delete_link_local_site(self):
        """Testing the GET <URL> API contains the correct DELETE link with a
        local site
        """
        self._login_user(admin=True)

        repository = self.create_repository(with_local_site=True)
        group = self.create_review_group(with_local_site=True,
                                         invite_only=True)
        repository.review_groups.add(group)

        rsp = self.api_get(
            get_repository_group_item_url(repository, group.name,
                                          self.local_site_name),
            expected_mimetype=repository_group_item_mimetype)

        delete_href = \
            rsp['group']['links']['delete']['href'][len(self.base_url):]

        self.assertEqual(
            delete_href,
            get_repository_group_item_url(repository, group.name,
                                          self.local_site_name))
        self.assertNotEqual(
            delete_href,
            get_review_group_item_url(group.name, self.local_site_name))
