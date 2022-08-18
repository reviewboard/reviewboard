"""Unit tests for the RepositoryUserResource.

Version Added:
    4.0.11
"""

from django.contrib.auth.models import User
from djblets.testing.decorators import add_fixtures
from djblets.webapi.errors import PERMISSION_DENIED
from djblets.webapi.testing.decorators import webapi_test_template

from reviewboard.webapi.errors import INVALID_USER
from reviewboard.webapi.resources import resources
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import (repository_user_item_mimetype,
                                                repository_user_list_mimetype)
from reviewboard.webapi.tests.mixins import BasicTestsMetaclass
from reviewboard.webapi.tests.urls import (get_repository_user_item_url,
                                           get_repository_user_list_url,
                                           get_user_item_url)


class ResourceListTests(BaseWebAPITestCase, metaclass=BasicTestsMetaclass):
    """Unit tests for the RepositoryUserResource list API.

    Version Added:
        4.0.11
    """

    fixtures = ['test_users', 'test_scmtools']
    sample_api_url = 'repositories/<id>/users/'
    resource = resources.repository_user
    basic_get_use_admin = True
    basic_post_use_admin = True

    def compare_item(self, item_rsp, user):
        """Compare an item in the results.

        Args:
            item_rsp (dict):
                The response object.

            user (django.contrib.auth.models.User):
                The user to compare against.
        """
        self.assertEqual(item_rsp['id'], user.pk)
        self.assertEqual(item_rsp['username'], user.username)
        self.assertEqual(item_rsp['first_name'], user.first_name)
        self.assertEqual(item_rsp['last_name'], user.last_name)

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
                User.objects.get(username='doc'),
                User.objects.get(username='grumpy'),
            ]
            repository.users.add(*items)
        else:
            items = []

        return (get_repository_user_list_url(repository, local_site_name),
                repository_user_list_mimetype,
                items)

    @webapi_test_template
    def test_get_with_no_access(self):
        """Testing the GET <URL> API with Permission Denied"""
        repository = self.create_repository()
        rsp = self.api_get(get_repository_user_list_url(repository),
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

        if post_valid_data:
            post_data = {
                'username': 'doc',
            }
        else:
            post_data = {}

        return (get_repository_user_list_url(repository, local_site_name),
                repository_user_item_mimetype,
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
        users = list(repository.users.all())
        self.assertEqual(len(users), 1)
        self.assertEqual(users[0].username, 'doc')
        self.compare_item(rsp['user'], users[0])

    @webapi_test_template
    def test_post_with_no_access(self):
        """Testing the POST <URL> API with Permission Denied"""
        repository = self.create_repository()
        user = User.objects.get(pk=1)

        rsp = self.api_post(
            get_repository_user_list_url(repository),
            {'username': user.username},
            expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')

    @webapi_test_template
    def test_post_with_invalid_user(self):
        """Testing the POST <URL> API with invalid user"""
        self._login_user(admin=True)

        repository = self.create_repository()

        rsp = self.api_post(
            get_repository_user_list_url(repository),
            {'username': 'grabl'},
            expected_status=400)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], INVALID_USER.code)

    @add_fixtures(['test_site'])
    @webapi_test_template
    def test_post_with_site(self):
        """Testing the POST <URL> API with a local site"""
        self._login_user(admin=True)

        user = User.objects.get(username='doc')

        local_site = self.get_local_site(name=self.local_site_name)
        local_site.users.add(user)

        repository = self.create_repository(with_local_site=True)

        rsp = self.api_post(
            get_repository_user_list_url(repository, self.local_site_name),
            {'username': 'doc'},
            expected_mimetype=repository_user_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')

        users = list(repository.users.all())
        self.assertEqual(len(users), 1)
        self.assertEqual(users[0], user)

    @add_fixtures(['test_site'])
    @webapi_test_template
    def test_post_with_site_non_member(self):
        """Testing the POST <URL> API with a local site and a user who is not a
        member
        """
        self._login_user(admin=True)

        repository = self.create_repository(with_local_site=True)

        rsp = self.api_post(
            get_repository_user_list_url(repository, self.local_site_name),
            {'username': 'grumpy'},
            expected_status=400)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], INVALID_USER.code)


class ResourceItemTests(BaseWebAPITestCase, metaclass=BasicTestsMetaclass):
    """Unit tests for the RepositoryUserResource item API."""

    fixtures = ['test_users', 'test_scmtools']
    sample_api_url = 'repositories/<id>/users/<username>/'
    resource = resources.repository_user
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
        return get_repository_user_list_url(repository)

    def compare_item(self, item_rsp, user):
        """Compare an item in the results.

        Args:
            item_rsp (dict):
                The response object.

            user (django.contrib.auth.models.User):
                The user to compare against.
        """
        self.assertEqual(item_rsp['id'], user.pk)
        self.assertEqual(item_rsp['username'], user.username)
        self.assertEqual(item_rsp['first_name'], user.first_name)
        self.assertEqual(item_rsp['last_name'], user.last_name)

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
        doc = User.objects.get(username='doc')
        repository.users.add(doc)

        return (get_repository_user_item_url(repository, doc.username,
                                             local_site_name),
                [repository, doc])

    def check_delete_result(self, user, repository, doc):
        """Check the result of an HTTP DELETE.

        Args:
            user (django.contrib.auth.models.User, unused):
                The user to run the test as.

            repository (reviewboard.scmtools.models.Repository):
                The repository being tested.

            doc (django.contrib.auth.models.User):
                The user being removed from the repository.
        """
        self.assertNotIn(doc, repository.users.all())

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
            A 3-tuple containing the resource URL, the expected mimetype, and
            the item to compare.
        """
        repository = self.create_repository(with_local_site=with_local_site)
        doc = User.objects.get(username='doc')
        repository.users.add(doc)

        return (get_repository_user_item_url(repository, doc.username,
                                             local_site_name),
                repository_user_item_mimetype,
                doc)

    @webapi_test_template
    def test_get_delete_link(self):
        """Testing the GET <URL> API contains the correct DELETE link"""
        self._login_user(admin=True)

        doc = User.objects.get(username='doc')
        repository = self.create_repository()
        repository.users.add(doc)

        rsp = self.api_get(
            get_repository_user_item_url(repository, doc.username),
            expected_mimetype=repository_user_item_mimetype)

        delete_href = \
            rsp['user']['links']['delete']['href'][len(self.base_url):]

        self.assertEqual(
            delete_href,
            get_repository_user_item_url(repository, doc.username))

        self.assertNotEqual(delete_href, get_user_item_url(doc.username))

    @add_fixtures(['test_site'])
    @webapi_test_template
    def test_get_delete_link_local_site(self):
        """Testing the GET <URL> API contains the correct DELETE link with a local
        site
        """
        self._login_user(admin=True)

        doc = User.objects.get(username='doc')

        local_site = self.get_local_site(self.local_site_name)
        local_site.users.add(doc)

        repository = self.create_repository(local_site=local_site)
        repository.users.add(doc)

        rsp = self.api_get(
            get_repository_user_item_url(repository, doc.username,
                                         local_site.name),
            expected_mimetype=repository_user_item_mimetype)

        delete_href = \
            rsp['user']['links']['delete']['href'][len(self.base_url):]

        self.assertEqual(
            delete_href,
            get_repository_user_item_url(repository, doc.username,
                                         local_site.name))

        self.assertNotEqual(delete_href,
                            get_user_item_url(doc.username, local_site.name))
