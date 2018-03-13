from __future__ import unicode_literals

import json
from textwrap import dedent

from django.utils.six.moves import cStringIO as StringIO
from django.utils.six.moves.urllib.error import HTTPError
from django.utils.six.moves.urllib.parse import urlparse
from django.utils.six.moves.urllib.request import urlopen
from reviewboard.hostingsvcs.models import HostingServiceAccount
from reviewboard.hostingsvcs.tests.testcases import ServiceTests
from reviewboard.scmtools.core import Branch
from reviewboard.scmtools.crypto_utils import encrypt_password
from reviewboard.scmtools.models import Repository


class FakeResponse(object):
    """A fake HTTP response."""

    def __init__(self, request, body, headers):
        """Initialize the response.

        Args:
            request (reviewboard.hostingsvcs.service.URLRequest):
                The request that triggered this response.

            body (bytes):
                The response body.

            headers (dict):
                The response headers.
        """
        self.request = request
        self.body = body
        self.headers = headers

    def read(self):
        """Read the response.

        Returns:
            bytes:
            The response body this instance was initialized with.
        """
        return self.body


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

    def test_check_repository_personal_v3(self):
        """Testing GitLab check_repository with personal repository (API v3)"""
        self._test_check_repository_v3(plan='personal',
                                       gitlab_personal_repo_name='myrepo')

    def test_check_repository_personal_v4(self):
        """Testing GitLab check_repository with personal repository (API v4)"""
        self._test_check_repository_v4(plan='personal',
                                       gitlab_personal_repo_name='myrepo')

    def test_check_repository_group_v3(self):
        """Testing GitLab check_repository with group repository (API v3)"""
        self._test_check_repository_v3(plan='group',
                                       gitlab_group_name='mygroup',
                                       gitlab_group_repo_name='myrepo',
                                       expected_user='mygroup')

    def test_check_repository_group_v4(self):
        """Testing GitLab check_repository with group repository (API v4)"""
        self._test_check_repository_v4(plan='group',
                                       gitlab_group_name='mygroup',
                                       gitlab_group_repo_name='myrepo',
                                       expected_user='mygroup')

    def test_check_repository_personal_not_found_v4(self):
        """Testing GitLab check_repository with not found error and personal
        repository (API v4)
        """
        self._test_check_repository_error_v4(
            plan='personal',
            gitlab_personal_repo_name='myrepo',
            expected_error='A repository with this name was not found, '
                           'or your user may not own it.')

    def test_check_repository_group_repo_not_found_v4(self):
        """Testing GitLab check_repository with not found error and
        group repository (API v4)
        """
        self._test_check_repository_error_v4(
            plan='group',
            gitlab_group_name='mygroup',
            gitlab_group_repo_name='badrepo',
            expected_error='A repository with this name was not found, '
                           'or your user may not own it.')

    def test_check_repository_personal_not_found_v3(self):
        """Testing GitLab check_repository with not found error and personal
        repository (API v3)
        """
        self._test_check_repository_error_v3(
            plan='personal',
            gitlab_personal_repo_name='myrepo',
            expected_error='A repository with this name was not found, '
                           'or your user may not own it.')

    def test_check_repository_group_repo_not_found_v3(self):
        """Testing GitLab check_repository with not found error and
        group repository (API v3)
        """
        self._test_check_repository_error_v3(
            plan='group',
            gitlab_group_name='mygroup',
            gitlab_group_repo_name='badrepo',
            expected_error='A repository with this name was not found on '
                           'this group, or your user may not have access '
                           'to it.')

    def test_check_repository_group_not_found_v3(self):
        """Testing GitLab check_repository with an incorrect group name (API
        v3)
        """
        self._test_check_repository_error_v3(
            plan='group',
            gitlab_group_name='badgroup',
            gitlab_group_repo_name='myrepo',
            expected_error='A group with this name was not found, or your '
                           'user may not have access to it.')

    def test_authorization_v4(self):
        """Testing that GitLab APIv4 account authorization sends expected
        data
        """
        def _urlopen(url, *args, **kwargs):
            return FakeResponse(url, '{}', {})

        self.spy_on(urlopen, call_fake=_urlopen)

        account = HostingServiceAccount(service_name=self.service_name,
                                        username='myuser')
        service = account.service
        self.assertFalse(account.is_authorized)

        service.authorize(
            'myuser',
            credentials={
                'username': 'myuser',
                'private_token': 'foobarbaz',
            },
            hosting_url='https://example.com')
        self.assertTrue(account.is_authorized)

        self.assertTrue(urlopen.spy.called)
        request = urlopen.spy.last_call.return_value.request
        self.assertEqual(request.get_full_url(),
                         'https://example.com/api/v4/projects?per_page=1')

        self.assertEqual(request.headers, {'Private-token': 'foobarbaz'})
        self.assertIsNone(request.data)

    def test_authorization_v3(self):
        """Testing that GitLab APIv3 account authorization sends expected
        data
        """
        def _urlopen(url, *args, **kwargs):
            if 'api/v4' in url._Request__original:
                raise HTTPError

            return FakeResponse(url, '{}', {})

        self.spy_on(urlopen, call_fake=_urlopen)

        account = HostingServiceAccount(service_name=self.service_name,
                                        username='myuser')
        service = account.service
        self.assertFalse(account.is_authorized)

        service.authorize('myuser',
                          credentials={
                              'username': 'myuser',
                              'private_token': 'foobarbaz',
                          },
                          hosting_url='https://example.com')
        self.assertTrue(account.is_authorized)

        self.assertTrue(urlopen.spy.called)
        request = urlopen.spy.last_call.return_value.request
        self.assertEqual(request.get_full_url(),
                         'https://example.com/api/v3/projects?per_page=1')

        self.assertEqual(request.headers, {'Private-token': 'foobarbaz'})
        self.assertIsNone(request.data)

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

        def _urlopen(url, *args, **kwargs):
            return FakeResponse(url, branches_api_response, None)

        self.spy_on(urlopen, call_fake=_urlopen)

        account = self._get_hosting_account(use_url=True)
        account.data['private_token'] = encrypt_password('abc123')

        service = account.service

        repository = Repository(hosting_account=account)
        repository.extra_data = {'gitlab_project_id': 123456}

        branches = service.get_branches(repository)

        self.assertTrue(urlopen.spy.called)
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
        commit_rsp = json.dumps({
            'author_name': 'Chester Li',
            'id': commit_id,
            'created_at': '2015-03-10T11:50:22+03:00',
            'message': 'Replace sanitize with escape once',
            'parent_ids': ['ae1d9fb46aa2b07ee9836d49862ec4e2c46fbbba'],
        })

        diff_rsp = dedent(
            b'''\
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
            +add one line to f2 with Unicode\xe2\x9d\xb6
            '''
        )

        project_rsp = json.dumps({
            'path_with_namespace': 'username/project_name',
        })

        def _urlopen(url, *args, **kwargs):
            url = url.get_full_url()
            parse_result = urlparse(url)

            if (parse_result.path.startswith('/api/v4/projects') and
                parse_result.query == 'per_page=1'):
                rsp = ''
            elif parse_result.path.startswith('/api/v4/projects/123456/'
                                              'repository/commits'):
                rsp = commit_rsp
            elif parse_result.path == '/api/v4/projects/123456':
                rsp = project_rsp
            elif parse_result.path.endswith('.diff'):
                rsp = diff_rsp
            else:
                self.fail('Unexpected HTTP request URL: %s' % url)

            return FakeResponse(url, rsp, {})

        self.spy_on(urlopen, call_fake=_urlopen)

        account = self._get_hosting_account(use_url=True)
        account.data['private_token'] = encrypt_password('abc123')
        service = account.service

        repository = Repository(hosting_account=account)
        repository.extra_data = {'gitlab_project_id': 123456}

        commit = service.get_change(repository, commit_id)

        self.assertTrue(urlopen.spy.called)

        self.assertEqual(commit.date, '2015-03-10T11:50:22+03:00')
        self.assertEqual(commit.diff, diff_rsp)
        self.assertNotEqual(commit.parent, '')

        self.assertEqual(commit.message, 'Replace sanitize with escape once')

    def _test_check_repository_v4(self, expected_user='myuser', **kwargs):
        def _http_get(service, url, *args, **kwargs):
            if url == 'https://example.com/api/v4/projects/mygroup%2Fmyrepo':
                # We don't care about the contents. Just that it exists.
                payload = {}
            elif url == 'https://example.com/api/v4/projects/myuser%2Fmyrepo':
                # We don't care about the contents. Just that it exists.
                payload = {}
            else:
                self.fail('Unexpected URL %s' % url)

            return json.dumps(payload), {}

    def _test_check_repository_v3(self, expected_user='myuser', **kwargs):
        def _http_get(service, url, *args, **kwargs):
            if url.startswith('https://example.com/api/v3/projects?per_page='):
                payload = [
                    {
                        'id': 1,
                        'path': 'myrepo',
                        'namespace': {
                            'path': expected_user,
                        },
                    },
                ]
            elif url == 'https://example.com/api/v3/groups?per_page=100':
                payload = [
                    {
                        'id': 1,
                        'name': 'mygroup',
                    },
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
        self.spy_on(service._get_api_version,
                    call_fake=lambda self, hosting_url: '3')
        self.spy_on(service.client.http_get, call_fake=_http_get)
        account.data['private_token'] = encrypt_password('abc123')

        service.check_repository(**kwargs)
        self.assertTrue(service.client.http_get.called)

    def _test_check_repository_error_v4(self, expected_error, **kwargs):
        def _http_get(service, url, *args, **kwargs):
            error = HTTPError(url, 404, '', {}, StringIO())

            if url == 'https://example.com/api/v4/projects/mygroup%2Fbadrepo':
                raise error
            elif url == 'https://example.com/api/v4/projects/myuser%2Fmyrepo':
                raise error
            else:
                self.fail('Unexpected URL %s' % url)

        account = self._get_hosting_account(use_url=True)
        service = account.service
        self.spy_on(service._get_api_version,
                    call_fake=lambda self, hosting_url: '4')
        self.spy_on(service.client.http_get, call_fake=_http_get)
        account.data['private_token'] = encrypt_password('abc123')

        with self.assertRaisesMessage(Exception, expected_error):
            service.check_repository(**kwargs)

    def _test_check_repository_error_v3(self, expected_error, **kwargs):
        def _http_get(service, url, *args, **kwargs):
            if url == 'https://example.com/api/v3/groups?per_page=100':
                payload = [
                    {
                        'id': 1,
                        'name': 'mygroup',
                    }
                ]
            elif url == 'https://example.com/api/v3/projects?per_page=100':
                payload = []
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
        self.spy_on(service._get_api_version,
                    call_fake=lambda self, hosting_url: '3')
        self.spy_on(service.client.http_get, call_fake=_http_get)
        account.data['private_token'] = encrypt_password('abc123')

        with self.assertRaisesMessage(Exception, expected_error):
            service.check_repository(**kwargs)

    def _get_repo_api_url(self, plan, fields):
        account = self._get_hosting_account(use_url=True)
        service = account.service
        self.assertNotEqual(service, None)

        repository = Repository(hosting_account=account)
        repository.extra_data['repository_plan'] = plan

        form = self._get_form(plan, fields)
        form.save(repository)

        return service._get_repo_api_url(repository)
