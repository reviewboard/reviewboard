"""Unit tests for GitHub account data helpers.

Version Added:
    9.0
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from reviewboard.hostingsvcs.github.accounts import (
    GitHubAppInstallationData,
    find_repository_for_installation,
    get_app_settings_url,
    get_github_app_data,
    set_github_app_data,
)
from reviewboard.hostingsvcs.models import HostingServiceAccount
from reviewboard.hostingsvcs.tests.github.base import GitHubTestCase

if TYPE_CHECKING:
    from reviewboard.scmtools.models import Repository


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


class FindRepositoryForInstallationTests(GitHubTestCase):
    """Unit tests for find_repository_for_installation.

    Version Added:
        9.0
    """

    def test_with_org_plan(self) -> None:
        """Testing find_repository_for_installation with an organization
        repository
        """
        installation = self._create_app_installation_account()
        repository = self.create_repository(
            hosting_account=installation,
            extra_data={
                'repository_plan': 'public-org',
                'github_public_org_name': 'myorg',
                'github_public_org_repo_name': 'myrepo',
            })

        self.assertEqual(
            find_repository_for_installation(account=installation,
                                             owner='myorg',
                                             name='myrepo'),
            repository)

    def test_with_user_plan(self) -> None:
        """Testing find_repository_for_installation with a user repository"""
        installation = self._create_app_installation_account(
            owner_login='myuser',
            owner_type='user')
        repository = self.create_repository(
            hosting_account=installation,
            extra_data={
                'repository_plan': 'public',
                'github_public_repo_name': 'myrepo',
            })

        self.assertEqual(
            find_repository_for_installation(account=installation,
                                             owner='myuser',
                                             name='myrepo'),
            repository)

    def test_with_other_installation(self) -> None:
        """Testing find_repository_for_installation ignores repositories on
        other installations
        """
        app_account = self._create_app_record_account()
        installation1 = self._create_app_installation_account(app_account)
        installation2 = self._create_app_installation_account(
            app_account,
            owner_id=556)
        self._create_org_repository(installation2)

        self.assertIsNone(find_repository_for_installation(
            account=installation1,
            owner='myorg',
            name='myrepo'))

    def test_with_archived_repository(self) -> None:
        """Testing find_repository_for_installation ignores archived
        repositories
        """
        installation = self._create_app_installation_account()
        self._create_org_repository(installation).archive()

        self.assertIsNone(find_repository_for_installation(
            account=installation,
            owner='myorg',
            name='myrepo'))

    def test_with_no_match(self) -> None:
        """Testing find_repository_for_installation with no matching
        repository
        """
        installation = self._create_app_installation_account()
        self._create_org_repository(installation)

        self.assertIsNone(find_repository_for_installation(
            account=installation,
            owner='myorg',
            name='otherrepo'))

    def test_with_cached_match(self) -> None:
        """Testing find_repository_for_installation with a cached match"""
        installation = self._create_app_installation_account()
        repository = self._create_org_repository(installation)

        find_repository_for_installation(account=installation,
                                         owner='myorg',
                                         name='myrepo')

        with self.assertNumQueries(1):
            self.assertEqual(
                find_repository_for_installation(account=installation,
                                                 owner='myorg',
                                                 name='myrepo'),
                repository)

    def test_with_cached_no_match(self) -> None:
        """Testing find_repository_for_installation with a cached map and no
        matching repository
        """
        installation = self._create_app_installation_account()
        self._create_org_repository(installation)

        find_repository_for_installation(account=installation,
                                         owner='myorg',
                                         name='myrepo')

        with self.assertNumQueries(0):
            self.assertIsNone(find_repository_for_installation(
                account=installation,
                owner='myorg',
                name='otherrepo'))

    def test_with_cached_empty_map(self) -> None:
        """Testing find_repository_for_installation caches the map for an
        installation without repositories
        """
        installation = self._create_app_installation_account()

        self.assertIsNone(find_repository_for_installation(
            account=installation,
            owner='myorg',
            name='myrepo'))

        with self.assertNumQueries(0):
            self.assertIsNone(find_repository_for_installation(
                account=installation,
                owner='myorg',
                name='myrepo'))

    def test_with_repository_added_after_caching(self) -> None:
        """Testing find_repository_for_installation finds a repository added
        after the map was cached
        """
        installation = self._create_app_installation_account()

        self.assertIsNone(find_repository_for_installation(
            account=installation,
            owner='myorg',
            name='myrepo'))

        repository = self._create_org_repository(installation)

        self.assertEqual(
            find_repository_for_installation(account=installation,
                                             owner='myorg',
                                             name='myrepo'),
            repository)

    def _create_org_repository(
        self,
        installation: HostingServiceAccount,
    ) -> Repository:
        """Return a new organization repository on an installation.

        Args:
            installation (reviewboard.hostingsvcs.models.
                          HostingServiceAccount):
                The installation account.

        Returns:
            reviewboard.scmtools.models.Repository:
            The new repository.
        """
        return self.create_repository(
            hosting_account=installation,
            extra_data={
                'repository_plan': 'public-org',
                'github_public_org_name': 'MyOrg',
                'github_public_org_repo_name': 'MyRepo',
            })
