from __future__ import unicode_literals

import os

import kgb
import paramiko
from django.utils import six
from djblets.testing.decorators import add_fixtures
from kgb import SpyAgency

from reviewboard import scmtools
from reviewboard.hostingsvcs.models import HostingServiceAccount
from reviewboard.reviews.models import ReviewRequest
from reviewboard.scmtools.errors import (AuthenticationError,
                                         UnverifiedCertificateError)
from reviewboard.scmtools.models import Repository, Tool
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


# Only generate these keys once.
key1 = paramiko.RSAKey.generate(1024)
key2 = paramiko.RSAKey.generate(1024)


class BaseRepositoryTests(SpyAgency, BaseWebAPITestCase):
    """Base class for the RepositoryResource test suites."""

    fixtures = ['test_users', 'test_scmtools']

    sample_repo_path = (
        'file://' + os.path.abspath(
            os.path.join(os.path.dirname(scmtools.__file__), 'testdata',
                         'git_repo')))

    def compare_item(self, item_rsp, repository):
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

        self.assertEqual(
            item_rsp['links']['self']['href'],
            '%s%s' % (self.base_url,
                      get_repository_item_url(item_rsp['id'],
                                              local_site_name)))

    def _verify_repository_info(self, rsp, expected_tool_id=None,
                                expected_attrs={}):
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


@six.add_metaclass(BasicTestsMetaclass)
class ResourceListTests(ExtraDataListMixin, BaseRepositoryTests):
    """Testing the RepositoryResource list APIs."""

    sample_api_url = 'repositories/'
    resource = resources.repository
    basic_post_fixtures = ['test_scmtools']
    basic_post_use_admin = True

    compare_item = BaseRepositoryTests.compare_item

    #
    # HTTP GET tests
    #

    def setup_basic_get_test(self, user, with_local_site, local_site_name,
                             populate_items):
        if populate_items:
            items = [
                self.create_repository(
                    tool_name='Test', with_local_site=with_local_site)
            ]
        else:
            items = []

        return (get_repository_list_url(local_site_name),
                repository_list_mimetype,
                items)

    @add_fixtures(['test_site'])
    def test_get_with_show_visible(self):
        """Testing the GET repositories/ API with show_invisible=True"""
        self.create_repository(name='test1', tool_name='Test', visible=False)
        self.create_repository(name='test2', tool_name='Test', visible=True)

        rsp = self.api_get(get_repository_list_url(),
                           query={'show-invisible': True},
                           expected_mimetype=repository_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['repositories']), 2)
        self.assertEqual(rsp['repositories'][0]['name'], 'test1')
        self.assertEqual(rsp['repositories'][1]['name'], 'test2')

    def test_get_repositories_with_name(self):
        """Testing the GET repositories/?name= API"""
        self.create_repository(name='test1', tool_name='Test')
        self.create_repository(name='test2', tool_name='Test')

        rsp = self.api_get(get_repository_list_url() + '?name=test1',
                           expected_mimetype=repository_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['repositories']), 1)
        self.assertEqual(rsp['repositories'][0]['name'], 'test1')

    def test_get_repositories_with_name_many(self):
        """Testing the GET repositories/?name= API and comma-separated list"""
        self.create_repository(name='test1', tool_name='Test')
        self.create_repository(name='test2', tool_name='Test')
        self.create_repository(name='test3', tool_name='Test')

        rsp = self.api_get(get_repository_list_url() + '?name=test1,test2',
                           expected_mimetype=repository_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['repositories']), 2)
        self.assertEqual(rsp['repositories'][0]['name'], 'test1')
        self.assertEqual(rsp['repositories'][1]['name'], 'test2')

    def test_get_repositories_with_path(self):
        """Testing the GET repositories/?path= API"""
        self.create_repository(name='test1', path='dummy1', tool_name='Test')
        self.create_repository(name='test2', path='dummy2', tool_name='Test')

        rsp = self.api_get(get_repository_list_url() + '?path=dummy1',
                           expected_mimetype=repository_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['repositories']), 1)
        self.assertEqual(rsp['repositories'][0]['name'], 'test1')

    def test_get_repositories_with_path_many(self):
        """Testing the GET repositories/?path= API and comma-separated lists"""
        self.create_repository(name='test1', path='dummy1', tool_name='Test')
        self.create_repository(name='test2', path='dummy2', tool_name='Test')
        self.create_repository(name='test3', path='dummy3', tool_name='Test')

        rsp = self.api_get(get_repository_list_url() + '?path=dummy1,dummy2',
                           expected_mimetype=repository_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['repositories']), 2)
        self.assertEqual(rsp['repositories'][0]['name'], 'test1')
        self.assertEqual(rsp['repositories'][1]['name'], 'test2')

    def test_get_repositories_with_name_or_path(self):
        """Testing the GET repositories/?name-or-path= API"""
        self.create_repository(name='test1', path='dummy1', tool_name='Test')
        self.create_repository(name='test2', path='dummy2', tool_name='Test')
        self.create_repository(name='test3', path='dummy3', tool_name='Test')

        rsp = self.api_get(get_repository_list_url() + '?name-or-path=test1',
                           expected_mimetype=repository_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['repositories']), 1)
        self.assertEqual(rsp['repositories'][0]['name'], 'test1')

        rsp = self.api_get(get_repository_list_url() + '?name-or-path=dummy2',
                           expected_mimetype=repository_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['repositories']), 1)
        self.assertEqual(rsp['repositories'][0]['name'], 'test2')

    def test_get_repositories_with_name_or_path_many(self):
        """Testing the GET repositories/?name-or-path= API
        and comma-separated list
        """
        self.create_repository(name='test1', path='dummy1', tool_name='Test')
        self.create_repository(name='test2', path='dummy2', tool_name='Test')
        self.create_repository(name='test3', path='dummy3', tool_name='Test')

        rsp = self.api_get(
            get_repository_list_url() + '?name-or-path=test1,dummy2',
            expected_mimetype=repository_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['repositories']), 2)
        self.assertEqual(rsp['repositories'][0]['name'], 'test1')
        self.assertEqual(rsp['repositories'][1]['name'], 'test2')

    def test_get_repositories_with_tool(self):
        """Testing the GET repositories/?tool= API"""
        self.create_repository(name='test1', path='dummy1', tool_name='Git')
        self.create_repository(name='test2', path='dummy2', tool_name='Test')

        rsp = self.api_get(get_repository_list_url() + '?tool=Git',
                           expected_mimetype=repository_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['repositories']), 1)
        self.assertEqual(rsp['repositories'][0]['name'], 'test1')

    def test_get_repositories_with_tool_many(self):
        """Testing the GET repositories/?tool= API and comma-separated list"""
        self.create_repository(name='test1', path='dummy1', tool_name='Git')
        self.create_repository(name='test2', path='dummy2', tool_name='Test')
        self.create_repository(name='test3', path='dummy3',
                               tool_name='Subversion')

        rsp = self.api_get(get_repository_list_url() + '?tool=Git,Subversion',
                           expected_mimetype=repository_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['repositories']), 2)
        self.assertEqual(rsp['repositories'][0]['name'], 'test1')
        self.assertEqual(rsp['repositories'][1]['name'], 'test3')

    def test_get_repositories_with_hosting_service(self):
        """Testing the GET repositories/?hosting-service= API"""
        hosting_account = HostingServiceAccount.objects.create(
            service_name='github',
            username='my-username')

        Repository.objects.create(
            name='My New Repository',
            path='https://example.com',
            tool=Tool.objects.get(name='Git'),
            hosting_account=hosting_account)

        rsp = self.api_get(
            get_repository_list_url() + '?hosting-service=github',
            expected_mimetype=repository_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['repositories']), 1)
        self.assertEqual(rsp['repositories'][0]['name'],
                         'My New Repository')

    def test_get_repositories_with_hosting_service_many(self):
        """Testing the GET repositories/?hosting-service= API and
        comma-separated list
        """
        hosting_account = HostingServiceAccount.objects.create(
            service_name='github',
            username='my-username')

        Repository.objects.create(
            name='My New Repository 1',
            path='https://example.com',
            tool=Tool.objects.get(name='Git'),
            hosting_account=hosting_account)

        hosting_account = HostingServiceAccount.objects.create(
            service_name='beanstalk',
            username='my-username')

        Repository.objects.create(
            name='My New Repository 2',
            path='https://example.com',
            tool=Tool.objects.get(name='Subversion'),
            hosting_account=hosting_account)

        rsp = self.api_get(
            get_repository_list_url() + '?hosting-service=github,beanstalk',
            expected_mimetype=repository_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['repositories']), 2)
        self.assertEqual(rsp['repositories'][0]['name'],
                         'My New Repository 1')
        self.assertEqual(rsp['repositories'][1]['name'],
                         'My New Repository 2')

    def test_get_repositories_with_username(self):
        """Testing the GET repositories/?username= API"""
        hosting_account = HostingServiceAccount.objects.create(
            service_name='github',
            username='my-username')

        Repository.objects.create(
            name='My New Repository 1',
            path='https://example.com',
            tool=Tool.objects.get(name='Git'),
            hosting_account=hosting_account)

        Repository.objects.create(
            name='My New Repository 2',
            path='https://example.com',
            username='my-username',
            tool=Tool.objects.get(name='Subversion'))

        rsp = self.api_get(get_repository_list_url() + '?username=my-username',
                           expected_mimetype=repository_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['repositories']), 2)
        self.assertEqual(rsp['repositories'][0]['name'],
                         'My New Repository 1')
        self.assertEqual(rsp['repositories'][1]['name'],
                         'My New Repository 2')

    def test_get_repositories_with_username_many(self):
        """Testing the GET repositories/?username= API and comma-separated list
        """
        hosting_account = HostingServiceAccount.objects.create(
            service_name='github',
            username='my-username')

        Repository.objects.create(
            name='My New Repository 1',
            path='https://example.com',
            tool=Tool.objects.get(name='Git'),
            hosting_account=hosting_account)

        Repository.objects.create(
            name='My New Repository 2',
            path='https://example.com',
            username='my-username-2',
            tool=Tool.objects.get(name='Subversion'))

        rsp = self.api_get(
            get_repository_list_url() + '?username=my-username,my-username-2',
            expected_mimetype=repository_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['repositories']), 2)
        self.assertEqual(rsp['repositories'][0]['name'],
                         'My New Repository 1')
        self.assertEqual(rsp['repositories'][1]['name'],
                         'My New Repository 2')

    #
    # HTTP POST tests
    #

    def setup_basic_post_test(self, user, with_local_site, local_site_name,
                              post_valid_data):

        return (get_repository_list_url(local_site_name),
                repository_item_mimetype,
                {
                    'name': 'Test Repository',
                    'path': self.sample_repo_path,
                    'tool': 'Test',
                },
                [])

    def check_post_result(self, user, rsp):
        self._verify_repository_info(
            rsp=rsp,
            expected_tool_id='test',
            expected_attrs={
                'name': 'Test Repository',
                'path': self.sample_repo_path,
            })

    def test_post_with_visible_False(self):
        """Testing the POST repositories/ API with visible=False"""
        rsp = self._post_repository({
            'visible': False,
        })

        self._verify_repository_info(
            rsp=rsp,
            expected_attrs={
                'visible': False,
            })

    def test_post_with_bad_host_key(self):
        """Testing the POST repositories/ API with Bad Host Key error"""
        self.spy_on(TestTool.check_repository,
                    owner=TestTool,
                    op=kgb.SpyOpRaise(BadHostKeyError('example.com', key1,
                                                      key2)))

        rsp = self._post_repository(expected_status=403)

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], BAD_HOST_KEY.code)
        self.assertIn('hostname', rsp)
        self.assertIn('expected_key', rsp)
        self.assertIn('key', rsp)
        self.assertEqual(rsp['hostname'], 'example.com')
        self.assertEqual(rsp['expected_key'], key2.get_base64())
        self.assertEqual(rsp['key'], key1.get_base64())

    def test_post_with_bad_host_key_and_trust_host(self):
        """Testing the POST repositories/ API with Bad Host Key error and
        trust_host=1
        """
        self.spy_on(SSHClient.replace_host_key,
                    owner=SSHClient,
                    call_original=False)

        @self.spy_for(TestTool.check_repository, owner=TestTool)
        def _check_repository(cls, *args, **kwargs):
            if not SSHClient.replace_host_key.called:
                raise BadHostKeyError('example.com', key1, key2)

        self._post_repository({
            'trust_host': 1,
        })

        self.assertSpyCalledWith(SSHClient.replace_host_key,
                                 'example.com', key2, key1)

    def test_post_with_unknown_host_key(self):
        """Testing the POST repositories/ API with Unknown Host Key error"""
        self.spy_on(TestTool.check_repository,
                    owner=TestTool,
                    op=kgb.SpyOpRaise(UnknownHostKeyError('example.com',
                                                          key1)))

        rsp = self._post_repository(expected_status=403)

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], UNVERIFIED_HOST_KEY.code)
        self.assertIn('hostname', rsp)
        self.assertIn('key', rsp)
        self.assertEqual(rsp['hostname'], 'example.com')
        self.assertEqual(rsp['key'], key1.get_base64())

    def test_post_with_unknown_host_key_and_trust_host(self):
        """Testing the POST repositories/ API with Unknown Host Key error
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

    def test_post_with_unknown_cert(self):
        """Testing the POST repositories/ API with Unknown Certificate error"""
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

    def test_post_with_unknown_cert_and_trust_host(self):
        """Testing the POST repositories/ API with Unknown Certificate error
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
        def _check_repository(cls, *args, **kwargs):
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

    def test_post_with_missing_user_key(self):
        """Testing the POST repositories/ API with Missing User Key error"""
        self.spy_on(
            TestTool.check_repository,
            owner=TestTool,
            op=kgb.SpyOpRaise(AuthenticationError(allowed_types=['publickey'],
                                                  user_key=None)))

        rsp = self._post_repository(expected_status=403)

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], MISSING_USER_KEY.code)

    def test_post_with_authentication_error(self):
        """Testing the POST repositories/ API with Authentication Error"""
        self.spy_on(
            TestTool.check_repository,
            owner=TestTool,
            op=kgb.SpyOpRaise(AuthenticationError()))

        rsp = self._post_repository(expected_status=403)

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], REPO_AUTHENTICATION_ERROR.code)
        self.assertIn('reason', rsp)

    def test_post_full_info(self):
        """Testing the POST repositories/ API with all available info"""
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

    def test_post_with_no_access(self):
        """Testing the POST repositories/ API with no access"""
        self._post_repository(use_admin=False,
                              expected_status=403)

    def test_post_duplicate(self):
        """Testing the POST repositories/ API with a duplicate repository"""
        self._post_repository()
        self._post_repository(expected_status=409)

    def _post_repository(self, data={}, use_local_site=None, use_admin=True,
                         expected_status=201, expected_tool_id='test',
                         expected_attrs={}):
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

        if 'hosting_type' not in data:
            post_data['path'] = self.sample_repo_path

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


@six.add_metaclass(BasicTestsMetaclass)
class ResourceItemTests(ExtraDataItemMixin, BaseRepositoryTests):
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

    def test_delete(self):
        """Testing the DELETE repositories/<id>/ API"""
        repo_id = self._delete_repository(with_review_request=True)

        repo = Repository.objects.get(pk=repo_id)
        self.assertTrue(repo.archived)

    def test_delete_empty_repository(self):
        """Testing the DELETE repositories/<id>/ API with no review requests"""
        repo_id = self._delete_repository()

        self.assertFalse(Repository.objects.filter(pk=repo_id).exists())

    @add_fixtures(['test_site'])
    def test_delete_with_site(self):
        """Testing the DELETE repositories/<id>/ API with a local site"""
        repo_id = self._delete_repository(use_local_site=True,
                                          with_review_request=True)

        repo = Repository.objects.get(pk=repo_id)
        self.assertTrue(repo.archived)

    @add_fixtures(['test_site'])
    def test_delete_empty_repository_with_site(self):
        """Testing the DELETE repositories/<id>/ API with a local site and
        no review requests
        """
        repo_id = self._delete_repository(use_local_site=True)

        self.assertFalse(Repository.objects.filter(pk=repo_id).exists())

    def test_delete_with_no_access(self):
        """Testing the DELETE repositories/<id>/ API with no access"""
        self._delete_repository(use_admin=False,
                                expected_status=403)

    @add_fixtures(['test_site'])
    def test_delete_with_site_no_access(self):
        """Testing the DELETE repositories/<id>/ API with a local site and
        no access
        """
        self._delete_repository(use_local_site=True,
                                use_admin=False,
                                expected_status=403)

    #
    # HTTP GET tests
    #

    def setup_basic_get_test(self, user, with_local_site, local_site_name):
        repository = self.create_repository(with_local_site=with_local_site)

        return (get_repository_item_url(repository, local_site_name),
                repository_item_mimetype,
                repository)

    #
    # HTTP PUT tests
    #

    def setup_basic_put_test(self, user, with_local_site, local_site_name,
                             put_valid_data):
        repository = self.create_repository(
            with_local_site=with_local_site,
            tool_name='Git',
            path=self.sample_repo_path,
            mirror_path='git@localhost:test.git')

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

    def check_put_result(self, user, item_rsp, repository, *args):
        repository = Repository.objects.get(pk=repository.pk)
        self.assertEqual(repository.raw_file_url,
                         'http://example.com/<filename>/<version>')
        self.assertEqual(repository.get_credentials(), {
            'username': 'user',
            'password': '123',
        })

        self.compare_item(item_rsp, repository)

    def test_put_with_archive(self):
        """Testing the PUT repositories/<id>/ API with archive_name=True"""
        rsp = self._put_repository(data={
            'archive_name': True,
        })

        repository = self._verify_repository_info(
            rsp=rsp,
            expected_attrs={
                'archived': True,
                'public': False,
            })
        self.assertEqual(repository.name[:23], 'ar:New Test Repository:')
        self.assertIsNotNone(repository.archived_timestamp)

    def _put_repository(self, data={}, use_local_site=False, use_admin=True,
                        expected_status=200):
        """Modify a repository via the API.

        This will build and send an API request to modify a repository,
        returning the resulting payload.

        By default, the form data will set the ``name`` to a default value.
        This can be overridden by the caller to another value.

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
        repo_name = 'New Test Repository'

        repo = self.create_repository(with_local_site=use_local_site)

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

        return self.api_put(
            get_repository_item_url(repo, local_site_name),
            dict({
                'name': repo_name,
            }, **data),
            expected_status=expected_status,
            expected_mimetype=expected_mimetype)

    def _delete_repository(self, use_local_site=False, use_admin=True,
                           expected_status=204, with_review_request=False):
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
            self.create_review_request(submitter=self.user,
                                       repository=repo)

        # Make the request to the API.
        if use_admin:
            self._login_user(local_site=use_local_site,
                             admin=True)

        self.api_delete(get_repository_item_url(repo, local_site_name),
                        expected_status=expected_status)

        return repo.pk
