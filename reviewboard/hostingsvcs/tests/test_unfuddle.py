from __future__ import unicode_literals

from django.utils.six.moves.urllib.error import HTTPError

from reviewboard.hostingsvcs.errors import RepositoryError
from reviewboard.hostingsvcs.tests.testcases import ServiceTests
from reviewboard.scmtools.crypto_utils import encrypt_password
from reviewboard.scmtools.errors import FileNotFoundError
from reviewboard.scmtools.models import Repository, Tool


class UnfuddleTests(ServiceTests):
    """Unit tests for the Unfuddle hosting service."""

    service_name = 'unfuddle'
    fixtures = ['test_scmtools']

    def test_service_support(self):
        """Testing Unfuddle service support capabilities"""
        self.assertTrue(self.service_class.supports_bug_trackers)
        self.assertTrue(self.service_class.supports_repositories)

    def test_repo_field_values_git(self):
        """Testing Unfuddle repository field values for Git"""
        fields = self._get_repository_fields('Git', fields={
            'unfuddle_account_domain': 'mydomain',
            'unfuddle_project_id': 1,
            'unfuddle_repo_name': 'myrepo',
        })
        self.assertEqual(
            fields['path'],
            'git@mydomain.unfuddle.com:mydomain/myrepo.git')
        self.assertEqual(
            fields['mirror_path'],
            'https://mydomain.unfuddle.com/git/mydomain_myrepo/')

    def test_repo_field_values_subversion(self):
        """Testing Unfuddle repository field values for Subversion"""
        fields = self._get_repository_fields('Subversion', fields={
            'unfuddle_account_domain': 'mydomain',
            'unfuddle_project_id': 1,
            'unfuddle_repo_name': 'myrepo',
        })
        self.assertEqual(
            fields['path'],
            'https://mydomain.unfuddle.com/svn/mydomain_myrepo')
        self.assertEqual(
            fields['mirror_path'],
            'http://mydomain.unfuddle.com/svn/mydomain_myrepo')

    def test_authorize(self):
        """Testing Unfuddle authorization password storage"""
        def _http_get(service, url, *args, **kwargs):
            self.assertEqual(
                url,
                'https://mydomain.unfuddle.com/api/v1/account/')
            return '{}', {}

        account = self._get_hosting_account()
        service = account.service

        self.assertFalse(service.is_authorized())

        self.spy_on(service.client.http_get, call_fake=_http_get)

        service.authorize('myuser', 'abc123',
                          unfuddle_account_domain='mydomain')

        self.assertIn('password', account.data)
        self.assertNotEqual(account.data['password'], 'abc123')
        self.assertTrue(service.is_authorized())

    def test_check_repository(self):
        """Testing Unfuddle check_repository"""
        def _http_get(service, url, *args, **kwargs):
            self.assertEqual(
                url,
                'https://mydomain.unfuddle.com/api/v1/repositories/')

            return '[{"id": 2, "abbreviation": "myrepo", "system": "git"}]', {}

        account = self._get_hosting_account()
        service = account.service
        account.data['password'] = encrypt_password('password')

        self.spy_on(service.client.http_get, call_fake=_http_get)

        service.check_repository(unfuddle_account_domain='mydomain',
                                 unfuddle_repo_name='myrepo',
                                 tool_name='Git')
        self.assertTrue(service.client.http_get.called)

    def test_check_repository_with_wrong_repo_type(self):
        """Testing Unfuddle check_repository with wrong repo type"""
        def _http_get(service, url, *args, **kwargs):
            self.assertEqual(
                url,
                'https://mydomain.unfuddle.com/api/v1/repositories/')

            return '[{"id": 1, "abbreviation": "myrepo", "system": "svn"}]', {}

        account = self._get_hosting_account()
        service = account.service
        account.data['password'] = encrypt_password('password')

        self.spy_on(service.client.http_get, call_fake=_http_get)

        self.assertRaises(
            RepositoryError,
            lambda: service.check_repository(
                unfuddle_account_domain='mydomain',
                unfuddle_repo_name='myrepo',
                tool_name='Git'))
        self.assertTrue(service.client.http_get.called)

    def test_get_file_with_svn_and_base_commit_id(self):
        """Testing Unfuddle get_file with Subversion and base commit ID"""
        self._test_get_file(
            tool_name='Subversion',
            revision='123',
            base_commit_id='456',
            expected_revision='456')

    def test_get_file_with_svn_and_revision(self):
        """Testing Unfuddle get_file with Subversion and revision"""
        self._test_get_file(
            tool_name='Subversion',
            revision='123',
            base_commit_id=None,
            expected_revision='123')

    def test_get_file_with_git_and_base_commit_id(self):
        """Testing Unfuddle get_file with Git and base commit ID"""
        self._test_get_file(
            tool_name='Git',
            revision='123',
            base_commit_id='456',
            expected_revision='456')

    def test_get_file_with_git_and_revision(self):
        """Testing Unfuddle get_file with Git and revision"""
        self._test_get_file(
            tool_name='Git',
            revision='123',
            base_commit_id=None,
            expected_revision=None,
            expected_error=True)

    def test_get_file_exists_with_svn_and_base_commit_id(self):
        """Testing Unfuddle get_file_exists with Subversion and base commit ID
        """
        self._test_get_file_exists(
            tool_name='Subversion',
            revision='123',
            base_commit_id='456',
            expected_revision='456',
            expected_found=True)

    def test_get_file_exists_with_svn_and_revision(self):
        """Testing Unfuddle get_file_exists with Subversion and revision"""
        self._test_get_file_exists(
            tool_name='Subversion',
            revision='123',
            base_commit_id=None,
            expected_revision='123',
            expected_found=True)

    def test_get_file_exists_with_git_and_base_commit_id(self):
        """Testing Unfuddle get_file_exists with Git and base commit ID"""
        self._test_get_file_exists(
            tool_name='Git',
            revision='123',
            base_commit_id='456',
            expected_revision='456',
            expected_found=True)

    def test_get_file_exists_with_git_and_revision(self):
        """Testing Unfuddle get_file_exists with Git and revision"""
        self._test_get_file_exists(
            tool_name='Git',
            revision='123',
            base_commit_id=None,
            expected_revision=None,
            expected_found=False,
            expected_error=True)

    def _test_get_file(self, tool_name, revision, base_commit_id,
                       expected_revision, expected_error=False):
        def _http_get(service, url, *args, **kwargs):
            self.assertEqual(
                url,
                'https://mydomain.unfuddle.com/api/v1/repositories/2/'
                'download/?path=%s&commit=%s'
                % (path, expected_revision))
            return 'My data', {}

        path = '/path'
        account = self._get_hosting_account()
        service = account.service
        repository = Repository(hosting_account=account,
                                tool=Tool.objects.get(name=tool_name))
        repository.extra_data = {
            'unfuddle_account_domain': 'mydomain',
            'unfuddle_project_id': 1,
            'unfuddle_repo_id': 2,
            'unfuddle_repo_name': 'myrepo',
        }

        account.data['password'] = encrypt_password('password')

        self.spy_on(service.client.http_get, call_fake=_http_get)

        if expected_error:
            self.assertRaises(
                FileNotFoundError,
                lambda: service.get_file(repository, path, revision,
                                         base_commit_id))
            self.assertFalse(service.client.http_get.called)
        else:
            result = service.get_file(repository, path, revision,
                                      base_commit_id)
            self.assertTrue(service.client.http_get.called)
            self.assertEqual(result, 'My data')

    def _test_get_file_exists(self, tool_name, revision, base_commit_id,
                              expected_revision, expected_found=True,
                              expected_error=False):
        def _http_get(service, url, *args, **kwargs):
            self.assertEqual(
                url,
                'https://mydomain.unfuddle.com/api/v1/repositories/2/'
                'history/?path=/path&commit=%s&count=0'
                % expected_revision)

            if expected_found:
                return '{}', {}
            else:
                raise HTTPError()

        account = self._get_hosting_account()
        service = account.service
        repository = Repository(hosting_account=account,
                                tool=Tool.objects.get(name=tool_name))
        repository.extra_data = {
            'unfuddle_account_domain': 'mydomain',
            'unfuddle_project_id': 1,
            'unfuddle_repo_id': 2,
            'unfuddle_repo_name': 'myrepo',
        }

        account.data['password'] = encrypt_password('password')

        self.spy_on(service.client.http_get, call_fake=_http_get)

        result = service.get_file_exists(repository, '/path', revision,
                                         base_commit_id)

        if expected_error:
            self.assertFalse(service.client.http_get.called)
            self.assertFalse(result)
        else:
            self.assertTrue(service.client.http_get.called)
            self.assertEqual(result, expected_found)
