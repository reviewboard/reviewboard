"""Unit tests for the Codebase HQ hosting service."""

from __future__ import unicode_literals

from django.utils.six.moves import cStringIO as StringIO
from django.utils.six.moves.urllib.error import HTTPError

from reviewboard.hostingsvcs.errors import RepositoryError
from reviewboard.hostingsvcs.tests.testcases import ServiceTests
from reviewboard.scmtools.crypto_utils import decrypt_password
from reviewboard.scmtools.errors import FileNotFoundError
from reviewboard.scmtools.models import Repository, Tool


class CodebaseHQTests(ServiceTests):
    """Unit tests for the Codebase HQ hosting service."""

    service_name = 'codebasehq'
    fixtures = ['test_scmtools']

    def test_service_support(self):
        """Testing CodebaseHQ service support capabilities"""
        self.assertFalse(self.service_class.supports_post_commit)
        self.assertTrue(self.service_class.supports_bug_trackers)
        self.assertTrue(self.service_class.supports_repositories)

    def test_get_repository_fields_for_git(self):
        """Testing CodebaseHQ.get_repository_fields for Git"""
        hosting_account = self._get_hosting_account()
        service = hosting_account.service

        self._authorize(service)

        self.assertEqual(
            self.get_repository_fields(
                'Git',
                hosting_account=hosting_account,
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
        hosting_account = self._get_hosting_account()
        service = hosting_account.service

        self._authorize(service)

        self.assertEqual(
            self.get_repository_fields(
                'Mercurial',
                hosting_account=hosting_account,
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
        hosting_account = self._get_hosting_account()
        service = hosting_account.service

        self._authorize(service)

        self.assertEqual(
            self.get_repository_fields(
                'Subversion',
                hosting_account=hosting_account,
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
        account = self._get_hosting_account()
        service = account.service

        self.assertFalse(service.is_authorized())

        self._authorize(service)

        self.assertIn('api_key', account.data)
        self.assertIn('domain', account.data)
        self.assertIn('password', account.data)
        self.assertEqual(decrypt_password(account.data['api_key']),
                         'abc123')
        self.assertEqual(account.data['domain'], 'mydomain')
        self.assertEqual(decrypt_password(account.data['password']),
                         'mypass')
        self.assertTrue(service.is_authorized())

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
        def _http_get(service, url, *args, **kwargs):
            self.assertEqual(
                url,
                'https://api3.codebasehq.com/myproj/myrepo')
            return (
                ('<?xml version="1.0" encoding="UTF-8"?>\n'
                 '<repository>\n'
                 ' <scm>%s</scm>\n'
                 '</repository>\n'
                 % codebase_scm_type),
                {})

        account = self._get_hosting_account()
        service = account.service

        self._authorize(service)

        self.spy_on(service.client.http_get, call_fake=_http_get)

        if expect_success:
            service.check_repository(codebasehq_project_name='myproj',
                                     codebasehq_repo_name='myrepo',
                                     tool_name=tool_name)
        else:
            message = (
                "The repository type doesn't match what you selected. Did "
                "you mean %s?"
                % expected_name_for_error
            )

            with self.assertRaisesMessage(RepositoryError, message):
                service.check_repository(codebasehq_project_name='myproj',
                                         codebasehq_repo_name='myrepo',
                                         tool_name=tool_name)

        self.assertTrue(service.client.http_get.called)

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
        def _http_get(service, url, *args, **kwargs):
            if expect_git_blob_url:
                self.assertEqual(
                    url,
                    'https://api3.codebasehq.com/myproj/myrepo/blob/123')
            else:
                self.assertEqual(
                    url,
                    'https://api3.codebasehq.com/myproj/myrepo/blob/123/'
                    'myfile')

            if file_exists:
                return b'My data\n', {}
            else:
                raise HTTPError(url, 404, '', {}, StringIO())

        account = self._get_hosting_account()
        service = account.service
        repository = Repository(hosting_account=account,
                                tool=Tool.objects.get(name=tool_name))
        repository.extra_data = {
            'codebasehq_project_name': 'myproj',
            'codebasehq_repo_name': 'myrepo',
        }

        self._authorize(service)

        self.spy_on(service.client.http_get, call_fake=_http_get)

        if file_exists:
            result = service.get_file(repository, 'myfile', '123')
            self.assertIsInstance(result, bytes)
            self.assertEqual(result, b'My data\n')
        else:
            with self.assertRaises(FileNotFoundError):
                service.get_file(repository, 'myfile', '123')

        self.assertTrue(service.client.http_get.called)

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
        def _http_get(service, url, *args, **kwargs):
            if expect_git_blob_url:
                self.assertEqual(
                    url,
                    'https://api3.codebasehq.com/myproj/myrepo/blob/123')
            else:
                self.assertEqual(
                    url,
                    'https://api3.codebasehq.com/myproj/myrepo/blob/123/'
                    'myfile')

            if file_exists:
                return b'{}', {}
            else:
                raise HTTPError(url, 404, '', {}, StringIO())

        account = self._get_hosting_account()
        service = account.service
        repository = Repository(hosting_account=account,
                                tool=Tool.objects.get(name=tool_name))
        repository.extra_data = {
            'codebasehq_project_name': 'myproj',
            'codebasehq_repo_name': 'myrepo',
        }

        self._authorize(service)

        self.spy_on(service.client.http_get, call_fake=_http_get)

        result = service.get_file_exists(repository, 'myfile', '123')
        self.assertTrue(service.client.http_get.called)
        self.assertEqual(result, file_exists)

    def _authorize(self, service):
        # Don't perform the call to test the API's credentials.
        self.spy_on(service.client.api_get_public_keys, call_original=False)

        service.authorize('myuser', 'mypass', {
            'domain': 'mydomain',
            'api_key': 'abc123',
        })
