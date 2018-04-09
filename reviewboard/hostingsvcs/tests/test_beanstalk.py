"""Unit tests for the Beanstalk hosting service."""

from __future__ import unicode_literals

from django.utils.six.moves.urllib.error import HTTPError

from reviewboard.hostingsvcs.tests.testcases import ServiceTests
from reviewboard.scmtools.models import Repository, Tool


class BeanstalkTests(ServiceTests):
    """Unit tests for the Beanstalk hosting service."""

    service_name = 'beanstalk'
    fixtures = ['test_scmtools']

    def test_service_support(self):
        """Testing Beanstalk service support capabilities"""
        self.assertFalse(self.service_class.supports_bug_trackers)
        self.assertTrue(self.service_class.supports_repositories)

    def test_get_repository_fields_for_git(self):
        """Testing Beanstalk.get_repository_fields for Git"""
        self.assertEqual(
            self.get_repository_fields(
                'Git',
                fields={
                    'beanstalk_account_domain': 'mydomain',
                    'beanstalk_repo_name': 'myrepo',
                }
            ),
            {
                'path': 'git@mydomain.beanstalkapp.com:/mydomain/myrepo.git',
                'mirror_path': ('https://mydomain.git.beanstalkapp.com/'
                                'myrepo.git'),
            })

    def test_get_repository_fields_for_subversion(self):
        """Testing Beanstalk.get_repository_fields for Subversion"""
        self.assertEqual(
            self.get_repository_fields(
                'Subversion',
                fields={
                    'beanstalk_account_domain': 'mydomain',
                    'beanstalk_repo_name': 'myrepo',
                }
            ),
            {
                'path': 'https://mydomain.svn.beanstalkapp.com/myrepo/',
            })

    def test_authorize(self):
        """Testing Beanstalk.authorize"""
        account = self._get_hosting_account()
        service = account.service

        self.assertFalse(service.is_authorized())

        service.authorize('myuser', 'abc123', None)

        self.assertIn('password', account.data)
        self.assertNotEqual(account.data['password'], 'abc123')
        self.assertTrue(service.is_authorized())

    def test_check_repository(self):
        """Testing Beanstalk.check_repository"""
        def _http_get(service, url, *args, **kwargs):
            self.assertEqual(
                url,
                'https://mydomain.beanstalkapp.com/api/repositories/'
                'myrepo.json')
            return '{}', {}

        account = self._get_hosting_account()
        service = account.service

        service.authorize('myuser', 'abc123', None)

        self.spy_on(service.client.http_get, call_fake=_http_get)

        service.check_repository(beanstalk_account_domain='mydomain',
                                 beanstalk_repo_name='myrepo')
        self.assertTrue(service.client.http_get.called)

    def test_get_file_with_svn_and_base_commit_id(self):
        """Testing Beanstalk.get_file with Subversion and base commit ID"""
        self._test_get_file(
            tool_name='Subversion',
            revision='123',
            base_commit_id='456',
            expected_revision='123')

    def test_get_file_with_svn_and_revision(self):
        """Testing Beanstalk.get_file with Subversion and revision"""
        self._test_get_file(
            tool_name='Subversion',
            revision='123',
            base_commit_id=None,
            expected_revision='123')

    def test_get_file_with_git_and_base_commit_id(self):
        """Testing Beanstalk.get_file with Git and base commit ID"""
        self._test_get_file(
            tool_name='Git',
            revision='123',
            base_commit_id='456',
            expected_revision='123')

    def test_get_file_with_git_and_revision(self):
        """Testing Beanstalk.get_file with Git and revision"""
        self._test_get_file(
            tool_name='Git',
            revision='123',
            base_commit_id=None,
            expected_revision='123')

    def test_get_file_exists_with_svn_and_base_commit_id(self):
        """Testing Beanstalk.get_file_exists with Subversion and base commit ID
        """
        self._test_get_file_exists(
            tool_name='Subversion',
            revision='123',
            base_commit_id='456',
            expected_revision='123',
            expected_found=True)

    def test_get_file_exists_with_svn_and_revision(self):
        """Testing Beanstalk.get_file_exists with Subversion and revision"""
        self._test_get_file_exists(
            tool_name='Subversion',
            revision='123',
            base_commit_id=None,
            expected_revision='123',
            expected_found=True)

    def test_get_file_exists_with_git_and_base_commit_id(self):
        """Testing Beanstalk.get_file_exists with Git and base commit ID"""
        self._test_get_file_exists(
            tool_name='Git',
            revision='123',
            base_commit_id='456',
            expected_revision='456',
            expected_found=True)

    def test_get_file_exists_with_git_and_revision(self):
        """Testing Beanstalk.get_file_exists with Git and revision"""
        self._test_get_file_exists(
            tool_name='Git',
            revision='123',
            base_commit_id=None,
            expected_revision='123',
            expected_found=True)

    def _test_get_file(self, tool_name, revision, base_commit_id,
                       expected_revision):
        """Test file fetching.

        Args:
            tool_name (unicode):
                The name of the SCM Tool to test with.

            revision (unicode, optional):
                The revision to check.

            base_commit_id (unicode, optional):
                The base commit to fetch against.

            expected_revision (unicode, optional):
                The revision expected in the payload.
        """
        def _http_get(service, url, *args, **kwargs):
            if tool_name == 'Git':
                self.assertEqual(
                    url,
                    'https://mydomain.beanstalkapp.com/api/repositories/'
                    'myrepo/blob?id=%s&name=path'
                    % expected_revision)
                payload = b'My data'
            else:
                self.assertEqual(
                    url,
                    'https://mydomain.beanstalkapp.com/api/repositories/'
                    'myrepo/node.json?path=/path&revision=%s&contents=true'
                    % expected_revision)
                payload = b'{"contents": "My data"}'

            return payload, {}

        account = self._get_hosting_account()
        service = account.service
        repository = Repository(hosting_account=account,
                                tool=Tool.objects.get(name=tool_name))
        repository.extra_data = {
            'beanstalk_account_domain': 'mydomain',
            'beanstalk_repo_name': 'myrepo',
        }

        service.authorize('myuser', 'abc123', None)

        self.spy_on(service.client.http_get, call_fake=_http_get)

        result = service.get_file(repository, '/path', revision,
                                  base_commit_id)
        self.assertTrue(service.client.http_get.called)
        self.assertIsInstance(result, bytes)
        self.assertEqual(result, b'My data')

    def _test_get_file_exists(self, tool_name, revision, base_commit_id,
                              expected_revision, expected_found):
        """Test file existence checks.

        Args:
            tool_name (unicode):
                The name of the SCM Tool to test with.

            revision (unicode, optional):
                The revision to check.

            base_commit_id (unicode, optional):
                The base commit to fetch against.

            expected_revision (unicode, optional):
                The revision expected in the payload.

            expected_found (bool, optional):
                Whether a truthy response should be expected.
        """
        def _http_get(service, url, *args, **kwargs):
            expected_url = ('https://mydomain.beanstalkapp.com/api/'
                            'repositories/myrepo/')

            if not base_commit_id and tool_name == 'Git':
                expected_url += 'blob?id=%s&name=path' % expected_revision
            else:
                expected_url += ('node.json?path=/path&revision=%s'
                                 % expected_revision)

            self.assertEqual(url, expected_url)

            if expected_found:
                return b'{}', {}
            else:
                raise HTTPError()

        account = self._get_hosting_account()
        service = account.service
        repository = Repository(hosting_account=account,
                                tool=Tool.objects.get(name=tool_name))
        repository.extra_data = {
            'beanstalk_account_domain': 'mydomain',
            'beanstalk_repo_name': 'myrepo',
        }

        service.authorize('myuser', 'abc123', None)

        self.spy_on(service.client.http_get, call_fake=_http_get)

        result = service.get_file_exists(repository, '/path', revision,
                                         base_commit_id)
        self.assertTrue(service.client.http_get.called)
        self.assertEqual(result, expected_found)
