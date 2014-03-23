from urllib import quote
from urllib2 import HTTPError, URLError

from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.utils import simplejson
from django.utils.translation import ugettext_lazy as _, ugettext

from reviewboard.hostingsvcs.errors import (AuthorizationError,
                                            HostingServiceError,
                                            InvalidPlanError,
                                            RepositoryError)
from reviewboard.hostingsvcs.forms import HostingServiceForm
from reviewboard.hostingsvcs.service import HostingService
from reviewboard.scmtools.crypto_utils import (decrypt_password,
                                               encrypt_password)
from reviewboard.scmtools.errors import FileNotFoundError


class GitLabPersonalForm(HostingServiceForm):
    gitlab_personal_repo_name = forms.CharField(
        label=_('Repository name'),
        max_length=64,
        required=True,
        widget=forms.TextInput(attrs={'size': '60'}))


class GitLabGroupForm(HostingServiceForm):
    gitlab_group_name = forms.CharField(
        label=_('GitLab group name'),
        max_length=64,
        required=True,
        widget=forms.TextInput(attrs={'size': '60'}))

    gitlab_group_repo_name = forms.CharField(
        label=_('Repository name'),
        max_length=64,
        required=True,
        widget=forms.TextInput(attrs={'size': '60'}))


class GitLab(HostingService):
    """Hosting service support for GitLab.

    GitLab is a self-installed source hosting service that supports Git
    repositories. It's available at https://gitlab.org/.
    """
    name = 'GitLab'

    self_hosted = True
    needs_authorization = True
    supports_bug_trackers = True
    supports_repositories = True
    supported_scmtools = ['Git']

    plans = [
        ('personal', {
            'name': _('Personal'),
            'form': GitLabPersonalForm,
            'repository_fields': {
                'Git': {
                    'path': 'git@%(hosting_domain)s:'
                            '%(hosting_account_username)s/'
                            '%(gitlab_personal_repo_name)s.git',
                    'mirror_path': '%(hosting_url)s/'
                                   '%(hosting_account_username)s/'
                                   '%(gitlab_personal_repo_name)s.git',
                },
            },
            'bug_tracker_field': '%(hosting_url)s/'
                                 '%(hosting_account_username)s/'
                                 '%(gitlab_personal_repo_name)s/issues/%%s'
        }),
        ('group', {
            'name': _('Group'),
            'form': GitLabGroupForm,
            'repository_fields': {
                'Git': {
                    'path': 'git@%(hosting_domain)s:'
                            '%(gitlab_group_name)s/'
                            '%(gitlab_group_repo_name)s.git',
                    'mirror_path': '%(hosting_url)s/%(gitlab_group_name)s/'
                                   '%(gitlab_group_repo_name)s.git',
                },
            },
            'bug_tracker_field': '%(hosting_url)s/%(gitlab_group_name)s/'
                                 '%(gitlab_group_repo_name)s/issues/%%s'
        }),
    ]

    def check_repository(self, plan=None, *args, **kwargs):
        """Checks the validity of a repository.

        This will perform an API request against GitLab to get
        information on the repository. This will throw an exception if
        the repository was not found, and return cleanly if it was found.
        """
        self._find_repository_id(
            plan,
            self._get_repository_owner(plan, kwargs),
            self._get_repository_name(plan, kwargs))

    def authorize(self, username, password, hosting_url, *args, **kwargs):
        """Authorizes the GitLab repository.

        GitLab uses HTTP Basic Auth for the API, so this will store the
        provided password, encrypted, for use in later API requests.
        """
        if self._is_email(username):
            login_key = 'email'
        else:
            login_key = 'login'

        # This will raise an exception if it fails, which the form will
        # catch.
        try:
            rsp, headers = self._json_post(
                url=self._build_api_url(hosting_url, 'session'),
                fields={
                    login_key : username,
                    'password': password,
                })
        except HTTPError, e:
            if e.code == 404:
                raise HostingServiceError(
                    ugettext('A GitLab server was not found at the '
                             'provided URL.'))
            elif e.code == 401:
                raise AuthorizationError(
                    ugettext('The username or password is incorrect.'))
            else:
                raise

        self.account.data['private_token'] = \
            encrypt_password(rsp['private_token'])
        self.account.save()

    def is_authorized(self):
        """Determines if the account has supported authorization tokens.

        This checks if we have previously stored a private token for the
        account. It does not validate that the token still works.
        """
        return 'private_token' in self.account.data

    def get_file(self, repository, path, revision, base_commit_id=None,
                 *args, **kwargs):
        """Fetches a file from GitLab.

        This will perform an API request to fetch the contents of a file.
        """
        try:
            return self._api_get(
                self._get_blob_url(repository, path, revision, base_commit_id),
                raw_content=True)
        except (HTTPError, URLError):
            raise FileNotFoundError(path, revision)

    def get_file_exists(self, repository, path, revision, base_commit_id=None,
                        *args, **kwargs):
        """Determines if a file exists.

        This will perform an API request to fetch the metadata for a file.
        """
        try:
            self._api_get(
                self._get_blob_url(repository, path, revision, base_commit_id),
                raw_content=True)

            return True
        except (HTTPError, URLError):
            return False

    def _find_repository_id(self, plan, owner, repo_name):
        """Finds the ID of a repository matching the given name and owner.

        If the repository could not be found, an appropriate error will be
        raised.
        """
        # GitLab claims pagination support, but it has a number of problems.
        # We have no idea how many pages there are, or even if there's another
        # page of items. Furthermore, if we try to go beyond the last page,
        # we just get the first again, so we can't attempt to guess very
        # well.
        #
        # If the list doesn't return the repository, the user is out of luck.
        #
        # This is true as of GitLab 6.4.3.
        repositories = self._api_get_repositories()

        for repository_entry in repositories:
            namespace = repository_entry['namespace']

            if (namespace['path'] == owner and
                repository_entry['path'] == repo_name):
                # This is the repository we wanted to find.
                return repository_entry['id']

        if plan == 'personal':
            raise RepositoryError(
                ugettext('A repository with this name was not found, or your '
                         'user may not own it.'))
        elif plan == 'group':
            raise RepositoryError(
                ugettext('A repository with this name was not found on this '
                         'group, or your user may not have access to it.'))
        else:
            raise InvalidPlanError(plan)

    def _api_get_repositories(self):
        """Returns a list of repositories the user has access to.

        This will fetch up to 100 repositories from GitLab. These are all
        repositories the user has any form of access to.

        We cannot go beyond 100 repositories, due to GitLab's limits,
        and there's no pagination information available, so if users
        have more than 100 repositories, they may be out of luck.
        """
        return self._api_get(
            '%s?per_page=100'
            % self._build_api_url(self.account.hosting_url, 'projects'))

    def _build_api_url(self, hosting_url, *api_paths):
        """Constructs a URL for GitLab API with the given paths."""
        if not hosting_url.endswith('/'):
            hosting_url += '/'

        return '%sapi/v3/%s' % (hosting_url, '/'.join(api_paths))

    def _get_blob_url(self, repository, path, revision, base_commit_id=None):
        """Returns the URL for accessing the contents of a file.

        If a base commit ID is provided, this will use their standard blob
        API, which takes a commit ID and a file path.

        If not provided, it will try the newer API for accessing based on a
        blob SHA1. This requires a new enough version of GitLab, which we
        unfortunately cannot detect through their API.
        """
        # Not all versions of GitLab support a blob ID, so if a base commit ID
        # is provided, we're going to use that instead.
        if base_commit_id:
            return ('%s/repository/blobs/%s?filepath=%s'
                    % (self._get_repo_api_url(repository), base_commit_id,
                       quote(path)))
        else:
            return ('%s/repository/raw_blobs/%s'
                    % (self._get_repo_api_url(repository), revision))

    def _get_repo_api_url(self, repository):
        """Returns the base URL for a repository's API.

        The first time this is called, it will look up the repository ID
        through the API. This may take time, but only has to be done once
        per repository.
        """
        return self._build_api_url(
            self.account.hosting_url,
            'projects/%s' % self._get_repository_id(repository))

    def _get_repository_id(self, repository):
        """Returns the ID of a repository.

        If the ID is unknown, this will attempt to look up the ID in the
        list of repositories the user has access to. It will then store the
        ID for later requests, to prevent further lookups.
        """
        key = 'gitlab_project_id'

        if key not in repository.extra_data:
            plan = repository.extra_data['repository_plan']

            repository.extra_data[key] = self._find_repository_id(
                plan,
                self._get_repository_owner(plan, repository.extra_data),
                self._get_repository_name(plan, repository.extra_data))
            repository.save()

        return repository.extra_data[key]

    def _get_repository_owner(self, plan, extra_data):
        """Returns the owner of a repository.

        If this is a personal repository, the owner will be the user who
        has linked their account to GitLab.

        if this is a group repository, the owner will be the group name.
        """
        if plan == 'personal':
            return self.account.username
        elif plan == 'group':
            return extra_data['gitlab_group_name']
        else:
            raise InvalidPlanError(plan)

    def _get_repository_name(self, plan, extra_data):
        """Returns the name of the repository."""
        if plan == 'personal':
            return extra_data['gitlab_personal_repo_name']
        elif plan == 'group':
            return extra_data['gitlab_group_repo_name']
        else:
            raise InvalidPlanError(plan)

    def _get_private_token(self):
        """Returns the private token used for authentication."""
        return decrypt_password(self.account.data['private_token'])

    def _api_get(self, url, raw_content=False):
        """Makes a request to the GitLab API and returns the result."""
        try:
            data, headers = self._http_get(
                url,
                headers={
                    'Accept': 'application/json',
                    'PRIVATE-TOKEN': self._get_private_token(),
                })

            if raw_content:
                return data
            else:
                return simplejson.loads(data)
        except HTTPError, e:
            if e.code == 401:
                raise AuthorizationError(
                    ugettext('The login or password is incorrect.'))

            raise

    def _is_email(self, email):
        """Returns True if given string is valid email address"""
        try:
            validate_email(email)
            return True
        except ValidationError:
            return False

