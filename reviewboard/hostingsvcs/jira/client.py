"""API client for JIRA.

Version Added:
    9.0
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, TypeVar
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse

from django.utils.translation import gettext
from pydantic import BaseModel, ValidationError

from reviewboard.hostingsvcs.base.client import HostingServiceClient
from reviewboard.hostingsvcs.errors import (
    AuthorizationError,
    HostingServiceAPIError,
    HostingServiceError,
)
from reviewboard.hostingsvcs.jira import api

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from reviewboard.hostingsvcs.base.hosting_service import (
        HostingServiceCredentials,
    )
    from reviewboard.hostingsvcs.base.http import (
        HostingServiceHTTPRequest,
        HostingServiceHTTPResponse,
    )
    from reviewboard.hostingsvcs.jira.service import JIRA  # noqa: F401
    from reviewboard.hostingsvcs.models import HostingServiceAccount


logger = logging.getLogger(__name__)


_TModel = TypeVar('_TModel', bound=BaseModel)


#: The Atlassian Cloud domain suffix for JIRA Cloud sites.
#:
#: Version Added:
#:     9.0
ATLASSIAN_CLOUD_DOMAIN = '.atlassian.net'


#: The timeout for requests to the JIRA server, in seconds.
#:
#: This keeps a slow or unresponsive server from tying up a web worker.
#:
#: Version Added:
#:     9.0
_REQUEST_TIMEOUT_SECS = 10


def get_jira_cloud_site(
    url: str | None,
) -> str | None:
    """Return the Atlassian site name for a JIRA Cloud URL.

    Version Added:
        9.0

    Args:
        url (str):
            The JIRA server URL.

    Returns:
        str:
        The site name (the "yourteam" in yourteam.atlassian.net), or
        ``None`` if the URL is not for a JIRA Cloud site.
    """
    hostname = urlparse(url or '').hostname or ''

    if hostname.endswith(ATLASSIAN_CLOUD_DOMAIN):
        return hostname.removesuffix(ATLASSIAN_CLOUD_DOMAIN)

    return None


class JIRAClient(HostingServiceClient['JIRA']):
    """API client for JIRA.

    This talks to the JIRA REST API (version 2), which JIRA Cloud and JIRA
    Data Center both offer.

    Each call takes the URL of the JIRA server to talk to. The account's
    stored credentials are only sent to the server name on the account. Any
    other server (such as a legacy URL stored on a repository) is contacted
    anonymously.

    Version Added:
        9.0
    """

    def check_credentials(
        self,
        *,
        server_url: str,
        username: str,
        password: str,
    ) -> None:
        """Check that credentials are accepted by a JIRA server.

        Args:
            server_url (str):
                The root URL of the JIRA server.

            username (str):
                The username or Atlassian account e-mail address.

            password (str):
                The API token or password.

        Raises:
            reviewboard.hostingsvcs.errors.AuthorizationError:
                The server rejected the credentials.

            reviewboard.hostingsvcs.errors.HostingServiceError:
                There was an error talking to the server.
        """
        self._http_get(server_url=server_url,
                       path='myself',
                       username=username,
                       password=password)

    def get_issue(
        self,
        *,
        server_url: str,
        key: str,
        fields: str,
    ) -> api.Issue:
        """Return an issue.

        Args:
            server_url (str):
                The root URL of the JIRA server.

            key (str):
                The issue key.

            fields (str):
                A comma-separated list of the fields to load.

        Returns:
            reviewboard.hostingsvcs.jira.api.Issue:
            The issue.

        Raises:
            reviewboard.hostingsvcs.errors.HostingServiceError:
                There was an error loading the issue.
        """
        # Issue keys come from users, so they're escaped to keep them from
        # changing the rest of the URL.
        return self._api_get(
            server_url=server_url,
            path=f'issue/{quote(key, safe="")}',
            result_type=api.Issue,
            params={
                'fields': fields,
            })

    def search_issues(
        self,
        *,
        server_url: str,
        jql: str,
        max_results: int,
        fields: str,
    ) -> Sequence[api.Issue]:
        """Return issues matching a JQL query.

        JIRA Cloud no longer offers the ``search`` endpoint, so its
        replacement (``search/jql``) is used there.

        On JIRA Data Center, the query isn't validated, so a key that
        doesn't exist returns no results instead of an error. JIRA Cloud
        always validates the query, and returns an HTTP 400 instead.

        Args:
            server_url (str):
                The root URL of the JIRA server.

            jql (str):
                The JQL query.

            max_results (int):
                The maximum number of issues to return.

            fields (str):
                A comma-separated list of the fields to load.

        Returns:
            list of reviewboard.hostingsvcs.jira.api.Issue:
            The matching issues.

        Raises:
            reviewboard.hostingsvcs.errors.HostingServiceError:
                There was an error performing the search.
        """
        params = {
            'fields': fields,
            'jql': jql,
            'maxResults': str(max_results),
        }

        if get_jira_cloud_site(server_url) is not None:
            path = 'search/jql'
        else:
            path = 'search'
            params['validateQuery'] = 'false'

        rsp = self._api_get(server_url=server_url,
                            path=path,
                            result_type=api.SearchResponse,
                            params=params)

        return rsp.issues

    def get_issue_picker_keys(
        self,
        *,
        server_url: str,
        query: str,
        current_jql: str,
    ) -> list[str]:
        """Return issue keys matching a query through the issue picker.

        Args:
            server_url (str):
                The root URL of the JIRA server.

            query (str):
                The typed query.

            current_jql (str):
                A JQL query to limit the "current search" section to.

        Returns:
            list of str:
            The matching issue keys, in the picker's order, without
            duplicates.

        Raises:
            reviewboard.hostingsvcs.errors.HostingServiceError:
                There was an error querying the picker.
        """
        rsp = self._api_get(
            server_url=server_url,
            path='issue/picker',
            result_type=api.PickerResponse,
            params={
                # Without this, the "current search" section (the actual
                # matches) is left out of the response.
                'currentJQL': current_jql,
                'query': query,
            })

        keys: list[str] = []

        for section in rsp.sections:
            for issue in section.issues:
                key = issue.key

                if key not in keys:
                    keys.append(key)

        return keys

    def get_http_credentials(
        self,
        account: HostingServiceAccount,
        username: (str | None) = None,
        password: (str | None) = None,
        *,
        anonymous: bool = False,
        **kwargs,
    ) -> HostingServiceCredentials:
        """Return credentials used to authenticate with the service.

        Args:
            account (reviewboard.hostingsvcs.models.HostingServiceAccount):
                The stored authentication data for the service.

            username (str, optional):
                An explicit username passed by the caller.

            password (str, optional):
                An explicit password passed by the caller.

            anonymous (bool, optional):
                Whether to send the request without credentials.

            **kwargs (dict):
                Additional keyword arguments passed in when making the HTTP
                request.

        Returns:
            dict:
            A dictionary of credentials for the request.
        """
        if anonymous:
            return {}

        return super().get_http_credentials(account=account,
                                            username=username,
                                            password=password,
                                            **kwargs)

    def open_http_request(
        self,
        request: HostingServiceHTTPRequest,
    ) -> HostingServiceHTTPResponse:
        """Perform a raw HTTP request and return the result.

        Requests time out, so a slow server can't tie up a web worker.

        Args:
            request (reviewboard.hostingsvcs.base.http.
                     HostingServiceHTTPRequest):
                The HTTP request to open.

        Returns:
            reviewboard.hostingsvcs.base.http.HostingServiceHTTPResponse:
            The successful response information from the server.

        Raises:
            urllib.error.URLError:
                There was an error performing a request on the URL.
        """
        try:
            return request.open(timeout=_REQUEST_TIMEOUT_SECS)
        except TimeoutError as e:
            # urllib only wraps timeouts while connecting. A timeout while
            # reading the response is raised as-is.
            raise URLError(e) from e

    def process_http_error(
        self,
        request: HostingServiceHTTPRequest,
        e: URLError,
    ) -> None:
        """Process an HTTP error, raising a more specific error.

        Args:
            request (reviewboard.hostingsvcs.base.http.
                     HostingServiceHTTPRequest):
                The request that resulted in an error.

            e (urllib.error.URLError):
                The error to process.

        Raises:
            reviewboard.hostingsvcs.errors.AuthorizationError:
                The server rejected the credentials.

            reviewboard.hostingsvcs.errors.HostingServiceAPIError:
                The server returned an HTTP error.

            reviewboard.hostingsvcs.errors.HostingServiceError:
                The server could not be reached.
        """
        super().process_http_error(request, e)

        if not isinstance(e, HTTPError):
            raise HostingServiceError(str(e.reason))

        http_code = e.code

        try:
            error = api.APIError.model_validate_json(e.read())
            message = error.message
        except ValidationError:
            # Some errors (such as a proxy's error page) aren't JSON.
            error = None
            message = ''

        message = message or str(e)

        if http_code == 401:
            raise AuthorizationError(message, http_code=http_code)

        raise HostingServiceAPIError(message,
                                     http_code=http_code,
                                     rsp=error)

    def _api_get(
        self,
        *,
        server_url: str,
        path: str,
        result_type: type[_TModel],
        params: (Mapping[str, str] | None) = None,
    ) -> _TModel:
        """Perform a GET request to the API and parse the result.

        Args:
            server_url (str):
                The root URL of the JIRA server.

            path (str):
                The path of the API endpoint, relative to ``/rest/api/2/``.

            result_type (type):
                The pydantic model to parse the response into.

            params (dict, optional):
                Query parameters for the request.

        Returns:
            pydantic.BaseModel:
            The parsed response.

        Raises:
            reviewboard.hostingsvcs.errors.HostingServiceError:
                There was an error performing the request, or the response
                could not be parsed.
        """
        rsp = self._http_get(server_url=server_url,
                             path=path,
                             params=params)

        try:
            return result_type.model_validate_json(rsp.data)
        except ValidationError as e:
            logger.error('Unexpected response from JIRA for %s/rest/api/2/%s: '
                         '%s',
                         server_url, path, e)

            raise HostingServiceError(
                gettext('Unexpected response from JIRA.'))

    def _http_get(
        self,
        *,
        server_url: str,
        path: str,
        params: (Mapping[str, str] | None) = None,
        username: (str | None) = None,
        password: (str | None) = None,
    ) -> HostingServiceHTTPResponse:
        """Perform a GET request to the API.

        Without an explicit username and password, the account's stored
        credentials are used, but only for the account's own server.

        Args:
            server_url (str):
                The root URL of the JIRA server.

            path (str):
                The path of the API endpoint, relative to ``/rest/api/2/``.

            params (dict, optional):
                Query parameters for the request.

            username (str, optional):
                An explicit username to authenticate with.

            password (str, optional):
                An explicit password or API token to authenticate with.

        Returns:
            reviewboard.hostingsvcs.base.http.HostingServiceHTTPResponse:
            The response.

        Raises:
            reviewboard.hostingsvcs.errors.HostingServiceError:
                There was an error performing the request.
        """
        anonymous = (
            username is None and
            server_url != self.hosting_service.account.hosting_url
        )

        return self.http_get(f'{server_url}/rest/api/2/{path}',
                             query=params,
                             username=username,
                             password=password,
                             anonymous=anonymous)
