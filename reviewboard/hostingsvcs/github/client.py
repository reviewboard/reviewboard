"""Hosting service client for GitHub.

Version Added:
    9.0:
    Split up :py:mod:`reviewboard.hostingsvcs.github`.
"""

from __future__ import annotations

import json
import re
import logging
from typing import TYPE_CHECKING

from reviewboard.hostingsvcs.base.client import HostingServiceClient
from reviewboard.hostingsvcs.errors import (
    AuthorizationError,
    HostingServiceError,
)
from reviewboard.hostingsvcs.utils.paginator import APIPaginator
from reviewboard.scmtools.crypto_utils import decrypt_password
from reviewboard.scmtools.errors import FileNotFoundError, SCMError

if TYPE_CHECKING:
    from urllib.error import URLError

    from reviewboard.hostingsvcs.base.http import HostingServiceHTTPRequest


logger = logging.getLogger(__name__)


class GitHubAPIPaginator(APIPaginator):
    """Paginates over GitHub API list resources.

    This is returned by some GitHubClient functions in order to handle
    iteration over pages of results, without resorting to fetching all
    pages at once or baking pagination into the functions themselves.
    """
    start_query_param = 'page'
    per_page_query_param = 'per_page'

    LINK_RE = re.compile(r'\<(?P<url>[^>]+)\>; rel="(?P<rel>[^"]+)",? *')

    def fetch_url(self, url):
        """Fetches the page data from a URL."""
        rsp = self.client.http_get(url)

        # Find all the links in the Link header and key off by the link
        # name ('prev', 'next', etc.).
        link_header = rsp.get_header('Link', '')

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


class GitHubClient(HostingServiceClient):
    """Hosting service client for GitHub."""

    RAW_MIMETYPE = 'application/vnd.github.v3.raw'

    def __init__(self, hosting_service):
        super(GitHubClient, self).__init__(hosting_service)
        self.account = hosting_service.account

    def get_http_credentials(self, account, username=None, password=None,
                             **kwargs):
        """Return credentials used to authenticate with GitHub.

        Unless an explicit username and password is provided, this will
        use the ones stored for the account.

        Args:
            account (reviewboard.hostingsvcs.models.HostingServiceAccount):
                The stored authentication data for the service.

            username (unicode, optional):
                An explicit username passed by the caller. This will override
                the data stored in the account, if both a username and
                password are provided.

            password (unicode, optional):
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

    def process_http_response(self, response):
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

        try:
            data = e.read()  # type: ignore
            rsp = json.loads(data.decode('utf-8'))
        except Exception:
            rsp = None

        http_code: (int | None) = getattr(e, 'code', None)

        if rsp and 'message' in rsp:
            message = rsp['message']

            if http_code == 401:
                raise AuthorizationError(message, http_code=http_code)

            raise HostingServiceError(message, http_code=http_code)
        else:
            raise HostingServiceError(str(e), http_code=http_code)

    #
    # Higher-level API methods
    #

    def api_get_list(self, url, start=None, per_page=None, *args, **kwargs):
        """Perform an HTTP GET to a GitHub API and returns a paginator.

        This returns a GitHubAPIPaginator that's used to iterate over the
        pages of results. Each page contains information on the data and
        headers from that given page.

        The ``start`` and ``per_page`` parameters can be used to control
        where pagination begins and how many results are returned per page.
        ``start`` is a 0-based index representing a page number.
        """
        if start is not None:
            # GitHub uses 1-based indexing, so add one.
            start += 1

        return GitHubAPIPaginator(
            client=self,
            url=url,
            start=start,
            per_page=per_page)

    def api_get_blob(self, repo_api_url, path, sha):
        """Return the contents of a file using the GitHub API.

        Args:
            repo_api_url (unicode):
                The absolute URL for the base repository API.

            path (unicode):
                The path of the file within the repository.

            sha (unicode):
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
                url='%s/git/blobs/%s' % (repo_api_url, sha),
                headers={
                    'Accept': self.RAW_MIMETYPE,
                }).data
        except HostingServiceError:
            raise FileNotFoundError(path, sha)

    def api_get_commits(self, repo_api_url, branch=None, start=None):
        url = '%s/commits' % repo_api_url

        # Note that we don't always use the branch, since the GitHub API
        # doesn't support limiting by branch *and* starting at a SHA. So, the
        # branch argument can be safely ignored if a sha is provided.
        start = start or branch

        if start:
            url += '?sha=%s' % start

        try:
            return self.http_get(url).json
        except Exception as e:
            logger.warning('Failed to fetch commits from %s: %s',
                           url, e, exc_info=True)
            raise SCMError(str(e))

    def api_get_compare_commits(self, repo_api_url, parent_revision, revision):
        # If the commit has a parent commit, use GitHub's "compare two commits"
        # API to get the diff. Otherwise, fetch the commit itself.
        if parent_revision:
            url = '%s/compare/%s...%s' % (repo_api_url, parent_revision,
                                          revision)
        else:
            url = '%s/commits/%s' % (repo_api_url, revision)

        try:
            comparison = self.http_get(url).json
        except Exception as e:
            logger.warning('Failed to fetch commit comparison from %s: %s',
                           url, e, exc_info=True)
            raise SCMError(str(e))

        if parent_revision:
            tree_sha = comparison['base_commit']['commit']['tree']['sha']
        else:
            tree_sha = comparison['commit']['tree']['sha']

        return comparison['files'], tree_sha

    def api_get_heads(self, repo_api_url):
        url = '%s/git/refs/heads' % repo_api_url

        try:
            rsp = self.http_get(url).json
            return [ref for ref in rsp if ref['ref'].startswith('refs/heads/')]
        except Exception as e:
            logger.warning('Failed to fetch commits from %s: %s',
                           url, e, exc_info=True)
            raise SCMError(str(e))

    def api_get_issue(self, repo_api_url, issue_id):
        url = '%s/issues/%s' % (repo_api_url, issue_id)

        try:
            return self.http_get(url).json
        except Exception as e:
            logger.warning('GitHub: Failed to fetch issue from %s: %s',
                           url, e, exc_info=True)
            raise SCMError(str(e))

    def api_get_remote_repositories(self, api_url, owner, owner_type,
                                    filter_type=None, start=None,
                                    per_page=None):
        url = api_url

        if owner_type == 'organization':
            url += 'orgs/%s/repos' % owner
        elif owner_type == 'user':
            if owner == self.account.username:
                # All repositories belonging to an authenticated user.
                url += 'user/repos'
            else:
                # Only public repositories for the user.
                url += 'users/%s/repos' % owner
        else:
            raise ValueError(
                "owner_type must be 'organization' or 'user', not %r'"
                % owner_type)

        if filter_type:
            url += '?type=%s' % (filter_type or 'all')

        return self.api_get_list(url,
                                 start=start,
                                 per_page=per_page)

    def api_get_remote_repository(self, api_url, owner, repository_id):
        try:
            return self.http_get(
                '%srepos/%s/%s' % (api_url, owner, repository_id)).json
        except HostingServiceError as e:
            if e.http_code == 404:
                return None
            else:
                raise

    def api_get_tree(self, repo_api_url, sha, recursive=False):
        url = '%s/git/trees/%s' % (repo_api_url, sha)

        if recursive:
            url += '?recursive=1'

        try:
            return self.http_get(url).json
        except Exception as e:
            logger.warning('Failed to fetch tree from %s: %s',
                           url, e, exc_info=True)
            raise SCMError(str(e))
