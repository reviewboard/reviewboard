"""Unit tests for GitHub account data helpers.

Version Added:
    9.0
"""

from __future__ import annotations

from reviewboard.hostingsvcs.github.accounts import (
    GitHubAppInstallationData,
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
