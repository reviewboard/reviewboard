from __future__ import unicode_literals

import os

import paramiko
from django.utils import six
from djblets.testing.decorators import add_fixtures

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
from reviewboard.webapi.tests.urls import (get_repository_item_url,
                                           get_repository_list_url)


# Only generate these keys once.
key1 = paramiko.RSAKey.generate(1024)
key2 = paramiko.RSAKey.generate(1024)


class BaseRepositoryTests(BaseWebAPITestCase):
    """Base class for the RepositoryResource test suites."""
    fixtures = ['test_users', 'test_scmtools']

    sample_repo_path = (
        'file://' + os.path.abspath(
            os.path.join(os.path.dirname(scmtools.__file__), 'testdata',
                         'git_repo')))

    def _verify_repository_info(self, rsp, repo_name, repo_path, data):
        self.assertEqual(rsp['stat'], 'ok')
        self.assertIn('repository', rsp)

        repository = Repository.objects.get(pk=rsp['repository']['id'])

        self.assertEqual(rsp['repository']['path'], repo_path)
        self.assertEqual(repository.path, repo_path)

        if not data.get('archive_name', False):
            self.assertEqual(rsp['repository']['name'], repo_name)
            self.assertEqual(repository.name, repo_name)

        for key, value in six.iteritems(data):
            if hasattr(repository, key):
                self.assertEqual(getattr(repository, key), value)


@six.add_metaclass(BasicTestsMetaclass)
class ResourceListTests(BaseRepositoryTests):
    """Testing the RepositoryResource list APIs."""
    sample_api_url = 'repositories/'
    resource = resources.repository
    basic_post_fixtures = ['test_scmtools']
    basic_post_use_admin = True

    def setUp(self):
        super(ResourceListTests, self).setUp()

        # Some tests will temporarily replace some functions, so back them up
        # so we can restore them.
        self._old_check_repository = TestTool.check_repository
        self._old_accept_certificate = TestTool.accept_certificate
        self._old_add_host_key = SSHClient.add_host_key
        self._old_replace_host_key = SSHClient.replace_host_key

    def tearDown(self):
        super(ResourceListTests, self).tearDown()

        TestTool.check_repository = self._old_check_repository
        TestTool.accept_certificate = self._old_accept_certificate
        SSHClient.add_host_key = self._old_add_host_key
        SSHClient.replace_host_key = self._old_replace_host_key

    def compare_item(self, item_rsp, repository):
        self.assertEqual(item_rsp['id'], repository.pk)
        self.assertEqual(item_rsp['path'], repository.path)

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
        """Testing the GET repositories/?hosting-service= API
        and comma-separated list
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
        """Testing the GET repositories/?username= API
        and comma-separated list
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
        self._verify_repository_info(rsp, 'Test Repository',
                                     self.sample_repo_path, {})

    def test_post_with_visible_False(self):
        """Testing the POST repositories/ API with visible=False"""
        self._login_user(admin=True)
        rsp = self._post_repository(False, data={'visible': False})
        self.assertEqual(rsp['repository']['visible'], False)

    def test_post_with_bad_host_key(self):
        """Testing the POST repositories/ API with Bad Host Key error"""
        hostname = 'example.com'
        key = key1
        expected_key = key2

        @classmethod
        def _check_repository(cls, *args, **kwargs):
            raise BadHostKeyError(hostname, key, expected_key)

        TestTool.check_repository = _check_repository

        self._login_user(admin=True)
        rsp = self._post_repository(False, expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], BAD_HOST_KEY.code)
        self.assertIn('hostname', rsp)
        self.assertIn('expected_key', rsp)
        self.assertIn('key', rsp)
        self.assertEqual(rsp['hostname'], hostname)
        self.assertEqual(rsp['expected_key'], expected_key.get_base64())
        self.assertEqual(rsp['key'], key.get_base64())

    def test_post_with_bad_host_key_and_trust_host(self):
        """Testing the POST repositories/ API
        with Bad Host Key error and trust_host=1
        """
        hostname = 'example.com'
        key = key1
        expected_key = key2
        saw = {'replace_host_key': False}

        def _replace_host_key(cls, _hostname, _expected_key, _key):
            self.assertEqual(hostname, _hostname)
            self.assertEqual(expected_key, _expected_key)
            self.assertEqual(key, _key)
            saw['replace_host_key'] = True

        @classmethod
        def _check_repository(cls, *args, **kwargs):
            if not saw['replace_host_key']:
                raise BadHostKeyError(hostname, key, expected_key)

        TestTool.check_repository = _check_repository
        SSHClient.replace_host_key = _replace_host_key

        self._login_user(admin=True)
        self._post_repository(False, data={
            'trust_host': 1,
        })

        self.assertTrue(saw['replace_host_key'])

    def test_post_with_unknown_host_key(self):
        """Testing the POST repositories/ API with Unknown Host Key error"""
        hostname = 'example.com'
        key = key1

        @classmethod
        def _check_repository(cls, *args, **kwargs):
            raise UnknownHostKeyError(hostname, key)

        TestTool.check_repository = _check_repository

        self._login_user(admin=True)
        rsp = self._post_repository(False, expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], UNVERIFIED_HOST_KEY.code)
        self.assertIn('hostname', rsp)
        self.assertIn('key', rsp)
        self.assertEqual(rsp['hostname'], hostname)
        self.assertEqual(rsp['key'], key.get_base64())

    def test_post_with_unknown_host_key_and_trust_host(self):
        """Testing the POST repositories/ API
        with Unknown Host Key error and trust_host=1
        """
        hostname = 'example.com'
        key = key1
        saw = {'add_host_key': False}

        def _add_host_key(cls, _hostname, _key):
            self.assertEqual(hostname, _hostname)
            self.assertEqual(key, _key)
            saw['add_host_key'] = True

        @classmethod
        def _check_repository(cls, *args, **kwargs):
            if not saw['add_host_key']:
                raise UnknownHostKeyError(hostname, key)

        TestTool.check_repository = _check_repository
        SSHClient.add_host_key = _add_host_key

        self._login_user(admin=True)
        self._post_repository(False, data={
            'trust_host': 1,
        })

        self.assertTrue(saw['add_host_key'])

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

        @classmethod
        def _check_repository(cls, *args, **kwargs):
            raise UnverifiedCertificateError(cert)

        TestTool.check_repository = _check_repository

        self._login_user(admin=True)
        rsp = self._post_repository(False, expected_status=403)
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
        """Testing the POST repositories/ API
        with Unknown Certificate error and trust_host=1
        """
        class Certificate(object):
            failures = ['failures']
            fingerprint = 'fingerprint'
            hostname = 'example.com'
            issuer = 'issuer'
            valid_from = 'valid_from'
            valid_until = 'valid_until'

        cert = Certificate()
        saw = {'accept_certificate': False}

        @classmethod
        def _check_repository(cls, *args, **kwargs):
            if not saw['accept_certificate']:
                raise UnverifiedCertificateError(cert)

        @classmethod
        def _accept_certificate(cls, path, local_site_name=None):
            saw['accept_certificate'] = True
            return {
                'fingerprint': '123',
            }

        TestTool.check_repository = _check_repository
        TestTool.accept_certificate = _accept_certificate

        self._login_user(admin=True)
        rsp = self._post_repository(False, data={
            'trust_host': 1,
        })
        self.assertTrue(saw['accept_certificate'])

        repository = Repository.objects.get(pk=rsp['repository']['id'])
        self.assertIn('cert', repository.extra_data)
        self.assertEqual(repository.extra_data['cert']['fingerprint'], '123')

    def test_post_with_missing_user_key(self):
        """Testing the POST repositories/ API with Missing User Key error"""
        @classmethod
        def _check_repository(cls, *args, **kwargs):
            raise AuthenticationError(allowed_types=['publickey'],
                                      user_key=None)

        TestTool.check_repository = _check_repository

        self._login_user(admin=True)
        rsp = self._post_repository(False, expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], MISSING_USER_KEY.code)

    def test_post_with_authentication_error(self):
        """Testing the POST repositories/ API with Authentication Error"""
        @classmethod
        def _check_repository(cls, *args, **kwargs):
            raise AuthenticationError

        TestTool.check_repository = _check_repository

        self._login_user(admin=True)
        rsp = self._post_repository(False, expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], REPO_AUTHENTICATION_ERROR.code)
        self.assertIn('reason', rsp)

    def test_post_full_info(self):
        """Testing the POST repositories/ API with all available info"""
        self._login_user(admin=True)
        self._post_repository(False, {
            'bug_tracker': 'http://bugtracker/%s/',
            'encoding': 'UTF-8',
            'mirror_path': 'http://svn.example.com/',
            'username': 'user',
            'password': '123',
            'public': False,
            'raw_file_url': 'http://example.com/<filename>/<version>',
        })

    def test_post_with_no_access(self):
        """Testing the POST repositories/ API with no access"""
        self._login_user()
        self._post_repository(False, expected_status=403)

    def test_post_duplicate(self):
        """Testing the POST repositories/ API with a duplicate repository"""
        self._login_user(admin=True)
        self._post_repository(False)
        self._post_repository(False, expected_status=409)

    def _post_repository(self, use_local_site, data={}, expected_status=201):
        repo_name = 'Test Repository'

        if 200 <= expected_status < 300:
            expected_mimetype = repository_item_mimetype
        else:
            expected_mimetype = None

        if use_local_site:
            local_site_name = self.local_site_name
        else:
            local_site_name = None

        rsp = self.api_post(
            get_repository_list_url(local_site_name),
            dict({
                'name': repo_name,
                'path': self.sample_repo_path,
                'tool': 'Test',
            }, **data),
            expected_status=expected_status,
            expected_mimetype=expected_mimetype)

        if 200 <= expected_status < 300:
            self._verify_repository_info(rsp, repo_name, self.sample_repo_path,
                                         data)

            self.assertEqual(
                rsp['repository']['links']['self']['href'],
                self.base_url +
                get_repository_item_url(rsp['repository']['id'],
                                        local_site_name))

        return rsp


@six.add_metaclass(BasicTestsMetaclass)
class ResourceItemTests(BaseRepositoryTests):
    """Testing the RepositoryResource item APIs."""
    sample_api_url = 'repositories/<id>/'
    fixtures = ['test_users', 'test_scmtools']
    test_http_methods = ('GET',)
    resource = resources.repository

    def compare_item(self, item_rsp, repository):
        self.assertEqual(item_rsp['id'], repository.pk)
        self.assertEqual(item_rsp['path'], repository.path)

    #
    # HTTP DELETE tests
    #

    def test_delete(self):
        """Testing the DELETE repositories/<id>/ API"""
        self._login_user(admin=True)
        repo_id = self._delete_repository(False, with_review_request=True)

        repo = Repository.objects.get(pk=repo_id)
        self.assertFalse(repo.visible)

    def test_delete_empty_repository(self):
        """Testing the DELETE repositories/<id>/ API with no review requests"""
        self._login_user(admin=True)
        repo_id = self._delete_repository(False)
        self.assertRaises(Repository.DoesNotExist,
                          Repository.objects.get,
                          pk=repo_id)

    @add_fixtures(['test_site'])
    def test_delete_with_site(self):
        """Testing the DELETE repositories/<id>/ API with a local site"""
        self._login_user(local_site=True, admin=True)
        repo_id = self._delete_repository(True, with_review_request=True)

        repo = Repository.objects.get(pk=repo_id)
        self.assertFalse(repo.visible)

    @add_fixtures(['test_site'])
    def test_delete_empty_repository_with_site(self):
        """Testing the DELETE repositories/<id>/ API
        with a local site and no review requests
        """
        self._login_user(local_site=True, admin=True)
        repo_id = self._delete_repository(True)
        self.assertRaises(Repository.DoesNotExist,
                          Repository.objects.get,
                          pk=repo_id)

    def test_delete_with_no_access(self):
        """Testing the DELETE repositories/<id>/ API with no access"""
        self._login_user()
        self._delete_repository(False, expected_status=403)

    @add_fixtures(['test_site'])
    def test_delete_with_site_no_access(self):
        """Testing the DELETE repositories/<id>/ API
        with a local site and no access
        """
        self._login_user(local_site=True)
        self._delete_repository(True, expected_status=403)

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

    def test_put(self):
        """Testing the PUT repositories/<id>/ API"""
        self._login_user(admin=True)
        self._put_repository(False, {
            'bug_tracker': 'http://bugtracker/%s/',
            'encoding': 'UTF-8',
            'mirror_path': 'http://svn.example.com/',
            'username': 'user',
            'password': '123',
            'public': False,
            'raw_file_url': 'http://example.com/<filename>/<version>',
        })

    @add_fixtures(['test_site'])
    def test_put_with_site(self):
        """Testing the PUT repositories/<id>/ API with a local site"""
        self._login_user(local_site=True, admin=True)
        self._put_repository(True, {
            'bug_tracker': 'http://bugtracker/%s/',
            'encoding': 'UTF-8',
            'mirror_path': 'http://svn.example.com/',
            'username': 'user',
            'password': '123',
            'public': False,
            'raw_file_url': 'http://example.com/<filename>/<version>',
        })

    def test_put_with_no_access(self):
        """Testing the PUT repositories/<id>/ API with no access"""
        self._login_user()
        self._put_repository(False, expected_status=403)

    @add_fixtures(['test_site'])
    def test_put_with_site_no_access(self):
        """Testing the PUT repositories/<id>/ API
        with a local site and no access
        """
        self._login_user(local_site=True)
        self._put_repository(False, expected_status=403)

    def test_put_with_archive(self):
        """Testing the PUT repositories/<id>/ API with archive_name=True"""
        self._login_user(admin=True)
        repo_id = self._put_repository(False, {'archive_name': True})

        repo = Repository.objects.get(pk=repo_id)
        self.assertEqual(repo.name[:23], 'ar:New Test Repository:')
        self.assertTrue(repo.archived)
        self.assertFalse(repo.public)
        self.assertIsNotNone(repo.archived_timestamp)

    def _put_repository(self, use_local_site, data={}, expected_status=200):
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

        rsp = self.api_put(
            get_repository_item_url(repo, local_site_name),
            dict({
                'name': repo_name,
                'path': self.sample_repo_path,
            }, **data),
            expected_status=expected_status,
            expected_mimetype=expected_mimetype)

        if 200 <= expected_status < 300:
            self._verify_repository_info(rsp, repo_name, self.sample_repo_path,
                                         data)

        return repo.pk

    def _delete_repository(self, use_local_site, expected_status=204,
                           with_review_request=False):
        repo = self.create_repository(with_local_site=use_local_site)

        if use_local_site:
            local_site_name = self.local_site_name
        else:
            local_site_name = None

        if with_review_request:
            request = ReviewRequest.objects.create(self.user, repo)
            request.save()

        self.api_delete(get_repository_item_url(repo, local_site_name),
                        expected_status=expected_status)

        return repo.pk
