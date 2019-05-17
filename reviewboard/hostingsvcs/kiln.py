from __future__ import unicode_literals

import binascii
import json

from django import forms
from django.utils import six
from django.utils.six.moves.urllib.error import HTTPError, URLError
from django.utils.translation import ugettext, ugettext_lazy as _

from reviewboard.hostingsvcs.errors import (AuthorizationError,
                                            HostingServiceError,
                                            RepositoryError)
from reviewboard.hostingsvcs.forms import HostingServiceForm
from reviewboard.hostingsvcs.service import (HostingService,
                                             HostingServiceClient)
from reviewboard.scmtools.errors import FileNotFoundError


class KilnForm(HostingServiceForm):
    kiln_account_domain = forms.CharField(
        label=_('Account domain'),
        max_length=64,
        required=True,
        help_text=_('The domain used for your Kiln site, as in '
                    'https://&lt;domain&gt;.kilnhg.com/'),
        widget=forms.TextInput(attrs={'size': '60'}))

    kiln_project_name = forms.CharField(
        label=_('Project name'),
        initial='Repositories',
        max_length=64,
        required=True,
        help_text=_('The Kiln project name. Defaults to "Repositories".'),
        widget=forms.TextInput(attrs={'size': '60'}))

    kiln_group_name = forms.CharField(
        label=_('Group name'),
        initial='Group',
        max_length=64,
        required=True,
        help_text=_('The Kiln group name. Defaults to "Group".'),
        widget=forms.TextInput(attrs={'size': '60'}))

    kiln_repo_name = forms.CharField(
        label=_('Repository name'),
        max_length=64,
        required=True,
        widget=forms.TextInput(attrs={'size': '60'}))


class KilnAPIError(HostingServiceError):
    """Represents one or more errors from a Kiln API request.

    Kiln API responses can contain multiple errors, containing both
    string-based error codes and error text. KilnAPIError stores a
    mapping of provided error codes to error text as an 'errors'
    attribute.

    All error text is joined together with '; ' when displaying the error.
    """
    def __init__(self, errors):
        super(KilnAPIError, self).__init__('; '.join([
            error['sError']
            for error in errors
        ]))

        self.errors = dict([
            (error['codeError'], error['sError'])
            for error in errors
        ])


class KilnClient(HostingServiceClient):
    """Interfaces with the Kiln 1.0 API."""
    def __init__(self, hosting_service):
        super(KilnClient, self).__init__(hosting_service)

        self.account = hosting_service.account

    def get_base_api_url(self):
        return 'https://%s.kilnhg.com/Api/1.0/' % (
            self.account.data['kiln_account_domain'])

    def login(self, username, password):
        return self.api_post('Auth/Login', fields={
            'sUser': username,
            'sPassword': password,
        })

    def get_projects(self):
        return self.api_get('Project')

    def get_raw_file(self, repository_id, path, revision):
        return self.api_get('Repo/%s/Raw/File/%s?rev=%s'
                            % (repository_id, self._hex_encode(path),
                               revision),
                            raw_content=True)

    #
    # API wrappers around HTTP/JSON methods
    #

    def api_delete(self, url, *args, **kwargs):
        try:
            data = self.http_delete(self._build_api_url(url),
                                    *args, **kwargs).json
            self._check_api_error(data)

            return data
        except (URLError, HTTPError) as e:
            self._check_api_error_from_exception(e)

    def api_get(self, url, raw_content=False, *args, **kwargs):
        try:
            response = self.http_get(self._build_api_url(url), *args, **kwargs)

            if raw_content:
                data = response.data
            else:
                data = response.json

            self._check_api_error(data, raw_content=raw_content)

            return data
        except (URLError, HTTPError) as e:
            self._check_api_error_from_exception(e)

    def api_post(self, url, *args, **kwargs):
        try:
            data = self.http_post(self._build_api_url(url),
                                  *args, **kwargs).json
            self._check_api_error(data)

            return data
        except (URLError, HTTPError) as e:
            self._check_api_error_from_exception(e)

    #
    # Internal utilities
    #

    def _build_api_url(self, path):
        url = '%s%s' % (self.get_base_api_url(), path)

        if 'auth_token' in self.account.data:
            if '?' in path:
                url += '&'
            else:
                url += '?'

            url += 'token=%s' % self.account.data['auth_token']

        return url

    def _hex_encode(self, s):
        if isinstance(s, six.text_type):
            s = s.encode('utf-8')

        return binascii.hexlify(s).decode('utf-8').upper()

    def _check_api_error_from_exception(self, e):
        self._check_api_error(e.read(), raw_content=True)

        # No error was raised, so raise a default one.
        raise HostingServiceError(six.text_type(e))

    def _check_api_error(self, rsp, raw_content=False):
        if raw_content:
            try:
                rsp = json.loads(rsp)
            except:
                rsp = None

        if rsp and 'errors' in rsp:
            # Look for certain errors.
            for error_info in rsp['errors']:
                if error_info['codeError'] in ('BadAuthentication',
                                               'InvalidToken'):
                    raise AuthorizationError(error_info['sError'])

            raise KilnAPIError(rsp['errors'])


class Kiln(HostingService):
    """Hosting service support for Kiln On Demand.

    Kiln On Demand supports Git and Mercurial repositories, accessible
    over its API.

    Bug tracker integration is not provided by Kiln. FogBugz is used for
    that purpose instead.
    """
    name = _('Kiln On Demand')

    needs_authorization = True
    supports_repositories = True
    supported_scmtools = ['Git', 'Mercurial']

    form = KilnForm
    client_class = KilnClient

    repository_fields = {
        'Git': {
            'path': 'https://%(kiln_account_domain)s.kilnhg.com/Code/'
                    '%(kiln_project_name)s/%(kiln_group_name)s/'
                    '%(kiln_repo_name)s.git',
            'mirror_path': 'ssh://%(kiln_account_domain)s@'
                           '%(kiln_account_domain)s.kilnhg.com/'
                           '%(kiln_project_name)s/%(kiln_group_name)s/'
                           '%(kiln_repo_name)s',
        },
        'Mercurial': {
            'path': 'https://%(kiln_account_domain)s.kilnhg.com/Code/'
                    '%(kiln_project_name)s/%(kiln_group_name)s/'
                    '%(kiln_repo_name)s',
            'mirror_path': 'ssh://%(kiln_account_domain)s@'
                           '%(kiln_account_domain)s.kilnhg.com/'
                           '%(kiln_project_name)s/%(kiln_group_name)s/'
                           '%(kiln_repo_name)s',
        },
    }

    def check_repository(self, kiln_account_domain=None,
                         kiln_project_name=None, kiln_group_name=None,
                         kiln_repo_name=None, *args, **kwargs):
        """Checks the validity of a repository.

        This will check to see if there's a repository accessible to the
        user matching the provided information. This will throw an exception
        if the repository was not found, and return cleanly if it was found.
        """
        repo_info = self._find_repository_info(kiln_project_name,
                                               kiln_group_name,
                                               kiln_repo_name)

        if not repo_info:
            raise RepositoryError(ugettext(
                'The repository with this project, group, and name was not '
                'found. Please verify that the information exactly matches '
                'the configuration on Kiln.'))

    def authorize(self, username, password, kiln_account_domain,
                  *args, **kwargs):
        """Authorizes the Kiln repository.

        Kiln requires an authentication request against a login URL,
        and will return an API token on success. This token is stored
        along with the account data. The username and password are not
        stored.
        """
        self.account.data['kiln_account_domain'] = kiln_account_domain

        token = self.client.login(username, password)

        self.account.data['auth_token'] = token

    def is_authorized(self):
        """Determines if the account is authorized.

        This just checks if there's a token stored on the account.
        """
        return 'auth_token' in self.account.data

    def get_file(self, repository, path, revision, *args, **kwargs):
        """Fetches a file from the repository.

        This will perform an API request to fetch the contents of a file.
        """
        try:
            return self.client.get_raw_file(
                self._get_repository_id(repository),
                path,
                revision)
        except KilnAPIError as e:
            if 'FileNotFound' in e.errors:
                raise FileNotFoundError(path, revision)

            raise

    def get_file_exists(self, *args, **kwargs):
        """Determines if a file exists.

        This will attempt to fetch the file. This will return whether or not
        that was successful.
        """
        try:
            self.get_file(*args, **kwargs)
            return True
        except FileNotFoundError:
            return False

    def _get_repository_id(self, repository):
        """Returns the Kiln repository ID for a repository.

        Kiln requires usage of a repository ID, instead of using the
        provided name. If the ID hasn't already been fetched, this will
        query for the whole project hierarchy and look for the repository.
        If found, the ID will be recorded for future lookup, avoiding
        any expensive checks in the future.
        """
        key = 'kiln_repo_ix'

        if key not in repository.extra_data:
            repo_info = self._find_repository_info(
                repository.extra_data['kiln_project_name'],
                repository.extra_data['kiln_group_name'],
                repository.extra_data['kiln_repo_name'])

            if repo_info:
                repo_id = repo_info['ixRepo']
            else:
                repo_id = None

            repository.extra_data[key] = repo_id
            repository.save(update_fields=['extra_data'])

        return repository.extra_data[key]

    def _find_repository_info(self, project_name, group_name, repo_name):
        """Finds information on a repository.

        This will query the list of projects and look for a repository
        matching the provided project name, group name, and repository
        name.
        """
        projects = self.client.get_projects()

        for project in projects:
            if project['sSlug'] == project_name:
                for group in project['repoGroups']:
                    if group['sSlug'] == group_name:
                        for repo in group['repos']:
                            if repo['sSlug'] == repo_name:
                                return repo

        return None
