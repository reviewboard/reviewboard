from __future__ import unicode_literals

import json
from textwrap import dedent

from django.utils import six
from django.utils.six.moves.urllib.parse import urlparse

from reviewboard.hostingsvcs.models import HostingServiceAccount
from reviewboard.hostingsvcs.tests.testcases import ServiceTests
from reviewboard.scmtools.core import Branch
from reviewboard.scmtools.crypto_utils import encrypt_password
from reviewboard.scmtools.models import Repository


class GitLabTests(ServiceTests):
    """Unit tests for the GitLab hosting service."""

    service_name = 'gitlab'

    def test_service_support(self):
        """Testing the GitLab service support capabilities"""
        self.assertTrue(self.service_class.supports_bug_trackers)
        self.assertTrue(self.service_class.supports_repositories)
        self.assertFalse(self.service_class.supports_ssh_key_association)

    def test_personal_field_values(self):
        """Testing the GitLab personal plan repository field values"""
        fields = self._get_repository_fields('Git', plan='personal', fields={
            'hosting_url': 'https://example.com',
            'gitlab_personal_repo_name': 'myrepo',
        })
        self.assertEqual(fields['path'],
                         'git@example.com:myuser/myrepo.git')
        self.assertEqual(fields['mirror_path'],
                         'https://example.com/myuser/myrepo.git')

    def test_personal_bug_tracker_field(self):
        """Testing the GitLab personal repository bug tracker field value"""
        self.assertTrue(
            self.service_class.get_bug_tracker_requires_username('personal'))
        self.assertEqual(
            self.service_class.get_bug_tracker_field('personal', {
                'hosting_url': 'https://example.com',
                'gitlab_personal_repo_name': 'myrepo',
                'hosting_account_username': 'myuser',
            }),
            'https://example.com/myuser/myrepo/issues/%s')

    def test_group_field_values(self):
        """Testing the GitLab group plan repository field values"""
        fields = self._get_repository_fields('Git', plan='group', fields={
            'hosting_url': 'https://example.com',
            'gitlab_group_repo_name': 'myrepo',
            'gitlab_group_name': 'mygroup',
        })
        self.assertEqual(fields['path'],
                         'git@example.com:mygroup/myrepo.git')
        self.assertEqual(fields['mirror_path'],
                         'https://example.com/mygroup/myrepo.git')

    def test_group_bug_tracker_field(self):
        """Testing the GitLab group repository bug tracker field value"""
        self.assertFalse(
            self.service_class.get_bug_tracker_requires_username('group'))
        self.assertEqual(
            self.service_class.get_bug_tracker_field('group', {
                'hosting_url': 'https://example.com',
                'gitlab_group_name': 'mygroup',
                'gitlab_group_repo_name': 'myrepo',
            }),
            'https://example.com/mygroup/myrepo/issues/%s')

    def test_check_repository_personal(self):
        """Testing GitLab check_repository with personal repository"""
        self._test_check_repository(plan='personal',
                                    gitlab_personal_repo_name='myrepo')

    def test_check_repository_group(self):
        """Testing GitLab check_repository with group repository"""
        self._test_check_repository(plan='group',
                                    gitlab_group_name='mygroup',
                                    gitlab_group_repo_name='myrepo',
                                    expected_user='mygroup')

    def test_check_repository_personal_not_found(self):
        """Testing GitLab check_repository with not found error and personal
        repository"""
        self._test_check_repository_error(
            plan='personal',
            gitlab_personal_repo_name='myrepo',
            expected_error='A repository with this name was not found, '
                           'or your user may not own it.')

    def test_check_repository_group_repo_not_found(self):
        """Testing GitLab check_repository with not found error and
        group repository"""
        self._test_check_repository_error(
            plan='group',
            gitlab_group_name='mygroup',
            gitlab_group_repo_name='badrepo',
            expected_error='A repository with this name was not found on '
                           'this group, or your user may not have access '
                           'to it.')

    def test_check_repository_group_not_found(self):
        """Testing GitLab check_repository with an incorrect group name"""
        self._test_check_repository_error(
            plan='group',
            gitlab_group_name='badgroup',
            gitlab_group_repo_name='myrepo',
            expected_error='A group with this name was not found, or your '
                           'user may not have access to it.')

    def test_authorization(self):
        """Testing that GitLab account authorization sends expected data"""
        http_post_data = {}

        def _http_post(self, *args, **kwargs):
            http_post_data['args'] = args
            http_post_data['kwargs'] = kwargs

            return json.dumps({
                'id': 1,
                'private_token': 'abc123',
            }), {}

        account = HostingServiceAccount(service_name=self.service_name,
                                        username='myuser')
        service = account.service

        self.spy_on(service.client.http_post, call_fake=_http_post)

        self.assertFalse(account.is_authorized)

        service.authorize('myuser', 'mypass',
                          hosting_url='https://example.com')
        self.assertTrue(account.is_authorized)

        self.assertEqual(http_post_data['kwargs']['url'],
                         'https://example.com/api/v3/session')
        self.assertIn('fields', http_post_data['kwargs'])

        fields = http_post_data['kwargs']['fields']
        self.assertEqual(fields['login'], 'myuser')
        self.assertEqual(fields['password'], 'mypass')

    def test_get_branches(self):
        """Testing GitLab get_branches implementation"""
        branches_api_response = json.dumps([
            {
                'name': 'master',
                'commit': {
                    'id': 'ed899a2f4b50b4370feeea94676502b42383c746'
                }
            },
            {
                'name': 'branch1',
                'commit': {
                    'id': '6104942438c14ec7bd21c6cd5bd995272b3faff6'
                }
            },
            {
                'name': 'branch2',
                'commit': {
                    'id': '21b3bcabcff2ab3dc3c9caa172f783aad602c0b0'
                }
            },
            {
                'branch-name': 'branch3',
                'commit': {
                    'id': 'd5a3ff139356ce33e37e73add446f16869741b50'
                }
            }
        ])

        def _http_get(self, *args, **kwargs):
            return branches_api_response, None

        account = self._get_hosting_account(use_url=True)
        account.data['private_token'] = encrypt_password('abc123')

        service = account.service

        repository = Repository(hosting_account=account)
        repository.extra_data = {'gitlab_project_id': 123456}

        self.spy_on(service.client.http_get, call_fake=_http_get)

        branches = service.get_branches(repository)

        self.assertTrue(service.client.http_get.called)
        self.assertEqual(len(branches), 3)
        self.assertEqual(
            branches,
            [
                Branch(id='master',
                       commit='ed899a2f4b50b4370feeea94676502b42383c746',
                       default=True),
                Branch(id='branch1',
                       commit='6104942438c14ec7bd21c6cd5bd995272b3faff6',
                       default=False),
                Branch(id='branch2',
                       commit='21b3bcabcff2ab3dc3c9caa172f783aad602c0b0',
                       default=False)
            ])

    def test_get_commits(self):
        """Testing GitLab get_commits implementation"""
        commits_api_response = json.dumps([
            {
                'id': 'ed899a2f4b50b4370feeea94676502b42383c746',
                'author_name': 'Chester Li',
                'created_at': '2015-03-10T11:50:22+03:00',
                'message': 'Replace sanitize with escape once'
            },
            {
                'id': '6104942438c14ec7bd21c6cd5bd995272b3faff6',
                'author_name': 'Chester Li',
                'created_at': '2015-03-10T09:06:12+03:00',
                'message': 'Sanitize for network graph'
            },
            {
                'id': '21b3bcabcff2ab3dc3c9caa172f783aad602c0b0',
                'author_name': 'East Coast',
                'created_at': '2015-03-04T15:31:18.000-04:00',
                'message': 'Add a timer to test file'
            }
        ])

        def _http_get(self, *args, **kargs):
            return commits_api_response, None

        account = self._get_hosting_account(use_url=True)
        account.data['private_token'] = encrypt_password('abc123')

        service = account.service

        repository = Repository(hosting_account=account)
        repository.extra_data = {'gitlab_project_id': 123456}

        self.spy_on(service.client.http_get, call_fake=_http_get)

        commits = service.get_commits(
            repository, start='ed899a2f4b50b4370feeea94676502b42383c746')

        self.assertTrue(service.client.http_get.called)
        self.assertEqual(len(commits), 3)
        self.assertEqual(commits[0].id,
                         'ed899a2f4b50b4370feeea94676502b42383c746')
        self.assertNotEqual(commits[0].author_name, 'East Coast')
        self.assertEqual(commits[1].date, '2015-03-10T09:06:12+03:00')
        self.assertNotEqual(commits[1].message,
                            'Replace sanitize with escape once')
        self.assertEqual(commits[2].author_name, 'East Coast')

    def test_get_change(self):
        """Testing GitLab get_change implementation"""
        commit_id = 'ed899a2f4b50b4370feeea94676502b42383c746'

        commit_api_response = json.dumps(
            {
                'author_name': 'Chester Li',
                'id': commit_id,
                'created_at': '2015-03-10T11:50:22+03:00',
                'message': 'Replace sanitize with escape once',
                'parent_ids': ['ae1d9fb46aa2b07ee9836d49862ec4e2c46fbbba']
            }
        )

        path_api_response = json.dumps(
            {
                'path_with_namespace': 'username/project_name'
            }
        )

        diff = dedent(b'''\
            ---
            f1 | 1 +
            f2 | 1 +
            2 files changed, 2 insertions(+), 0 deletions(-)

            diff --git a/f1 b/f1
            index 11ac561..3ea0691 100644
            --- a/f1
            +++ b/f1
            @@ -1 +1,2 @@
            this is f1
            +add one line to f1
            diff --git a/f2 b/f2
            index c837441..9302ecd 100644
            --- a/f2
            +++ b/f2
            @@ -1 +1,2 @@
            this is f2
            +add one line to f2
            ''')

        def _http_get(service, url, *args, **kwargs):
            parsed = urlparse(url)
            if parsed.path.startswith(
                    '/api/v3/projects/123456/repository/commits'):
                # If the url is commit_api_url.
                return commit_api_response, None
            elif parsed.path == '/api/v3/projects/123456':
                # If the url is path_api_url.
                return path_api_response, None
            elif parsed.path.endswith('.diff'):
                # If the url is diff_url.
                return diff, None
            else:
                print(parsed)
                self.fail('Got an unexpected GET request')

        account = self._get_hosting_account(use_url=True)
        account.data['private_token'] = encrypt_password('abc123')

        service = account.service

        repository = Repository(hosting_account=account)
        repository.extra_data = {'gitlab_project_id': 123456}

        self.spy_on(service.client.http_get, call_fake=_http_get)

        commit = service.get_change(repository, commit_id)

        self.assertTrue(service.client.http_get.called)
        self.assertEqual(commit.date, '2015-03-10T11:50:22+03:00')
        self.assertEqual(commit.diff, diff)
        self.assertNotEqual(commit.parent, '')

    def _test_check_repository(self, expected_user='myuser', **kwargs):
        def _http_get(service, url, *args, **kwargs):
            if url == 'https://example.com/api/v3/projects?per_page=100':
                payload = [
                    {
                        'id': 1,
                        'path': 'myrepo',
                        'namespace': {
                            'path': expected_user,
                        },
                    }
                ]
            elif url == 'https://example.com/api/v3/groups?per_page=100':
                payload = [
                    {
                        'id': 1,
                        'name': 'mygroup',
                    }
                ]
            elif url == 'https://example.com/api/v3/projects/1':
                # We don't care about the contents. Just that it exists.
                payload = {}
            elif url == 'https://example.com/api/v3/groups/1':
                payload = {
                    'projects': [
                        {
                            'id': 1,
                            'name': 'myrepo',
                        },
                    ],
                }
            else:
                self.fail('Unexpected URL %s' % url)

            return json.dumps(payload), {}

        account = self._get_hosting_account(use_url=True)
        service = account.service
        self.spy_on(service.client.http_get, call_fake=_http_get)
        account.data['private_token'] = encrypt_password('abc123')

        service.check_repository(**kwargs)
        self.assertTrue(service.client.http_get.called)

    def _test_check_repository_error(self, expected_error, **kwargs):
        def _http_get(service, url, *args, **kwargs):
            if url == 'https://example.com/api/v3/groups?per_page=100':
                payload = [
                    {
                        'id': 1,
                        'name': 'mygroup',
                    }
                ]
            elif url == 'https://example.com/api/v3/groups/1':
                payload = {
                    'projects': [
                        {
                            'id': 1,
                            'name': 'myrepo',
                        },
                    ],
                }
            else:
                payload = []

            return json.dumps(payload), {}

        account = self._get_hosting_account(use_url=True)
        service = account.service
        self.spy_on(service.client.http_get, call_fake=_http_get)
        account.data['private_token'] = encrypt_password('abc123')

        try:
            service.check_repository(**kwargs)
            saw_exception = False
        except Exception as e:
            self.assertEqual(six.text_type(e), expected_error)
            saw_exception = True

        self.assertTrue(saw_exception)

    def _get_repo_api_url(self, plan, fields):
        account = self._get_hosting_account(use_url=True)
        service = account.service
        self.assertNotEqual(service, None)

        repository = Repository(hosting_account=account)
        repository.extra_data['repository_plan'] = plan

        form = self._get_form(plan, fields)
        form.save(repository)

        return service._get_repo_api_url(repository)
