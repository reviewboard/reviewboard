"""Unit tests for the JIRA hosting service.

Version Added:
    9.0:
    Split up ``reviewboard.hostingsvcs.test_jira``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.error import URLError

from reviewboard.hostingsvcs.errors import AuthorizationError
from reviewboard.hostingsvcs.jira.service import JIRA
from reviewboard.hostingsvcs.tests.jira.base import JIRATestCase
from reviewboard.scmtools.crypto_utils import (
    decrypt_password,
    encrypt_password,
)

if TYPE_CHECKING:
    from reviewboard.hostingsvcs.base.client import HostingServiceClient
    from reviewboard.hostingsvcs.base.http import (
        HostingServiceHTTPRequest,
        HostingServiceHTTPResponse,
    )


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
            JIRA.connect_ui.get_bug_tracker_display_path(config),
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
            JIRA.connect_ui.get_bug_tracker_display_path(config),
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
            JIRA.connect_ui.get_bug_tracker_display_path(config),
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

        with self.setup_http_test(payload=b'{}',
                                  hosting_account=account,
                                  expected_http_calls=1) as ctx:
            service.authorize(
                username='myuser',
                password='mytoken',
                hosting_url='https://jira.example.com')

        ctx.assertHTTPCall(
            0,
            url=self.make_api_url('myself'),
            username='myuser',
            password='mytoken')

        account.refresh_from_db()
        self.assertTrue(service.is_authorized())
        self.assertEqual(decrypt_password(account.data['password']),
                         'mytoken')

    def test_authorize_with_invalid_credentials(self) -> None:
        """Testing JIRA.authorize with invalid credentials"""
        account = self.create_hosting_account()
        service = account.service

        with self.setup_http_test(status_code=401,
                                  hosting_account=account):
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

        with self.setup_http_test(status_code=401,
                                  hosting_account=account):
            with self.assertRaisesMessage(
                    AuthorizationError,
                    'JIRA Cloud requires an API token instead of a '
                    'password.'):
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

        with self.setup_http_test(
                status_code=403,
                payload=self.dump_json({
                    'errorMessages': ['CAPTCHA required'],
                }),
                hosting_account=account):
            with self.assertRaisesMessage(
                    AuthorizationError,
                    'Unable to authenticate with JIRA: CAPTCHA required'):
                service.authorize(
                    username='myuser',
                    password='mytoken',
                    hosting_url='https://jira.example.com')

    def test_authorize_with_unreachable_server(self) -> None:
        """Testing JIRA.authorize with an unreachable server"""
        account = self.create_hosting_account()
        service = account.service

        with self.setup_http_test(
                http_request_func=_raise_connection_refused,
                hosting_account=account):
            with self.assertRaisesMessage(
                    AuthorizationError,
                    'Unable to communicate with JIRA: Connection refused'):
                service.authorize(
                    username='myuser',
                    password='mytoken',
                    hosting_url='https://jira.example.com')

        self.assertFalse(service.is_authorized())

    def test_authorize_without_credentials(self) -> None:
        """Testing JIRA.authorize without full credentials"""
        account = self.create_hosting_account()
        service = account.service

        with self.setup_http_test(hosting_account=account,
                                  expected_http_calls=0):
            with self.assertRaisesMessage(AuthorizationError,
                                          'are required'):
                service.authorize(
                    username='myuser',
                    password='',
                    hosting_url='https://jira.example.com')


class JIRACredentialsTests(JIRATestCase):
    """Unit tests for which credentials JIRA lookups send.

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

        with self.setup_http_test(
                payload=self.make_picker_payload([]),
                hosting_account=account) as ctx:
            config.service.search_bugs(config=config, query='crash')

        ctx.assertHTTPCall(
            0,
            url=self.make_api_url('issue/picker',
                                  currentJQL='',
                                  query='crash'),
            username='myuser',
            password='mytoken')

    def test_search_bugs_without_account_is_anonymous(self) -> None:
        """Testing JIRA bug lookups without an account, connecting anonymously
        """
        config = self.create_bug_tracker(
            service_name='jira',
            settings={
                'jira_url': 'https://jira.example.com',
            })

        with self.setup_http_test(
                payload=self.make_picker_payload([])) as ctx:
            config.service.search_bugs(config=config, query='crash')

        ctx.assertHTTPCall(
            0,
            url=self.make_api_url('issue/picker',
                                  currentJQL='',
                                  query='crash'),
            credentials={})

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

        with self.setup_http_test(
                payload=self.dump_json(
                    self.make_issue('ENG-1', 'A crash', 'Open')),
                hosting_account=account) as ctx:
            service.get_bug_info_uncached(repository=repository,
                                          bug_id='ENG-1')

            # The account's own server still gets the credentials.
            service.get_bug_info_uncached(config=config,
                                          bug_id='ENG-1')

        fields = 'summary,status,description'

        ctx.assertHTTPCall(
            0,
            url=self.make_api_url(
                'issue/ENG-1',
                server_url='http://legacy-jira.example.com',
                fields=fields),
            credentials={})
        ctx.assertHTTPCall(
            1,
            url=self.make_api_url('issue/ENG-1',
                                  fields=fields),
            username='myuser',
            password='mytoken')


class JIRABugInfoTests(JIRATestCase):
    """Unit tests for JIRA.get_bug_info_uncached.

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

    def test_get_bug_info(self) -> None:
        """Testing JIRA.get_bug_info_uncached loads only the needed fields"""
        config = self.config

        with self.setup_http_test(
                payload=self.dump_json(self.make_issue(
                    'ENG-1',
                    'A crash',
                    'Open',
                    description='It crashes.')),
                expected_http_calls=1) as ctx:
            bug_info = self.get_jira_service(config).get_bug_info_uncached(
                config=config,
                bug_id='ENG-1')

        ctx.assertHTTPCall(
            0,
            url=self.make_api_url('issue/ENG-1',
                                  fields='summary,status,description'),
            credentials={})
        self.assertEqual(bug_info, {
            'description': 'It crashes.',
            'status': 'Open',
            'summary': 'A crash',
        })

    def test_get_bug_info_escapes_bug_id(self) -> None:
        """Testing JIRA.get_bug_info_uncached escapes the bug ID in the URL"""
        config = self.config

        with self.setup_http_test(
                payload=self.dump_json(
                    self.make_issue('ENG-1', 'A crash', 'Open'))) as ctx:
            self.get_jira_service(config).get_bug_info_uncached(
                config=config,
                bug_id='../myself?x=')

        ctx.assertHTTPCall(
            0,
            url=self.make_api_url('issue/..%2Fmyself%3Fx%3D',
                                  fields='summary,status,description'),
            credentials={})

    def test_get_bug_info_with_unreachable_server(self) -> None:
        """Testing JIRA.get_bug_info_uncached with an unreachable server
        returns empty information
        """
        config = self.config

        with self.setup_http_test(
                http_request_func=_raise_connection_refused):
            bug_info = self.get_jira_service(config).get_bug_info_uncached(
                config=config,
                bug_id='ENG-1')

        self.assertEqual(bug_info, {
            'description': '',
            'status': '',
            'summary': '',
        })

    def test_get_bug_info_with_missing_issue(self) -> None:
        """Testing JIRA.get_bug_info_uncached with an issue that does not
        exist returns empty information
        """
        config = self.config

        with self.setup_http_test(
                status_code=404,
                payload=self.dump_json({
                    'errorMessages': ['Issue does not exist'],
                })):
            bug_info = self.get_jira_service(config).get_bug_info_uncached(
                config=config,
                bug_id='ENG-1')

        self.assertEqual(bug_info, {
            'description': '',
            'status': '',
            'summary': '',
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

    def test_search_bugs_with_empty_query(self) -> None:
        """Testing JIRA.search_bugs with an empty query does not contact
        the server
        """
        config = self.config

        with self.setup_http_test(expected_http_calls=0):
            self.assertEqual(
                config.service.search_bugs(config=config, query='  '),
                [])

    def test_search_bugs(self) -> None:
        """Testing JIRA.search_bugs"""
        config = self.config

        handler = self.make_handler_for_paths({
            '/rest/api/2/issue/picker': {
                'payload': self.make_picker_payload([]),
            },
            '/rest/api/2/search': {
                'payload': self.make_search_payload([
                    self.make_issue('PROJ-42', 'Crash on startup', 'Open'),
                ]),
            },
        })

        with self.setup_http_test(http_request_func=handler,
                                  expected_http_calls=2) as ctx:
            results = config.service.search_bugs(config=config,
                                                 query='crash "quoted"')

        self.assertEqual(results, [
            {
                'bug_id': 'PROJ-42',
                'status': 'Open',
                'summary': 'Crash on startup',
            },
        ])

        # The picker found nothing, so this falls back to JQL. Quotes in the
        # query are escaped in the JQL, and only the summary is searched.
        ctx.assertHTTPCall(
            1,
            url=self.make_api_url(
                'search',
                fields='summary,status',
                jql='summary ~ "crash \\"quoted\\"*"',
                maxResults='25',
                validateQuery='false'),
            credentials={})

    def test_search_bugs_with_picker(self) -> None:
        """Testing JIRA.search_bugs uses the issue picker, promoting an
        exact key match
        """
        config = self.config

        # ENG-100 is left out of the search results, simulating an issue
        # that could not be loaded.
        handler = self.make_handler_for_paths({
            '/rest/api/2/issue/picker': {
                'payload': self.make_picker_payload([
                    'ENG-10',
                    'ENG-1',
                    'ENG-100',
                ]),
            },
            '/rest/api/2/search': {
                'payload': self.make_search_payload([
                    self.make_issue('ENG-10', 'Crash on startup', 'Open'),
                    self.make_issue('ENG-1', 'First bug', 'Open'),
                ]),
            },
        })

        with self.setup_http_test(http_request_func=handler,
                                  expected_http_calls=2) as ctx:
            results = config.service.search_bugs(config=config,
                                                 query='eng-1')

        ctx.assertHTTPCall(
            0,
            url=self.make_api_url('issue/picker',
                                  currentJQL='',
                                  query='eng-1'),
            credentials={})

        # Details are loaded for the picker's keys, with the exact match
        # promoted to the front.
        ctx.assertHTTPCall(
            1,
            url=self.make_api_url(
                'search',
                fields='summary,status',
                jql='key in ("ENG-1", "ENG-10", "ENG-100")',
                maxResults='3',
                validateQuery='false'),
            credentials={})

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

        handler = self.make_handler_for_paths({
            '/rest/api/2/issue/picker': {
                'payload': self.make_picker_payload([
                    'OTHER-5',
                    'ENG-10',
                    'ENG-1',
                ]),
            },
            '/rest/api/2/search': {
                'payload': self.make_search_payload([
                    self.make_issue('ENG-10', 'Crash on startup', 'Open'),
                    self.make_issue('ENG-1', 'First bug', 'Open'),
                ]),
            },
        })

        with self.setup_http_test(http_request_func=handler,
                                  expected_http_calls=2) as ctx:
            results = config.service.search_bugs(config=config,
                                                 query='eng-1')

        # The picker's current search is limited to the project.
        ctx.assertHTTPCall(
            0,
            url=self.make_api_url('issue/picker',
                                  currentJQL='project = "ENG"',
                                  query='eng-1'),
            credentials={})

        # The other project's issue (as from the picker's history section)
        # never reaches the details query.
        ctx.assertHTTPCall(
            1,
            url=self.make_api_url(
                'search',
                fields='summary,status',
                jql='key in ("ENG-1", "ENG-10")',
                maxResults='2',
                validateQuery='false'),
            credentials={})

        self.assertEqual(
            [result['bug_id'] for result in results],
            ['ENG-1', 'ENG-10'])

    def test_search_bugs_with_picker_unavailable(self) -> None:
        """Testing JIRA.search_bugs falls back to JQL when the issue
        picker is unavailable
        """
        config = self.config

        handler = self.make_handler_for_paths({
            '/rest/api/2/issue/picker': {
                'status_code': 404,
            },
            '/rest/api/2/search': {
                'payload': self.make_search_payload([
                    self.make_issue('ENG-102', 'Crash on startup', 'Open'),
                ]),
            },
        })

        with self.setup_http_test(http_request_func=handler,
                                  expected_http_calls=3) as ctx:
            results = config.service.search_bugs(config=config,
                                                 query='eng-102')

        # The exact key is tried first, then summaries. The duplicate
        # result is dropped.
        ctx.assertHTTPCall(
            1,
            url=self.make_api_url(
                'search',
                fields='summary,status',
                jql='key = "ENG-102"',
                maxResults='25',
                validateQuery='false'),
            credentials={})
        ctx.assertHTTPCall(
            2,
            url=self.make_api_url(
                'search',
                fields='summary,status',
                jql='summary ~ "eng-102*"',
                maxResults='24',
                validateQuery='false'),
            credentials={})

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

        with self.setup_http_test(
                payload=self.make_search_payload([
                    self.make_issue('ENG-1', 'A crash', 'Open'),
                    self.make_issue('ENG-2', 'A typo', 'Fixed'),
                ]),
                expected_http_calls=1) as ctx:
            bugs_info = config.service.get_bugs_info(
                config=config,
                bug_ids=['ENG-1', 'ENG-2'])

        ctx.assertHTTPCall(
            0,
            url=self.make_api_url(
                'search',
                fields='summary,status',
                jql='key in ("ENG-1", "ENG-2")',
                maxResults='2',
                validateQuery='false'),
            credentials={})
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

        with self.setup_http_test(expected_http_calls=0):
            self.assertEqual(
                config.service.get_bugs_info(config=config,
                                             bug_ids=['ENG-1']),
                {})

    def test_get_bugs_info_skips_malformed_ids(self) -> None:
        """Testing JIRA.get_bugs_info leaves IDs that are not issue keys
        out of the JQL query
        """
        config = self.config

        with self.setup_http_test(
                payload=self.make_search_payload([
                    self.make_issue('ENG-1', 'A crash', 'Open'),
                ]),
                expected_http_calls=1) as ctx:
            bugs_info = config.service.get_bugs_info(
                config=config,
                bug_ids=[
                    'ENG-1',
                    'X") OR project = "HR" OR key in ("Y',
                    '#123',
                ])

        ctx.assertHTTPCall(
            0,
            url=self.make_api_url(
                'search',
                fields='summary,status',
                jql='key in ("ENG-1")',
                maxResults='1',
                validateQuery='false'),
            credentials={})
        self.assertEqual(list(bugs_info), ['ENG-1'])

    def test_get_bugs_info_with_only_malformed_ids(self) -> None:
        """Testing JIRA.get_bugs_info with no valid issue keys does not
        contact the server
        """
        config = self.config

        with self.setup_http_test(expected_http_calls=0):
            self.assertEqual(
                config.service.get_bugs_info(config=config,
                                             bug_ids=['#123', 'not a key']),
                {})

    def test_get_bugs_info_with_query_error(self) -> None:
        """Testing JIRA.get_bugs_info falls back to fetching each issue when
        the batch query fails
        """
        config = self.config

        handler = self.make_handler_for_paths({
            '/rest/api/2/search': {
                'status_code': 400,
                'payload': self.dump_json({
                    'errorMessages': [
                        "An issue with key 'ENG-404' does not exist.",
                    ],
                }),
            },
            '/rest/api/2/issue/ENG-1': {
                'payload': self.dump_json(
                    self.make_issue('ENG-1', 'A crash', 'Open')),
            },
            '/rest/api/2/issue/ENG-404': {
                'status_code': 404,
            },
        })

        with self.setup_http_test(http_request_func=handler,
                                  expected_http_calls=3):
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

        with self.setup_http_test(status_code=401,
                                  expected_http_calls=1):
            bugs_info = config.service.get_bugs_info(
                config=config,
                bug_ids=['ENG-1', 'ENG-2'])

        self.assertEqual(bugs_info, {})


def _raise_connection_refused(
    client: HostingServiceClient,
    request: HostingServiceHTTPRequest,
) -> HostingServiceHTTPResponse:
    """Raise an error for a server that can't be reached.

    This is used as the HTTP handler for tests.

    Version Added:
        9.0

    Args:
        client (reviewboard.hostingsvcs.base.client.HostingServiceClient):
            The client performing the request.

        request (reviewboard.hostingsvcs.base.http.HostingServiceHTTPRequest):
            The request.

    Raises:
        urllib.error.URLError:
            The error for the unreachable server.
    """
    raise URLError('Connection refused')
