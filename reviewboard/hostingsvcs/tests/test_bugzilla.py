"""Unit tests for the Bugzilla hosting service."""

from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.error import URLError
from urllib.parse import parse_qs, urlparse

from djblets.conditions import ConditionSet

from reviewboard.hostingsvcs.bug_tracker_forms import BugTrackerForm
from reviewboard.hostingsvcs.bugzilla import Bugzilla, BugzillaAuthForm
from reviewboard.hostingsvcs.errors import AuthorizationError
from reviewboard.hostingsvcs.models import ConfiguredBugTracker
from reviewboard.hostingsvcs.testing import HostingServiceTestCase
from reviewboard.scmtools.crypto_utils import (
    decrypt_password,
    encrypt_password,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from reviewboard.hostingsvcs.base.client import HostingServiceClient
    from reviewboard.hostingsvcs.base.http import (
        HostingServiceHTTPRequest,
        HostingServiceHTTPResponse,
    )


def _record_requests(
    handler: Callable[[HostingServiceClient, HostingServiceHTTPRequest],
                      HostingServiceHTTPResponse],
    requests: list[HostingServiceHTTPRequest],
) -> Callable[[HostingServiceClient, HostingServiceHTTPRequest],
              HostingServiceHTTPResponse]:
    """Return an HTTP handler that records each request.

    Args:
        handler (callable):
            The handler to pass requests on to.

        requests (list):
            The list to append each request to.

    Returns:
        callable:
        The recording handler.
    """
    def _handler(
        client: HostingServiceClient,
        request: HostingServiceHTTPRequest,
    ) -> HostingServiceHTTPResponse:
        requests.append(request)

        return handler(client, request)

    return _handler


def _get_query(
    request: HostingServiceHTTPRequest,
) -> dict[str, list[str]]:
    """Return the parsed query string of a request.

    Args:
        request (HostingServiceHTTPRequest):
            The request.

    Returns:
        dict:
        The parsed query string.
    """
    return parse_qs(urlparse(request.url).query)


class BugzillaTests(HostingServiceTestCase[Bugzilla]):
    """Unit tests for the Bugzilla hosting service."""

    service_name = 'bugzilla'
    fixtures = ['test_scmtools']

    def test_service_support(self) -> None:
        """Testing Bugzilla service support capabilities"""
        self.assertTrue(self.service_class.supports_bug_trackers)
        self.assertFalse(self.service_class.supports_repositories)

    def test_bug_tracker_field(self) -> None:
        """Testing Bugzilla.get_bug_tracker_field"""
        self.assertFalse(
            self.service_class.get_bug_tracker_requires_username())
        self.assertEqual(
            self.service_class.get_bug_tracker_field(None, {
                'bugzilla_url': 'http://bugzilla.example.com',
            }),
            'http://bugzilla.example.com/show_bug.cgi?id=%s')

    def test_search_bugs(self) -> None:
        """Testing Bugzilla.search_bugs"""
        config = ConfiguredBugTracker.objects.create(
            name='Bugzilla',
            service_name='bugzilla',
            settings={
                'bugzilla_url': 'https://bugzilla.example.com',
            })

        payload = self.dump_json({
            'bugs': [
                {
                    'id': 1234,
                    'is_open': True,
                    'status': 'NEW',
                    'summary': 'Crash on startup',
                },
                {
                    'id': 1000,
                    'is_open': False,
                    'status': 'RESOLVED',
                    'summary': 'Old crash',
                },
            ],
        })

        requests: list[HostingServiceHTTPRequest] = []
        handler = _record_requests(
            self.make_handler_for_paths({
                '/rest/bug': {
                    'payload': payload,
                    'headers': {'Content-Type': 'application/json'},
                },
            }),
            requests)

        with self.setup_http_test(http_request_func=handler,
                                  expected_http_calls=1):
            results = config.service.search_bugs(config=config,
                                                 query='crash')

        self.assertEqual(results, [
            {
                'bug_id': '1234',
                'closed': False,
                'status': 'NEW',
                'summary': 'Crash on startup',
            },
            {
                'bug_id': '1000',
                'closed': True,
                'status': 'RESOLVED',
                'summary': 'Old crash',
            },
        ])

        query = _get_query(requests[0])

        # Closed bugs are searched too.
        self.assertEqual(query['quicksearch'], ['ALL crash'])
        self.assertEqual(query['limit'], ['25'])

    def test_search_bugs_with_bug_id(self) -> None:
        """Testing Bugzilla.search_bugs with a bug number"""
        config = ConfiguredBugTracker.objects.create(
            name='Bugzilla',
            service_name='bugzilla',
            settings={
                'bugzilla_url': 'https://bugzilla.example.com',
            })

        requests: list[HostingServiceHTTPRequest] = []
        handler = _record_requests(
            self.make_handler_for_paths({
                '/rest/bug': {
                    'payload': self.dump_json({
                        'bugs': [],
                    }),
                    'headers': {'Content-Type': 'application/json'},
                },
            }),
            requests)

        with self.setup_http_test(http_request_func=handler,
                                  expected_http_calls=1):
            config.service.search_bugs(config=config, query=' 1000 ')

        # A bare number finds that bug whether it's open or closed. "ALL"
        # would turn it into a text search.
        self.assertEqual(_get_query(requests[0])['quicksearch'], ['1000'])

    def test_search_bugs_with_empty_query(self) -> None:
        """Testing Bugzilla.search_bugs with an empty query"""
        config = ConfiguredBugTracker.objects.create(
            name='Bugzilla',
            service_name='bugzilla',
            settings={
                'bugzilla_url': 'https://bugzilla.example.com',
            })

        # "ALL" on its own would list every bug, so nothing is requested.
        with self.setup_http_test(expected_http_calls=0):
            self.assertEqual(
                config.service.search_bugs(config=config, query='  '),
                [])

    def test_search_bugs_with_error(self) -> None:
        """Testing Bugzilla.search_bugs with an HTTP error"""
        config = ConfiguredBugTracker.objects.create(
            name='Bugzilla',
            service_name='bugzilla',
            settings={
                'bugzilla_url': 'https://bugzilla.example.com',
            })

        handler = self.make_handler_for_paths({
            '/rest/bug': {
                'status_code': 500,
                'payload': b'error',
            },
        })

        with self.setup_http_test(http_request_func=handler,
                                  expected_http_calls=1):
            results = config.service.search_bugs(config=config,
                                                 query='crash')

        self.assertEqual(results, [])

    def test_search_bugs_without_url(self) -> None:
        """Testing Bugzilla.search_bugs without any Bugzilla URL"""
        config = ConfiguredBugTracker.objects.create(
            name='Bugzilla',
            service_name='bugzilla',
            settings={})

        with self.setup_http_test(expected_http_calls=0):
            self.assertEqual(
                config.service.search_bugs(config=config, query='crash'),
                [])

    def test_get_bugs_info(self) -> None:
        """Testing Bugzilla.get_bugs_info"""
        config = ConfiguredBugTracker.objects.create(
            name='Bugzilla',
            service_name='bugzilla',
            settings={
                'bugzilla_url': 'https://bugzilla.example.com',
            })

        payload = self.dump_json({
            'bugs': [
                {
                    'alias': [],
                    'id': 1234,
                    'status': 'NEW',
                    'summary': 'Crash on startup',
                },
                {
                    'alias': ['old-crash'],
                    'id': 1000,
                    'status': 'RESOLVED',
                    'summary': 'Old crash',
                },
            ],
            'faults': [
                {
                    'error': True,
                    'faultCode': 101,
                    'id': 9999,
                },
            ],
        })

        requests: list[HostingServiceHTTPRequest] = []
        handler = _record_requests(
            self.make_handler_for_paths({
                '/rest/bug': {
                    'payload': payload,
                    'headers': {'Content-Type': 'application/json'},
                },
            }),
            requests)

        with self.setup_http_test(http_request_func=handler,
                                  expected_http_calls=1):
            results = config.service.get_bugs_info(
                config=config,
                bug_ids=['1234', 'old-crash', '9999'])

        # The bug requested by alias is keyed by that alias, and the
        # missing bug is left out.
        self.assertEqual(results, {
            '1234': {
                'description': '',
                'status': 'NEW',
                'summary': 'Crash on startup',
            },
            'old-crash': {
                'description': '',
                'status': 'RESOLVED',
                'summary': 'Old crash',
            },
        })

        query = _get_query(requests[0])
        self.assertEqual(query['id'], ['1234,old-crash,9999'])
        self.assertEqual(query['permissive'], ['1'])

    def test_get_bugs_info_without_bug_ids(self) -> None:
        """Testing Bugzilla.get_bugs_info without any bug IDs"""
        config = ConfiguredBugTracker.objects.create(
            name='Bugzilla',
            service_name='bugzilla',
            settings={
                'bugzilla_url': 'https://bugzilla.example.com',
            })

        with self.setup_http_test(expected_http_calls=0):
            self.assertEqual(
                config.service.get_bugs_info(config=config, bug_ids=[]),
                {})

    def test_get_bugs_info_with_error(self) -> None:
        """Testing Bugzilla.get_bugs_info with an HTTP error"""
        config = ConfiguredBugTracker.objects.create(
            name='Bugzilla',
            service_name='bugzilla',
            settings={
                'bugzilla_url': 'https://bugzilla.example.com',
            })

        handler = self.make_handler_for_paths({
            '/rest/bug': {
                'status_code': 500,
                'payload': b'error',
            },
        })

        with self.setup_http_test(http_request_func=handler,
                                  expected_http_calls=1):
            results = config.service.get_bugs_info(config=config,
                                                   bug_ids=['1234'])

        self.assertEqual(results, {})

    def test_get_bugs_info_without_url(self) -> None:
        """Testing Bugzilla.get_bugs_info without any Bugzilla URL"""
        config = ConfiguredBugTracker.objects.create(
            name='Bugzilla',
            service_name='bugzilla',
            settings={})

        with self.setup_http_test(expected_http_calls=0):
            self.assertEqual(
                config.service.get_bugs_info(config=config,
                                             bug_ids=['1234']),
                {})


class BugzillaAuthFormTests(HostingServiceTestCase[Bugzilla]):
    """Unit tests for BugzillaAuthForm.

    Version Added:
        9.0
    """

    service_name = 'bugzilla'

    def test_get_hosting_url(self) -> None:
        """Testing BugzillaAuthForm.get_hosting_url returns the Bugzilla
        URL
        """
        form = BugzillaAuthForm(
            data={
                'bugzilla_url': 'https://bugzilla.example.com/',
                'hosting_account_password': 'my-api-key',
                'hosting_account_username': 'me@example.com',
            },
            hosting_service_cls=Bugzilla)

        self.assertTrue(form.is_valid(), form.errors)

        # Trailing slashes are stripped.
        self.assertEqual(form.get_hosting_url(),
                         'https://bugzilla.example.com')

    def test_save_with_same_login_on_two_servers(self) -> None:
        """Testing BugzillaAuthForm.save with the same login on two servers
        creates two accounts
        """
        handler = self.make_handler_for_paths({
            '/rest/valid_login': {
                'payload': self.dump_json({
                    'result': True,
                }),
                'headers': {'Content-Type': 'application/json'},
            },
        })

        accounts = []

        with self.setup_http_test(http_request_func=handler,
                                  expected_http_calls=2):
            for bugzilla_url in ('https://one.example.com',
                                 'https://two.example.com'):
                form = BugzillaAuthForm(
                    data={
                        'bugzilla_url': bugzilla_url,
                        'hosting_account_password': 'my-api-key',
                        'hosting_account_username': 'me@example.com',
                    },
                    hosting_service_cls=Bugzilla)

                self.assertTrue(form.is_valid(), form.errors)
                accounts.append(form.save())

        self.assertNotEqual(accounts[0].pk, accounts[1].pk)

        for account in accounts:
            account.refresh_from_db()

        self.assertEqual(accounts[0].hosting_url, 'https://one.example.com')
        self.assertEqual(accounts[1].hosting_url, 'https://two.example.com')

    def test_requires_bugzilla_url(self) -> None:
        """Testing BugzillaAuthForm requires the Bugzilla URL"""
        form = BugzillaAuthForm(
            data={
                'hosting_account_password': 'my-api-key',
                'hosting_account_username': 'me@example.com',
            },
            hosting_service_cls=Bugzilla)

        self.assertFalse(form.is_valid())
        self.assertIn('bugzilla_url', form.errors)

    def test_load(self) -> None:
        """Testing BugzillaAuthForm.load fills in the account's Bugzilla
        URL
        """
        account = self.create_hosting_account()
        account.hosting_url = 'https://bugzilla.example.com'
        account.save()

        form = BugzillaAuthForm(hosting_service_cls=Bugzilla,
                                hosting_account=account)
        form.load()

        self.assertEqual(form.fields['bugzilla_url'].initial,
                         'https://bugzilla.example.com')


class BugzillaAuthorizeTests(HostingServiceTestCase[Bugzilla]):
    """Unit tests for Bugzilla.authorize.

    Version Added:
        9.0
    """

    service_name = 'bugzilla'

    def test_authorize(self) -> None:
        """Testing Bugzilla.authorize stores verified credentials"""
        account = self.create_hosting_account()
        service = account.service

        requests: list[HostingServiceHTTPRequest] = []
        handler = _record_requests(
            self.make_handler_for_paths({
                '/rest/valid_login': {
                    'payload': self.dump_json({
                        'result': True,
                    }),
                    'headers': {'Content-Type': 'application/json'},
                },
            }),
            requests)

        with self.setup_http_test(http_request_func=handler,
                                  expected_http_calls=1):
            service.authorize(
                username='me@example.com',
                password='my-api-key',
                hosting_url='https://bugzilla.example.com')

        request = requests[0]
        self.assertTrue(request.url.startswith(
            'https://bugzilla.example.com/rest/valid_login?'))
        self.assertEqual(_get_query(request), {
            'api_key': ['my-api-key'],
            'login': ['me@example.com'],
        })

        # The API key is never sent as HTTP Basic Auth.
        self.assertIsNone(request.get_header('Authorization'))

        account.refresh_from_db()
        self.assertTrue(service.is_authorized())
        self.assertEqual(decrypt_password(account.data['password']),
                         'my-api-key')

    def test_authorize_with_invalid_api_key(self) -> None:
        """Testing Bugzilla.authorize with an API key Bugzilla rejects"""
        account = self.create_hosting_account()
        service = account.service

        handler = self.make_handler_for_paths({
            '/rest/valid_login': {
                'status_code': 400,
                'payload': self.dump_json({
                    'code': 306,
                    'error': True,
                    'message': 'The API key you specified is invalid.',
                }),
            },
        })

        with self.setup_http_test(http_request_func=handler,
                                  expected_http_calls=1), \
             self.assertRaisesMessage(
                 AuthorizationError,
                 'Bugzilla rejected the login or API key: The API key you '
                 'specified is invalid.'):
            service.authorize(
                username='me@example.com',
                password='bad-key',
                hosting_url='https://bugzilla.example.com')

        self.assertFalse(service.is_authorized())

    def test_authorize_with_other_login(self) -> None:
        """Testing Bugzilla.authorize with an API key that belongs to a
        different login
        """
        account = self.create_hosting_account()
        service = account.service

        # Bugzilla reports a valid key for another user as a false result,
        # not an error.
        handler = self.make_handler_for_paths({
            '/rest/valid_login': {
                'payload': self.dump_json({
                    'result': False,
                }),
                'headers': {'Content-Type': 'application/json'},
            },
        })

        with self.setup_http_test(http_request_func=handler,
                                  expected_http_calls=1), \
             self.assertRaisesMessage(
                 AuthorizationError,
                 'This API key does not belong to the login '
                 'me@example.com.'):
            service.authorize(
                username='me@example.com',
                password='my-api-key',
                hosting_url='https://bugzilla.example.com')

        self.assertFalse(service.is_authorized())

    def test_authorize_without_credentials(self) -> None:
        """Testing Bugzilla.authorize without full credentials"""
        account = self.create_hosting_account()
        service = account.service

        with self.setup_http_test(expected_http_calls=0), \
             self.assertRaisesMessage(AuthorizationError,
                                      'are required'):
            service.authorize(
                username='me@example.com',
                password='',
                hosting_url='https://bugzilla.example.com')

    def test_authorize_with_network_error(self) -> None:
        """Testing Bugzilla.authorize when Bugzilla can't be reached"""
        account = self.create_hosting_account()
        service = account.service

        def handler(
            client: HostingServiceClient,
            request: HostingServiceHTTPRequest,
        ) -> HostingServiceHTTPResponse:
            raise URLError('Connection refused')

        with self.setup_http_test(http_request_func=handler,
                                  expected_http_calls=1), \
             self.assertRaisesMessage(
                 AuthorizationError,
                 'Unable to communicate with Bugzilla: <urlopen error '
                 'Connection refused>'):
            service.authorize(
                username='me@example.com',
                password='my-api-key',
                hosting_url='https://bugzilla.example.com')

        self.assertFalse(service.is_authorized())


class BugzillaAccountTests(HostingServiceTestCase[Bugzilla]):
    """Unit tests for Bugzilla configurations with linked accounts."""

    service_name = 'bugzilla'

    def test_config_requires_url_or_account(self) -> None:
        """Testing Bugzilla configurations require a Bugzilla URL or an
        account
        """
        form = BugTrackerForm(
            data={
                'apply_to': ConfiguredBugTracker.APPLY_TO_ALL,
                'enabled': True,
                'name': 'My Tracker',
                'service_name': 'bugzilla',
                'user_conditions_last_id': '0',
                'user_conditions_mode': ConditionSet.MODE_ALL,
            })

        self.assertFalse(form.is_valid())
        self.assertIn('hosting_account', form.errors)

    def test_config_with_url_and_no_account(self) -> None:
        """Testing Bugzilla configurations save with a Bugzilla URL and no
        account
        """
        form = BugTrackerForm(
            data={
                'apply_to': ConfiguredBugTracker.APPLY_TO_ALL,
                'bugzilla_url': 'https://bugzilla.example.com/',
                'enabled': True,
                'name': 'My Tracker',
                'service_name': 'bugzilla',
                'user_conditions_last_id': '0',
                'user_conditions_mode': ConditionSet.MODE_ALL,
            })

        self.assertTrue(form.is_valid(), form.errors)

        bug_tracker = form.save()
        self.assertIsNone(bug_tracker.hosting_account)
        self.assertEqual(bug_tracker.settings['bugzilla_url'],
                         'https://bugzilla.example.com')

    def test_config_with_account(self) -> None:
        """Testing Bugzilla configurations save with an account and no
        Bugzilla URL
        """
        account = self.create_hosting_account(data={
            'password': encrypt_password('my-api-key'),
        })
        account.hosting_url = 'https://bugzilla.example.com'
        account.save()

        form = BugTrackerForm(
            data={
                'apply_to': ConfiguredBugTracker.APPLY_TO_ALL,
                'enabled': True,
                'hosting_account': account.pk,
                'name': 'My Tracker',
                'service_name': 'bugzilla',
                'user_conditions_last_id': '0',
                'user_conditions_mode': ConditionSet.MODE_ALL,
            })

        self.assertTrue(form.is_valid(), form.errors)

        bug_tracker = form.save()
        self.assertEqual(bug_tracker.hosting_account, account)

    def test_get_bug_url_with_settings_url(self) -> None:
        """Testing Bugzilla.get_bug_url with the configuration's URL"""
        config = ConfiguredBugTracker.objects.create(
            name='Bugzilla',
            service_name='bugzilla',
            settings={
                'bugzilla_url': 'https://bugzilla.example.com',
            })

        self.assertEqual(
            config.service.get_bug_url(config=config, bug_id='123'),
            'https://bugzilla.example.com/show_bug.cgi?id=123')

    def test_get_bug_url_with_account_url(self) -> None:
        """Testing Bugzilla.get_bug_url prefers the account's URL"""
        account = self.create_hosting_account()
        account.hosting_url = 'https://private.example.com'
        account.save()

        config = ConfiguredBugTracker.objects.create(
            name='Bugzilla',
            service_name='bugzilla',
            hosting_account=account,
            settings={
                'bugzilla_url': 'https://bugzilla.example.com',
            })

        self.assertEqual(
            config.service.get_bug_url(config=config, bug_id='123'),
            'https://private.example.com/show_bug.cgi?id=123')

    def test_get_bug_url_without_url(self) -> None:
        """Testing Bugzilla.get_bug_url without any Bugzilla URL"""
        config = ConfiguredBugTracker.objects.create(
            name='Bugzilla',
            service_name='bugzilla',
            settings={})

        self.assertIsNone(config.service.get_bug_url(config=config,
                                                     bug_id='123'))

    def test_get_bug_tracker_display_path(self) -> None:
        """Testing BugzillaConnectUI.get_bug_tracker_display_path with the
        configuration's URL
        """
        config = ConfiguredBugTracker.objects.create(
            name='Bugzilla',
            service_name='bugzilla',
            settings={
                'bugzilla_url': 'https://bugzilla.example.com',
            })

        self.assertEqual(
            Bugzilla.connect_ui.get_bug_tracker_display_path(config),
            'https://bugzilla.example.com')

    def test_get_bug_tracker_display_path_with_account(self) -> None:
        """Testing BugzillaConnectUI.get_bug_tracker_display_path shows the
        account's URL
        """
        account = self.create_hosting_account()
        account.hosting_url = 'https://private.example.com'
        account.save()

        # The account's server is the one actually used, so it's the one
        # shown.
        config = ConfiguredBugTracker.objects.create(
            name='Bugzilla',
            service_name='bugzilla',
            hosting_account=account,
            settings={
                'bugzilla_url': 'https://bugzilla.example.com',
            })

        self.assertEqual(
            Bugzilla.connect_ui.get_bug_tracker_display_path(config),
            'https://private.example.com')

    def test_get_bug_tracker_display_path_without_url(self) -> None:
        """Testing BugzillaConnectUI.get_bug_tracker_display_path without
        any Bugzilla URL
        """
        config = ConfiguredBugTracker.objects.create(
            name='Bugzilla',
            service_name='bugzilla',
            settings={})

        self.assertEqual(
            Bugzilla.connect_ui.get_bug_tracker_display_path(config),
            '')

    def test_search_bugs_with_account(self) -> None:
        """Testing Bugzilla.search_bugs sends the account's API key to the
        account's server
        """
        account = self.create_hosting_account(data={
            'password': encrypt_password('my-api-key'),
        })
        account.hosting_url = 'https://private.example.com'
        account.save()

        # The configuration's URL is ignored when an account is linked,
        # so the key can't be sent to a different server.
        config = ConfiguredBugTracker.objects.create(
            name='Bugzilla',
            service_name='bugzilla',
            hosting_account=account,
            settings={
                'bugzilla_url': 'https://bugzilla.example.com',
            })

        requests: list[HostingServiceHTTPRequest] = []
        handler = _record_requests(
            self.make_handler_for_paths({
                '/rest/bug': {
                    'payload': self.dump_json({
                        'bugs': [],
                    }),
                    'headers': {'Content-Type': 'application/json'},
                },
            }),
            requests)

        with self.setup_http_test(http_request_func=handler,
                                  expected_http_calls=1):
            config.service.search_bugs(config=config, query='crash')

        request = requests[0]
        self.assertTrue(request.url.startswith(
            'https://private.example.com/rest/bug?'))
        self.assertEqual(_get_query(request)['api_key'], ['my-api-key'])
        self.assertIsNone(request.get_header('Authorization'))

    def test_get_bugs_info_without_account(self) -> None:
        """Testing Bugzilla.get_bugs_info without an account is anonymous"""
        config = ConfiguredBugTracker.objects.create(
            name='Bugzilla',
            service_name='bugzilla',
            settings={
                'bugzilla_url': 'https://bugzilla.example.com',
            })

        requests: list[HostingServiceHTTPRequest] = []
        handler = _record_requests(
            self.make_handler_for_paths({
                '/rest/bug': {
                    'payload': self.dump_json({
                        'bugs': [],
                    }),
                    'headers': {'Content-Type': 'application/json'},
                },
            }),
            requests)

        with self.setup_http_test(http_request_func=handler,
                                  expected_http_calls=1):
            config.service.get_bugs_info(config=config, bug_ids=['123'])

        self.assertNotIn('api_key', _get_query(requests[0]))

    def test_get_bug_info_with_alias(self) -> None:
        """Testing Bugzilla.get_bug_info with a bug alias"""
        config = ConfiguredBugTracker.objects.create(
            name='Bugzilla',
            service_name='bugzilla',
            settings={
                'bugzilla_url': 'https://bugzilla.example.com',
            })

        # Bugzilla keys comments by the numeric ID, even when the bug is
        # requested by alias.
        handler = self.make_handler_for_paths({
            '/rest/bug/startup-crash': {
                'payload': self.dump_json({
                    'bugs': [{
                        'status': 'NEW',
                        'summary': 'Crash on startup',
                    }],
                }),
                'headers': {'Content-Type': 'application/json'},
            },
            '/rest/bug/startup-crash/comment': {
                'payload': self.dump_json({
                    'bugs': {
                        '1234': {
                            'comments': [{'text': 'It crashes.'}],
                        },
                    },
                }),
                'headers': {'Content-Type': 'application/json'},
            },
        })

        with self.setup_http_test(http_request_func=handler,
                                  expected_http_calls=2):
            bug_info = config.service.get_bug_info_uncached(
                config=config,
                bug_id='startup-crash')

        self.assertEqual(bug_info, {
            'description': 'It crashes.',
            'status': 'NEW',
            'summary': 'Crash on startup',
        })

    def test_get_bug_info_with_account(self) -> None:
        """Testing Bugzilla.get_bug_info sends the account's API key with
        both requests
        """
        account = self.create_hosting_account(data={
            'password': encrypt_password('my-api-key'),
        })
        account.hosting_url = 'https://private.example.com'
        account.save()

        config = ConfiguredBugTracker.objects.create(
            name='Bugzilla',
            service_name='bugzilla',
            hosting_account=account,
            settings={})

        requests: list[HostingServiceHTTPRequest] = []
        handler = _record_requests(
            self.make_handler_for_paths({
                '/rest/bug/123': {
                    'payload': self.dump_json({
                        'bugs': [{
                            'status': 'NEW',
                            'summary': 'Private crash',
                        }],
                    }),
                    'headers': {'Content-Type': 'application/json'},
                },
                '/rest/bug/123/comment': {
                    'payload': self.dump_json({
                        'bugs': {
                            '123': {
                                'comments': [{'text': 'It crashes.'}],
                            },
                        },
                    }),
                    'headers': {'Content-Type': 'application/json'},
                },
            }),
            requests)

        with self.setup_http_test(http_request_func=handler,
                                  expected_http_calls=2):
            bug_info = config.service.get_bug_info_uncached(config=config,
                                                            bug_id='123')

        self.assertEqual(bug_info, {
            'description': 'It crashes.',
            'status': 'NEW',
            'summary': 'Private crash',
        })

        for request in requests:
            self.assertEqual(_get_query(request)['api_key'], ['my-api-key'])

    def test_get_bug_info_escapes_bug_id(self) -> None:
        """Testing Bugzilla.get_bug_info escapes the bug ID in the URL"""
        account = self.create_hosting_account(data={
            'password': encrypt_password('my-api-key'),
        })
        account.hosting_url = 'https://bugzilla.example.com'
        account.save()

        config = ConfiguredBugTracker.objects.create(
            name='Bugzilla',
            service_name='bugzilla',
            hosting_account=account,
            settings={})

        requests: list[HostingServiceHTTPRequest] = []
        handler = _record_requests(
            self.make_handler_for_paths({
                '/rest/bug/1%3Fid%3D2%23x': {
                    'payload': self.dump_json({
                        'bugs': [{
                            'status': 'NEW',
                            'summary': 'Crash on startup',
                        }],
                    }),
                    'headers': {'Content-Type': 'application/json'},
                },
                '/rest/bug/1%3Fid%3D2%23x/comment': {
                    'payload': self.dump_json({
                        'bugs': {
                            '1234': {
                                'comments': [{'text': 'It crashes.'}],
                            },
                        },
                    }),
                    'headers': {'Content-Type': 'application/json'},
                },
            }),
            requests)

        with self.setup_http_test(http_request_func=handler,
                                  expected_http_calls=2):
            bug_info = config.service.get_bug_info_uncached(
                config=config,
                bug_id='1?id=2#x')

        self.assertEqual(bug_info, {
            'description': 'It crashes.',
            'status': 'NEW',
            'summary': 'Crash on startup',
        })

        # The bug ID stays in the path, so it can't change the query string or
        # drop the API key.
        for request in requests:
            query = _get_query(request)
            self.assertNotIn('id', query)
            self.assertEqual(query['api_key'], ['my-api-key'])
