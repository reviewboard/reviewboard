from __future__ import unicode_literals

import json
import logging

from django import forms
from django.utils import six
from django.utils.six.moves.urllib.error import HTTPError, URLError
from django.utils.translation import ugettext_lazy as _, ugettext

from reviewboard.hostingsvcs.errors import (AuthorizationError,
                                            HostingServiceError)
from reviewboard.hostingsvcs.forms import HostingServiceForm
from reviewboard.hostingsvcs.service import HostingService
from reviewboard.scmtools.crypto_utils import (decrypt_password,
                                               encrypt_password)
from reviewboard.scmtools.core import Branch, Commit
from reviewboard.scmtools.errors import FileNotFoundError, SCMError


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
    supported_scmtools = ['Git']

    repository_fields = {
        'Git': {
            'path': '%(hosting_url)s/repos/%(rbgateway_repo_name)s/path'
        }
    }

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
            if e.code == 404:
                raise HostingServiceError(
                    ugettext('A Review Board Gateway server was not found at '
                             'the provided URL.'))
            elif e.code == 401:
                raise AuthorizationError(
                    ugettext('The username or password is incorrect.'))
            else:
                logging.warning('Failed authorization at %s: %s',
                                hosting_url + '/session', e, exc_info=1)
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
                logging.warning('Failed to get file from %s: %s',
                                url, e, exc_info=1)
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
                logging.warning('Failed to get file exists from %s: %s',
                                url, e, exc_info=1)
                raise SCMError(six.text_type(e))

    def get_branches(self, repository):
        url = ('%s/repos/%s/branches' %
               (self.account.hosting_url,
                repository.extra_data['rbgateway_repo_name']))

        try:
            data, headers = self._api_get(url)
            branches = json.loads(data)

            results = []

            for branch in branches:
                results.append(Branch(id=branch['name'],
                                      commit=branch['id'],
                                      default=(branch['name'] == 'master')))

            return results
        except Exception as e:
            logging.warning('Failed to get branches from %s: %s',
                            url, e, exc_info=1)
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
            logging.warning('Failed to fetch commits from %s: %s',
                            url, e, exc_info=1)
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
            logging.warning('Failed to fetch commit change from %s: %s',
                            url, e, exc_info=1)
            raise SCMError(six.text_type(e))

    def _get_file_url(self, repository, revision, base_commit_id=None,
                      path=None):
        """Get the URL for accessing the contents of a file.

        A revision or a base commit id, path pair is expected to be provided.
        By default, this will return the URL based on the revision, if both
        are provided.
        """
        if revision:
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
                    ugettext('The login or password is incorrect.'))
            elif e.code == 404:
                raise
            else:
                logging.warning('Failed to execute a GET request at %s: %s',
                                url, e, exc_info=1)
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
                    ugettext('The login or password is incorrect.'))
            elif e.code == 404:
                raise
            else:
                logging.warning('Failed to execute a HEAD request at %s: %s',
                                url, e, exc_info=1)
                raise

    def _get_private_token(self):
        """Return the private token used for authentication."""
        return decrypt_password(self.account.data['private_token'])
