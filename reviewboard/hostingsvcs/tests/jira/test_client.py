"""Unit tests for the JIRA API client.

Version Added:
    9.0
"""

from __future__ import annotations

import kgb

from reviewboard.hostingsvcs.base.http import (
    HostingServiceHTTPRequest,
    HostingServiceHTTPResponse,
)
from reviewboard.hostingsvcs.errors import (
    AuthorizationError,
    HostingServiceAPIError,
    HostingServiceError,
)
from reviewboard.hostingsvcs.jira import api
from reviewboard.hostingsvcs.jira.client import JIRAClient
from reviewboard.hostingsvcs.tests.jira.base import JIRATestCase
from reviewboard.scmtools.crypto_utils import encrypt_password


class JIRAClientTests(JIRATestCase):
    """Unit tests for JIRAClient.

    Version Added:
        9.0
    """

    def get_client(
        self,
        hosting_url: str = 'https://jira.example.com',
    ) -> JIRAClient:
        """Return a client for an account with stored credentials.

        Args:
            hosting_url (str, optional):
                The account's server URL.

        Returns:
            reviewboard.hostingsvcs.jira.client.JIRAClient:
            The client.
        """
        account = self.create_hosting_account(data={
            'password': encrypt_password('mytoken'),
        })
        account.hosting_url = hosting_url
        account.save()

        client = account.service.client
        assert isinstance(client, JIRAClient)

        return client

    def test_stored_credentials_on_account_server(self) -> None:
        """Testing JIRAClient sends the stored credentials to the
        account's server
        """
        client = self.get_client()

        with self.setup_http_test(
                payload=self.dump_json(
                    self.make_issue('ENG-1', 'A crash', 'Open')),
                hosting_account=client.hosting_service.account) as ctx:
            client.get_issue(server_url='https://jira.example.com',
                             key='ENG-1',
                             fields='summary')

        ctx.assertHTTPCall(
            0,
            url=self.make_api_url('issue/ENG-1',
                                  fields='summary'),
            username='myuser',
            password='mytoken')

    def test_anonymous_on_other_server(self) -> None:
        """Testing JIRAClient does not send the stored credentials to
        other servers
        """
        client = self.get_client()

        with self.setup_http_test(
                payload=self.dump_json(
                    self.make_issue('ENG-1', 'A crash', 'Open')),
                hosting_account=client.hosting_service.account) as ctx:
            client.get_issue(server_url='https://other.example.com',
                             key='ENG-1',
                             fields='summary')

        ctx.assertHTTPCall(
            0,
            url=self.make_api_url('issue/ENG-1',
                                  server_url='https://other.example.com',
                                  fields='summary'),
            credentials={})

    def test_check_credentials(self) -> None:
        """Testing JIRAClient.check_credentials sends the given credentials"""
        client = self.get_client(hosting_url='')

        with self.setup_http_test(
                payload=b'{}',
                hosting_account=client.hosting_service.account) as ctx:
            client.check_credentials(server_url='https://jira.example.com',
                                     username='newuser',
                                     password='newtoken')

        ctx.assertHTTPCall(
            0,
            url=self.make_api_url('myself'),
            username='newuser',
            password='newtoken')

    def test_search_issues_on_jira_cloud(self) -> None:
        """Testing JIRAClient.search_issues uses search/jql on JIRA Cloud"""
        server_url = 'https://myteam.atlassian.net'
        client = self.get_client(hosting_url=server_url)

        with self.setup_http_test(
                payload=self.make_search_payload([
                    self.make_issue('ENG-1', 'A crash', 'Open'),
                ]),
                hosting_account=client.hosting_service.account) as ctx:
            issues = client.search_issues(server_url=server_url,
                                          jql='key = "ENG-1"',
                                          max_results=5,
                                          fields='summary,status')

        ctx.assertHTTPCall(
            0,
            url=self.make_api_url('search/jql',
                                  server_url=server_url,
                                  fields='summary,status',
                                  jql='key = "ENG-1"',
                                  maxResults='5'),
            username='myuser',
            password='mytoken')

        self.assertEqual([issue.key for issue in issues], ['ENG-1'])

    def test_get_issue_picker_keys(self) -> None:
        """Testing JIRAClient.get_issue_picker_keys returns each key once,
        in order
        """
        client = self.get_client()

        with self.setup_http_test(
                payload=self.dump_json({
                    'sections': [
                        {
                            'id': 'hs',
                            'issues': [
                                {'key': 'ENG-2'},
                            ],
                        },
                        {
                            'id': 'cs',
                            'issues': [
                                {'key': 'ENG-1'},
                                {'key': 'ENG-2'},
                            ],
                        },
                    ],
                }),
                hosting_account=client.hosting_service.account):
            keys = client.get_issue_picker_keys(
                server_url='https://jira.example.com',
                query='eng',
                current_jql='')

        self.assertEqual(keys, ['ENG-2', 'ENG-1'])

    def test_open_http_request_timeout(self) -> None:
        """Testing JIRAClient.open_http_request uses a timeout"""
        client = self.get_client()
        request = HostingServiceHTTPRequest('https://jira.example.com')
        response = HostingServiceHTTPResponse(request=request,
                                              url=request.url,
                                              data=b'{}',
                                              headers={},
                                              status_code=200)

        self.spy_on(HostingServiceHTTPRequest.open,
                    owner=HostingServiceHTTPRequest,
                    op=kgb.SpyOpReturn(response))

        self.assertIs(client.open_http_request(request), response)
        self.assertSpyCalledWith(HostingServiceHTTPRequest.open,
                                 timeout=10)

    def test_read_timeout(self) -> None:
        """Testing JIRAClient with a timeout while reading the response"""
        client = self.get_client()

        self.spy_on(HostingServiceHTTPRequest.open,
                    owner=HostingServiceHTTPRequest,
                    op=kgb.SpyOpRaise(TimeoutError('timed out')))

        with self.assertRaisesMessage(HostingServiceError, 'timed out'):
            client.get_issue(server_url='https://jira.example.com',
                             key='ENG-1',
                             fields='summary')

    def test_http_401(self) -> None:
        """Testing JIRAClient with an HTTP 401 raises AuthorizationError"""
        client = self.get_client()

        with self.setup_http_test(
                status_code=401,
                hosting_account=client.hosting_service.account):
            with self.assertRaises(AuthorizationError) as ctx:
                client.check_credentials(
                    server_url='https://jira.example.com',
                    username='myuser',
                    password='badtoken')

        self.assertEqual(ctx.exception.http_code, 401)

    def test_http_error_with_api_error(self) -> None:
        """Testing JIRAClient with an HTTP error carrying JIRA's error
        payload
        """
        client = self.get_client()

        with self.setup_http_test(
                status_code=400,
                payload=self.dump_json({
                    'errorMessages': ['The query is invalid.'],
                    'errors': {
                        'jql': 'Field "x" does not exist.',
                    },
                }),
                hosting_account=client.hosting_service.account):
            with self.assertRaises(HostingServiceAPIError) as ctx:
                client.search_issues(server_url='https://jira.example.com',
                                     jql='x = 1',
                                     max_results=5,
                                     fields='summary')

        e = ctx.exception
        self.assertEqual(str(e),
                         'The query is invalid. Field "x" does not exist.')
        self.assertEqual(e.http_code, 400)
        self.assertIsInstance(e.rsp, api.APIError)

    def test_http_error_without_api_error(self) -> None:
        """Testing JIRAClient with an HTTP error that isn't JIRA's error
        payload
        """
        client = self.get_client()

        with self.setup_http_test(
                status_code=502,
                payload=b'<html>Bad Gateway</html>',
                hosting_account=client.hosting_service.account):
            with self.assertRaises(HostingServiceAPIError) as ctx:
                client.get_issue(server_url='https://jira.example.com',
                                 key='ENG-1',
                                 fields='summary')

        e = ctx.exception
        self.assertEqual(str(e), 'HTTP Error 502: Unknown error')
        self.assertEqual(e.http_code, 502)
        self.assertIsNone(e.rsp)

    def test_unexpected_response(self) -> None:
        """Testing JIRAClient with a response that doesn't match the
        expected data
        """
        client = self.get_client()

        with self.setup_http_test(
                payload=b'{"not": "an issue"}',
                hosting_account=client.hosting_service.account):
            with self.assertRaisesMessage(HostingServiceError,
                                          'Unexpected response from JIRA.'):
                client.get_issue(server_url='https://jira.example.com',
                                 key='ENG-1',
                                 fields='summary')
