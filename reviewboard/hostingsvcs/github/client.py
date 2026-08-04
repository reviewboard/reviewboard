"""Hosting service client for GitHub.

Version Added:
    9.0:
    Split up :py:mod:`reviewboard.hostingsvcs.github`.
"""

from __future__ import annotations

import re
import logging
from collections.abc import Sequence
from typing import TYPE_CHECKING, TypeVar
from urllib.error import HTTPError
from urllib.parse import quote as urlquote, urlencode

from django.utils.translation import gettext as _
from pydantic import BaseModel, TypeAdapter, ValidationError

from reviewboard.hostingsvcs.base.client import HostingServiceClient
from reviewboard.hostingsvcs.errors import (
    AuthorizationError,
    HostingServiceError,
    HostingServiceAPIError,
)
from reviewboard.hostingsvcs.base.paginator import (
    APIPaginator,
    PageDataT,
    PageDataItemT,
    ProxyPaginator,
)
from reviewboard.hostingsvcs.github import api
from reviewboard.scmtools.crypto_utils import decrypt_password
from reviewboard.scmtools.errors import FileNotFoundError

if TYPE_CHECKING:
    from typing import Any
    from urllib.error import URLError

    from reviewboard.hostingsvcs.base.hosting_service import \
        HostingServiceCredentials
    from reviewboard.hostingsvcs.base.http import (
        HostingServiceHTTPRequest,
        HostingServiceHTTPResponse,
    )
    from reviewboard.hostingsvcs.base.paginator import (
        APIPaginatorPageData,
        BasePaginator,
    )
    from reviewboard.hostingsvcs.github.service import GitHub
    from reviewboard.hostingsvcs.models import HostingServiceAccount
    from reviewboard.scmtools.models import Repository


_T = TypeVar('_T')
_TModel = TypeVar('_TModel', bound=BaseModel)


logger = logging.getLogger(__name__)


class GitHubAPIPaginator(APIPaginator[PageDataItemT, PageDataT]):
    """Paginates over GitHub API list resources.

    This is returned by some GitHubClient functions in order to handle
    iteration over pages of results, without resorting to fetching all
    pages at once or baking pagination into the functions themselves.
    """

    LINK_RE = re.compile(r'\<(?P<url>[^>]+)\>; rel="(?P<rel>[^"]+)",? *')

    def fetch_url(
        self,
        url: str,
    ) -> APIPaginatorPageData:
        """Fetch the page data from a URL.

        Args:
            url (str):
                The URL to fetch.

        Returns:
            dict:
            A page of data.
        """
        rsp = self.client.http_get(url)

        # Find all the links in the Link header and key off by the link
        # name ('prev', 'next', etc.).
        link_header = rsp.get_header('Link', '')
        assert link_header is not None

        links = {
            m.group('rel'): m.group('url')
            for m in self.LINK_RE.finditer(link_header)
        }

        return {
            'data': rsp.json,
            'response': rsp,
            'headers': rsp.headers,
            'prev_url': links.get('prev'),
            'next_url': links.get('next'),
        }


class GitHubClient(HostingServiceClient['GitHub']):
    """Hosting service client for GitHub."""

    RAW_MIMETYPE = 'application/vnd.github.v3.raw'

    def __init__(
        self,
        hosting_service: GitHub,
    ) -> None:
        """Initialize the client.

        Args:
            hosting_service (reviewboard.hostingsvcs.base.hosting_service):
                The hosting service instance.
        """
        super().__init__(hosting_service)
        self.account = hosting_service.account

    def get_http_credentials(
        self,
        account: HostingServiceAccount,
        username: (str | None) = None,
        password: (str | None) = None,
        **kwargs,
    ) -> HostingServiceCredentials:
        """Return credentials used to authenticate with GitHub.

        Unless an explicit username and password is provided, this will
        use the ones stored for the account.

        Args:
            account (reviewboard.hostingsvcs.models.HostingServiceAccount):
                The stored authentication data for the service.

            username (str, optional):
                An explicit username passed by the caller. This will override
                the data stored in the account, if both a username and
                password are provided.

            password (str, optional):
                An explicit password passed by the caller. This will override
                the data stored in the account, if both a username and
                password are provided.

            **kwargs (dict, unused):
                Additional keyword arguments passed in when making the HTTP
                request.

        Returns:
            dict:
            A dictionary of credentials for the request.
        """
        if username is None and password is None:
            if 'personal_token' in account.data:
                username = account.username
                password = decrypt_password(account.data['personal_token'])
            elif ('authorization' in account.data and
                  'token' in account.data['authorization']):
                username = account.username
                password = account.data['authorization']['token']

        if username is not None and password is not None:
            return {
                'username': username,
                'password': password,
            }

        return {}

    def process_http_response(
        self,
        response: HostingServiceHTTPResponse,
    ) -> HostingServiceHTTPResponse:
        """Process an HTTP response and return a result.

        Args:
            response (reviewboard.hostingsvcs.base.http.
                      HostingServiceHTTPResponse):
                The response to process.

        Returns:
            reviewboard.hostingsvcs.base.http.HostingServiceHTTPResponse:
            The resulting response.
        """
        rate_limit_remaining = response.get_header('X-RateLimit-Remaining')

        try:
            if (rate_limit_remaining is not None and
                int(rate_limit_remaining) <= 100):
                logger.warning('GitHub rate limit for %s is down to %s',
                               self.account.username, rate_limit_remaining)
        except ValueError:
            pass

        return response

    def process_http_error(
        self,
        request: HostingServiceHTTPRequest,
        e: URLError,
    ) -> None:
        """Process an HTTP error, possibly raising a result.

        This will look at the error, possibly raising a more suitable exception
        in its place. It checks for SSL verification failures, bad credentials,
        and GitHub error payloads.

        Args:
            request (reviewboard.hostingsvcs.base.http.
                     HostingServiceHTTPRequest):
                The request that resulted in an error.

            e (urllib2.URLError):
                The error to process.

        Raises:
            reviewboard.hostingsvcs.errors.AuthorizationError:
                The repository credentials are invalid.

            reviewboard.hostingsvcs.errors.HostingServiceError:
                There was an error with the request. Details are in the
                response.

            reviewboard.scmtools.errors.UnverifiedCertificateError:
                The SSL certificate was not able to be verified.
        """
        super().process_http_error(request, e)

        if isinstance(e, HTTPError):
            data = e.read()
            http_code = e.code

            logger.error('HTTP error in HTTP request to %s: %s',
                         e.url, e)

            try:
                error = api.APIError.model_validate_json(data)

                if http_code == 401:
                    raise AuthorizationError(error.message,
                                             http_code=http_code)
                else:
                    raise HostingServiceAPIError(
                        _('API Error from GitHub: {e}').format(
                            e=error.message),
                        http_code=http_code,
                        rsp=error)
            except ValidationError as pydantic_err:
                logger.error('Unable to parse error response for HTTP '
                             'request to %s: %s',
                             e.url, pydantic_err)
                raise HostingServiceError(
                    _('Unknown response from GitHub: {rsp}').format(
                        rsp=data.decode()),
                    http_code=http_code)
        else:
            logger.error('Error when making HTTP request to GitHub: %s',
                         e)

            raise HostingServiceError(str(e))

    #
    # Higher-level API methods
    #

    def get_blob(
        self,
        *,
        repo_api_url: str,
        path: str,
        sha: str,
    ) -> bytes:
        """Return the contents of a file using the GitHub API.

        Args:
            repo_api_url (str):
                The absolute URL for the base repository API.

            path (str):
                The path of the file within the repository.

            sha (str):
                The SHA1 of the file within the repository.

        Returns:
            bytes:
            The contents of the file.

        Raises:
            reviewboard.scmtools.errors.FileNotFoundError:
                The file could not be found or the API could not be accessed.
        """
        try:
            return self.http_get(
                url=f'{repo_api_url}/git/blobs/{sha}',
                headers={
                    'Accept': self.RAW_MIMETYPE,
                }).data
        except HostingServiceError:
            raise FileNotFoundError(path, sha)

    def get_branches(
        self,
        *,
        repo_api_url: str,
        repository: Repository | None,
    ) -> BasePaginator[api.Branch, Sequence[api.Branch]]:
        """Make a get request to the branch list API.

        Args:
            repo_api_url (str):
                The absolute URL for the base repository API.

            repository (reviewboard.scmtools.models.Repository):
                The repository object, if available.

        Returns:
            reviewboard.hostingsvcs.utils.APIPaginator:
            A paginator for the branch repsponses.

        Raises:
            reviewboard.hostingsvcs.errors.HostingServiceError:
                There was an error fetching branches.
        """
        return self._api_get_paginated(
            url=f'{repo_api_url}/branches',
            result_type=TypeAdapter(list[api.Branch]),
            repository=repository,
        )

    def get_repository(
        self,
        *,
        repo_api_url: str,
        repository: Repository | None,
    ) -> api.Repository:
        """Make a get request to the repository API.

        Args:
            repo_api_url (str):
                The absolute URL of the base repository API.

            repository (reviewboard.scmtools.models.Repository):
                The repository object, if available.

        Returns:
            reviewboard.hostingsvcs.github.api.Repository:
            The fetched data.

        Raises:
            reviewboard.hostingsvcs.errors.HostingServiceError:
                There was an error fetching the repository.
        """
        return self._api_get(
            url=repo_api_url,
            result_type=api.Repository,
            repository=repository)

    def get_commit(
        self,
        *,
        repo_api_url: str,
        commit_id: str,
        repository: Repository | None,
    ) -> api.CommitResponse:
        """Make a get request to the commit API.

        Args:
            repo_api_url (str):
                The absolute URL for the base repository API.

            commit_id (str):
                The revision of the commit to retrieve.

            repository (reviewboard.scmtools.models.Repository):
                The repository object.

            repository (reviewboard.scmtools.models.Repository):
                The repository object, if available.

        Returns:
            reviewboard.hostingsvcs.github.api.CommitResponse:
            The fetched data.

        Raises:
            reviewboard.hostingsvcs.errors.HostingServiceError:
                There was an error fetching information about the bug.
        """
        return self._api_get(
            url=f'{repo_api_url}/commits/{urlquote(commit_id)}',
            result_type=api.CommitResponse,
            repository=repository)

    def get_commits(
        self,
        *,
        repo_api_url: str,
        start: str | None,
        repository: Repository,
    ) -> BasePaginator[api.CommitResponse, Sequence[api.CommitResponse]]:
        """Make a request to the commits API.

        This can be called multiple times in succession using the "parent"
        field of the last entry as the start parameter in order to paginate
        through the history of commits in the repository.

        Args:
            repo_api_url (str):
                The absolute URL for the base repository API.

            start (str, optional):
                An optional starting revision or branch.

                If this is not provided, the most recent commits will be
                returned.

            repository (reviewboard.scmtools.models.Repository):
                The repository to retrieve commits from.

        Returns:
            list of reviewboard.scmtools.core.Commit:
            The retrieved commits.

        Raises:
            reviewboard.hostingsvcs.errors.HostingServiceError:
                There was an error fetching commits.
        """
        if start:
            params = {'sha': start}
        else:
            params = None

        return self._api_get_paginated(
            url=f'{repo_api_url}/commits',
            result_type=TypeAdapter(list[api.CommitResponse]),
            repository=repository,
            params=params,
        )

    def get_compare_commits(
        self,
        *,
        repo_api_url: str,
        parent_id: str,
        commit_id: str,
        repository: Repository | None,
    ) -> api.CompareCommitsResponse:
        """Make a get request to the compare commits API.

        Args:
            repo_api_url (str):
                The absolute URL for the base repository API.

            parent_id (str):
                The revision of the base commit to compare against.

            commit_id (str):
                The revision of the tip commit to compare to.

            repository (reviewboard.scmtools.models.Repository):
                The repository object.

            repository (reviewboard.scmtools.models.Repository):
                The repository object, if available.

        Returns:
            reviewboard.hostingsvcs.github.api.CommitResponse:
            The fetched data.

        Raises:
            reviewboard.hostingsvcs.errors.HostingServiceError:
                There was an error fetching information about the bug.
        """
        return self._api_get(
            url=f'{repo_api_url}/compare/{parent_id}...{commit_id}',
            result_type=api.CompareCommitsResponse,
            repository=repository)

    def get_issue(
        self,
        *,
        repo_api_url: str,
        bug_id: str,
        repository: Repository | None,
    ) -> api.Issue:
        """Make a get request to the issue API.

        Args:
            repo_api_url (str):
                The absolute URL for the base repository API.

            repository (reviewboard.scmtools.models.Repository):
                The repository object.

            bug_id (str):
                The ID of the bug to fetch.

            repository (reviewboard.scmtools.models.Repository):
                The repository object, if available.

        Returns:
            reviewboard.hostingsvcs.github.api.Issue:
            The fetched data.

        Raises:
            reviewboard.hostingsvcs.errors.HostingServiceError:
                There was an error fetching information about the bug.
        """
        issue_rsp = self._api_get(
            url=f'{repo_api_url}/issues/{bug_id}',
            result_type=api.IssueResponse,
            repository=repository)

        return issue_rsp.value

    def get_repositories(
        self,
        *,
        repos_api_url: str,
        filter_type: (str | None) = None,
        start: (int | None) = None,
        per_page: (int | None) = None,
    ) -> BasePaginator[api.Repository, Sequence[api.Repository]]:
        """Make a get request to the repository list API.

        Args:
            repos_api_url (str):
                The URL of the repository list to fetch.

                This can vary depending on whether we're fetching repositories
                for a user or an organization.

            filter_type (str, optional):
                Some hosting service-specific criteria to filter by.

            start (int, optional):
                The index to start at.

            per_page (int, optional):
                The number of results per page.

        Returns:
            reviewboard.hostingsvcs.utils.APIPaginator:
            A paginator for the repository repsponses.

        Raises:
            reviewboard.hostingsvcs.errors.HostingServiceError:
                There was an error fetching the repository.
        """
        params = {}

        if filter_type:
            params['type'] = filter_type

        if start:
            params['page'] = str(start + 1)

        return self._api_get_paginated(
            url=repos_api_url,
            result_type=TypeAdapter(list[api.Repository]),
            repository=None,
            params=params,
            per_page=per_page)

    def get_tree(
        self,
        *,
        repo_api_url: str,
        tree_sha: str,
        recursive: bool,
        repository: Repository | None,
    ) -> api.TreeResponse:
        """Make a get request to the git tree API.

        Args:
            repo_api_url (str):
                The absolute URL for the base repository API.

            tree_sha (str):
                The SHA of the tree object to fetch.

            recursive (bool):
                Whether to fetch the tree contents recursively.

            repository (reviewboard.scmtools.models.Repository):
                The repository object, if available.

        Returns:
            reviewboard.hostingsvcs.github.api.TreeResponse:
            The fetched data.

        Raises:
            reviewboard.hostingsvcs.errors.HostingServiceError:
                There was an error fetching information about the bug.
        """
        if recursive:
            params = {'recursive': '1'}
        else:
            params = None

        return self._api_get(
            url=f'{repo_api_url}/git/trees/{tree_sha}',
            params=params,
            result_type=api.TreeResponse,
            repository=repository)

    def _api_get(
        self,
        *,
        url: str,
        result_type: type[_TModel] | TypeAdapter[_T],
        params: (dict[str, str] | None) = None,
        repository: (Repository | None) = None,
    ) -> _TModel | _T:
        """Perform a GET request to the API.

        Args:
            url (str):
                The URL of the API endpoint.

            result_type (pydantic.BaseModel or pydantic.TypeAdapter):
                The pydantic model or adapter to use for deserialization.

            params (dict):
                Parameters to include in the URL.

            repository (reviewboard.scmtools.models.Repository, optional):
                The repository object, if available.

        Returns:
            object:
            The deserialized data.

        Raises:
            reviewboard.hostingsvcs.base.errors.HostingServiceError:
                An error occurred while making the request.

            reviewboard.hostingsvcs.base.errors.HostingServiceAPIError:
                An error occurred while making the request, with a parsed error
                structure.
        """
        if params:
            url = f'{url}?{urlencode(params)}'

        logger.debug('Making GET request to %s', url)

        try:
            rsp = self.http_get(url)

            if isinstance(result_type, TypeAdapter):
                return result_type.validate_json(rsp.data)
            else:
                return result_type.model_validate_json(rsp.data)
        except ValidationError as e:
            logger.error('Data validation failed for API GET %s '
                         '(repository=%s): %s',
                         url, repository, e)

            raise HostingServiceError(
                _('Unexpected response from GitHub.'))

    def _api_get_paginated(
        self,
        *,
        url: str,
        result_type: TypeAdapter[list[_T]],
        repository: Repository | None,
        params: (dict[str, str] | None) = None,
        per_page: (int | None) = None,
    ) -> ProxyPaginator[_T, Sequence[_T]]:
        """Perform an HTTP GET to the API and return a paginator.

        Args:
            url (str):
                The URL of the API endpoint.

            result_type (pydantic.BaseModel or pydantic.TypeAdapter):
                The pydantic model or adapter to use for deserialization.

            repository (reviewboard.scmtools.models.Repository):
                The repository object, if available.

            params (dict, optional):
                Parameters to include in the URL.

            per_page (int, optional):
                The number of items to return per page.

        Returns:
            reviewboard.hostingsvcs.paginator.ProxyPaginator:
            A paginator over the validated results.

        Raises:
            reviewboard.hostingsvcs.base.errors.HostingServiceError:
                An error occurred while making the request.
        """
        def normalize_page_data(
            page_data: Sequence[Any],
        ) -> Sequence[_T] | None:
            try:
                return result_type.validate_python(page_data)
            except ValidationError as e:
                logger.error('Data validation failed for API GET %s '
                             '(repository=%s): %s',
                             url, repository, e)

                raise HostingServiceError(
                    _('Unexpected response from GitHub.'))

        if params is None:
            params = {}

        if per_page:
            params['per_page'] = str(per_page)

        if params:
            url = f'{url}?{urlencode(params)}'

        return ProxyPaginator[_T, Sequence[_T]](
            GitHubAPIPaginator(
                client=self,
                url=url),
            normalize_page_data_func=normalize_page_data)
