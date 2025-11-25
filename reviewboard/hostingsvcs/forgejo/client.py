"""Client for Forgejo.

Version Added:
    7.1
"""

from __future__ import annotations

import json
import logging
import re
from base64 import b64decode
from typing import List, TypeVar, TYPE_CHECKING
from urllib.error import HTTPError
from urllib.parse import quote as urlquote, urlencode
from uuid import uuid4

from django.utils.translation import gettext as _
from pydantic import BaseModel, TypeAdapter, ValidationError

from reviewboard.hostingsvcs.base.client import HostingServiceClient
from reviewboard.hostingsvcs.errors import (
    AuthorizationError,
    HostingServiceError,
    HostingServiceAPIError,
    TwoFactorAuthCodeRequiredError,
)
from reviewboard.hostingsvcs.forgejo import api
from reviewboard.hostingsvcs.forgejo.errors import APITokenNameInUseError
from reviewboard.scmtools.core import Branch, Commit
from reviewboard.scmtools.crypto_utils import decrypt_password
from reviewboard.scmtools.errors import (
    FileNotFoundError,
    RepositoryNotFoundError,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from reviewboard.hostingsvcs.base.bug_tracker import BugInfo
    from reviewboard.hostingsvcs.base.hosting_service import \
        HostingServiceCredentials
    from reviewboard.hostingsvcs.forgejo.service import Forgejo
    from reviewboard.hostingsvcs.models import HostingServiceAccount
    from reviewboard.scmtools.models import Repository

    _T = TypeVar('_T')
    _TModel = TypeVar('_TModel', bound=BaseModel)


logger = logging.getLogger(__name__)


class ForgejoClient(HostingServiceClient):
    """Hosting service client for Forgejo.

    Version Added:
        7.1
    """

    #: Regex for index lines in the diff.
    _index_line_re: re.Pattern[bytes]

    #: Regex for SHAs for deleted/added files.
    _missing_file_sha_re: re.Pattern[str]

    def __init__(
        self,
        hosting_service: Forgejo,
    ) -> None:
        """Initialize the client.

        Args:
            hosting_service (Forgejo):
                The hosting service instance.
        """
        super().__init__(hosting_service)

        self.account = hosting_service.account
        self._index_line_re = re.compile(
            br'^index (?P<a>[0-9a-f]+)..(?P<b>[0-9a-f]+)((?P<rest>\s.*)?)$')
        self._missing_file_sha_re = re.compile(r'^0+$')

    def get_http_credentials(
        self,
        account: HostingServiceAccount,
        username: (str | None) = None,
        password: (str | None) = None,
        **kwargs,
    ) -> HostingServiceCredentials:
        """Return credentials used to authenticate with Forgejo.

        Args:
            account (reviewboard.hostingsvcs.models.HostingServiceAccount):
                The stored authentication data for the service.

            username (str, optional):
                An explicit username passed by the caller. This is not used.

            password (str, optional):
                An explicit password passed by the caller. This is not used.

            **kwargs (dict, unused):
                Additional keyword arguments passed in when making the HTTP
                request.

        Returns:
            dict:
            A dictionary of credentials for the request.
        """
        if encrypted_token := account.data.get('api_token'):
            token = decrypt_password(encrypted_token)

            return {
                'header': {
                    'Authorization': f'token {token}',
                },
            }

        return {}

    def check_repository(
        self,
        *,
        hosting_url: str,
        repository_owner: str,
        repository_name: str,
    ) -> None:
        """Check that a repository is valid and accessible.

        Args:
            hosting_url (str):
                The URL of the Forgejo server.

            repository_owner (str):
                The repository owner.

            repository_name (str):
                The repository name.

        Raises:
            reviewboard.scmtools.errors.RepositoryNotFoundError:
                A repository was not found with the given parameters.
        """
        url = self._get_api_repo_root(
            hosting_url=hosting_url,
            repository_owner=repository_owner,
            repository_name=repository_name)

        try:
            # We don't actually use any fields from this (right now), but we
            # want to attempt to deserialize just to verify that we have a
            # valid repository response.
            self._api_get(
                url=url,
                result_type=api.Repository)
        except HostingServiceAPIError as e:
            error = e.rsp
            assert isinstance(error, api.APIError)

            if error.message == 'GetUserByName':
                raise RepositoryNotFoundError(
                    (
                        _('A user with the name {repository_owner} was not '
                          'found or is not accessible.')
                        .format(repository_owner=repository_owner)
                    ),
                    form_field_id='repository_owner')
            elif e.http_code == 404:
                raise RepositoryNotFoundError(
                    (
                        _('A repository with the name {repository_name} was '
                          'not found for the owner {repository_owner}')
                        .format(repository_owner=repository_owner,
                                repository_name=repository_name)
                    ),
                    form_field_id='repository_name')
            else:
                logger.warning(
                    'Unexpected error when checking repository with API URL '
                    '%s: %s',
                    url, str(e))

                raise RepositoryNotFoundError()
        except HostingServiceError as e:
            logger.warning(
                'Unexpected error when checking repository with API URL '
                '%s: %s',
                url, str(e))

            raise RepositoryNotFoundError()

    def create_api_token(
        self,
        *,
        token_name: str,
        hosting_url: str,
        username: str,
        password: str,
        two_factor_auth_code: (str | None) = None,
    ) -> str:
        """Create an API token for the given user.

        Args:
            token_name (str):
                The name to use for the token.

            hosting_url (str):
                The URL of the Forgejo server.

            username (str):
                The username for the account.

            password (str):
                The password for the account.

            two_factor_auth_code (str, optional):
                The two-factor authentication code provided by the user.

        Returns:
            str:

        Raises:
            reviewboard.certs.errors.CertificateVerificationError:
                The certificate for the host is invalid or untrusted.

            reviewboard.hostingsvcs.errors.AuthorizationError:
                The credentials provided were not valid.

            reviewboard.hostingsvcs.errors.TwoFactorAuthCodeRequiredError:
                A two-factor authentication code is required to authorize
                this account. The request must be retried with the same
                credentials and with the ``two_factor_auth_code`` parameter
                provided.

            reviewboard.hostingsvcs.errors.HostingServiceError:
                A non-authentication error occurred.

            reviewboard.hostingsvcs.forgejo.errors.APITokenNameInUseError:
                The API token name was already used.
        """
        api_root = self._get_api_root(hosting_url)
        url_username = urlquote(username)
        url = f'{api_root}/users/{url_username}/tokens'
        trace_id = str(uuid4())

        try:
            body = json.dumps({
                'name': token_name,
                'scopes': [
                    'read:issue',
                    'read:organization',
                    'read:repository',
                    'read:user',
                ],
            }).encode()

            headers = {
                'Accept': 'application/json',
            }

            if two_factor_auth_code:
                headers['X-Forgejo-OTP'] = two_factor_auth_code

            rsp = self.http_post(
                url,
                body=body,
                content_type='application/json',
                headers=headers,
                username=username,
                password=password)

            logger.info('Created API token for user %s on server %s',
                        username, hosting_url)
            access_token = api.AccessToken.model_validate_json(rsp.data)

            return access_token.sha1
        except ValidationError as e:
            logger.error('[%s] Data validation failed for API token creation: '
                         '%s',
                         trace_id, e)
            raise HostingServiceError(
                _(
                    'Unexpected response from Forgejo server. Check the '
                    'Review Board server logs for more information (error ID '
                    '{trace_id}'
                ).format(trace_id=trace_id))
        except HTTPError as e:
            data = e.read()

            logger.error('[%s] HTTP error (code=%s) creating API token with '
                         'POST %s: %s ',
                         trace_id, e.code, url, data.decode())

            try:
                error = api.APIError.model_validate_json(data)
            except ValidationError:
                error = data.decode()
                error_code = e.code

                logger.error(
                    '[%s] Unexpected error (HTTP %d) when creating API token '
                    'for user %s on server %s: %s',
                    trace_id, error_code, username, hosting_url, error)

                raise HostingServiceError(
                    _(
                        'Unknown error while creating Forgejo API token. '
                        'See the Review Board server logs for more '
                        'information (error ID {trace_id}).'
                    )
                    .format(trace_id=trace_id))

            if error.message == 'access token name has been used already':
                logger.warning(
                    'Creating API token (name="%s") for user %s on server %s '
                    'failed due to duplicate name.',
                    token_name, username, hosting_url)

                raise APITokenNameInUseError()
            elif error.message == 'invalid provided OTP':
                logger.info('Invalid OTP when creating API token for user %s '
                            'on server %s',
                            username, hosting_url)

                raise TwoFactorAuthCodeRequiredError(
                    _('Enter your two-factor authentication code'))
            elif e.code == 401:
                logger.warning('Authentication failure when creating API '
                               'token for user %s on server %s',
                               username, hosting_url)

                raise AuthorizationError(
                    _('The username or password is incorrect.'))
            else:
                logger.error('Unexpected error when creating API token for '
                             'user %s on server %s: %s',
                             username, hosting_url, error.message)

                raise HostingServiceError(error.message)

    def get_blob(
        self,
        *,
        hosting_url: str,
        repository: Repository,
        path: str,
        sha: str,
    ) -> bytes:
        """Retrieve a git blob.

        Args:
            hosting_url (str):
                The URL of the Forgejo server.

            repository (reviewboard.scmtools.models.Repsitory):
                The repository.

            path (str):
                The path of the file.

            sha (str):
                The hash of the blob to retrieve.

        Returns:
            bytes:
            The contents of the file.

        Raises:
            reviewboard.hostingsvcs.errors.HostingServiceError:
                An error occurred when fetching the file.

            reviewboard.scmtools.errors.FileNotFoundError:
                The blob with the given SHA was not found.
        """
        repo_root = self._get_api_repo_root(hosting_url, repository)

        try:
            url_sha = urlquote(sha)
            blob = self._api_get(
                url=f'{repo_root}/git/blobs/{url_sha}',
                result_type=api.GitBlobResponse,
                repository=repository)

            if blob.encoding != 'base64':
                logger.error('Failed to get blob "%s" for repository pk=%d: '
                             'encoding was "%s" but only base64 is '
                             'supported.',
                             sha, repository.pk, blob.encoding)

                raise HostingServiceError(
                    _('Forgejo returned data with an unknown encoding.'))

            return b64decode(blob.content)
        except HostingServiceAPIError as e:
            error = e.rsp
            assert isinstance(error, api.APIError)

            # If a blob with the given SHA cannot be found, this endpoint
            # returns HTTP 400 with this message. We only get HTTP 404 if
            # the owner/repository names in the URL are incorrect.
            if error.message.startswith('object does not exist'):
                raise FileNotFoundError(path, revision=sha)
            else:
                raise e
        except Exception as e:
            raise HostingServiceError(str(e))

    def get_branches(
        self,
        *,
        hosting_url: str,
        repository: Repository,
    ) -> Sequence[Branch]:
        """Return a list of all branches in the repositories.

        Args:
            hosting_url (str):
                The URL of the Forgejo server.

            repository (reviewboard.scmtools.models.Repository):
                The repository for which branches should be returned.

        Returns:
            list of reviewboard.scmtools.core.Branch:
            The branches.

        Raises:
            reviewboard.hostingsvcs.errors.HostingServiceError:
                There was an error fetching branches.
        """
        repo_root = self._get_api_repo_root(hosting_url, repository)

        repo_info = self._api_get(url=repo_root, result_type=api.Repository)

        refs = self._api_get(
            url=f'{repo_root}/git/refs',
            result_type=TypeAdapter(List[api.GitReference]),
            repository=repository)

        results: list[Branch] = []

        default_ref: (int | None) = None
        main_ref: (int | None) = None
        master_ref: (int | None) = None

        for i, ref in enumerate(refs):
            if ref.ref.startswith('refs/heads/'):
                name = ref.ref[len('refs/heads/'):]
            else:
                name = ref.ref

            results.append(Branch(
                id=name,
                commit=ref.object.sha,
            ))

            if name == repo_info.default_branch:
                default_ref = i
            if name == 'main':
                main_ref = i
            elif name == 'master':
                master_ref = i

        # Prefer the configured default, then "main", then "master".
        if default_ref is not None:
            results[default_ref].default = True
        elif main_ref is not None:
            results[main_ref].default = True
        elif master_ref is not None:
            results[master_ref].default = True
        elif len(results) > 0:
            results[0].default = True

        return results

    def get_commits(
        self,
        hosting_url: str,
        repository: Repository,
        branch: (str | None) = None,
        start: (str | None) = None,
    ) -> Sequence[Commit]:
        """Return a list of commits backward in history from a given point.

        Args:
            hosting_url (str):
                The URL of the Forgejo server.

            repository (reviewboard.scmtools.models.Repository):
                The repository to retrieve commits from.

            branch (str, optional):
                The branch to retrieve from.

                If this is not provided, the default branch will be used.

            start (str, optional):
                An optional starting revision.

                If this is not provided, the most recent commits will be
                returned.

        Returns:
            list of reviewboard.scmtools.core.Commit:
            The retrieved commits.

        Raises:
            ValueError:
                Neither a ``branch`` or ``start`` parameter was provided.

            reviewboard.hostingsvcs.errors.HostingServiceError:
                There was an error fetching commits.
        """
        repo_root = self._get_api_repo_root(hosting_url, repository)

        sha = start or branch

        if not sha:
            raise ValueError('Either "branch" or "start" must be provided.')

        assert isinstance(sha, str)

        commits = self._api_get(
            url=f'{repo_root}/commits',
            result_type=TypeAdapter(List[api.Commit]),
            params={
                'sha': sha,
                'stat': '0',
                'verification': '0',
                'files': '0',
                'limit': '30',
            },
            repository=repository)

        results: list[Commit] = []

        for commit in commits:
            if commit.parents:
                parent = commit.parents[0].sha
            else:
                parent = ''

            results.append(Commit(
                author_name=commit.commit.author.name,
                id=commit.sha,
                date=commit.created,
                message=commit.commit.message,
                parent=parent,
            ))

        return results

    def get_change(
        self,
        hosting_url: str,
        repository: Repository,
        revision: str,
    ) -> Commit:
        """Return an individual change.

        Args:
            hosting_url (str):
                The URL of the Forgejo server.

            repository (reviewboard.scmtools.models.Repository):
                The repository to get the change from.

            revision (str):
                The revision to retrieve.

        Returns:
            reviewboard.scmtools.core.Commit:
            The change.

        Raises:
            reviewboard.hostingsvcs.errors.HostingServiceError:
                There was an error fetching the commit.
        """
        repo_root = self._get_api_repo_root(hosting_url, repository)
        url_revision = urlquote(revision)

        commit = self._api_get(
            url=f'{repo_root}/git/commits/{url_revision}',
            result_type=api.Commit,
            repository=repository)

        if commit.parents:
            parent = commit.parents[0].sha
        else:
            parent = ''

        diff_url = f'{repo_root}/git/commits/{url_revision}.diff'

        try:
            diff = self.http_get(diff_url).data.splitlines()
        except HTTPError as e:
            logger.error('HTTP error fetching diff at %s (repository %s): %s',
                         diff_url, repository, e)

            raise HostingServiceError(
                'Failed to fetch diff data from Forgejo.')

        all_shas = (
            self._get_blob_shas_in_tree(repo_root, commit.sha, repository) |
            self._get_blob_shas_in_tree(repo_root, parent, repository))

        diff_lines: list[bytes] = []
        index_line_re = self._index_line_re
        missing_file_sha_re = self._missing_file_sha_re

        def expand_sha(
            partial_sha: str,
        ) -> str:
            if missing_file_sha_re.match(partial_sha):
                return '0' * 40

            for full_sha in all_shas:
                if full_sha.startswith(partial_sha):
                    return full_sha

            logger.warning('Unable to find full SHA for blob %s (repository '
                           '%s)',
                           partial_sha, repository)
            return partial_sha

        for line in diff:
            m = index_line_re.match(line)

            if m:
                sha1 = expand_sha(m.group('a').decode())
                sha2 = expand_sha(m.group('b').decode())
                rest = m.group('rest') or b''

                new_line = (b'index %s..%s%s'
                            % (sha1.encode(), sha2.encode(), rest))

                diff_lines.append(new_line)
            else:
                new_line = line
                diff_lines.append(line)

        return Commit(
            author_name=commit.commit.author.name,
            id=commit.sha,
            date=commit.created,
            message=commit.commit.message,
            parent=parent,
            diff=b'\n'.join(diff_lines),
        )

    def get_bug_info(
        self,
        hosting_url: str,
        repository: Repository,
        bug_id: str,
    ) -> BugInfo:
        """Return the information for the specified bug.

        Args:
            hosting_url (str):
                The URL of the Forgejo server.

            repository (reviewboard.scmtools.models.Repository):
                The repository object.

            bug_id (str):
                The ID of the bug to fetch.

        Returns:
            reviewboard.hostingsvcs.bugtracker.BugInfo:
            Information about the bug.
        """
        repo_root = self._get_api_repo_root(hosting_url, repository)

        result: BugInfo = {
            'summary': '',
            'description': '',
            'status': '',
        }

        try:
            url_bug_id = urlquote(bug_id)
            issue = self._api_get(
                url=f'{repo_root}/issues/{url_bug_id}',
                result_type=api.Issue,
                repository=repository)

            result['summary'] = issue.title
            result['description'] = issue.body
            result['description_text_format'] = 'markdown'
            result['status'] = issue.state
        except HostingServiceError:
            # Errors will already be logged, and the failure mode for this is
            # to return the result with empty strings.
            pass

        return result

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
            query = urlencode(params)
            url = f'{url}?{query}'

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
                _('Unexpected response from Forgejo server.'))
        except HTTPError as e:
            logger.error('HTTP error in API GET %s for repository %s: %s',
                         url, repository, e)

            data = e.read()

            try:
                error = api.APIError.model_validate_json(data)

                raise HostingServiceAPIError(
                    _('API error from Forgejo: {e}').format(e=error.message),
                    http_code=e.code,
                    rsp=error,
                )
            except ValidationError as pydantic_err:
                logger.error('Unable to parse error response for API GET %s '
                             '(repository=%s): %s',
                             url, repository, pydantic_err)

                raise HostingServiceError(
                    _('Unknown response from Forgejo: {rsp}').format(
                        rsp=data.decode()),
                    http_code=e.code)

    def _get_api_root(
        self,
        hosting_url: str,
    ) -> str:
        """Return the root URL for the API.

        Args:
            hosting_url (str):
                The URL of the Forgejo server.

        Returns:
            str:
            The base URL for the API.
        """
        if not hosting_url.endswith('/'):
            hosting_url += '/'

        return f'{hosting_url}api/v1'

    def _get_api_repo_root(
        self,
        hosting_url: str,
        repository: (Repository | None) = None,
        repository_owner: (str | None) = None,
        repository_name: (str | None) = None,
    ) -> str:
        """Get the API root for a repository in the API.

        Args:
            hosting_url (str):
                The URL of the Forgejo server.

            repository (reviewboard.scmtools.models.Repository, optional):
                The repository object.

            repository_owner (str, optional):
                The repository owner.

            repository_name (str, optional):
                The repository name.

        Returns:
            str:
            The base URL for API resources for the repository.
        """
        if repository:
            repository_owner = urlquote(
                repository.extra_data['repository_owner'])
            repository_name = urlquote(
                repository.extra_data['repository_name'])
        elif not repository_owner or not repository_name:
            raise ValueError('Either a repository or an owner/name must be '
                             'provided')

        api_root = self._get_api_root(hosting_url)

        return f'{api_root}/repos/{repository_owner}/{repository_name}'

    def _get_blob_shas_in_tree(
        self,
        repo_root: str,
        commit: str,
        repository: Repository,
    ) -> set[str]:
        """Return all the SHAs in the tree for a given commit.

        Args:
            repo_root (str):
                The URL root for the repository.

            commit (str):
                The SHA of the commit to fetch the tree for.

            repository (reviewboard.scmtools.models.Repository):
                The repository.

        Returns:
            set:
            A set of all the blob SHAs in the tree.

        Raises:
            reviewboard.hostingsvcs.errors.HostingServiceError:
                There was an error fetching the tree.
        """
        url_commit = urlquote(commit)
        url = f'{repo_root}/git/trees/{url_commit}'
        result: set[str] = set()

        page = 1

        while 1:
            tree_page = self._api_get(
                url=url,
                result_type=api.GitTreeResponse,
                params={
                    'page': str(page),
                    'recursive': 'true',
                },
                repository=repository)

            if tree_page.tree is None:
                break

            for entry in tree_page.tree:
                result.add(entry.sha)

            if tree_page.truncated:
                page += 1
            else:
                break

        return result
