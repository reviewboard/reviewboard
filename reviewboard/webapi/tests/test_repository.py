import os

import paramiko
from djblets.testing.decorators import add_fixtures

from reviewboard import scmtools
from reviewboard.reviews.models import ReviewRequest
from reviewboard.scmtools.errors import (AuthenticationError,
                                         UnverifiedCertificateError)
from reviewboard.scmtools.models import Repository
from reviewboard.scmtools.svn import SVNTool
from reviewboard.site.models import LocalSite
from reviewboard.ssh.client import SSHClient
from reviewboard.ssh.errors import (BadHostKeyError,
                                    UnknownHostKeyError)
from reviewboard.webapi.errors import (BAD_HOST_KEY,
                                       MISSING_USER_KEY,
                                       REPO_AUTHENTICATION_ERROR,
                                       UNVERIFIED_HOST_CERT,
                                       UNVERIFIED_HOST_KEY)
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import (repository_item_mimetype,
                                                repository_list_mimetype)
from reviewboard.webapi.tests.urls import (get_repository_item_url,
                                           get_repository_list_url)


# Only generate these keys once.
key1 = paramiko.RSAKey.generate(1024)
key2 = paramiko.RSAKey.generate(1024)


class RepositoryResourceTests(BaseWebAPITestCase):
    """Testing the RepositoryResource APIs."""
    fixtures = ['test_users', 'test_scmtools']

    def setUp(self):
        super(RepositoryResourceTests, self).setUp()

        # Some tests will temporarily replace some functions, so back them up
        # so we can restore them.
        self._old_check_repository = SVNTool.check_repository
        self._old_accept_certificate = SVNTool.accept_certificate
        self._old_add_host_key = SSHClient.add_host_key
        self._old_replace_host_key = SSHClient.replace_host_key

    def tearDown(self):
        super(RepositoryResourceTests, self).tearDown()

        SVNTool.check_repository = self._old_check_repository
        SVNTool.accept_certificate = self._old_accept_certificate
        SSHClient.add_host_key = self._old_add_host_key
        SSHClient.replace_host_key = self._old_replace_host_key

    def test_get_repositories(self):
        """Testing the GET repositories/ API"""
        rsp = self.apiGet(get_repository_list_url(),
                          expected_mimetype=repository_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['repositories']),
                         Repository.objects.accessible(self.user).count())

    @add_fixtures(['test_site'])
    def test_get_repositories_with_site(self):
        """Testing the GET repositories/ API with a local site"""
        self._login_user(local_site=True)
        rsp = self.apiGet(get_repository_list_url(self.local_site_name),
                          expected_mimetype=repository_list_mimetype)
        self.assertEqual(len(rsp['repositories']),
                         Repository.objects.filter(
                             local_site__name=self.local_site_name).count())

    @add_fixtures(['test_site'])
    def test_get_repositories_with_show_visible(self):
        """Testing the GET repositories/ API with show_invisible=True"""
        rsp = self.apiGet(get_repository_list_url(),
                          query={'show-invisible': True},
                          expected_mimetype=repository_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['repositories']),
                         Repository.objects.accessible(
                             self.user, visible_only=False).count())

    @add_fixtures(['test_site'])
    def test_get_repositories_with_site_no_access(self):
        """Testing the GET repositories/ API with a local site and Permission Denied error"""
        self.apiGet(get_repository_list_url(self.local_site_name),
                    expected_status=403)

    def test_post_repository(self):
        """Testing the POST repositories/ API"""
        self._login_user(admin=True)
        self._post_repository(False)

    def test_post_repository_with_visible_False(self):
        """Testing the POST repositories/ API with visible=False"""
        self._login_user(admin=True)
        rsp = self._post_repository(False, data={'visible': False})
        self.assertEqual(rsp['repository']['visible'], False)

    def test_post_repository_with_bad_host_key(self):
        """Testing the POST repositories/ API with Bad Host Key error"""
        hostname = 'example.com'
        key = key1
        expected_key = key2

        @classmethod
        def _check_repository(cls, *args, **kwargs):
            raise BadHostKeyError(hostname, key, expected_key)

        SVNTool.check_repository = _check_repository

        self._login_user(admin=True)
        rsp = self._post_repository(False, expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], BAD_HOST_KEY.code)
        self.assertTrue('hostname' in rsp)
        self.assertTrue('expected_key' in rsp)
        self.assertTrue('key' in rsp)
        self.assertEqual(rsp['hostname'], hostname)
        self.assertEqual(rsp['expected_key'], expected_key.get_base64())
        self.assertEqual(rsp['key'], key.get_base64())

    def test_post_repository_with_bad_host_key_and_trust_host(self):
        """Testing the POST repositories/ API with Bad Host Key error and trust_host=1"""
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

        SVNTool.check_repository = _check_repository
        SSHClient.replace_host_key = _replace_host_key

        self._login_user(admin=True)
        self._post_repository(False, data={
            'trust_host': 1,
        })

        self.assertTrue(saw['replace_host_key'])

    def test_post_repository_with_unknown_host_key(self):
        """Testing the POST repositories/ API with Unknown Host Key error"""
        hostname = 'example.com'
        key = key1

        @classmethod
        def _check_repository(cls, *args, **kwargs):
            raise UnknownHostKeyError(hostname, key)

        SVNTool.check_repository = _check_repository

        self._login_user(admin=True)
        rsp = self._post_repository(False, expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], UNVERIFIED_HOST_KEY.code)
        self.assertTrue('hostname' in rsp)
        self.assertTrue('key' in rsp)
        self.assertEqual(rsp['hostname'], hostname)
        self.assertEqual(rsp['key'], key.get_base64())

    def test_post_repository_with_unknown_host_key_and_trust_host(self):
        """Testing the POST repositories/ API with Unknown Host Key error and trust_host=1"""
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

        SVNTool.check_repository = _check_repository
        SSHClient.add_host_key = _add_host_key

        self._login_user(admin=True)
        self._post_repository(False, data={
            'trust_host': 1,
        })

        self.assertTrue(saw['add_host_key'])

    def test_post_repository_with_unknown_cert(self):
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

        SVNTool.check_repository = _check_repository

        self._login_user(admin=True)
        rsp = self._post_repository(False, expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], UNVERIFIED_HOST_CERT.code)
        self.assertTrue('certificate' in rsp)
        self.assertEqual(rsp['certificate']['failures'], cert.failures)
        self.assertEqual(rsp['certificate']['fingerprint'], cert.fingerprint)
        self.assertEqual(rsp['certificate']['hostname'], cert.hostname)
        self.assertEqual(rsp['certificate']['issuer'], cert.issuer)
        self.assertEqual(rsp['certificate']['valid']['from'], cert.valid_from)
        self.assertEqual(rsp['certificate']['valid']['until'],
                         cert.valid_until)

    def test_post_repository_with_unknown_cert_and_trust_host(self):
        """Testing the POST repositories/ API with Unknown Certificate error and trust_host=1"""
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

        SVNTool.check_repository = _check_repository
        SVNTool.accept_certificate = _accept_certificate

        self._login_user(admin=True)
        rsp = self._post_repository(False, data={
            'trust_host': 1,
        })
        self.assertTrue(saw['accept_certificate'])

        repository = Repository.objects.get(pk=rsp['repository']['id'])
        self.assertTrue('cert' in repository.extra_data)
        self.assertEqual(repository.extra_data['cert']['fingerprint'], '123')

    def test_post_repository_with_missing_user_key(self):
        """Testing the POST repositories/ API with Missing User Key error"""
        @classmethod
        def _check_repository(cls, *args, **kwargs):
            raise AuthenticationError(allowed_types=['publickey'],
                                      user_key=None)

        SVNTool.check_repository = _check_repository

        self._login_user(admin=True)
        rsp = self._post_repository(False, expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], MISSING_USER_KEY.code)

    def test_post_repository_with_authentication_error(self):
        """Testing the POST repositories/ API with Authentication Error"""
        @classmethod
        def _check_repository(cls, *args, **kwargs):
            raise AuthenticationError

        SVNTool.check_repository = _check_repository

        self._login_user(admin=True)
        rsp = self._post_repository(False, expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], REPO_AUTHENTICATION_ERROR.code)
        self.assertTrue('reason' in rsp)

    @add_fixtures(['test_site'])
    def test_post_repository_with_site(self):
        """Testing the POST repositories/ API with a local site"""
        self._login_user(local_site=True, admin=True)
        self._post_repository(True)

    def test_post_repository_full_info(self):
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

    def test_post_repository_with_no_access(self):
        """Testing the POST repositories/ API with no access"""
        self._login_user()
        self._post_repository(False, expected_status=403)

    @add_fixtures(['test_site'])
    def test_post_repository_with_site_no_access(self):
        """Testing the POST repositories/ API with a local site and no access"""
        self._login_user(local_site=True)
        self._post_repository(True, expected_status=403)

    def test_put_repository(self):
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
    def test_put_repository_with_site(self):
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

    def test_put_repository_with_no_access(self):
        """Testing the PUT repositories/<id>/ API with no access"""
        self._login_user()
        self._put_repository(False, expected_status=403)

    @add_fixtures(['test_site'])
    def test_put_repository_with_site_no_access(self):
        """Testing the PUT repositories/<id>/ API with a local site and no access"""
        self._login_user(local_site=True)
        self._put_repository(False, expected_status=403)

    def test_put_repository_with_archive(self):
        """Testing the PUT repositories/<id>/ API with archive_name=True"""
        self._login_user(admin=True)
        repo_id = self._put_repository(False, {'archive_name': True})

        repo = Repository.objects.get(pk=repo_id)
        self.assertEqual(repo.name[:23], 'ar:New Test Repository:')

    def test_delete_repository(self):
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
    def test_delete_repository_with_site(self):
        """Testing the DELETE repositories/<id>/ API with a local site"""
        self._login_user(local_site=True, admin=True)
        repo_id = self._delete_repository(True, with_review_request=True)

        repo = Repository.objects.get(pk=repo_id)
        self.assertFalse(repo.visible)

    @add_fixtures(['test_site'])
    def test_delete_empty_repository_with_site(self):
        """Testing the DELETE repositories/<id>/ API with a local site and no review requests"""
        self._login_user(local_site=True, admin=True)
        repo_id = self._delete_repository(True)
        self.assertRaises(Repository.DoesNotExist,
                          Repository.objects.get,
                          pk=repo_id)

    def test_delete_repository_with_no_access(self):
        """Testing the DELETE repositories/<id>/ API with no access"""
        self._login_user()
        self._delete_repository(False, expected_status=403)

    @add_fixtures(['test_site'])
    def test_delete_repository_with_site_no_access(self):
        """Testing the DELETE repositories/<id>/ API with a local site and no access"""
        self._login_user(local_site=True)
        self._delete_repository(True, expected_status=403)

    def _post_repository(self, use_local_site, data={}, expected_status=201):
        repo_name = 'Test Repository'
        repo_path = 'file://' + os.path.abspath(
            os.path.join(os.path.dirname(scmtools.__file__), 'testdata',
                         'svn_repo'))

        local_site_name = self._get_local_site_info(use_local_site)[1]

        if 200 <= expected_status < 300:
            expected_mimetype = repository_item_mimetype
        else:
            expected_mimetype = None

        rsp = self.apiPost(
            get_repository_list_url(local_site_name),
            dict({
                'name': repo_name,
                'path': repo_path,
                'tool': 'Subversion',
            }, **data),
            expected_status=expected_status,
            expected_mimetype=expected_mimetype)

        if 200 <= expected_status < 300:
            self._verify_repository_info(rsp, repo_name, repo_path, data)

            self.assertEqual(
                rsp['repository']['links']['self']['href'],
                self.base_url +
                get_repository_item_url(rsp['repository']['id'],
                                        local_site_name))

        return rsp

    def _put_repository(self, use_local_site, data={}, expected_status=200):
        repo_name = 'New Test Repository'
        repo_path = 'file://' + os.path.abspath(
            os.path.join(os.path.dirname(scmtools.__file__), 'testdata',
                         'svn_repo'))

        local_site, local_site_name = self._get_local_site_info(use_local_site)
        repo = Repository.objects.filter(local_site=local_site,
                                         tool__name='Subversion')[0]

        if 200 <= expected_status < 300:
            expected_mimetype = repository_item_mimetype
        else:
            expected_mimetype = None

        rsp = self.apiPut(
            get_repository_item_url(repo, local_site_name),
            dict({
                'name': repo_name,
                'path': repo_path,
            }, **data),
            expected_status=expected_status,
            expected_mimetype=expected_mimetype)

        if 200 <= expected_status < 300:
            self._verify_repository_info(rsp, repo_name, repo_path, data)

        return repo.pk

    def _delete_repository(self, use_local_site, expected_status=204,
                           with_review_request=False):
        local_site, local_site_name = self._get_local_site_info(use_local_site)
        repo = Repository.objects.filter(local_site=local_site,
                                         tool__name='Subversion')[0]
        if with_review_request:
            request = ReviewRequest.objects.create(self.user, repo)
            request.save()

        self.apiDelete(get_repository_item_url(repo, local_site_name),
                       expected_status=expected_status)

        return repo.pk

    def _get_local_site_info(self, use_local_site):
        if use_local_site:
            return (LocalSite.objects.get(name=self.local_site_name),
                    self.local_site_name)
        else:
            return None, None

    def _verify_repository_info(self, rsp, repo_name, repo_path, data):
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('repository' in rsp)

        repository = Repository.objects.get(pk=rsp['repository']['id'])

        self.assertEqual(rsp['repository']['path'], repo_path)
        self.assertEqual(repository.path, repo_path)

        if not data.get('archive_name', False):
            self.assertEqual(rsp['repository']['name'], repo_name)
            self.assertEqual(repository.name, repo_name)

        for key, value in data.iteritems():
            if hasattr(repository, key):
                self.assertEqual(getattr(repository, key), value)
