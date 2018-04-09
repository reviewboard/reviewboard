from __future__ import unicode_literals

import json

from django import forms
from django.utils import six
from django.utils.six.moves.urllib.error import HTTPError, URLError
from django.utils.six.moves.urllib.parse import quote
from django.utils.translation import ugettext, ugettext_lazy as _

from reviewboard.hostingsvcs.errors import (AuthorizationError,
                                            RepositoryError)
from reviewboard.hostingsvcs.forms import HostingServiceForm
from reviewboard.hostingsvcs.service import HostingService
from reviewboard.scmtools.crypto_utils import (decrypt_password,
                                               encrypt_password)
from reviewboard.scmtools.errors import FileNotFoundError


class UnfuddleForm(HostingServiceForm):
    unfuddle_account_domain = forms.CharField(
        label=_('Unfuddle account domain'),
        max_length=64,
        required=True,
        widget=forms.TextInput(attrs={'size': '60'}),
        help_text=_('This is the <tt>domain</tt> part of '
                    '<tt>domain.unfuddle.com</tt>'))

    unfuddle_project_id = forms.CharField(
        label=_('Unfuddle project ID'),
        max_length=64,
        required=True,
        widget=forms.TextInput(attrs={'size': '5'}),
        initial=1,
        help_text=_('This is the numeric project ID found in the URL '
                    'on your Project page (for example, '
                    'https://myaccount.unfuddle.com/a#/projects/'
                    '<b>&lt;id&gt;</b>)'))

    unfuddle_repo_name = forms.CharField(
        label=_('Repository name'),
        max_length=64,
        required=True,
        widget=forms.TextInput(attrs={'size': '60'}))


class Unfuddle(HostingService):
    """Hosting service support for Unfuddle.

    Unfuddle is a source hosting service that supports Git and Subversion
    repositories. It's available at https://unfuddle.com/.
    """
    name = 'Unfuddle'

    needs_authorization = True
    supports_bug_trackers = True
    supports_repositories = True
    supported_scmtools = ['Git', 'Subversion']

    bug_tracker_field = (
        'https://%(unfuddle_account_domain)s.unfuddle.com/a#/projects/'
        '%(unfuddle_project_id)s/tickets/by_number/%%s'
    )

    form = UnfuddleForm
    repository_fields = {
        'Git': {
            'path': 'git@%(unfuddle_account_domain)s.unfuddle.com:'
                    '%(unfuddle_account_domain)s/%(unfuddle_repo_name)s.git',
            'mirror_path': 'https://%(unfuddle_account_domain)s.unfuddle.com'
                           '/git/%(unfuddle_account_domain)s_'
                           '%(unfuddle_repo_name)s/',
        },
        'Subversion': {
            'path': 'https://%(unfuddle_account_domain)s.unfuddle.com/svn/'
                    '%(unfuddle_account_domain)s_%(unfuddle_repo_name)s',
            'mirror_path': 'http://%(unfuddle_account_domain)s.unfuddle.com'
                           '/svn/%(unfuddle_account_domain)s_'
                           '%(unfuddle_repo_name)s',
        },
    }

    # Maps Unfuddle "system" names to SCMTool names.
    TOOL_NAME_MAP = {
        'git': 'Git',
        'svn': 'Subversion',
    }

    def check_repository(self, unfuddle_account_domain=None,
                         unfuddle_repo_name=None, tool_name=None,
                         *args, **kwargs):
        """Checks the validity of a repository.

        This will perform an API request against Unfuddle to get
        information on the repository. This will throw an exception if
        the repository was not found, and return cleanly if it was found.
        """
        self._api_get_repository(unfuddle_account_domain, unfuddle_repo_name,
                                 tool_name)

    def authorize(self, username, password, unfuddle_account_domain=None,
                  *args, **kwargs):
        """Authorizes the Unfuddle repository.

        Unfuddle uses HTTP Basic Auth for the API, so this will store the
        provided password, encrypted, for use in later API requests.
        """
        # This will raise an exception if it fails, which the form will
        # catch.
        self._api_get(
            self._build_api_url(unfuddle_account_domain, 'account/'),
            username=username,
            password=password)

        self.account.data['password'] = encrypt_password(password)
        self.account.save()

    def is_authorized(self):
        """Determines if the account has supported authorization tokens.

        This just checks if there's a password set on the account.
        """
        return self.account.data.get('password', None) is not None

    def get_password(self):
        """Returns the password for this account.

        This is needed for API calls and for Subversion.
        """
        return decrypt_password(self.account.data['password'])

    def get_file(self, repository, path, revision, base_commit_id=None,
                 *args, **kwargs):
        """Fetches a file from Unfuddle.

        This will perform an API request to fetch the contents of a file.

        If using Git, this will expect a base commit ID to be provided.
        """
        try:
            commit_id = self._get_commit_id(repository, path, revision,
                                            base_commit_id)

            url = self._build_api_url(
                self._get_repository_account_domain(repository),
                'repositories/%s/download/?path=%s&commit=%s'
                % (self._get_repository_id(repository),
                   quote(path), quote(commit_id)))

            return self._api_get(url, raw_content=True)
        except (HTTPError, URLError):
            raise FileNotFoundError(path, revision)

    def get_file_exists(self, repository, path, revision, base_commit_id=None,
                        *args, **kwargs):
        """Determines if a file exists.

        This will perform an API request to fetch the metadata for a file.

        If using Git, this will expect a base commit ID to be provided.
        """
        try:
            commit_id = self._get_commit_id(repository, path, revision,
                                            base_commit_id)

            url = self._build_api_url(
                self._get_repository_account_domain(repository),
                'repositories/%s/history/?path=%s&commit=%s&count=0'
                % (self._get_repository_id(repository),
                   quote(path), quote(commit_id)))

            self._api_get(url)

            return True
        except (HTTPError, URLError, FileNotFoundError):
            return False

    def _get_commit_id(self, repository, path, revision, base_commit_id):
        # If a base commit ID is provided, use it. It may not be provided,
        # though, and in this case, we need to use the provided revision,
        # which will work for Subversion but not for Git.
        #
        # If not provided, and using Git, we'll give the user a File Not
        # Found error with some info on what they need to do to correct
        # this.
        if base_commit_id:
            revision = base_commit_id
        elif repository.tool.name == 'Git':
            raise FileNotFoundError(
                path,
                revision,
                detail='The necessary revision information needed to find '
                       'this file was not provided. Use RBTools 0.5.2 or '
                       'newer.')

        return revision

    def _api_get_repository(self, account_domain, repository_name, tool_name):
        url = self._build_api_url(account_domain, 'repositories/')

        # Let the exception bubble up.
        results = self._api_get(url)

        for repo in results:
            if repo['abbreviation'] == repository_name:
                unfuddle_tool_name = self.TOOL_NAME_MAP.get(repo['system'])

                if unfuddle_tool_name == tool_name:
                    return repo

        raise RepositoryError(
            ugettext('A repository with this name was not found'))

    def _build_api_url(self, account_domain, url):
        return 'https://%s.unfuddle.com/api/v1/%s' % (account_domain, url)

    def _get_repository_id(self, repository):
        key = 'unfuddle_repo_id'

        if key not in repository.extra_data:
            repo = self._api_get_repository(
                self._get_repository_account_domain(repository),
                self._get_repository_name(repository),
                repository.tool.name)

            repository.extra_data[key] = repo['id']
            repository.save()

        return repository.extra_data[key]

    def _get_repository_account_domain(self, repository):
        return repository.extra_data['unfuddle_account_domain']

    def _get_repository_name(self, repository):
        return repository.extra_data['unfuddle_repo_name']

    def _api_get(self, url, raw_content=False, username=None, password=None):
        try:
            data, headers = self.client.http_get(
                url,
                username=username or self.account.username,
                password=password or self.get_password(),
                headers={
                    'Accept': 'application/json',
                })

            if raw_content:
                return data
            else:
                return json.loads(data)
        except HTTPError as e:
            if e.code == 401:
                raise AuthorizationError(
                    ugettext('The login or password is incorrect.'))

            raise
