"""Unit tests for the Codebase HQ hosting service."""

from __future__ import unicode_literals

from django.utils import six

from reviewboard.hostingsvcs.errors import RepositoryError
from reviewboard.hostingsvcs.testing import HostingServiceTestCase
from reviewboard.scmtools.crypto_utils import (decrypt_password,
                                               encrypt_password)
from reviewboard.scmtools.errors import FileNotFoundError


class CodebaseHQTests(HostingServiceTestCase):
    """Unit tests for the Codebase HQ hosting service."""

    service_name = 'codebasehq'
    fixtures = ['test_scmtools']

    default_account_data = {
        'domain': 'mydomain',
        'api_key': encrypt_password('abc123'),
        'password': encrypt_password(HostingServiceTestCase.default_password),
    }

    default_repository_extra_data = {
        'codebasehq_project_name': 'myproj',
        'codebasehq_repo_name': 'myrepo',
    }

    def test_service_support(self):
        """Testing CodebaseHQ service support capabilities"""
        self.assertFalse(self.service_class.supports_post_commit)
        self.assertTrue(self.service_class.supports_bug_trackers)
        self.assertTrue(self.service_class.supports_repositories)

    def test_get_repository_fields_for_git(self):
        """Testing CodebaseHQ.get_repository_fields for Git"""
        self.assertEqual(
            self.get_repository_fields(
                'Git',
                fields={
                    'codebasehq_project_name': 'myproj',
                    'codebasehq_repo_name': 'myrepo',
                }
            ),
            {
                'path': 'git@codebasehq.com:mydomain/myproj/myrepo.git',
            })

    def test_get_repository_fields_for_mercurial(self):
        """Testing CodebaseHQ.get_repository_fields for Mercurial"""
        self.assertEqual(
            self.get_repository_fields(
                'Mercurial',
                fields={
                    'codebasehq_project_name': 'myproj',
                    'codebasehq_repo_name': 'myrepo',
                }
            ),
            {
                'path': ('https://mydomain.codebasehq.com/projects/'
                         'myproj/repositories/myrepo/'),
            })

    def test_get_repository_fields_for_subversion(self):
        """Testing CodebaseHQ.get_repository_fields for Subversion"""
        self.assertEqual(
            self.get_repository_fields(
                'Subversion',
                fields={
                    'codebasehq_project_name': 'myproj',
                    'codebasehq_repo_name': 'myrepo',
                }
            ),
            {
                'path': 'https://mydomain.codebasehq.com/myproj/myrepo.svn',
            })

    def test_get_bug_tracker_field(self):
        """Testing CodebaseHQ.get_bug_tracker_field"""
        self.assertEqual(
            self.service_class.get_bug_tracker_field(
                None,
                {
                    'codebasehq_project_name': 'myproj',
                    'domain': 'mydomain',
                }),
            'https://mydomain.codebasehq.com/projects/myproj/tickets/%s')

    def test_check_repository_git(self):
        """Testing CodebaseHQ.check_repository for Git"""
        self._test_check_repository(codebase_scm_type='git',
                                    tool_name='Git')

    def test_check_repository_mercurial(self):
        """Testing CodebaseHQ.check_repository for Mercurial"""
        self._test_check_repository(codebase_scm_type='hg',
                                    tool_name='Mercurial')

    def test_check_repository_subversion(self):
        """Testing CodebaseHQ.check_repository for Subversion"""
        self._test_check_repository(codebase_scm_type='svn',
                                    tool_name='Subversion')

    def test_check_repository_with_mismatching_type(self):
        """Testing CodebaseHQ.check_repository with mismatching repository type
        """
        self._test_check_repository(codebase_scm_type='svn',
                                    tool_name='Mercurial',
                                    expect_success=False,
                                    expected_name_for_error='Subversion')

    def test_authorize(self):
        """Testing CodebaseHQ.authorize"""
        hosting_account = self.create_hosting_account(data={})

        with self.setup_http_test(payload=b'{}',
                                  hosting_account=hosting_account,
                                  expected_http_calls=1) as ctx:
            self.assertFalse(ctx.service.is_authorized())

            ctx.service.authorize(
                username='myuser',
                password='mypass',
                credentials={
                    'domain': 'mydomain',
                    'api_key': 'abc123',
                })

        ctx.assertHTTPCall(
            0,
            url='https://api3.codebasehq.com/users/myuser/public_keys',
            username='mydomain/myuser',
            password='abc123',
            headers={
                'Accept': 'application/xml',
            })

        self.assertEqual(set(six.iterkeys(hosting_account.data)),
                         {'api_key', 'domain', 'password'})
        self.assertEqual(decrypt_password(hosting_account.data['api_key']),
                         'abc123')
        self.assertEqual(hosting_account.data['domain'], 'mydomain')
        self.assertEqual(decrypt_password(hosting_account.data['password']),
                         'mypass')
        self.assertTrue(ctx.service.is_authorized())

    def test_get_file_with_mercurial(self):
        """Testing CodebaseHQ.get_file with Mercurial"""
        self._test_get_file(tool_name='Mercurial')

    def test_get_file_with_mercurial_not_found(self):
        """Testing CodebaseHQ.get_file with Mercurial with file not found"""
        self._test_get_file(tool_name='Mercurial', file_exists=False)

    def test_get_file_with_git(self):
        """Testing CodebaseHQ.get_file with Git"""
        self._test_get_file(tool_name='Git', expect_git_blob_url=True)

    def test_get_file_with_git_not_found(self):
        """Testing CodebaseHQ.get_file with Git with file not found"""
        self._test_get_file(tool_name='Git', expect_git_blob_url=True,
                            file_exists=False)

    def test_get_file_with_subversion(self):
        """Testing CodebaseHQ.get_file with Subversion"""
        self._test_get_file(tool_name='Subversion')

    def test_get_file_with_subversion_not_found(self):
        """Testing CodebaseHQ.get_file with Subversion with file not found"""
        self._test_get_file(tool_name='Subversion', file_exists=False)

    def test_get_file_exists_with_mercurial(self):
        """Testing CodebaseHQ.get_file_exists with Mercurial"""
        self._test_get_file_exists(tool_name='Mercurial')

    def test_get_file_exists_with_mercurial_not_found(self):
        """Testing CodebaseHQ.get_file_exists with Mercurial with file not
        found
        """
        self._test_get_file_exists(tool_name='Mercurial', file_exists=False)

    def test_get_file_exists_with_git(self):
        """Testing CodebaseHQ.get_file_exists with Git"""
        self._test_get_file_exists(tool_name='Git', expect_git_blob_url=True)

    def test_get_file_exists_with_git_not_found(self):
        """Testing CodebaseHQ.get_file_exists with Git with file not found"""
        self._test_get_file_exists(tool_name='Git', expect_git_blob_url=True,
                                   file_exists=False)

    def test_get_file_exists_with_subversion(self):
        """Testing CodebaseHQ.get_file_exists with Subversion"""
        self._test_get_file_exists(tool_name='Subversion')

    def test_get_file_exists_with_subversion_not_found(self):
        """Testing CodebaseHQ.get_file_exists with Subversion with file not
        found
        """
        self._test_get_file_exists(tool_name='Subversion', file_exists=False)

    def _test_check_repository(self, codebase_scm_type, tool_name,
                               expect_success=True,
                               expected_name_for_error=None):
        """Test repository checks.

        Args:
            codebase_scm_type (unicode):
                The name of the SCM type in the CodebaseHQ API to return in
                payloads.

            tool_name (unicode):
                The name of the SCM Tool to test with.

            expect_success (bool, optional):
                Whether to simulate a truthy response.

            expected_name_for_error (unicode, optional):
                The name of the SCM Tool to expect in the error response,
                if ``expect_success`` is ``False``.
        """
        payload = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<repository>\n'
            ' <scm>%s</scm>\n'
            '</repository>\n'
            % codebase_scm_type
        ).encode('utf-8')

        check_repository_kwargs = {
            'codebasehq_project_name': 'myproj',
            'codebasehq_repo_name': 'myrepo',
            'tool_name': tool_name,
        }

        with self.setup_http_test(payload=payload,
                                  expected_http_calls=1) as ctx:
            if expect_success:
                ctx.service.check_repository(**check_repository_kwargs)
            else:
                message = (
                    "The repository type doesn't match what you selected. Did "
                    "you mean %s?"
                    % expected_name_for_error
                )

                with self.assertRaisesMessage(RepositoryError, message):
                    ctx.service.check_repository(**check_repository_kwargs)

        ctx.assertHTTPCall(
            0,
            url='https://api3.codebasehq.com/myproj/myrepo',
            username='mydomain/myuser',
            password='abc123',
            headers={
                'Accept': 'application/xml',
            })

    def _test_get_file(self, tool_name, expect_git_blob_url=False,
                       file_exists=True):
        """Test file fetching.

        Args:
            tool_name (unicode):
                The name of the SCM Tool to test with.

            expect_git_blob_url (bool, optional):
                Whether to expect a URL referencing a Git blob.

            file_exists (bool, optional):
                Whether to simulate a truthy response.
        """
        if expect_git_blob_url:
            expected_url = 'https://api3.codebasehq.com/myproj/myrepo/blob/123'
        else:
            expected_url = \
                'https://api3.codebasehq.com/myproj/myrepo/blob/123/myfile'

        if file_exists:
            payload = b'My data\n'
            status_code = None
        else:
            payload = b''
            status_code = 404

        with self.setup_http_test(payload=payload,
                                  status_code=status_code,
                                  expected_http_calls=1) as ctx:
            repository = ctx.create_repository(tool_name=tool_name)

            get_file_kwargs = {
                'repository': repository,
                'path': 'myfile',
                'revision': '123',
            }

            if file_exists:
                result = ctx.service.get_file(**get_file_kwargs)

                self.assertIsInstance(result, bytes)
                self.assertEqual(result, b'My data\n')
            else:
                with self.assertRaises(FileNotFoundError):
                    ctx.service.get_file(**get_file_kwargs)

        ctx.assertHTTPCall(
            0,
            url=expected_url,
            username='mydomain/myuser',
            password='abc123',
            headers={
                'Accept': 'application/xml',
            })

    def _test_get_file_exists(self, tool_name, expect_git_blob_url=False,
                              file_exists=True):
        """Test file existence checks.

        Args:
            tool_name (unicode):
                The name of the SCM Tool to test with.

            expect_git_blob_url (bool, optional):
                Whether to expect a URL referencing a Git blob.

            file_exists (bool, optional):
                Whether to simulate a truthy response.
        """
        if file_exists:
            payload = b'{"scm": "git"}'
            status_code = None
        else:
            payload = None
            status_code = 404

        with self.setup_http_test(payload=payload,
                                  status_code=status_code,
                                  expected_http_calls=1) as ctx:
            repository = ctx.create_repository(tool_name=tool_name)
            result = ctx.service.get_file_exists(repository=repository,
                                                 path='myfile',
                                                 revision='123')

            self.assertEqual(result, file_exists)

        if expect_git_blob_url:
            expected_url = 'https://api3.codebasehq.com/myproj/myrepo/blob/123'
        else:
            expected_url = \
                'https://api3.codebasehq.com/myproj/myrepo/blob/123/myfile'

        ctx.assertHTTPCall(
            0,
            url=expected_url,
            username='mydomain/myuser',
            password='abc123',
            body=None,
            headers={
                'Accept': 'application/xml',
            })
