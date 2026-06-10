"""Unit tests for GitHub App views.

Version Added:
    9.0
"""

from __future__ import annotations

import base64
import json
from typing import TYPE_CHECKING

import kgb
from django.contrib.messages import Message
from pydantic import ValidationError

from reviewboard.hostingsvcs.errors import HostingServiceError
from reviewboard.hostingsvcs.github import api, views
from reviewboard.hostingsvcs.github.client import GitHubClient
from reviewboard.hostingsvcs.models import HostingServiceAccount
from reviewboard.hostingsvcs.testing.paginator import TestPaginator
from reviewboard.hostingsvcs.tests.github.base import GitHubTestCase
from reviewboard.scmtools.crypto_utils import decrypt_password
from reviewboard.scmtools.models import Repository
from reviewboard.site.urlresolvers import local_site_reverse

if TYPE_CHECKING:
    from typing import ClassVar

    from django.test.client import _MonkeyPatchedWSGIResponse
    from typelets.json import JSONDictImmutable


class GitHubAppCreateViewTests(GitHubTestCase):
    """Unit tests for GitHubAppCreateView.

    Version Added:
        9.0
    """

    def setUp(self) -> None:
        """Set up the test, logging in a staff user."""
        super().setUp()

        user = self.create_user(username='admin',
                                is_staff=True,
                                is_superuser=True)
        self.client.force_login(user)

    def test_get_renders_confirmation_fragment(self) -> None:
        """Testing GitHubAppCreateView GET renders the manifest confirmation
        as a wizard fragment
        """
        url = local_site_reverse('github-app-create',
                                 kwargs={'hosting_service_id': 'github'})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

        content = response.content
        self.assertIn(b'github-app-manifest-form', content)

        # The confirmation renders inside the wizard, so it has no full-page
        # chrome.
        self.assertNotIn(b'<!DOCTYPE', content)

    def test_manifest_points_webhook_at_handler(self) -> None:
        """Testing GitHubAppCreateView manifest points the webhook at the
        webhook handler
        """
        url = local_site_reverse('github-app-create',
                                 kwargs={'hosting_service_id': 'github'})
        response = self.client.get(url)

        manifest = json.loads(response.context['manifest_json'])
        webhook_url = local_site_reverse(
            'github-app-webhook',
            kwargs={'hosting_service_id': 'github'})

        self.assertTrue(
            manifest['hook_attributes']['url'].endswith(webhook_url))


class GitHubAppCallbackViewTests(GitHubTestCase):
    """Unit tests for GitHubAppCallbackView.

    Version Added:
        9.0
    """

    #: A representative GitHub app-manifest conversion response.
    _MANIFEST_RESPONSE: ClassVar[JSONDictImmutable] = {
        'id': 12345,
        'slug': 'rb-app',
        'client_id': 'Iv1.abc123',
        'client_secret': 'theclientsecret',
        'pem': ('-----BEGIN PRIVATE KEY-----\n'
                'MIIfake\n'
                '-----END PRIVATE KEY-----\n'),
        'webhook_secret': 'thewebhooksecret',
        'html_url': 'https://github.com/apps/rb-app',
        'owner': {
            'login': 'myorg',
            'type': 'Organization',
        },
    }

    def setUp(self) -> None:
        """Set up the test, logging in a staff user."""
        super().setUp()

        user = self.create_user(username='admin',
                                is_staff=True,
                                is_superuser=True)
        self.client.force_login(user)

    def test_get_creates_app_account_and_redirects(self) -> None:
        """Testing GitHubAppCallbackView GET creates the app-record account
        and redirects to install
        """
        self.spy_on(
            views.GitHubAppCallbackView._convert_manifest,
            op=kgb.SpyOpReturn(
                api.AppManifestResponse.model_validate(
                    dict(self._MANIFEST_RESPONSE))))

        self._set_create_session('teststate')

        response = self._get_callback(state='teststate', code='tempcode')

        self.assertEqual(response.status_code, 302)
        self.assertIn('/apps/rb-app/installations/new', response['Location'])

        # A single hidden app-record account is created, holding the app
        # credentials.
        account = HostingServiceAccount.objects.get(service_name='github',
                                                    visible=False)

        self.assertEqual(account.username, 'myorg')

        # Secrets are encrypted at rest with a random nonce, so decrypt
        # them before comparing the full contents. The PEM is Base64-encoded
        # before encryption, since decrypt_password() rejects multi-line
        # content.
        github_app = dict(account.data['github_app'])
        github_app['client_secret'] = \
            decrypt_password(github_app['client_secret'])
        github_app['webhook_secret'] = \
            decrypt_password(github_app['webhook_secret'])
        github_app['private_key'] = base64.b64decode(
            decrypt_password(github_app['private_key'])).decode('utf-8')

        self.assertEqual(
            github_app,
            {
                'app_id': 12345,
                'app_slug': 'rb-app',
                'client_id': 'Iv1.abc123',
                'client_secret': 'theclientsecret',
                'html_url': 'https://github.com/apps/rb-app',
                'owner_login': 'myorg',
                'owner_type': 'organization',
                'private_key': self._MANIFEST_RESPONSE['pem'],
                'role': 'app',
                'webhook_secret': 'thewebhooksecret',
            })

        # The install handoff state is stored and matches the redirect.
        install_session = self.client.session[views._INSTALL_SESSION_KEY]
        self.assertEqual(install_session['account_id'], account.pk)
        self.assertIn(f"state={install_session['state']}",
                      response['Location'])

        # The create state is consumed so it can't be replayed.
        self.assertNotIn(views._CREATE_SESSION_KEY, self.client.session)

    def test_get_without_session(self) -> None:
        """Testing GitHubAppCallbackView GET without create-session state"""
        response = self._get_callback(state='teststate', code='tempcode')

        self._assert_error_redirect(
            response,
            'The GitHub connection state was invalid or has expired. Please '
            'try connecting again.')

    def test_get_with_invalid_state(self) -> None:
        """Testing GitHubAppCallbackView GET with a mismatched state token"""
        self._set_create_session('realstate')

        response = self._get_callback(state='wrongstate', code='tempcode')

        self._assert_error_redirect(
            response,
            'The GitHub connection state was invalid or has expired. Please '
            'try connecting again.')

    def test_get_without_code(self) -> None:
        """Testing GitHubAppCallbackView GET without a setup code"""
        self._set_create_session('teststate')

        response = self._get_callback(state='teststate')

        self._assert_error_redirect(
            response,
            'GitHub did not provide a setup code. Please try connecting '
            'again.')

    def test_get_with_failed_conversion(self) -> None:
        """Testing GitHubAppCallbackView GET when manifest conversion fails"""
        self.spy_on(views.GitHubAppCallbackView._convert_manifest,
                    op=kgb.SpyOpRaise(Exception('boom')))

        self._set_create_session('teststate')

        response = self._get_callback(state='teststate', code='tempcode')

        self._assert_error_redirect(
            response,
            'Could not retrieve the GitHub App details from GitHub. Please '
            'try connecting again.')

        # No account is created when the conversion fails.
        self.assertFalse(
            HostingServiceAccount.objects
            .filter(service_name='github')
            .exists())

    def test_manifest_rejects_missing_credentials(self) -> None:
        """Testing AppManifestResponse rejects a conversion response missing
        required credentials
        """
        # A response missing any credential field must be rejected. The view
        # turns the resulting error into a friendly failure (see
        # test_get_with_failed_conversion).
        for field in ('id', 'slug', 'client_id', 'client_secret', 'pem'):
            incomplete = dict(self._MANIFEST_RESPONSE)
            del incomplete[field]

            with self.assertRaises(ValidationError):
                api.AppManifestResponse.model_validate(incomplete)

    def _set_create_session(
        self,
        state: str,
    ) -> None:
        """Store app-creation state in the test client's session.

        Args:
            state (str):
                The state token to store.
        """
        session = self.client.session
        session[views._CREATE_SESSION_KEY] = {
            'hosting_url': None,
            'local_site_id': None,
            'state': state,
        }
        session.save()

    def _get_callback(
        self,
        **query: str,
    ) -> _MonkeyPatchedWSGIResponse:
        """Perform a GET against the app-creation callback.

        Args:
            **query (dict):
                Query arguments to include in the request.

        Returns:
            django.test.client.HttpResponse:
            The response from the view.
        """
        url = local_site_reverse('github-app-callback',
                                 kwargs={'hosting_service_id': 'github'})

        return self.client.get(url, query)


class GitHubAppInstallViewTests(GitHubTestCase):
    """Unit tests for GitHubAppInstallView.

    Version Added:
        9.0
    """

    def setUp(self) -> None:
        """Set up the test, logging in a staff user."""
        super().setUp()

        user = self.create_user(username='admin',
                                is_staff=True,
                                is_superuser=True)
        self.client.force_login(user)

    def test_get_redirects_to_install(self) -> None:
        """Testing GitHubAppInstallView GET redirects to the GitHub install
        page
        """
        app_account = self.create_hosting_account(data={
            'github_app': {
                'app_id': 12345,
                'app_slug': 'rb-app',
                'client_id': 'client-id',
                'client_secret': 'encrypted-client-secret',
                'private_key': 'encrypted-private-key',
                'role': 'app',
                'webhook_secret': 'encrypted-webhook-secret',
            },
        })

        response = self._get_install(app_account.pk)

        self.assertEqual(response.status_code, 302)
        self.assertIn('/apps/rb-app/installations/new', response['Location'])

        # The install handoff state is stored for the callback to verify.
        install_session = self.client.session[views._INSTALL_SESSION_KEY]
        self.assertEqual(install_session['account_id'], app_account.pk)

    def test_get_with_missing_account(self) -> None:
        """Testing GitHubAppInstallView GET with an unknown account"""
        response = self._get_install(99999)

        self._assert_error_redirect(
            response,
            'The GitHub App connection was not found. Please try connecting '
            'again.')

    def test_get_with_non_app_account(self) -> None:
        """Testing GitHubAppInstallView GET with a non-app-record account"""
        pat_account = self.create_hosting_account()

        response = self._get_install(pat_account.pk)

        self._assert_error_redirect(
            response,
            'The GitHub App connection was not found. Please try connecting '
            'again.')

    def test_get_with_missing_app_slug(self) -> None:
        """Testing GitHubAppInstallView GET when the app record has no slug"""
        app_account = self.create_hosting_account(data={
            'github_app': {
                'app_id': 12345,
                'app_slug': '',
                'client_id': 'client-id',
                'client_secret': 'encrypted-client-secret',
                'private_key': 'encrypted-private-key',
                'role': 'app',
                'webhook_secret': 'encrypted-webhook-secret',
            },
        })

        response = self._get_install(app_account.pk)

        self._assert_error_redirect(
            response,
            'The GitHub App is missing its configuration. Please try '
            'connecting again.')

    def _get_install(
        self,
        account_id: int,
    ) -> _MonkeyPatchedWSGIResponse:
        """Perform a GET against the app install start view.

        Args:
            account_id (int):
                The account ID to include in the URL.

        Returns:
            django.test.client.HttpResponse:
            The response from the view.
        """
        url = local_site_reverse(
            'github-app-install',
            kwargs={
                'hosting_service_id': 'github',
                'account_id': account_id,
            })

        return self.client.get(url)


class GitHubAppInstallCallbackViewTests(GitHubTestCase):
    """Unit tests for the GitHub App installation success page and reassign.

    Version Added:
        9.0
    """

    fixtures = ['test_users', 'test_scmtools']

    def test_get_reassignable_with_matching_pat_repo(self) -> None:
        """Testing _get_reassignable_repositories with a matching PAT repo"""
        installation_account = self._create_app_installation_account()
        pat_account = self.create_hosting_account()
        repository = self._create_org_repo('repo1', 'myorg', pat_account)

        self.assertEqual(
            views.GitHubAppInstallCallbackView
            ._get_reassignable_repositories(installation_account),
            [repository])

    def test_get_reassignable_with_user_plan_repo(self) -> None:
        """Testing _get_reassignable_repositories matching a user-plan repo"""
        # User-plan repos are owned by the account's own username.
        installation_account = self._create_app_installation_account(
            owner_login='myuser',
            owner_type='user')
        pat_account = self.create_hosting_account()
        repository = self.create_repository(hosting_account=pat_account)

        self.assertEqual(
            views.GitHubAppInstallCallbackView
            ._get_reassignable_repositories(installation_account),
            [repository])

    def test_get_reassignable_excludes_other_owner(self) -> None:
        """Testing _get_reassignable_repositories excludes other owners"""
        installation_account = self._create_app_installation_account()
        pat_account = self.create_hosting_account()
        self._create_org_repo('repo1', 'otherorg', pat_account)

        self.assertEqual(
            views.GitHubAppInstallCallbackView
            ._get_reassignable_repositories(installation_account),
            [])

    def test_get_reassignable_excludes_app_accounts(self) -> None:
        """Testing _get_reassignable_repositories excludes app-backed repos"""
        installation_account = self._create_app_installation_account()
        other_install_account = self._create_app_installation_account()
        self._create_org_repo('repo1', 'myorg', other_install_account)

        self.assertEqual(
            views.GitHubAppInstallCallbackView
            ._get_reassignable_repositories(installation_account),
            [])

    def test_get_reassignable_excludes_archived(self) -> None:
        """Testing _get_reassignable_repositories excludes archived repos"""
        installation_account = self._create_app_installation_account()
        pat_account = self.create_hosting_account()
        self._create_org_repo('repo1', 'myorg', pat_account, archived=True)

        self.assertEqual(
            views.GitHubAppInstallCallbackView
            ._get_reassignable_repositories(installation_account),
            [])

    def test_get_reassignable_filters_to_accessible(self) -> None:
        """Testing _get_reassignable_repositories filters to accessible"""
        installation_account = self._create_app_installation_account(
            repository_selection='selected')
        pat_account = self.create_hosting_account()
        repository1 = self._create_org_repo('repo1', 'myorg', pat_account)
        self._create_org_repo('repo2', 'myorg', pat_account)

        self.spy_on(
            GitHubClient.get_installation_accessible_repositories,
            op=kgb.SpyOpReturn(TestPaginator([
                [
                    api.Repository(
                        clone_url='',
                        default_branch='',
                        mirror_url='',
                        name='repo1',
                        owner=api.RepositoryOwner(login='myorg'),
                    ),
                ],
            ])))

        self.assertEqual(
            views.GitHubAppInstallCallbackView
            ._get_reassignable_repositories(installation_account),
            [repository1])

    def test_get_reassignable_all_selection_skips_api(self) -> None:
        """Testing _get_reassignable_repositories skips the API for 'all'"""
        installation_account = self._create_app_installation_account()
        pat_account = self.create_hosting_account()
        repository = self._create_org_repo('repo1', 'myorg', pat_account)

        self.spy_on(GitHubClient.get_installation_accessible_repositories)

        self.assertEqual(
            views.GitHubAppInstallCallbackView
            ._get_reassignable_repositories(installation_account),
            [repository])
        self.assertSpyNotCalled(
            GitHubClient.get_installation_accessible_repositories)

    def test_get_reassign_step_renders_fragment(self) -> None:
        """Testing GitHubAppInstallCallbackView GET ?step=reassign fragment"""
        installation_account = self._create_app_installation_account()
        pat_account = self.create_hosting_account()
        repository = self._create_org_repo('repo1', 'myorg', pat_account)

        self.login_user(admin=True)
        url = local_site_reverse('github-app-install-callback',
                                 kwargs={'hosting_service_id': 'github'})
        response = self.client.get(url, {
            'step': 'reassign',
            'account_id': installation_account.pk,
        })

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, 'hostingsvcs/github/app_install_success.html')
        self.assertEqual(list(response.context['repositories']), [repository])
        self.assertEqual(response.context['owner_login'], 'myorg')

        # The fragment carries the dialog title and icon for the wizard.
        self.assertTrue(response.context['service_logo'])
        self.assertIn(b'data-wizard-title="Connected to GitHub"',
                      response.content)

    def test_get_reassign_step_with_non_installation_account(self) -> None:
        """Testing GitHubAppInstallCallbackView GET ?step=reassign with a
        non-app account
        """
        pat_account = self.create_hosting_account()

        self.login_user(admin=True)
        url = local_site_reverse('github-app-install-callback',
                                 kwargs={'hosting_service_id': 'github'})
        response = self.client.get(url, {
            'step': 'reassign',
            'account_id': pat_account.pk,
        })

        self.assertEqual(response.status_code, 404)

    def test_get_reassign_step_with_invalid_account_id(self) -> None:
        """Testing GitHubAppInstallCallbackView GET ?step=reassign with a
        non-numeric account ID
        """
        self.login_user(admin=True)
        url = local_site_reverse('github-app-install-callback',
                                 kwargs={'hosting_service_id': 'github'})
        response = self.client.get(url, {
            'step': 'reassign',
            'account_id': 'abc',
        })

        self.assertEqual(response.status_code, 404)

    def test_get_reassign_step_without_account_id(self) -> None:
        """Testing GitHubAppInstallCallbackView GET ?step=reassign without an
        account ID
        """
        self.login_user(admin=True)
        url = local_site_reverse('github-app-install-callback',
                                 kwargs={'hosting_service_id': 'github'})
        response = self.client.get(url, {
            'step': 'reassign',
        })

        self.assertEqual(response.status_code, 404)

    def test_get_reassign_step_notes_verification_failure(self) -> None:
        """Testing GitHubAppInstallCallbackView GET ?step=reassign notes a
        failed check
        """
        installation_account = self._create_app_installation_account(
            repository_selection='selected')
        pat_account = self.create_hosting_account()
        self._create_org_repo('repo1', 'myorg', pat_account)

        self.spy_on(GitHubClient.get_installation_accessible_repositories,
                    op=kgb.SpyOpRaise(HostingServiceError('boom')))

        self.login_user(admin=True)
        url = local_site_reverse('github-app-install-callback',
                                 kwargs={'hosting_service_id': 'github'})
        response = self.client.get(url, {
            'step': 'reassign',
            'account_id': installation_account.pk,
        })

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['verification_failed'])
        self.assertEqual(list(response.context['repositories']), [])

    def test_get_redirects_to_wizard(self) -> None:
        """Testing GitHubAppInstallCallbackView GET redirects to the wizard"""
        app_account = self.create_hosting_account(data={
            'github_app': {
                'app_id': 12345,
                'app_slug': 'rb-app',
                'client_id': 'client-id',
                'client_secret': 'encrypted-client-secret',
                'private_key': 'encrypted-private-key',
                'role': 'app',
                'webhook_secret': 'encrypted-webhook-secret',
            },
        })
        pat_account = self.create_hosting_account()
        self._create_org_repo('repo1', 'myorg', pat_account)

        self.spy_on(
            GitHubClient.get_installation_info,
            op=kgb.SpyOpReturn(api.InstallationResponse(
                account=api.InstallationAccount(
                    login='myorg',
                    type='Organization',
                    avatar_url='https://example.com/a.png'),
                repository_selection='all')))

        self.login_user(admin=True)
        session = self.client.session
        session[views._INSTALL_SESSION_KEY] = {
            'state': 'teststate',
            'account_id': app_account.pk,
        }
        session.save()

        url = local_site_reverse('github-app-install-callback',
                                 kwargs={'hosting_service_id': 'github'})
        response = self.client.get(url, {
            'state': 'teststate',
            'installation_id': '42',
        })

        # The newly-created installation account drives the success step URL.
        installation_account = HostingServiceAccount.objects.get(
            service_name='github',
            username='myorg')

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'],
                         local_site_reverse('connected-services-list'))
        self.assertEqual(
            self.client.session['connect_wizard_url'],
            f'{url}?step=reassign&account_id={installation_account.pk}')

    def test_get_reinstall_reuses_existing_account(self) -> None:
        """Testing GitHubAppInstallCallbackView GET reuses the existing
        installation account on reinstall with a new installation ID
        """
        app_account = self.create_hosting_account(data={
            'github_app': {
                'app_id': 12345,
                'app_slug': 'rb-app',
                'client_id': 'client-id',
                'client_secret': 'encrypted-client-secret',
                'private_key': 'encrypted-private-key',
                'role': 'app',
                'webhook_secret': 'encrypted-webhook-secret',
            },
        })

        # An earlier install of the same app on the same org. GitHub issues a
        # new installation ID when the app is removed and reinstalled, so the
        # stored ID will not match the one coming back from the callback.
        existing_account = HostingServiceAccount.objects.create(
            service_name='github',
            username='myorg',
            hosting_url='',
            data={
                'github_app': {
                    'role': 'installation',
                    'app_account_id': app_account.pk,
                    'installation_id': 1,
                    'owner_id': 555,
                    'owner_login': 'myorg',
                    'owner_type': 'organization',
                    'repository_selection': 'all',
                },
            })

        self.spy_on(
            GitHubClient.get_installation_info,
            op=kgb.SpyOpReturn(api.InstallationResponse(
                account=api.InstallationAccount(
                    id=555,
                    login='myorg',
                    type='Organization',
                    avatar_url='https://example.com/a.png'),
                repository_selection='all')))

        self.login_user(admin=True)
        session = self.client.session
        session[views._INSTALL_SESSION_KEY] = {
            'state': 'teststate',
            'account_id': app_account.pk,
        }
        session.save()

        url = local_site_reverse('github-app-install-callback',
                                 kwargs={'hosting_service_id': 'github'})
        response = self.client.get(url, {
            'state': 'teststate',
            'installation_id': '42',
        })

        self.assertEqual(response.status_code, 302)

        # No duplicate account was created. The existing one was reused and
        # updated with the new installation ID.
        accounts = list(HostingServiceAccount.objects.filter(
            service_name='github',
            username='myorg'))

        self.assertEqual(len(accounts), 1)

        account = accounts[0]
        self.assertEqual(account.pk, existing_account.pk)
        self.assertEqual(account.data['github_app']['installation_id'], 42)

    def test_get_reinstall_matches_renamed_owner_by_id(self) -> None:
        """Testing GitHubAppInstallCallbackView reuses the account across a
        rename by matching the stable owner ID
        """
        app_account = self.create_hosting_account(data={
            'github_app': {
                'app_id': 12345,
                'app_slug': 'rb-app',
                'client_id': 'client-id',
                'client_secret': 'encrypted-client-secret',
                'private_key': 'encrypted-private-key',
                'role': 'app',
                'webhook_secret': 'encrypted-webhook-secret',
            },
        })

        # The org was named "oldname" when it was first installed. It has since
        # been renamed to "newname" on GitHub, but keeps the same numeric ID.
        existing_account = HostingServiceAccount.objects.create(
            service_name='github',
            username='oldname',
            hosting_url='',
            data={
                'github_app': {
                    'role': 'installation',
                    'app_account_id': app_account.pk,
                    'installation_id': 1,
                    'owner_id': 555,
                    'owner_login': 'oldname',
                    'owner_type': 'organization',
                    'repository_selection': 'all',
                },
            })

        self.spy_on(
            GitHubClient.get_installation_info,
            op=kgb.SpyOpReturn(api.InstallationResponse(
                account=api.InstallationAccount(
                    id=555,
                    login='newname',
                    type='Organization',
                    avatar_url='https://example.com/a.png'),
                repository_selection='all')))

        self.login_user(admin=True)
        session = self.client.session
        session[views._INSTALL_SESSION_KEY] = {
            'state': 'teststate',
            'account_id': app_account.pk,
        }
        session.save()

        url = local_site_reverse('github-app-install-callback',
                                 kwargs={'hosting_service_id': 'github'})
        response = self.client.get(url, {
            'state': 'teststate',
            'installation_id': '42',
        })

        self.assertEqual(response.status_code, 302)

        # The renamed org resolved to the same account by owner ID rather than
        # creating a duplicate. The login was refreshed to the new name.
        installations = [
            account
            for account in HostingServiceAccount.objects.filter(
                service_name='github')
            if account.data.get('github_app', {}).get('role') == 'installation'
        ]

        self.assertEqual(len(installations), 1)
        installation = installations[0]
        self.assertEqual(installation.pk, existing_account.pk)
        self.assertEqual(installation.username, 'newname')
        self.assertEqual(installation.data['github_app']['owner_id'], 555)

    def test_installation_account_parses_owner_id(self) -> None:
        """Testing api.InstallationResponse parses the account's stable owner
        ID
        """
        installation = api.InstallationResponse.model_validate_json(
            self.dump_json({
                'account': {
                    'id': 777,
                    'login': 'myorg',
                    'type': 'Organization',
                },
                'repository_selection': 'all',
            }))

        self.assertEqual(installation.account.id, 777)

    def test_get_test_mode_redirects_to_wizard(self) -> None:
        """Testing GitHubAppInstallCallbackView test_account preview in DEBUG
        """
        installation_account = self._create_app_installation_account()
        pat_account = self.create_hosting_account()
        self._create_org_repo('repo1', 'myorg', pat_account)

        self.login_user(admin=True)
        url = local_site_reverse('github-app-install-callback',
                                 kwargs={'hosting_service_id': 'github'})

        with self.settings(DEBUG=True):
            response = self.client.get(url, {
                'test_account': installation_account.pk,
            })

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'],
                         local_site_reverse('connected-services-list'))
        self.assertEqual(
            self.client.session['connect_wizard_url'],
            f'{url}?step=reassign&account_id={installation_account.pk}')

    def test_get_test_mode_ignored_without_debug(self) -> None:
        """Testing GitHubAppInstallCallbackView test_account ignored if no
        DEBUG
        """
        installation_account = self._create_app_installation_account()

        self.login_user(admin=True)
        url = local_site_reverse('github-app-install-callback',
                                 kwargs={'hosting_service_id': 'github'})

        with self.settings(DEBUG=False):
            response = self.client.get(url, {
                'test_account': installation_account.pk,
            })

        # Without DEBUG the preview is inert, so this falls through to the
        # normal flow and fails the missing-state check.
        self._assert_error_redirect(
            response,
            'The GitHub installation state was invalid or has expired. '
            'Please try connecting again.')

    def test_post_reassigns_selected_repositories(self) -> None:
        """Testing GitHubAppInstallCallbackView POST reassigns the repos"""
        installation_account = self._create_app_installation_account()
        pat_account = self.create_hosting_account()
        repository1 = self._create_org_repo('repo1', 'myorg', pat_account)
        repository2 = self._create_org_repo('repo2', 'myorg', pat_account)

        self.login_user(admin=True)
        url = local_site_reverse('github-app-install-callback',
                                 kwargs={'hosting_service_id': 'github'})
        response = self.client.post(url, {
            'account_id': installation_account.pk,
            'repositories': [repository1.pk],
        })

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            Repository.objects.get(pk=repository1.pk).hosting_account,
            installation_account)
        self.assertEqual(
            Repository.objects.get(pk=repository2.pk).hosting_account,
            pat_account)

    def test_post_ignores_non_candidate_repository(self) -> None:
        """Testing GitHubAppInstallCallbackView POST ignores non-candidates"""
        installation_account = self._create_app_installation_account()
        pat_account = self.create_hosting_account()
        repository = self._create_org_repo('repo1', 'otherorg', pat_account)

        self.login_user(admin=True)
        url = local_site_reverse('github-app-install-callback',
                                 kwargs={'hosting_service_id': 'github'})
        response = self.client.post(url, {
            'account_id': installation_account.pk,
            'repositories': [repository.pk],
        })

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            Repository.objects.get(pk=repository.pk).hosting_account,
            pat_account)

    def test_post_ignores_inaccessible_repository(self) -> None:
        """Testing GitHubAppInstallCallbackView POST ignores inaccessible repos
        """
        installation_account = self._create_app_installation_account(
            repository_selection='selected')
        pat_account = self.create_hosting_account()
        repository1 = self._create_org_repo('repo1', 'myorg', pat_account)
        repository2 = self._create_org_repo('repo2', 'myorg', pat_account)

        self.spy_on(
            GitHubClient.get_installation_accessible_repositories,
            op=kgb.SpyOpReturn(TestPaginator([
                [
                    api.Repository(
                        clone_url='',
                        default_branch='',
                        mirror_url='',
                        name='repo1',
                        owner=api.RepositoryOwner(login='myorg'),
                    ),
                ],
            ])))

        self.login_user(admin=True)
        url = local_site_reverse('github-app-install-callback',
                                 kwargs={'hosting_service_id': 'github'})
        response = self.client.post(url, {
            'account_id': installation_account.pk,
            'repositories': [repository1.pk, repository2.pk],
        })

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            Repository.objects.get(pk=repository1.pk).hosting_account,
            installation_account)
        self.assertEqual(
            Repository.objects.get(pk=repository2.pk).hosting_account,
            pat_account)

    def test_post_with_repository_lookup_failure(self) -> None:
        """Testing GitHubAppInstallCallbackView POST warns when the accessible
        repositories can't be retrieved
        """
        installation_account = self._create_app_installation_account(
            repository_selection='selected')
        pat_account = self.create_hosting_account()
        repository = self._create_org_repo('repo1', 'myorg', pat_account)

        self.spy_on(
            GitHubClient.get_installation_accessible_repositories,
            op=kgb.SpyOpRaise(HostingServiceError('Kaboom')))

        self.login_user(admin=True)
        url = local_site_reverse('github-app-install-callback',
                                 kwargs={'hosting_service_id': 'github'})
        response = self.client.post(url, {
            'account_id': installation_account.pk,
            'repositories': [repository.pk],
        })

        self.assertEqual(response.status_code, 302)

        # The repository was left on its old credentials.
        self.assertEqual(
            Repository.objects.get(pk=repository.pk).hosting_account,
            pat_account)

        # The administrator was told the move didn't happen.
        self.assertMessages(response, [
            Message(
                30,
                'Review Board is now connected to GitHub, but the '
                'repositories you selected could not be moved to the new '
                'connection. They are still using their old credentials. '
                'Please try moving them again.',
            ),
        ])

    def test_post_with_non_installation_account(self) -> None:
        """Testing GitHubAppInstallCallbackView POST with a non-app account"""
        pat_account = self.create_hosting_account()

        self.login_user(admin=True)
        url = local_site_reverse('github-app-install-callback',
                                 kwargs={'hosting_service_id': 'github'})
        response = self.client.post(url, {
            'account_id': pat_account.pk,
        })

        self._assert_error_redirect(
            response,
            'The specified GitHub App installation was not found. Please try '
            'connecting again.')

    def _create_org_repo(
        self,
        name: str,
        org: str,
        account: HostingServiceAccount,
        **kwargs,
    ) -> Repository:
        """Return an organization-plan repository owned by the given org.

        Args:
            name (str):
                The repository name.

            org (str):
                The owning organization.

            account (reviewboard.hostingsvcs.models.HostingServiceAccount):
                The account to attach the repository to.

            **kwargs (dict):
                Additional keyword arguments for the repository.

        Returns:
            reviewboard.scmtools.models.Repository:
            The new repository.
        """
        return self.create_repository(
            name=name,
            path=f'git://github.com/{org}/{name}.git',
            hosting_account=account,
            extra_data={
                'repository_plan': 'public-org',
                'github_public_org_name': org,
                'github_public_org_repo_name': name,
            },
            **kwargs)
