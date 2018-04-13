"""Unit tests for the GitHub hosting service."""

from __future__ import unicode_literals

import hashlib
import hmac
import uuid

from django.core.exceptions import ObjectDoesNotExist
from djblets.testing.decorators import add_fixtures

from reviewboard.scmtools.core import Branch, Commit
from reviewboard.hostingsvcs.errors import RepositoryError
from reviewboard.hostingsvcs.repository import RemoteRepository
from reviewboard.hostingsvcs.testing import HostingServiceTestCase
from reviewboard.reviews.models import ReviewRequest
from reviewboard.scmtools.errors import SCMError
from reviewboard.site.models import LocalSite
from reviewboard.site.urlresolvers import local_site_reverse


class GitHubTestCase(HostingServiceTestCase):
    """Base class for GitHub test suites."""

    service_name = 'github'

    default_account_data = {
        'authorization': {
            'token': 'abc123',
        },
    }

    default_repository_extra_data = {
        'repository_plan': 'public',
        'github_public_repo_name': 'myrepo',
    }


class GitHubTests(GitHubTestCase):
    """Unit tests for the GitHub hosting service."""

    def test_service_support(self):
        """Testing GitHub service support capabilities"""
        self.assertTrue(self.service_class.supports_bug_trackers)
        self.assertTrue(self.service_class.supports_repositories)
        self.assertFalse(self.service_class.supports_ssh_key_association)

    def test_get_repository_fields_with_public_plan(self):
        """Testing GitHub.get_repository_fields with the public plan"""
        self.assertEqual(
            self.get_repository_fields(
                'Git',
                plan='public',
                fields={
                    'github_public_repo_name': 'myrepo',
                }
            ),
            {
                'path': 'git://github.com/myuser/myrepo.git',
                'mirror_path': 'git@github.com:myuser/myrepo.git',
            })

    def test_get_repository_fields_with_public_org_plan(self):
        """Testing GitHub.get_repository_fields with the public-org plan"""
        self.assertEqual(
            self.get_repository_fields(
                'Git',
                plan='public-org',
                fields={
                    'github_public_org_repo_name': 'myrepo',
                    'github_public_org_name': 'myorg',
                }
            ),
            {
                'path': 'git://github.com/myorg/myrepo.git',
                'mirror_path': 'git@github.com:myorg/myrepo.git',
            })

    def test_get_repository_fields_with_private_plan(self):
        """Testing GitHub.get_repository_fields with the private plan"""
        self.assertEqual(
            self.get_repository_fields(
                'Git',
                plan='private',
                fields={
                    'github_private_repo_name': 'myrepo',
                }
            ),
            {
                'path': 'git@github.com:myuser/myrepo.git',
                'mirror_path': '',
            })

    def test_get_repository_fields_with_private_org_plan(self):
        """Testing GitHub.get_repository_fields with the private-org plan"""
        self.assertEqual(
            self.get_repository_fields(
                'Git',
                plan='private-org',
                fields={
                    'github_private_org_repo_name': 'myrepo',
                    'github_private_org_name': 'myorg',
                }
            ),
            {
                'path': 'git@github.com:myorg/myrepo.git',
                'mirror_path': '',
            })

    def test_get_repo_api_url_with_public_plan(self):
        """Testing GitHub._get_repo_api_url with the public plan"""
        url = self._get_repo_api_url('public', {
            'github_public_repo_name': 'testrepo',
        })
        self.assertEqual(url, 'https://api.github.com/repos/myuser/testrepo')

    def test_get_repo_api_url_with_public_org_plan(self):
        """Testing GitHub._get_repo_api_url with the public-org plan"""
        url = self._get_repo_api_url('public-org', {
            'github_public_org_name': 'myorg',
            'github_public_org_repo_name': 'testrepo',
        })
        self.assertEqual(url, 'https://api.github.com/repos/myorg/testrepo')

    def test_get_repo_api_url_with_private_plan(self):
        """Testing GitHub._get_repo_api_url with the private plan"""
        url = self._get_repo_api_url('private', {
            'github_private_repo_name': 'testrepo',
        })
        self.assertEqual(url, 'https://api.github.com/repos/myuser/testrepo')

    def test_get_repo_api_url_with_private_org_plan(self):
        """Testing GitHub._get_repo_api_url with the private-org plan"""
        url = self._get_repo_api_url('private-org', {
            'github_private_org_name': 'myorg',
            'github_private_org_repo_name': 'testrepo',
        })
        self.assertEqual(url, 'https://api.github.com/repos/myorg/testrepo')

    def test_get_bug_tracker_field_with_public_plan(self):
        """Testing GitHub.get_bug_tracker_field with the public plan"""
        self.assertTrue(
            self.service_class.get_bug_tracker_requires_username('public'))
        self.assertEqual(
            self.service_class.get_bug_tracker_field('public', {
                'github_public_repo_name': 'myrepo',
                'hosting_account_username': 'myuser',
            }),
            'http://github.com/myuser/myrepo/issues#issue/%s')

    def test_get_bug_tracker_field_with_public_org_plan(self):
        """Testing GitHub.get_bug_tracker_field with the public-org plan"""
        self.assertFalse(
            self.service_class.get_bug_tracker_requires_username('public-org'))
        self.assertEqual(
            self.service_class.get_bug_tracker_field('public-org', {
                'github_public_org_name': 'myorg',
                'github_public_org_repo_name': 'myrepo',
            }),
            'http://github.com/myorg/myrepo/issues#issue/%s')

    def test_get_bug_tracker_field_with_private_plan(self):
        """Testing GitHub.get_bug_tracker_field with the private plan"""
        self.assertTrue(
            self.service_class.get_bug_tracker_requires_username('private'))
        self.assertEqual(
            self.service_class.get_bug_tracker_field('private', {
                'github_private_repo_name': 'myrepo',
                'hosting_account_username': 'myuser',
            }),
            'http://github.com/myuser/myrepo/issues#issue/%s')

    def test_get_bug_tracker_field_with_private_org_plan(self):
        """Testing GitHub.get_bug_tracker_field with the private-org plan"""
        self.assertFalse(self.service_class.get_bug_tracker_requires_username(
            'private-org'))
        self.assertEqual(
            self.service_class.get_bug_tracker_field('private-org', {
                'github_private_org_name': 'myorg',
                'github_private_org_repo_name': 'myrepo',
            }),
            'http://github.com/myorg/myrepo/issues#issue/%s')

    def test_check_repository_public(self):
        """Testing GitHub.check_repository with public repository"""
        self._test_check_repository(plan='public',
                                    github_public_repo_name='myrepo')

    def test_check_repository_private(self):
        """Testing GitHub.check_repository with private repository"""
        self._test_check_repository(plan='private',
                                    github_private_repo_name='myrepo')

    def test_check_repository_public_org(self):
        """Testing GitHub.check_repository with public org repository"""
        self._test_check_repository(plan='public-org',
                                    github_public_org_name='myorg',
                                    github_public_org_repo_name='myrepo',
                                    expected_owner='myorg')

    def test_check_repository_private_org(self):
        """Testing GitHub.check_repository with private org repository"""
        self._test_check_repository(plan='private-org',
                                    github_private_org_name='myorg',
                                    github_private_org_repo_name='myrepo',
                                    expected_owner='myorg')

    def test_check_repository_public_not_found(self):
        """Testing GitHub.check_repository with not found error and public
        repository
        """
        self._test_check_repository_error(
            plan='public',
            github_public_repo_name='myrepo',
            http_status=404,
            payload=b'{"message": "Not Found"}',
            expected_url='https://api.github.com/repos/myuser/myrepo',
            expected_error='A repository with this name was not found, '
                           'or your user may not own it.')

    def test_check_repository_private_not_found(self):
        """Testing GitHub.check_repository with not found error and private
        repository
        """
        self._test_check_repository_error(
            plan='private',
            github_private_repo_name='myrepo',
            http_status=404,
            payload=b'{"message": "Not Found"}',
            expected_url='https://api.github.com/repos/myuser/myrepo',
            expected_error='A repository with this name was not found, '
                           'or your user may not own it.')

    def test_check_repository_public_org_not_found(self):
        """Testing GitHub.check_repository with not found error and
        public organization repository
        """
        self._test_check_repository_error(
            plan='public-org',
            github_public_org_name='myorg',
            github_public_org_repo_name='myrepo',
            http_status=404,
            payload=b'{"message": "Not Found"}',
            expected_url='https://api.github.com/repos/myorg/myrepo',
            expected_error='A repository with this organization or name '
                           'was not found.')

    def test_check_repository_private_org_not_found(self):
        """Testing GitHub.check_repository with not found error and
        private organization repository
        """
        self._test_check_repository_error(
            plan='private-org',
            github_private_org_name='myorg',
            github_private_org_repo_name='myrepo',
            http_status=404,
            payload=b'{"message": "Not Found"}',
            expected_url='https://api.github.com/repos/myorg/myrepo',
            expected_error='A repository with this organization or name '
                           'was not found, or your user may not have access '
                           'to it.')

    def test_check_repository_public_plan_private_repo(self):
        """Testing GitHub.check_repository with public plan and
        private repository
        """
        self._test_check_repository_error(
            plan='public',
            github_public_repo_name='myrepo',
            http_status=200,
            payload=b'{"private": true}',
            expected_url='https://api.github.com/repos/myuser/myrepo',
            expected_error='This is a private repository, but you have '
                           'selected a public plan.')

    def test_check_repository_private_plan_public_repo(self):
        """Testing GitHub.check_repository with private plan and
        public repository
        """
        self._test_check_repository_error(
            plan='private',
            github_private_repo_name='myrepo',
            http_status=200,
            payload=b'{"private": false}',
            expected_url='https://api.github.com/repos/myuser/myrepo',
            expected_error='This is a public repository, but you have '
                           'selected a private plan.')

    def test_check_repository_public_org_plan_private_repo(self):
        """Testing GitHub.check_repository with public organization plan and
        private repository
        """
        self._test_check_repository_error(
            plan='public-org',
            github_public_org_name='myorg',
            github_public_org_repo_name='myrepo',
            http_status=200,
            payload=b'{"private": true}',
            expected_url='https://api.github.com/repos/myorg/myrepo',
            expected_error='This is a private repository, but you have '
                           'selected a public plan.')

    def test_check_repository_private_org_plan_public_repo(self):
        """Testing GitHub.check_repository with private organization plan and
        public repository
        """
        self._test_check_repository_error(
            plan='private-org',
            github_private_org_name='myorg',
            github_private_org_repo_name='myrepo',
            http_status=200,
            payload=b'{"private": false}',
            expected_url='https://api.github.com/repos/myorg/myrepo',
            expected_error='This is a public repository, but you have '
                           'selected a private plan.')

    def test_authorization(self):
        """Testing GitHub.authorize"""
        payload = self.dump_json({
            'id': 1,
            'url': 'https://api.github.com/authorizations/1',
            'scopes': ['user', 'repo'],
            'token': 'abc123',
            'note': '',
            'note_url': '',
            'updated_at': '2012-05-04T03:30:00Z',
            'created_at': '2012-05-04T03:30:00Z',
        })

        hosting_account = self.create_hosting_account(data={})
        self.assertFalse(hosting_account.is_authorized)

        self.spy_on(
            uuid.uuid4,
            call_fake=lambda: uuid.UUID('2a707f8c6fc14dd590e545ebe1e9b2f6'))

        with self.setup_http_test(payload=payload,
                                  hosting_account=hosting_account,
                                  expected_http_calls=1) as ctx:
            with self.settings(GITHUB_CLIENT_ID=None,
                               GITHUB_CLIENT_SECRET=None):
                ctx.service.authorize(username='myuser',
                                      password='mypass')

        self.assertTrue(hosting_account.is_authorized)

        ctx.assertHTTPCall(
            0,
            url='https://api.github.com/authorizations',
            method='POST',
            username='myuser',
            password='mypass',
            body=(
                '{'
                '"note": "Access for Review Board (example.com/ - 2a707f8)", '
                '"note_url": "http://example.com/", '
                '"scopes": ["user", "repo"]'
                '}'
            ),
            headers={
                'Content-Length': '123',
            })

    def test_authorization_with_client_info(self):
        """Testing GitHub.authorize with registered client ID/secret"""
        payload = self.dump_json({
            'id': 1,
            'url': 'https://api.github.com/authorizations/1',
            'scopes': ['user', 'repo'],
            'token': 'abc123',
            'note': '',
            'note_url': '',
            'updated_at': '2012-05-04T03:30:00Z',
            'created_at': '2012-05-04T03:30:00Z',
        })

        hosting_account = self.create_hosting_account(data={})
        self.assertFalse(hosting_account.is_authorized)

        self.spy_on(
            uuid.uuid4,
            call_fake=lambda: uuid.UUID('2a707f8c6fc14dd590e545ebe1e9b2f6'))

        with self.setup_http_test(payload=payload,
                                  hosting_account=hosting_account,
                                  expected_http_calls=1) as ctx:
            with self.settings(GITHUB_CLIENT_ID='abc123',
                               GITHUB_CLIENT_SECRET='def456'):
                ctx.service.authorize(username='myuser',
                                      password='mypass')

        self.assertTrue(hosting_account.is_authorized)

        ctx.assertHTTPCall(
            0,
            url='https://api.github.com/authorizations',
            method='POST',
            username='myuser',
            password='mypass',
            body=(
                '{'
                '"client_id": "abc123", '
                '"client_secret": "def456", '
                '"note": "Access for Review Board (example.com/ - 2a707f8)", '
                '"note_url": "http://example.com/", '
                '"scopes": ["user", "repo"]'
                '}'
            ),
            headers={
                'Content-Length': '173',
            })

    def test_get_branches(self):
        """Testing GitHub.get_branches"""
        payload = self.dump_json([
            {
                'ref': 'refs/heads/master',
                'object': {
                    'sha': '859d4e148ce3ce60bbda6622cdbe5c2c2f8d9817',
                }
            },
            {
                'ref': 'refs/heads/release-1.7.x',
                'object': {
                    'sha': '92463764015ef463b4b6d1a1825fee7aeec8cb15',
                }
            },
            {
                'ref': 'refs/heads/some-component/fix',
                'object': {
                    'sha': '764015ef492c8cb1546363b45fee7ab6d1a182ee',
                }
            },
            {
                'ref': 'refs/tags/release-1.7.11',
                'object': {
                    'sha': 'f5a35f1d8a8dcefb336a8e3211334f1f50ea7792',
                }
            },
        ])

        with self.setup_http_test(payload=payload,
                                  expected_http_calls=1) as ctx:
            repository = ctx.create_repository()
            branches = ctx.service.get_branches(repository)

        ctx.assertHTTPCall(
            0,
            url=('https://api.github.com/repos/myuser/myrepo/git/refs/heads'
                 '?access_token=abc123'),
            username=None,
            password=None)

        self.assertEqual(
            branches,
            [
                Branch(id='master',
                       commit='859d4e148ce3ce60bbda6622cdbe5c2c2f8d9817',
                       default=True),
                Branch(id='release-1.7.x',
                       commit='92463764015ef463b4b6d1a1825fee7aeec8cb15',
                       default=False),
                Branch(id='some-component/fix',
                       commit='764015ef492c8cb1546363b45fee7ab6d1a182ee',
                       default=False),
            ])

    def test_get_commits(self):
        """Testing GitHub.get_commits"""
        payload = self.dump_json([
            {
                'commit': {
                    'author': {'name': 'Christian Hammond'},
                    'committer': {'date': '2013-06-25T23:31:22Z'},
                    'message': 'Fixed the bug number for the '
                               'blacktriangledown bug.',
                },
                'sha': '859d4e148ce3ce60bbda6622cdbe5c2c2f8d9817',
                'parents': [
                    {'sha': '92463764015ef463b4b6d1a1825fee7aeec8cb15'}
                ],
            },
            {
                'commit': {
                    'author': {'name': 'Christian Hammond'},
                    'committer': {'date': '2013-06-25T23:30:59Z'},
                    'message': "Merge branch 'release-1.7.x'",
                },
                'sha': '92463764015ef463b4b6d1a1825fee7aeec8cb15',
                'parents': [
                    {'sha': 'f5a35f1d8a8dcefb336a8e3211334f1f50ea7792'},
                    {'sha': '6c5f3465da5ed03dca8128bb3dd03121bd2cddb2'},
                ],
            },
            {
                'commit': {
                    'author': {'name': 'David Trowbridge'},
                    'committer': {'date': '2013-06-25T22:41:09Z'},
                    'message': 'Add DIFF_PARSE_ERROR to the '
                               'ValidateDiffResource.create error list.',
                },
                'sha': 'f5a35f1d8a8dcefb336a8e3211334f1f50ea7792',
                'parents': [],
            }
        ])

        with self.setup_http_test(payload=payload,
                                  expected_http_calls=1) as ctx:
            repository = ctx.create_repository()
            commits = ctx.service.get_commits(
                repository=repository,
                start='859d4e148ce3ce60bbda6622cdbe5c2c2f8d9817')

        ctx.assertHTTPCall(
            0,
            url=('https://api.github.com/repos/myuser/myrepo/commits'
                 '?access_token=abc123'
                 '&sha=859d4e148ce3ce60bbda6622cdbe5c2c2f8d9817'),
            username=None,
            password=None)

        self.assertEqual(
            commits,
            [
                Commit(author_name='Christian Hammond',
                       date='2013-06-25T23:31:22Z',
                       id='859d4e148ce3ce60bbda6622cdbe5c2c2f8d9817',
                       message=('Fixed the bug number for the '
                                'blacktriangledown bug.'),
                       parent='92463764015ef463b4b6d1a1825fee7aeec8cb15'),
                Commit(author_name='Christian Hammond',
                       date='2013-06-25T23:30:59Z',
                       id='92463764015ef463b4b6d1a1825fee7aeec8cb15',
                       message="Merge branch 'release-1.7.x'",
                       parent='f5a35f1d8a8dcefb336a8e3211334f1f50ea7792'),
                Commit(author_name='David Trowbridge',
                       date='2013-06-25T22:41:09Z',
                       id='f5a35f1d8a8dcefb336a8e3211334f1f50ea7792',
                       message=('Add DIFF_PARSE_ERROR to the '
                                'ValidateDiffResource.create error list.'),
                       parent=''),
            ])

        for commit in commits:
            self.assertIsNone(commit.diff)

    def test_get_change(self):
        """Testing GitHub.get_change"""
        commit_sha = '1c44b461cebe5874a857c51a4a13a849a4d1e52d'
        parent_sha = '44568f7d33647d286691517e6325fea5c7a21d5e'
        tree_sha = '56e25e58380daf9b4dfe35677ae6043fe1743922'

        paths = {
            '/repos/myuser/myrepo/commits': {
                'payload': self.dump_json([
                    {
                        'commit': {
                            'author': {'name': 'David Trowbridge'},
                            'committer': {'date': '2013-06-25T23:31:22Z'},
                            'message': 'Move .clearfix to defs.less',
                        },
                        'sha': commit_sha,
                        'parents': [{'sha': parent_sha}],
                    },
                ])
            },
            '/repos/myuser/myrepo/compare/%s...%s' % (parent_sha,
                                                      commit_sha): {
                'payload': self.dump_json({
                    'base_commit': {
                        'commit': {
                            'tree': {'sha': tree_sha},
                        },
                    },
                    'files': [
                        {
                            'sha': '4344b3ad41b171ea606e88e9665c34cca602affb',
                            'filename': 'reviewboard/static/rb/css/defs.less',
                            'status': 'modified',
                            'patch': (
                                '@@ -182,4 +182,6 @@\n'
                                ' }\n'
                                ' \n'
                                '+.foo {\n'
                                '+}\n'
                                ' \n'
                                ' table {'
                            ),
                        },
                        {
                            'sha': '8e3129277b018b169cb8d13771433fbcd165a17c',
                            'filename': ('reviewboard/static/rb/css/'
                                         'reviews.less'),
                            'status': 'modified',
                            'patch': (
                                '@@ -1311,6 +1311,4 @@\n'
                                ' }\n'
                                ' \n'
                                '-.bar {\n'
                                '-}\n'
                                ' \n'
                                ' h1 {'
                            ),
                        },
                        {
                            'sha': '17ba0791499db908433b80f37c5fbc89b870084b',
                            'filename': 'new_filename',
                            'previous_filename': 'old_filename',
                            'status': 'renamed',
                            'patch': (
                                '@@ -1,1 +1,1 @@\n'
                                '- foo\n'
                                '+ bar'
                            ),
                        },
                    ],
                }),
            },
            '/repos/myuser/myrepo/git/trees/%s' % tree_sha: {
                'payload': self.dump_json({
                    'tree': [
                        {
                            'path': 'reviewboard/static/rb/css/defs.less',
                            'sha': '830a40c3197223c6a0abb3355ea48891a1857bfd',
                        },
                        {
                            'path': 'reviewboard/static/rb/css/reviews.less',
                            'sha': '535cd2c4211038d1bb8ab6beaed504e0db9d7e62',
                        },
                        {
                            'path': 'old_filename',
                            'sha': '356a192b7913b04c54574d18c28d46e6395428ab',
                        }
                    ],
                }),
            },
        }

        with self.setup_http_test(self.make_handler_for_paths(paths),
                                  expected_http_calls=3) as ctx:
            repository = ctx.create_repository()
            change = ctx.service.get_change(repository=repository,
                                            revision=commit_sha)

        ctx.assertHTTPCall(
            0,
            url=('https://api.github.com/repos/myuser/myrepo/commits'
                 '?access_token=abc123'
                 '&sha=1c44b461cebe5874a857c51a4a13a849a4d1e52d'),
            username=None,
            password=None)

        ctx.assertHTTPCall(
            1,
            url=('https://api.github.com/repos/myuser/myrepo/compare/'
                 '44568f7d33647d286691517e6325fea5c7a21d5e...'
                 '1c44b461cebe5874a857c51a4a13a849a4d1e52d'
                 '?access_token=abc123'),
            username=None,
            password=None)

        ctx.assertHTTPCall(
            2,
            url=('https://api.github.com/repos/myuser/myrepo/git/trees/'
                 '56e25e58380daf9b4dfe35677ae6043fe1743922'
                 '?access_token=abc123&recursive=1'),
            username=None,
            password=None)

        self.assertEqual(
            change,
            Commit(author_name='David Trowbridge',
                   date='2013-06-25T23:31:22Z',
                   id='1c44b461cebe5874a857c51a4a13a849a4d1e52d',
                   message='Move .clearfix to defs.less',
                   parent='44568f7d33647d286691517e6325fea5c7a21d5e'))
        self.assertEqual(
            change.diff,
            b'diff --git a/reviewboard/static/rb/css/defs.less'
            b' b/reviewboard/static/rb/css/defs.less\n'
            b'index 830a40c3197223c6a0abb3355ea48891a1857bfd'
            b'..4344b3ad41b171ea606e88e9665c34cca602affb 100644\n'
            b'--- a/reviewboard/static/rb/css/defs.less\n'
            b'+++ b/reviewboard/static/rb/css/defs.less\n'
            b'@@ -182,4 +182,6 @@\n'
            b' }\n'
            b' \n'
            b'+.foo {\n'
            b'+}\n'
            b' \n'
            b' table {\n'
            b'diff --git a/reviewboard/static/rb/css/reviews.less'
            b' b/reviewboard/static/rb/css/reviews.less\n'
            b'index 535cd2c4211038d1bb8ab6beaed504e0db9d7e62'
            b'..8e3129277b018b169cb8d13771433fbcd165a17c 100644\n'
            b'--- a/reviewboard/static/rb/css/reviews.less\n'
            b'+++ b/reviewboard/static/rb/css/reviews.less\n'
            b'@@ -1311,6 +1311,4 @@\n'
            b' }\n'
            b' \n'
            b'-.bar {\n'
            b'-}\n'
            b' \n'
            b' h1 {\n'
            b'diff --git a/new_filename b/new_filename\n'
            b'rename from old_filename\n'
            b'rename to new_filename\n'
            b'index 356a192b7913b04c54574d18c28d46e6395428ab'
            b'..17ba0791499db908433b80f37c5fbc89b870084b\n'
            b'--- a/old_filename\n'
            b'+++ b/new_filename\n'
            b'@@ -1,1 +1,1 @@\n'
            b'- foo\n'
            b'+ bar\n')

    def test_get_change_with_not_found(self):
        """Testing GitHub.get_change with commit not found"""
        with self.setup_http_test(status_code=404,
                                  payload=b'{"message": "Not Found"}',
                                  expected_http_calls=1) as ctx:
            with self.assertRaisesMessage(SCMError, 'Not Found'):
                repository = ctx.create_repository()
                ctx.service.get_change(
                    repository=repository,
                    revision='1c44b461cebe5874a857c51a4a13a849a4d1e52d')

        ctx.assertHTTPCall(
            0,
            url=('https://api.github.com/repos/myuser/myrepo/commits'
                 '?access_token=abc123'
                 '&sha=1c44b461cebe5874a857c51a4a13a849a4d1e52d'),
            username=None,
            password=None)

    def test_get_remote_repositories_with_owner(self):
        """Testing GitHub.get_remote_repositories with requesting
        authenticated user's repositories
        """
        base_url = 'https://api.github.com/user/repos?access_token=abc123'
        paths = {
            '/user/repos?access_token=abc123': {
                'payload': self.dump_json([
                    {
                        'id': 1,
                        'owner': {
                            'login': 'myuser',
                        },
                        'name': 'myrepo',
                        'clone_url': 'myrepo_path',
                        'mirror_url': 'myrepo_mirror',
                        'private': 'false'
                    },
                ]),
                'headers': {
                    b'Link': b'<%s&page=2>; rel="next"' % base_url,
                },
            },
            '/user/repos?access_token=abc123&page=2': {
                'payload': self.dump_json([
                    {
                        'id': 2,
                        'owner': {
                            'login': 'myuser',
                        },
                        'name': 'myrepo2',
                        'clone_url': 'myrepo_path2',
                        'mirror_url': 'myrepo_mirror2',
                        'private': 'true'
                    },
                ]),
                'headers': {
                    b'Link': b'<%s&page=1>; rel="prev"' % base_url,
                },
            },
        }

        # Fetch and check the first page.
        with self.setup_http_test(self.make_handler_for_paths(paths),
                                  expected_http_calls=1) as ctx:
            paginator = ctx.service.get_remote_repositories('myuser')

        ctx.assertHTTPCall(
            0,
            url='https://api.github.com/user/repos?access_token=abc123',
            username=None,
            password=None)

        self.assertEqual(len(paginator.page_data), 1)
        self.assertFalse(paginator.has_prev)
        self.assertTrue(paginator.has_next)
        repo = paginator.page_data[0]

        self.assertIsInstance(repo, RemoteRepository)
        self.assertEqual(repo.id, 'myuser/myrepo')
        self.assertEqual(repo.owner, 'myuser')
        self.assertEqual(repo.name, 'myrepo')
        self.assertEqual(repo.scm_type, 'Git')
        self.assertEqual(repo.path, 'myrepo_path')
        self.assertEqual(repo.mirror_path, 'myrepo_mirror')

        # Fetch and check the second page.
        paginator.next()

        ctx.assertHTTPCall(
            1,
            url='https://api.github.com/user/repos?access_token=abc123&page=2',
            username=None,
            password=None)

        self.assertEqual(len(paginator.page_data), 1)
        self.assertTrue(paginator.has_prev)
        self.assertFalse(paginator.has_next)
        repo = paginator.page_data[0]

        self.assertIsInstance(repo, RemoteRepository)
        self.assertEqual(repo.id, 'myuser/myrepo2')
        self.assertEqual(repo.owner, 'myuser')
        self.assertEqual(repo.name, 'myrepo2')
        self.assertEqual(repo.scm_type, 'Git')
        self.assertEqual(repo.path, 'myrepo_path2')
        self.assertEqual(repo.mirror_path, 'myrepo_mirror2')

    def test_get_remote_repositories_with_other_user(self):
        """Testing GitHub.get_remote_repositories with requesting user's
        repositories
        """
        repos1 = self.dump_json([
            {
                'id': 1,
                'owner': {
                    'login': 'other',
                },
                'name': 'myrepo',
                'clone_url': 'myrepo_path',
                'mirror_url': 'myrepo_mirror',
                'private': 'false'
            }
        ])

        headers = {
            b'Link': (
                b'<https://api.github.com/users/other/repos'
                b'?access_token=abc123&page=2>; rel="next"'
            ),
        }

        with self.setup_http_test(payload=repos1,
                                  headers=headers,
                                  expected_http_calls=1) as ctx:
            paginator = ctx.service.get_remote_repositories('other')

        ctx.assertHTTPCall(
            0,
            url='https://api.github.com/users/other/repos?access_token=abc123',
            username=None,
            password=None)

        self.assertEqual(len(paginator.page_data), 1)
        public_repo = paginator.page_data[0]
        self.assertIsInstance(public_repo, RemoteRepository)
        self.assertEqual(public_repo.id, 'other/myrepo')
        self.assertEqual(public_repo.owner, 'other')
        self.assertEqual(public_repo.name, 'myrepo')
        self.assertEqual(public_repo.scm_type, 'Git')
        self.assertEqual(public_repo.path, 'myrepo_path')
        self.assertEqual(public_repo.mirror_path, 'myrepo_mirror')

    def test_get_remote_repositories_with_org(self):
        """Testing GitHub.get_remote_repositories with requesting
        organization's repositories
        """
        payload = self.dump_json([
            {
                'id': 1,
                'owner': {
                    'login': 'myorg',
                },
                'name': 'myrepo',
                'clone_url': 'myrepo_path',
                'mirror_url': 'myrepo_mirror',
                'private': 'false'
            },
            {
                'id': 2,
                'owner': {
                    'login': 'myuser',
                },
                'name': 'myrepo2',
                'clone_url': 'myrepo_path2',
                'mirror_url': 'myrepo_mirror2',
                'private': 'true'
            }
        ])

        with self.setup_http_test(payload=payload,
                                  expected_http_calls=1) as ctx:
            paginator = ctx.service.get_remote_repositories('myorg',
                                                            'organization')

        ctx.assertHTTPCall(
            0,
            url='https://api.github.com/orgs/myorg/repos?access_token=abc123',
            username=None,
            password=None)

        self.assertEqual(len(paginator.page_data), 2)
        public_repo, private_repo = paginator.page_data

        self.assertIsInstance(public_repo, RemoteRepository)
        self.assertEqual(public_repo.id, 'myorg/myrepo')
        self.assertEqual(public_repo.owner, 'myorg')
        self.assertEqual(public_repo.name, 'myrepo')
        self.assertEqual(public_repo.scm_type, 'Git')
        self.assertEqual(public_repo.path, 'myrepo_path')
        self.assertEqual(public_repo.mirror_path, 'myrepo_mirror')

        self.assertIsInstance(private_repo, RemoteRepository)
        self.assertEqual(private_repo.id, 'myuser/myrepo2')
        self.assertEqual(private_repo.owner, 'myuser')
        self.assertEqual(private_repo.name, 'myrepo2')
        self.assertEqual(private_repo.scm_type, 'Git')
        self.assertEqual(private_repo.path, 'myrepo_path2')
        self.assertEqual(private_repo.mirror_path, 'myrepo_mirror2')

    def test_get_remote_repositories_with_defaults(self):
        """Testing GitHub.get_remote_repositories with default values"""
        with self.setup_http_test(payload=b'{}',
                                  expected_http_calls=1) as ctx:
            ctx.service.get_remote_repositories()

        ctx.assertHTTPCall(
            0,
            url='https://api.github.com/user/repos?access_token=abc123',
            username=None,
            password=None)

    def test_get_remote_repositories_with_filter(self):
        """Testing GitHub.get_remote_repositories with ?filter-type="""
        with self.setup_http_test(payload=b'[]',
                                  expected_http_calls=1) as ctx:
            ctx.service.get_remote_repositories('myuser',
                                                filter_type='private')

        ctx.assertHTTPCall(
            0,
            url=('https://api.github.com/user/repos?access_token=abc123'
                 '&type=private'),
            username=None,
            password=None)

    def test_get_remote_repository(self):
        """Testing GitHub.get_remote_repository"""
        payload = self.dump_json({
            'id': 1,
            'owner': {
                'login': 'myuser',
            },
            'name': 'myrepo',
            'clone_url': 'myrepo_path',
            'mirror_url': 'myrepo_mirror',
            'private': 'false'
        })

        with self.setup_http_test(payload=payload,
                                  expected_http_calls=1) as ctx:
            remote_repository = \
                ctx.service.get_remote_repository('myuser/myrepo')

        ctx.assertHTTPCall(
            0,
            url=('https://api.github.com/repos/myuser/myrepo'
                 '?access_token=abc123'),
            username=None,
            password=None)

        self.assertIsInstance(remote_repository, RemoteRepository)
        self.assertEqual(remote_repository.id, 'myuser/myrepo')
        self.assertEqual(remote_repository.owner, 'myuser')
        self.assertEqual(remote_repository.name, 'myrepo')
        self.assertEqual(remote_repository.scm_type, 'Git')
        self.assertEqual(remote_repository.path, 'myrepo_path')
        self.assertEqual(remote_repository.mirror_path, 'myrepo_mirror')

    def test_get_remote_repository_invalid(self):
        """Testing GitHub.get_remote_repository with invalid repository ID"""
        with self.setup_http_test(status_code=404,
                                  payload=b'{"message": "Not Found"}',
                                  expected_http_calls=1) as ctx:
            with self.assertRaises(ObjectDoesNotExist):
                ctx.service.get_remote_repository('myuser/invalid')

        ctx.assertHTTPCall(
            0,
            url=('https://api.github.com/repos/myuser/invalid'
                 '?access_token=abc123'),
            username=None,
            password=None)

    def _test_check_repository(self, expected_owner='myuser', **kwargs):
        """Test checking for a repository.

        Args:
            expected_owner (unicode):
                The expected owner of the repository.

            **kwargs (dict):
                Keyword arguments to pass to
                :py:meth:`check_repository()
                <reviewboard.hostingsvcs.gitlab.GitLab.check_repository>`.
        """
        with self.setup_http_test(payload=b'{}',
                                  expected_http_calls=1) as ctx:
            ctx.service.check_repository(**kwargs)

        ctx.assertHTTPCall(
            0,
            url=('https://api.github.com/repos/%s/myrepo?access_token=abc123'
                 % expected_owner),
            username=None,
            password=None)

    def _test_check_repository_error(self, http_status, payload, expected_url,
                                     expected_error, **kwargs):
        """Test error conditions when checking for a repository.

        Args:
            http_status (int):
                The HTTP status to simulate returning.

            payload (bytes):
                The payload to return, if ``http_status`` is 200.

            expected_url (unicode):
                The expected URL accessed (minus any query strings).

            expected_error (unicode):
                The expected error message from a raised exception.

            **kwargs (dict):
                Keyword arguments to pass to
                :py:meth:`check_repository()
                <reviewboard.hostingsvcs.gitlab.GitLab.check_repository>`.
        """
        if http_status != 200:
            payload = b'{"message": "not Found"}'

        with self.setup_http_test(status_code=http_status,
                                  payload=payload,
                                  expected_http_calls=1) as ctx:
            with self.assertRaisesMessage(RepositoryError, expected_error):
                ctx.service.check_repository(**kwargs)

        ctx.assertHTTPCall(
            0,
            url='%s?access_token=abc123' % expected_url,
            username=None,
            password=None)

    def _get_repo_api_url(self, plan, fields):
        """Return the base API URL for a repository.

        Args:
            plan (unicode):
                The name of the plan.

            fields (dict):
                Fields containing repository information.

        Returns:
            unicode:
            The API URL for the repository.
        """
        account = self.create_hosting_account()

        repository = self.create_repository(
            hosting_account=account,
            extra_data={
                'repository_plan': plan,
            })

        form = self.get_form(plan, fields)
        form.save(repository)

        return account.service._get_repo_api_url(repository)


class CloseSubmittedHookTests(GitHubTestCase):
    """Unit tests for the GitHub close-submitted webhook."""

    fixtures = ['test_users', 'test_scmtools']

    def test_close_submitted_hook(self):
        """Testing GitHub close_submitted hook with event=push"""
        self._test_post_commit_hook()

    @add_fixtures(['test_site'])
    def test_close_submitted_hook_with_local_site(self):
        """Testing GitHub close_submitted hook with event=push and using a
        Local Site
        """
        self._test_post_commit_hook(
            LocalSite.objects.get(name=self.local_site_name))

    @add_fixtures(['test_site'])
    def test_close_submitted_hook_with_unpublished_review_request(self):
        """Testing GitHub close_submitted hook with event=push and an
        un-published review request
        """
        self._test_post_commit_hook(publish=False)

    def test_close_submitted_hook_ping(self):
        """Testing GitHub close_submitted hook with event=ping"""
        account = self.create_hosting_account()
        repository = self.create_repository(hosting_account=account)

        review_request = self.create_review_request(repository=repository,
                                                    publish=True)
        self.assertTrue(review_request.public)
        self.assertEqual(review_request.status, review_request.PENDING_REVIEW)

        url = local_site_reverse(
            'github-hooks-close-submitted',
            kwargs={
                'repository_id': repository.pk,
                'hosting_service_id': 'github',
            })

        response = self._post_commit_hook_payload(
            url, review_request, repository.get_or_create_hooks_uuid(),
            event='ping')
        self.assertEqual(response.status_code, 200)

        review_request = ReviewRequest.objects.get(pk=review_request.pk)
        self.assertTrue(review_request.public)
        self.assertEqual(review_request.status, review_request.PENDING_REVIEW)
        self.assertEqual(review_request.changedescs.count(), 0)

    def test_close_submitted_hook_with_invalid_repo(self):
        """Testing GitHub close_submitted hook with event=push and invalid
        repository
        """
        repository = self.create_repository()

        review_request = self.create_review_request(repository=repository,
                                                    publish=True)
        self.assertTrue(review_request.public)
        self.assertEqual(review_request.status, review_request.PENDING_REVIEW)

        url = local_site_reverse(
            'github-hooks-close-submitted',
            kwargs={
                'repository_id': repository.pk,
                'hosting_service_id': 'github',
            })

        response = self._post_commit_hook_payload(
            url, review_request, repository.get_or_create_hooks_uuid())
        self.assertEqual(response.status_code, 404)

        review_request = ReviewRequest.objects.get(pk=review_request.pk)
        self.assertTrue(review_request.public)
        self.assertEqual(review_request.status, review_request.PENDING_REVIEW)
        self.assertEqual(review_request.changedescs.count(), 0)

    def test_close_submitted_hook_with_invalid_site(self):
        """Testing GitHub close_submitted hook with event=push and invalid
        Local Site
        """
        repository = self.create_repository()

        review_request = self.create_review_request(repository=repository,
                                                    publish=True)
        self.assertTrue(review_request.public)
        self.assertEqual(review_request.status, review_request.PENDING_REVIEW)

        url = local_site_reverse(
            'github-hooks-close-submitted',
            local_site_name='badsite',
            kwargs={
                'repository_id': repository.pk,
                'hosting_service_id': 'github',
            })

        response = self._post_commit_hook_payload(
            url, review_request, repository.get_or_create_hooks_uuid())
        self.assertEqual(response.status_code, 404)

        review_request = ReviewRequest.objects.get(pk=review_request.pk)
        self.assertTrue(review_request.public)
        self.assertEqual(review_request.status, review_request.PENDING_REVIEW)
        self.assertEqual(review_request.changedescs.count(), 0)

    def test_close_submitted_hook_with_invalid_service_id(self):
        """Testing GitHub close_submitted hook with event=push and invalid
        hosting service ID
        """
        # We'll test against Bitbucket for this test.
        account = self.create_hosting_account()
        account.service_name = 'bitbucket'
        account.save()

        repository = self.create_repository(hosting_account=account)

        review_request = self.create_review_request(repository=repository,
                                                    publish=True)
        self.assertTrue(review_request.public)
        self.assertEqual(review_request.status, review_request.PENDING_REVIEW)

        url = local_site_reverse(
            'github-hooks-close-submitted',
            kwargs={
                'repository_id': repository.pk,
                'hosting_service_id': 'github',
            })

        response = self._post_commit_hook_payload(
            url, review_request, repository.get_or_create_hooks_uuid())
        self.assertEqual(response.status_code, 404)

        review_request = ReviewRequest.objects.get(pk=review_request.pk)
        self.assertTrue(review_request.public)
        self.assertEqual(review_request.status, review_request.PENDING_REVIEW)
        self.assertEqual(review_request.changedescs.count(), 0)

    def test_close_submitted_hook_with_invalid_event(self):
        """Testing GitHub close_submitted hook with invalid event"""
        account = self.create_hosting_account()
        repository = self.create_repository(hosting_account=account)
        review_request = self.create_review_request(repository=repository,
                                                    publish=True)
        self.assertTrue(review_request.public)
        self.assertEqual(review_request.status, review_request.PENDING_REVIEW)

        url = local_site_reverse(
            'github-hooks-close-submitted',
            kwargs={
                'repository_id': repository.pk,
                'hosting_service_id': 'github',
            })

        response = self._post_commit_hook_payload(
            url, review_request, repository.get_or_create_hooks_uuid(),
            event='foo')
        self.assertEqual(response.status_code, 400)

        review_request = ReviewRequest.objects.get(pk=review_request.pk)
        self.assertTrue(review_request.public)
        self.assertEqual(review_request.status, review_request.PENDING_REVIEW)
        self.assertEqual(review_request.changedescs.count(), 0)

    def test_close_submitted_hook_with_invalid_signature(self):
        """Testing GitHub close_submitted hook with invalid signature"""
        account = self.create_hosting_account()
        repository = self.create_repository(hosting_account=account)
        review_request = self.create_review_request(repository=repository,
                                                    publish=True)
        self.assertTrue(review_request.public)
        self.assertEqual(review_request.status, review_request.PENDING_REVIEW)

        url = local_site_reverse(
            'github-hooks-close-submitted',
            kwargs={
                'repository_id': repository.pk,
                'hosting_service_id': 'github',
            })

        response = self._post_commit_hook_payload(
            url, review_request, 'bad-secret')
        self.assertEqual(response.status_code, 400)

        review_request = ReviewRequest.objects.get(pk=review_request.pk)
        self.assertTrue(review_request.public)
        self.assertEqual(review_request.status, review_request.PENDING_REVIEW)
        self.assertEqual(review_request.changedescs.count(), 0)

    def _test_post_commit_hook(self, local_site=None, publish=True):
        """Testing posting to a commit hook.

        This will simulate pushing a commit and posting the resulting webhook
        payload from GitHub to the handler for the hook.

        Args:
            local_site (reviewboard.site.models.LocalSite, optional):
                The Local Site owning the review request.

            publish (bool, optional):
                Whether to test with a published review request.
        """
        account = self.create_hosting_account(local_site=local_site)
        repository = self.create_repository(hosting_account=account,
                                            local_site=local_site)

        review_request = self.create_review_request(repository=repository,
                                                    local_site=local_site,
                                                    publish=publish)
        self.assertEqual(review_request.status, review_request.PENDING_REVIEW)

        url = local_site_reverse(
            'github-hooks-close-submitted',
            local_site=local_site,
            kwargs={
                'repository_id': repository.pk,
                'hosting_service_id': 'github',
            })

        response = self._post_commit_hook_payload(
            url, review_request, repository.get_or_create_hooks_uuid())
        self.assertEqual(response.status_code, 200)

        review_request = ReviewRequest.objects.get(pk=review_request.pk)
        self.assertTrue(review_request.public)
        self.assertEqual(review_request.status, review_request.SUBMITTED)
        self.assertEqual(review_request.changedescs.count(), 1)

        changedesc = review_request.changedescs.get()
        self.assertEqual(changedesc.text, 'Pushed to master (1c44b46)')

    def _post_commit_hook_payload(self, url, review_request, secret,
                                  event='push'):
        """Post a payload for a hook for testing.

        Args:
            url (unicode):
                The URL to post to.

            review_request (reviewboard.reviews.models.review_request.
                            ReviewRequest):
                The review request being represented in the payload.

            secret (unicode):
                The HMAC secret for the message.

            event (unicode, optional):
                The webhook event.

        Results:
            django.core.handlers.request.wsgi.WSGIRequest:
            The post request.
        """
        payload = self.dump_json({
            # NOTE: This payload only contains the content we make
            #       use of in the hook.
            'ref': 'refs/heads/master',
            'commits': [
                {
                    'id': '1c44b461cebe5874a857c51a4a13a849a4d1e52d',
                    'message': 'This is my fancy commit\n'
                               '\n'
                               'Reviewed at http://example.com%s'
                               % review_request.get_absolute_url(),
                },
            ]
        })

        m = hmac.new(bytes(secret), payload, hashlib.sha1)

        return self.client.post(
            url,
            payload,
            content_type='application/json',
            HTTP_X_GITHUB_EVENT=event,
            HTTP_X_HUB_SIGNATURE='sha1=%s' % m.hexdigest())
