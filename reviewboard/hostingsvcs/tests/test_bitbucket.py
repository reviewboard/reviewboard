"""Unit tests for the Bitbucket hosting service."""

from __future__ import unicode_literals

import json

from django.utils.six.moves import cStringIO as StringIO
from django.utils.six.moves.urllib.error import HTTPError
from django.utils.six.moves.urllib.parse import parse_qs, urlparse
from djblets.testing.decorators import add_fixtures

from reviewboard.hostingsvcs.errors import (AuthorizationError,
                                            RepositoryError)
from reviewboard.hostingsvcs.tests.testcases import ServiceTests
from reviewboard.reviews.models import ReviewRequest
from reviewboard.scmtools.core import Branch, Commit
from reviewboard.scmtools.crypto_utils import encrypt_password
from reviewboard.scmtools.errors import FileNotFoundError
from reviewboard.scmtools.models import Repository, Tool
from reviewboard.site.models import LocalSite
from reviewboard.site.urlresolvers import local_site_reverse


class BitbucketTestCase(ServiceTests):
    """Base class for Bitbucket test suites."""

    service_name = 'bitbucket'
    fixtures = ['test_scmtools']


class BitbucketTests(BitbucketTestCase):
    """Unit tests for the Bitbucket hosting service."""

    def test_service_support(self):
        """Testing Bitbucket service support capabilities"""
        self.assertTrue(self.service_class.supports_bug_trackers)
        self.assertTrue(self.service_class.supports_repositories)

    def test_get_repository_fields_with_git_and_personal_plan(self):
        """Testing Bitbucket.get_repository_fields for Git and plan=personal"""
        self.assertEqual(
            self.get_repository_fields(
                'Git',
                fields={
                    'bitbucket_repo_name': 'myrepo',
                },
                plan='personal'
            ),
            {
                'path': 'git@bitbucket.org:myuser/myrepo.git',
                'mirror_path': ('https://myuser@bitbucket.org/myuser/'
                                'myrepo.git'),
            })

    def test_get_repository_fields_with_mercurial_and_personal_plan(self):
        """Testing Bitbucket.get_repository_fields for Mercurial and
        plan=personal
        """
        self.assertEqual(
            self.get_repository_fields(
                'Mercurial',
                fields={
                    'bitbucket_repo_name': 'myrepo',
                },
                plan='personal'
            ),
            {
                'path': 'https://myuser@bitbucket.org/myuser/myrepo',
                'mirror_path': 'ssh://hg@bitbucket.org/myuser/myrepo',
            })

    def test_get_repository_fields_with_git_and_team_plan(self):
        """Testing Bitbucket.get_repository_fields for Git and plan=team"""
        self.assertEqual(
            self.get_repository_fields(
                'Git',
                fields={
                    'bitbucket_team_name': 'myteam',
                    'bitbucket_team_repo_name': 'myrepo',
                },
                plan='team'
            ),
            {
                'path': 'git@bitbucket.org:myteam/myrepo.git',
                'mirror_path': ('https://myuser@bitbucket.org/myteam/'
                                'myrepo.git'),
            })

    def test_get_repository_fields_with_mercurial_and_team_plan(self):
        """Testing Bitbucket.get_repository_fields for Mercurial and plan=team
        """
        self.assertEqual(
            self.get_repository_fields(
                'Mercurial',
                fields={
                    'bitbucket_team_name': 'myteam',
                    'bitbucket_team_repo_name': 'myrepo',
                },
                plan='team'
            ),
            {
                'path': 'https://myuser@bitbucket.org/myteam/myrepo',
                'mirror_path': 'ssh://hg@bitbucket.org/myteam/myrepo',
            })

    def test_get_repository_fields_with_git_and_other_user_plan(self):
        """Testing Bitbucket.get_repository_fields for Git and plan=other-user
        """
        self.assertEqual(
            self.get_repository_fields(
                'Git',
                fields={
                    'bitbucket_other_user_username': 'someuser',
                    'bitbucket_other_user_repo_name': 'myrepo',
                },
                plan='other-user'
            ),
            {
                'path': 'git@bitbucket.org:someuser/myrepo.git',
                'mirror_path': ('https://myuser@bitbucket.org/someuser/'
                                'myrepo.git'),
            })

    def test_get_repository_fields_with_mercurial_and_other_user_plan(self):
        """Testing Bitbucket.get_repository_fields for Mercurial and
        plan=other-user
        """
        self.assertEqual(
            self.get_repository_fields(
                'Mercurial',
                fields={
                    'bitbucket_other_user_username': 'someuser',
                    'bitbucket_other_user_repo_name': 'myrepo',
                },
                plan='other-user'
            ),
            {
                'path': 'https://myuser@bitbucket.org/someuser/myrepo',
                'mirror_path': 'ssh://hg@bitbucket.org/someuser/myrepo',
            })

    def test_get_bug_tracker_field_with_personal_plan(self):
        """Testing Bitbucket.get_bug_tracker_field with plan=personal"""
        self.assertTrue(self.service_class.get_bug_tracker_requires_username(
            plan='personal'))
        self.assertEqual(
            self.service_class.get_bug_tracker_field(
                'personal',
                {
                    'bitbucket_repo_name': 'myrepo',
                    'hosting_account_username': 'myuser',
                }),
            'https://bitbucket.org/myuser/myrepo/issue/%s/')

    def test_get_bug_tracker_field_with_team_plan(self):
        """Testing Bitbucket.get_bug_tracker_field with plan=team"""
        self.assertFalse(self.service_class.get_bug_tracker_requires_username(
            plan='team'))
        self.assertEqual(
            self.service_class.get_bug_tracker_field(
                'team',
                {
                    'bitbucket_team_name': 'myteam',
                    'bitbucket_team_repo_name': 'myrepo',
                }),
            'https://bitbucket.org/myteam/myrepo/issue/%s/')

    def test_get_bug_tracker_field_with_other_user_plan(self):
        """Testing Bitbucket.get_bug_tracker_field with plan=other-user"""
        self.assertFalse(self.service_class.get_bug_tracker_requires_username(
            plan='other-user'))
        self.assertEqual(
            self.service_class.get_bug_tracker_field(
                'other-user',
                {
                    'bitbucket_other_user_username': 'someuser',
                    'bitbucket_other_user_repo_name': 'myrepo',
                }),
            'https://bitbucket.org/someuser/myrepo/issue/%s/')

    def test_check_repository_with_personal_plan(self):
        """Testing Bitbucket.check_repository with plan=personal"""
        def _http_get(service, url, *args, **kwargs):
            self.assertEqual(
                url,
                'https://bitbucket.org/api/2.0/repositories/myuser/myrepo'
                '?fields=scm')
            return (
                json.dumps({
                    'scm': 'git',
                }),
                {})

        account = self._get_hosting_account()
        account.data['password'] = encrypt_password('abc123')
        service = account.service

        self.spy_on(service.client.http_get, call_fake=_http_get)

        service.check_repository(bitbucket_repo_name='myrepo',
                                 plan='personal',
                                 tool_name='Git')
        self.assertTrue(service.client.http_get.called)

    def test_check_repository_with_team_plan(self):
        """Testing Bitbucket.check_repository with plan=team"""
        def _http_get(service, url, *args, **kwargs):
            self.assertEqual(
                url,
                'https://bitbucket.org/api/2.0/repositories/myteam/myrepo'
                '?fields=scm')
            return (
                json.dumps({
                    'scm': 'git',
                }),
                {})

        account = self._get_hosting_account()
        service = account.service

        account.data['password'] = encrypt_password('abc123')

        self.spy_on(service.client.http_get, call_fake=_http_get)

        service.check_repository(bitbucket_team_name='myteam',
                                 bitbucket_team_repo_name='myrepo',
                                 tool_name='Git',
                                 plan='team')
        self.assertTrue(service.client.http_get.called)

    def test_check_repository_with_other_user_plan(self):
        """Testing Bitbucket.check_repository with plan=other-user"""
        def _http_get(service, url, *args, **kwargs):
            self.assertEqual(
                url,
                'https://bitbucket.org/api/2.0/repositories/someuser/myrepo'
                '?fields=scm')
            return (
                json.dumps({
                    'scm': 'git',
                }),
                {})

        account = self._get_hosting_account()
        service = account.service

        account.data['password'] = encrypt_password('abc123')

        self.spy_on(service.client.http_get, call_fake=_http_get)

        service.check_repository(bitbucket_other_user_username='someuser',
                                 bitbucket_other_user_repo_name='myrepo',
                                 plan='other-user',
                                 tool_name='Git')
        self.assertTrue(service.client.http_get.called)

    def test_check_repository_with_slash(self):
        """Testing Bitbucket.check_repository with /"""
        account = self._get_hosting_account()
        account.data['password'] = encrypt_password('abc123')
        service = account.service

        expected_message = \
            'Please specify just the name of the repository, not a path.'

        with self.assertRaisesMessage(RepositoryError, expected_message):
            service.check_repository(
                bitbucket_team_name='myteam',
                bitbucket_team_repo_name='myteam/myrepo',
                plan='team')

    def test_check_repository_with_dot_git(self):
        """Testing Bitbucket.check_repository with .git"""
        account = self._get_hosting_account()
        account.data['password'] = encrypt_password('abc123')
        service = account.service

        expected_message = \
            'Please specify just the name of the repository without ".git".'

        with self.assertRaisesMessage(RepositoryError, expected_message):
            service.check_repository(
                bitbucket_team_name='myteam',
                bitbucket_team_repo_name='myrepo.git',
                plan='team')

    def test_check_repository_with_type_mismatch(self):
        """Testing Bitbucket.check_repository with type mismatch"""
        error_message = (
            'The Bitbucket repository being configured does not match the '
            'type of repository you have selected.'
        )
        repository_type = 'git'

        def _http_get(service, url, *args, **kwargs):
            self.assertEqual(
                url,
                'https://bitbucket.org/api/2.0/repositories/myteam/myrepo'
                '?fields=scm')
            return (
                json.dumps({
                    'scm': repository_type,
                }),
                {})

        account = self._get_hosting_account()
        service = account.service
        account.data['password'] = encrypt_password('abc123')

        self.spy_on(service.client.http_get, call_fake=_http_get)

        # Check Git repositories.
        with self.assertRaisesMessage(RepositoryError, error_message):
            service.check_repository(
                bitbucket_team_name='myteam',
                bitbucket_team_repo_name='myrepo',
                plan='team',
                tool_name='Mercurial')

        # Now check Mercurial repositories.
        repository_type = 'hg'

        with self.assertRaisesMessage(RepositoryError, error_message):
            service.check_repository(
                bitbucket_team_name='myteam',
                bitbucket_team_repo_name='myrepo',
                plan='team',
                tool_name='Git')

    def test_authorize(self):
        """Testing Bitbucket.authorize"""
        def _http_get(self, *args, **kwargs):
            return '{}', {}

        account = self._get_hosting_account()
        service = account.service

        self.spy_on(service.client.http_get, call_fake=_http_get)

        self.assertFalse(service.is_authorized())

        service.authorize('myuser', 'abc123', None)

        self.assertIn('password', account.data)
        self.assertNotEqual(account.data['password'], 'abc123')
        self.assertTrue(service.is_authorized())

    def test_authorize_with_bad_credentials(self):
        """Testing Bitbucket.authorize with bad credentials"""
        def _http_get(service, url, *args, **kwargs):
            raise HTTPError(url, 401, '', {}, StringIO(''))

        account = self._get_hosting_account()
        service = account.service

        self.spy_on(service.client.http_get, call_fake=_http_get)

        self.assertFalse(service.is_authorized())

        expected_message = (
            'Invalid Bitbucket username or password. Make sure you are using '
            'your Bitbucket username and not e-mail address, and are using an '
            'app password if two-factor authentication is enabled.'
        )

        with self.assertRaisesMessage(AuthorizationError, expected_message):
            service.authorize('myuser', 'abc123', None)

        self.assertNotIn('password', account.data)
        self.assertFalse(service.is_authorized())

    def test_authorize_with_403(self):
        """Testing Bitbucket.authorize with HTTP 403 result"""
        def _http_get(service, url, *args, **kwargs):
            raise HTTPError(url, 403, '', {}, StringIO(''))

        account = self._get_hosting_account()
        service = account.service

        self.spy_on(service.client.http_get, call_fake=_http_get)

        self.assertFalse(service.is_authorized())

        expected_message = (
            'Invalid Bitbucket username or password. Make sure you are using '
            'your Bitbucket username and not e-mail address, and are using '
            'an app password if two-factor authentication is enabled.'
        )

        with self.assertRaisesMessage(AuthorizationError, expected_message):
            service.authorize('myuser', 'abc123', None)

        self.assertNotIn('password', account.data)
        self.assertFalse(service.is_authorized())

    def test_get_file_with_mercurial_and_base_commit_id(self):
        """Testing Bitbucket.get_file with Mercurial and base commit ID"""
        self._test_get_file(
            tool_name='Mercurial',
            revision='123',
            base_commit_id='456',
            expected_revision='456')

    def test_get_file_with_mercurial_and_revision(self):
        """Testing Bitbucket.get_file with Mercurial and revision"""
        self._test_get_file(
            tool_name='Mercurial',
            revision='123',
            base_commit_id=None,
            expected_revision='123')

    def test_get_file_with_git_and_base_commit_id(self):
        """Testing Bitbucket.get_file with Git and base commit ID"""
        self._test_get_file(
            tool_name='Git',
            revision='123',
            base_commit_id='456',
            expected_revision='456')

    def test_get_file_with_git_and_revision(self):
        """Testing Bitbucket.get_file with Git and revision"""
        with self.assertRaises(FileNotFoundError):
            self._test_get_file(tool_name='Git',
                                revision='123',
                                base_commit_id=None,
                                expected_revision='123')

    def test_get_file_exists_with_mercurial_and_base_commit_id(self):
        """Testing Bitbucket.get_file_exists with Mercurial and base commit ID
        """
        self._test_get_file_exists(
            tool_name='Mercurial',
            revision='123',
            base_commit_id='456',
            expected_revision='456',
            expected_found=True)

    def test_get_file_exists_with_mercurial_and_revision(self):
        """Testing Bitbucket.get_file_exists with Mercurial and revision"""
        self._test_get_file_exists(
            tool_name='Mercurial',
            revision='123',
            base_commit_id=None,
            expected_revision='123',
            expected_found=True)

    def test_get_file_exists_with_git_and_base_commit_id(self):
        """Testing Bitbucket.get_file_exists with Git and base commit ID"""
        self._test_get_file_exists(
            tool_name='Git',
            revision='123',
            base_commit_id='456',
            expected_revision='456',
            expected_found=True)

    def test_get_file_exists_with_git_and_revision(self):
        """Testing Bitbucket.get_file_exists with Git and revision"""
        self._test_get_file_exists(
            tool_name='Git',
            revision='123',
            base_commit_id=None,
            expected_revision='123',
            expected_found=False,
            expected_http_called=False)

    def test_get_file_exists_with_git_and_404(self):
        """Testing BitBucket.get_file_exists with Git and a 404 error"""
        self._test_get_file_exists(
            tool_name='Git',
            revision='123',
            base_commit_id='456',
            expected_revision='456',
            expected_found=False)

    def test_get_branches(self):
        """Testing Bitbucket.get_branches"""
        branches_api_response_1 = json.dumps({
            'next': ('https://bitbucket.org/api/2.0/repositories/myuser/'
                     'myrepo/refs/branches?pagelen=100&page=2&'
                     'fields=values.name%2Cvalues.target.hash%2Cnext'),
            'values': [
                {
                    'name': 'branch1',
                    'target': {
                        'hash': '1c44b461cebe5874a857c51a4a13a849a4d1e52d',
                    },
                },
                {
                    'name': 'branch2',
                    'target': {
                        'hash': '44568f7d33647d286691517e6325fea5c7a21d5e',
                    },
                },
            ],
        })

        branches_api_response_2 = json.dumps({
            'values': [
                {
                    'name': 'branch3',
                    'target': {
                        'hash': 'e5874a857c51a4a13a849a4d1e52d1c44b461ceb',
                    },
                },
                {
                    'name': 'branch4',
                    'target': {
                        'hash': 'd286691517e6325fea5c7a21d5e44568f7d33647',
                    },
                },
            ],
        })

        get_repository_api_response = json.dumps({
            'mainbranch': {
                'name': 'branch3',
            },
        })

        def _http_get(service, url, *args, **kwargs):
            url_parts = urlparse(url)
            path = url_parts.path
            query = parse_qs(url_parts.query)

            if path == '/api/2.0/repositories/myuser/myrepo/':
                self.assertEqual(
                    query,
                    {
                        'fields': ['mainbranch.name'],
                    })

                return get_repository_api_response, None
            elif path == '/api/2.0/repositories/myuser/myrepo/refs/branches':
                if 'page' in query:
                    self.assertEqual(
                        query,
                        {
                            'fields': ['values.name,values.target.hash,next'],
                            'pagelen': ['100'],
                            'page': ['2'],
                        })

                    return branches_api_response_2, None
                else:
                    self.assertEqual(
                        query,
                        {
                            'fields': ['values.name,values.target.hash,next'],
                            'pagelen': ['100'],
                        })

                    return branches_api_response_1, None
            else:
                self.fail('Unexpected URL %s' % url)

        account = self._get_hosting_account()
        service = account.service
        repository = Repository(hosting_account=account,
                                tool=Tool.objects.get(name='Git'))
        repository.extra_data = {
            'bitbucket_repo_name': 'myrepo',
        }

        account.data['password'] = encrypt_password('abc123')

        self.spy_on(service.client.http_get, call_fake=_http_get)

        branches = service.get_branches(repository)
        self.assertEqual(
            branches,
            [
                Branch(id='branch1',
                       commit='1c44b461cebe5874a857c51a4a13a849a4d1e52d'),
                Branch(id='branch2',
                       commit='44568f7d33647d286691517e6325fea5c7a21d5e'),
                Branch(id='branch3',
                       commit='e5874a857c51a4a13a849a4d1e52d1c44b461ceb',
                       default=True),
                Branch(id='branch4',
                       commit='d286691517e6325fea5c7a21d5e44568f7d33647'),
            ])

    def test_get_commits(self):
        """Testing Bitbucket.get_commits"""
        commits_api_response = json.dumps({
            'values': [
                {
                    'hash': '1c44b461cebe5874a857c51a4a13a849a4d1e52d',
                    'author': {
                        'raw': 'Some User 1 <user1@example.com>',
                    },
                    'date': '2017-01-24T13:11:22+00:00',
                    'message': 'This is commit 1.',
                    'parents': [
                        {
                            'hash': '44568f7d33647d286691517e6325fea5c7a21d5e',
                        },
                    ],
                },
                {
                    'hash': '44568f7d33647d286691517e6325fea5c7a21d5e',
                    'author': {
                        'raw': 'Some User 2 <user2@example.com>',
                    },
                    'date': '2017-01-23T08:09:10+00:00',
                    'message': 'This is commit 2.',
                    'parents': [
                        {
                            'hash': 'e5874a857c51a4a13a849a4d1e52d1c44b461ceb',
                        },
                    ],
                },
            ],
        })

        def _http_get(service, url, *args, **kwargs):
            url_parts = urlparse(url)
            path = url_parts.path
            query = parse_qs(url_parts.query)

            if path == '/api/2.0/repositories/myuser/myrepo/commits':
                self.assertEqual(
                    query,
                    {
                        'pagelen': ['20'],
                        'fields': ['values.author.raw,values.hash,'
                                   'values.date,values.message,'
                                   'values.parents.hash'],
                    })

                return commits_api_response, None
            else:
                self.fail('Unexpected URL %s' % url)

        account = self._get_hosting_account()
        service = account.service
        repository = Repository(hosting_account=account,
                                tool=Tool.objects.get(name='Git'))
        repository.extra_data = {
            'bitbucket_repo_name': 'myrepo',
        }

        account.data['password'] = encrypt_password('abc123')

        self.spy_on(service.client.http_get, call_fake=_http_get)

        commits = service.get_commits(repository)
        self.assertEqual(
            commits,
            [
                Commit(author_name='Some User 1 <user1@example.com>',
                       date='2017-01-24T13:11:22+00:00',
                       id='1c44b461cebe5874a857c51a4a13a849a4d1e52d',
                       message='This is commit 1.',
                       parent='44568f7d33647d286691517e6325fea5c7a21d5e'),
                Commit(author_name='Some User 2 <user2@example.com>',
                       date='2017-01-23T08:09:10+00:00',
                       id='44568f7d33647d286691517e6325fea5c7a21d5e',
                       message='This is commit 2.',
                       parent='e5874a857c51a4a13a849a4d1e52d1c44b461ceb'),
            ])

        for commit in commits:
            self.assertIsNone(commit.diff)

    def test_get_change(self):
        """Testing BitBucket.get_change"""
        commit_sha = '1c44b461cebe5874a857c51a4a13a849a4d1e52d'
        parent_sha = '44568f7d33647d286691517e6325fea5c7a21d5e'

        commits_api_response = json.dumps({
            'hash': commit_sha,
            'author': {
                'raw': 'Some User <user@example.com>',
            },
            'date': '2017-01-24T13:11:22+00:00',
            'message': 'This is a message.',
            'parents': [{'hash': parent_sha}],
        })

        diff_api_response = b'This is a test \xc7.'
        norm_diff_api_response = b'This is a test \xc7.\n'

        def _http_get(service, url, *args, **kwargs):
            if url == ('https://bitbucket.org/api/2.0/repositories/'
                       'myuser/myrepo/commit/%s?'
                       'fields=author.raw%%2Chash%%2Cdate%%2C'
                       'message%%2Cparents.hash'
                       % commit_sha):
                return commits_api_response, None
            elif url == ('https://bitbucket.org/api/2.0/repositories/'
                         'myuser/myrepo/diff/%s' % commit_sha):
                return diff_api_response, None
            else:
                self.fail('Unexpected URL %s' % url)

        account = self._get_hosting_account()
        service = account.service
        repository = Repository(hosting_account=account,
                                tool=Tool.objects.get(name='Git'))
        repository.extra_data = {
            'bitbucket_repo_name': 'myrepo',
        }

        account.data['password'] = encrypt_password('abc123')

        self.spy_on(service.client.http_get, call_fake=_http_get)

        commit = service.get_change(repository, commit_sha)

        self.assertEqual(
            commit,
            Commit(author_name='Some User <user@example.com>',
                   date='2017-01-24T13:11:22+00:00',
                   id=commit_sha,
                   message='This is a message.',
                   parent=parent_sha))
        self.assertEqual(commit.diff, norm_diff_api_response)

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
            self.assertEqual(
                url,
                'https://bitbucket.org/api/1.0/repositories/'
                'myuser/myrepo/raw/%s/path'
                % expected_revision)
            return b'My data', {}

        account = self._get_hosting_account()
        service = account.service
        repository = Repository(hosting_account=account,
                                tool=Tool.objects.get(name=tool_name))
        repository.extra_data = {
            'bitbucket_repo_name': 'myrepo',
        }

        account.data['password'] = encrypt_password('abc123')

        self.spy_on(service.client.http_get, call_fake=_http_get)

        result = service.get_file(repository, 'path', revision,
                                  base_commit_id)
        self.assertTrue(service.client.http_get.called)
        self.assertIsInstance(result, bytes)
        self.assertEqual(result, b'My data')

    def _test_get_file_exists(self, tool_name, revision, base_commit_id,
                              expected_revision, expected_found,
                              expected_http_called=True):
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

            expected_http_called (bool, optional):
                Whether an HTTP request is expected to have been made.
        """
        def _http_get(service, url, *args, **kwargs):
            self.assertEqual(
                url,
                'https://bitbucket.org/api/1.0/repositories/'
                'myuser/myrepo/raw/%s/path'
                % expected_revision)

            if expected_found:
                return b'{}', {}
            else:
                error = HTTPError(url, 404, 'Not Found', {}, None)
                error.read = lambda: error.msg
                raise error

        account = self._get_hosting_account()
        service = account.service
        repository = Repository(hosting_account=account,
                                tool=Tool.objects.get(name=tool_name))
        repository.extra_data = {
            'bitbucket_repo_name': 'myrepo',
        }

        account.data['password'] = encrypt_password('abc123')

        self.spy_on(service.client.http_get, call_fake=_http_get)

        result = service.get_file_exists(repository, 'path', revision,
                                         base_commit_id)
        self.assertEqual(service.client.http_get.called, expected_http_called)
        self.assertEqual(result, expected_found)


class CloseSubmittedHookTests(BitbucketTestCase):
    """Unit tests for the Bitbucket close-submitted webhook."""

    fixtures = ['test_users', 'test_scmtools']

    def test_close_submitted_hook(self):
        """Testing BitBucket close_submitted hook"""
        self._test_post_commit_hook()

    @add_fixtures(['test_site'])
    def test_close_submitted_hook_with_local_site(self):
        """Testing BitBucket close_submitted hook with a Local Site"""
        self._test_post_commit_hook(
            LocalSite.objects.get(name=self.local_site_name))

    def test_close_submitted_hook_with_invalid_repo(self):
        """Testing BitBucket close_submitted hook with invalid repository"""
        repository = self.create_repository()

        review_request = self.create_review_request(repository=repository,
                                                    publish=True)
        self.assertTrue(review_request.public)
        self.assertEqual(review_request.status, review_request.PENDING_REVIEW)

        url = local_site_reverse(
            'bitbucket-hooks-close-submitted',
            kwargs={
                'repository_id': repository.pk,
                'hosting_service_id': 'bitbucket',
                'hooks_uuid': repository.get_or_create_hooks_uuid(),
            })

        response = self._post_commit_hook_payload(url, review_request)
        self.assertEqual(response.status_code, 404)

        review_request = ReviewRequest.objects.get(pk=review_request.pk)
        self.assertTrue(review_request.public)
        self.assertEqual(review_request.status, review_request.PENDING_REVIEW)
        self.assertEqual(review_request.changedescs.count(), 0)

    @add_fixtures(['test_site'])
    def test_close_submitted_hook_with_invalid_site(self):
        """Testing BitBucket close_submitted hook with invalid Local Site"""
        local_site = LocalSite.objects.get(name=self.local_site_name)
        account = self._get_hosting_account(local_site=local_site)
        account.save()

        repository = self.create_repository(hosting_account=account,
                                            local_site=local_site)

        review_request = self.create_review_request(repository=repository,
                                                    publish=True)
        self.assertTrue(review_request.public)
        self.assertEqual(review_request.status, review_request.PENDING_REVIEW)

        url = local_site_reverse(
            'bitbucket-hooks-close-submitted',
            local_site_name='badsite',
            kwargs={
                'repository_id': repository.pk,
                'hosting_service_id': 'bitbucket',
                'hooks_uuid': repository.get_or_create_hooks_uuid(),
            })

        response = self._post_commit_hook_payload(url, review_request)
        self.assertEqual(response.status_code, 404)

        review_request = ReviewRequest.objects.get(pk=review_request.pk)
        self.assertTrue(review_request.public)
        self.assertEqual(review_request.status, review_request.PENDING_REVIEW)
        self.assertEqual(review_request.changedescs.count(), 0)

    def test_close_submitted_hook_with_invalid_service_id(self):
        """Testing BitBucket close_submitted hook with invalid hosting
        service ID
        """
        # We'll test against GitHub for this test.
        account = self._get_hosting_account()
        account.service_name = 'github'
        account.save()
        repository = self.create_repository(hosting_account=account)

        review_request = self.create_review_request(repository=repository,
                                                    publish=True)
        self.assertTrue(review_request.public)
        self.assertEqual(review_request.status, review_request.PENDING_REVIEW)

        url = local_site_reverse(
            'bitbucket-hooks-close-submitted',
            kwargs={
                'repository_id': repository.pk,
                'hosting_service_id': 'bitbucket',
                'hooks_uuid': repository.get_or_create_hooks_uuid(),
            })

        response = self._post_commit_hook_payload(url, review_request)
        self.assertEqual(response.status_code, 404)

        review_request = ReviewRequest.objects.get(pk=review_request.pk)
        self.assertTrue(review_request.public)
        self.assertEqual(review_request.status, review_request.PENDING_REVIEW)
        self.assertEqual(review_request.changedescs.count(), 0)

    def _test_post_commit_hook(self, local_site=None):
        """Testing posting to a commit hook.

        This will simulate pushing a commit and posting the resulting webhook
        payload from Bitbucket to the handler for the hook.

        Args:
            local_site (reviewboard.site.models.LocalSite, optional):
                The Local Site owning the review request.
        """
        account = self._get_hosting_account(local_site=local_site)
        account.save()

        repository = self.create_repository(hosting_account=account,
                                            local_site=local_site)

        review_request = self.create_review_request(repository=repository,
                                                    local_site=local_site,
                                                    publish=True)
        self.assertTrue(review_request.public)
        self.assertEqual(review_request.status, review_request.PENDING_REVIEW)

        url = local_site_reverse(
            'bitbucket-hooks-close-submitted',
            local_site=local_site,
            kwargs={
                'repository_id': repository.pk,
                'hosting_service_id': 'bitbucket',
                'hooks_uuid': repository.get_or_create_hooks_uuid(),
            })

        self._post_commit_hook_payload(url, review_request)

        review_request = ReviewRequest.objects.get(pk=review_request.pk)
        self.assertTrue(review_request.public)
        self.assertEqual(review_request.status, review_request.SUBMITTED)
        self.assertEqual(review_request.changedescs.count(), 1)

        changedesc = review_request.changedescs.get()
        self.assertEqual(changedesc.text, 'Pushed to master (1c44b46)')

    def _post_commit_hook_payload(self, url, review_request):
        """Post a payload for a hook for testing.

        Args:
            url (unicode):
                The URL to post to.

            review_request (reviewboard.reviews.models.review_request.
                            ReviewRequest):
                The review request being represented in the payload.

        Results:
            django.core.handlers.request.wsgi.WSGIRequest:
            The post request.
        """
        return self.client.post(
            url,
            data={
                'payload': json.dumps({
                    # NOTE: This payload only contains the content we make
                    #       use of in the hook.
                    'commits': [
                        {
                            'raw_node': '1c44b461cebe5874a857c51a4a13a84'
                                        '9a4d1e52d',
                            'branch': 'master',
                            'message': 'This is my fancy commit\n'
                                       '\n'
                                       'Reviewed at http://example.com%s'
                                       % review_request.get_absolute_url(),
                        },
                    ]
                }),
            })
