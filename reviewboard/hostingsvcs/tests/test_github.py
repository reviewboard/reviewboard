"""Unit tests for the GitHub hosting service."""

from __future__ import unicode_literals

import hashlib
import hmac
import io
import json
import uuid

from django.core.exceptions import ObjectDoesNotExist
from django.utils.six.moves.urllib.error import HTTPError
from django.utils.six.moves.urllib.parse import urlparse
from djblets.testing.decorators import add_fixtures

from reviewboard.scmtools.core import Branch
from reviewboard.hostingsvcs.errors import RepositoryError
from reviewboard.hostingsvcs.models import HostingServiceAccount
from reviewboard.hostingsvcs.repository import RemoteRepository
from reviewboard.hostingsvcs.tests.testcases import ServiceTests
from reviewboard.reviews.models import ReviewRequest
from reviewboard.scmtools.errors import SCMError
from reviewboard.scmtools.models import Repository
from reviewboard.site.models import LocalSite
from reviewboard.site.urlresolvers import local_site_reverse


class GitHubTests(ServiceTests):
    """Unit tests for the GitHub hosting service."""

    service_name = 'github'

    def test_service_support(self):
        """Testing GitHub service support capabilities"""
        self.assertTrue(self.service_class.supports_bug_trackers)
        self.assertTrue(self.service_class.supports_repositories)
        self.assertFalse(self.service_class.supports_ssh_key_association)

    def test_get_repository_fields_with_public_plan(self):
        """Testing GitHub.get_repository_fields with the public plan"""
        fields = self._get_repository_fields('Git', plan='public', fields={
            'github_public_repo_name': 'myrepo',
        })
        self.assertEqual(fields['path'], 'git://github.com/myuser/myrepo.git')
        self.assertEqual(fields['mirror_path'],
                         'git@github.com:myuser/myrepo.git')

    def test_get_repository_fields_with_public_org_plan(self):
        """Testing GitHub.get_repository_fields with the public-org plan"""
        fields = self._get_repository_fields('Git', plan='public-org', fields={
            'github_public_org_repo_name': 'myrepo',
            'github_public_org_name': 'myorg',
        })
        self.assertEqual(fields['path'], 'git://github.com/myorg/myrepo.git')
        self.assertEqual(fields['mirror_path'],
                         'git@github.com:myorg/myrepo.git')

    def test_get_repository_fields_with_private_plan(self):
        """Testing GitHub.get_repository_fields with the private plan"""
        fields = self._get_repository_fields('Git', plan='private', fields={
            'github_private_repo_name': 'myrepo',
        })
        self.assertEqual(fields['path'], 'git@github.com:myuser/myrepo.git')
        self.assertEqual(fields['mirror_path'], '')

    def test_get_repository_fields_with_private_org_plan(self):
        """Testing GitHub.get_repository_fields with the private-org plan"""
        fields = self._get_repository_fields(
            'Git', plan='private-org', fields={
                'github_private_org_repo_name': 'myrepo',
                'github_private_org_name': 'myorg',
            })
        self.assertEqual(fields['path'], 'git@github.com:myorg/myrepo.git')
        self.assertEqual(fields['mirror_path'], '')

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
        def _http_request(client, *args, **kwargs):
            return json.dumps({
                'id': 1,
                'url': 'https://api.github.com/authorizations/1',
                'scopes': ['user', 'repo'],
                'token': 'abc123',
                'note': '',
                'note_url': '',
                'updated_at': '2012-05-04T03:30:00Z',
                'created_at': '2012-05-04T03:30:00Z',
            }).encode('utf-8'), {}

        account = HostingServiceAccount(service_name=self.service_name,
                                        username='myuser')
        self.assertFalse(account.is_authorized)

        service = account.service
        client = service.client

        self.spy_on(client.http_request, call_fake=_http_request)
        self.spy_on(
            uuid.uuid4,
            call_fake=lambda: uuid.UUID('2a707f8c6fc14dd590e545ebe1e9b2f6'))

        with self.settings(GITHUB_CLIENT_ID=None,
                           GITHUB_CLIENT_SECRET=None):
            service.authorize('myuser', 'mypass', None)

        self.assertTrue(account.is_authorized)

        calls = client.http_request.calls
        self.assertEqual(len(calls), 1)
        self.assertTrue(calls[0].called_with(
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
            }))

    def test_authorization_with_client_info(self):
        """Testing GitHub.authorize with registered client ID/secret"""
        def _http_request(client, *args, **kwargs):
            return json.dumps({
                'id': 1,
                'url': 'https://api.github.com/authorizations/1',
                'scopes': ['user', 'repo'],
                'token': 'abc123',
                'note': '',
                'note_url': '',
                'updated_at': '2012-05-04T03:30:00Z',
                'created_at': '2012-05-04T03:30:00Z',
            }).encode('utf-8'), {}

        account = HostingServiceAccount(service_name=self.service_name,
                                        username='myuser')
        service = account.service
        client = service.client

        self.spy_on(client.http_request, call_fake=_http_request)
        self.spy_on(
            uuid.uuid4,
            call_fake=lambda: uuid.UUID('2a707f8c6fc14dd590e545ebe1e9b2f6'))

        self.assertFalse(account.is_authorized)

        with self.settings(GITHUB_CLIENT_ID='abc123',
                           GITHUB_CLIENT_SECRET='def456'):
            service.authorize('myuser', 'mypass', None)

        self.assertTrue(account.is_authorized)

        calls = client.http_request.calls
        self.assertEqual(len(calls), 1)
        self.assertTrue(calls[0].called_with(
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
            }))

    def test_get_branches(self):
        """Testing GitHub.get_branches"""
        branches_api_response = json.dumps([
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

        def _http_request(client, *args, **kwargs):
            return branches_api_response.encode('utf-8'), {}

        account = self._get_hosting_account()
        account.data['authorization'] = {'token': 'abc123'}

        repository = Repository(hosting_account=account)
        repository.extra_data = {
            'repository_plan': 'public',
            'github_public_repo_name': 'myrepo',
        }

        service = account.service
        client = service.client

        self.spy_on(client.http_request, call_fake=_http_request)

        branches = service.get_branches(repository)

        calls = client.http_request.calls
        self.assertEqual(len(calls), 1)
        self.assertTrue(calls[0].called_with(
            url=('https://api.github.com/repos/myuser/myrepo/git/refs/heads'
                 '?access_token=abc123'),
            method='GET',
            username=None,
            password=None,
            body=None,
            headers=None))

        self.assertEqual(len(branches), 3)
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
        commits_api_response = json.dumps([
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

        def _http_request(client, *args, **kwargs):
            return commits_api_response.encode('utf-8'), {}

        account = self._get_hosting_account()
        service = account.service
        client = service.client

        self.spy_on(client.http_request, call_fake=_http_request)

        account.data['authorization'] = {'token': 'abc123'}

        repository = Repository(hosting_account=account)
        repository.extra_data = {
            'repository_plan': 'public',
            'github_public_repo_name': 'myrepo',
        }

        commits = service.get_commits(
            repository,
            start='859d4e148ce3ce60bbda6622cdbe5c2c2f8d9817')

        calls = client.http_request.calls
        self.assertEqual(len(calls), 1)
        self.assertTrue(calls[0].called_with(
            url=('https://api.github.com/repos/myuser/myrepo/commits'
                 '?access_token=abc123'
                 '&sha=859d4e148ce3ce60bbda6622cdbe5c2c2f8d9817'),
            method='GET',
            username=None,
            password=None,
            body=None,
            headers=None))

        self.assertEqual(len(commits), 3)

        commit = commits[0]
        self.assertEqual(commit.author_name, 'Christian Hammond')
        self.assertEqual(commit.date, '2013-06-25T23:31:22Z')
        self.assertEqual(commit.id, '859d4e148ce3ce60bbda6622cdbe5c2c2f8d9817')
        self.assertEqual(commit.message,
                         'Fixed the bug number for the blacktriangledown bug.')
        self.assertEqual(commit.parent, commits[1].id)

        commit = commits[1]
        self.assertEqual(commit.author_name, 'Christian Hammond')
        self.assertEqual(commit.date, '2013-06-25T23:30:59Z')
        self.assertEqual(commit.id, '92463764015ef463b4b6d1a1825fee7aeec8cb15')
        self.assertEqual(commit.message, "Merge branch 'release-1.7.x'")
        self.assertEqual(commit.parent, commits[2].id)

        commit = commits[2]
        self.assertEqual(commit.author_name, 'David Trowbridge')
        self.assertEqual(commit.date, '2013-06-25T22:41:09Z')
        self.assertEqual(commit.id, 'f5a35f1d8a8dcefb336a8e3211334f1f50ea7792')
        self.assertEqual(commit.message,
                         'Add DIFF_PARSE_ERROR to the '
                         'ValidateDiffResource.create error list.')
        self.assertEqual(commit.parent, '')

    def test_get_change(self):
        """Testing GitHub.get_change"""
        commit_sha = '1c44b461cebe5874a857c51a4a13a849a4d1e52d'
        parent_sha = '44568f7d33647d286691517e6325fea5c7a21d5e'
        tree_sha = '56e25e58380daf9b4dfe35677ae6043fe1743922'

        commits_api_response = json.dumps([
            {
                'commit': {
                    'author': {'name': 'David Trowbridge'},
                    'committer': {'date': '2013-06-25T23:31:22Z'},
                    'message': 'Move .clearfix to defs.less',
                },
                'sha': commit_sha,
                'parents': [{'sha': parent_sha}],
            },
        ]).encode('utf-8')

        compare_api_response = json.dumps({
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
                    'filename': 'reviewboard/static/rb/css/reviews.less',
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
        })

        trees_api_response = json.dumps({
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
        }).encode('utf-8')

        # This has to be a list to avoid python's hinky treatment of scope of
        # variables assigned within a closure.
        step = [1]

        def _http_request(client, url, *args, **kwargs):
            parsed = urlparse(url)

            if parsed.path == '/repos/myuser/myrepo/commits':
                self.assertEqual(step[0], 1)
                step[0] += 1

                query = parsed.query.split('&')
                self.assertIn(('sha=%s' % commit_sha), query)

                return commits_api_response, {}
            elif parsed.path.startswith('/repos/myuser/myrepo/compare/'):
                self.assertEqual(step[0], 2)
                step[0] += 1

                revs = parsed.path.split('/')[-1].split('...')
                self.assertEqual(revs[0], parent_sha)
                self.assertEqual(revs[1], commit_sha)

                return compare_api_response, {}
            elif parsed.path.startswith('/repos/myuser/myrepo/git/trees/'):
                self.assertEqual(step[0], 3)
                step[0] += 1

                self.assertEqual(parsed.path.split('/')[-1], tree_sha)

                return trees_api_response, {}
            else:
                print(parsed)
                self.fail('Got an unexpected GET request')

        account = self._get_hosting_account()
        account.data['authorization'] = {'token': 'abc123'}

        service = account.service
        client = service.client

        repository = Repository(hosting_account=account)
        repository.extra_data = {
            'repository_plan': 'public',
            'github_public_repo_name': 'myrepo',
        }

        self.spy_on(client.http_request, call_fake=_http_request)

        change = service.get_change(repository, commit_sha)

        calls = client.http_request.calls
        self.assertEqual(len(calls), 3)

        self.assertTrue(calls[0].called_with(
            url=('https://api.github.com/repos/myuser/myrepo/commits'
                 '?access_token=abc123'
                 '&sha=1c44b461cebe5874a857c51a4a13a849a4d1e52d'),
            method='GET',
            username=None,
            password=None,
            body=None,
            headers=None))

        self.assertTrue(calls[1].called_with(
            url=('https://api.github.com/repos/myuser/myrepo/compare/'
                 '44568f7d33647d286691517e6325fea5c7a21d5e...'
                 '1c44b461cebe5874a857c51a4a13a849a4d1e52d'
                 '?access_token=abc123'),
            method='GET',
            username=None,
            password=None,
            body=None,
            headers=None))

        self.assertTrue(calls[2].called_with(
            url=('https://api.github.com/repos/myuser/myrepo/git/trees/'
                 '56e25e58380daf9b4dfe35677ae6043fe1743922'
                 '?access_token=abc123&recursive=1'),
            method='GET',
            username=None,
            password=None,
            body=None,
            headers=None))

        self.assertEqual(change.author_name, 'David Trowbridge')
        self.assertEqual(change.date, '2013-06-25T23:31:22Z')
        self.assertEqual(change.id, '1c44b461cebe5874a857c51a4a13a849a4d1e52d')
        self.assertEqual(change.message, 'Move .clearfix to defs.less')
        self.assertEqual(change.parent,
                         '44568f7d33647d286691517e6325fea5c7a21d5e')
        self.assertIsInstance(change.diff, bytes)
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
        def _http_request(client, url, *args, **kwargs):
            raise HTTPError(url, 404, '', {},
                            io.BytesIO(b'{"message": "Not Found"}'))

        account = self._get_hosting_account()
        account.data['authorization'] = {'token': 'abc123'}

        service = account.service
        client = service.client

        repository = Repository(hosting_account=account)
        repository.extra_data = {
            'repository_plan': 'public',
            'github_public_repo_name': 'myrepo',
        }

        self.spy_on(client.http_request, call_fake=_http_request)

        with self.assertRaisesMessage(SCMError, 'Not Found'):
            service.get_change(repository,
                               '1c44b461cebe5874a857c51a4a13a849a4d1e52d')

        calls = client.http_request.calls
        self.assertEqual(len(calls), 1)
        self.assertTrue(calls[0].called_with(
            url=('https://api.github.com/repos/myuser/myrepo/commits'
                 '?access_token=abc123'
                 '&sha=1c44b461cebe5874a857c51a4a13a849a4d1e52d'),
            method='GET',
            username=None,
            password=None,
            body=None,
            headers=None))

    def test_get_remote_repositories_with_owner(self):
        """Testing GitHub.get_remote_repositories with requesting
        authenticated user's repositories
        """
        repos1 = [
            {
                'id': 1,
                'owner': {
                    'login': 'myuser',
                },
                'name': 'myrepo',
                'clone_url': 'myrepo_path',
                'mirror_url': 'myrepo_mirror',
                'private': 'false'
            }
        ]

        repos2 = [
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
        ]

        def _http_request(client, url, *args, **kwargs):
            base_url = 'https://api.github.com/user/repos?access_token=123'
            self.assertIn(url, [base_url, '%s&page=2' % base_url])

            if url == base_url:
                payload = repos1
                link = '<%s&page=2>; rel="next"' % base_url
            else:
                payload = repos2
                link = '<%s&page=1>; rel="prev"' % base_url

            return json.dumps(payload).encode('utf-8'), {
                b'Link': link.encode('utf-8'),
            }

        account = self._get_hosting_account()
        account.data['authorization'] = {
            'token': '123',
        }

        service = account.service
        client = service.client

        self.spy_on(client.http_request, call_fake=_http_request)

        # Fetch and check the first page.
        paginator = service.get_remote_repositories('myuser')

        calls = client.http_request.calls
        self.assertEqual(len(calls), 1)
        self.assertTrue(calls[0].called_with(
            url='https://api.github.com/user/repos?access_token=123',
            method='GET',
            username=None,
            password=None,
            body=None,
            headers=None))

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

        calls = client.http_request.calls
        self.assertEqual(len(calls), 2)
        self.assertTrue(calls[1].called_with(
            url='https://api.github.com/user/repos?access_token=123&page=2',
            method='GET',
            username=None,
            password=None,
            body=None,
            headers=None))

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
        repos1 = [
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
        ]

        def _http_request(client, url, *args, **kwargs):
            next_url = '<%s&page=2>; rel="next"' % url

            return json.dumps(repos1).encode('utf-8'), {
                b'Link': next_url.encode('utf-8'),
            }

        account = self._get_hosting_account()
        account.data['authorization'] = {
            'token': '123',
        }

        service = account.service
        client = service.client

        self.spy_on(client.http_request, call_fake=_http_request)

        paginator = service.get_remote_repositories('other')

        calls = client.http_request.calls
        self.assertEqual(len(calls), 1)
        self.assertTrue(calls[0].called_with(
            url='https://api.github.com/users/other/repos?access_token=123',
            method='GET',
            username=None,
            password=None,
            body=None,
            headers=None))

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
        repos = [
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
        ]

        def _http_request(client, *args, **kwargs):
            return json.dumps(repos).encode('utf-8'), {}

        account = self._get_hosting_account()
        account.data['authorization'] = {
            'token': '123',
        }

        service = account.service
        client = service.client

        self.spy_on(client.http_request, call_fake=_http_request)

        paginator = service.get_remote_repositories('myorg', 'organization')

        calls = client.http_request.calls
        self.assertEqual(len(calls), 1)
        self.assertTrue(calls[0].called_with(
            url='https://api.github.com/orgs/myorg/repos?access_token=123',
            method='GET',
            username=None,
            password=None,
            body=None,
            headers=None))

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
        def _http_request(client, *args, **kwargs):
            return b'{}', {}

        account = self._get_hosting_account()
        account.data['authorization'] = {
            'token': '123',
        }

        service = account.service
        client = service.client

        self.spy_on(client.http_request, call_fake=_http_request)

        service.get_remote_repositories()

        calls = client.http_request.calls
        self.assertEqual(len(calls), 1)
        self.assertTrue(calls[0].called_with(
            url='https://api.github.com/user/repos?access_token=123',
            method='GET',
            username=None,
            password=None,
            body=None,
            headers=None))

    def test_get_remote_repositories_with_filter(self):
        """Testing GitHub.get_remote_repositories with ?filter-type="""
        def _http_request(client, *args, **kwargs):
            return b'[]', {}

        account = self._get_hosting_account()
        account.data['authorization'] = {
            'token': '123',
        }

        service = account.service
        client = service.client

        self.spy_on(client.http_request, call_fake=_http_request)

        service.get_remote_repositories('myuser', filter_type='private')

        calls = client.http_request.calls
        self.assertEqual(len(calls), 1)
        self.assertTrue(calls[0].called_with(
            url=('https://api.github.com/user/repos?access_token=123'
                 '&type=private'),
            method='GET',
            username=None,
            password=None,
            body=None,
            headers=None))

    def test_get_remote_repository(self):
        """Testing GitHub.get_remote_repository"""
        def _http_request(client, *args, **kwargs):
            repo_data = {
                'id': 1,
                'owner': {
                    'login': 'myuser',
                },
                'name': 'myrepo',
                'clone_url': 'myrepo_path',
                'mirror_url': 'myrepo_mirror',
                'private': 'false'
            }

            return json.dumps(repo_data).encode('utf-8'), {}

        account = self._get_hosting_account()
        account.data['authorization'] = {
            'token': '123',
        }

        service = account.service
        client = service.client

        self.spy_on(client.http_request, call_fake=_http_request)

        remote_repository = service.get_remote_repository('myuser/myrepo')

        calls = client.http_request.calls
        self.assertEqual(len(calls), 1)
        self.assertTrue(calls[0].called_with(
            url='https://api.github.com/repos/myuser/myrepo?access_token=123',
            method='GET',
            username=None,
            password=None,
            body=None,
            headers=None))

        self.assertIsInstance(remote_repository, RemoteRepository)
        self.assertEqual(remote_repository.id, 'myuser/myrepo')
        self.assertEqual(remote_repository.owner, 'myuser')
        self.assertEqual(remote_repository.name, 'myrepo')
        self.assertEqual(remote_repository.scm_type, 'Git')
        self.assertEqual(remote_repository.path, 'myrepo_path')
        self.assertEqual(remote_repository.mirror_path, 'myrepo_mirror')

    def test_get_remote_repository_invalid(self):
        """Testing GitHub.get_remote_repository with invalid repository ID"""
        def _http_request(client, url, *args, **kwargs):
            raise HTTPError(url, 404, '', {},
                            io.BytesIO(b'{"message": "Not Found"}'))

        account = self._get_hosting_account()
        account.data['authorization'] = {
            'token': '123',
        }

        service = account.service
        client = service.client

        self.spy_on(client.http_request, call_fake=_http_request)

        with self.assertRaises(ObjectDoesNotExist):
            service.get_remote_repository('myuser/invalid')

        calls = client.http_request.calls
        self.assertEqual(len(calls), 1)
        self.assertTrue(calls[0].called_with(
            url='https://api.github.com/repos/myuser/invalid?access_token=123',
            method='GET',
            username=None,
            password=None,
            body=None,
            headers=None))

    @add_fixtures(['test_users', 'test_scmtools'])
    def test_close_submitted_hook(self):
        """Testing GitHub close_submitted hook with event=push"""
        self._test_post_commit_hook()

    @add_fixtures(['test_site', 'test_users', 'test_scmtools'])
    def test_close_submitted_hook_with_local_site(self):
        """Testing GitHub close_submitted hook with event=push and using a
        Local Site
        """
        self._test_post_commit_hook(
            LocalSite.objects.get(name=self.local_site_name))

    @add_fixtures(['test_site', 'test_users', 'test_scmtools'])
    def test_close_submitted_hook_with_unpublished_review_request(self):
        """Testing GitHub close_submitted hook with event=push and an
        un-published review request
        """
        self._test_post_commit_hook(publish=False)

    @add_fixtures(['test_users', 'test_scmtools'])
    def test_close_submitted_hook_ping(self):
        """Testing GitHub close_submitted hook with event=ping"""
        account = self._get_hosting_account()
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
            url, review_request, repository.get_or_create_hooks_uuid(),
            event='ping')
        self.assertEqual(response.status_code, 200)

        review_request = ReviewRequest.objects.get(pk=review_request.pk)
        self.assertTrue(review_request.public)
        self.assertEqual(review_request.status, review_request.PENDING_REVIEW)
        self.assertEqual(review_request.changedescs.count(), 0)

    @add_fixtures(['test_users', 'test_scmtools'])
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

    @add_fixtures(['test_users', 'test_scmtools'])
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

    @add_fixtures(['test_users', 'test_scmtools'])
    def test_close_submitted_hook_with_invalid_service_id(self):
        """Testing GitHub close_submitted hook with event=push and invalid
        hosting service ID
        """
        # We'll test against Bitbucket for this test.
        account = self._get_hosting_account()
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

    @add_fixtures(['test_users', 'test_scmtools'])
    def test_close_submitted_hook_with_invalid_event(self):
        """Testing GitHub close_submitted hook with invalid event"""
        account = self._get_hosting_account()
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
            url, review_request, repository.get_or_create_hooks_uuid(),
            event='foo')
        self.assertEqual(response.status_code, 400)

        review_request = ReviewRequest.objects.get(pk=review_request.pk)
        self.assertTrue(review_request.public)
        self.assertEqual(review_request.status, review_request.PENDING_REVIEW)
        self.assertEqual(review_request.changedescs.count(), 0)

    @add_fixtures(['test_users', 'test_scmtools'])
    def test_close_submitted_hook_with_invalid_signature(self):
        """Testing GitHub close_submitted hook with invalid signature"""
        account = self._get_hosting_account()
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
        account = self._get_hosting_account(local_site=local_site)
        account.save()

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
        payload = json.dumps({
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
        def _http_request(client, url, *args, **kwargs):
            return b'{}', {}

        account = self._get_hosting_account()
        service = account.service
        client = service.client

        account.data['authorization'] = {
            'token': '123',
        }

        self.spy_on(service.client.http_request, call_fake=_http_request)

        service.check_repository(**kwargs)

        calls = client.http_request.calls
        self.assertEqual(len(calls), 1)
        self.assertTrue(calls[0].called_with(
            url=('https://api.github.com/repos/%s/myrepo?access_token=123'
                 % expected_owner),
            method='GET',
            username=None,
            password=None,
            body=None,
            headers=None))

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
        def _http_request(client, url, *args, **kwargs):
            if http_status == 200:
                return payload, {}

            raise HTTPError(url, http_status, '', {},
                            io.BytesIO(b'{"message": "Not Found"}'))

        account = self._get_hosting_account()
        service = account.service
        client = service.client

        self.spy_on(client.http_request, call_fake=_http_request)

        account.data['authorization'] = {
            'token': '123',
        }

        with self.assertRaisesMessage(RepositoryError, expected_error):
            service.check_repository(**kwargs)

        calls = client.http_request.calls
        self.assertEqual(len(calls), 1)
        self.assertTrue(calls[0].called_with(
            url='%s?access_token=123' % expected_url,
            method='GET',
            username=None,
            password=None,
            body=None,
            headers=None))

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
        account = self._get_hosting_account()
        service = account.service
        self.assertNotEqual(service, None)

        repository = Repository(hosting_account=account)
        repository.extra_data['repository_plan'] = plan

        form = self._get_form(plan, fields)
        form.save(repository)

        return service._get_repo_api_url(repository)
