"""Unit tests for the JIRA hosting service.

Version Added:
    9.0
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING

import kgb
from djblets.conditions import ConditionSet

import reviewboard.hostingsvcs.jira as jira_module
from reviewboard.hostingsvcs.bug_tracker_forms import BugTrackerForm
from reviewboard.hostingsvcs.errors import AuthorizationError
from reviewboard.hostingsvcs.models import ConfiguredBugTracker
from reviewboard.hostingsvcs.testing import HostingServiceTestCase
from reviewboard.scmtools.crypto_utils import (
    decrypt_password,
    encrypt_password,
)

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from typing import Any


class _FakeJIRAError(Exception):
    """A stand-in for jira.exceptions.JIRAError."""

    def __init__(
        self,
        text: str = '',
        status_code: (int | None) = None,
    ) -> None:
        """Initialize the error."""
        super().__init__(text)

        self.text = text
        self.status_code = status_code


class _FakeRequestError(Exception):
    """A stand-in for requests.RequestException."""


class _FakeJIRAIssue:
    """A stand-in for a JIRA issue."""

    def __init__(
        self,
        key: str,
        summary: str,
        status: str,
    ) -> None:
        """Initialize the issue."""
        self.key = key
        self.fields = SimpleNamespace(
            description='',
            summary=summary,
            status=status,
        )


class FakePickerResponse:
    """A stand-in for a response from JIRA's issue picker."""

    def __init__(
        self,
        keys: Sequence[str] = (),
    ) -> None:
        """Initialize the response.

        Args:
            keys (list of str, optional):
                The issue keys the picker matched.
        """
        self.keys = keys

    def raise_for_status(self) -> None:
        """Do nothing, since the request succeeded."""

    def json(self) -> dict[str, Any]:
        """Return the response payload."""
        return {
            'sections': [
                {
                    'id': 'cs',
                    'issues': [
                        {
                            'key': key,
                        }
                        for key in self.keys
                    ],
                },
            ],
        }


class _FakeSession:
    """A stand-in for the HTTP session used by the JIRA client."""

    def get(
        self,
        url: str,
        params: Mapping[str, str],
    ) -> FakePickerResponse:
        """Return a response with no matches."""
        return FakePickerResponse()


class _FakeJIRAClient:
    """A stand-in for jira.client.JIRA.

    The methods return empty results. Tests spy on them to provide
    results or errors.
    """

    def __init__(
        self,
        options: Mapping[str, Any],
        max_retries: int,
        timeout: float,
        basic_auth: (tuple[str, str] | None) = None,
    ) -> None:
        """Initialize the client."""
        self.options = options
        self.basic_auth = basic_auth
        self.timeout = timeout
        self._session = _FakeSession()

    def myself(self) -> dict[str, Any]:
        """Return the authenticated user."""
        return {}

    def issue(
        self,
        id: str,
        fields: (str | None) = None,
    ) -> _FakeJIRAIssue:
        """Return a single issue, or raise if it does not exist."""
        raise _FakeJIRAError(
            text=f'Issue {id} does not exist',
            status_code=404,
        )

    def search_issues(
        self,
        jql: str,
        maxResults: int,  # noqa: N803
        validate_query: bool = True,
        fields: (str | None) = None,
    ) -> list[_FakeJIRAIssue]:
        """Return search results."""
        return []


_UNSET = object()


def _restore_module_attr(
    attr: str,
    value: object,
) -> None:
    """Restore an attribute on the JIRA hosting service module.

    Args:
        attr (str):
            The name of the attribute.

        value (object):
            The original value, or ``_UNSET`` if the attribute did not exist.
    """
    if value is _UNSET:
        delattr(jira_module, attr)
    else:
        setattr(jira_module, attr, value)


class JIRATestCase(HostingServiceTestCase[jira_module.JIRA]):
    """Base class for JIRA unit tests.

    This handles mocking for the ``jira`` package.

    Version Added:
        9.0
    """

    service_name = 'jira'
    default_hosting_url = 'https://jira.example.com'

    def setUp(self) -> None:
        """Set up the test case."""
        super().setUp()

        # The jira package is optional, so these may not exist on the
        # module. They're put back the way they were after each test.
        fakes = {
            'has_jira': True,
            'JIRAClient': _FakeJIRAClient,
            'JIRAError': _FakeJIRAError,
            'RequestException': _FakeRequestError,
        }

        for attr, value in fakes.items():
            self.addCleanup(
                _restore_module_attr,
                attr,
                getattr(jira_module, attr, _UNSET),
            )
            setattr(jira_module, attr, value)

    def get_jira_service(
        self,
        config: ConfiguredBugTracker,
    ) -> jira_module.JIRA:
        """Return the JIRA service for a bug tracker configuration.

        Args:
            config (reviewboard.hostingsvcs.models.ConfiguredBugTracker):
                The bug tracker configuration.

        Returns:
            reviewboard.hostingsvcs.jira.JIRA:
            The JIRA service.
        """
        service = config.service
        assert isinstance(service, jira_module.JIRA)

        return service


class JIRAAuthFormTests(JIRATestCase):
    """Unit tests for JIRAAuthForm.

    Version Added:
        9.0
    """

    def test_get_hosting_url(self) -> None:
        """Testing JIRAAuthForm.get_hosting_url returns the server URL"""
        form = jira_module.JIRAAuthForm(
            data={
                'hosting_account_username': 'myuser',
                'hosting_account_password': 'mytoken',
                'jira_server_url': 'https://jira.example.com/',
            },
            hosting_service_cls=jira_module.JIRA)

        self.assertTrue(form.is_valid(), form.errors)

        # Trailing slashes are stripped.
        self.assertEqual(form.get_hosting_url(), 'https://jira.example.com')

    def test_save_with_same_username_on_two_servers(self) -> None:
        """Testing JIRAAuthForm.save with the same username on two servers
        creates two accounts
        """
        accounts = []

        for server_url in ('https://one.example.com',
                           'https://two.example.com'):
            form = jira_module.JIRAAuthForm(
                data={
                    'hosting_account_username': 'myuser',
                    'hosting_account_password': 'mytoken',
                    'jira_server_url': server_url,
                },
                hosting_service_cls=jira_module.JIRA)

            self.assertTrue(form.is_valid(), form.errors)
            accounts.append(form.save())

        self.assertNotEqual(accounts[0].pk, accounts[1].pk)

        for account in accounts:
            account.refresh_from_db()

        self.assertEqual(accounts[0].hosting_url, 'https://one.example.com')
        self.assertEqual(accounts[1].hosting_url, 'https://two.example.com')


class JIRAAuthFormDeploymentTests(JIRATestCase):
    """Unit tests for JIRAAuthForm deployment handling.

    Version Added:
        9.0
    """

    def test_cloud_composes_server_url(self) -> None:
        """Testing JIRAAuthForm with JIRA Cloud composes the server URL
        from the site name
        """
        form = jira_module.JIRAAuthForm(
            data={
                'jira_deployment': 'cloud',
                'jira_cloud_site': 'myteam',
                'hosting_account_username': 'me@example.com',
                'hosting_account_password': 'mytoken',
            },
            hosting_service_cls=jira_module.JIRA)

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.get_hosting_url(),
                         'https://myteam.atlassian.net')

    def test_cloud_normalizes_pasted_urls(self) -> None:
        """Testing JIRAAuthForm with JIRA Cloud normalizes pasted URLs
        down to the site name
        """
        form = jira_module.JIRAAuthForm(
            data={
                'jira_deployment': 'cloud',
                'jira_cloud_site': 'https://MyTeam.atlassian.net/jira',
                'hosting_account_username': 'me@example.com',
                'hosting_account_password': 'mytoken',
            },
            hosting_service_cls=jira_module.JIRA)

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['jira_server_url'],
                         'https://myteam.atlassian.net')

    def test_cloud_requires_site(self) -> None:
        """Testing JIRAAuthForm with JIRA Cloud requires the site name"""
        form = jira_module.JIRAAuthForm(
            data={
                'jira_deployment': 'cloud',
                'hosting_account_username': 'me@example.com',
                'hosting_account_password': 'mytoken',
            },
            hosting_service_cls=jira_module.JIRA)

        self.assertFalse(form.is_valid())
        self.assertIn('jira_cloud_site', form.errors)

    def test_data_center_requires_server_url(self) -> None:
        """Testing JIRAAuthForm defaults to Data Center and requires the
        server URL
        """
        form = jira_module.JIRAAuthForm(
            data={
                'hosting_account_username': 'myuser',
                'hosting_account_password': 'mypass',
            },
            hosting_service_cls=jira_module.JIRA)

        self.assertFalse(form.is_valid())
        self.assertIn('jira_server_url', form.errors)

    def test_data_center_with_invalid_server_url(self) -> None:
        """Testing JIRAAuthForm with Data Center rejects server URLs that
        are not full HTTP or HTTPS URLs
        """
        for server_url in ('jira.example.com',
                           'ftp://jira.example.com',
                           'https://'):
            with self.subTest(server_url=server_url):
                form = jira_module.JIRAAuthForm(
                    data={
                        'jira_deployment': 'dc',
                        'jira_server_url': server_url,
                        'hosting_account_username': 'myuser',
                        'hosting_account_password': 'mypass',
                    },
                    hosting_service_cls=jira_module.JIRA)

                self.assertFalse(form.is_valid())
                self.assertIn('jira_server_url', form.errors)

    def test_data_center_with_intranet_server_url(self) -> None:
        """Testing JIRAAuthForm with Data Center accepts single-label
        intranet hostnames with ports
        """
        form = jira_module.JIRAAuthForm(
            data={
                'jira_deployment': 'dc',
                'jira_server_url': 'http://jira:8080/',
                'hosting_account_username': 'myuser',
                'hosting_account_password': 'mypass',
            },
            hosting_service_cls=jira_module.JIRA)

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.get_hosting_url(), 'http://jira:8080')

    def test_required_flags_per_deployment(self) -> None:
        """Testing JIRAAuthForm marks the chosen deployment's URL field
        required
        """
        form = jira_module.JIRAAuthForm(
            data={
                'jira_deployment': 'cloud',
            },
            hosting_service_cls=jira_module.JIRA)
        self.assertTrue(form.fields['jira_cloud_site'].required)
        self.assertFalse(form.fields['jira_server_url'].required)

        form = jira_module.JIRAAuthForm(
            data={
                'jira_deployment': 'dc',
            },
            hosting_service_cls=jira_module.JIRA)
        self.assertTrue(form.fields['jira_server_url'].required)
        self.assertFalse(form.fields['jira_cloud_site'].required)


class JIRARequiresAccountTests(JIRATestCase):
    """Unit tests for JIRA's account requirement on configurations.

    Version Added:
        9.0
    """

    def test_config_requires_account(self) -> None:
        """Testing JIRA bug tracker configurations require an account"""
        form = BugTrackerForm(
            data={
                'apply_to': ConfiguredBugTracker.APPLY_TO_ALL,
                'enabled': True,
                'name': 'My Tracker',
                'service_name': 'jira',
                'user_conditions_last_id': '0',
                'user_conditions_mode': ConditionSet.MODE_ALL,
            })

        self.assertFalse(form.is_valid())
        self.assertIn('hosting_account', form.errors)

    def test_legacy_config_grandfathered(self) -> None:
        """Testing migrated legacy JIRA configurations stay editable
        without an account
        """
        bug_tracker = self.create_bug_tracker(
            name='Legacy JIRA',
            service_name='jira',
            settings={
                'jira_url': 'https://jira.example.com',
            })

        form = BugTrackerForm(
            data={
                'apply_to': ConfiguredBugTracker.APPLY_TO_ALL,
                'enabled': True,
                'name': 'Legacy JIRA',
                'service_name': 'jira',
                'user_conditions_last_id': '0',
                'user_conditions_mode': ConditionSet.MODE_ALL,
            },
            instance=bug_tracker)

        self.assertTrue(form.is_valid(), form.errors)

        bug_tracker = form.save()
        self.assertIsNone(bug_tracker.hosting_account)

        # The legacy server URL is preserved.
        self.assertEqual(bug_tracker.settings['jira_url'],
                         'https://jira.example.com')

    def test_config_with_account(self) -> None:
        """Testing JIRA bug tracker configurations save with an account"""
        account = self.create_hosting_account(use_url=True)

        form = BugTrackerForm(
            data={
                'apply_to': ConfiguredBugTracker.APPLY_TO_ALL,
                'enabled': True,
                'hosting_account': account.pk,
                'name': 'My Tracker',
                'service_name': 'jira',
                'user_conditions_last_id': '0',
                'user_conditions_mode': ConditionSet.MODE_ALL,
            })

        self.assertTrue(form.is_valid(), form.errors)

        bug_tracker = form.save()
        self.assertEqual(bug_tracker.hosting_account, account)


class JIRABugTrackerConfigFormTests(JIRATestCase):
    """Unit tests for JIRABugTrackerConfigForm.

    Version Added:
        9.0
    """

    def test_project_normalized(self) -> None:
        """Testing JIRABugTrackerConfigForm normalizes the project key"""
        form = jira_module.JIRABugTrackerConfigForm(
            data={
                'jira_project': ' eng ',
            },
            hosting_service_cls=jira_module.JIRA)

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['jira_project'], 'ENG')

    def test_invalid_project(self) -> None:
        """Testing JIRABugTrackerConfigForm with an invalid project key"""
        form = jira_module.JIRABugTrackerConfigForm(
            data={
                'jira_project': 'not a key',
            },
            hosting_service_cls=jira_module.JIRA)

        self.assertFalse(form.is_valid())
        self.assertIn('jira_project', form.errors)

    def test_is_bug_tracker_config_form(self) -> None:
        """Testing JIRA uses JIRABugTrackerConfigForm for configs"""
        self.assertIs(jira_module.JIRA.bug_tracker_config_form,
                      jira_module.JIRABugTrackerConfigForm)


class JIRASortKeyTests(JIRATestCase):
    """Unit tests for JIRA.get_bug_id_sort_key.

    Version Added:
        9.0
    """

    def test_with_issue_key(self) -> None:
        """Testing JIRA.get_bug_id_sort_key with an issue key"""
        service = self.create_bug_tracker(service_name='jira').service

        self.assertEqual(service.get_bug_id_sort_key(bug_id='ENG-42'),
                         ('ENG', 42))
        self.assertEqual(service.get_bug_id_sort_key(bug_id='eng-5'),
                         ('ENG', 5))

    def test_with_other_ids(self) -> None:
        """Testing JIRA.get_bug_id_sort_key with non-issue-key IDs"""
        service = self.create_bug_tracker(service_name='jira').service

        self.assertIsNone(service.get_bug_id_sort_key(bug_id='123'))
        self.assertIsNone(service.get_bug_id_sort_key(bug_id='not a key'))

    def test_sorts_bug_ids(self) -> None:
        """Testing sort_bug_ids with a JIRA tracker"""
        from reviewboard.reviews.models.bug import sort_bug_ids

        tracker = self.create_bug_tracker(
            service_name='jira',
            hosting_account=self.create_hosting_account())

        self.assertEqual(
            sort_bug_ids(['ENG-12', 'APP-3', 'ENG-5'], tracker=tracker),
            ['APP-3', 'ENG-5', 'ENG-12'])


class JIRAConfigURLTests(JIRATestCase):
    """Unit tests for JIRA server URL resolution on configurations.

    Version Added:
        9.0
    """

    def test_get_bug_url_with_settings_url(self) -> None:
        """Testing JIRA.get_bug_url with a legacy settings URL"""
        config = self.create_bug_tracker(
            service_name='jira',
            settings={
                'jira_url': 'https://jira.example.com',
            })

        self.assertEqual(config.service.get_bug_url(config=config,
                                                    bug_id='ENG-1'),
                         'https://jira.example.com/browse/ENG-1')

    def test_get_bug_url_with_account_url(self) -> None:
        """Testing JIRA.get_bug_url falls back to the account's server"""
        account = self.create_hosting_account()
        account.hosting_url = 'https://myteam.atlassian.net'
        account.save()

        config = self.create_bug_tracker(
            service_name='jira',
            hosting_account=account)

        self.assertEqual(config.service.get_bug_url(config=config,
                                                    bug_id='ENG-1'),
                         'https://myteam.atlassian.net/browse/ENG-1')

    def test_get_bug_url_without_url(self) -> None:
        """Testing JIRA.get_bug_url without any server URL"""
        config = self.create_bug_tracker(service_name='jira')

        self.assertIsNone(config.service.get_bug_url(config=config,
                                                     bug_id='ENG-1'))

    def test_get_bug_tracker_display_path(self) -> None:
        """Testing JIRAConnectUI.get_bug_tracker_display_path with a
        self-hosted server
        """
        config = self.create_bug_tracker(
            service_name='jira',
            hosting_account=self.create_hosting_account(use_url=True))

        self.assertEqual(
            jira_module.JIRA.connect_ui.get_bug_tracker_display_path(config),
            'https://jira.example.com')

    def test_get_bug_tracker_display_path_with_jira_cloud(self) -> None:
        """Testing JIRAConnectUI.get_bug_tracker_display_path with a JIRA
        Cloud site
        """
        account = self.create_hosting_account()
        account.hosting_url = 'https://myteam.atlassian.net'
        account.save()

        config = self.create_bug_tracker(
            service_name='jira',
            hosting_account=account)

        self.assertEqual(
            jira_module.JIRA.connect_ui.get_bug_tracker_display_path(config),
            '')

    def test_get_bug_tracker_display_path_with_settings_url(self) -> None:
        """Testing JIRAConnectUI.get_bug_tracker_display_path with a legacy
        settings URL
        """
        config = self.create_bug_tracker(
            service_name='jira',
            settings={
                'jira_url': 'https://jira.example.com',
            })

        self.assertEqual(
            jira_module.JIRA.connect_ui.get_bug_tracker_display_path(config),
            'https://jira.example.com')


class JIRAAuthorizeTests(JIRATestCase):
    """Unit tests for JIRA.authorize.

    Version Added:
        9.0
    """

    def test_authorize(self) -> None:
        """Testing JIRA.authorize stores verified credentials"""
        account = self.create_hosting_account()
        service = account.service

        self.spy_on(_FakeJIRAClient.__init__, owner=_FakeJIRAClient)
        self.spy_on(_FakeJIRAClient.myself, owner=_FakeJIRAClient)

        service.authorize(
            username='myuser',
            password='mytoken',
            hosting_url='https://jira.example.com')

        self.assertSpyCalledWith(
            _FakeJIRAClient.__init__,
            options={
                'server': 'https://jira.example.com',
            },
            basic_auth=('myuser', 'mytoken'))
        self.assertSpyCalled(_FakeJIRAClient.myself)

        account.refresh_from_db()
        self.assertTrue(service.is_authorized())
        self.assertEqual(decrypt_password(account.data['password']),
                         'mytoken')

    def test_authorize_with_invalid_credentials(self) -> None:
        """Testing JIRA.authorize with invalid credentials"""
        account = self.create_hosting_account()
        service = account.service

        self.spy_on(
            _FakeJIRAClient.myself,
            owner=_FakeJIRAClient,
            op=kgb.SpyOpRaise(_FakeJIRAError(
                text='Client must be authenticated',
                status_code=401,
            )),
        )

        with self.assertRaisesMessage(
                AuthorizationError,
                'JIRA rejected the username and API token or password.'):
            service.authorize(
                username='myuser',
                password='badtoken',
                hosting_url='https://jira.example.com')

        self.assertFalse(service.is_authorized())

    def test_authorize_with_password_on_jira_cloud(self) -> None:
        """Testing JIRA.authorize with rejected credentials on JIRA
        Cloud points to API tokens
        """
        account = self.create_hosting_account()
        service = account.service

        self.spy_on(
            _FakeJIRAClient.myself,
            owner=_FakeJIRAClient,
            op=kgb.SpyOpRaise(_FakeJIRAError(
                text='Client must be authenticated',
                status_code=401,
            )),
        )

        with self.assertRaisesMessage(
                AuthorizationError,
                'JIRA Cloud requires an API token instead of a password.'):
            service.authorize(
                username='myuser@example.com',
                password='my-account-password',
                hosting_url='https://myteam.atlassian.net')

        self.assertFalse(service.is_authorized())

    def test_authorize_with_other_error(self) -> None:
        """Testing JIRA.authorize with a non-401 error shows the error
        text without the response dump
        """
        account = self.create_hosting_account()
        service = account.service

        self.spy_on(
            _FakeJIRAClient.myself,
            owner=_FakeJIRAClient,
            op=kgb.SpyOpRaise(_FakeJIRAError(
                text='CAPTCHA required',
                status_code=403,
            )),
        )

        with self.assertRaisesMessage(
                AuthorizationError,
                'Unable to authenticate with JIRA: CAPTCHA required'):
            service.authorize(
                username='myuser',
                password='mytoken',
                hosting_url='https://jira.example.com')

    def test_authorize_without_jira_module(self) -> None:
        """Testing JIRA.authorize without the jira module installed"""
        account = self.create_hosting_account()
        service = account.service

        jira_module.has_jira = False

        with self.assertRaisesMessage(AuthorizationError,
                                      'requires the "jira" Python package'):
            service.authorize(
                username='myuser',
                password='mytoken',
                hosting_url='https://jira.example.com')

    def test_authorize_without_credentials(self) -> None:
        """Testing JIRA.authorize without full credentials"""
        account = self.create_hosting_account()
        service = account.service

        self.spy_on(_FakeJIRAClient.__init__, owner=_FakeJIRAClient)

        with self.assertRaisesMessage(AuthorizationError, 'are required'):
            service.authorize(
                username='myuser',
                password='',
                hosting_url='https://jira.example.com')

        self.assertSpyNotCalled(_FakeJIRAClient.__init__)


class JIRAClientCredentialsTests(JIRATestCase):
    """Unit tests for JIRA API credential usage.

    Version Added:
        9.0
    """

    def test_search_bugs_with_account_credentials(self) -> None:
        """Testing JIRA.search_bugs authenticates with the config
        account's credentials on the account's server
        """
        account = self.create_hosting_account(
            use_url=True,
            data={
                'password': encrypt_password('mytoken'),
            })

        # This is a migrated legacy configuration that later had an account
        # linked. The legacy URL is ignored, so the credentials can't be
        # sent to a different server (or over plain HTTP).
        config = self.create_bug_tracker(
            service_name='jira',
            hosting_account=account,
            settings={
                'jira_url': 'http://legacy-jira.example.com',
            })
        service = self.get_jira_service(config)

        service.search_bugs(config=config, query='crash')

        client = service.jira_client
        assert isinstance(client, _FakeJIRAClient)

        self.assertEqual(client.basic_auth, ('myuser', 'mytoken'))
        self.assertEqual(client.options, {
            'server': 'https://jira.example.com',
        })

    def test_search_bugs_without_account_is_anonymous(self) -> None:
        """Testing JIRA bug lookups without an account, connecting anonymously
        """
        config = self.create_bug_tracker(
            service_name='jira',
            settings={
                'jira_url': 'https://jira.example.com',
            })
        service = self.get_jira_service(config)

        service.search_bugs(config=config, query='crash')

        client = service.jira_client
        assert isinstance(client, _FakeJIRAClient)

        self.assertIsNone(client.basic_auth)

    def test_get_bug_info_with_repository_legacy_url(self) -> None:
        """Testing JIRA.get_bug_info_uncached with a repository's legacy URL
        does not send the config account's credentials there
        """
        account = self.create_hosting_account(
            use_url=True,
            data={
                'password': encrypt_password('mytoken'),
            })
        config = self.create_bug_tracker(
            service_name='jira',
            hosting_account=account)
        repository = self.create_repository(extra_data={
            'bug_tracker-jira_url': 'http://legacy-jira.example.com',
        })
        service = self.get_jira_service(config)

        service.get_bug_info_uncached(repository=repository,
                                      bug_id='ENG-1')

        client = service.jira_client
        assert isinstance(client, _FakeJIRAClient)

        self.assertIsNone(client.basic_auth)
        self.assertEqual(client.options, {
            'server': 'http://legacy-jira.example.com',
        })

        # The anonymous client isn't reused for the account's own server.
        service.search_bugs(config=config, query='crash')

        client = service.jira_client
        assert isinstance(client, _FakeJIRAClient)

        self.assertEqual(client.basic_auth, ('myuser', 'mytoken'))
        self.assertEqual(client.options, {
            'server': 'https://jira.example.com',
        })

    def test_client_timeout(self) -> None:
        """Testing JIRA API clients are built with a request timeout"""
        config = self.create_bug_tracker(
            service_name='jira',
            settings={
                'jira_url': 'https://jira.example.com',
            })
        service = self.get_jira_service(config)

        service.search_bugs(config=config, query='crash')

        client = service.jira_client
        assert isinstance(client, _FakeJIRAClient)

        self.assertEqual(client.timeout, 10)

    def test_get_bug_info_with_unreachable_server(self) -> None:
        """Testing JIRA.get_bug_info_uncached with an unreachable server
        returns empty information
        """
        config = self.create_bug_tracker(
            service_name='jira',
            settings={
                'jira_url': 'https://jira.example.com',
            })
        service = self.get_jira_service(config)

        self.spy_on(
            _FakeJIRAClient.__init__,
            owner=_FakeJIRAClient,
            op=kgb.SpyOpRaise(_FakeRequestError('Connection refused')),
        )

        self.assertEqual(
            service.get_bug_info_uncached(config=config, bug_id='ENG-1'),
            {
                'description': '',
                'status': '',
                'summary': '',
            })
        self.assertIsNone(service.jira_client)

    def test_get_bug_info_with_request_error(self) -> None:
        """Testing JIRA.get_bug_info_uncached with a request error while
        fetching the issue returns empty information
        """
        config = self.create_bug_tracker(
            service_name='jira',
            settings={
                'jira_url': 'https://jira.example.com',
            })
        service = self.get_jira_service(config)

        self.spy_on(
            _FakeJIRAClient.issue,
            owner=_FakeJIRAClient,
            op=kgb.SpyOpRaise(_FakeRequestError('Read timed out')),
        )

        self.assertEqual(
            service.get_bug_info_uncached(config=config, bug_id='ENG-1'),
            {
                'description': '',
                'status': '',
                'summary': '',
            })


class JIRABugInfoTests(JIRATestCase):
    """Unit tests for JIRA.get_bug_info_uncached.

    Version Added:
        9.0
    """

    def test_get_bug_info(self) -> None:
        """Testing JIRA.get_bug_info_uncached loads only the needed fields"""
        config = self.create_bug_tracker(
            service_name='jira',
            settings={
                'jira_url': 'https://jira.example.com',
            })

        self.spy_on(
            _FakeJIRAClient.issue,
            owner=_FakeJIRAClient,
            op=kgb.SpyOpReturn(
                _FakeJIRAIssue('ENG-1', 'A crash', 'Open')),
        )

        bug_info = self.get_jira_service(config).get_bug_info_uncached(
            config=config,
            bug_id='ENG-1')

        self.assertSpyCalledWith(_FakeJIRAClient.issue,
                                 'ENG-1',
                                 fields='summary,status,description')
        self.assertEqual(bug_info, {
            'description': '',
            'status': 'Open',
            'summary': 'A crash',
        })


class JIRASearchTests(JIRATestCase):
    """Unit tests for JIRA.search_bugs.

    Version Added:
        9.0
    """

    def setUp(self) -> None:
        """Set up the test case."""
        super().setUp()

        self.config = self.create_bug_tracker(
            service_name='jira',
            settings={
                'jira_url': 'https://jira.example.com',
            })

    def test_search_bugs_without_jira_module(self) -> None:
        """Testing JIRA.search_bugs without the jira module installed"""
        config = self.config

        jira_module.has_jira = False

        self.assertEqual(
            config.service.search_bugs(config=config, query='crash'),
            [])

    def test_search_bugs_with_empty_query(self) -> None:
        """Testing JIRA.search_bugs with an empty query does not contact
        the server
        """
        config = self.config
        service = self.get_jira_service(config)

        self.assertEqual(service.search_bugs(config=config, query='  '), [])
        self.assertIsNone(service.jira_client)

    def test_search_bugs(self) -> None:
        """Testing JIRA.search_bugs"""
        config = self.config

        self.spy_on(
            _FakeJIRAClient.search_issues,
            owner=_FakeJIRAClient,
            op=kgb.SpyOpReturn([
                _FakeJIRAIssue('PROJ-42', 'Crash on startup', 'Open'),
            ]),
        )

        results = config.service.search_bugs(config=config,
                                             query='crash "quoted"')

        self.assertEqual(results, [
            {
                'bug_id': 'PROJ-42',
                'status': 'Open',
                'summary': 'Crash on startup',
            },
        ])

        # Quotes in the query are escaped in the JQL, and only the
        # summary is searched.
        self.assertSpyCallCount(_FakeJIRAClient.search_issues, 1)
        self.assertSpyCalledWith(
            _FakeJIRAClient.search_issues,
            'summary ~ "crash \\"quoted\\"*"',
            maxResults=25,
            validate_query=False,
            fields='summary,status')

    def test_search_bugs_with_picker(self) -> None:
        """Testing JIRA.search_bugs uses the issue picker, promoting an
        exact key match
        """
        config = self.config

        self.spy_on(
            _FakeSession.get,
            owner=_FakeSession,
            op=kgb.SpyOpReturn(FakePickerResponse([
                'ENG-10',
                'ENG-1',
                'ENG-100',
            ])),
        )

        # ENG-100 is left out, simulating an issue that could not be
        # loaded.
        self.spy_on(
            _FakeJIRAClient.search_issues,
            owner=_FakeJIRAClient,
            op=kgb.SpyOpReturn([
                _FakeJIRAIssue('ENG-10', 'Crash on startup', 'Open'),
                _FakeJIRAIssue('ENG-1', 'First bug', 'Open'),
            ]),
        )

        results = config.service.search_bugs(config=config, query='eng-1')

        self.assertSpyCalledWith(
            _FakeSession.get,
            'https://jira.example.com/rest/api/2/issue/picker',
            params={
                'query': 'eng-1',
                'currentJQL': '',
            })

        # Details are loaded for the picker's keys, with the exact
        # match promoted to the front.
        self.assertSpyCallCount(_FakeJIRAClient.search_issues, 1)
        self.assertSpyCalledWith(
            _FakeJIRAClient.search_issues,
            'key in ("ENG-1", "ENG-10", "ENG-100")',
            maxResults=3,
            validate_query=False)

        self.assertEqual(results, [
            {
                'bug_id': 'ENG-1',
                'status': 'Open',
                'summary': 'First bug',
            },
            {
                'bug_id': 'ENG-10',
                'status': 'Open',
                'summary': 'Crash on startup',
            },
        ])

    def test_search_bugs_with_project_scoping(self) -> None:
        """Testing JIRA.search_bugs with a project-scoped configuration
        filters other projects' issues
        """
        config = self.create_bug_tracker(
            service_name='jira',
            settings={
                'jira_url': 'https://jira.example.com',
                'jira_project': 'ENG',
            })

        self.spy_on(
            _FakeSession.get,
            owner=_FakeSession,
            op=kgb.SpyOpReturn(FakePickerResponse([
                'OTHER-5',
                'ENG-10',
                'ENG-1',
            ])),
        )
        self.spy_on(
            _FakeJIRAClient.search_issues,
            owner=_FakeJIRAClient,
            op=kgb.SpyOpReturn([
                _FakeJIRAIssue('ENG-10', 'Crash on startup', 'Open'),
                _FakeJIRAIssue('ENG-1', 'First bug', 'Open'),
            ]),
        )

        results = config.service.search_bugs(config=config, query='eng-1')

        # The picker's current search is limited to the project.
        self.assertSpyCalledWith(
            _FakeSession.get,
            'https://jira.example.com/rest/api/2/issue/picker',
            params={
                'query': 'eng-1',
                'currentJQL': 'project = "ENG"',
            })

        # The other project's issue (as from the picker's history section)
        # never reaches the details query.
        self.assertSpyCallCount(_FakeJIRAClient.search_issues, 1)
        self.assertSpyCalledWith(
            _FakeJIRAClient.search_issues,
            'key in ("ENG-1", "ENG-10")',
            maxResults=2,
            validate_query=False)

        self.assertEqual(
            [result['bug_id'] for result in results],
            ['ENG-1', 'ENG-10'])

    def test_search_bugs_with_picker_unavailable(self) -> None:
        """Testing JIRA.search_bugs falls back to JQL when the issue
        picker is unavailable
        """
        config = self.config

        self.spy_on(
            _FakeSession.get,
            owner=_FakeSession,
            op=kgb.SpyOpRaise(Exception('404 from server')),
        )
        self.spy_on(
            _FakeJIRAClient.search_issues,
            owner=_FakeJIRAClient,
            op=kgb.SpyOpReturn([
                _FakeJIRAIssue('ENG-102', 'Crash on startup', 'Open'),
            ]),
        )

        results = config.service.search_bugs(config=config, query='eng-102')

        # The exact key is tried first, then summaries. The duplicate
        # result is dropped.
        search_issues = _FakeJIRAClient.search_issues
        self.assertSpyCallCount(search_issues, 2)
        self.assertSpyCalledWith(
            search_issues.calls[0],
            'key = "ENG-102"',
            maxResults=25,
            validate_query=False)
        self.assertSpyCalledWith(
            search_issues.calls[1],
            'summary ~ "eng-102*"',
            maxResults=24,
            validate_query=False)

        self.assertEqual(results, [
            {
                'bug_id': 'ENG-102',
                'status': 'Open',
                'summary': 'Crash on startup',
            },
        ])


class JIRABulkBugInfoTests(JIRATestCase):
    """Unit tests for JIRA.get_bugs_info.

    Version Added:
        9.0
    """

    def setUp(self) -> None:
        """Set up the test case."""
        super().setUp()

        self.config = self.create_bug_tracker(
            service_name='jira',
            settings={
                'jira_url': 'https://jira.example.com',
            })

    def test_get_bugs_info(self) -> None:
        """Testing JIRA.get_bugs_info fetches every issue in one query"""
        config = self.config

        self.spy_on(
            _FakeJIRAClient.search_issues,
            owner=_FakeJIRAClient,
            op=kgb.SpyOpReturn([
                _FakeJIRAIssue('ENG-1', 'A crash', 'Open'),
                _FakeJIRAIssue('ENG-2', 'A typo', 'Fixed'),
            ]),
        )

        bugs_info = config.service.get_bugs_info(
            config=config,
            bug_ids=['ENG-1', 'ENG-2'])

        self.assertSpyCallCount(_FakeJIRAClient.search_issues, 1)
        self.assertSpyCalledWith(
            _FakeJIRAClient.search_issues,
            'key in ("ENG-1", "ENG-2")',
            fields='summary,status')
        self.assertEqual(bugs_info, {
            'ENG-1': {
                'description': '',
                'status': 'Open',
                'summary': 'A crash',
            },
            'ENG-2': {
                'description': '',
                'status': 'Fixed',
                'summary': 'A typo',
            },
        })

    def test_get_bugs_info_without_jira_url(self) -> None:
        """Testing JIRA.get_bugs_info without a server URL"""
        config = self.create_bug_tracker(service_name='jira')
        service = self.get_jira_service(config)

        self.assertEqual(
            service.get_bugs_info(config=config, bug_ids=['ENG-1']),
            {})
        self.assertIsNone(service.jira_client)

    def test_get_bugs_info_skips_malformed_ids(self) -> None:
        """Testing JIRA.get_bugs_info leaves IDs that are not issue keys
        out of the JQL query
        """
        config = self.config

        self.spy_on(
            _FakeJIRAClient.search_issues,
            owner=_FakeJIRAClient,
            op=kgb.SpyOpReturn([
                _FakeJIRAIssue('ENG-1', 'A crash', 'Open'),
            ]),
        )

        bugs_info = config.service.get_bugs_info(
            config=config,
            bug_ids=[
                'ENG-1',
                'X") OR project = "HR" OR key in ("Y',
                '#123',
            ])

        self.assertSpyCallCount(_FakeJIRAClient.search_issues, 1)
        self.assertSpyCalledWith(_FakeJIRAClient.search_issues,
                                 'key in ("ENG-1")')
        self.assertEqual(list(bugs_info), ['ENG-1'])

    def test_get_bugs_info_with_only_malformed_ids(self) -> None:
        """Testing JIRA.get_bugs_info with no valid issue keys does not
        contact the server
        """
        config = self.config
        service = self.get_jira_service(config)

        self.assertEqual(
            service.get_bugs_info(config=config,
                                  bug_ids=['#123', 'not a key']),
            {})
        self.assertIsNone(service.jira_client)

    def test_get_bugs_info_with_query_error(self) -> None:
        """Testing JIRA.get_bugs_info falls back to fetching each issue when
        the batch query fails
        """
        config = self.config

        self.spy_on(
            _FakeJIRAClient.search_issues,
            owner=_FakeJIRAClient,
            op=kgb.SpyOpRaise(_FakeJIRAError(
                text="An issue with key 'ENG-404' does not exist.",
                status_code=400,
            )),
        )
        self.spy_on(
            _FakeJIRAClient.issue,
            owner=_FakeJIRAClient,
            op=kgb.SpyOpMatchInOrder([
                {
                    'args': ('ENG-1',),
                    'op': kgb.SpyOpReturn(
                        _FakeJIRAIssue('ENG-1', 'A crash', 'Open')),
                },
                {
                    'args': ('ENG-404',),
                    'call_original': True,
                },
            ]),
        )

        bugs_info = config.service.get_bugs_info(
            config=config,
            bug_ids=['ENG-1', 'ENG-404'])

        # The missing issue is left out, but the other one still loads.
        self.assertEqual(bugs_info, {
            'ENG-1': {
                'description': '',
                'status': 'Open',
                'summary': 'A crash',
            },
        })

    def test_get_bugs_info_with_auth_error(self) -> None:
        """Testing JIRA.get_bugs_info does not fetch each issue when the
        batch query fails with a non-400 error
        """
        config = self.config

        self.spy_on(
            _FakeJIRAClient.search_issues,
            owner=_FakeJIRAClient,
            op=kgb.SpyOpRaise(_FakeJIRAError(
                text='Unauthorized',
                status_code=401,
            )),
        )
        self.spy_on(_FakeJIRAClient.issue,
                    owner=_FakeJIRAClient)

        bugs_info = config.service.get_bugs_info(
            config=config,
            bug_ids=['ENG-1', 'ENG-2'])

        self.assertEqual(bugs_info, {})
        self.assertSpyNotCalled(_FakeJIRAClient.issue)
