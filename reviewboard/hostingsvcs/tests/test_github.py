from __future__ import unicode_literals

import hashlib
import hmac
import json
from hashlib import md5
from textwrap import dedent

from django.core.exceptions import ObjectDoesNotExist
from django.utils import six
from django.utils.six.moves import cStringIO as StringIO
from django.utils.six.moves.urllib.error import HTTPError
from django.utils.six.moves.urllib.parse import urlparse
from djblets.testing.decorators import add_fixtures

from reviewboard.scmtools.core import Branch
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
        """Testing the GitHub service support capabilities"""
        self.assertTrue(self.service_class.supports_bug_trackers)
        self.assertTrue(self.service_class.supports_repositories)
        self.assertFalse(self.service_class.supports_ssh_key_association)

    def test_public_field_values(self):
        """Testing the GitHub public plan repository field values"""
        fields = self._get_repository_fields('Git', plan='public', fields={
            'github_public_repo_name': 'myrepo',
        })
        self.assertEqual(fields['path'], 'git://github.com/myuser/myrepo.git')
        self.assertEqual(fields['mirror_path'],
                         'git@github.com:myuser/myrepo.git')

    def test_public_repo_api_url(self):
        """Testing the GitHub public repository API URL"""
        url = self._get_repo_api_url('public', {
            'github_public_repo_name': 'testrepo',
        })
        self.assertEqual(url, 'https://api.github.com/repos/myuser/testrepo')

    def test_public_bug_tracker_field(self):
        """Testing the GitHub public repository bug tracker field value"""
        self.assertTrue(
            self.service_class.get_bug_tracker_requires_username('public'))
        self.assertEqual(
            self.service_class.get_bug_tracker_field('public', {
                'github_public_repo_name': 'myrepo',
                'hosting_account_username': 'myuser',
            }),
            'http://github.com/myuser/myrepo/issues#issue/%s')

    def test_public_org_field_values(self):
        """Testing the GitHub public-org plan repository field values"""
        fields = self._get_repository_fields('Git', plan='public-org', fields={
            'github_public_org_repo_name': 'myrepo',
            'github_public_org_name': 'myorg',
        })
        self.assertEqual(fields['path'], 'git://github.com/myorg/myrepo.git')
        self.assertEqual(fields['mirror_path'],
                         'git@github.com:myorg/myrepo.git')

    def test_public_org_repo_api_url(self):
        """Testing the GitHub public-org repository API URL"""
        url = self._get_repo_api_url('public-org', {
            'github_public_org_name': 'myorg',
            'github_public_org_repo_name': 'testrepo',
        })
        self.assertEqual(url, 'https://api.github.com/repos/myorg/testrepo')

    def test_public_org_bug_tracker_field(self):
        """Testing the GitHub public-org repository bug tracker field value"""
        self.assertFalse(
            self.service_class.get_bug_tracker_requires_username('public-org'))
        self.assertEqual(
            self.service_class.get_bug_tracker_field('public-org', {
                'github_public_org_name': 'myorg',
                'github_public_org_repo_name': 'myrepo',
            }),
            'http://github.com/myorg/myrepo/issues#issue/%s')

    def test_private_field_values(self):
        """Testing the GitHub private plan repository field values"""
        fields = self._get_repository_fields('Git', plan='private', fields={
            'github_private_repo_name': 'myrepo',
        })
        self.assertEqual(fields['path'], 'git@github.com:myuser/myrepo.git')
        self.assertEqual(fields['mirror_path'], '')

    def test_private_repo_api_url(self):
        """Testing the GitHub private repository API URL"""
        url = self._get_repo_api_url('private', {
            'github_private_repo_name': 'testrepo',
        })
        self.assertEqual(url, 'https://api.github.com/repos/myuser/testrepo')

    def test_private_bug_tracker_field(self):
        """Testing the GitHub private repository bug tracker field value"""
        self.assertTrue(
            self.service_class.get_bug_tracker_requires_username('private'))
        self.assertEqual(
            self.service_class.get_bug_tracker_field('private', {
                'github_private_repo_name': 'myrepo',
                'hosting_account_username': 'myuser',
            }),
            'http://github.com/myuser/myrepo/issues#issue/%s')

    def test_private_org_field_values(self):
        """Testing the GitHub private-org plan repository field values"""
        fields = self._get_repository_fields(
            'Git', plan='private-org', fields={
                'github_private_org_repo_name': 'myrepo',
                'github_private_org_name': 'myorg',
            })
        self.assertEqual(fields['path'], 'git@github.com:myorg/myrepo.git')
        self.assertEqual(fields['mirror_path'], '')

    def test_private_org_repo_api_url(self):
        """Testing the GitHub private-org repository API URL"""
        url = self._get_repo_api_url('private-org', {
            'github_private_org_name': 'myorg',
            'github_private_org_repo_name': 'testrepo',
        })
        self.assertEqual(url, 'https://api.github.com/repos/myorg/testrepo')

    def test_private_org_bug_tracker_field(self):
        """Testing the GitHub private-org repository bug tracker field value"""
        self.assertFalse(self.service_class.get_bug_tracker_requires_username(
            'private-org'))
        self.assertEqual(
            self.service_class.get_bug_tracker_field('private-org', {
                'github_private_org_name': 'myorg',
                'github_private_org_repo_name': 'myrepo',
            }),
            'http://github.com/myorg/myrepo/issues#issue/%s')

    def test_check_repository_public(self):
        """Testing GitHub check_repository with public repository"""
        self._test_check_repository(plan='public',
                                    github_public_repo_name='myrepo')

    def test_check_repository_private(self):
        """Testing GitHub check_repository with private repository"""
        self._test_check_repository(plan='private',
                                    github_private_repo_name='myrepo')

    def test_check_repository_public_org(self):
        """Testing GitHub check_repository with public org repository"""
        self._test_check_repository(plan='public-org',
                                    github_public_org_name='myorg',
                                    github_public_org_repo_name='myrepo',
                                    expected_user='myorg')

    def test_check_repository_private_org(self):
        """Testing GitHub check_repository with private org repository"""
        self._test_check_repository(plan='private-org',
                                    github_private_org_name='myorg',
                                    github_private_org_repo_name='myrepo',
                                    expected_user='myorg')

    def test_check_repository_public_not_found(self):
        """Testing GitHub check_repository with not found error and public
        repository"""
        self._test_check_repository_error(
            plan='public',
            github_public_repo_name='myrepo',
            http_status=404,
            payload=b'{"message": "Not Found"}',
            expected_error='A repository with this name was not found, '
                           'or your user may not own it.')

    def test_check_repository_private_not_found(self):
        """Testing GitHub check_repository with not found error and private
        repository"""
        self._test_check_repository_error(
            plan='private',
            github_private_repo_name='myrepo',
            http_status=404,
            payload=b'{"message": "Not Found"}',
            expected_error='A repository with this name was not found, '
                           'or your user may not own it.')

    def test_check_repository_public_org_not_found(self):
        """Testing GitHub check_repository with not found error and
        public organization repository"""
        self._test_check_repository_error(
            plan='public-org',
            github_public_org_name='myorg',
            github_public_org_repo_name='myrepo',
            http_status=404,
            payload=b'{"message": "Not Found"}',
            expected_error='A repository with this organization or name '
                           'was not found.')

    def test_check_repository_private_org_not_found(self):
        """Testing GitHub check_repository with not found error and
        private organization repository"""
        self._test_check_repository_error(
            plan='private-org',
            github_private_org_name='myorg',
            github_private_org_repo_name='myrepo',
            http_status=404,
            payload=b'{"message": "Not Found"}',
            expected_error='A repository with this organization or name '
                           'was not found, or your user may not have access '
                           'to it.')

    def test_check_repository_public_plan_private_repo(self):
        """Testing GitHub check_repository with public plan and
        private repository"""
        self._test_check_repository_error(
            plan='public',
            github_public_repo_name='myrepo',
            http_status=200,
            payload=b'{"private": true}',
            expected_error='This is a private repository, but you have '
                           'selected a public plan.')

    def test_check_repository_private_plan_public_repo(self):
        """Testing GitHub check_repository with private plan and
        public repository"""
        self._test_check_repository_error(
            plan='private',
            github_private_repo_name='myrepo',
            http_status=200,
            payload=b'{"private": false}',
            expected_error='This is a public repository, but you have '
                           'selected a private plan.')

    def test_check_repository_public_org_plan_private_repo(self):
        """Testing GitHub check_repository with public organization plan and
        private repository"""
        self._test_check_repository_error(
            plan='public-org',
            github_public_org_name='myorg',
            github_public_org_repo_name='myrepo',
            http_status=200,
            payload=b'{"private": true}',
            expected_error='This is a private repository, but you have '
                           'selected a public plan.')

    def test_check_repository_private_org_plan_public_repo(self):
        """Testing GitHub check_repository with private organization plan and
        public repository"""
        self._test_check_repository_error(
            plan='private-org',
            github_private_org_name='myorg',
            github_private_org_repo_name='myrepo',
            http_status=200,
            payload=b'{"private": false}',
            expected_error='This is a public repository, but you have '
                           'selected a private plan.')

    def test_authorization(self):
        """Testing that GitHub account authorization sends expected data"""
        http_post_data = {}

        def _http_post(self, *args, **kwargs):
            http_post_data['args'] = args
            http_post_data['kwargs'] = kwargs

            return json.dumps({
                'id': 1,
                'url': 'https://api.github.com/authorizations/1',
                'scopes': ['user', 'repo'],
                'token': 'abc123',
                'note': '',
                'note_url': '',
                'updated_at': '2012-05-04T03:30:00Z',
                'created_at': '2012-05-04T03:30:00Z',
            }), {}

        account = HostingServiceAccount(service_name=self.service_name,
                                        username='myuser')
        service = account.service

        self.spy_on(service.client.http_post, call_fake=_http_post)

        self.assertFalse(account.is_authorized)

        service.authorize('myuser', 'mypass', None)
        self.assertTrue(account.is_authorized)

        self.assertEqual(http_post_data['kwargs']['url'],
                         'https://api.github.com/authorizations')
        self.assertEqual(http_post_data['kwargs']['username'], 'myuser')
        self.assertEqual(http_post_data['kwargs']['password'], 'mypass')

    def test_authorization_with_client_info(self):
        """Testing that GitHub account authorization with registered client
        info
        """
        http_post_data = {}
        client_id = '<my client id>'
        client_secret = '<my client secret>'

        def _http_post(self, *args, **kwargs):
            http_post_data['args'] = args
            http_post_data['kwargs'] = kwargs

            return json.dumps({
                'id': 1,
                'url': 'https://api.github.com/authorizations/1',
                'scopes': ['user', 'repo'],
                'token': 'abc123',
                'note': '',
                'note_url': '',
                'updated_at': '2012-05-04T03:30:00Z',
                'created_at': '2012-05-04T03:30:00Z',
            }), {}

        account = HostingServiceAccount(service_name=self.service_name,
                                        username='myuser')
        service = account.service

        self.spy_on(service.client.http_post, call_fake=_http_post)

        self.assertFalse(account.is_authorized)

        with self.settings(GITHUB_CLIENT_ID=client_id,
                           GITHUB_CLIENT_SECRET=client_secret):
            service.authorize('myuser', 'mypass', None)

        self.assertTrue(account.is_authorized)

        body = json.loads(http_post_data['kwargs']['body'])
        self.assertEqual(body['client_id'], client_id)
        self.assertEqual(body['client_secret'], client_secret)

    def test_get_branches(self):
        """Testing GitHub get_branches implementation"""
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

        def _http_get(self, *args, **kwargs):
            return branches_api_response, None

        account = self._get_hosting_account()
        account.data['authorization'] = {'token': 'abc123'}

        repository = Repository(hosting_account=account)
        repository.extra_data = {
            'repository_plan': 'public',
            'github_public_repo_name': 'myrepo',
        }

        service = account.service
        self.spy_on(service.client.http_get, call_fake=_http_get)

        branches = service.get_branches(repository)

        self.assertTrue(service.client.http_get.called)

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
        """Testing GitHub get_commits implementation"""
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

        def _http_get(self, *args, **kwargs):
            return commits_api_response, None

        account = self._get_hosting_account()
        service = account.service
        self.spy_on(service.client.http_get, call_fake=_http_get)

        account.data['authorization'] = {'token': 'abc123'}

        repository = Repository(hosting_account=account)
        repository.extra_data = {
            'repository_plan': 'public',
            'github_public_repo_name': 'myrepo',
        }

        commits = service.get_commits(
            repository, start='859d4e148ce3ce60bbda6622cdbe5c2c2f8d9817')

        self.assertTrue(service.client.http_get.called)

        self.assertEqual(len(commits), 3)
        self.assertEqual(commits[0].parent, commits[1].id)
        self.assertEqual(commits[1].parent, commits[2].id)
        self.assertEqual(commits[0].date, '2013-06-25T23:31:22Z')
        self.assertEqual(commits[1].id,
                         '92463764015ef463b4b6d1a1825fee7aeec8cb15')
        self.assertEqual(commits[2].author_name, 'David Trowbridge')
        self.assertEqual(commits[2].parent, '')

    def test_get_change(self):
        """Testing GitHub get_change implementation"""
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
        ])

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
                    'patch': dedent("""\
                        @@ -182,4 +182,23 @@
                         }


                        +/* Add a rule for clearing floats, */
                        +.clearfix {
                        +  display: inline-block;
                        +
                        +  &:after {
                        +    clear: both;
                        +    content: \".\";
                        +    display: block;
                        +    height: 0;
                        +    visibility: hidden;
                        +  }
                        +}
                        +
                        +/* Hides from IE-mac \\*/
                        +* html .clearfix {height: 1%;}
                        +.clearfix {display: block;}
                        +/* End hide from IE-mac */
                        +
                        +
                         // vim: set et ts=2 sw=2:"""),
                },
                {
                    'sha': '8e3129277b018b169cb8d13771433fbcd165a17c',
                    'filename': 'reviewboard/static/rb/css/reviews.less',
                    'status': 'modified',
                    'patch': dedent("""\
                        @@ -1311,24 +1311,6 @@
                           .border-radius(8px);
                         }

                        -/* Add a rule for clearing floats, */
                        -.clearfix {
                        -  display: inline-block;
                        -
                        -  &:after {
                        -    clear: both;
                        -    content: \".\";
                        -    display: block;
                        -    height: 0;
                        -    visibility: hidden;
                        -  }
                        -}
                        -
                        -/* Hides from IE-mac \\*/
                        -* html .clearfix {height: 1%;}
                        -.clearfix {display: block;}
                        -/* End hide from IE-mac */
                        -

                         /****************************************************
                          * Issue Summary"""),
                },
            ]
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
            ],
        })

        # This has to be a list to avoid python's hinky treatment of scope of
        # variables assigned within a closure.
        step = [1]

        def _http_get(service, url, *args, **kwargs):
            parsed = urlparse(url)
            if parsed.path == '/repos/myuser/myrepo/commits':
                self.assertEqual(step[0], 1)
                step[0] += 1

                query = parsed.query.split('&')
                self.assertIn(('sha=%s' % commit_sha), query)

                return commits_api_response, None
            elif parsed.path.startswith('/repos/myuser/myrepo/compare/'):
                self.assertEqual(step[0], 2)
                step[0] += 1

                revs = parsed.path.split('/')[-1].split('...')
                self.assertEqual(revs[0], parent_sha)
                self.assertEqual(revs[1], commit_sha)

                return compare_api_response, None
            elif parsed.path.startswith('/repos/myuser/myrepo/git/trees/'):
                self.assertEqual(step[0], 3)
                step[0] += 1

                self.assertEqual(parsed.path.split('/')[-1], tree_sha)

                return trees_api_response, None
            else:
                print(parsed)
                self.fail('Got an unexpected GET request')

        account = self._get_hosting_account()
        account.data['authorization'] = {'token': 'abc123'}

        service = account.service
        self.spy_on(service.client.http_get, call_fake=_http_get)

        repository = Repository(hosting_account=account)
        repository.extra_data = {
            'repository_plan': 'public',
            'github_public_repo_name': 'myrepo',
        }

        change = service.get_change(repository, commit_sha)

        self.assertTrue(service.client.http_get.called)

        self.assertEqual(change.message, 'Move .clearfix to defs.less')
        self.assertEqual(md5(change.diff.encode('utf-8')).hexdigest(),
                         '0dd1bde0a60c0a7bb92c27b50f51fcb6')

    def test_get_change_exception(self):
        """Testing GitHub get_change exception types"""
        def _http_get(service, url, *args, **kwargs):
            raise Exception('Not Found')

        account = self._get_hosting_account()
        account.data['authorization'] = {'token': 'abc123'}

        service = account.service
        self.spy_on(service.client.http_get, call_fake=_http_get)

        repository = Repository(hosting_account=account)
        repository.extra_data = {
            'repository_plan': 'public',
            'github_public_repo_name': 'myrepo',
        }

        service = account.service
        commit_sha = '1c44b461cebe5874a857c51a4a13a849a4d1e52d'
        self.assertRaisesMessage(
            SCMError, 'Not Found',
            lambda: service.get_change(repository, commit_sha))

    def test_get_remote_repositories_with_owner(self, **kwargs):
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

        def _http_get(service, url, *args, **kwargs):
            base_url = 'https://api.github.com/user/repos?access_token=123'
            self.assertIn(url, [base_url, '%s&page=2' % base_url])

            if url == base_url:
                return json.dumps(repos1), {
                    'Link': '<%s&page=2>; rel="next"' % base_url,
                }
            else:
                return json.dumps(repos2), {
                    'Link': '<%s&page=1>; rel="prev"' % base_url,
                }

        account = self._get_hosting_account()
        account.data['authorization'] = {
            'token': '123',
        }

        service = account.service
        self.spy_on(service.client.http_get, call_fake=_http_get)

        paginator = service.get_remote_repositories('myuser')

        # Check the first result.
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

        # Check the second result.
        paginator.next()
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

    def test_get_remote_repositories_with_other_user(self, **kwargs):
        """Testing GitHub.get_remote_repositories with requesting
        user's repositories
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
        repos2 = []

        def _http_get(service, url, *args, **kwargs):
            base_url = ('https://api.github.com/users/other/repos'
                        '?access_token=123')

            self.assertIn(url, [base_url, '%s&page=2' % base_url])

            if url == base_url:
                next_url = '<%s&page=2>; rel="next"' % base_url
                return json.dumps(repos1), {'Link': next_url}
            else:
                return json.dumps(repos2), {}

        account = self._get_hosting_account()
        account.data['authorization'] = {
            'token': '123',
        }

        service = account.service
        self.spy_on(service.client.http_get, call_fake=_http_get)

        paginator = service.get_remote_repositories('other')

        self.assertEqual(len(paginator.page_data), 1)
        public_repo = paginator.page_data[0]
        self.assertIsInstance(public_repo, RemoteRepository)
        self.assertEqual(public_repo.id, 'other/myrepo')
        self.assertEqual(public_repo.owner, 'other')
        self.assertEqual(public_repo.name, 'myrepo')
        self.assertEqual(public_repo.scm_type, 'Git')
        self.assertEqual(public_repo.path, 'myrepo_path')
        self.assertEqual(public_repo.mirror_path, 'myrepo_mirror')

    def test_get_remote_repositories_with_org(self, **kwargs):
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

        def _http_get(service, url, *args, **kwargs):
            self.assertEqual(
                url,
                'https://api.github.com/orgs/myorg/repos?access_token=123')
            return json.dumps(repos), {}

        account = self._get_hosting_account()
        account.data['authorization'] = {
            'token': '123',
        }

        service = account.service
        self.spy_on(service.client.http_get, call_fake=_http_get)

        paginator = service.get_remote_repositories('myorg', 'organization')
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

    def test_get_remote_repositories_with_defaults(self, **kwargs):
        """Testing GitHub.get_remote_repositories with default values"""
        def _http_get(service, url, *args, **kwargs):
            self.assertEqual(
                url,
                'https://api.github.com/user/repos?access_token=123')

            return b'{}', {}

        account = self._get_hosting_account()
        account.data['authorization'] = {
            'token': '123',
        }

        service = account.service
        self.spy_on(service.client.http_get, call_fake=_http_get)

        service.get_remote_repositories()

    def test_get_remote_repositories_with_filter(self, **kwargs):
        """Testing GitHub.get_remote_repositories with ?filter-type="""
        def _http_get(service, url, *args, **kwargs):
            self.assertEqual(url,
                             'https://api.github.com/user/repos'
                             '?access_token=123&type=private')

            return json.dumps([]), {}

        account = self._get_hosting_account()
        account.data['authorization'] = {
            'token': '123',
        }

        service = account.service
        self.spy_on(service.client.http_get, call_fake=_http_get)

        service.get_remote_repositories('myuser', filter_type='private')

    def test_get_remote_repository(self, **kwargs):
        """Testing GitHub.get_remote_repository"""
        def _http_get(service, url, *args, **kwargs):
            self.assertEqual(
                url,
                'https://api.github.com/repos/myuser/myrepo'
                '?access_token=123')

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

            return json.dumps(repo_data), {}

        account = self._get_hosting_account()
        account.data['authorization'] = {
            'token': '123',
        }

        service = account.service
        self.spy_on(service.client.http_get, call_fake=_http_get)

        remote_repository = service.get_remote_repository('myuser/myrepo')

        self.assertIsInstance(remote_repository, RemoteRepository)
        self.assertEqual(remote_repository.id, 'myuser/myrepo')
        self.assertEqual(remote_repository.owner, 'myuser')
        self.assertEqual(remote_repository.name, 'myrepo')
        self.assertEqual(remote_repository.scm_type, 'Git')
        self.assertEqual(remote_repository.path, 'myrepo_path')
        self.assertEqual(remote_repository.mirror_path, 'myrepo_mirror')

    def test_get_remote_repository_invalid(self, **kwargs):
        """Testing GitHub.get_remote_repository with invalid repository ID"""
        def _http_get(service, url, *args, **kwargs):
            self.assertEqual(
                url,
                'https://api.github.com/repos/myuser/invalid'
                '?access_token=123')

            payload = {
                'message': 'Not Found',
            }

            raise HTTPError(url, 404, '', {}, StringIO(json.dumps(payload)))

        account = self._get_hosting_account()
        account.data['authorization'] = {
            'token': '123',
        }

        service = account.service
        self.spy_on(service.client.http_get, call_fake=_http_get)

        self.assertRaises(ObjectDoesNotExist,
                          service.get_remote_repository, 'myuser/invalid')

    @add_fixtures(['test_users', 'test_scmtools'])
    def test_close_submitted_hook(self):
        """Testing GitHub close_submitted hook"""
        self._test_post_commit_hook()

    @add_fixtures(['test_site', 'test_users', 'test_scmtools'])
    def test_close_submitted_hook_with_local_site(self):
        """Testing GitHub close_submitted hook with a Local Site"""
        self._test_post_commit_hook(
            LocalSite.objects.get(name=self.local_site_name))

    @add_fixtures(['test_site', 'test_users', 'test_scmtools'])
    def test_close_submitted_hook_with_unpublished_review_request(self):
        """Testing GitHub close_submitted hook with an un-published review
        request
        """
        self._test_post_commit_hook(publish=False)

    @add_fixtures(['test_users', 'test_scmtools'])
    def test_close_submitted_hook_ping(self):
        """Testing GitHub close_submitted hook ping"""
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
        """Testing GitHub close_submitted hook with invalid repository"""
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
        """Testing GitHub close_submitted hook with invalid Local Site"""
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
        """Testing GitHub close_submitted hook with invalid hosting service ID
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
        """Testing GitHub close_submitted hook with non-push event"""
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

    def _test_check_repository(self, expected_user='myuser', **kwargs):
        def _http_get(service, url, *args, **kwargs):
            self.assertEqual(
                url,
                'https://api.github.com/repos/%s/myrepo?access_token=123'
                % expected_user)
            return b'{}', {}

        account = self._get_hosting_account()
        service = account.service
        self.spy_on(service.client.http_get, call_fake=_http_get)
        account.data['authorization'] = {
            'token': '123',
        }

        service.check_repository(**kwargs)
        self.assertTrue(service.client.http_get.called)

    def _test_check_repository_error(self, http_status, payload,
                                     expected_error, **kwargs):
        def _http_get(service, url, *args, **kwargs):
            if http_status == 200:
                return payload, {}
            else:
                raise HTTPError(url, http_status, '', {}, StringIO(payload))

        account = self._get_hosting_account()
        service = account.service
        self.spy_on(service.client.http_get, call_fake=_http_get)
        account.data['authorization'] = {
            'token': '123',
        }

        try:
            service.check_repository(**kwargs)
            saw_exception = False
        except Exception as e:
            self.assertEqual(six.text_type(e), expected_error)
            saw_exception = True

        self.assertTrue(saw_exception)

    def _get_repo_api_url(self, plan, fields):
        account = self._get_hosting_account()
        service = account.service
        self.assertNotEqual(service, None)

        repository = Repository(hosting_account=account)
        repository.extra_data['repository_plan'] = plan

        form = self._get_form(plan, fields)
        form.save(repository)

        return service._get_repo_api_url(repository)
