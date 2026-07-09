"""Unit tests for GitHub account data helpers.

Version Added:
    9.0
"""

from __future__ import annotations

from reviewboard.hostingsvcs.github.accounts import (
    GitHubAppInstallationData,
    get_app_settings_url,
    get_github_app_data,
    set_github_app_data,
)
from reviewboard.hostingsvcs.models import HostingServiceAccount
from reviewboard.hostingsvcs.tests.github.base import GitHubTestCase


class GetGitHubAppDataTests(GitHubTestCase):
    """Unit tests for get_github_app_data and set_github_app_data.

    Version Added:
        9.0
    """

    def test_caches_parsed_data(self) -> None:
        """Testing get_github_app_data caches the parsed data on the
        account instance
        """
        account = self.create_hosting_account(data={
            'github_app': {
                'role': 'installation',
                'app_account_id': 1,
                'installation_id': 42,
                'owner_login': 'myorg',
            },
        })

        app_data = get_github_app_data(account)

        assert isinstance(app_data, GitHubAppInstallationData)
        self.assertEqual(app_data.installation_id, 42)

        self.assertIs(get_github_app_data(account), app_data)

    def test_caches_missing_data(self) -> None:
        """Testing get_github_app_data caches a None result for accounts
        without github_app data
        """
        account = self.create_hosting_account()

        self.assertIsNone(get_github_app_data(account))
        self.assertIsNone(get_github_app_data(account))

    def test_no_caching_across_instances(self) -> None:
        """Testing get_github_app_data re-parses on a freshly-loaded
        account instance
        """
        account = self.create_hosting_account(data={
            'github_app': {
                'role': 'installation',
                'app_account_id': 1,
                'installation_id': 42,
                'owner_login': 'myorg',
            },
        })

        app_data = get_github_app_data(account)
        assert app_data is not None

        fresh_account = HostingServiceAccount.objects.get(pk=account.pk)
        fresh_app_data = get_github_app_data(fresh_account)

        assert fresh_app_data is not None
        self.assertIsNot(fresh_app_data, app_data)
        self.assertEqual(fresh_app_data, app_data)

    def test_set_stores_and_caches(self) -> None:
        """Testing set_github_app_data stores serialized data and updates
        the cache
        """
        account = self.create_hosting_account(data={
            'github_app': {
                'role': 'installation',
                'app_account_id': 1,
                'installation_id': 42,
                'owner_login': 'myorg',
            },
        })

        old_app_data = get_github_app_data(account)
        assert isinstance(old_app_data, GitHubAppInstallationData)

        new_app_data = old_app_data.model_copy(
            update={'installation_id': 43})
        set_github_app_data(account, new_app_data)

        self.assertEqual(account.data['github_app']['installation_id'], 43)
        self.assertIs(get_github_app_data(account), new_app_data)


class GetAppSettingsURLTests(GitHubTestCase):
    """Unit tests for get_app_settings_url.

    Version Added:
        9.0
    """

    def test_with_user_owner(self) -> None:
        """Testing get_app_settings_url with a user-owned app"""
        account = self._create_account(owner_type='user')

        self.assertEqual(get_app_settings_url(account),
                         'https://github.com/settings/apps/rb-app')

    def test_with_organization_owner(self) -> None:
        """Testing get_app_settings_url with an organization-owned app"""
        account = self._create_account(owner_type='organization')

        self.assertEqual(
            get_app_settings_url(account),
            'https://github.com/organizations/myuser/settings/apps/rb-app')

    def test_with_hosting_url(self) -> None:
        """Testing get_app_settings_url with a self-hosted GitHub server"""
        account = self._create_account(use_url=True, owner_type='user')

        self.assertEqual(get_app_settings_url(account),
                         'https://example.com/settings/apps/rb-app')

    def test_with_empty_slug(self) -> None:
        """Testing get_app_settings_url with an app missing a slug"""
        account = self._create_account(app_slug='')

        self.assertIsNone(get_app_settings_url(account))

    def test_with_installation_account(self) -> None:
        """Testing get_app_settings_url with an installation account"""
        account = self._create_app_installation_account()

        self.assertIsNone(get_app_settings_url(account))

    def test_without_app_data(self) -> None:
        """Testing get_app_settings_url with an account lacking app data"""
        account = self.create_hosting_account()

        self.assertIsNone(get_app_settings_url(account))

    def _create_account(
        self,
        *,
        use_url: bool = False,
        **app_data,
    ) -> HostingServiceAccount:
        """Return an app-record account with the given app data.

        Args:
            use_url (bool, optional):
                Whether to attach the account to a self-hosted GitHub URL.

            **app_data (dict):
                Fields to override in the stored ``github_app`` data.

        Returns:
            reviewboard.hostingsvcs.models.HostingServiceAccount:
            The new app-record account.
        """
        return self.create_hosting_account(
            use_url=use_url,
            data={
                'github_app': {
                    'app_id': 1,
                    'app_slug': 'rb-app',
                    'client_id': 'client-id',
                    'client_secret': 'client-secret',
                    'private_key': 'private-key',
                    'role': 'app',
                    'webhook_secret': 'webhook-secret',
                    **app_data,
                },
            })
