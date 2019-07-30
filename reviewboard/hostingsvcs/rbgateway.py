from __future__ import unicode_literals

import hashlib
import hmac
import json
import logging
from collections import defaultdict

from django import forms
from django.conf.urls import url
from django.http import HttpResponse, HttpResponseBadRequest
from django.utils.six.moves.urllib.error import HTTPError
from django.utils.six.moves.urllib.parse import quote
from django.utils.translation import ugettext_lazy as _, ugettext
from djblets.util.compat.django.template.loader import render_to_string

from reviewboard.admin.server import build_server_url, get_server_url
from reviewboard.hostingsvcs.errors import (AuthorizationError,
                                            HostingServiceAPIError,
                                            HostingServiceError)
from reviewboard.hostingsvcs.forms import HostingServiceForm
from reviewboard.hostingsvcs.hook_utils import (close_all_review_requests,
                                                get_repository_for_hook,
                                                get_review_request_id)
from reviewboard.hostingsvcs.service import (HostingService,
                                             HostingServiceClient)
from reviewboard.scmtools.core import Branch, Commit, UNKNOWN
from reviewboard.scmtools.crypto_utils import (decrypt_password,
                                               encrypt_password)
from reviewboard.scmtools.errors import (FileNotFoundError,
                                         RepositoryNotFoundError)
from reviewboard.site.urlresolvers import local_site_reverse


logger = logging.getLogger(__name__)


def hook_close_submitted(request, local_site_name=None,
                         repository_id=None,
                         hosting_service_id=None):
    """Close review requests as submitted after a push.

    Args:
        request (django.http.HttpRequest):
            The request from the RB Gateway webhook.

        local_site_name (unicode, optional):
            The local site name, if available.

        repository_id (int, optional):
            The ID of the repository, if available.

        hosting_service_id (unicode, optional):
            The ID of the hosting service.

    Returns:
        django.http.HttpResponse;
        A response for the request.
    """
    hook_event = request.META.get('HTTP_X_RBG_EVENT')

    if hook_event == 'ping':
        return HttpResponse()
    elif hook_event != 'push':
        return HttpResponseBadRequest(
            'Only "ping" and "push" events are supported.')

    repository = get_repository_for_hook(repository_id, hosting_service_id,
                                         local_site_name)

    sig = request.META.get('HTTP_X_RBG_SIGNATURE', '')
    m = hmac.new(repository.get_or_create_hooks_uuid().encode('utf-8'),
                 request.body,
                 hashlib.sha1)

    if not hmac.compare_digest(m.hexdigest(), sig):
        return HttpResponseBadRequest('Bad signature.')

    try:
        payload = json.loads(request.body.decode('utf-8'))
    except ValueError as e:
        logging.error('The payload is not in JSON format: %s', e)
        return HttpResponseBadRequest('Invalid payload format.')

    if 'commits' not in payload:
        return HttpResponseBadRequest('Invalid payload; expected "commits".')

    server_url = get_server_url(request=request)
    review_request_ids_to_commits = defaultdict(list)

    for commit in payload['commits']:
        commit_id = commit.get('id')
        commit_message = commit.get('message')
        review_request_id = get_review_request_id(
            commit_message, server_url, commit_id, repository)

        targets = commit['target']

        if 'tags' in targets and targets['tags']:
            target = targets['tags'][0]
        elif 'bookmarks' in targets and targets['bookmarks']:
            target = targets['bookmarks'][0]
        elif 'branch' in targets:
            target = targets['branch']
        else:
            target = ''

        if target:
            target_str = '%s (%s)' % (target, commit_id[:7])
        else:
            target_str = commit_id[:7]

        review_request_ids_to_commits[review_request_id].append(target_str)

    if review_request_ids_to_commits:
        close_all_review_requests(review_request_ids_to_commits,
                                  local_site_name,
                                  repository,
                                  hosting_service_id)

    return HttpResponse()


class ReviewBoardGatewayForm(HostingServiceForm):
    """Hosting service form for Review Board Gateway.

    Provide an additional field on top of the base hosting service form to
    allow specification of the repository name.
    """

    rbgateway_repo_name = forms.CharField(
        label=_('Repository name'),
        max_length=128,
        required=True,
        widget=forms.TextInput(attrs={'size': '60'}),
        help_text=_('The name of the repository. This is the name '
                    'specified in the configuration file for rb-gateway.'))


class ReviewBoardGatewayClient(HostingServiceClient):
    """Client interface to the RB Gateway API."""

    def __init__(self, *args, **kwargs):
        """Initialize the client.

        Args:
            *args (tuple):
                Positional arguments for the parent class.

            **kwargs (dict):
                Keyword arguments for the parent class.
        """
        super(ReviewBoardGatewayClient, self).__init__(*args, **kwargs)

        self.api_url = self.hosting_service.account.hosting_url

    def api_authenticate(self, username, password):
        """Authenticate against the RB Gateway server.

        This will attempt to authenticate with the given credentials. If
        successful, information on the session, including an API token for
        further API requests, will be returned.

        Args:
            username (unicode):
                The username to authenticate with.

            password (unicode):
                The password to authenticate with.

        Returns:
            dict:
            The new session information.

        Raises:
            reviewboard.hostingsvcs.errors.AuthorizationError:
                The credentials provided were not valid.

            reviewboard.hostingsvcs.errors.HostingServiceError:
                Error retrieving the file contents. There may be a more
                specific subclass raised. See :py:meth:`process_http_error`.

            reviewboard.scmtools.errors.UnverifiedCertificateError:
                The SSL certificate was not able to be verified.
        """
        try:
            response = self.http_post('%s/session' % self.api_url,
                                      username=username,
                                      password=password)

            return response.json
        except HostingServiceAPIError as e:
            if e.http_code == 404:
                raise HostingServiceAPIError(
                    ugettext('A Review Board Gateway server was not found at '
                             'the provided URL. Make sure you are providing '
                             'the root of the server, and not a path '
                             'within it.'))

            raise

    def api_get_repository(self, repo_name):
        """Return information on a repository.

        Args:
            repo_name (unicode):
                The name of the repository.

        Returns:
            dict:
            The repository information.

        Raises:
            reviewboard.hostingsvcs.errors.HostingServiceError:
                Error retrieving the file contents. There may be a more
                specific subclass raised. See :py:meth:`process_http_error`.

            reviewboard.scmtools.errors.UnverifiedCertificateError:
                The SSL certificate was not able to be verified.
        """
        url = '%s/path' % self._get_repos_api_url(repo_name)

        return self.http_get(url).json

    def api_get_file_contents(self, repo_name, revision, base_commit_id, path):
        """Return a file from a repository.

        This will perform an API request to fetch the contents of a file.

        Args:
            repo_name (unicode):
                The name of the repository registered on RB Gateway.

            path (unicode):
                The file path.

            revision (unicode):
                The revision of the file to retrieve.

            base_commit_id (unicode, optional):
                The ID of the commit that the file was changed in. This may
                not be provided, and is dependent on the type of repository.

        Returns:
            bytes:
            The contents of the file.

        Raises:
            reviewboard.hostingsvcs.errors.HostingServiceError:
                Error retrieving the file contents. There may be a more
                specific subclass raised. See :py:meth:`process_http_error`.

            reviewboard.scmtools.errors.FileNotFoundError:
                The file was not found.

            reviewboard.scmtools.errors.UnverifiedCertificateError:
                The SSL certificate was not able to be verified.
        """
        url = self._get_file_api_url(repo_name=repo_name,
                                     revision=revision,
                                     base_commit_id=base_commit_id,
                                     path=path)

        try:
            return self.http_get(url).data
        except HostingServiceError as e:
            if e.http_code == 404:
                raise FileNotFoundError(path, revision)

            raise

    def api_get_file_exists(self, repo_name, revision, base_commit_id,
                            path):
        """Return whether a file exists in a repository.

        This will perform an API request to fetch information on the file,
        using that to determine if the file exists.

        Args:
            repo_name (unicode):
                The name of the repository registered on RB Gateway.

            path (unicode):
                The file path.

            revision (unicode):
                The revision of the file.

            base_commit_id (unicode, optional):
                The ID of the commit that the file was changed in. This may
                not be provided, and is dependent on the type of repository.

        Returns:
            bool:
            ``True`` if the file exists. ``False`` if it does not.

        Raises:
            reviewboard.hostingsvcs.errors.HostingServiceError:
                Error retrieving the file information. There may be a more
                specific subclass raised. See :py:meth:`process_http_error`.

            reviewboard.scmtools.errors.UnverifiedCertificateError:
                The SSL certificate was not able to be verified.
        """
        url = self._get_file_api_url(repo_name=repo_name,
                                     revision=revision,
                                     base_commit_id=base_commit_id,
                                     path=path)

        try:
            self.http_head(url)
            return True
        except HostingServiceError as e:
            if e.http_code == 404:
                return False

            raise

    def api_get_branches(self, repo_name):
        """Return a list of branches for a repository.

        Args:
            repo_name (unicode):
                The name of the repository.

        Returns:
            list of dict:
            The list of branches in the repository.

        Raises:
            reviewboard.hostingsvcs.errors.HostingServiceError:
                Error retrieving the branch information. There may be a more
                specific subclass raised. See :py:meth:`process_http_error`.
        """
        url = self._get_branches_api_url(repo_name)

        return self.http_get(url).json

    def api_get_commits(self, repo_name, branch_name, start=None):
        """Return a list of commits for a repository.

        Args:
            repo_name (unicode):
                The name of the repository.

            branch_name (unicode):
                The name of the branch to list commits on.

            start (unicode, optional):
                The optional starting commit ID for the list. This is used
                for pagination purposes.

        Returns:
            list of dict:
            The list of commits in the repository.

        Raises:
            reviewboard.hostingsvcs.errors.HostingServiceError:
                Error retrieving the branch information. There may be a more
                specific subclass raised. See :py:meth:`process_http_error`.

            reviewboard.scmtools.errors.UnverifiedCertificateError:
                The SSL certificate was not able to be verified.
        """
        url = self._get_commits_api_url(repo_name, branch_name=branch_name)

        if start is not None:
            url = '%s?start=%s' % (url, start)

        return self.http_get(url).json

    def api_get_commit(self, repo_name, commit_id):
        """Return a commit at a given revision/commit ID.

        Args:
            repo_name (unicode):
                The name of the repository.

            revision (unicode):
                The revision/ID of the commit to fetch.

        Returns:
            dict:
            Information on the commit from the repository.

        Raises:
            reviewboard.hostingsvcs.errors.HostingServiceError:
                Error retrieving the branch information. There may be a more
                specific subclass raised. See :py:meth:`process_http_error`.

            reviewboard.scmtools.errors.UnverifiedCertificateError:
                The SSL certificate was not able to be verified.
        """
        url = self._get_commits_api_url(repo_name, commit_id)

        return self.http_get(url).json

    def get_http_credentials(self, account, username=None, password=None,
                             **kwargs):
        """Return credentials used to authenticate with RB Gateway.

        If a username and password is provided, this will authenticate using
        HTTP Basic Auth. This is needed for initially linking an account or
        updating credentials.

        If instead the account data contains a private token from a previous
        authentication request, it will be provided to RB Gateway through the
        :mailheader:`PRIVATE-TOKEN` header.

        Args:
            account (reviewboard.hostingsvcs.models.HostingServiceAccount):
                The stored authentication data for the account.

            username (unicode, optional):
                An explicit username passed by the caller. This will override
                the token stored in the account, if both a username and
                password are provided.

            password (unicode, optional):
                An explicit password passed by the caller. This will override
                the token stored in the account, if both a username and
                password are provided.

            **kwargs (dict, unused):
                Additional keyword arguments passed in when making the HTTP
                request.

        Returns:
            dict:
            A dictionary of credentials for the request.
        """
        if username is None and password is None:
            private_token = self.hosting_service.get_private_token()

            if private_token is not None:
                return {
                    'headers': {
                        'PRIVATE-TOKEN': private_token,
                    },
                }

        return super(ReviewBoardGatewayClient, self).get_http_credentials(
            account=account,
            username=username,
            password=password,
            **kwargs)

    def process_http_error(self, request, e):
        """Process an HTTP error, raising a result.

        This will look at the error, raising a more suitable exception
        in its place.

        Args:
            request (reviewboard.hostingsvcs.service.HostingServiceHTTPRequest,
                     unused):
                The request that resulted in an error.

            e (urllib2.URLError):
                The error to check.

        Raises:
            reviewboard.hostingsvcs.errors.AuthorizationError:
                The credentials provided were not valid.

            reviewboard.hostingsvcs.errors.HostingServiceAPIError:
                An error occurred communicating with the API. An unparsed
                payload is available.

            reviewboard.hostingsvcs.errors.HostingServiceError:
                There was an unexpected error performing the request.

            reviewboard.scmtools.errors.UnverifiedCertificateError:
                The SSL certificate was not able to be verified.
        """
        # Perform any default checks.
        super(ReviewBoardGatewayClient, self).process_http_error(request, e)

        if isinstance(e, HTTPError):
            code = e.getcode()

            if e.code == 401:
                raise AuthorizationError(
                    ugettext('The username or password is incorrect.'))
            elif e.code == 404:
                raise HostingServiceAPIError(
                    ugettext('The API endpoint was not found.'),
                    http_code=code)
            else:
                msg = e.read()

                raise HostingServiceAPIError(msg,
                                             http_code=code,
                                             rsp=msg)
        else:
            raise HostingServiceError(e.reason)

    def _get_repos_api_url(self, repo_name=None):
        """Return the API URL for working with repositories.

        Args:
            repo_name (unicode, optional):
                The optional name of a repository to include in the URL.

        Returns:
            unicode:
            The URL for working with a list of repositories or the specified
            repository.
        """
        url = '%s/repos' % self.api_url

        if repo_name is not None:
            url = '%s/%s' % (url, quote(repo_name))

        return url

    def _get_branches_api_url(self, repo_name, branch_name=None):
        """Return the API URL for branches on a repository.

        Args:
            repo_name (unicode):
                The name of the repository.

            branch_name (unicode, optional):
                The optional name of a branch to include in the URL.

        Returns:
            unicode:
            The URL for working with a list of branches or a specific branch.
        """
        url = '%s/branches' % self._get_repos_api_url(repo_name)

        if branch_name is not None:
            url = '%s/%s' % (url, quote(branch_name))

        return url

    def _get_commits_api_url(self, repo_name, commit_id=None,
                             branch_name=None):
        """Return the API URL for commits on a repository.

        Args:
            repo_name (unicode):
                The name of the repository.

            commit_id (unicode, optional):
                The optional commit ID to include in the URL.

            branch_name (unicode, optional):
                The optional branch to fetch commits from.

        Returns:
            unicode:
            The URL for working with a list of commits or a specific commit.
        """
        if branch_name is None or commit_id is not None:
            url = '%s/commits' % self._get_repos_api_url(repo_name)
        else:
            url = '%s/commits' % self._get_branches_api_url(repo_name,
                                                            branch_name)

        if commit_id is not None:
            url = '%s/%s' % (url, quote(commit_id))

        return url

    def _get_file_api_url(self, repo_name, revision, base_commit_id=None,
                          path=None):
        """Return the URL for accessing information about a file.

        A revision or a (base commit ID, path) pair is expected to be provided.
        By default, this will return the URL based on the revision, if both
        are provided.

        Args:
            repo_name (unicode):
                The name of the repository registered on RB Gateway.

            revision (unicode):
                The revision of the file to retrieve.

            base_commit_id (unicode, optional):
                The ID of the commit that the file was changed in. This may
                not be provided, and is dependent on the type of repository.

            path (unicode, optional):
                The file path.

        Returns:
            unicode:
            The URL for fetching file information.
        """
        if revision and revision != UNKNOWN:
            return ('%s/file/%s'
                    % (self._get_repos_api_url(repo_name), quote(revision)))
        else:
            return ('%s/path/%s'
                    % (self._get_commits_api_url(repo_name, base_commit_id),
                       quote(path)))


class ReviewBoardGateway(HostingService):
    """Hosting service support for Review Board Gateway.

    Review Board Gateway is a lightweight self-installed source hosting service
    that provides an API around self-hosted source code repositories.

    More information can be found at
    https://www.reviewboard.org/downloads/rbgateway/
    """

    name = 'Review Board Gateway'

    client_class = ReviewBoardGatewayClient
    form = ReviewBoardGatewayForm

    self_hosted = True
    needs_authorization = True
    supports_repositories = True
    supports_post_commit = True
    supported_scmtools = ['Git', 'Mercurial']

    has_repository_hook_instructions = True

    repository_fields = {
        'Git': {
            'path': '%(hosting_url)s/repos/%(rbgateway_repo_name)s/path',
        },
        'Mercurial': {
            'path': '%(hosting_url)s/repos/%(rbgateway_repo_name)s/path',
        },
    }

    repository_url_patterns = [
        url(r'^hooks/close-submitted/$',
            hook_close_submitted,
            name='rbgateway-hooks-close-submitted'),
    ]

    def check_repository(self, rbgateway_repo_name, *args, **kwargs):
        """Checks the validity of a repository configuration.

        Args:
            rbgateway_repo_name (unicode):
                The name of the repository to check.

            *args (tuple, unused):
                Unused positional arguments.

            **kwargs (dict, unused):
                Unused dictionary arguments.

        Raises:
            reviewboard.hostingsvcs.errors.RepositoryError:
                The repository is not valid.

            reviewboard.scmtools.errors.RepositoryNotFoundError:
                The repository was not found.
        """
        try:
            self.client.api_get_repository(rbgateway_repo_name)
        except HostingServiceAPIError as e:
            if e.http_code == 404:
                raise RepositoryNotFoundError()

            raise

    def authorize(self, username, password, *args, **kwargs):
        """Authorize an account on the RB Gateway service.

        This will perform an authentication request against the API. If
        successful, the generated API token will be stored, encrypted, for
        future requests to the API.

        Args:
            username (unicode):
                The username for the account.

            password (unicode):
                The password for the account.

            *args (tuple, unused):
                Unused positional arguments.

            **kwargs (dict, unused):
                Unused keyword arguments.

        Raises:
            reviewboard.hostingsvcs.errors.HostingServiceError:
                Error retrieving the branch information. There may be a more
                specific subclass raised.
        """
        auth_data = self.client.api_authenticate(username, password)

        self.account.data['private_token'] = \
            encrypt_password(auth_data['private_token'])
        self.account.save()

    def is_authorized(self):
        """Return if the account has a stored auth token.

        This will check if we have previously stored a private token for the
        account. It does not validate that the token still works.
        """
        return 'private_token' in self.account.data

    def get_private_token(self):
        """Return the private token used for authentication.

        Returns:
            unicode:
            The private token, or ``None`` if one wasn't set.
        """
        private_token = self.account.data.get('private_token')

        if not private_token:
            return None

        return decrypt_password(private_token)

    def get_file(self, repository, path, revision, base_commit_id, *args,
                 **kwargs):
        """Return a file from a repository.

        This will perform an API request to fetch the contents of a file.

        Args:
            repository (reviewboard.scmtools.models.Repository):
                The repository to retrieve the file from.

            path (unicode):
                The file path.

            revision (unicode):
                The revision the file should be retrieved from.

            base_commit_id (unicode):
                The ID of the commit that the file was changed in. This may
                not be provided, and is dependent on the type of repository.

            *args (tuple, unused):
                Additional positional arguments.

            **kwargs (dict, unused):
                Additional keyword arguments.

        Returns:
            bytes:
            The contents of the file.

        Raises:
            reviewboard.hostingsvcs.errors.HostingServiceError:
                Error retrieving the branch information. There may be a more
                specific subclass raised.

            reviewboard.scmtools.errors.FileNotFoundError:
                The file could not be found.
        """
        return self.client.api_get_file_contents(
            repo_name=self._get_repo_name(repository),
            revision=revision,
            base_commit_id=base_commit_id,
            path=path)

    def get_file_exists(self, repository, path, revision, base_commit_id,
                        *args, **kwargs):
        """Return whether a file exists in a repository.

        This will perform an API request to fetch information on the file,
        using that to determine if the file exists.

        Args:
            repository (reviewboard.scmtools.models.Repository):
                The repository to retrieve the file from.

            path (unicode):
                The file path.

            revision (unicode):
                The revision the file should be retrieved from.

            base_commit_id (unicode):
                The ID of the commit that the file was changed in. This may
                not be provided, and is dependent on the type of repository.

            *args (tuple, unused):
                Additional positional arguments.

            **kwargs (dict, unused):
                Additional keyword arguments.

        Returns:
            bool:
            ``True`` if the file exists. ``False`` if it does not.

        Raises:
            reviewboard.hostingsvcs.errors.HostingServiceError:
                Error retrieving the branch information. There may be a more
                specific subclass raised.
        """
        return self.client.api_get_file_exists(
            repo_name=self._get_repo_name(repository),
            revision=revision,
            base_commit_id=base_commit_id,
            path=path)

    def get_branches(self, repository):
        """Return the branches for the repository.

        Args:
            repository (reviewboard.scmtools.models.Repository):
                The repository to fetch branches for.

        Returns:
            list of reviewboard.scmtools.core.Branch:
            The branches returned for the repository.

        Raises:
            reviewboard.hostingsvcs.errors.HostingServiceError:
                Error retrieving the branch information. There may be a more
                specific subclass raised.
        """
        repo_name = self._get_repo_name(repository)
        tool_name = repository.scmtool_class.name

        if tool_name == 'Git':
            default_branch = 'master'
        elif tool_name == 'Mercurial':
            default_branch = 'default'
        else:
            default_branch = None

        return [
            Branch(id=branch_info['name'],
                   commit=branch_info['id'],
                   default=(branch_info['name'] == default_branch))
            for branch_info in self.client.api_get_branches(repo_name)
        ]

    def get_commits(self, repository, branch, start=None):
        """Return a list of commits for a repository.

        Args:
            repository (reviewboard.scmtools.models.Repository):
                The repository to fetch commits on.

            branch (unicode):
                The name of the branch to list commits on.

            start (unicode, optional):
                The optional starting commit ID for the list. This is used
                for pagination purposes.

        Returns:
            list of reviewboard.scmtools.core.Commit:
            The list of commits in the repository.

        Raises:
            reviewboard.hostingsvcs.errors.HostingServiceError:
                Error retrieving the branch information. There may be a more
                specific subclass raised.
        """
        repo_name = self._get_repo_name(repository)

        return [
            Commit(author_name=commit_info['author'],
                   id=commit_info['id'],
                   date=commit_info['date'],
                   message=commit_info['message'],
                   parent=commit_info['parent_id'])
            for commit_info in self.client.api_get_commits(repo_name, branch)
        ]

    def get_change(self, repository, revision):
        """Return a commit at a given revision/commit ID.

        Args:
            repository (reviewboard.scmtools.models.Repository):
                The repository to fetch the commit from.

            revision (unicode):
                The revision/ID of the commit to fetch.

        Returns:
            reviewboard.scmtools.core.Commit:
            The commit from the repository.

        Raises:
            reviewboard.hostingsvcs.errors.HostingServiceError:
                Error retrieving the branch information. There may be a more
                specific subclass raised.
        """
        repo_name = self._get_repo_name(repository)
        commit_info = self.client.api_get_commit(repo_name, revision)

        return Commit(author_name=commit_info['author'],
                      id=commit_info['id'],
                      date=commit_info['date'],
                      message=commit_info['message'],
                      parent=commit_info['parent_id'],
                      diff=commit_info['diff'].encode('utf-8'))

    def get_repository_hook_instructions(self, request, repository):
        """Returns instructions for setting up incoming webhooks.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            repository (reviewboard.scmtools.models.Repository):
                The repository to show instructions for.

        Returns:
            django.http.HttpResponse:
            The hook installation instructions rendered to the contents of an
            HTTP response.
        """
        example_id = 123
        example_url = build_server_url(local_site_reverse(
            'review-request-detail',
            local_site=repository.local_site,
            kwargs={
                'review_request_id': example_id,
            }))

        hook_uuid = repository.get_or_create_hooks_uuid()
        close_url = build_server_url(local_site_reverse(
            'rbgateway-hooks-close-submitted',
            kwargs={
                'repository_id': repository.pk,
                'hosting_service_id': 'rbgateway',
            },
            local_site=repository.local_site))

        return render_to_string(
            template_name='hostingsvcs/rb-gateway/repo_hook_instructions.html',
            request=request,
            context={
                'example_id': example_id,
                'example_url': example_url,
                'hook_uuid': hook_uuid,
                'close_url': close_url,
                'repo_name': repository.extra_data['rbgateway_repo_name'],
            })

    def _get_repo_name(self, repository):
        """Return the stored API name for the repository.

        Args:
            repository (reviewboard.scmtools.models.Repository):
                The repository to return the API name for.

        Returns:
            unicode:
            The API name for the repository.
        """
        return repository.extra_data['rbgateway_repo_name']
