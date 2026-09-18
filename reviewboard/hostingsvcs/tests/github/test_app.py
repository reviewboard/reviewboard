"""Unit tests for GitHub App connectivity.

Version Added:
    9.0
"""

from __future__ import annotations

import base64
import json
from typing import TYPE_CHECKING, cast

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from django.core.cache import cache
from django.test.client import RequestFactory
from django.urls import reverse
from djblets.cache.backend import make_cache_key

from reviewboard.hostingsvcs.errors import HostingServiceError
from reviewboard.hostingsvcs.github.accounts import (
    GitHubAppRecordData,
    InstallationStatus,
    get_github_app_data,
    is_app_record_data,
)
from reviewboard.hostingsvcs.github.app_auth import (
    build_app_jwt_from_data,
    encrypt_app_private_key,
    load_app_private_key,
)
from reviewboard.hostingsvcs.github.client import GitHubClient
from reviewboard.hostingsvcs.github.service import GitHub, GitHubConnectUI
from reviewboard.hostingsvcs.models import HostingServiceAccount
from reviewboard.hostingsvcs.tests.github.base import GitHubTestCase
from reviewboard.scmtools.core import Branch
from reviewboard.site.urlresolvers import local_site_reverse

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
        account = self._create_app_installation_account(
            owner_login='myuser',
            owner_type='user')

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
        account = self._create_app_installation_account(
            owner_login='myuser',
            owner_type='user')

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
        account = self._create_app_installation_account(
            owner_login='myuser',
            owner_type='user')

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
        account = self._create_app_installation_account(
            owner_login='myuser',
            owner_type='user')

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

    def test_get_installation_token_refused_when_removed(self) -> None:
        """Testing GitHubClient token minting refused for a removed install"""
        account = self._create_app_installation_account()
        account.data['github_app']['status'] = 'removed'
        account.save(update_fields=('data',))

        message = (
            'This GitHub App installation was removed on GitHub. Please '
            'reinstall the app to restore the connection.')

        with self.assertRaises(HostingServiceError, msg=message):
            account.service.client.get_http_credentials(account)

    def test_get_installation_token_refused_when_suspended(self) -> None:
        """Testing GitHubClient token minting refused for a suspended install
        """
        account = self._create_app_installation_account()
        account.data['github_app']['status'] = 'suspended'
        account.save(update_fields=('data',))

        message = (
            'This GitHub App installation is suspended on GitHub. Please '
            'unsuspend it to restore the connection.')

        with self.assertRaises(HostingServiceError, msg=message):
            account.service.client.get_http_credentials(account)

    def test_menu_items_for_active_installation(self) -> None:
        """Testing GitHubConnectUI.
        get_connected_services_list_account_menu_items with an active
        installation account
        """
        account = self._create_app_installation_account()
        request = RequestFactory().get('/')

        items = \
            GitHub.connect_ui.get_connected_services_list_account_menu_items(
                request,
                account=account)

        self.assertEqual(items, [])

    def test_menu_items_for_suspended_installation(self) -> None:
        """Testing GitHubConnectUI.
        get_connected_services_list_account_menu_items links a suspended
        installation to the reconnect view
        """
        account = self._create_app_installation_account(
            owner_login='myuser',
            owner_type='user')
        account.data['github_app']['status'] = 'suspended'
        account.save(update_fields=('data',))

        request = RequestFactory().get('/')
        items = \
            GitHub.connect_ui.get_connected_services_list_account_menu_items(
                request,
                account=account)

        self.assertEqual(items, [{
            'id': 'reconnect',
            'label': 'Reconnect',
            'url': self._get_reconnect_view_url(account),
        }])

    def test_menu_items_for_removed_installation(self) -> None:
        """Testing GitHubConnectUI.
        get_connected_services_list_account_menu_items links a removed
        installation to the reconnect view
        """
        account = self._create_app_installation_account(
            status=InstallationStatus.REMOVED)

        request = RequestFactory().get('/')
        items = \
            GitHub.connect_ui.get_connected_services_list_account_menu_items(
                request,
                account=account)

        self.assertEqual(items, [{
            'id': 'reconnect',
            'label': 'Reconnect',
            'url': self._get_reconnect_view_url(account),
        }])

    def test_get_reconnect_url_for_suspended_user_installation(self) -> None:
        """Testing GitHubConnectUI.get_reconnect_url links a suspended user
        installation to its GitHub settings page
        """
        account = self._create_app_installation_account(
            owner_login='myuser',
            owner_type='user',
            status=InstallationStatus.SUSPENDED)

        connect_ui = GitHub.connect_ui
        assert isinstance(connect_ui, GitHubConnectUI)

        self.assertEqual(
            connect_ui.get_reconnect_url(account),
            f'https://github.com/settings/installations/'
            f'{self.installation_id}')

    def test_get_reconnect_url_for_suspended_org_installation(self) -> None:
        """Testing GitHubConnectUI.get_reconnect_url links a suspended org
        installation to its GitHub settings page
        """
        account = self._create_app_installation_account(
            status=InstallationStatus.SUSPENDED)

        connect_ui = GitHub.connect_ui
        assert isinstance(connect_ui, GitHubConnectUI)

        self.assertEqual(
            connect_ui.get_reconnect_url(account),
            f'https://github.com/organizations/{account.username}'
            f'/settings/installations/{self.installation_id}')

    def test_get_reconnect_url_for_removed_installation(self) -> None:
        """Testing GitHubConnectUI.get_reconnect_url links a removed
        installation back through the install flow for its account
        """
        owner_id = 123
        account = self._create_app_installation_account(owner_id=owner_id)
        account.data['github_app']['status'] = 'removed'
        account.save(update_fields=('data',))

        app_account_id = account.data['github_app']['app_account_id']
        install_url = local_site_reverse(
            'github-app-install',
            kwargs={
                'hosting_service_id': 'github',
                'account_id': app_account_id,
            })

        connect_ui = GitHub.connect_ui
        assert isinstance(connect_ui, GitHubConnectUI)

        self.assertEqual(connect_ui.get_reconnect_url(account),
                         f'{install_url}?target_id={owner_id}')

    def test_get_reconnect_url_for_removed_installation_without_owner_id(
        self,
    ) -> None:
        """Testing GitHubConnectUI.get_reconnect_url links a removed
        installation to the install flow without a target when the owner ID is
        unknown
        """
        account = self._create_app_installation_account()
        del account.data['github_app']['owner_id']
        account.data['github_app']['status'] = 'removed'
        account.save(update_fields=('data',))

        app_account_id = account.data['github_app']['app_account_id']

        connect_ui = GitHub.connect_ui
        assert isinstance(connect_ui, GitHubConnectUI)

        self.assertEqual(
            connect_ui.get_reconnect_url(account),
            local_site_reverse(
                'github-app-install',
                kwargs={
                    'hosting_service_id': 'github',
                    'account_id': app_account_id,
                }))

    def test_attention_items_for_active_installation(self) -> None:
        """Testing GitHubConnectUI.get_connected_services_list_attention_items
        with an active installation account
        """
        account = self._create_app_installation_account()
        request = RequestFactory().get('/')

        items = GitHub.connect_ui.get_connected_services_list_attention_items(
            request,
            accounts=[account])

        self.assertEqual(items, [])

    def test_attention_items_for_suspended_installation(self) -> None:
        """Testing GitHubConnectUI.get_connected_services_list_attention_items
        reports a suspended installation with a Reconnect action
        """
        account = self._create_app_installation_account()
        account.data['github_app']['status'] = 'suspended'
        account.save(update_fields=('data',))

        request = RequestFactory().get('/')
        items = GitHub.connect_ui.get_connected_services_list_attention_items(
            request,
            accounts=[account])

        self.assertEqual(items, [{
            'service_name': 'GitHub',
            'account_label': account.username,
            'message': 'Suspended on GitHub',
            'account_id': account.pk,
            'service_id': 'github',
            'action': {
                'id': 'reconnect',
                'label': 'Reconnect',
                'url': self._get_reconnect_view_url(account),
            },
        }])

    def test_attention_items_for_removed_installation(self) -> None:
        """Testing GitHubConnectUI.get_connected_services_list_attention_items
        reports a removed installation with a Reconnect action
        """
        account = self._create_app_installation_account()
        account.data['github_app']['status'] = 'removed'
        account.save(update_fields=('data',))

        request = RequestFactory().get('/')
        items = GitHub.connect_ui.get_connected_services_list_attention_items(
            request,
            accounts=[account])

        self.assertEqual(items, [{
            'service_name': 'GitHub',
            'account_label': account.username,
            'message': 'Removed on GitHub',
            'account_id': account.pk,
            'service_id': 'github',
            'action': {
                'id': 'reconnect',
                'label': 'Reconnect',
                'url': self._get_reconnect_view_url(account),
            },
        }])

    def test_attention_items_for_pat_account(self) -> None:
        """Testing GitHubConnectUI.get_connected_services_list_attention_items
        ignores a Personal Access Token account
        """
        account = self.create_hosting_account()
        request = RequestFactory().get('/')

        items = GitHub.connect_ui.get_connected_services_list_attention_items(
            request,
            accounts=[account])

        self.assertEqual(items, [])

    def test_mint_403_marks_installation_suspended(self) -> None:
        """Testing GitHubClient token minting marks the installation suspended
        when GitHub refuses with a 403 and reports a suspension
        """
        account = self._create_app_installation_account()

        handler = self.make_handler_for_paths({
            f'/app/installations/{self.installation_id}/access_tokens': {
                'status_code': 403,
                'payload': self.dump_json({
                    'message': 'This installation has been suspended',
                }),
            },
            f'/app/installations/{self.installation_id}': {
                'payload': self._make_installation_payload(
                    suspended_at='2026-07-01T00:00:00Z'),
            },
        })

        message = (
            'This GitHub App installation is suspended on GitHub. '
            'Unsuspend it to restore the connection.')

        # Two calls: the refused token mint and the status lookup.
        with (self.setup_http_test(handler,
                                   hosting_account=account,
                                   expected_http_calls=2) as ctx,
              self.assertRaises(HostingServiceError, msg=message)):
            ctx.service.client.get_http_credentials(account)

        account = HostingServiceAccount.objects.get(pk=account.pk)
        self.assertEqual(account.data['github_app']['status'], 'suspended')

    def test_mint_404_marks_installation_removed(self) -> None:
        """Testing GitHubClient token minting marks the installation removed
        when GitHub no longer has it
        """
        account = self._create_app_installation_account()

        handler = self.make_handler_for_paths({
            f'/app/installations/{self.installation_id}/access_tokens': {
                'status_code': 404,
                'payload': self.dump_json({'message': 'Not Found'}),
            },
            f'/app/installations/{self.installation_id}': {
                'status_code': 404,
                'payload': self.dump_json({'message': 'Not Found'}),
            },
            '/app/installations?per_page=100': {
                'payload': self.dump_json([]),
            },
        })

        message = (
            'This GitHub App installation was removed on GitHub. '
            'Reinstall the app to restore the connection.')

        # Three calls: the refused token mint, the status lookup, and the
        # search for a reinstall on the same owner.
        with (self.setup_http_test(handler,
                                   hosting_account=account,
                                   expected_http_calls=3) as ctx,
              self.assertRaises(HostingServiceError, msg=message)):
            ctx.service.client.get_http_credentials(account)

        account = HostingServiceAccount.objects.get(pk=account.pk)
        self.assertEqual(account.data['github_app']['status'], 'removed')

    def test_mint_404_adopts_reinstalled_installation_id(self) -> None:
        """Testing GitHubClient token minting adopts the new installation ID
        after a reinstall performed directly on GitHub
        """
        new_installation_id = self.installation_id + 1
        branches_payload = self.dump_json([
            {
                'name': 'master',
                'commit': {
                    'sha': '859d4e148ce3ce60bbda6622cdbe5c2c2f8d9817',
                },
            },
        ])
        account = self._create_app_installation_account(
            owner_login='myuser',
            owner_type='user')

        handler = self.make_handler_for_paths({
            f'/app/installations/{self.installation_id}/access_tokens': {
                'status_code': 404,
                'payload': self.dump_json({'message': 'Not Found'}),
            },
            f'/app/installations/{self.installation_id}': {
                'status_code': 404,
                'payload': self.dump_json({'message': 'Not Found'}),
            },
            '/app/installations?per_page=100': {
                'payload': self.dump_json([
                    json.loads(self._make_installation_payload(
                        installation_id=new_installation_id)),
                ]),
            },
            f'/app/installations/{new_installation_id}/access_tokens': {
                'payload': self.dump_json({
                    'token': 'ghs_installationtoken',
                    'expires_at': '2099-01-01T00:00:00Z',
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

        # Six calls: the refused token mint, the status lookup, the search
        # for a reinstall, the successful mint against the new ID, then the
        # repository lookup and branches request.
        with self.setup_http_test(handler,
                                  hosting_account=account,
                                  expected_http_calls=6) as ctx:
            repository = ctx.create_repository()
            branches = ctx.service.get_branches(repository)

        self.assertEqual(len(branches), 1)

        account = HostingServiceAccount.objects.get(pk=account.pk)
        github_app = account.data['github_app']
        self.assertEqual(github_app['status'], 'active')
        self.assertEqual(github_app['installation_id'], new_installation_id)

    def test_request_403_with_cached_token_rechecks_status(self) -> None:
        """Testing GitHubClient re-checks the installation status when a
        request made with an installation token is rejected
        """
        account = self._create_app_installation_account(
            owner_login='myuser',
            owner_type='user')

        handler = self.make_handler_for_paths({
            f'/app/installations/{self.installation_id}/access_tokens': {
                'payload': self.dump_json({
                    'token': 'ghs_installationtoken',
                    'expires_at': '2099-01-01T00:00:00Z',
                }),
            },
            '/repos/myuser/myrepo/branches': {
                'status_code': 403,
                'payload': self.dump_json({
                    'message': 'This installation has been suspended',
                }),
            },
            f'/app/installations/{self.installation_id}': {
                'payload': self._make_installation_payload(
                    suspended_at='2026-07-01T00:00:00Z'),
            },
        })

        message = (
            'This GitHub App installation is suspended on GitHub. '
            'Unsuspend it to restore the connection.')

        # Three calls: the token mint, the rejected branches request, and
        # the status lookup.
        with self.setup_http_test(handler,
                                  hosting_account=account,
                                  expected_http_calls=3) as ctx:
            repository = ctx.create_repository()

            with self.assertRaises(HostingServiceError, msg=message):
                ctx.service.get_branches(repository)

        account = HostingServiceAccount.objects.get(pk=account.pk)
        self.assertEqual(account.data['github_app']['status'], 'suspended')

        # The now-invalid token must no longer be cached.
        self.assertIsNone(cache.get(make_cache_key([
            'github-app-installation-token',
            str(account.pk),
            str(self.installation_id),
        ])))

    def test_stale_suspended_status_self_heals(self) -> None:
        """Testing GitHubClient token minting re-checks a stored suspended
        status and heals the connection when GitHub reports it active
        """
        branches_payload = self.dump_json([
            {
                'name': 'master',
                'commit': {
                    'sha': '859d4e148ce3ce60bbda6622cdbe5c2c2f8d9817',
                },
            },
        ])
        account = self._create_app_installation_account(
            owner_login='myuser',
            owner_type='user')
        account.data['github_app']['status'] = 'suspended'
        account.save(update_fields=('data',))

        handler = self.make_handler_for_paths({
            f'/app/installations/{self.installation_id}': {
                'payload': self._make_installation_payload(),
            },
            f'/app/installations/{self.installation_id}/access_tokens': {
                'payload': self.dump_json({
                    'token': 'ghs_installationtoken',
                    'expires_at': '2099-01-01T00:00:00Z',
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

        # Four calls: the status lookup, the token mint, the repository
        # lookup, and the branches request.
        with self.setup_http_test(handler,
                                  hosting_account=account,
                                  expected_http_calls=4) as ctx:
            repository = ctx.create_repository()
            branches = ctx.service.get_branches(repository)

        self.assertEqual(len(branches), 1)

        account = HostingServiceAccount.objects.get(pk=account.pk)
        self.assertEqual(account.data['github_app']['status'], 'active')

    def test_stale_status_check_is_debounced(self) -> None:
        """Testing GitHubClient token minting does not re-check a stored
        non-active status when a check ran recently
        """
        account = self._create_app_installation_account()
        account.data['github_app']['status'] = 'suspended'
        account.save(update_fields=('data',))

        # Simulate a recent check.
        cache.add(
            make_cache_key([
                'github-app-status-check',
                str(account.pk),
            ]),
            True,
            timeout=60)

        message = (
            'This GitHub App installation is suspended on GitHub. '
            'Unsuspend it to restore the connection.')

        with (self.setup_http_test(self.make_handler_for_paths({}),
                                   hosting_account=account,
                                   expected_http_calls=0) as ctx,
              self.assertRaises(HostingServiceError, msg=message)):
            ctx.service.client.get_http_credentials(account)

    def test_encrypt_app_private_key_round_trip(self) -> None:
        """Testing encrypt_app_private_key round-trips a PEM key"""
        app_account = self._create_app_record_account()
        app_data = get_github_app_data(app_account)
        assert is_app_record_data(app_data)

        app_data.private_key = encrypt_app_private_key(
            self._pem.decode('utf-8'))

        # load_app_private_key reverses the encode-and-encrypt transform.
        self.assertEqual(
            load_app_private_key(app_data),
            self._pem.decode('utf-8'))

    def test_encrypt_app_private_key_rejects_invalid(self) -> None:
        """Testing encrypt_app_private_key rejects a non-PEM value"""
        from reviewboard.hostingsvcs.github.app_auth import \
            encrypt_app_private_key

        with self.assertRaises(ValueError):
            encrypt_app_private_key('not a private key')

    def test_encrypt_app_private_key_rejects_non_rsa(self) -> None:
        """Testing encrypt_app_private_key rejects a non-RSA key"""
        from cryptography.hazmat.primitives.asymmetric import ec

        from reviewboard.hostingsvcs.github.app_auth import \
            encrypt_app_private_key

        ec_pem = (
            ec.generate_private_key(ec.SECP256R1())
            .private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption())
            .decode('utf-8'))

        with self.assertRaises(ValueError):
            encrypt_app_private_key(ec_pem)

    def _get_reconnect_view_url(
        self,
        account: HostingServiceAccount,
    ) -> str:
        """Return the URL for the reconnect view for an installation account.

        Args:
            account (reviewboard.hostingsvcs.models.HostingServiceAccount):
                The installation account.

        Returns:
            str:
            The URL for the reconnect view.
        """
        return local_site_reverse(
            'github-app-reconnect',
            kwargs={
                'hosting_service_id': 'github',
                'account_id': account.pk,
            })

    def _make_installation_payload(
        self,
        *,
        installation_id: (int | None) = None,
        suspended_at: (str | None) = None,
    ) -> bytes:
        """Return an installation API payload for the test's owner.

        Args:
            installation_id (int, optional):
                The installation ID to include. Defaults to the test's
                installation ID.

            suspended_at (str, optional):
                The suspension time to include, or ``None`` if the
                installation is not suspended.

        Returns:
            bytes:
            The JSON payload.
        """
        if installation_id is None:
            installation_id = self.installation_id

        return self.dump_json({
            'id': installation_id,
            'account': {
                'login': 'myuser',
                'id': 555,
                'type': 'User',
            },
            'repository_selection': 'all',
            'suspended_at': suspended_at,
        })

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


class GitHubAppRecordDeletionTests(GitHubTestCase):
    """Unit tests for deleting an app-record account in the admin UI.

    Version Added:
        9.0
    """

    fixtures = ['test_users']

    def test_admin_delete_app_record_with_dependents_blocked(self) -> None:
        """Testing the admin UI refuses to delete an app-record account while
        an installation depends on it
        """
        app_account = self._create_app_record_account()
        installation = self._create_app_installation_account(app_account)

        self.login_user(admin=True)

        response = self.client.post(
            reverse('admin:hostingsvcs_hostingserviceaccount_delete',
                    args=(app_account.pk,)),
            {'post': 'yes'})

        # The confirmation page is re-rendered listing what blocks the delete,
        # rather than the delete failing partway through.
        self.assertEqual(response.status_code, 200)
        self.assertIn(str(installation).encode('utf-8'), response.content)

        self.assertTrue(
            HostingServiceAccount.objects.filter(pk=app_account.pk).exists())

    def test_admin_delete_app_record_without_dependents_allowed(self) -> None:
        """Testing the admin UI deletes an app-record account with no
        installations
        """
        app_account = self._create_app_record_account()

        self.login_user(admin=True)

        response = self.client.post(
            reverse('admin:hostingsvcs_hostingserviceaccount_delete',
                    args=(app_account.pk,)),
            {'post': 'yes'})

        self.assertEqual(response.status_code, 302)
        self.assertFalse(
            HostingServiceAccount.objects.filter(pk=app_account.pk).exists())

    def test_admin_delete_pat_account_allowed(self) -> None:
        """Testing the admin UI deletes a Personal Access Token account"""
        pat_account = self.create_hosting_account()

        self.login_user(admin=True)

        response = self.client.post(
            reverse('admin:hostingsvcs_hostingserviceaccount_delete',
                    args=(pat_account.pk,)),
            {'post': 'yes'})

        self.assertEqual(response.status_code, 302)
        self.assertFalse(
            HostingServiceAccount.objects.filter(pk=pat_account.pk).exists())

    def test_admin_delete_account_for_unknown_service(self) -> None:
        """Testing the admin UI deletes an account whose hosting service is no
        longer registered
        """
        account = HostingServiceAccount.objects.create(
            service_name='not-a-registered-service',
            username='user1',
            hosting_url='')

        self.login_user(admin=True)

        response = self.client.post(
            reverse('admin:hostingsvcs_hostingserviceaccount_delete',
                    args=(account.pk,)),
            {'post': 'yes'})

        self.assertEqual(response.status_code, 302)
        self.assertFalse(
            HostingServiceAccount.objects.filter(pk=account.pk).exists())

    def test_admin_delete_app_record_with_dependents_together(self) -> None:
        """Testing the admin UI deletes an app-record account selected together
        with the installations depending on it
        """
        app_account = self._create_app_record_account()
        installation = self._create_app_installation_account(app_account)

        self.login_user(admin=True)

        response = self.client.post(
            reverse('admin:hostingsvcs_hostingserviceaccount_changelist'),
            {
                'action': 'delete_selected',
                '_selected_action': [app_account.pk, installation.pk],
                'post': 'yes',
            })

        self.assertEqual(response.status_code, 302)
        self.assertFalse(HostingServiceAccount.objects.exists())
