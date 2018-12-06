"""Unit tests for the Bitbucket hosting service."""

from __future__ import unicode_literals

from djblets.testing.decorators import add_fixtures

from reviewboard.hostingsvcs.bitbucket import Bitbucket
from reviewboard.hostingsvcs.errors import (AuthorizationError,
                                            RepositoryError)
from reviewboard.hostingsvcs.testing import HostingServiceTestCase
from reviewboard.reviews.models import ReviewRequest
from reviewboard.scmtools.core import Branch, Commit
from reviewboard.scmtools.crypto_utils import (decrypt_password,
                                               encrypt_password)
from reviewboard.scmtools.errors import FileNotFoundError
from reviewboard.site.models import LocalSite
from reviewboard.site.urlresolvers import local_site_reverse


class BitbucketTestCase(HostingServiceTestCase):
    """Base class for Bitbucket test suites."""

    service_name = 'bitbucket'
    fixtures = ['test_scmtools']

    default_account_data = {
        'password': encrypt_password(HostingServiceTestCase.default_password),
    }

    default_repository_extra_data = {
        'bitbucket_repo_name': 'myrepo',
    }


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
        with self.setup_http_test(payload=b'{"scm": "git"}',
                                  expected_http_calls=1) as ctx:
            ctx.service.check_repository(bitbucket_repo_name='myrepo',
                                         plan='personal',
                                         tool_name='Git')

        ctx.assertHTTPCall(
            0,
            url=('https://bitbucket.org/api/2.0/repositories/myuser/myrepo'
                 '?fields=scm'))

    def test_check_repository_with_team_plan(self):
        """Testing Bitbucket.check_repository with plan=team"""
        with self.setup_http_test(payload=b'{"scm": "git"}',
                                  expected_http_calls=1) as ctx:
            ctx.service.check_repository(bitbucket_team_name='myteam',
                                         bitbucket_team_repo_name='myrepo',
                                         tool_name='Git',
                                         plan='team')

        ctx.assertHTTPCall(
            0,
            url=('https://bitbucket.org/api/2.0/repositories/myteam/myrepo'
                 '?fields=scm'))

    def test_check_repository_with_other_user_plan(self):
        """Testing Bitbucket.check_repository with plan=other-user"""
        with self.setup_http_test(payload=b'{"scm": "git"}',
                                  expected_http_calls=1) as ctx:
            ctx.service.check_repository(
                bitbucket_other_user_username='someuser',
                bitbucket_other_user_repo_name='myrepo',
                plan='other-user',
                tool_name='Git')

        ctx.assertHTTPCall(
            0,
            url=('https://bitbucket.org/api/2.0/repositories/someuser/myrepo'
                 '?fields=scm'))

    def test_check_repository_with_slash(self):
        """Testing Bitbucket.check_repository with /"""
        expected_message = \
            'Please specify just the name of the repository, not a path.'

        with self.setup_http_test(expected_http_calls=0) as ctx:
            with self.assertRaisesMessage(RepositoryError, expected_message):
                ctx.service.check_repository(
                    bitbucket_team_name='myteam',
                    bitbucket_team_repo_name='myteam/myrepo',
                    plan='team')

    def test_check_repository_with_dot_git(self):
        """Testing Bitbucket.check_repository with .git"""
        expected_message = \
            'Please specify just the name of the repository without ".git".'

        with self.setup_http_test(expected_http_calls=0) as ctx:
            with self.assertRaisesMessage(RepositoryError, expected_message):
                ctx.service.check_repository(
                    bitbucket_team_name='myteam',
                    bitbucket_team_repo_name='myrepo.git',
                    plan='team')

    def test_check_repository_with_type_mismatch(self):
        """Testing Bitbucket.check_repository with type mismatch"""
        error_message = (
            'The Bitbucket repository being configured does not match the '
            'type of repository you have selected.'
        )

        with self.setup_http_test(payload=b'{"scm": "git"}',
                                  expected_http_calls=1) as ctx:
            # Check Git repositories.
            with self.assertRaisesMessage(RepositoryError, error_message):
                ctx.service.check_repository(
                    bitbucket_team_name='myteam',
                    bitbucket_team_repo_name='myrepo',
                    plan='team',
                    tool_name='Mercurial')

        ctx.assertHTTPCall(
            0,
            url=('https://bitbucket.org/api/2.0/repositories/myteam/myrepo'
                 '?fields=scm'))

        # Now check Mercurial repositories.
        with self.setup_http_test(payload=b'{"scm": "hg"}',
                                  expected_http_calls=1) as ctx:
            with self.assertRaisesMessage(RepositoryError, error_message):
                ctx.service.check_repository(
                    bitbucket_team_name='myteam',
                    bitbucket_team_repo_name='myrepo',
                    plan='team',
                    tool_name='Git')

        ctx.assertHTTPCall(
            0,
            url=('https://bitbucket.org/api/2.0/repositories/myteam/myrepo'
                 '?fields=scm'))

    def test_authorize(self):
        """Testing Bitbucket.authorize"""
        hosting_account = self.create_hosting_account(data={})

        with self.setup_http_test(payload=b'{}',
                                  hosting_account=hosting_account,
                                  expected_http_calls=1) as ctx:
            self.assertFalse(ctx.service.is_authorized())
            ctx.service.authorize(username='myuser',
                                  password='abc123')

        self.assertIn('password', hosting_account.data)
        self.assertNotEqual(hosting_account.data['password'], 'abc123')
        self.assertEqual(decrypt_password(hosting_account.data['password']),
                         'abc123')
        self.assertTrue(ctx.service.is_authorized())

        ctx.assertHTTPCall(
            0,
            url='https://bitbucket.org/api/2.0/user',
            username='myuser',
            password='abc123')

    def test_authorize_with_bad_credentials(self):
        """Testing Bitbucket.authorize with bad credentials"""
        hosting_account = self.create_hosting_account(data={})
        expected_message = (
            'Invalid Bitbucket username or password. Make sure you are using '
            'your Bitbucket username and not e-mail address, and are using an '
            'app password if two-factor authentication is enabled.'
        )

        with self.setup_http_test(status_code=401,
                                  hosting_account=hosting_account,
                                  expected_http_calls=1) as ctx:
            self.assertFalse(ctx.service.is_authorized())

            with self.assertRaisesMessage(AuthorizationError,
                                          expected_message):
                ctx.service.authorize(username='myuser',
                                      password='abc123')

        self.assertNotIn('password', hosting_account.data)
        self.assertFalse(ctx.service.is_authorized())

        ctx.assertHTTPCall(
            0,
            url='https://bitbucket.org/api/2.0/user',
            username='myuser',
            password='abc123')

    def test_authorize_with_403(self):
        """Testing Bitbucket.authorize with HTTP 403 result"""
        hosting_account = self.create_hosting_account(data={})
        expected_message = (
            'Invalid Bitbucket username or password. Make sure you are using '
            'your Bitbucket username and not e-mail address, and are using '
            'an app password if two-factor authentication is enabled.'
        )

        with self.setup_http_test(status_code=403,
                                  hosting_account=hosting_account,
                                  expected_http_calls=1) as ctx:
            self.assertFalse(ctx.service.is_authorized())

            with self.assertRaisesMessage(AuthorizationError,
                                          expected_message):
                ctx.service.authorize(username='myuser',
                                      password='abc123')

        self.assertNotIn('password', hosting_account.data)
        self.assertFalse(ctx.service.is_authorized())

        ctx.assertHTTPCall(
            0,
            url='https://bitbucket.org/api/2.0/user',
            username='myuser',
            password='abc123')

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
        branches_api_response_1 = self.dump_json({
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

        branches_api_response_2 = self.dump_json({
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

        get_repository_api_response = self.dump_json({
            'mainbranch': {
                'name': 'branch3',
            },
        })

        paths = {
            '/api/2.0/repositories/myuser/myrepo/': {
                'payload': get_repository_api_response,
            },
            ('/api/2.0/repositories/myuser/myrepo/refs/branches'
             '?pagelen=100&fields=values.name%2Cvalues.target.hash%2Cnext'): {
                 'payload': branches_api_response_1,
            },
            ('/api/2.0/repositories/myuser/myrepo/refs/branches'
             '?pagelen=100&page=2&fields=values.name%2Cvalues.target.hash'
             '%2Cnext'): {
                 'payload': branches_api_response_2,
            },
        }

        with self.setup_http_test(self.make_handler_for_paths(paths),
                                  expected_http_calls=3) as ctx:
            repository = self.create_repository(tool_name='Git')
            branches = ctx.service.get_branches(repository)

        ctx.assertHTTPCall(
            0,
            url=('https://bitbucket.org/api/2.0/repositories/myuser/myrepo/'
                 '?fields=mainbranch.name'))

        ctx.assertHTTPCall(
            1,
            url=('https://bitbucket.org/api/2.0/repositories/myuser/myrepo/'
                 'refs/branches?pagelen=100&fields=values.name'
                 '%2Cvalues.target.hash%2Cnext'))

        ctx.assertHTTPCall(
            2,
            url=('https://bitbucket.org/api/2.0/repositories/myuser/myrepo/'
                 'refs/branches?pagelen=100&page=2&fields=values.name'
                 '%2Cvalues.target.hash%2Cnext'))

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
        payload = self.dump_json({
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

        with self.setup_http_test(payload=payload,
                                  expected_http_calls=1) as ctx:
            repository = ctx.create_repository(tool_name='Git')
            commits = ctx.service.get_commits(repository)

        ctx.assertHTTPCall(
            0,
            url=('https://bitbucket.org/api/2.0/repositories/myuser/myrepo/'
                 'commits?pagelen=20&fields=values.author.raw%2Cvalues.hash'
                 '%2Cvalues.date%2Cvalues.message%2Cvalues.parents.hash'))

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

        paths = {
            '/api/2.0/repositories/myuser/myrepo/commit/%s' % commit_sha: {
                'payload': self.dump_json({
                    'hash': commit_sha,
                    'author': {
                        'raw': 'Some User <user@example.com>',
                    },
                    'date': '2017-01-24T13:11:22+00:00',
                    'message': 'This is a message.',
                    'parents': [{'hash': parent_sha}],
                }),
            },
            '/api/2.0/repositories/myuser/myrepo/diff/%s' % commit_sha: {
                'payload': b'This is a test \xc7.',
            },
        }

        with self.setup_http_test(self.make_handler_for_paths(paths),
                                  expected_http_calls=2) as ctx:
            repository = ctx.create_repository(tool_name='Git')
            commit = ctx.service.get_change(repository, commit_sha)

        ctx.assertHTTPCall(
            0,
            url=('https://bitbucket.org/api/2.0/repositories/myuser/myrepo/'
                 'commit/1c44b461cebe5874a857c51a4a13a849a4d1e52d'
                 '?fields=author.raw%2Chash%2Cdate%2Cmessage%2Cparents.hash'))

        ctx.assertHTTPCall(
            1,
            url=('https://bitbucket.org/api/2.0/repositories/myuser/myrepo/'
                 'diff/1c44b461cebe5874a857c51a4a13a849a4d1e52d'))

        self.assertEqual(
            commit,
            Commit(author_name='Some User <user@example.com>',
                   date='2017-01-24T13:11:22+00:00',
                   id=commit_sha,
                   message='This is a message.',
                   parent=parent_sha))
        self.assertEqual(commit.diff, b'This is a test \xc7.\n')

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
        with self.setup_http_test(payload=b'My data',
                                  expected_http_calls=1) as ctx:
            repository = ctx.create_repository(tool_name=tool_name)
            result = ctx.service.get_file(repository=repository,
                                          path='path',
                                          revision=revision,
                                          base_commit_id=base_commit_id)

        ctx.assertHTTPCall(
            0,
            url=('https://bitbucket.org/api/1.0/repositories/myuser/myrepo/'
                 'raw/%s/path'
                 % expected_revision))

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
        if expected_found:
            payload = b'{}'
            status_code = None
        else:
            payload = b'Not Found'
            status_code = 404

        if expected_http_called:
            expected_calls = 1
        else:
            expected_calls = 0

        with self.setup_http_test(payload=payload,
                                  status_code=status_code,
                                  expected_http_calls=expected_calls) as ctx:
            repository = ctx.create_repository(tool_name=tool_name)
            result = ctx.service.get_file_exists(repository=repository,
                                                 path='path',
                                                 revision=revision,
                                                 base_commit_id=base_commit_id)

        if expected_http_called:
            ctx.assertHTTPCall(
                0,
                url=('https://bitbucket.org/api/1.0/repositories/myuser/'
                     'myrepo/raw/%s/path'
                     % expected_revision))

        self.assertEqual(result, expected_found)


class CloseSubmittedHookTests(BitbucketTestCase):
    """Unit tests for the Bitbucket close-submitted webhook."""

    fixtures = ['test_users', 'test_scmtools']

    COMMITS_URL = ('https://api.bitbucket.org/2.0/repositories/test/test/'
                   'commits?include=abc123&exclude=def456')

    def test_close_submitted_hook(self):
        """Testing BitBucket close_submitted hook"""
        self._test_post_commit_hook()

    @add_fixtures(['test_site'])
    def test_close_submitted_hook_with_local_site(self):
        """Testing BitBucket close_submitted hook with a Local Site"""
        self._test_post_commit_hook(
            LocalSite.objects.get(name=self.local_site_name))

    def test_close_submitted_hook_with_truncated_commits(self):
        """Testing BitBucket close_submitted hook with truncated list of
        commits
        """
        def _api_get(service, url, **kwargs):
            page2_url = '%s&page=2' % self.COMMITS_URL

            if url == self.COMMITS_URL:
                return {
                    'next': page2_url,
                    'values': [
                        {
                            'hash': '1c44b461cebe5874a857c51a4a13a84'
                                    '9a4d1e52d',
                            'message': 'This is my fancy commit.\n'
                                       '\n'
                                       'Reviewed at http://example.com%s'
                                       % review_request1.get_absolute_url(),
                        },
                    ],
                }
            elif url == page2_url:
                return {
                    'values': [
                        {
                            'hash': '9fad89712ebe5874a857c5112a3c9d1'
                                    '87ada0dbc',
                            'message': 'This is another commit\n'
                                       '\n'
                                       'Reviewed at http://example.com%s'
                                       % review_request2.get_absolute_url(),
                        },
                    ],
                }
            else:
                self.fail('Unexpected commits URL "%s"' % url)

        self.spy_on(Bitbucket.api_get, call_fake=_api_get)

        account = self.create_hosting_account()
        repository = self.create_repository(hosting_account=account)

        # Create two review requests: One per referenced commit.
        review_request1 = self.create_review_request(id=99,
                                                     repository=repository,
                                                     publish=True)
        self.assertTrue(review_request1.public)
        self.assertEqual(review_request1.status,
                         review_request1.PENDING_REVIEW)

        review_request2 = self.create_review_request(id=100,
                                                     repository=repository,
                                                     publish=True)
        self.assertTrue(review_request2.public)
        self.assertEqual(review_request2.status,
                         review_request2.PENDING_REVIEW)

        # Simulate the webhook.
        url = local_site_reverse(
            'bitbucket-hooks-close-submitted',
            kwargs={
                'repository_id': repository.pk,
                'hosting_service_id': 'bitbucket',
                'hooks_uuid': repository.get_or_create_hooks_uuid(),
            })

        self._post_commit_hook_payload(url, review_request1,
                                       truncated=True)

        # There should have been two API requests.
        self.assertEqual(len(Bitbucket.api_get.calls), 2)

        # Check the first review request.
        #
        # The first review request has an entry in the truncated list and the
        # fetched list. We'll make sure we've only processed it once.
        review_request1 = ReviewRequest.objects.get(pk=review_request1.pk)
        self.assertTrue(review_request1.public)
        self.assertEqual(review_request1.status, review_request1.SUBMITTED)
        self.assertEqual(review_request1.changedescs.count(), 1)

        changedesc = review_request1.changedescs.get()
        self.assertEqual(changedesc.text, 'Pushed to master (1c44b46)')

        # Check the first review request.
        review_request2 = ReviewRequest.objects.get(pk=review_request2.pk)
        self.assertTrue(review_request2.public)
        self.assertEqual(review_request2.status, review_request2.SUBMITTED)
        self.assertEqual(review_request2.changedescs.count(), 1)

        changedesc = review_request2.changedescs.get()
        self.assertEqual(changedesc.text, 'Pushed to master (9fad897)')

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
        account = self.create_hosting_account(local_site=local_site)
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
        account = self.create_hosting_account()
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
        account = self.create_hosting_account(local_site=local_site)
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

    def _post_commit_hook_payload(self, url, review_request, truncated=False):
        """Post a payload for a hook for testing.

        Args:
            url (unicode):
                The URL to post to.

            review_request (reviewboard.reviews.models.review_request.
                            ReviewRequest):
                The review request being represented in the payload.

            truncated (bool, optional):
                Whether the commit list should be marked truncated.

        Results:
            django.core.handlers.request.wsgi.WSGIRequest:
            The post request.
        """
        return self.client.post(
            url,
            content_type='application/json',
            data=self.dump_json({
                # NOTE: This payload only contains the content we make
                #       use of in the hook.
                'push': {
                    'changes': [{
                        'new': {
                            'type': 'branch',
                            'name': 'master',
                        },
                        'truncated': truncated,
                        'commits': [
                            {
                                'hash': '1c44b461cebe5874a857c51a4a13a84'
                                        '9a4d1e52d',
                                'message': 'This is my fancy commit\n'
                                           '\n'
                                           'Reviewed at http://example.com%s'
                                           % review_request.get_absolute_url(),
                            },
                        ],
                        'links': {
                            'commits': {
                                'href': self.COMMITS_URL,
                            },
                        },
                    }],
                }
            }))
