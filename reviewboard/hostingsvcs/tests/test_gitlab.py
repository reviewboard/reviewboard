"""Unit tests for the GitLab hosting service."""

from __future__ import unicode_literals

from django.utils.safestring import SafeText

from reviewboard.hostingsvcs.errors import RepositoryError
from reviewboard.hostingsvcs.gitlab import (GitLabAPIVersionError,
                                            GitLabHostingURLWidget)
from reviewboard.hostingsvcs.testing import HostingServiceTestCase
from reviewboard.scmtools.core import Branch, Commit
from reviewboard.scmtools.crypto_utils import encrypt_password


class GitLabTestCase(HostingServiceTestCase):
    """Base class for GitLab test suites."""

    service_name = 'gitlab'

    default_use_hosting_url = True
    default_account_data = {
        'private_token': encrypt_password('abc123'),
    }

    default_repository_extra_data = {
        'gitlab_project_id': 123456,
    }


class GitLabTests(GitLabTestCase):
    """Unit tests for the GitLab hosting service."""

    def test_service_support(self):
        """Testing GitLab service support capabilities"""
        self.assertTrue(self.service_class.supports_bug_trackers)
        self.assertTrue(self.service_class.supports_repositories)
        self.assertFalse(self.service_class.supports_ssh_key_association)

    def test_get_repository_fields_with_personal_plan(self):
        """Testing GitLab.get_repository_fields with plan=personal"""
        self.assertEqual(
            self.get_repository_fields(
                'Git',
                plan='personal',
                fields={
                    'hosting_url': 'https://example.com',
                    'gitlab_personal_repo_name': 'myrepo',
                }
            ),
            {
                'path': 'git@example.com:myuser/myrepo.git',
                'mirror_path': 'https://example.com/myuser/myrepo.git',
            })

    def test_get_repository_fields_with_group_plan(self):
        """Testing GitLab.get_repository_fields with plan=group"""
        self.assertEqual(
            self.get_repository_fields(
                'Git',
                plan='group',
                fields={
                    'hosting_url': 'https://example.com',
                    'gitlab_group_repo_name': 'myrepo',
                    'gitlab_group_name': 'mygroup',
                }
            ),
            {
                'path': 'git@example.com:mygroup/myrepo.git',
                'mirror_path': 'https://example.com/mygroup/myrepo.git',
            })

    def test_get_bug_tracker_field_with_personal_plan(self):
        """Testing GitLab.get_bug_tracker_field with plan=personal"""
        self.assertTrue(
            self.service_class.get_bug_tracker_requires_username('personal'))
        self.assertEqual(
            self.service_class.get_bug_tracker_field('personal', {
                'hosting_url': 'https://example.com',
                'gitlab_personal_repo_name': 'myrepo',
                'hosting_account_username': 'myuser',
            }),
            'https://example.com/myuser/myrepo/issues/%s')

    def test_get_bug_tracker_field_with_group_plan(self):
        """Testing GitLab.get_bug_tracker_field with plan=group"""
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
        """Testing GitLab.check_repository with personal repository (API v3)"""
        ctx = self._test_check_repository_v3(
            plan='personal',
            gitlab_personal_repo_name='myrepo',
            expected_http_calls=1)

        ctx.assertHTTPCall(
            0,
            url='https://example.com/api/v3/projects?per_page=100',
            username=None,
            password=None,
            headers={
                'Accept': 'application/json',
                'PRIVATE-TOKEN': 'abc123',
            })

    def test_check_repository_personal_v4(self):
        """Testing GitLab.check_repository with personal repository (API v4)"""
        ctx = self._test_check_repository_v4(
            plan='personal',
            gitlab_personal_repo_name='myrepo',
            expected_http_calls=1)

        ctx.assertHTTPCall(
            0,
            url='https://example.com/api/v4/projects/myuser%2Fmyrepo',
            username=None,
            password=None,
            headers={
                'Accept': 'application/json',
                'PRIVATE-TOKEN': 'abc123',
            })

    def test_check_repository_group_v3(self):
        """Testing GitLab.check_repository with group repository (API v3)"""
        ctx = self._test_check_repository_v3(
            plan='group',
            gitlab_group_name='mygroup',
            gitlab_group_repo_name='myrepo',
            expected_owner='mygroup',
            expected_http_calls=2)

        ctx.assertHTTPCall(
            0,
            url='https://example.com/api/v3/groups?per_page=100',
            username=None,
            password=None,
            headers={
                'Accept': 'application/json',
                'PRIVATE-TOKEN': 'abc123',
            })

        ctx.assertHTTPCall(
            1,
            url='https://example.com/api/v3/groups/1',
            username=None,
            password=None,
            headers={
                'Accept': 'application/json',
                'PRIVATE-TOKEN': 'abc123',
            })

    def test_check_repository_group_v4(self):
        """Testing GitLab.check_repository with group repository (API v4)"""
        ctx = self._test_check_repository_v4(plan='group',
                                             gitlab_group_name='mygroup',
                                             gitlab_group_repo_name='myrepo',
                                             expected_owner='mygroup',
                                             expected_http_calls=1)

        ctx.assertHTTPCall(
            0,
            url='https://example.com/api/v4/projects/mygroup%2Fmyrepo',
            username=None,
            password=None,
            headers={
                'Accept': 'application/json',
                'PRIVATE-TOKEN': 'abc123',
            })

    def test_check_repository_personal_not_found_v4(self):
        """Testing GitLab.check_repository with not found error and personal
        repository (API v4)
        """
        ctx = self._test_check_repository_error_v4(
            plan='personal',
            gitlab_personal_repo_name='myrepo',
            expected_error='A repository with this name was not found, '
                           'or your user may not own it.',
            expected_http_calls=1)

        ctx.assertHTTPCall(
            0,
            url='https://example.com/api/v4/projects/myuser%2Fmyrepo',
            username=None,
            password=None,
            headers={
                'Accept': 'application/json',
                'PRIVATE-TOKEN': 'abc123',
            })

    def test_check_repository_group_repo_not_found_v4(self):
        """Testing GitLab.check_repository with not found error and
        group repository (API v4)
        """
        ctx = self._test_check_repository_error_v4(
            plan='group',
            gitlab_group_name='mygroup',
            gitlab_group_repo_name='badrepo',
            expected_error='A repository with this name was not found, '
                           'or your user may not own it.',
            expected_http_calls=1)

        ctx.assertHTTPCall(
            0,
            url='https://example.com/api/v4/projects/mygroup%2Fbadrepo',
            username=None,
            password=None,
            headers={
                'Accept': 'application/json',
                'PRIVATE-TOKEN': 'abc123',
            })

    def test_check_repository_personal_not_found_v3(self):
        """Testing GitLab.check_repository with not found error and personal
        repository (API v3)
        """
        ctx = self._test_check_repository_error_v3(
            plan='personal',
            gitlab_personal_repo_name='myrepo',
            expected_error='A repository with this name was not found, '
                           'or your user may not own it.',
            expected_http_calls=1)

        ctx.assertHTTPCall(
            0,
            url='https://example.com/api/v3/projects?per_page=100',
            username=None,
            password=None,
            headers={
                'Accept': 'application/json',
                'PRIVATE-TOKEN': 'abc123',
            })

    def test_check_repository_group_repo_not_found_v3(self):
        """Testing GitLab.check_repository with not found error and
        group repository (API v3)
        """
        ctx = self._test_check_repository_error_v3(
            plan='group',
            gitlab_group_name='mygroup',
            gitlab_group_repo_name='badrepo',
            expected_error='A repository with this name was not found on '
                           'this group, or your user may not have access '
                           'to it.',
            expected_http_calls=2)

        ctx.assertHTTPCall(
            0,
            url='https://example.com/api/v3/groups?per_page=100',
            username=None,
            password=None,
            headers={
                'Accept': 'application/json',
                'PRIVATE-TOKEN': 'abc123',
            })

        ctx.assertHTTPCall(
            1,
            url='https://example.com/api/v3/groups/1',
            username=None,
            password=None,
            headers={
                'Accept': 'application/json',
                'PRIVATE-TOKEN': 'abc123',
            })

    def test_check_repository_group_not_found_v3(self):
        """Testing GitLab.check_repository with an incorrect group name (API
        v3)
        """
        ctx = self._test_check_repository_error_v3(
            plan='group',
            gitlab_group_name='badgroup',
            gitlab_group_repo_name='myrepo',
            expected_error='A group with this name was not found, or your '
                           'user may not have access to it.',
            expected_http_calls=1)

        ctx.assertHTTPCall(
            0,
            url='https://example.com/api/v3/groups?per_page=100',
            username=None,
            password=None,
            headers={
                'Accept': 'application/json',
                'PRIVATE-TOKEN': 'abc123',
            })

    def test_authorize_v4(self):
        """Testing GitLab.authorize (API v4)"""
        ctx = self._test_check_authorize(payload=b'{}',
                                         expected_http_calls=1)
        ctx.assertHTTPCall(
            0,
            url='https://example.com/api/v4/projects?per_page=1',
            username=None,
            password=None,
            headers={
                'PRIVATE-TOKEN': 'foobarbaz',
            })

    def test_authorize_v3(self):
        """Testing GitLab.authorize (API v3)"""
        paths = {
            '/api/v4/projects': {
                'status_code': 404,
            },
            '/api/v3/projects': {
                'payload': b'{}',
            },
        }

        ctx = self._test_check_authorize(self.make_handler_for_paths(paths),
                                         expected_http_calls=2)

        ctx.assertHTTPCall(
            0,
            url='https://example.com/api/v4/projects?per_page=1',
            username=None,
            password=None,
            headers={
                'PRIVATE-TOKEN': 'foobarbaz',
            })

        ctx.assertHTTPCall(
            1,
            url='https://example.com/api/v3/projects?per_page=1',
            username=None,
            password=None,
            headers={
                'PRIVATE-TOKEN': 'foobarbaz',
            })

    def test_authorize_with_api_version_not_found(self):
        """Testing GitLab.authorize (API version not found)"""
        hosting_account = self.create_hosting_account(data={})
        self.assertFalse(hosting_account.is_authorized)

        message = (
            'Could not determine the GitLab API version for '
            'https://example.com due to an unexpected error (Unexpected path '
            '"/api/v4/projects?per_page=1"). Check to make sure the URL can '
            'be resolved from this server and that any SSL certificates are '
            'valid and trusted.'
        )

        with self.setup_http_test(self.make_handler_for_paths({}),
                                  hosting_account=hosting_account) as ctx:
            with self.assertRaisesMessage(GitLabAPIVersionError, message):
                ctx.service.authorize(
                    'myuser',
                    credentials={
                        'username': 'myuser',
                        'private_token': 'foobarbaz',
                    },
                    hosting_url='https://example.com')

        self.assertFalse(hosting_account.is_authorized)

        ctx.assertHTTPCall(
            0,
            url='https://example.com/api/v4/projects?per_page=1',
            username=None,
            password=None,
            headers={
                'PRIVATE-TOKEN': 'foobarbaz',
            })
        ctx.assertHTTPCall(
            1,
            url='https://example.com/api/v3/projects?per_page=1',
            username=None,
            password=None,
            headers={
                'PRIVATE-TOKEN': 'foobarbaz',
            })

    def test_get_branches_v4(self):
        """Testing GitLab.get_branches (API v4)"""
        base_url = '/api/v4/projects/123456/repository/branches'
        paths = {
            base_url: {
                'headers': {
                    str('Link'): str(
                        '<https://example.com%s?page=2>; rel="next"' % base_url
                    ),
                },
                'payload': self.dump_json([
                    {
                        'name': 'master',
                        'commit': {
                            'id': 'ed899a2f4b50b4370feeea94676502b42383c746',
                        },
                    },
                    {
                        'name': 'branch1',
                        'commit': {
                            'id': '6104942438c14ec7bd21c6cd5bd995272b3faff6',
                        },
                    },
                    {
                        'name': 'branch2',
                        'commit': {
                            'id': '21b3bcabcff2ab3dc3c9caa172f783aad602c0b0',
                        },
                    },
                    {
                        'branch-name': 'branch3',
                        'commit': {
                            'id': 'd5a3ff139356ce33e37e73add446f16869741b50',
                        },
                    },
                ]),
            },
            '%s?page=2' % base_url: {
                'payload': self.dump_json([
                    {
                        'name': 'branch4',
                        'commit': {
                            'id': 'abcff2ab321b3bcdc32f783aadc9caa172c0b060',
                        },
                    },
                    {
                        'name': 'branch5',
                        'commit': {
                            'id': '13933ffe33d5ae73adde3756c49741b5046f1686',
                        },
                    },
                ]),
            }
        }

        with self.setup_http_test(self.make_handler_for_paths(paths),
                                  expected_http_calls=2) as ctx:
            self._set_api_version(ctx.service, '4')

            repository = ctx.create_repository()
            branches = ctx.service.get_branches(repository)

        ctx.assertHTTPCall(
            0,
            url=('https://example.com/api/v4/projects/123456/repository/'
                 'branches'),
            username=None,
            password=None,
            headers={
                'Accept': 'application/json',
                'PRIVATE-TOKEN': 'abc123',
            })

        ctx.assertHTTPCall(
            1,
            url=('https://example.com/api/v4/projects/123456/repository/'
                 'branches?page=2'),
            username=None,
            password=None,
            headers={
                'Accept': 'application/json',
                'PRIVATE-TOKEN': 'abc123',
            })

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
                       default=False),
                Branch(id='branch4',
                       commit='abcff2ab321b3bcdc32f783aadc9caa172c0b060',
                       default=False),
                Branch(id='branch5',
                       commit='13933ffe33d5ae73adde3756c49741b5046f1686',
                       default=False),
            ])

    def test_get_branches_v3(self):
        """Testing GitLab.get_branches (API v3)"""
        paths = {
            '/api/v3/projects/123456/repository/branches': {
                'payload': self.dump_json([
                    {
                        'name': 'master',
                        'commit': {
                            'id': 'ed899a2f4b50b4370feeea94676502b42383c746',
                        },
                    },
                    {
                        'name': 'branch1',
                        'commit': {
                            'id': '6104942438c14ec7bd21c6cd5bd995272b3faff6',
                        },
                    },
                    {
                        'name': 'branch2',
                        'commit': {
                            'id': '21b3bcabcff2ab3dc3c9caa172f783aad602c0b0',
                        },
                    },
                    {
                        'branch-name': 'branch3',
                        'commit': {
                            'id': 'd5a3ff139356ce33e37e73add446f16869741b50',
                        },
                    },
                ]),
            },
        }

        with self.setup_http_test(self.make_handler_for_paths(paths),
                                  expected_http_calls=1) as ctx:
            self._set_api_version(ctx.service, '3')

            repository = ctx.create_repository()
            branches = ctx.service.get_branches(repository)

        ctx.assertHTTPCall(
            0,
            url=('https://example.com/api/v3/projects/123456/repository/'
                 'branches'),
            username=None,
            password=None,
            headers={
                'Accept': 'application/json',
                'PRIVATE-TOKEN': 'abc123',
            })

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
                       default=False),
            ])

    def test_get_commits_v4(self):
        """Testing GitLab.get_commits (API v4)"""
        self._test_get_commits(api_version='4')

    def test_get_commits_v3(self):
        """Testing GitLab.get_commits (API v3)"""
        self._test_get_commits(api_version='3')

    def test_get_change_v4(self):
        """Testing GitLab.get_change (API v4)"""
        self._test_get_change(api_version='4')

    def test_get_change_v3(self):
        """Testing GitLab.get_change (API v3)"""
        self._test_get_change(api_version='3')

    def test_get_file_v4(self):
        """Testing GitLab.get_file (API v4)"""
        self._test_get_file(
            api_version='4',
            expected_url=(
                'https://example.com/api/v4/projects/123456/repository/'
                'blobs/676502b42383c746ed899a2f4b50b4370feeea94/raw'))

    def test_get_file_with_base_commit_v3(self):
        """Testing GitLab.get_file with base commit ID (API v3)"""
        self._test_get_file(
            api_version='3',
            base_commit_id='ed899a2f4b50b4370feeea94676502b42383c746',
            expected_url=(
                'https://example.com/api/v3/projects/123456/repository/'
                'blobs/ed899a2f4b50b4370feeea94676502b42383c746'
                '?filepath=path/to/file.txt'))

    def test_get_file_without_base_commit_v3(self):
        """Testing GitLab.get_file without base commit ID (API v3)"""
        self._test_get_file(
            api_version='3',
            expected_url=(
                'https://example.com/api/v3/projects/123456/repository/'
                'raw_blobs/676502b42383c746ed899a2f4b50b4370feeea94'))

    def test_get_file_exists_with_exists_v4(self):
        """Testing GitLab.get_file_exists with exists (API v4)"""
        self._test_get_file_exists(
            api_version='4',
            should_exist=True,
            expected_url=(
                'https://example.com/api/v4/projects/123456/repository/'
                'blobs/676502b42383c746ed899a2f4b50b4370feeea94/raw'))

    def test_get_file_exists_with_not_exists_v4(self):
        """Testing GitLab.get_file_exists with not exists (API v4)"""
        self._test_get_file_exists(
            api_version='4',
            should_exist=False,
            expected_url=(
                'https://example.com/api/v4/projects/123456/repository/'
                'blobs/676502b42383c746ed899a2f4b50b4370feeea94/raw'))

    def test_get_file_exists_with_base_commit_and_exists_v3(self):
        """Testing GitLab.get_file_exists with base commit ID and exists
        (API v3)
        """
        self._test_get_file_exists(
            api_version='3',
            should_exist=True,
            base_commit_id='ed899a2f4b50b4370feeea94676502b42383c746',
            expected_url=(
                'https://example.com/api/v3/projects/123456/repository/'
                'blobs/ed899a2f4b50b4370feeea94676502b42383c746'
                '?filepath=path/to/file.txt'))

    def test_get_file_exists_without_base_commit_and_exists_v3(self):
        """Testing GitLab.get_file_exists without base commit ID and with
        exists
        (API v3)
        """
        self._test_get_file_exists(
            api_version='3',
            should_exist=True,
            expected_url=(
                'https://example.com/api/v3/projects/123456/repository/'
                'raw_blobs/676502b42383c746ed899a2f4b50b4370feeea94'))

    def test_get_file_exists_with_not_exists_v3(self):
        """Testing GitLab.get_file_exists with not exists (API v3)"""
        self._test_get_file_exists(
            api_version='3',
            should_exist=False,
            expected_url=(
                'https://example.com/api/v3/projects/123456/repository/'
                'raw_blobs/676502b42383c746ed899a2f4b50b4370feeea94'))

    def _test_check_authorize(self, *args, **kwargs):
        """Test authorizing a new account.

        Args:
            *args (tuple):
                Positional arguments for the HTTP test.

            **kwargs (dict):
                Keyword arguments for the HTTP test.

        Returns:
            reviewboard.hostingsvcs.testing.testcases.HttpTestContext:
            The context used for this test.
        """
        hosting_account = self.create_hosting_account(data={})
        self.assertFalse(hosting_account.is_authorized)

        with self.setup_http_test(hosting_account=hosting_account,
                                  *args, **kwargs) as ctx:
            ctx.service.authorize(
                'myuser',
                credentials={
                    'username': 'myuser',
                    'private_token': 'foobarbaz',
                },
                hosting_url='https://example.com')

        self.assertTrue(hosting_account.is_authorized)

        return ctx

    def _test_check_repository_v4(self, expected_owner='myuser', **kwargs):
        """Test checking for a repository using API v4.

        Args:
            expected_owner (unicode):
                The expected user/group name owning the repository.

            **kwargs (dict):
                Keyword arguments to pass to
                :py:meth:`check_repository()
                <reviewboard.hostingsvcs.gitlab.GitLab.check_repository>`.

        Returns:
            reviewboard.hostingsvcs.testing.testcases.HttpTestContext:
            The context used for this test.
        """
        with self.setup_http_test(payload=b'{"id": 12345}') as ctx:
            self._set_api_version(ctx.service, '4')
            ctx.service.check_repository(**kwargs)

        return ctx

    def _test_check_repository_v3(self, expected_owner='myuser', **kwargs):
        """Test checking for a repository using API v3.

        Args:
            expected_owner (unicode):
                The expected user/group name owning the repository.

            **kwargs (dict):
                Keyword arguments to pass to
                :py:meth:`check_repository()
                <reviewboard.hostingsvcs.gitlab.GitLab.check_repository>`.

        Returns:
            reviewboard.hostingsvcs.testing.testcases.HttpTestContext:
            The context used for this test.
        """
        paths = {
            '/api/v3/projects': {
                'payload': self.dump_json([
                    {
                        'id': 1,
                        'path': 'myrepo',
                        'namespace': {
                            'path': expected_owner,
                        },
                    },
                ]),
            },
            '/api/v3/groups': {
                'payload': self.dump_json([
                    {
                        'id': 1,
                        'name': 'mygroup',
                    },
                ]),
            },
            '/api/v3/groups/1': {
                'payload': self.dump_json({
                    'projects': [
                        {
                            'id': 1,
                            'name': 'myrepo',
                        }
                    ],
                }),
            },
        }

        with self.setup_http_test(self.make_handler_for_paths(paths)) as ctx:
            self._set_api_version(ctx.service, '3')
            ctx.service.check_repository(**kwargs)

        return ctx

    def _test_check_repository_error_v4(self, expected_error,
                                        expected_http_calls, **kwargs):
        """Test error conditions when checking for a repository using API v4.

        Args:
            expected_error (unicode):
                The expected error message from a raised exception.

            expected_http_calls (int):
                The number of expected HTTP calls.

            **kwargs (dict):
                Keyword arguments to pass to
                :py:meth:`check_repository()
                <reviewboard.hostingsvcs.gitlab.GitLab.check_repository>`.

        Returns:
            reviewboard.hostingsvcs.testing.testcases.HttpTestContext:
            The context used for this test.
        """
        with self.setup_http_test(expected_http_calls=expected_http_calls,
                                  status_code=404) as ctx:
            with self.assertRaisesMessage(RepositoryError, expected_error):
                self._set_api_version(ctx.service, '4')
                ctx.service.check_repository(**kwargs)

        return ctx

    def _test_check_repository_error_v3(self, expected_error,
                                        expected_http_calls, **kwargs):
        """Test error conditions when checking for a repository using API v3.

        Args:
            expected_error (unicode):
                The expected error message from a raised exception.

            expected_http_calls (int):
                The number of expected HTTP calls.

            **kwargs (dict):
                Keyword arguments to pass to
                :py:meth:`check_repository()
                <reviewboard.hostingsvcs.gitlab.GitLab.check_repository>`.

        Returns:
            reviewboard.hostingsvcs.testing.testcases.HttpTestContext:
            The context used for this test.
        """
        paths = {
            '/api/v3/groups': {
                'payload': self.dump_json([
                    {
                        'id': 1,
                        'name': 'mygroup',
                    },
                ]),
            },
            '/api/v3/projects': {
                'payload': self.dump_json([]),
            },
            '/api/v3/groups/1': {
                'payload': self.dump_json({
                    'projects': [
                        {
                            'id': 1,
                            'name': 'myrepo',
                        },
                    ],
                }),
            },
        }

        with self.setup_http_test(self.make_handler_for_paths(paths),
                                  expected_http_calls=expected_http_calls,
                                  ) as ctx:
            self._set_api_version(ctx.service, '3')

            with self.assertRaisesMessage(RepositoryError, expected_error):
                ctx.service.check_repository(**kwargs)

        return ctx

    def test_check_repository_with_api_version_not_found(self):
        """Testing GitLab.check_repository (API version not found)"""
        hosting_account = self.create_hosting_account(data={})
        self.assertFalse(hosting_account.is_authorized)

        message = (
            'Could not determine the GitLab API version for '
            'https://example.com due to an unexpected error (Unexpected path '
            '"/api/v4/projects?per_page=1"). Check to make sure the URL can '
            'be resolved from this server and that any SSL certificates are '
            'valid and trusted.'
        )

        with self.setup_http_test(self.make_handler_for_paths({}),
                                  hosting_account=hosting_account) as ctx:
            with self.assertRaisesMessage(GitLabAPIVersionError, message):
                ctx.service.check_repository(
                    plan='group',
                    gitlab_group_name='mygroup',
                    gitlab_group_repo_name='myrepo')

        ctx.assertHTTPCall(
            0,
            url='https://example.com/api/v4/projects?per_page=1',
            username=None,
            password=None,
            headers={})
        ctx.assertHTTPCall(
            1,
            url='https://example.com/api/v3/projects?per_page=1',
            username=None,
            password=None,
            headers={})

    def _test_get_file(self, api_version, expected_url, base_commit_id=None):
        """Common test for file retrieval.

        Args:
            api_version (unicode):
                The API version to test against.

            expected_url (unicode):
                The expected URL to fetch for the request.

            base_commit_id (unicode, optional):
                An optional base commit ID to specify during file retrieval.
        """
        with self.setup_http_test(payload=b'test data',
                                  expected_http_calls=1) as ctx:
            self._set_api_version(ctx.service, api_version)

            repository = ctx.create_repository()
            data = ctx.service.get_file(
                repository=repository,
                path='path/to/file.txt',
                revision='676502b42383c746ed899a2f4b50b4370feeea94',
                base_commit_id=base_commit_id)

        self.assertIsInstance(data, bytes)
        self.assertEqual(data, b'test data')

        ctx.assertHTTPCall(
            0,
            url=expected_url,
            username=None,
            password=None,
            headers={
                'PRIVATE-TOKEN': 'abc123',
            })

    def _test_get_file_exists(self, api_version, should_exist, expected_url,
                              base_commit_id=None):
        """Common test for file existence checks.

        Args:
            api_version (unicode):
                The API version to test against.

            should_exist (bool):
                Whether this should simulate that the file exists.

            expected_url (unicode):
                The expected URL to fetch for the request.

            base_commit_id (unicode, optional):
                An optional base commit ID to specify during file existence
                checks.
        """
        if should_exist:
            test_kwargs = {
                'payload': b'test data'
            }
        else:
            test_kwargs = {
                'status_code': 400,
            }

        with self.setup_http_test(expected_http_calls=1, **test_kwargs) as ctx:
            self._set_api_version(ctx.service, api_version)

            repository = ctx.create_repository()
            result = ctx.service.get_file_exists(
                repository=repository,
                path='path/to/file.txt',
                revision='676502b42383c746ed899a2f4b50b4370feeea94',
                base_commit_id=base_commit_id)

        self.assertEqual(result, should_exist)

        ctx.assertHTTPCall(
            0,
            url=expected_url,
            username=None,
            password=None,
            headers={
                'PRIVATE-TOKEN': 'abc123',
            })

    def _test_get_branches(self, api_version):
        """Common test for fetching branches.

        Args:
            api_version (unicode):
                The API version to test against.
        """

    def _test_get_commits(self, api_version):
        """Common test for fetching lists of commits.

        Args:
            api_version (unicode):
                The API version to test against.
        """
        payload = self.dump_json([
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

        with self.setup_http_test(payload=payload,
                                  expected_http_calls=1) as ctx:
            self._set_api_version(ctx.service, api_version)

            repository = ctx.create_repository()
            commits = ctx.service.get_commits(
                repository=repository,
                start='ed899a2f4b50b4370feeea94676502b42383c746')

        ctx.assertHTTPCall(
            0,
            url=('https://example.com/api/v%s/projects/123456/repository/'
                 'commits?per_page=21&ref_name='
                 'ed899a2f4b50b4370feeea94676502b42383c746'
                 % api_version),
            username=None,
            password=None,
            headers={
                'Accept': 'application/json',
                'PRIVATE-TOKEN': 'abc123',
            })

        self.assertEqual(
            commits,
            [
                Commit(author_name='Chester Li',
                       date='2015-03-10T11:50:22+03:00',
                       id='ed899a2f4b50b4370feeea94676502b42383c746',
                       message='Replace sanitize with escape once',
                       parent='6104942438c14ec7bd21c6cd5bd995272b3faff6'),
                Commit(author_name='Chester Li',
                       date='2015-03-10T09:06:12+03:00',
                       id='6104942438c14ec7bd21c6cd5bd995272b3faff6',
                       message='Sanitize for network graph',
                       parent='21b3bcabcff2ab3dc3c9caa172f783aad602c0b0'),
                Commit(author_name='East Coast',
                       date='2015-03-04T15:31:18.000-04:00',
                       id='21b3bcabcff2ab3dc3c9caa172f783aad602c0b0',
                       message='Add a timer to test file',
                       parent=''),
            ])

        for commit in commits:
            self.assertIsNone(commit.diff)

    def _test_get_change(self, api_version):
        """Common test for fetching individual commits.

        Args:
            api_version (unicode):
                The API version to test against.
        """
        commit_sha = 'ed899a2f4b50b4370feeea94676502b42383c746'
        diff_rsp = (
            b'---\n'
            b'f1 | 1 +\n'
            b'f2 | 1 +\n'
            b'2 files changed, 2 insertions(+), 0 deletions(-)\n'
            b'\n'
            b'diff --git a/f1 b/f1\n'
            b'index 11ac561..3ea0691 100644\n'
            b'--- a/f1\n'
            b'+++ b/f1\n'
            b'@@ -1 +1,2 @@\n'
            b' this is f1\n'
            b'+add one line to f1\n'
            b'diff --git a/f2 b/f2\n'
            b'index c837441..9302ecd 100644\n'
            b'--- a/f2\n'
            b'+++ b/f2\n'
            b'@@ -1 +1,2 @@\n'
            b' this is f2\n'
            b'+add one line to f2 with Unicode\xe2\x9d\xb6\n'
        )

        paths = {
            '/api/v%s/projects/123456/repository/commits/%s' % (api_version,
                                                                commit_sha): {
                'payload': self.dump_json({
                    'author_name': 'Chester Li',
                    'id': commit_sha,
                    'created_at': '2015-03-10T11:50:22+03:00',
                    'message': 'Replace sanitize with escape once',
                    'parent_ids': ['ae1d9fb46aa2b07ee9836d49862ec4e2c46fbbba'],
                }),
            },
            '/api/v%s/projects/123456' % api_version: {
                'payload': self.dump_json({
                    'path_with_namespace': 'myuser/myproject',
                }),
            },
            '/myuser/myproject/commit/%s.diff' % commit_sha: {
                'payload': diff_rsp,
            },
        }

        with self.setup_http_test(self.make_handler_for_paths(paths),
                                  expected_http_calls=3) as ctx:
            self._set_api_version(ctx.service, api_version)

            repository = ctx.create_repository()
            commit = ctx.service.get_change(repository=repository,
                                            revision=commit_sha)

        ctx.assertHTTPCall(
            0,
            url=('https://example.com/api/v%s/projects/123456/repository/'
                 'commits/%s'
                 % (api_version, commit_sha)),
            username=None,
            password=None,
            headers={
                'Accept': 'application/json',
                'PRIVATE-TOKEN': 'abc123',
            })

        ctx.assertHTTPCall(
            1,
            url=('https://example.com/api/v%s/projects/123456'
                 '?private_token=abc123'
                 % api_version),
            username=None,
            password=None,
            headers={
                'Accept': 'application/json',
                'PRIVATE-TOKEN': 'abc123',
            })

        ctx.assertHTTPCall(
            2,
            url=('https://example.com/myuser/myproject/commit/'
                 '%s.diff?private_token=abc123'
                 % commit_sha),
            username=None,
            password=None,
            headers={
                'Accept': 'text/plain',
                'PRIVATE-TOKEN': 'abc123',
            })

        self.assertEqual(
            commit,
            Commit(author_name='Chester Li',
                   date='2015-03-10T11:50:22+03:00',
                   id=commit_sha,
                   message='Replace sanitize with escape once',
                   parent='ae1d9fb46aa2b07ee9836d49862ec4e2c46fbbba'))
        self.assertEqual(commit.diff, diff_rsp)

    def _set_api_version(self, service, api_version):
        """Set the API version for a test.

        Args:
            service (reviewboard.hostingsvcs.gitlab.GitLab):
                The GitLab hosting service instance.

            api_version (unicode):
                The API version for the test.
        """
        self.spy_on(service._get_api_version,
                    call_fake=lambda self, hosting_url: api_version)


class GitLabHostingURLWidgetTests(GitLabTestCase):
    """Unit tests for reviewboard.hostingsvcs.gitlab.GitLabHostingURLWidget."""

    def test_render(self):
        """Testing GitLabHostingURLWidget.render"""
        widget = GitLabHostingURLWidget()
        content = widget.render(
            name='url',
            value='http://example.com/',
            attrs={
                'id': 'my-url',
                'data-foo': 'bar',
            })

        self.assertIsInstance(content, SafeText)
        self.assertInHTML(
            '<input type="text" id="my-url_custom_input"'
            ' value="http://example.com/" data-foo="bar">',
            content)
        self.assertInHTML(
            '<input type="hidden" id="my-url" name="url"'
            ' value="http://example.com/">',
            content)
