"""Unit tests for the RepositoryResource."""

from __future__ import annotations

import os
from typing import Any, Optional, Sequence, TYPE_CHECKING

import kgb
import paramiko
from djblets.testing.decorators import add_fixtures
from djblets.webapi.errors import INVALID_FORM_DATA
from djblets.webapi.testing.decorators import webapi_test_template

from reviewboard import scmtools
from reviewboard.hostingsvcs.bitbucket import Bitbucket
from reviewboard.hostingsvcs.github import GitHub
from reviewboard.hostingsvcs.gitlab import GitLab
from reviewboard.hostingsvcs.models import HostingServiceAccount
from reviewboard.scmtools.errors import (AuthenticationError,
                                         UnverifiedCertificateError)
from reviewboard.scmtools.models import Repository
from reviewboard.ssh.client import SSHClient
from reviewboard.ssh.errors import (BadHostKeyError,
                                    UnknownHostKeyError)
from reviewboard.testing.scmtool import TestTool
from reviewboard.webapi.errors import (BAD_HOST_KEY,
                                       MISSING_USER_KEY,
                                       REPO_AUTHENTICATION_ERROR,
                                       UNVERIFIED_HOST_CERT,
                                       UNVERIFIED_HOST_KEY)
from reviewboard.webapi.resources import resources
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import (repository_item_mimetype,
                                                repository_list_mimetype)
from reviewboard.webapi.tests.mixins import BasicTestsMetaclass
from reviewboard.webapi.tests.mixins_extra_data import (ExtraDataItemMixin,
                                                        ExtraDataListMixin)
from reviewboard.webapi.tests.urls import (get_repository_item_url,
                                           get_repository_list_url)

if TYPE_CHECKING:
    from django.contrib.auth.models import User
    from djblets.util.typing import JSONDict


# Only generate these keys once.
key1 = paramiko.RSAKey.generate(1024)
key2 = paramiko.RSAKey.generate(1024)


class BaseRepositoryTests(kgb.SpyAgency, BaseWebAPITestCase):
    """Base class for the RepositoryResource test suites."""

    fixtures = ['test_users', 'test_scmtools']

    sample_repo_path = (
        'file://' + os.path.abspath(
            os.path.join(os.path.dirname(scmtools.__file__), 'testdata',
                         'git_repo')))

    def compare_item(
        self,
        item_rsp: JSONDict,
        repository: Repository,
    ) -> None:
        """Compare an API result to an object.

        Args:
            item_rsp (dict):
                The encoded data from the API response.

            repository (reviewboard.scmtools.models.Repository):
                The repository object to compare to.
        """
        self.assertEqual(item_rsp['bug_tracker'], repository.bug_tracker)
        self.assertEqual(item_rsp['extra_data'], repository.extra_data)
        self.assertEqual(item_rsp['id'], repository.pk)
        self.assertEqual(item_rsp['mirror_path'], repository.mirror_path)
        self.assertEqual(item_rsp['name'], repository.name)
        self.assertEqual(item_rsp['path'], repository.path)
        self.assertEqual(item_rsp['tool'], repository.tool.name)
        self.assertEqual(item_rsp['visible'], repository.visible)

        if repository.local_site:
            local_site_name = repository.local_site.name
        else:
            local_site_name = None

        item_url = get_repository_item_url(item_rsp['id'], local_site_name)
        self.assertEqual(
            item_rsp['links']['self']['href'],
            f'{self.base_url}{item_url}')

    def _verify_repository_info(
        self,
        rsp: JSONDict,
        expected_tool_id: Optional[str] = None,
        expected_attrs: Optional[dict[str, Any]] = None,
    ) -> Repository:
        """Verify information in a payload and repository.

        This will check that the payload represents a valid, in-database
        repository, and check some of its content against that repository.
        It will also check the repository's tool and attributes against any
        caller-supplied values.

        Args:
            rsp (dict):
                The API response payload to check.

            expected_tool_id (unicode, optional):
                The ID of the tool expected in the repository.

            expected_attrs (dict, optional):
                Expected values for attributes on the repository.

        Returns:
            reviewboard.scmtools.models.Repository:
            The repository corresponding to the payload.

        Raises:
            AssertionError:
                One of the checks failed.
        """
        self.assertEqual(rsp['stat'], 'ok')
        self.assertIn('repository', rsp)
        item_rsp = rsp['repository']

        repository = Repository.objects.get(pk=item_rsp['id'])
        self.compare_item(item_rsp, repository)

        if expected_tool_id:
            self.assertEqual(repository.tool.scmtool_id, expected_tool_id)

        if expected_attrs:
            self.assertAttrsEqual(repository, expected_attrs)

        return repository


class ResourceListTests(ExtraDataListMixin, BaseRepositoryTests,
                        metaclass=BasicTestsMetaclass):
    """Testing the RepositoryResource list APIs."""

    sample_api_url = 'repositories/'
    resource = resources.repository
    basic_post_fixtures = ['test_scmtools']
    basic_post_use_admin = True

    compare_item = BaseRepositoryTests.compare_item

    def setup_http_not_allowed_item_test(
        self,
        user: User,
    ) -> str:
        """Set up a basic HTTP DELETE test.

        Args:
            user (django.contrib.auth.models.User):
                The user performing the API requests.

        Returns:
            str:
            The URL to the API resource to access.
        """
        return get_repository_list_url()

    #
    # HTTP GET tests
    #

    def setup_basic_get_test(
        self,
        user: User,
        with_local_site: bool,
        local_site_name: Optional[str],
        populate_items: bool,
    ) -> tuple[str, str, list[Repository]]:
        """Set up a basic HTTP GET test.

        Args:
            user (django.contrib.auth.models.User):
                The user performing the API requests.

            with_local_site (bool):
                Whether the test is being performed on a Local Site.

            local_site_name (str):
                The name of the Local Site to test against.

            populate_items (bool):
                Whether to pre-create items in the database.

        Returns:
            tuple:
            A 3-tuple of:

            Tuple:
                0 (str):
                    The URL of the API resource to access.

                1 (str):
                    The expected mimetype of the response.

                2 (list):
                    The items to compare to in :py:meth:`compare_item`.
        """
        if populate_items:
            items = [
                self.create_repository(
                    tool_name='Test', with_local_site=with_local_site),
            ]
        else:
            items = []

        return (get_repository_list_url(local_site_name),
                repository_list_mimetype,
                items)

    @add_fixtures(['test_site'])
    @webapi_test_template
    def test_get_with_show_visible(self) -> None:
        """Testing the GET <URL> API with show_invisible=True"""
        self.create_repository(name='test1', tool_name='Test', visible=False)
        self.create_repository(name='test2', tool_name='Test', visible=True)

        rsp = self.api_get(get_repository_list_url(),
                           data={'show-invisible': True},
                           expected_mimetype=repository_list_mimetype)
        assert rsp is not None
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['repositories']), 2)
        self.assertEqual(rsp['repositories'][0]['name'], 'test1')
        self.assertEqual(rsp['repositories'][1]['name'], 'test2')

    @webapi_test_template
    def test_get_repositories_with_name(self) -> None:
        """Testing the GET <URL>?name= API"""
        self.create_repository(name='test1', tool_name='Test')
        self.create_repository(name='test2', tool_name='Test')

        rsp = self.api_get(get_repository_list_url() + '?name=test1',
                           expected_mimetype=repository_list_mimetype)
        assert rsp is not None
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['repositories']), 1)
        self.assertEqual(rsp['repositories'][0]['name'], 'test1')

    @webapi_test_template
    def test_get_repositories_with_name_search(self) -> None:
        """Testing the GET <URL>?q= API"""
        self.create_repository(name='test1', tool_name='Test')
        self.create_repository(name='tset2', tool_name='Test')

        rsp = self.api_get(get_repository_list_url() + '?q=te',
                           expected_mimetype=repository_list_mimetype)
        assert rsp is not None
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['repositories']), 1)
        self.assertEqual(rsp['repositories'][0]['name'], 'test1')

    @webapi_test_template
    def test_get_repositories_with_name_many(self) -> None:
        """Testing the GET <URL>?name= API and comma-separated list"""
        self.create_repository(name='test1', tool_name='Test')
        self.create_repository(name='test2', tool_name='Test')
        self.create_repository(name='test3', tool_name='Test')

        rsp = self.api_get(get_repository_list_url() + '?name=test1,test2',
                           expected_mimetype=repository_list_mimetype)
        assert rsp is not None
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['repositories']), 2)
        self.assertEqual(rsp['repositories'][0]['name'], 'test1')
        self.assertEqual(rsp['repositories'][1]['name'], 'test2')

    @webapi_test_template
    def test_get_repositories_with_path(self) -> None:
        """Testing the GET <URL>?path= API"""
        self.create_repository(name='test1', path='dummy1', tool_name='Test')
        self.create_repository(name='test2', path='dummy2', tool_name='Test')

        rsp = self.api_get(get_repository_list_url() + '?path=dummy1',
                           expected_mimetype=repository_list_mimetype)
        assert rsp is not None
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['repositories']), 1)
        self.assertEqual(rsp['repositories'][0]['name'], 'test1')

    @webapi_test_template
    def test_get_repositories_with_path_many(self) -> None:
        """Testing the GET <URL>?path= API and comma-separated lists"""
        self.create_repository(name='test1', path='dummy1', tool_name='Test')
        self.create_repository(name='test2', path='dummy2', tool_name='Test')
        self.create_repository(name='test3', path='dummy3', tool_name='Test')

        rsp = self.api_get(get_repository_list_url() + '?path=dummy1,dummy2',
                           expected_mimetype=repository_list_mimetype)
        assert rsp is not None
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['repositories']), 2)
        self.assertEqual(rsp['repositories'][0]['name'], 'test1')
        self.assertEqual(rsp['repositories'][1]['name'], 'test2')

    @webapi_test_template
    def test_get_repositories_with_name_or_path(self) -> None:
        """Testing the GET <URL>?name-or-path= API"""
        self.create_repository(name='test1', path='dummy1', tool_name='Test')
        self.create_repository(name='test2', path='dummy2', tool_name='Test')
        self.create_repository(name='test3', path='dummy3', tool_name='Test')

        rsp = self.api_get(get_repository_list_url() + '?name-or-path=test1',
                           expected_mimetype=repository_list_mimetype)
        assert rsp is not None
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['repositories']), 1)
        self.assertEqual(rsp['repositories'][0]['name'], 'test1')

        rsp = self.api_get(get_repository_list_url() + '?name-or-path=dummy2',
                           expected_mimetype=repository_list_mimetype)
        assert rsp is not None
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['repositories']), 1)
        self.assertEqual(rsp['repositories'][0]['name'], 'test2')

    @webapi_test_template
    def test_get_repositories_with_name_or_path_many(self) -> None:
        """Testing the GET <URL>?name-or-path= API
        and comma-separated list
        """
        self.create_repository(name='test1', path='dummy1', tool_name='Test')
        self.create_repository(name='test2', path='dummy2', tool_name='Test')
        self.create_repository(name='test3', path='dummy3', tool_name='Test')

        rsp = self.api_get(
            get_repository_list_url() + '?name-or-path=test1,dummy2',
            expected_mimetype=repository_list_mimetype)
        assert rsp is not None
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['repositories']), 2)
        self.assertEqual(rsp['repositories'][0]['name'], 'test1')
        self.assertEqual(rsp['repositories'][1]['name'], 'test2')

    @webapi_test_template
    def test_get_repositories_with_tool_name(self) -> None:
        """Testing the GET <URL>?tool= API with tool names"""
        self.create_repository(name='test1', path='dummy1', tool_name='Git')
        self.create_repository(name='test2', path='dummy2', tool_name='Test')

        rsp = self.api_get(get_repository_list_url() + '?tool=Git',
                           expected_mimetype=repository_list_mimetype)
        assert rsp is not None
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['repositories']), 1)
        self.assertEqual(rsp['repositories'][0]['name'], 'test1')

    @webapi_test_template
    def test_get_repositories_with_tool_many_names(self) -> None:
        """Testing the GET <URL>?tool= API with tool names in a
        comma-separated list
        """
        self.create_repository(name='test1', path='dummy1', tool_name='Git')
        self.create_repository(name='test2', path='dummy2', tool_name='Test')
        self.create_repository(name='test3', path='dummy3',
                               tool_name='Subversion')

        rsp = self.api_get(get_repository_list_url() + '?tool=Git,Subversion',
                           expected_mimetype=repository_list_mimetype)
        assert rsp is not None
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['repositories']), 2)
        self.assertEqual(rsp['repositories'][0]['name'], 'test1')
        self.assertEqual(rsp['repositories'][1]['name'], 'test3')

    @webapi_test_template
    def test_get_repositories_with_tool_missing_name(self) -> None:
        """Testing the GET <URL>?tool= API with unknown tool name/ID"""
        # This was previously crashing due to the tool registry lookup
        # returning None.
        rsp = self.api_get(get_repository_list_url() + '?tool=unknown',
                           expected_mimetype=repository_list_mimetype)
        assert rsp is not None
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['repositories']), 0)

    @webapi_test_template
    def test_get_repositories_with_tool_id(self) -> None:
        """Testing the GET <URL>?tool= API with tool IDs."""
        self.create_repository(name='test1', path='dummy1', tool_name='Git')
        self.create_repository(name='test2', path='dummy2', tool_name='Test')

        rsp = self.api_get(get_repository_list_url() + '?tool=git',
                           expected_mimetype=repository_list_mimetype)
        assert rsp is not None
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['repositories']), 1)
        self.assertEqual(rsp['repositories'][0]['name'], 'test1')

    @webapi_test_template
    def test_get_repositories_with_tool_many_ids(self) -> None:
        """Testing the GET <URL>?tool= API with tool IDs in a
        comma-separated list
        """
        self.create_repository(name='test1', path='dummy1', tool_name='Git')
        self.create_repository(name='test2', path='dummy2', tool_name='Test')
        self.create_repository(name='test3', path='dummy3',
                               tool_name='Subversion')

        rsp = self.api_get(get_repository_list_url() + '?tool=git,subversion',
                           expected_mimetype=repository_list_mimetype)
        assert rsp is not None
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['repositories']), 2)
        self.assertEqual(rsp['repositories'][0]['name'], 'test1')
        self.assertEqual(rsp['repositories'][1]['name'], 'test3')

    @webapi_test_template
    def test_get_repositories_with_hosting_service(self) -> None:
        """Testing the GET <URL>?hosting-service= API"""
        hosting_account = HostingServiceAccount.objects.create(
            service_name='github',
            username='my-username')

        self.create_repository(
            name='My New Repository',
            path='https://example.com',
            tool_name='Git',
            hosting_account=hosting_account)

        rsp = self.api_get(
            get_repository_list_url() + '?hosting-service=github',
            expected_mimetype=repository_list_mimetype)
        assert rsp is not None
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['repositories']), 1)
        self.assertEqual(rsp['repositories'][0]['name'],
                         'My New Repository')

    @webapi_test_template
    def test_get_repositories_with_hosting_service_many(self) -> None:
        """Testing the GET <URL>?hosting-service= API and comma-separated list
        """
        hosting_account = HostingServiceAccount.objects.create(
            service_name='github',
            username='my-username')

        self.create_repository(
            name='My New Repository 1',
            path='https://example.com',
            tool_name='Git',
            hosting_account=hosting_account)

        hosting_account = HostingServiceAccount.objects.create(
            service_name='beanstalk',
            username='my-username')

        self.create_repository(
            name='My New Repository 2',
            path='https://example.com',
            tool_name='Subversion',
            hosting_account=hosting_account)

        rsp = self.api_get(
            get_repository_list_url() + '?hosting-service=github,beanstalk',
            expected_mimetype=repository_list_mimetype)
        assert rsp is not None
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['repositories']), 2)
        self.assertEqual(rsp['repositories'][0]['name'],
                         'My New Repository 1')
        self.assertEqual(rsp['repositories'][1]['name'],
                         'My New Repository 2')

    @webapi_test_template
    def test_get_repositories_with_username(self) -> None:
        """Testing the GET <URL>?username= API"""
        hosting_account = HostingServiceAccount.objects.create(
            service_name='github',
            username='my-username')

        self.create_repository(
            name='My New Repository 1',
            path='https://example.com',
            tool_name='Git',
            hosting_account=hosting_account)

        self.create_repository(
            name='My New Repository 2',
            path='https://example.com',
            username='my-username',
            tool_name='Subversion')

        rsp = self.api_get(get_repository_list_url() + '?username=my-username',
                           expected_mimetype=repository_list_mimetype)
        assert rsp is not None
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['repositories']), 2)
        self.assertEqual(rsp['repositories'][0]['name'],
                         'My New Repository 1')
        self.assertEqual(rsp['repositories'][1]['name'],
                         'My New Repository 2')

    @webapi_test_template
    def test_get_repositories_with_username_many(self) -> None:
        """Testing the GET <URL>?username= API and comma-separated list"""
        hosting_account = HostingServiceAccount.objects.create(
            service_name='github',
            username='my-username')

        self.create_repository(
            name='My New Repository 1',
            path='https://example.com',
            tool_name='Git',
            hosting_account=hosting_account)

        self.create_repository(
            name='My New Repository 2',
            path='https://example.com',
            username='my-username-2',
            tool_name='Subversion')

        rsp = self.api_get(
            get_repository_list_url() + '?username=my-username,my-username-2',
            expected_mimetype=repository_list_mimetype)
        assert rsp is not None
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['repositories']), 2)
        self.assertEqual(rsp['repositories'][0]['name'],
                         'My New Repository 1')
        self.assertEqual(rsp['repositories'][1]['name'],
                         'My New Repository 2')

    #
    # HTTP POST tests
    #

    def setup_basic_post_test(
        self,
        user: User,
        with_local_site: bool,
        local_site_name: Optional[str],
        post_valid_data: bool,
    ) -> tuple[str, str, dict[str, Any], Sequence[Any]]:
        """Set up a basic HTTP POST test.

        Args:
            user (django.contrib.auth.models.User):
                The user performing the API requests.

            with_local_site (bool):
                Whether the test is being performed on a Local Site.

            local_site_name (str):
                The name of the Local Site to test against.

            post_valid_data (bool):
                Whether to post valid data or not.

        Returns:
            tuple:
            A 4-tuple of:

            Tuple:
                0 (str):
                    The URL of the API resource to access.

                1 (str):
                    The expected mimetype of the response.

                2 (dict):
                    The data to send in the POST request.

                3 (list):
                    Additional positional arguments to pass to
                    :py:meth:`check_post_result`.
        """
        return (
            get_repository_list_url(local_site_name),
            repository_item_mimetype,
            {
                'name': 'Test Repository',
                'path': self.sample_repo_path,
                'raw_file_url': 'http://example.com/<filename>/<version>',
                'tool': 'Test',
            },
            [])

    def check_post_result(
        self,
        user: User,
        rsp: JSONDict,
    ) -> None:
        """Check the result of a POST operation.

        Args:
            user (django.contrib.auth.models.User):
                The user performing the API requests.

            rsp (dict):
                The response from the API resource.
        """
        self._verify_repository_info(
            rsp=rsp,
            expected_tool_id='test',
            expected_attrs={
                'name': 'Test Repository',
                'path': self.sample_repo_path,
            })

    @webapi_test_template
    def test_post_with_hosting_service(self) -> None:
        """Testing the POST <URL> API with hosting service"""
        account = HostingServiceAccount.objects.create(
            username='test-user',
            service_name='github')

        self.spy_on(GitHub.is_authorized,
                    owner=GitHub,
                    op=kgb.SpyOpReturn(True))
        self.spy_on(GitHub.check_repository,
                    owner=GitHub,
                    call_original=False)

        rsp = self._post_repository({
            'github_public_org_name': 'myorg',
            'github_public_org_repo_name': 'myrepo',
            'hosting_account_username': 'test-user',
            'hosting_type': 'github',
            'name': 'Test Repository',
            'repository_plan': 'public-org',
            'tool': 'Git',
        })
        assert rsp is not None

        self._verify_repository_info(
            rsp=rsp,
            expected_tool_id='git',
            expected_attrs={
                'hosting_account': account,
                'extra_data': {
                    'bug_tracker_use_hosting': False,
                    'github_public_org_name': 'myorg',
                    'github_public_org_repo_name': 'myrepo',
                    'repository_plan': 'public-org',
                },
                'mirror_path': 'git@github.com:myorg/myrepo.git',
                'path': 'git://github.com/myorg/myrepo.git',
            })

        self.assertSpyCalled(GitHub.is_authorized)
        self.assertSpyCalled(GitHub.check_repository)

    @webapi_test_template
    def test_post_with_hosting_service_and_hosting_url(self) -> None:
        """Testing the POST <URL> API with hosting service and hosting_url"""
        account = HostingServiceAccount.objects.create(
            hosting_url='https://example.com',
            username='test-user',
            service_name='gitlab')

        self.spy_on(GitLab.is_authorized,
                    owner=GitLab,
                    op=kgb.SpyOpReturn(True))
        self.spy_on(GitLab.check_repository,
                    owner=GitLab,
                    call_original=False)

        rsp = self._post_repository({
            'gitlab_personal_repo_name': 'myrepo',
            'hosting_account_username': 'test-user',
            'hosting_type': 'gitlab',
            'hosting_url': 'https://example.com',
            'repository_plan': 'personal',
            'tool': 'Git',
        })
        assert rsp is not None

        self._verify_repository_info(
            rsp=rsp,
            expected_tool_id='git',
            expected_attrs={
                'extra_data': {
                    'bug_tracker_use_hosting': False,
                    'gitlab_personal_repo_name': 'myrepo',
                    'hosting_url': 'https://example.com',
                    'repository_plan': 'personal',
                },
                'hosting_account': account,
                'mirror_path': 'https://example.com/test-user/myrepo.git',
                'path': 'git@example.com:test-user/myrepo.git',
            })

        self.assertSpyCalled(GitLab.is_authorized)
        self.assertSpyCalled(GitLab.check_repository)

    @webapi_test_template
    def test_post_with_hosting_service_and_bug_tracker_use_hosting(
        self,
    ) -> None:
        """Testing the POST <URL> API with hosting service and
        bug_tracker_use_hosting
        """
        account = HostingServiceAccount.objects.create(
            username='test-user',
            service_name='github')

        self.spy_on(GitHub.is_authorized,
                    owner=GitHub,
                    op=kgb.SpyOpReturn(True))
        self.spy_on(GitHub.check_repository,
                    owner=GitHub,
                    call_original=False)

        rsp = self._post_repository({
            'bug_tracker_use_hosting': True,
            'github_public_org_name': 'myorg',
            'github_public_org_repo_name': 'myrepo',
            'hosting_account_username': 'test-user',
            'hosting_type': 'github',
            'repository_plan': 'public-org',
            'tool': 'Git',
        })
        assert rsp is not None

        self._verify_repository_info(
            rsp=rsp,
            expected_tool_id='git',
            expected_attrs={
                'bug_tracker':
                    'http://github.com/myorg/myrepo/issues#issue/%s',
                'extra_data': {
                    'bug_tracker_use_hosting': True,
                    'github_public_org_name': 'myorg',
                    'github_public_org_repo_name': 'myrepo',
                    'repository_plan': 'public-org',
                },
                'hosting_account': account,
                'mirror_path': 'git@github.com:myorg/myrepo.git',
                'path': 'git://github.com/myorg/myrepo.git',
            })

        self.assertSpyCalled(GitHub.is_authorized)
        self.assertSpyCalled(GitHub.check_repository)

    @webapi_test_template
    def test_post_with_hosting_service_and_invalid_username(self) -> None:
        """Testing the POST <URL> API with hosting service and invalid
        hosting_account_username
        """
        self.spy_on(GitHub.is_authorized,
                    owner=GitHub,
                    op=kgb.SpyOpReturn(True))
        self.spy_on(GitHub.check_repository,
                    owner=GitHub,
                    call_original=False)

        rsp = self._post_repository(
            {
                'bug_tracker_use_hosting': True,
                'github_public_org_name': 'myorg',
                'github_public_org_repo_name': 'myrepo',
                'hosting_account_username': 'test-user',
                'hosting_type': 'github',
                'repository_plan': 'public-org',
                'tool': 'Git',
            },
            expected_status=400)
        assert rsp is not None

        self.assertEqual(rsp, {
            'err': {
                'code': INVALID_FORM_DATA.code,
                'msg': INVALID_FORM_DATA.msg,
                'type': INVALID_FORM_DATA.error_type,
            },
            'fields': {
                'hosting_account_username': [
                    'An existing hosting service account with the username '
                    '"test-user" could not be found for the hosting '
                    'service "github".'
                ],
            },
            'stat': 'fail',
        })

        self.assertSpyNotCalled(GitHub.is_authorized)
        self.assertSpyNotCalled(GitHub.check_repository)

    @webapi_test_template
    def test_post_with_hosting_service_and_bug_tracker_type(self) -> None:
        """Testing the POST <URL> API with hosting service and bug_tracker_type
        """
        rsp = self._post_repository({
            'bug_tracker_type': 'github',
            'bug_tracker-github_public_org_name': 'myorg',
            'bug_tracker-github_public_org_repo_name': 'myrepo',
            'hosting_account_username': 'test-user',
            'bug_tracker_plan': 'public-org',
            'tool': 'Git',
        })
        assert rsp is not None

        self._verify_repository_info(
            rsp=rsp,
            expected_tool_id='git',
            expected_attrs={
                'bug_tracker':
                    'http://github.com/myorg/myrepo/issues#issue/%s',
                'extra_data': {
                    'bug_tracker_plan': 'public-org',
                    'bug_tracker_type': 'github',
                    'bug_tracker-github_public_org_name': 'myorg',
                    'bug_tracker-github_public_org_repo_name': 'myrepo',
                },
            })

    @webapi_test_template
    def test_post_with_visible_False(self) -> None:
        """Testing the POST <URL> API with visible=False"""
        rsp = self._post_repository({
            'visible': False,
        })
        assert rsp is not None

        self._verify_repository_info(
            rsp=rsp,
            expected_attrs={
                'visible': False,
            })

    @webapi_test_template
    def test_post_with_bad_host_key(self) -> None:
        """Testing the POST <URL> API with Bad Host Key error"""
        self.spy_on(TestTool.check_repository,
                    owner=TestTool,
                    op=kgb.SpyOpRaise(BadHostKeyError('example.com', key1,
                                                      key2)))

        rsp = self._post_repository(expected_status=403)
        assert rsp is not None

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], BAD_HOST_KEY.code)
        self.assertIn('hostname', rsp)
        self.assertIn('expected_key', rsp)
        self.assertIn('key', rsp)
        self.assertEqual(rsp['hostname'], 'example.com')
        self.assertEqual(rsp['expected_key'], key2.get_base64())
        self.assertEqual(rsp['key'], key1.get_base64())

    @webapi_test_template
    def test_post_with_bad_host_key_and_trust_host(self) -> None:
        """Testing the POST <URL> API with Bad Host Key error and trust_host=1
        """
        self.spy_on(SSHClient.replace_host_key,
                    owner=SSHClient,
                    call_original=False)

        @self.spy_for(TestTool.check_repository, owner=TestTool)
        def _check_repository(cls, *args, **kwargs) -> None:
            if not SSHClient.replace_host_key.called:
                raise BadHostKeyError('example.com', key1, key2)

        self._post_repository({
            'trust_host': 1,
        })

        self.assertSpyCalledWith(SSHClient.replace_host_key,
                                 'example.com', key2, key1)

    @webapi_test_template
    def test_post_with_unknown_host_key(self) -> None:
        """Testing the POST <URL> API with Unknown Host Key error"""
        self.spy_on(TestTool.check_repository,
                    owner=TestTool,
                    op=kgb.SpyOpRaise(UnknownHostKeyError('example.com',
                                                          key1)))

        rsp = self._post_repository(expected_status=403)
        assert rsp is not None

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], UNVERIFIED_HOST_KEY.code)
        self.assertIn('hostname', rsp)
        self.assertIn('key', rsp)
        self.assertEqual(rsp['hostname'], 'example.com')
        self.assertEqual(rsp['key'], key1.get_base64())

    @webapi_test_template
    def test_post_with_unknown_host_key_and_trust_host(self) -> None:
        """Testing the POST <URL> API with Unknown Host Key error
        and trust_host=1
        """
        self.spy_on(SSHClient.add_host_key,
                    owner=SSHClient,
                    call_original=False)

        @self.spy_for(TestTool.check_repository, owner=TestTool)
        def _check_repository(cls, *args, **kwargs):
            if not SSHClient.add_host_key.called:
                raise UnknownHostKeyError('example.com', key1)

        self._post_repository({
            'trust_host': 1,
        })

        self.assertSpyCalledWith(SSHClient.add_host_key,
                                 'example.com', key1)
        self.assertSpyCalled(TestTool.check_repository)

    @webapi_test_template
    def test_post_with_unknown_cert(self) -> None:
        """Testing the POST <URL> API with Unknown Certificate error"""
        class Certificate(object):
            failures = ['failures']
            fingerprint = 'fingerprint'
            hostname = 'example.com'
            issuer = 'issuer'
            valid_from = 'valid_from'
            valid_until = 'valid_until'

        cert = Certificate()

        self.spy_on(TestTool.check_repository,
                    owner=TestTool,
                    op=kgb.SpyOpRaise(UnverifiedCertificateError(cert)))

        rsp = self._post_repository(expected_status=403)
        assert rsp is not None

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], UNVERIFIED_HOST_CERT.code)
        self.assertIn('certificate', rsp)
        self.assertEqual(rsp['certificate']['failures'], cert.failures)
        self.assertEqual(rsp['certificate']['fingerprint'], cert.fingerprint)
        self.assertEqual(rsp['certificate']['hostname'], cert.hostname)
        self.assertEqual(rsp['certificate']['issuer'], cert.issuer)
        self.assertEqual(rsp['certificate']['valid']['from'], cert.valid_from)
        self.assertEqual(rsp['certificate']['valid']['until'],
                         cert.valid_until)

    @webapi_test_template
    def test_post_with_unknown_cert_and_trust_host(self) -> None:
        """Testing the POST <URL> API with Unknown Certificate error
        and trust_host=1
        """
        class Certificate(object):
            failures = ['failures']
            fingerprint = 'fingerprint'
            hostname = 'example.com'
            issuer = 'issuer'
            valid_from = 'valid_from'
            valid_until = 'valid_until'

        cert = Certificate()

        @self.spy_for(TestTool.check_repository, owner=TestTool)
        def _check_repository(cls, *args, **kwargs) -> None:
            if not TestTool.accept_certificate.called:
                raise UnverifiedCertificateError(cert)

        self.spy_on(
            TestTool.accept_certificate,
            owner=TestTool,
            op=kgb.SpyOpReturn({
                'fingerprint': '123',
            }))

        rsp = self._post_repository({
            'trust_host': 1,
        })
        assert rsp is not None

        self._verify_repository_info(
            rsp=rsp,
            expected_attrs={
                'extra_data': {
                    'cert': {
                        'fingerprint': '123',
                    },
                },
            })

        self.assertSpyCalled(TestTool.accept_certificate)

    @webapi_test_template
    def test_post_with_missing_user_key(self) -> None:
        """Testing the POST <URL> API with Missing User Key error"""
        self.spy_on(
            TestTool.check_repository,
            owner=TestTool,
            op=kgb.SpyOpRaise(AuthenticationError(allowed_types=['publickey'],
                                                  user_key=None)))

        rsp = self._post_repository(expected_status=403)
        assert rsp is not None

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], MISSING_USER_KEY.code)

    @webapi_test_template
    def test_post_with_authentication_error(self) -> None:
        """Testing the POST <URL> API with Authentication Error"""
        self.spy_on(
            TestTool.check_repository,
            owner=TestTool,
            op=kgb.SpyOpRaise(AuthenticationError()))

        rsp = self._post_repository(expected_status=403)
        assert rsp is not None

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], REPO_AUTHENTICATION_ERROR.code)
        self.assertIn('reason', rsp)

    @webapi_test_template
    def test_post_full_info(self) -> None:
        """Testing the POST <URL> API with all available info"""
        rsp = self._post_repository({
            'bug_tracker': 'http://bugtracker/%s/',
            'encoding': 'UTF-8',
            'mirror_path': 'http://svn.example.com/',
            'password': '123',
            'public': False,
            'raw_file_url': 'http://example.com/<filename>/<version>',
            'tool': 'Subversion',
            'username': 'user',
        })
        assert rsp is not None

        self._verify_repository_info(
            rsp=rsp,
            expected_tool_id='subversion',
            expected_attrs={
                'bug_tracker': 'http://bugtracker/%s/',
                'encoding': 'UTF-8',
                'mirror_path': 'http://svn.example.com/',
                'password': '123',
                'public': False,
                'username': 'user',

                # raw_file_url will be cleared out, since it's not available
                # for Subversion repositories.
                'raw_file_url': '',
            })

    @webapi_test_template
    def test_post_with_no_access(self) -> None:
        """Testing the POST <URL> API with no access"""
        self._post_repository(use_admin=False,
                              expected_status=403)

    @webapi_test_template
    def test_post_duplicate(self) -> None:
        """Testing the POST <URL> API with a duplicate repository"""
        self._post_repository()
        self._post_repository(expected_status=409)

    @webapi_test_template
    def _post_repository(
        self,
        data: Optional[dict[str, Any]] = None,
        use_local_site: bool = False,
        use_admin: bool = True,
        expected_status: int = 201,
    ) -> JSONDict:
        """Create a repository via the API.

        This will build and send an API request to create a repository,
        returning the resulting payload.

        By default, the form data will set the ``name``, ``path``, and
        ``tool`` to default values. These can be overridden by the caller to
        other values.

        Args:
            data (dict, optional):
                Form data to send in the request.

            use_local_site (bool, optional):
                Whether to test this against a repository owned by a
                Local Site.

            use_admin (bool, optional):
                Whether to use an administrator account to perform the
                request.

            expected_status (int, optional):
                The expected HTTP status code for the operation.

        Returns:
            dict:
            The response payload.
        """
        repo_name = 'Test Repository'

        if 200 <= expected_status < 300:
            expected_mimetype = repository_item_mimetype
        else:
            expected_mimetype = None

        if use_local_site:
            local_site_name = self.local_site_name
        else:
            local_site_name = None

        # Build the payload that we'll sent to the API.
        post_data = {
            'name': repo_name,
            'tool': 'Test',
        }

        if data is None:
            data = {}

        if 'hosting_type' not in data:
            post_data['path'] = self.sample_repo_path
            post_data['raw_file_url'] = 'http://example.com/<version>'

        post_data.update(data)

        # Make the request to the API.
        if use_admin:
            self._login_user(local_site=use_local_site,
                             admin=True)

        return self.api_post(
            get_repository_list_url(local_site_name),
            post_data,
            expected_status=expected_status,
            expected_mimetype=expected_mimetype)


class ResourceItemTests(ExtraDataItemMixin, BaseRepositoryTests,
                        metaclass=BasicTestsMetaclass):
    """Testing the RepositoryResource item APIs."""

    sample_api_url = 'repositories/<id>/'
    fixtures = ['test_users', 'test_scmtools']
    test_http_methods = ('GET', 'PUT')
    resource = resources.repository
    basic_put_use_admin = True

    compare_item = BaseRepositoryTests.compare_item

    #
    # HTTP DELETE tests
    #

    @webapi_test_template
    def test_delete(self) -> None:
        """Testing the DELETE <URL> API"""
        repo_id = self._delete_repository(with_review_request=True)

        repo = Repository.objects.get(pk=repo_id)
        self.assertTrue(repo.archived)

    @webapi_test_template
    def test_delete_empty_repository(self) -> None:
        """Testing the DELETE <URL> API with no review requests"""
        repo_id = self._delete_repository()

        self.assertFalse(Repository.objects.filter(pk=repo_id).exists())

    @add_fixtures(['test_site'])
    @webapi_test_template
    def test_delete_with_site(self) -> None:
        """Testing the DELETE <URL> API with a local site"""
        repo_id = self._delete_repository(use_local_site=True,
                                          with_review_request=True)

        repo = Repository.objects.get(pk=repo_id)
        self.assertTrue(repo.archived)

    @add_fixtures(['test_site'])
    @webapi_test_template
    def test_delete_empty_repository_with_site(self) -> None:
        """Testing the DELETE <URL> API with a local site and
        no review requests
        """
        repo_id = self._delete_repository(use_local_site=True)

        self.assertFalse(Repository.objects.filter(pk=repo_id).exists())

    @webapi_test_template
    def test_delete_with_no_access(self) -> None:
        """Testing the DELETE <URL> API with no access"""
        self._delete_repository(use_admin=False,
                                expected_status=403)

    @webapi_test_template
    @add_fixtures(['test_site'])
    def test_delete_with_site_no_access(self) -> None:
        """Testing the DELETE <URL> API with a local site and no access"""
        self._delete_repository(use_local_site=True,
                                use_admin=False,
                                expected_status=403)

    #
    # HTTP GET tests
    #

    def setup_basic_get_test(
        self,
        user: User,
        with_local_site: bool,
        local_site_name: Optional[str],
    ) -> tuple[str, str, Repository]:
        """Set up a basic HTTP GET test.

        Args:
            user (django.contrib.auth.models.User):
                The user performing the API requests.

            with_local_site (bool):
                Whether the test is being performed on a Local Site.

            local_site_name (str):
                The name of the local site to test against.

        Returns:
            tuple:
            A 3-tuple of:

            Tuple:
                0 (str):
                    The URL of the API resource to access.

                1 (str):
                    The expected mimetype of the response.

                2 (reviewboard.scmtools.models.Repository):
                    The repository to pass in to :py:meth:`compare_item`.
        """
        repository = self.create_repository(with_local_site=with_local_site)

        return (get_repository_item_url(repository, local_site_name),
                repository_item_mimetype,
                repository)

    #
    # HTTP PUT tests
    #

    def setup_basic_put_test(
        self,
        user: User,
        with_local_site: bool,
        local_site_name: Optional[str],
        put_valid_data: bool,
    ) -> tuple[str, str, dict[str, Any], Repository, Sequence[Any]]:
        """Set up a basic HTTP PUT test.

        Args:
            user (django.contrib.auth.models.User):
                The user performing the API requests.

            with_local_site (bool):
                Whether the test is being performed on a Local Site.

            local_site_name (str):
                The name of the Local Site to test against.

            put_valid_data (bool):
                Whether to return valid data for the test.

        Returns:
            tuple:
            A 4-tuple of:

            Tuple:
                0 (str):
                    The URL to the API resource to access.

                1 (str):
                    The expected mimetype of the response.

                2 (dict):
                    The data to send in the PUT request.

                3 (reviewboard.scmtools.models.Repository):
                    The repository object to pass to :py:meth:`compare_item`.

                4 (list):
                    Additional positional arguments to pass to
                    :py:meth:`check_put_result`.
        """
        repository = self.create_repository(
            with_local_site=with_local_site,
            tool_name='Git',
            path=self.sample_repo_path,
            mirror_path='git@localhost:test.git',
            raw_file_url='http://example.org/<filename>/<version>')

        return (
            get_repository_item_url(repository, local_site_name),
            repository_item_mimetype,
            {
                'bug_tracker': 'http://bugtracker/%s/',
                'encoding': 'UTF-8',
                'name': 'New Test Repository',
                'username': 'user',
                'password': '123',
                'public': False,
                'raw_file_url': 'http://example.com/<filename>/<version>',
            },
            repository,
            [])

    def check_put_result(
        self,
        user: User,
        item_rsp: JSONDict,
        repository: Repository,
        *args,
    ) -> None:
        """Check the result of an HTTP PUT test.

        Args:
            user (django.contrib.auth.models.User):
                The user performing the API requests.

            item_rsp (dict):
                The data returned from the API endpoint.

            repository (reviewboard.scmtools.models.Repository):
                The repository item to check against.

            *args (tuple, unused):
                Additional positional arguments.
        """
        repository.refresh_from_db()

        self.assertEqual(repository.raw_file_url,
                         'http://example.com/<filename>/<version>')
        self.assertEqual(repository.get_credentials(), {
            'username': 'user',
            'password': '123',
        })

        self.compare_item(item_rsp, repository)

    @webapi_test_template
    def test_put_with_archive(self) -> None:
        """Testing the PUT <URL> API with archive_name=True"""
        rsp = self._put_repository(data={
            'archive_name': '1',
        })
        assert rsp is not None

        repository = self._verify_repository_info(
            rsp=rsp,
            expected_attrs={
                'archived': True,
                'public': False,
            })
        self.assertTrue(repository.name.startswith('ar:New Test Repository:'))
        self.assertIsNotNone(repository.archived_timestamp)

    @webapi_test_template
    def test_put_with_archive_and_bad_host_key(self) -> None:
        """Testing the PUT <URL> API with archive_name=True and a repository
        with a bad host key
        """
        repository = self.create_repository(tool_name='Test',
                                            name='Test repo')
        self.spy_on(TestTool.check_repository,
                    owner=TestTool,
                    op=kgb.SpyOpRaise(BadHostKeyError('example.com', key1,
                                                      key2)))

        rsp = self._put_repository(
            repository=repository,
            data={'archive_name': '1'},
            send_name=False)
        assert rsp is not None

        repository = self._verify_repository_info(
            rsp=rsp,
            expected_attrs={
                'archived': True,
                'public': False,
            })
        self.assertTrue(repository.name.startswith('ar:Test repo'))
        self.assertIsNotNone(repository.archived_timestamp)

    @webapi_test_template
    def test_put_with_hosting_service(self) -> None:
        """Testing the PUT <URL> API with hosting service"""
        old_account = HostingServiceAccount.objects.create(
            username='test-user',
            service_name='github')
        new_account = HostingServiceAccount.objects.create(
            username='new-user',
            service_name='bitbucket')

        repository = self.create_repository(
            hosting_account=old_account,
            extra_data={
                'bug_tracker_use_hosting': False,
                'github_public_org_name': 'myorg',
                'github_public_org_repo_name': 'myrepo',
                'repository_plan': 'public-org',
            })

        self.spy_on(Bitbucket.is_authorized,
                    owner=Bitbucket,
                    op=kgb.SpyOpReturn(True))
        self.spy_on(Bitbucket.check_repository,
                    owner=Bitbucket,
                    call_original=False)

        rsp = self._put_repository(
            repository=repository,
            data={
                'bitbucket_team_name': 'my-team',
                'bitbucket_team_repo_name': 'new-repo',
                'bug_tracker_use_hosting': True,
                'hosting_account_username': 'new-user',
                'hosting_type': 'bitbucket',
                'name': 'New Repository',
                'repository_plan': 'team',
                'tool': 'Git',
            })
        assert rsp is not None

        self._verify_repository_info(
            rsp=rsp,
            expected_tool_id='git',
            expected_attrs={
                'bug_tracker':
                    'https://bitbucket.org/my-team/new-repo/issue/%s/',
                'extra_data': {
                    'bitbucket_team_name': 'my-team',
                    'bitbucket_team_repo_name': 'new-repo',
                    'bug_tracker_use_hosting': True,
                    'repository_plan': 'team',
                },
                'hosting_account': new_account,
                'mirror_path':
                    'https://new-user@bitbucket.org/my-team/new-repo.git',
                'name': 'New Repository',
                'path': 'git@bitbucket.org:my-team/new-repo.git',
            })

        self.assertSpyCalled(Bitbucket.is_authorized)
        self.assertSpyCalled(Bitbucket.check_repository)

    @webapi_test_template
    def test_put_with_hosting_service_and_hosting_url(self) -> None:
        """Testing the PUT <URL> API with hosting service"""
        old_account = HostingServiceAccount.objects.create(
            username='test-user',
            service_name='github')
        new_account = HostingServiceAccount.objects.create(
            hosting_url='https://example.com',
            username='new-user',
            service_name='gitlab')

        repository = self.create_repository(
            hosting_account=old_account,
            bug_tracker='https://bugs.example.com/%s',
            extra_data={
                'bug_tracker_use_hosting': False,
                'github_public_org_name': 'myorg',
                'github_public_org_repo_name': 'myrepo',
                'repository_plan': 'public-org',
            })

        self.spy_on(GitLab.is_authorized,
                    owner=GitLab,
                    op=kgb.SpyOpReturn(True))
        self.spy_on(GitLab.check_repository,
                    owner=GitLab,
                    call_original=False)

        rsp = self._put_repository(
            repository=repository,
            data={
                'gitlab_personal_repo_name': 'new-repo',
                'hosting_account_username': 'new-user',
                'hosting_type': 'gitlab',
                'hosting_url': 'https://example.com',
                'name': 'New Repository',
                'repository_plan': 'personal',
                'tool': 'Git',
            })
        assert rsp is not None

        self._verify_repository_info(
            rsp=rsp,
            expected_tool_id='git',
            expected_attrs={
                'bug_tracker': 'https://bugs.example.com/%s',
                'extra_data': {
                    'gitlab_personal_repo_name': 'new-repo',
                    'hosting_url': 'https://example.com',
                    'bug_tracker_use_hosting': False,
                    'repository_plan': 'personal',
                },
                'hosting_account': new_account,
                'name': 'New Repository',
                'mirror_path': 'https://example.com/new-user/new-repo.git',
                'path': 'git@example.com:new-user/new-repo.git',
            })

        self.assertSpyCalled(GitLab.is_authorized)
        self.assertSpyCalled(GitLab.check_repository)

    @webapi_test_template
    def test_put_with_unsetting_hosting_service(self) -> None:
        """Testing the PUT <URL> API with unsetting a hosting service"""
        old_account = HostingServiceAccount.objects.create(
            username='test-user',
            service_name='github')

        repository = self.create_repository(
            hosting_account=old_account,
            extra_data={
                'bug_tracker_use_hosting': False,
                'github_public_org_name': 'myorg',
                'github_public_org_repo_name': 'myrepo',
                'repository_plan': 'public-org',
            })

        rsp = self._put_repository(
            repository=repository,
            data={
                'hosting_type': 'custom',
                'name': 'New Repository',
                'tool': 'Git',
                'path': self.sample_repo_path,
                'raw_file_url': 'http://example.com/<filename>/<version>',
            })
        assert rsp is not None

        self._verify_repository_info(
            rsp=rsp,
            expected_tool_id='git',
            expected_attrs={
                'extra_data': {},
                'hosting_account': None,
                'mirror_path': '',
                'name': 'New Repository',
                'path': self.sample_repo_path,
                'raw_file_url': 'http://example.com/<filename>/<version>',
            })

    @webapi_test_template
    def test_put_with_bug_tracker_type(self) -> None:
        """Testing the PUT <URL> API with bug_tracker_type"""
        repository = self.create_repository(
            bug_tracker='https://bugs.example.com/%s')

        rsp = self._put_repository(
            repository=repository,
            data={
                'bug_tracker_type': 'github',
                'bug_tracker-github_public_org_name': 'myorg',
                'bug_tracker-github_public_org_repo_name': 'myrepo',
                'bug_tracker_plan': 'public-org',
                'tool': 'Git',
            })
        assert rsp is not None

        self._verify_repository_info(
            rsp=rsp,
            expected_tool_id='git',
            expected_attrs={
                'bug_tracker':
                    'http://github.com/myorg/myrepo/issues#issue/%s',
                'extra_data': {
                    'bug_tracker_plan': 'public-org',
                    'bug_tracker_type': 'github',
                    'bug_tracker-github_public_org_name': 'myorg',
                    'bug_tracker-github_public_org_repo_name': 'myrepo',
                },
            })

    def _put_repository(
        self,
        *,
        data: Optional[dict[str, Any]] = None,
        use_local_site: bool = False,
        use_admin: bool = True,
        repository: Optional[Repository] = None,
        expected_status: int = 200,
        send_name: bool = True,
    ) -> Optional[dict[str, Any]]:
        """Modify a repository via the API.

        This will build and send an API request to modify a repository,
        returning the resulting payload.

        By default, the form data will set the ``name`` to a default value.
        This can be overridden by the caller to another value.

        Version Changed:
            7.1:
            * Made all arguments keyword-only.
            * Added the ``send_name`` argument.

        Args:
            data (dict, optional):
                Form data to send in the request.

            use_local_site (bool, optional):
                Whether to test this against a repository owned by a
                Local Site.

            use_admin (bool, optional):
                Whether to use an administrator account to perform the
                request.

            repository (reviewboard.scmtools.models.Repository, optional):
                An existing repository to post to. If not provided, one will
                be created.

            expected_status (int, optional):
                The expected HTTP status code for the operation.

            send_name (bool, optional):
                Whether to send the name in the payload.

                Version Added:
                    7.1

        Returns:
            dict:
            The response payload.
        """
        repo_name = 'New Test Repository'

        if repository is None:
            repository = self.create_repository(with_local_site=use_local_site)

        if use_local_site:
            local_site_name = self.local_site_name
        else:
            local_site_name = None

        if 200 <= expected_status < 300:
            expected_mimetype = repository_item_mimetype
        else:
            expected_mimetype = None

        # Make the request to the API.
        if use_admin:
            self._login_user(local_site=use_local_site,
                             admin=True)

        if data is None:
            data = {}

        if send_name and 'name' not in data:
            data['name'] = repo_name

        return self.api_put(
            get_repository_item_url(repository, local_site_name),
            data,
            expected_status=expected_status,
            expected_mimetype=expected_mimetype)

    def _delete_repository(
        self,
        use_local_site: bool = False,
        use_admin: bool = True,
        expected_status: int = 204,
        with_review_request: bool = False,
    ) -> int:
        """Delete a repository via the API.

        This will build and send an API request to delete (or archive) a
        repository, returning the initial ID of the repository.

        Args:
            use_local_site (bool, optional):
                Whether to test this against a repository owned by a
                Local Site.

            use_admin (bool, optional):
                Whether to use an administrator account to perform the
                request.

            expected_status (int, optional):
                The expected HTTP status code for the operation.

            with_review_request (bool, optional):
                Whether to create a review request against the repository
                before deleting.

        Returns:
            int:
            The initial ID of the repository.
        """
        repo = self.create_repository(with_local_site=use_local_site)

        if use_local_site:
            local_site_name = self.local_site_name
        else:
            local_site_name = None

        if with_review_request:
            assert self.user is not None
            self.create_review_request(submitter=self.user,
                                       repository=repo)

        # Make the request to the API.
        if use_admin:
            self._login_user(local_site=use_local_site,
                             admin=True)

        self.api_delete(get_repository_item_url(repo, local_site_name),
                        expected_status=expected_status)

        return repo.pk
