"""Unit tests for the Forgejo hosting service.

Version Added:
    7.1
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from typing import TYPE_CHECKING

import kgb
from djblets.testing.decorators import add_fixtures

from reviewboard.hostingsvcs.errors import (
    AuthorizationError,
    HostingServiceError,
    TwoFactorAuthCodeRequiredError,
)
from reviewboard.hostingsvcs.forgejo import Forgejo
from reviewboard.hostingsvcs.forgejo.client import ForgejoClient
from reviewboard.hostingsvcs.forgejo.errors import APITokenNameInUseError
from reviewboard.hostingsvcs.hook_utils import logger
from reviewboard.hostingsvcs.testing import HostingServiceTestCase
from reviewboard.reviews.models import ReviewRequest
from reviewboard.scmtools.crypto_utils import (
    decrypt_password,
    encrypt_password,
)
from reviewboard.scmtools.errors import FileNotFoundError
from reviewboard.site.models import LocalSite
from reviewboard.site.urlresolvers import local_site_reverse

if TYPE_CHECKING:
    from django.http import HttpResponse


class ForgejoTestCase(HostingServiceTestCase[Forgejo]):
    """Base class for Forgejo test suites.

    Version Added:
        7.1
    """

    service_name = 'forgejo'

    default_account_data = {
        'api_token': encrypt_password('test_token_123'),
    }

    default_repository_extra_data = {
        'repository_owner': 'testuser',
        'repository_name': 'testrepo',
    }

    default_hosting_url = 'https://forge.example.com'
    default_use_hosting_url = True


class ForgejoTests(ForgejoTestCase):
    """Unit tests for the Forgejo hosting service.

    Version Added:
        7.1
    """

    def test_service_support(self) -> None:
        """Testing Forgejo service support capabilities"""
        service_class = self.service_class
        assert service_class is not None
        self.assertTrue(service_class.supports_repositories)
        self.assertTrue(service_class.supports_post_commit)
        self.assertTrue(service_class.supports_two_factor_auth)
        self.assertTrue(service_class.self_hosted)
        self.assertEqual(service_class.supported_scmtools, ['Git'])

    def test_get_repository_fields(self) -> None:
        """Testing Forgejo.get_repository_fields"""
        fields = self.get_repository_fields(
            'Git',
            fields={
                'repository_owner': 'myowner',
                'repository_name': 'myrepo',
            }
        )

        self.assertEqual(fields, {
            'path': 'https://forge.example.com/myowner/myrepo.git',
        })

    def test_is_authorized_with_token(self) -> None:
        """Testing Forgejo.is_authorized with API token"""
        account = self.create_hosting_account()
        service = account.service

        self.assertTrue(service.is_authorized())

    def test_is_authorized_without_token(self) -> None:
        """Testing Forgejo.is_authorized without API token"""
        account = self.create_hosting_account(data={})
        service = account.service

        self.assertFalse(service.is_authorized())

    def test_authorize_success(self) -> None:
        """Testing Forgejo.authorize with valid credentials"""
        access_token_data = {
            'id': 1,
            'name': 'Review Board',
            'scopes': ['read:issue', 'read:organization', 'read:repository',
                       'read:user'],
            'sha1': 'new_test_token_456',
            'token_last_eight': '456',
        }

        account = self.create_hosting_account(data={})
        service = account.service

        self.assertFalse(service.is_authorized())

        handler = self.make_handler_for_paths({
            '/api/v1/users/myuser/tokens': {
                'payload': self.dump_json(access_token_data),
                'headers': {'Content-Type': 'application/json'},
            },
        })

        with self.setup_http_test(http_request_func=handler,
                                  expected_http_calls=1):
            service.authorize(
                username='myuser',
                password='testpass',
                hosting_url='https://forge.example.com',
                credentials={}
            )

        self.assertTrue(service.is_authorized())
        self.assertEqual(decrypt_password(account.data['api_token']),
                         'new_test_token_456')

    def test_authorize_with_two_factor_auth(self) -> None:
        """Testing Forgejo.authorize with two-factor authentication code"""
        access_token_data = {
            'id': 1,
            'name': 'Review Board',
            'scopes': ['read:issue', 'read:organization', 'read:repository',
                       'read:user'],
            'sha1': 'new_test_token_456',
            'token_last_eight': '456',
        }

        account = self.create_hosting_account(data={})
        service = account.service

        handler = self.make_handler_for_paths({
            '/api/v1/users/myuser/tokens': {
                'payload': self.dump_json(access_token_data),
                'headers': {'Content-Type': 'application/json'},
            },
        })

        with self.setup_http_test(http_request_func=handler,
                                  expected_http_calls=1):
            service.authorize(
                username='myuser',
                password='testpass',
                hosting_url='https://forge.example.com',
                credentials={},
                two_factor_auth_code='123456'
            )

        self.assertTrue(service.is_authorized())

    def test_authorize_invalid_credentials(self) -> None:
        """Testing Forgejo.authorize with invalid credentials"""
        error_data = {
            'message': 'invalid provided password',
            'url': 'https://forge.example.com/api/v1/users/myuser/tokens',
        }

        account = self.create_hosting_account(data={})
        service = account.service

        handler = self.make_handler_for_paths({
            '/api/v1/users/myuser/tokens': {
                'payload': self.dump_json(error_data),
                'status_code': 401,
                'headers': {'Content-Type': 'application/json'},
            },
        })

        message = 'username or password is incorrect'

        with self.setup_http_test(http_request_func=handler,
                                  expected_http_calls=1), \
             self.assertRaisesMessage(AuthorizationError,
                                      message):
            service.authorize(
                username='myuser',
                password='wrongpass',
                hosting_url='https://forge.example.com',
                credentials={}
            )

    def test_authorize_two_factor_required(self) -> None:
        """Testing Forgejo.authorize when two-factor auth is required"""
        error_data = {
            'message': 'invalid provided OTP',
            'url': 'https://forge.example.com/api/v1/users/myuser/tokens',
        }

        account = self.create_hosting_account(data={})
        service = account.service

        handler = self.make_handler_for_paths({
            '/api/v1/users/myuser/tokens': {
                'payload': self.dump_json(error_data),
                'status_code': 400,
                'headers': {'Content-Type': 'application/json'},
            },
        })

        with self.setup_http_test(http_request_func=handler,
                                  expected_http_calls=1), \
             self.assertRaises(TwoFactorAuthCodeRequiredError):
            service.authorize(
                username='myuser',
                password='testpass',
                hosting_url='https://forge.example.com',
                credentials={}
            )

    def test_authorize_with_token_name_retry_success(self) -> None:
        """Testing Forgejo.authorize with successful retry after duplicate
        token name
        """
        account = self.create_hosting_account(data={})
        service = account.service
        client = service.client
        assert isinstance(client, ForgejoClient)

        self.spy_on(
            client.create_api_token,
            op=kgb.SpyOpMatchInOrder([
                {
                    'op': kgb.SpyOpRaise(APITokenNameInUseError()),
                },
                {
                    'op': kgb.SpyOpReturn('retry_success_token_456'),
                }
            ]))

        service.authorize(
            username='myuser',
            password='testpass',
            hosting_url='https://forge.example.com',
            credentials={}
        )

        self.assertTrue(service.is_authorized())
        self.assertEqual(decrypt_password(account.data['api_token']),
                         'retry_success_token_456')

    def test_authorize_with_max_retries_exceeded(self) -> None:
        """Testing Forgejo.authorize fails after maximum retries due to
        duplicate token names
        """
        account = self.create_hosting_account(data={})
        service = account.service
        client = service.client
        assert isinstance(client, ForgejoClient)

        self.spy_on(client.create_api_token,
                    op=kgb.SpyOpRaise(APITokenNameInUseError()))

        message = (
            'Unable to create a Forgejo API token with a unique name after 5 '
            'attempts for user myuser on server https://forge.example.com'
        )

        with self.assertRaisesMessage(HostingServiceError, message):
            service.authorize(
                username='myuser',
                password='testpass',
                hosting_url='https://forge.example.com',
                credentials={}
            )

        self.assertFalse(service.is_authorized())

        spy = self.get_spy(client.create_api_token)
        self.assertEqual(len(spy.calls), 5)

    def test_create_api_token_name(self) -> None:
        """Testing Forgejo._create_api_token_name generates unique names"""
        account = self.create_hosting_account(data={})
        service = account.service
        assert isinstance(service, Forgejo)

        # Test that token names are generated with correct format
        token_name1 = service._create_api_token_name('example.com')
        token_name2 = service._create_api_token_name('example.com')

        # Both should start with 'reviewboard-example.com-'
        self.assertTrue(token_name1.startswith('reviewboard-example.com-'))
        self.assertTrue(token_name2.startswith('reviewboard-example.com-'))

        # They should be different (due to UUID)
        self.assertNotEqual(token_name1, token_name2)

        # Both should have the expected structure
        parts1 = token_name1.split('-')
        parts2 = token_name2.split('-')

        self.assertEqual(len(parts1), 3)
        self.assertEqual(len(parts2), 3)

        self.assertEqual(parts1[0], 'reviewboard')
        self.assertEqual(parts1[1], 'example.com')
        self.assertEqual(len(parts1[2]), 6)  # UUID hex should be 6 chars

        self.assertEqual(parts2[0], 'reviewboard')
        self.assertEqual(parts2[1], 'example.com')
        self.assertEqual(len(parts2[2]), 6)

    def test_create_api_token_name_truncates_long_server_name(self) -> None:
        """Testing Forgejo._create_api_token_name truncates server names to
        stay within 255 char limit
        """
        account = self.create_hosting_account(data={})
        service = account.service
        assert isinstance(service, Forgejo)

        long_server_name = ('a' * 250) + '.com'

        token_name = service._create_api_token_name(long_server_name)
        self.assertEqual(len(token_name), 255)

    def test_get_file(self) -> None:
        """Testing Forgejo.get_file"""
        file_content = b'def main():\n    print("Hello, World!")\n'
        encoded_content = base64.b64encode(file_content).decode('utf-8')

        blob_data = {
            'content': encoded_content,
            'encoding': 'base64',
            'sha': 'abc123def456',
            'size': len(file_content),
            'url': 'https://forge.example.com/api/v1/repos/testuser/testrepo/'
                   'git/blobs/abc123def456',
        }

        account = self.create_hosting_account()
        repository = self.create_repository(hosting_account=account)
        service = account.service

        handler = self.make_handler_for_paths({
            '/api/v1/repos/testuser/testrepo/git/blobs/abc123def456': {
                'payload': self.dump_json(blob_data),
                'headers': {'Content-Type': 'application/json'},
            },
        })

        with self.setup_http_test(http_request_func=handler,
                                  expected_http_calls=1):
            content = service.get_file(
                repository=repository,
                path='main.py',
                revision='abc123def456'
            )

        self.assertEqual(content, file_content)

    def test_get_file_not_found(self) -> None:
        """Testing Forgejo.get_file with file not found"""
        account = self.create_hosting_account()
        repository = self.create_repository(hosting_account=account)
        service = account.service

        handler = self.make_handler_for_paths({
            '/api/v1/repos/testuser/testrepo/git/blobs/abc123def456': {
                'status_code': 400,
                'payload': json.dumps({
                    'message': 'object does not exist [id: abc123def456, '
                               'rel_path: ]',
                    'url': '/api/v1/repos/testuser/testrepo/git/blobs/'
                           'abc123def456',
                }).encode(),
            },
        })

        with self.setup_http_test(http_request_func=handler,
                                  expected_http_calls=1), \
             self.assertRaises(FileNotFoundError):
            service.get_file(
                repository=repository,
                path='nonexistent.py',
                revision='abc123def456'
            )

    def test_get_file_repo_invalid(self) -> None:
        """Testing Forgejo.get_file with an invalid repository name"""
        account = self.create_hosting_account()
        repository = self.create_repository(hosting_account=account)
        service = account.service

        handler = self.make_handler_for_paths({
            '/api/v1/repos/testuser/testrepo/git/blobs/abc123def456': {
                'status_code': 404,
                'payload': json.dumps({
                    'errors': [],
                    'message': "The target couldn't be found.",
                    'url': '/api/v1/repos/testuser/testrepo/git/blobs/'
                           'abc123def456',
                }).encode(),
            },
        })

        with self.setup_http_test(http_request_func=handler,
                                  expected_http_calls=1), \
             self.assertRaises(HostingServiceError):
            service.get_file(
                repository=repository,
                path='nonexistent.py',
                revision='abc123def456'
            )

    def test_get_branches(self) -> None:
        """Testing Forgejo.get_branches"""
        repo_data = {
            'clone_url': 'https://forge.example.com/testuser/testrepo.git',
            'default_branch': 'main',
            'description': 'My repo',
            'id': 1,
            'name': 'testrepo',
            'private': False,
        }

        refs_data = [
            {
                'object': {
                    'sha': 'abc123',
                    'type': 'commit',
                    'url': 'https://forge.example.com/api/v1/repos/testuser/'
                           'testrepo/git/commits/abc123',
                },
                'ref': 'refs/heads/main',
                'url': 'https://forge.example.com/api/v1/repos/testuser/'
                       'testrepo/git/refs/heads/main',
            },
            {
                'object': {
                    'sha': 'def456',
                    'type': 'commit',
                    'url': 'https://forge.example.com/api/v1/repos/testuser/'
                           'testrepo/git/commits/def456',
                },
                'ref': 'refs/heads/feature',
                'url': 'https://forge.example.com/api/v1/repos/testuser/'
                       'testrepo/git/refs/heads/feature',
            }
        ]

        account = self.create_hosting_account()
        repository = self.create_repository(hosting_account=account)
        service = account.service

        handler = self.make_handler_for_paths({
            '/api/v1/repos/testuser/testrepo': {
                'payload': self.dump_json(repo_data),
                'headers': {'Content-Type': 'application/json'},
            },
            '/api/v1/repos/testuser/testrepo/git/refs': {
                'payload': self.dump_json(refs_data),
                'headers': {'Content-Type': 'application/json'},
            },
        })

        with self.setup_http_test(http_request_func=handler,
                                  expected_http_calls=2):
            branches = service.get_branches(repository)

        self.assertEqual(len(branches), 2)

        main_branch = next(b for b in branches if b.id == 'main')
        self.assertEqual(main_branch.commit, 'abc123')
        self.assertTrue(main_branch.default)

        feature_branch = next(b for b in branches if b.id == 'feature')
        self.assertEqual(feature_branch.commit, 'def456')
        self.assertFalse(feature_branch.default)

    def test_get_commits(self) -> None:
        """Testing Forgejo.get_commits"""
        commits_data = [
            {
                'commit': {
                    'author': {
                        'date': '2023-01-01T12:00:00Z',
                        'email': 'user@example.com',
                        'name': 'Test User',
                    },
                    'committer': {
                        'date': '2023-01-01T12:00:00Z',
                        'email': 'user@example.com',
                        'name': 'Test User',
                    },
                    'message': 'Initial commit',
                    'tree': {
                        'created': '2023-01-01T12:00:00Z',
                        'sha': 'tree123',
                        'url': 'https://forge.example.com/api/v1/repos/'
                               'testuser/testrepo/git/trees/tree123',
                    }
                },
                'created': '2023-01-01T12:00:00Z',
                'parents': [],
                'sha': 'commit123',
            }
        ]

        account = self.create_hosting_account()
        repository = self.create_repository(hosting_account=account)
        service = account.service

        handler = self.make_handler_for_paths({
            '/api/v1/repos/testuser/testrepo/commits': {
                'payload': self.dump_json(commits_data),
                'headers': {'Content-Type': 'application/json'},
            },
        })

        with self.setup_http_test(http_request_func=handler,
                                  expected_http_calls=1):
            commits = service.get_commits(repository, branch='main')

        self.assertEqual(len(commits), 1)
        commit = commits[0]
        self.assertEqual(commit.author_name, 'Test User')
        self.assertEqual(commit.id, 'commit123')
        self.assertEqual(commit.message, 'Initial commit')
        self.assertEqual(commit.parent, '')

    def test_get_commits_with_no_start(self) -> None:
        """Testing Forgejo.get_commits with no start point"""
        account = self.create_hosting_account()
        repository = self.create_repository(hosting_account=account)
        service = account.service

        with self.assertRaises(ValueError):
            service.get_commits(repository)

    def test_get_change(self) -> None:
        """Testing Forgejo.get_change"""
        commit_data = {
            'commit': {
                'author': {
                    'date': '2023-01-01T12:00:00Z',
                    'email': 'user@example.com',
                    'name': 'Test User',
                },
                'committer': {
                    'date': '2023-01-01T12:00:00Z',
                    'email': 'user@example.com',
                    'name': 'Test User',
                },
                'message': 'Add new feature',
                'tree': {
                    'created': '2023-01-01T12:00:00Z',
                    'sha': 'tree123',
                    'url': 'https://forge.example.com/api/v1/repos/testuser/'
                           'testrepo/git/trees/tree123',
                }
            },
            'created': '2023-01-01T12:00:00Z',
            'parents': [
                {
                    'created': '2023-01-01T11:00:00Z',
                    'sha': 'parent123',
                    'url': '/api/v1/repos/testuser/testrepo/git/commits/'
                           'parent123',
                },
            ],
            'sha': 'commit456',
        }

        tree_data = {
            'page': 1,
            'sha': 'tree123',
            'total_count': 1,
            'tree': [
                {
                    'path': 'file.py',
                    'sha': 'file123',
                    'size': 100,
                    'type': 'blob',
                }
            ],
            'truncated': False
        }

        diff_content = (
            b'diff --git a/file.py b/file.py\n'
            b'index abc123..def456 100644\n'
            b'--- a/file.py\n'
            b'+++ b/file.py\n'
            b'@@ -1 +1,2 @@\n'
            b' print("Hello")\n'
            b'+print("World")\n'
        )

        account = self.create_hosting_account()
        repository = self.create_repository(hosting_account=account)
        service = account.service

        handler = self.make_handler_for_paths({
            '/api/v1/repos/testuser/testrepo/git/commits/commit456': {
                'payload': self.dump_json(commit_data),
                'headers': {'Content-Type': 'application/json'},
            },
            '/api/v1/repos/testuser/testrepo/git/commits/commit456.diff': {
                'payload': diff_content,
                'headers': {'Content-Type': 'text/plain'},
            },
            '/api/v1/repos/testuser/testrepo/git/trees/commit456': {
                'payload': self.dump_json(tree_data),
                'headers': {'Content-Type': 'application/json'},
            },
            '/api/v1/repos/testuser/testrepo/git/trees/parent123': {
                'payload': self.dump_json(tree_data),
                'headers': {'Content-Type': 'application/json'},
            },
        })

        with self.setup_http_test(http_request_func=handler,
                                  expected_http_calls=4):
            commit = service.get_change(repository, 'commit456')

        self.assertEqual(commit.author_name, 'Test User')
        self.assertEqual(commit.id, 'commit456')
        self.assertEqual(commit.message, 'Add new feature')
        self.assertEqual(commit.parent, 'parent123')
        self.assertIsNotNone(commit.diff)

    def test_get_bug_info_uncached(self) -> None:
        """Testing Forgejo.get_bug_info_uncached"""
        issue_data = {
            'body': 'This is a test issue description with multiple lines.\n'
                    'It should be properly returned in the bug info.',
            'id': 123,
            'state': 'open',
            'title': 'Test Issue Title',
        }

        account = self.create_hosting_account()
        repository = self.create_repository(hosting_account=account)
        service = account.service
        assert isinstance(service, Forgejo)

        handler = self.make_handler_for_paths({
            '/api/v1/repos/testuser/testrepo/issues/123': {
                'payload': self.dump_json(issue_data),
                'headers': {'Content-Type': 'application/json'},
            },
        })

        with self.setup_http_test(http_request_func=handler,
                                  expected_http_calls=1):
            bug_info = service.get_bug_info_uncached(repository, '123')

        self.assertEqual(bug_info, {
            'description':
                'This is a test issue description with multiple lines.\n'
                'It should be properly returned in the bug info.',
            'description_text_format': 'markdown',
            'status': 'open',
            'summary': 'Test Issue Title',
        })

    def test_get_bug_info_uncached_issue_not_found(self) -> None:
        """Testing Forgejo.get_bug_info_uncached with issue not found"""
        account = self.create_hosting_account()
        repository = self.create_repository(hosting_account=account)
        service = account.service
        assert isinstance(service, Forgejo)

        handler = self.make_handler_for_paths({
            '/api/v1/repos/testuser/testrepo/issues/999': {
                'status_code': 404,
                'payload': json.dumps({
                    'message': 'Not Found',
                    'url': '/api/v1/repos/testuser/testrepo/issues/999',
                }).encode(),
            },
        })

        with self.setup_http_test(http_request_func=handler,
                                  expected_http_calls=1):
            bug_info = service.get_bug_info_uncached(repository, '999')

        self.assertEqual(bug_info, {
            'description': '',
            'status': '',
            'summary': '',
        })

    def test_get_bug_info_uncached_api_error(self) -> None:
        """Testing Forgejo.get_bug_info_uncached with API error"""
        account = self.create_hosting_account()
        repository = self.create_repository(hosting_account=account)
        service = account.service
        assert isinstance(service, Forgejo)

        handler = self.make_handler_for_paths({
            '/api/v1/repos/testuser/testrepo/issues/456': {
                'status_code': 500,
                'payload': json.dumps({
                    'message': 'Internal server error',
                    'url': '/api/v1/repos/testuser/testrepo/issues/456',
                }).encode(),
            },
        })

        with self.setup_http_test(http_request_func=handler,
                                  expected_http_calls=1):
            bug_info = service.get_bug_info_uncached(repository, '456')

        self.assertEqual(bug_info, {
            'description': '',
            'status': '',
            'summary': '',
        })


class ForgejoClientTests(ForgejoTestCase):
    """Unit tests for the ForgejoClient

    Version Added:
        7.1
    """

    def test_get_http_credentials_with_token(self) -> None:
        """Testing ForgejoClient.get_http_credentials with API token"""
        account = self.create_hosting_account()
        client = account.service.client

        credentials = client.get_http_credentials(account)

        expected_token = decrypt_password(account.data['api_token'])
        self.assertEqual(expected_token, 'test_token_123')
        self.assertEqual(credentials, {
            'header': {
                'Authorization': f'token {expected_token}',
            },
        })

    def test_get_http_credentials_without_token(self) -> None:
        """Testing ForgejoClient.get_http_credentials without API token"""
        account = self.create_hosting_account(data={})
        client = account.service.client

        credentials = client.get_http_credentials(account)

        self.assertEqual(credentials, {})

    def test_create_api_token(self) -> None:
        """Testing ForgejoClient.create_api_token"""
        access_token_data = {
            'id': 1,
            'name': 'Review Board',
            'scopes': ['read:issue', 'read:organization', 'read:repository',
                       'read:user'],
            'sha1': 'new_api_token_789',
            'token_last_eight': '789',
        }

        account = self.create_hosting_account()
        client = account.service.client
        assert isinstance(client, ForgejoClient)

        handler = self.make_handler_for_paths({
            '/api/v1/users/myuser/tokens': {
                'payload': self.dump_json(access_token_data),
                'headers': {'Content-Type': 'application/json'},
            },
        })

        with self.setup_http_test(http_request_func=handler,
                                  expected_http_calls=1):
            token = client.create_api_token(
                token_name='Review Board',
                hosting_url='https://forge.example.com',
                username='myuser',
                password='testpass',
            )

        self.assertEqual(token, 'new_api_token_789')

    def test_get_blob(self) -> None:
        """Testing ForgejoClient.get_blob"""
        file_content = b'print("Hello from Forgejo!")'
        encoded_content = base64.b64encode(file_content).decode('utf-8')

        blob_data = {
            'content': encoded_content,
            'encoding': 'base64',
            'sha': 'blob789',
            'size': len(file_content),
            'url': 'https://forge.example.com/api/v1/repos/testuser/testrepo/'
                   'git/blobs/blob789',
        }

        account = self.create_hosting_account()
        repository = self.create_repository(hosting_account=account)
        client = account.service.client
        assert isinstance(client, ForgejoClient)

        handler = self.make_handler_for_paths({
            '/api/v1/repos/testuser/testrepo/git/blobs/blob789': {
                'payload': self.dump_json(blob_data),
                'headers': {'Content-Type': 'application/json'},
            },
        })

        with self.setup_http_test(http_request_func=handler,
                                  expected_http_calls=1):
            content = client.get_blob(
                hosting_url='https://forge.example.com',
                repository=repository,
                path='hello.py',
                sha='blob789',
            )

        self.assertEqual(content, file_content)

    def test_get_blob_unsupported_encoding(self) -> None:
        """Testing ForgejoClient.get_blob with unsupported encoding"""
        blob_data = {
            'content': 'raw content',
            'encoding': 'raw',
            'sha': 'blob789',
            'size': 11,
            'url': 'https://forge.example.com/api/v1/repos/testuser/testrepo/'
                   'git/blobs/blob789',
        }

        account = self.create_hosting_account()
        repository = self.create_repository(hosting_account=account)
        client = account.service.client
        assert isinstance(client, ForgejoClient)

        handler = self.make_handler_for_paths({
            '/api/v1/repos/testuser/testrepo/git/blobs/blob789': {
                'payload': self.dump_json(blob_data),
                'headers': {'Content-Type': 'application/json'},
            },
        })

        message = 'Forgejo returned data with an unknown encoding.'

        with self.setup_http_test(http_request_func=handler,
                                  expected_http_calls=1), \
             self.assertRaisesMessage(HostingServiceError,
                                      message):
            client.get_blob(
                hosting_url='https://forge.example.com',
                repository=repository,
                path='hello.py',
                sha='blob789',
            )

    def test_api_root_generation(self) -> None:
        """Testing ForgejoClient._get_api_root"""
        account = self.create_hosting_account()
        client = account.service.client
        assert isinstance(client, ForgejoClient)

        # Test with trailing slash
        self.assertEqual(
            client._get_api_root('https://forge.example.com/'),
            'https://forge.example.com/api/v1'
        )

        # Test without trailing slash
        self.assertEqual(
            client._get_api_root('https://forge.example.com'),
            'https://forge.example.com/api/v1'
        )

    def test_api_repo_root_generation(self) -> None:
        """Testing ForgejoClient._get_api_repo_root"""
        account = self.create_hosting_account()
        repository = self.create_repository(hosting_account=account)
        client = account.service.client
        assert isinstance(client, ForgejoClient)

        repo_root = client._get_api_repo_root(
            'https://forge.example.com',
            repository
        )

        self.assertEqual(
            repo_root,
            'https://forge.example.com/api/v1/repos/testuser/testrepo'
        )


class ForgejoCloseSubmittedHookTests(ForgejoTestCase):
    """Unit tests for the Forgejo close-submitted webhook.

    Version Added:
        7.1
    """

    fixtures = ['test_users', 'test_scmtools']

    def test_hook(self) -> None:
        """Testing Forgejo close_submitted hook with event=push"""
        self._test_post_commit_hook()

    @add_fixtures(['test_site'])
    def test_hook_with_local_site(self) -> None:
        """Testing Forgejo close_submitted hook with event=push and using a
        Local Site
        """
        self._test_post_commit_hook(
            LocalSite.objects.get(name=self.local_site_name))

    @add_fixtures(['test_site'])
    def test_hook_with_unpublished_review_request(self) -> None:
        """Testing Forgejo close_submitted hook with event=push and an
        un-published review request
        """
        self._test_post_commit_hook(publish=False)

    def test_hook_with_invalid_repo(self) -> None:
        """Testing Forgejo close_submitted hook with event=push and invalid
        repository
        """
        repository = self.create_repository()

        review_request = self.create_review_request(repository=repository,
                                                    publish=True)
        self.assertTrue(review_request.public)
        self.assertEqual(review_request.status, review_request.PENDING_REVIEW)

        url = local_site_reverse(
            'forgejo-hooks-close-submitted',
            kwargs={
                'repository_id': repository.pk,
                'hosting_service_id': 'forgejo',
            })

        response = self._post_commit_hook_payload(
            post_url=url,
            review_request_url=review_request.get_absolute_url(),
            secret=repository.get_or_create_hooks_uuid())
        self.assertEqual(response.status_code, 404)

        review_request = ReviewRequest.objects.get(pk=review_request.pk)
        self.assertTrue(review_request.public)
        self.assertEqual(review_request.status, review_request.PENDING_REVIEW)
        self.assertEqual(review_request.changedescs.count(), 0)

    def test_hook_with_invalid_site(self) -> None:
        """Testing Forgejo close_submitted hook with event=push and invalid
        Local Site
        """
        account = self.create_hosting_account()
        repository = self.create_repository(hosting_account=account)

        review_request = self.create_review_request(repository=repository,
                                                    publish=True)
        self.assertTrue(review_request.public)
        self.assertEqual(review_request.status, review_request.PENDING_REVIEW)

        url = local_site_reverse(
            'forgejo-hooks-close-submitted',
            local_site_name='badsite',
            kwargs={
                'repository_id': repository.pk,
                'hosting_service_id': 'forgejo',
            })

        response = self._post_commit_hook_payload(
            post_url=url,
            review_request_url=review_request.get_absolute_url(),
            secret=repository.get_or_create_hooks_uuid())
        self.assertEqual(response.status_code, 404)

        review_request = ReviewRequest.objects.get(pk=review_request.pk)
        self.assertTrue(review_request.public)
        self.assertEqual(review_request.status, review_request.PENDING_REVIEW)
        self.assertEqual(review_request.changedescs.count(), 0)

    def test_hook_with_invalid_service_id(self) -> None:
        """Testing Forgejo close_submitted hook with event=push and invalid
        hosting service ID
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
            'forgejo-hooks-close-submitted',
            kwargs={
                'repository_id': repository.pk,
                'hosting_service_id': 'forgejo',
            })

        response = self._post_commit_hook_payload(
            post_url=url,
            review_request_url=review_request.get_absolute_url(),
            secret=repository.get_or_create_hooks_uuid())
        self.assertEqual(response.status_code, 404)

        review_request = ReviewRequest.objects.get(pk=review_request.pk)
        self.assertTrue(review_request.public)
        self.assertEqual(review_request.status, review_request.PENDING_REVIEW)
        self.assertEqual(review_request.changedescs.count(), 0)

    def test_hook_with_invalid_event(self) -> None:
        """Testing Forgejo close_submitted hook with invalid event"""
        account = self.create_hosting_account()
        repository = self.create_repository(hosting_account=account)
        review_request = self.create_review_request(repository=repository,
                                                    publish=True)
        self.assertTrue(review_request.public)
        self.assertEqual(review_request.status, review_request.PENDING_REVIEW)

        url = local_site_reverse(
            'forgejo-hooks-close-submitted',
            kwargs={
                'repository_id': repository.pk,
                'hosting_service_id': 'forgejo',
            })

        response = self._post_commit_hook_payload(
            post_url=url,
            review_request_url=review_request.get_absolute_url(),
            secret=repository.get_or_create_hooks_uuid(),
            event='issues')
        self.assertEqual(response.status_code, 400)

        review_request = ReviewRequest.objects.get(pk=review_request.pk)
        self.assertTrue(review_request.public)
        self.assertEqual(review_request.status, review_request.PENDING_REVIEW)
        self.assertEqual(review_request.changedescs.count(), 0)

    def test_hook_with_missing_signature(self) -> None:
        """Testing Forgejo close_submitted hook with missing signature"""
        account = self.create_hosting_account()
        repository = self.create_repository(hosting_account=account)
        review_request = self.create_review_request(repository=repository,
                                                    publish=True)
        self.assertTrue(review_request.public)
        self.assertEqual(review_request.status, review_request.PENDING_REVIEW)

        url = local_site_reverse(
            'forgejo-hooks-close-submitted',
            kwargs={
                'repository_id': repository.pk,
                'hosting_service_id': 'forgejo',
            })

        payload = self.dump_json({
            'ref': 'refs/heads/main',
            'commits': [
                {
                    'id': '1c44b461cebe5874a857c51a4a13a849a4d1e52d',
                    'message': (
                        f'This is my fancy commit\n'
                        f'\n'
                        f'Reviewed at '
                        f'http://example.com'
                        f'{review_request.get_absolute_url()}'
                    ),
                },
            ]
        })

        response = self.client.post(
            url,
            payload,
            content_type='application/json',
            HTTP_X_FORGEJO_EVENT='push')
        self.assertEqual(response.status_code, 400)

        review_request = ReviewRequest.objects.get(pk=review_request.pk)
        self.assertTrue(review_request.public)
        self.assertEqual(review_request.status, review_request.PENDING_REVIEW)
        self.assertEqual(review_request.changedescs.count(), 0)

    def test_hook_with_invalid_signature(self) -> None:
        """Testing Forgejo close_submitted hook with invalid signature"""
        account = self.create_hosting_account()
        repository = self.create_repository(hosting_account=account)
        review_request = self.create_review_request(repository=repository,
                                                    publish=True)
        self.assertTrue(review_request.public)
        self.assertEqual(review_request.status, review_request.PENDING_REVIEW)

        url = local_site_reverse(
            'forgejo-hooks-close-submitted',
            kwargs={
                'repository_id': repository.pk,
                'hosting_service_id': 'forgejo',
            })

        response = self._post_commit_hook_payload(
            post_url=url,
            review_request_url=review_request.get_absolute_url(),
            secret='bad-secret')
        self.assertEqual(response.status_code, 400)

        review_request = ReviewRequest.objects.get(pk=review_request.pk)
        self.assertTrue(review_request.public)
        self.assertEqual(review_request.status, review_request.PENDING_REVIEW)
        self.assertEqual(review_request.changedescs.count(), 0)

    def test_hook_with_invalid_review_requests(self) -> None:
        """Testing Forgejo close_submitted hook with event=push and invalid
        review requests
        """
        self.spy_on(logger.error)

        account = self.create_hosting_account()
        repository = self.create_repository(hosting_account=account)

        review_request = self.create_review_request(repository=repository,
                                                    publish=True)
        self.assertTrue(review_request.public)
        self.assertEqual(review_request.status, review_request.PENDING_REVIEW)

        url = local_site_reverse(
            'forgejo-hooks-close-submitted',
            kwargs={
                'repository_id': repository.pk,
                'hosting_service_id': 'forgejo',
            })

        response = self._post_commit_hook_payload(
            post_url=url,
            review_request_url='/r/9999/',
            secret=repository.get_or_create_hooks_uuid())
        self.assertEqual(response.status_code, 200)

        review_request = ReviewRequest.objects.get(pk=review_request.pk)
        self.assertTrue(review_request.public)
        self.assertEqual(review_request.status, review_request.PENDING_REVIEW)
        self.assertEqual(review_request.changedescs.count(), 0)

        self.assertSpyCalledWith(
            logger.error,
            'close_all_review_requests: Review request #%s does not exist.',
            9999)

    def test_hook_with_invalid_json(self) -> None:
        """Testing Forgejo close_submitted hook with invalid JSON payload"""
        account = self.create_hosting_account()
        repository = self.create_repository(hosting_account=account)
        review_request = self.create_review_request(repository=repository,
                                                    publish=True)
        self.assertTrue(review_request.public)
        self.assertEqual(review_request.status, review_request.PENDING_REVIEW)

        url = local_site_reverse(
            'forgejo-hooks-close-submitted',
            kwargs={
                'repository_id': repository.pk,
                'hosting_service_id': 'forgejo',
            })

        invalid_payload = b'invalid json'
        secret = repository.get_or_create_hooks_uuid()
        m = hmac.new(secret.encode('utf-8'), invalid_payload, hashlib.sha256)

        response = self.client.post(
            url,
            invalid_payload,
            content_type='application/json',
            HTTP_X_FORGEJO_EVENT='push',
            HTTP_X_FORGEJO_SIGNATURE=m.hexdigest())
        self.assertEqual(response.status_code, 400)

        review_request = ReviewRequest.objects.get(pk=review_request.pk)
        self.assertTrue(review_request.public)
        self.assertEqual(review_request.status, review_request.PENDING_REVIEW)
        self.assertEqual(review_request.changedescs.count(), 0)

    def _test_post_commit_hook(
        self,
        local_site: (LocalSite | None) = None,
        publish: bool = True,
    ) -> None:
        """Test posting to a commit hook.

        This will simulate pushing a commit and posting the resulting webhook
        payload from Forgejo to the handler for the hook.

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
            'forgejo-hooks-close-submitted',
            local_site=local_site,
            kwargs={
                'repository_id': repository.pk,
                'hosting_service_id': 'forgejo',
            })

        response = self._post_commit_hook_payload(
            post_url=url,
            review_request_url=review_request.get_absolute_url(),
            secret=repository.get_or_create_hooks_uuid())
        self.assertEqual(response.status_code, 200)

        review_request = ReviewRequest.objects.get(pk=review_request.pk)
        self.assertTrue(review_request.public)
        self.assertEqual(review_request.status, review_request.SUBMITTED)
        self.assertEqual(review_request.changedescs.count(), 1)

        changedesc = review_request.changedescs.get()
        self.assertEqual(changedesc.text, 'Pushed to main (1c44b46)')

    def _post_commit_hook_payload(
        self,
        post_url: str,
        review_request_url: str,
        secret: str,
        event: str = 'push'
    ) -> HttpResponse:
        """Post a payload for a hook for testing.

        Args:
            post_url (str):
                The URL to post to.

            review_request_url (str):
                The URL of the review request being represented in the
                payload.

            secret (str):
                The HMAC secret for the message.

            event (str, optional):
                The webhook event.

        Returns:
            django.http.HttpResponse:
            The response from the post request.
        """
        payload = json.dumps({
            # NOTE: This payload only contains the content we make
            #       use of in the hook.
            'ref': 'refs/heads/main',
            'commits': [
                {
                    'id': '1c44b461cebe5874a857c51a4a13a849a4d1e52d',
                    'message':
                        f'This is my fancy commit\n'
                        f'\n'
                        f'Reviewed at http://example.com{review_request_url}',
                },
            ]
        }).encode()

        m = hmac.new(secret.encode('utf-8'), payload, hashlib.sha256)

        return self.client.post(  # type:ignore
            post_url,
            payload,
            content_type='application/json',
            HTTP_X_FORGEJO_EVENT=event,
            HTTP_X_FORGEJO_SIGNATURE=m.hexdigest())
