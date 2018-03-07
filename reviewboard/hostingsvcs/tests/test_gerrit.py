"""Tests for the Gerrit hosting service."""

from __future__ import unicode_literals

import base64
import json

from django.utils import six
from django.utils.six.moves.urllib.parse import urlparse

from reviewboard.hostingsvcs.errors import (AuthorizationError,
                                            HostingServiceAPIError,
                                            HostingServiceError,
                                            RepositoryError)
from reviewboard.hostingsvcs.gerrit import Gerrit, GerritClient
from reviewboard.hostingsvcs.tests.testcases import ServiceTests
from reviewboard.scmtools.core import Branch, Commit
from reviewboard.scmtools.crypto_utils import encrypt_password
from reviewboard.scmtools.errors import FileNotFoundError
from reviewboard.scmtools.models import Repository


class GerritTests(ServiceTests):
    """Tests for the Gerrit hosting service."""

    service_name = 'gerrit'

    def test_service_support(self):
        """Testing the Gerrit service support capabilities"""
        self.assertFalse(self.service_class.supports_bug_trackers)
        self.assertTrue(self.service_class.supports_repositories)
        self.assertFalse(self.service_class.supports_ssh_key_association)
        self.assertTrue(self.service_class.supports_post_commit)

    def test_authorization_fail(self):
        """Testing Gerrit.authorize handles authentication failure"""
        self._setup_api_test()

        def _http_get(*args, **kwargs):
            raise HostingServiceError('', http_code=401)

        self.spy_on(GerritClient.http_get, call_fake=_http_get)

        with self.assertRaises(AuthorizationError):
            self.service.authorize(
                username=self.account.username,
                password=self.account.data['gerrit_http_password'],
                hosting_url='',
                credentials={
                    'username': self.account.username,
                    'password': self.account.data['gerrit_http_password'],
                },
                local_site_name=None,
                gerrit_url='http://gerrit.example.com')

        self.assertFalse(self.account.data['authorized'])

    def test_authorization(self):
        """Testing Gerrit.authorize"""
        self._setup_api_test()

        def _http_get(*args, **kwargs):
            return '', {}

        self.spy_on(GerritClient.http_get, call_fake=_http_get)
        self.service.authorize(
            username=self.account.username,
            password=self.account.data['gerrit_http_password'],
            hosting_url='',
            credentials={
                'username': self.account.username,
                'password': self.account.data['gerrit_http_password'],
            },
            local_site_name=None,
            gerrit_url='http://gerrit.example.com')

        self.assertIn('authorized', self.account.data)
        self.assertTrue(self.account.data['authorized'])

    def test_get_branches(self):
        """Testing Gerrit.get_branches parses branches correctly"""
        self._setup_api_test()

        def _http_get(*args, **kwargs):
            return b")]}'\n%s" % json.dumps([
                {
                    'ref': 'HEAD',
                    'revision': 'master'
                },
                {
                    'ref': 'refs/meta/config',
                    'revision': '7a59a483aeefc8c7d4082f1081c42db817176071'
                },
                {
                    'ref': 'refs/heads/master',
                    'revision': '6854734ef5fc8b2b9d291bf42aa59c344abf5a73'
                },
                {
                    'ref': 'refs/heads/release-2.0.x',
                    'revision': '7f68a001f8e5b77e7355c11385bfbcd2a6d3c077'
                },
                {
                    'ref': 'refs/heads/release-2.5.x',
                    'revision': 'fc8a7ecf288d835ecd9ded086ffaee9412d1da9c'
                },
            ]).encode('utf-8'), {}

        self.spy_on(GerritClient.http_get, call_fake=_http_get)
        rsp = self.service.get_branches(self.repository)
        self.assertEqual(
            rsp,
            [
                Branch(commit='6854734ef5fc8b2b9d291bf42aa59c344abf5a73',
                       id='master', default=True),
                Branch(commit='7f68a001f8e5b77e7355c11385bfbcd2a6d3c077',
                       id='release-2.0.x'),
                Branch(commit='fc8a7ecf288d835ecd9ded086ffaee9412d1da9c',
                       id='release-2.5.x'),
            ]
        )

    def test_get_commits(self):
        """Testing Gerrit.get_commits parses commits correctly"""
        self._setup_api_test()

        def _http_get(*args, **kwargs):
            return b")]}'\n%s" % json.dumps([
                {
                    'message': 'Backport a fix for screenshot commenting.\n',
                    'revision': '77c174669b7018936f16b98547445624c6738e1e',
                    'author': 'David Trowbridge',
                    'parents': [
                        'ecfbf578d31f550a135580cee26fa20fbaea36d9',
                    ],
                    'time': '2016-09-05T23:28:30-07:00',
                },
                {
                    'message': 'Fix some issues with screenshot commenting.'
                               '\n',
                    'revision': '8a39b87f0124f27225234014a87914e434b223a9',
                    'author': 'David Trowbridge',
                    'parents': [
                        '3fb32c83993cd8c07fbbb605cf0cc523010da7c8',
                    ],
                    'time': '2016-09-05T22:58:29-07:00',
                },
                {
                    'message': 'Fix draggability of the comment dialog.\n',
                    'revision': '3fb32c83993cd8c07fbbb605cf0cc523010da7c8',
                    'author': 'David Trowbridge',
                    'parents': [
                        '7619f51371b55bfcdf4cb3fccf5d3c76bf5002c0',
                    ],
                    'time': '2016-09-05T22:47:55-07:00',
                },
            ]).encode('utf-8'), {}

        self.spy_on(GerritClient.http_get, call_fake=_http_get)
        rsp = self.service.get_commits(self.repository)
        self.assertEqual(
            rsp,
            [
                Commit(
                    author_name='David Trowbridge',
                    id='77c174669b7018936f16b98547445624c6738e1e',
                    date='2016-09-05T23:28:30-07:00',
                    message='Backport a fix for screenshot commenting.\n',
                    parent='ecfbf578d31f550a135580cee26fa20fbaea36d9'
                ),
                Commit(
                    author_name='David Trowbridge',
                    id='8a39b87f0124f27225234014a87914e434b223a9',
                    date='2016-09-05T22:58:29-07:00',
                    message='Fix some issues with screenshot commenting.\n',
                    parent='3fb32c83993cd8c07fbbb605cf0cc523010da7c8'
                ),
                Commit(
                    author_name='David Trowbridge',
                    id='3fb32c83993cd8c07fbbb605cf0cc523010da7c8',
                    date='2016-09-05T22:47:55-07:00',
                    message='Fix draggability of the comment dialog.\n',
                    parent='7619f51371b55bfcdf4cb3fccf5d3c76bf5002c0'
                ),
            ]
        )

    def test_get_file_exists(self):
        """Testing Gerrit.get_file_exists"""
        self._setup_api_test()

        def _http_get(*args, **kwargs):
            return b")]}'\n%s" % json.dumps({
                'blobId': 'a' * 40,
            }).encode('utf-8'), {}

        self.spy_on(GerritClient.http_get, _http_get)
        self.assertTrue(self.service.get_file_exists(
            self.repository, '/bogus', 'a' * 40))

    def test_get_file_exists_404(self):
        """Testing Gerrit.get_file_exists with a non-existant file"""
        self._setup_api_test()

        def _http_get(*args, **kwargs):
            raise HostingServiceAPIError('', http_code=404)

        self.spy_on(GerritClient.http_get, _http_get)
        self.assertFalse(self.service.get_file_exists(
            self.repository, '/bogus', 'a' * 40))

    def test_get_file(self):
        """Testing Gerrit.get_file"""
        self._setup_api_test()

        def _http_get(*args, **kwargs):
            return base64.b64encode(b'Hello, world!'), {}

        self.spy_on(GerritClient.http_get, _http_get)

        self.assertEquals(self.service.get_file(self.repository, '/bogus',
                                                'a' * 40),
                          'Hello, world!')

    def test_get_file_404(self):
        """Testing Gerrit.get_file with a non-existent blob ID"""
        self._setup_api_test()

        def _http_get(*args, **kwargs):
            raise HostingServiceAPIError('', http_code=404)

        self.spy_on(GerritClient.http_get, _http_get)

        with self.assertRaises(FileNotFoundError):
            self.service.get_file(self.repository, '/bogus', 'a' * 40)

    def test_get_file_undecodable(self):
        """Testing Gerrit.get_file with an undecodable response."""
        self._setup_api_test()

        def _http_get(*args, **kwargs):
            return b'?Invalid base64', {}

        self.spy_on(GerritClient.http_get, _http_get)

        with self.assertRaises(HostingServiceAPIError) as e:
            self.service.get_file(self.repository, '/foo', 'a' * 40)

        self.assertIn('response could not be decoded',
                      six.text_type(e.exception))

    def test_check_repository_404(self):
        """Testing Gerrit.check_repository with a non-existent repository"""
        self._setup_api_test()

        def _http_get(*args, **kwargs):
            raise HostingServiceAPIError('', 404)

        self.spy_on(GerritClient.http_get, _http_get)

        with self.assertRaises(RepositoryError):
            self.service.check_repository('http://gerrit.example.com',
                                          'Project')

    def test_check_repository_no_plugin(self):
        """Testing Gerrit.check_repository with no plugin"""
        self._setup_api_test()

        def _http_get(*args, **kwargs):
            return b")]}'\n{}", {}

        self.spy_on(GerritClient.http_get, _http_get)

        with self.assertRaises(RepositoryError):
            self.service.check_repository('http://gerrit.example.com',
                                          'Project')

    def test_check_repository_bad_plugin_version(self):
        """Testing Gerrit.check_repository with an outdated plugin"""
        self._setup_api_test()

        def _http_get(*args, **kwargs):
            return b")]}'\n%s" % json.dumps({
                'gerrit-reviewboard': {
                    'id': 'gerrit-reviewboard',
                    'version': '0.0.0',
                },
            }).encode('utf-8'), {}

        self.spy_on(GerritClient.http_get, _http_get)

        with self.assertRaises(RepositoryError):
            self.service.check_repository('http://gerrit.example.com',
                                          'Project')

    def test_check_repository(self):
        """Testing Gerrit.check_repository"""
        self._setup_api_test()

        def _http_get(*args, **kwargs):
            return b")]}'\n%s" % json.dumps({
                'gerrit-reviewboard': {
                    'id': 'gerrit-reviewboard',
                    'version': '%s.%s.%s' % Gerrit.REQUIRED_PLUGIN_VERSION,
                },
            }).encode('utf-8'), {}

        self.spy_on(GerritClient.http_get, _http_get)
        self.service.check_repository('http://gerrit.example.com',
                                      'Project')

    def test_get_change(self):
        """Testing Gerrit.get_change"""
        self._setup_api_test()

        revision = '77c174669b7018936f16b98547445624c6738e1e'

        def _http_get(self, url, *args, **kwargs):
            parts = urlparse(url)

            if parts.path == '/a/projects/Project/commits/%s/diff/' % revision:
                rsp = b'fake diff'
            elif parts.path == '/a/projects/Project/all-commits/':
                rsp = b")]}'\n%s" % json.dumps([{
                    'message': 'Backport a fix for screenshot '
                               'commenting.\n',
                    'revision': '77c174669b7018936f16b98547445624c6738e1e',
                    'author': 'David Trowbridge',
                    'parents': [
                        'ecfbf578d31f550a135580cee26fa20fbaea36d9',
                    ],
                    'time': '2016-09-05T23:28:30-07:00',
                }]).encode('utf-8')
            else:
                raise AssertionError('Unexpected url: "%s"' % url)

            return rsp, {}

        self.spy_on(GerritClient.http_get, _http_get)

        self.assertEqual(
            self.service.get_change(
                self.repository, '77c174669b7018936f16b98547445624c6738e1e'
            ),
            Commit(
                author_name='David Trowbridge',
                id='77c174669b7018936f16b98547445624c6738e1e',
                date='2016-09-05T23:28:30-07:00',
                message='Backport a fix for screenshot commenting.\n',
                parent='ecfbf578d31f550a135580cee26fa20fbaea36d9',
                diff='fake diff'
            )
        )

    def _get_hosting_account(self, use_url=False, local_site=None):
        account = super(GerritTests, self)._get_hosting_account(
            use_url=use_url, local_site=local_site)
        account.data = {
            'authorized': False,
            'gerrit_http_password': encrypt_password('foo'),
            'gerrit_ssh_port': 1234,
        }

        return account

    def _setup_api_test(self):
        self.account = self._get_hosting_account()
        self.service = Gerrit(self.account)

        repository = Repository(name='bogus',
                                path='bogus',
                                hosting_account=self.account)
        repository.extra_data = {
            'gerrit_url': 'http://gerrit.example.com/',
            'gerrit_project_name': 'Project',
        }

        self.repository = repository
