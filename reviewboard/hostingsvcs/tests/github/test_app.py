"""Unit tests for GitHub App connectivity.

Version Added:
    9.0
"""

from __future__ import annotations

import base64
import json
from typing import TYPE_CHECKING, cast

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from django.core.cache import cache

from reviewboard.hostingsvcs.github.accounts import (
    GitHubAppRecordData,
    get_github_app_data,
)
from reviewboard.hostingsvcs.github.app_auth import build_app_jwt_from_data
from reviewboard.hostingsvcs.github.client import GitHubClient
from reviewboard.hostingsvcs.tests.github.base import GitHubTestCase
from reviewboard.scmtools.core import Branch

if TYPE_CHECKING:
    from typing import Any


class GitHubAppTests(GitHubTestCase):
    """Unit tests for GitHub App installation-token authentication.

    Version Added:
        9.0
    """

    @classmethod
    def setUpClass(cls) -> None:
        """Set up the test, generating an RSA key for the app."""
        super().setUpClass()

    def test_get_branches_with_app(self) -> None:
        """Testing GitHub.get_branches with a GitHub App account"""
        branches_payload = self.dump_json([
            {
                'name': 'master',
                'commit': {
                    'sha': '859d4e148ce3ce60bbda6622cdbe5c2c2f8d9817',
                },
            },
        ])
        account = self._create_app_installation_account()

        # Three calls: minting the installation token, the repository lookup,
        # and the branches request.
        with self.setup_http_test(self._make_app_handler(branches_payload),
                                  hosting_account=account,
                                  expected_http_calls=3) as ctx:
            repository = ctx.create_repository()
            branches = ctx.service.get_branches(repository)

        self.assertEqual(
            branches,
            [
                Branch(id='master',
                       commit='859d4e148ce3ce60bbda6622cdbe5c2c2f8d9817',
                       default=True),
            ])

        # The first request mints an installation token, authenticating with
        # a JWT signed by the app's private key.
        token_request = ctx.http_requests[0]
        self.assertEqual(
            token_request.url,
            'https://api.github.com/app/installations/99/access_tokens')
        self.assertEqual(token_request.method, 'POST')
        self.assertEqual(token_request.get_header('Accept'),
                         'application/vnd.github+json')
        self.assertTrue(
            token_request.get_header('Authorization').startswith('Bearer '))

        # The branch request uses the minted installation token as a Bearer
        # token.
        branches_request = ctx.http_requests[1]
        self.assertEqual(
            branches_request.url,
            'https://api.github.com/repos/myuser/myrepo/branches')
        self.assertEqual(branches_request.get_header('Authorization'),
                         'Bearer ghs_installationtoken')

    def test_get_installation_accessible_repositories(self) -> None:
        """Testing GitHubClient.get_installation_accessible_repositories"""
        base_url = ('https://api.github.com/installation/repositories'
                    '?per_page=100')
        account = self._create_app_installation_account()

        handler = self.make_handler_for_paths({
            f'/app/installations/{self.installation_id}/access_tokens': {
                'payload': self.dump_json({
                    'token': 'ghs_installationtoken',
                    'expires_at': '2099-01-01T00:00:00Z',
                }),
            },
            '/installation/repositories?per_page=100': {
                'payload': self.dump_json({
                    'total_count': 2,
                    # The list is nested under "repositories", and the owner is
                    # mixed-case to confirm the result is lowercased.
                    'repositories': [
                        {
                            'clone_url': 'repo1_path',
                            'default_branch': 'master',
                            'mirror_url': 'repo1_mirror',
                            'name': 'Repo1',
                            'owner': {'login': 'myuser'},
                        },
                    ],
                }),
                'headers': {
                    'Link': f'<{base_url}&page=2>; rel="next"',
                },
            },
            '/installation/repositories?per_page=100&page=2': {
                'payload': self.dump_json({
                    'total_count': 2,
                    'repositories': [
                        {
                            'clone_url': 'repo2_path',
                            'default_branch': 'master',
                            'mirror_url': 'repo2_mirror',
                            'name': 'repo2',
                            'owner': {'login': 'myuser'},
                        },
                    ],
                }),
            },
        })

        # Three calls: minting the installation token and one http_get per
        # page of repositories.
        with self.setup_http_test(handler,
                                  hosting_account=account,
                                  expected_http_calls=3) as ctx:
            full_names = ctx.service.get_accessible_repositories()

        self.assertEqual(full_names, {
            ('myuser', 'repo1'),
            ('myuser', 'repo2'),
        })

    def test_installation_token_is_cached(self) -> None:
        """Testing GitHub App installation token is cached and reused"""
        branches_payload = self.dump_json([
            {
                'name': 'master',
                'commit': {
                    'sha': '859d4e148ce3ce60bbda6622cdbe5c2c2f8d9817',
                },
            },
        ])
        account = self._create_app_installation_account()

        # Five calls: one token mint (cached after) plus a repository lookup
        # and branches request per get_branches.
        with self.setup_http_test(self._make_app_handler(branches_payload),
                                  hosting_account=account,
                                  expected_http_calls=5) as ctx:
            repository = ctx.create_repository()
            ctx.service.get_branches(repository)
            ctx.service.get_branches(repository)

        # The token endpoint should only be hit once across both operations.
        token_requests = [
            request
            for request in ctx.http_requests
            if 'access_tokens' in request.url
        ]
        self.assertEqual(len(token_requests), 1)

    def test_installation_token_refreshed_after_cache_loss(self) -> None:
        """Testing GitHub App installation token is re-minted after cache loss
        """
        branches_payload = self.dump_json([
            {
                'name': 'master',
                'commit': {
                    'sha': '859d4e148ce3ce60bbda6622cdbe5c2c2f8d9817',
                },
            },
        ])
        account = self._create_app_installation_account()

        # Six calls: the token is minted twice (once per get_branches, since
        # the cache is cleared between them), each with a repository lookup and
        # branches request.
        with self.setup_http_test(self._make_app_handler(branches_payload),
                                  hosting_account=account,
                                  expected_http_calls=6) as ctx:
            repository = ctx.create_repository()
            ctx.service.get_branches(repository)

            # Simulate the cached token being lost (cache flush or expiry).
            cache.clear()

            ctx.service.get_branches(repository)

        token_requests = [
            request
            for request in ctx.http_requests
            if 'access_tokens' in request.url
        ]
        self.assertEqual(len(token_requests), 2)

    def test_build_installation_jwt(self) -> None:
        """Testing GitHub App JWT is signed with the app's private key"""
        app_account = self._create_app_record_account()

        github_app = get_github_app_data(app_account)
        assert isinstance(github_app, GitHubAppRecordData)

        jwt = build_app_jwt_from_data(github_app)

        header_b64, claims_b64, signature_b64 = jwt.split('.')

        # The signature must verify against the app's public key.
        signing_input = f'{header_b64}.{claims_b64}'.encode('ascii')
        self._private_key.public_key().verify(
            self._b64url_decode(signature_b64),
            signing_input,
            padding.PKCS1v15(),
            hashes.SHA256())

        header = json.loads(self._b64url_decode(header_b64))
        self.assertEqual(header['alg'], 'RS256')

        claims = json.loads(self._b64url_decode(claims_b64))
        self.assertEqual(claims['iss'], self.app_id)

        # The token is valid for at most 10 minutes, and backdates iat to
        # tolerate clock skew.
        self.assertEqual(claims['exp'] - claims['iat'], 660)

    def test_get_token_cache_timeout(self) -> None:
        """Testing GitHub App installation token cache timeout calculation"""
        account = self._create_app_installation_account()
        client = cast(GitHubClient, account.service.client)

        # A missing or unparsable expiry falls back to the default.
        self.assertEqual(client._get_token_cache_timeout(None), 50 * 60)
        self.assertEqual(
            client._get_token_cache_timeout('2000-01-01T00:00:00Z'),
            50 * 60)

        # A future expiry yields a positive timeout.
        self.assertGreater(
            client._get_token_cache_timeout('2099-01-01T00:00:00Z'), 0)

    def test_get_http_credentials_with_personal_token_unaffected(self) -> None:
        """Testing GitHub.get_http_credentials still uses a Personal Access
        Token for non-app accounts
        """
        account = self.create_hosting_account()
        client = account.service.client

        self.assertEqual(
            client.get_http_credentials(account),
            {
                'username': 'myuser',
                'password': 'abc123',
            })

    def test_client_resolves_creds_across_app_reference(self) -> None:
        """Testing GitHub App installation token is signed with the referenced
        app record's key
        """
        branches_payload = self.dump_json([
            {
                'name': 'master',
                'commit': {
                    'sha': '859d4e148ce3ce60bbda6622cdbe5c2c2f8d9817',
                },
            },
        ])
        account = self._create_app_installation_account()

        with self.setup_http_test(self._make_app_handler(branches_payload),
                                  hosting_account=account,
                                  expected_http_calls=3) as ctx:
            repository = ctx.create_repository()
            ctx.service.get_branches(repository)

        # The JWT used to mint the token is signed by the app record's private
        # key, proving the installation account resolved its credentials across
        # the app_account_id reference.
        token_request = ctx.http_requests[0]
        jwt = token_request.get_header('Authorization').split(' ', 1)[1]
        header_b64, claims_b64, signature_b64 = jwt.split('.')

        signing_input = f'{header_b64}.{claims_b64}'.encode('ascii')
        self._private_key.public_key().verify(
            self._b64url_decode(signature_b64),
            signing_input,
            padding.PKCS1v15(),
            hashes.SHA256())

        claims = json.loads(self._b64url_decode(claims_b64))
        self.assertEqual(claims['iss'], self.app_id)

    def test_get_http_credentials_with_app_account(self) -> None:
        """Testing GitHub.get_http_credentials signs a JWT for app accounts"""
        app_account = self._create_app_record_account()
        client = cast(GitHubClient, app_account.service.client)

        credentials = client.get_http_credentials(app_account)
        authorization = credentials['headers']['Authorization']

        self.assertTrue(authorization.startswith('Bearer '))

        # The JWT must verify against the app's public key.
        jwt = authorization.split(' ', 1)[1]
        header_b64, claims_b64, signature_b64 = jwt.split('.')

        signing_input = f'{header_b64}.{claims_b64}'.encode('ascii')
        self._private_key.public_key().verify(
            self._b64url_decode(signature_b64),
            signing_input,
            padding.PKCS1v15(),
            hashes.SHA256())

        claims = json.loads(self._b64url_decode(claims_b64))
        self.assertEqual(claims['iss'], self.app_id)

    def test_get_installation_info(self) -> None:
        """Testing GitHubClient.get_installation_info reads the installation"""
        app_account = self._create_app_record_account()

        handler = self.make_handler_for_paths({
            f'/app/installations/{self.installation_id}': {
                'payload': self.dump_json({
                    'account': {
                        'login': 'myorg',
                        'type': 'Organization',
                        'avatar_url': 'https://example.com/a.png',
                    },
                    'repository_selection': 'all',
                }),
            },
        })

        with self.setup_http_test(handler,
                                  hosting_account=app_account,
                                  expected_http_calls=1) as ctx:
            install_info = ctx.service.client.get_installation_info(
                self.installation_id)

        self.assertEqual(install_info.account.login, 'myorg')
        self.assertEqual(install_info.account.type, 'Organization')
        self.assertEqual(install_info.repository_selection, 'all')

        # The request authenticates as the app via a signed JWT.
        request = ctx.http_requests[0]
        self.assertEqual(request.url,
                         'https://api.github.com/app/installations/99')
        self.assertEqual(request.method, 'GET')
        self.assertTrue(
            request.get_header('Authorization').startswith('Bearer '))

    def test_is_authorized_with_installation_account(self) -> None:
        """Testing GitHub.is_authorized with a GitHub App installation account
        """
        account = self._create_app_installation_account()

        self.assertTrue(account.is_authorized)

    def test_is_authorized_with_app_record_account(self) -> None:
        """Testing GitHub.is_authorized with a GitHub App record account"""
        account = self._create_app_record_account()

        self.assertTrue(account.is_authorized)

    def test_is_authorized_with_removed_installation_account(self) -> None:
        """Testing GitHub.is_authorized stays True for a removed installation

        Authorization reflects whether credentials exist, not whether GitHub
        still has the installation. The removed state surfaces separately when
        minting a token.
        """
        account = self._create_app_installation_account()
        account.data['github_app']['status'] = 'removed'
        account.save(update_fields=('data',))

        self.assertTrue(account.is_authorized)

    def _make_app_handler(
        self,
        branches_payload: bytes,
        token: str = 'ghs_installationtoken',
        expires_at: str = '2099-01-01T00:00:00Z',
    ) -> Any:
        """Return an HTTP handler serving the token and branch endpoints.

        Args:
            branches_payload (bytes):
                The payload to return for the branches endpoint.

            token (str, optional):
                The installation token to return from the token endpoint.

            expires_at (str, optional):
                The expiry to return from the token endpoint.

        Returns:
            callable:
            The HTTP handler.
        """
        return self.make_handler_for_paths({
            f'/app/installations/{self.installation_id}/access_tokens': {
                'payload': self.dump_json({
                    'token': token,
                    'expires_at': expires_at,
                }),
            },
            '/repos/myuser/myrepo/branches': {
                'payload': branches_payload,
            },
            '/repos/myuser/myrepo': {
                'payload': self.dump_json({
                    'clone_url': '',
                    'default_branch': 'master',
                    'mirror_url': '',
                    'name': 'myrepo',
                    'owner': {'login': 'myuser'},
                }),
            },
        })

    def _b64url_decode(
        self,
        data: str,
    ) -> bytes:
        """Decode a URL-safe Base64 JWT segment, restoring padding.

        Args:
            data (str):
                The unpadded URL-safe Base64 string.

        Returns:
            bytes:
            The decoded data.
        """
        padded = data + '=' * (-len(data) % 4)

        return base64.urlsafe_b64decode(padded)
