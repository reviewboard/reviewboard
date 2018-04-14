"""Unit tests for the Gerrit hosting service."""

from __future__ import unicode_literals

import base64

from django.utils.six.moves.urllib.request import (HTTPDigestAuthHandler,
                                                   OpenerDirector)

from reviewboard.hostingsvcs.errors import (AuthorizationError,
                                            HostingServiceAPIError,
                                            HostingServiceError,
                                            RepositoryError)
from reviewboard.hostingsvcs.gerrit import GerritForm
from reviewboard.hostingsvcs.testing import HostingServiceTestCase
from reviewboard.scmtools.core import Branch, Commit
from reviewboard.scmtools.crypto_utils import encrypt_password
from reviewboard.scmtools.errors import FileNotFoundError


class GerritTestCase(HostingServiceTestCase):
    """Base class for Gerrit unit tests."""

    service_name = 'gerrit'

    default_account_data = {
        'authorized': False,
        'gerrit_http_password': encrypt_password('mypass'),
        'gerrit_ssh_port': 1234,
    }

    default_repository_tool_name = 'Git'

    default_repository_extra_data = {
        'gerrit_url': 'http://gerrit.example.com/',
        'gerrit_project_name': 'Project',
    }


class GerritFormTests(GerritTestCase):
    """Unit tests for GerritForm."""

    def test_clean(self):
        """Testing GerritForm.clean"""
        form = GerritForm({
            'gerrit_project_name': 'test-project',
            'gerrit_ssh_port': 12345,
            'gerrit_url': 'http://gerrit.example.com:8080',
        })

        self.assertTrue(form.is_valid())
        self.assertEqual(
            form.cleaned_data,
            {
                'gerrit_domain': 'gerrit.example.com',
                'gerrit_project_name': 'test-project',
                'gerrit_ssh_port': 12345,
                'gerrit_url': 'http://gerrit.example.com:8080/',
            })

    def test_clean_with_errors(self):
        """Testing GerritForm.clean with errors"""
        form = GerritForm({
            'gerrit_url': 'invalid',
        })

        self.assertFalse(form.is_valid())
        self.assertEqual(form.cleaned_data, {})
        self.assertIn('gerrit_project_name', form.errors)
        self.assertIn('gerrit_ssh_port', form.errors)
        self.assertIn('gerrit_url', form.errors)
        self.assertEqual(form.errors['gerrit_project_name'],
                         ['This field is required.'])
        self.assertEqual(form.errors['gerrit_ssh_port'],
                         ['This field is required.'])
        self.assertEqual(form.errors['gerrit_url'],
                         ['Enter a valid URL.'])


class GerritClientTests(GerritTestCase):
    """Unit tests for GerritClient."""

    def setUp(self):
        super(GerritClientTests, self).setUp()

        hosting_account = self.create_hosting_account()
        self.client = hosting_account.service.client

    def test_auth_headers(self):
        """Testing GerritClient.http_request sets auth headers"""
        class DummyResponse(object):
            headers = {}

            def read(self):
                return b''

        def _open(*args, **kwargs):
            _open_args.extend(args)

            return DummyResponse()

        _open_args = []
        self.spy_on(OpenerDirector.open, call_fake=_open)

        self.client.http_request(url='http://gerrit.example.com/',
                                 username='test-user',
                                 password='test-pass')

        opener, request = _open_args
        handler = opener.handlers[0]
        self.assertIsInstance(handler, HTTPDigestAuthHandler)
        self.assertEqual(
            handler.passwd.find_user_password(None,
                                              'http://gerrit.example.com/'),
            ('test-user', 'test-pass'))

        self.assertEqual(
            request.headers,
            {
                'Authorization': 'Basic dGVzdC11c2VyOnRlc3QtcGFzcw==',
            })


class GerritTests(GerritTestCase):
    """Unit tests for the Gerrit hosting service."""

    service_name = 'gerrit'

    default_account_data = {
        'authorized': False,
        'gerrit_http_password': encrypt_password('mypass'),
        'gerrit_ssh_port': 1234,
    }

    default_repository_tool_name = 'Git'

    default_repository_extra_data = {
        'gerrit_url': 'http://gerrit.example.com/',
        'gerrit_project_name': 'Project',
    }

    def test_service_support(self):
        """Testing Gerrit service support capabilities"""
        self.assertFalse(self.service_class.supports_bug_trackers)
        self.assertTrue(self.service_class.supports_repositories)
        self.assertFalse(self.service_class.supports_ssh_key_association)
        self.assertTrue(self.service_class.supports_post_commit)

    def test_authorize(self):
        """Testing Gerrit.authorize"""
        hosting_account = self.create_hosting_account(data={})

        with self.setup_http_test(hosting_account=hosting_account,
                                  expected_http_calls=1) as ctx:
            ctx.service.authorize(
                username='myuser',
                password='mypass',
                hosting_url='',
                credentials={
                    'username': 'myuser',
                    'password': 'mypass',
                },
                local_site_name=None,
                gerrit_url='http://gerrit.example.com')

        self.assertIn('authorized', hosting_account.data)
        self.assertTrue(hosting_account.data['authorized'])

        ctx.assertHTTPCall(0, url='http://gerrit.example.com/a/projects/')

    def test_authorize_with_error(self):
        """Testing Gerrit.authorize handles authentication failure"""
        expected_message = (
            'Unable to authenticate to Gerrit at '
            'http://gerrit.example.com/a/projects/. The username or password '
            'used may be invalid.'
        )

        def _http_request(client, *args, **kwargs):
            raise HostingServiceError('', http_code=401)

        with self.setup_http_test(_http_request, expected_http_calls=1) as ctx:
            with self.assertRaisesMessage(AuthorizationError,
                                          expected_message):
                ctx.service.authorize(
                    username='myuser',
                    password='mypass',
                    hosting_url='',
                    credentials={
                        'username': 'myuser',
                        'password': 'mypass',
                    },
                    local_site_name=None,
                    gerrit_url='http://gerrit.example.com')

        ctx.assertHTTPCall(0, url='http://gerrit.example.com/a/projects/')

        self.assertFalse(ctx.hosting_account.data['authorized'])

    def test_check_repository(self):
        """Testing Gerrit.check_repository"""
        payload = self._make_json_rsp({
            'gerrit-reviewboard': {
                'id': 'gerrit-reviewboard',
                'version': self.service_class.REQUIRED_PLUGIN_VERSION_STR,
            },
        })

        with self.setup_http_test(payload=payload,
                                  expected_http_calls=2) as ctx:
            ctx.service.check_repository(
                gerrit_url='http://gerrit.example.com',
                gerrit_project_name='Project')

        ctx.assertHTTPCall(0,
                           url='http://gerrit.example.com/a/projects/Project')
        ctx.assertHTTPCall(1, url='http://gerrit.example.com/a/plugins/')

    def test_check_repository_with_404(self):
        """Testing Gerrit.check_repository with a non-existent repository"""
        def _http_request(client, *args, **kwargs):
            raise HostingServiceAPIError('', 404)

        expected_message = (
            'The project "Project" does not exist or you do not have access '
            'to it.'
        )

        with self.setup_http_test(_http_request,
                                  expected_http_calls=1) as ctx:
            with self.assertRaisesMessage(RepositoryError, expected_message):
                ctx.service.check_repository(
                    gerrit_url='http://gerrit.example.com',
                    gerrit_project_name='Project')

        ctx.assertHTTPCall(0,
                           url='http://gerrit.example.com/a/projects/Project')

    def test_check_repository_with_no_plugin(self):
        """Testing Gerrit.check_repository with no plugin"""
        expected_message = (
            'The "gerrit-reviewboard" plugin is not installed on the server. '
            'See https://github.com/reviewboard/gerrit-reviewboard-plugin/ '
            'for installation instructions.'
        )

        with self.setup_http_test(payload=self._make_json_rsp({}),
                                  expected_http_calls=2) as ctx:
            with self.assertRaisesMessage(RepositoryError, expected_message):
                ctx.service.check_repository(
                    gerrit_url='http://gerrit.example.com',
                    gerrit_project_name='Project')

        ctx.assertHTTPCall(0,
                           url='http://gerrit.example.com/a/projects/Project')
        ctx.assertHTTPCall(1, url='http://gerrit.example.com/a/plugins/')

    def test_check_repository_with_bad_plugin_version(self):
        """Testing Gerrit.check_repository with an outdated plugin"""
        payload = self._make_json_rsp({
            'gerrit-reviewboard': {
                'id': 'gerrit-reviewboard',
                'version': '0.0.0',
            },
        })

        expected_message = (
            'The "gerrit-reviewboard" plugin on the server is an incompatible '
            'version: found 0.0.0 but version %s or higher is required.'
            % self.service_class.REQUIRED_PLUGIN_VERSION_STR
        )

        with self.setup_http_test(payload=payload,
                                  expected_http_calls=2) as ctx:
            with self.assertRaisesMessage(RepositoryError, expected_message):
                ctx.service.check_repository(
                    gerrit_url='http://gerrit.example.com',
                    gerrit_project_name='Project')

        ctx.assertHTTPCall(0,
                           url='http://gerrit.example.com/a/projects/Project')
        ctx.assertHTTPCall(1, url='http://gerrit.example.com/a/plugins/')

    def test_get_file_exists(self):
        """Testing Gerrit.get_file_exists"""
        blob_id = 'a' * 40

        payload = self._make_json_rsp({
            'blobId': blob_id,
        })

        with self.setup_http_test(payload=payload,
                                  expected_http_calls=1) as ctx:
            self.assertTrue(ctx.service.get_file_exists(
                repository=ctx.create_repository(),
                path='/bogus',
                revision=blob_id))

        ctx.assertHTTPCall(
            0,
            url=('http://gerrit.example.com/a/projects/Project/blobs/%s/'
                 % blob_id))

    def test_get_file_exists_with_404(self):
        """Testing Gerrit.get_file_exists with a non-existant file"""
        def _http_request(client, *args, **kwargs):
            raise HostingServiceAPIError('', http_code=404)

        blob_id = 'a' * 40

        with self.setup_http_test(_http_request, expected_http_calls=1) as ctx:
            self.assertFalse(ctx.service.get_file_exists(
                repository=ctx.create_repository(),
                path='/bogus',
                revision=blob_id))

        ctx.assertHTTPCall(
            0,
            url=('http://gerrit.example.com/a/projects/Project/blobs/%s/'
                 % blob_id))

    def test_get_file(self):
        """Testing Gerrit.get_file"""
        blob_id = 'a' * 40

        with self.setup_http_test(payload=base64.b64encode(b'Hello, world!'),
                                  expected_http_calls=1) as ctx:
            data = ctx.service.get_file(repository=ctx.create_repository(),
                                        path='/bogus',
                                        revision=blob_id)

        self.assertIsInstance(data, bytes)
        self.assertEqual(data, b'Hello, world!')

        ctx.assertHTTPCall(
            0,
            url=('http://gerrit.example.com/a/projects/Project/blobs/%s/'
                 'content/'
                 % blob_id))

    def test_get_file_with_404(self):
        """Testing Gerrit.get_file with a non-existent blob ID"""
        def _http_request(client, *args, **kwargs):
            raise HostingServiceAPIError('', http_code=404)

        blob_id = 'a' * 40

        with self.setup_http_test(_http_request, expected_http_calls=1) as ctx:
            with self.assertRaises(FileNotFoundError):
                ctx.service.get_file(repository=ctx.create_repository(),
                                     path='/bogus',
                                     revision=blob_id)

        ctx.assertHTTPCall(
            0,
            url=('http://gerrit.example.com/a/projects/Project/blobs/%s/'
                 'content/'
                 % blob_id))

    def test_get_file_with_undecodable_response(self):
        """Testing Gerrit.get_file with an undecodable response"""
        blob_id = 'a' * 40
        expected_message = (
            'An error occurred while retrieving "/foo" at revision '
            '"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" from Gerrit: the '
            'response could not be decoded: Incorrect padding'
        )

        with self.setup_http_test(payload=b'?Invalid base64',
                                  expected_http_calls=1) as ctx:
            with self.assertRaisesMessage(HostingServiceAPIError,
                                          expected_message):
                ctx.service.get_file(repository=ctx.create_repository(),
                                     path='/foo',
                                     revision=blob_id)

        ctx.assertHTTPCall(
            0,
            url=('http://gerrit.example.com/a/projects/Project/blobs/%s/'
                 'content/'
                 % blob_id))

    def test_get_branches(self):
        """Testing Gerrit.get_branches"""
        payload = self._make_json_rsp([
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
        ])

        with self.setup_http_test(payload=payload,
                                  expected_http_calls=1) as ctx:
            branches = ctx.service.get_branches(ctx.create_repository())

        ctx.assertHTTPCall(
            0,
            url='http://gerrit.example.com/a/projects/Project/branches/')

        self.assertEqual(
            branches,
            [
                Branch(commit='6854734ef5fc8b2b9d291bf42aa59c344abf5a73',
                       id='master',
                       default=True),
                Branch(commit='7f68a001f8e5b77e7355c11385bfbcd2a6d3c077',
                       id='release-2.0.x'),
                Branch(commit='fc8a7ecf288d835ecd9ded086ffaee9412d1da9c',
                       id='release-2.5.x'),
            ]
        )

    def test_get_commits(self):
        """Testing Gerrit.get_commits"""
        payload = self._make_json_rsp([
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
        ])

        with self.setup_http_test(payload=payload,
                                  expected_http_calls=1) as ctx:
            commits = ctx.service.get_commits(ctx.create_repository())

        ctx.assertHTTPCall(
            0,
            url='http://gerrit.example.com/a/projects/Project/all-commits/')

        self.assertEqual(
            commits,
            [
                Commit(author_name='David Trowbridge',
                       id='77c174669b7018936f16b98547445624c6738e1e',
                       date='2016-09-05T23:28:30-07:00',
                       message='Backport a fix for screenshot commenting.\n',
                       parent='ecfbf578d31f550a135580cee26fa20fbaea36d9'),
                Commit(author_name='David Trowbridge',
                       id='8a39b87f0124f27225234014a87914e434b223a9',
                       date='2016-09-05T22:58:29-07:00',
                       message='Fix some issues with screenshot commenting.\n',
                       parent='3fb32c83993cd8c07fbbb605cf0cc523010da7c8'),
                Commit(author_name='David Trowbridge',
                       id='3fb32c83993cd8c07fbbb605cf0cc523010da7c8',
                       date='2016-09-05T22:47:55-07:00',
                       message='Fix draggability of the comment dialog.\n',
                       parent='7619f51371b55bfcdf4cb3fccf5d3c76bf5002c0'),
            ])

        for commit in commits:
            self.assertIsNone(commit.diff)

    def test_get_change(self):
        """Testing Gerrit.get_change"""
        revision = '77c174669b7018936f16b98547445624c6738e1e'
        paths = {
            '/a/projects/Project/commits/%s/diff/' % revision: {
                'payload': b'fake diff',
            },
            '/a/projects/Project/all-commits/': {
                'payload': self._make_json_rsp([{
                    'message': 'Backport a fix for screenshot '
                               'commenting.\n',
                    'revision': '77c174669b7018936f16b98547445624c6738e1e',
                    'author': 'David Trowbridge',
                    'parents': [
                        'ecfbf578d31f550a135580cee26fa20fbaea36d9',
                    ],
                    'time': '2016-09-05T23:28:30-07:00',
                }]),
            },
        }

        with self.setup_http_test(self.make_handler_for_paths(paths),
                                  expected_http_calls=2) as ctx:
            commit = ctx.service.get_change(
                repository=ctx.create_repository(),
                revision='77c174669b7018936f16b98547445624c6738e1e')

        self.assertEqual(
            commit,
            Commit(author_name='David Trowbridge',
                   id='77c174669b7018936f16b98547445624c6738e1e',
                   date='2016-09-05T23:28:30-07:00',
                   message='Backport a fix for screenshot commenting.\n',
                   parent='ecfbf578d31f550a135580cee26fa20fbaea36d9'))
        self.assertEqual(commit.diff, b'fake diff')

        ctx.assertHTTPCall(
            0,
            url=('http://gerrit.example.com/a/projects/Project/all-commits/'
                 '?start=77c174669b7018936f16b98547445624c6738e1e&limit=1'))

        ctx.assertHTTPCall(
            1,
            url=('http://gerrit.example.com/a/projects/Project/commits/'
                 '77c174669b7018936f16b98547445624c6738e1e/diff/'))

    def _make_json_rsp(self, data):
        """Return a Gerrit JSON response payload for the given data.

        Args:
            data (object):
                The data to serialize.

        Returns:
            bytes:
            The serialized payload data.
        """
        return b")]}'\n%s" % self.dump_json(data)
