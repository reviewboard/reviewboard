from __future__ import unicode_literals

import hashlib
import hmac
import json
import logging
from collections import defaultdict

from django import forms
from django.conf.urls import url
from django.http import HttpResponse, HttpResponseBadRequest
from django.template.context import RequestContext
from django.template.loader import render_to_string
from django.utils import six
from django.utils.six.moves.urllib.error import HTTPError, URLError
from django.utils.translation import ugettext_lazy as _, ugettext

from reviewboard.admin.server import build_server_url, get_server_url
from reviewboard.hostingsvcs.errors import (AuthorizationError,
                                            HostingServiceError)
from reviewboard.hostingsvcs.forms import HostingServiceForm
from reviewboard.hostingsvcs.hook_utils import (close_all_review_requests,
                                                get_repository_for_hook,
                                                get_review_request_id)
from reviewboard.hostingsvcs.service import HostingService
from reviewboard.scmtools.core import Branch, Commit, UNKNOWN
from reviewboard.scmtools.crypto_utils import (decrypt_password,
                                               encrypt_password)
from reviewboard.scmtools.errors import FileNotFoundError, SCMError
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
    m = hmac.new(bytes(repository.get_or_create_hooks_uuid()),
                 request.body, hashlib.sha1)

    if not hmac.compare_digest(m.hexdigest(), sig):
        return HttpResponseBadRequest('Bad signature.')

    try:
        payload = json.loads(request.body)
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


class ReviewBoardGateway(HostingService):
    """Hosting service support for Review Board Gateway.

    Review Board Gateway is a lightweight self-installed source hosting service
    that currently supports Git repositories.
    """

    name = 'Review Board Gateway'
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

    def check_repository(self, path, *args, **kwargs):
        """Check whether the repository exists."""
        self._api_get(path)

    def authorize(self, username, password, hosting_url, *args, **kwargs):
        """Authorize the Review Board Gateway repository.

        Review Board Gateway uses HTTP Basic Auth, so this will store the
        provided password, encrypted, for use in later API requests.

        Similar to GitLab's API, Review Board Gateway will return a private
        token on session authentication.
        """
        try:
            data, headers = self.client.json_post(
                url=hosting_url + '/session',
                username=username,
                password=password)
        except HTTPError as e:
            if e.code == 401:
                raise AuthorizationError(
                    ugettext('The username or password is incorrect.'))
            elif e.code == 404:
                raise HostingServiceError(
                    ugettext('A Review Board Gateway server was not found at '
                             'the provided URL.'))
            else:
                logger.exception('Failed authorization at %s/session: %s',
                                 hosting_url, e)
            raise

        self.account.data['private_token'] = \
            encrypt_password(data['private_token'])
        self.account.save()

    def is_authorized(self):
        """Determine if the account has supported authorization tokens.

        This will check if we have previously stored a private token for the
        account. It does not validate that the token still works.
        """
        return 'private_token' in self.account.data

    def get_file(self, repository, path, revision, base_commit_id, *args,
                 **kwargs):
        """Get a file from ReviewBoardGateway.

        This will perform an API request to fetch the contents of a file.
        """
        url = self._get_file_url(repository, revision, base_commit_id, path)

        try:
            data, is_new = self._api_get(url)
            return data
        except (HTTPError, URLError) as e:
            if e.code == 404:
                raise FileNotFoundError(path, revision)
            else:
                logger.exception('Failed to get file from %s: %s', url, e)
                raise SCMError(six.text_type(e))

    def get_file_exists(self, repository, path, revision, base_commit_id,
                        *args, **kwargs):
        """Check whether a file exists in ReviewBoardGateway.

        This will perform an API request to fetch the meta_data of a file.
        """
        url = self._get_file_url(repository, revision, base_commit_id, path)

        try:
            self._api_head(url)
            return True
        except (HTTPError, URLError) as e:
            if e.code == 404:
                return False
            else:
                logger.exception('Failed to get file exists from %s: %s',
                                 url, e)
                raise SCMError(six.text_type(e))

    def get_branches(self, repository):
        """Return the branches for the repository.

        Args:
            repository (reviewboard.scmtools.models.Repository):
                The repository to fetch branches for.

        Returns:
            list of reviewboard.scmtools.core.Branch:
            The branches returned from the Review Board Gateway API.

        Raises:
            SCMError:
                The branches could not be retrieved from Review Board Gateway.
        """
        url = ('%s/repos/%s/branches' %
               (self.account.hosting_url,
                repository.extra_data['rbgateway_repo_name']))

        tool_name = repository.scmtool_class.name

        if tool_name == 'Git':
            default_branch = 'master'
        elif tool_name == 'Mercurial':
            default_branch = 'default'
        else:
            raise SCMError('Review Board Gateway does not support %s',
                           tool_name)

        try:
            data, headers = self._api_get(url)
            branches = json.loads(data)

            results = []

            for branch in branches:
                results.append(Branch(
                    id=branch['name'],
                    commit=branch['id'],
                    default=(branch['name'] == default_branch)
                ))

            return results
        except Exception as e:
            logger.exception('Failed to get branches from %s: %s', url, e)
            raise SCMError(six.text_type(e))

    def get_commits(self, repository, branch=None, start=None):
        if start is not None:
            url = ('%s/repos/%s/branches/%s/commits?start=%s'
                   % (self.account.hosting_url,
                      repository.extra_data['rbgateway_repo_name'],
                      branch,
                      start))
        else:
            url = ('%s/repos/%s/branches/%s/commits'
                   % (self.account.hosting_url,
                      repository.extra_data['rbgateway_repo_name'],
                      branch))

        try:
            data, headers = self._api_get(url)
            commits = json.loads(data)

            results = []

            for commit in commits:
                results.append(Commit(commit['author'],
                                      commit['id'],
                                      commit['date'],
                                      commit['message'],
                                      commit['parent_id']))

            return results
        except Exception as e:
            logger.exception('Failed to fetch commits from %s: %s', url, e)
            raise SCMError(six.text_type(e))

    def get_change(self, repository, revision):
        url = ('%s/repos/%s/commits/%s'
               % (self.account.hosting_url,
                  repository.extra_data['rbgateway_repo_name'],
                  revision))

        try:
            data, headers = self._api_get(url)
            commit = json.loads(data)

            return Commit(commit['author'],
                          commit['id'],
                          commit['date'],
                          commit['message'],
                          commit['parent_id'],
                          diff=commit['diff'])

        except Exception as e:
            logger.exception('Failed to fetch commit change from %s: %s',
                             url, e)
            raise SCMError(six.text_type(e))

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
            'hostingsvcs/rb-gateway/repo_hook_instructions.html',
            RequestContext(request, {
                'example_id': example_id,
                'example_url': example_url,
                'hook_uuid': hook_uuid,
                'close_url': close_url,
                'repo_name': repository.extra_data['rbgateway_repo_name'],
            }))

    def _get_file_url(self, repository, revision, base_commit_id=None,
                      path=None):
        """Get the URL for accessing the contents of a file.

        A revision or a base commit id, path pair is expected to be provided.
        By default, this will return the URL based on the revision, if both
        are provided.
        """
        if revision and revision != UNKNOWN:
            return ('%s/repos/%s/file/%s'
                    % (self.account.hosting_url,
                       repository.extra_data['rbgateway_repo_name'],
                       revision))
        else:
            return ('%s/repos/%s/commits/%s/path/%s'
                    % (self.account.hosting_url,
                       repository.extra_data['rbgateway_repo_name'],
                       base_commit_id,
                       path))

    def _api_get(self, url):
        """Make a GET request to the Review Board Gateway API.

        Delegate to the client's http_get function but first add a
        PRIVATE-TOKEN in the header for authentication.
        """
        try:
            data, headers = self.client.http_get(
                url,
                headers={
                    'PRIVATE-TOKEN': self._get_private_token(),
                })

            return data, headers
        except HTTPError as e:
            if e.code == 401:
                raise AuthorizationError(
                    ugettext('The username or password is incorrect.'))
            elif e.code == 404:
                raise
            else:
                logger.exception('Failed to execute a GET request at %s: %s',
                                 url, e)
                raise

    def _api_head(self, url):
        """Make a HEAD request to the Review Board Gateway API.

        Delegate to the client's http_request function using the method
        HEAD but first add a PRIVATE-TOKEN in the header for authentication.
        """
        try:
            data, headers = self.client.http_request(
                url,
                headers={
                    'PRIVATE-TOKEN': self._get_private_token(),
                },
                method='HEAD')

            return headers
        except HTTPError as e:
            if e.code == 401:
                raise AuthorizationError(
                    ugettext('The username or password is incorrect.'))
            elif e.code == 404:
                raise
            else:
                logger.exception('Failed to execute a HEAD request at %s: %s',
                                 url, e)
                raise

    def _get_private_token(self):
        """Return the private token used for authentication."""
        return decrypt_password(self.account.data['private_token'])
