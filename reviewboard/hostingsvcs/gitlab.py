from __future__ import unicode_literals

import json
import logging
import re

from django import forms
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.utils.six.moves.urllib.error import HTTPError, URLError
from django.utils.six.moves.urllib.parse import quote, quote_plus, urlparse
from django.utils.translation import ugettext_lazy as _, ugettext
from djblets.cache.backend import cache_memoize
from djblets.util.compat.django.template.loader import render_to_string

from reviewboard.admin.support import get_kb_url
from reviewboard.hostingsvcs.errors import (AuthorizationError,
                                            HostingServiceError,
                                            InvalidPlanError,
                                            RepositoryError)
from reviewboard.hostingsvcs.forms import (HostingServiceAuthForm,
                                           HostingServiceForm)
from reviewboard.hostingsvcs.service import HostingService
from reviewboard.scmtools.crypto_utils import (decrypt_password,
                                               encrypt_password)
from reviewboard.scmtools.errors import FileNotFoundError
from reviewboard.scmtools.core import Branch, Commit


class GitLabAPIVersionError(HostingServiceError):
    """Raised if we cannot determine the API version."""

    def __init__(self, message, causes):
        """Initialize the GitLabAPIVersionError.

        Args:
            message (unicode):
                The exception message.

            causes (list of Exception):
                The underlying exceptions.
        """
        super(GitLabAPIVersionError, self).__init__(message)

        self.causes = causes

    def __repr__(self):
        """Return a representation of the exception.

        Returns:
            unicode:
            A representation of the exception.
        """
        return ('<GitLabAPIVersionError(message=%r, causes=%r)>'
                % (self.message, self.causes))


class GitLabHostingURLWidget(forms.Widget):
    """A custom input widget for selecting a GitLab host.

    The user can choose between gitlab.com-hosted and self-hosted instances of
    GitLab.
    """

    GITLAB = 'https://gitlab.com'
    CUSTOM = 'custom'

    CHOICES = (
        (GITLAB, _('gitlab.com')),
        (CUSTOM, _('Custom')),
    )

    def value_from_datadict(self, data, files, name):
        """Extract the value from the form data.

        Args:
            data (dict):
                The form data.

            files (dict):
                The files.

            name (unicode):
                The name of the form field.

        Returns:
            unicode:
            The form value.
        """
        if data:
            return data.get(name)

        return self.GITLAB

    def render(self, name, value, attrs=None):
        """Render the widget.

        Args:
            name (unicode):
                The name of the widget.

            value (unicode):
                The value of the widget.

            attrs (dict, optional):
                Additional attributes to pass to the widget.

        Returns:
            django.util.safestring.SafeText:
            The rendered widget.
        """
        attrs = self.build_attrs(attrs)

        return render_to_string(
            template_name='hostingsvcs/gitlab/url_widget.html',
            context={
                'attrs': attrs,
                'id': attrs.pop('id'),
                'is_custom': value and value != self.GITLAB,
                'name': name,
                'value': value or '',
            })


class GitLabAuthForm(HostingServiceAuthForm):
    """An authentication form for the GitLab hosting service.

    This form allows user to select between gitlab.com and self-hosted
    instances of GitLab.
    """

    hosting_url = forms.CharField(
        label=_('Service URL'),
        required=True,
        widget=GitLabHostingURLWidget(attrs={'size': 30}))

    private_token = forms.CharField(
        label=_('API Token'),
        required=True,
        help_text=_(
            'Your GitLab API token. In newer versions of GitLab, you can '
            'create one under <code>Settings &gt; Access Tokens &gt; Personal '
            'Access</code>. This token will need the <code>api</code> scope. '
            'In older versions of GitLab, you can find this under '
            '<code>Profile Settings &gt; Account &gt; Private Token</code>.'
        )
    )

    def __init__(self, *args, **kwargs):
        """Initialize the GitLabAuthForm.

        Args:
            *args (tuple):
                Positional arguments to pass to the base class constructor.

            **kwargs (dict):
                Keyword arguments to pass to the base class constructor.
        """
        super(GitLabAuthForm, self).__init__(*args, **kwargs)

        del self.fields['hosting_account_password']

    def clean_hosting_url(self):
        """Clean the hosting_url field.

        This method ensures that the URL has a scheme.

        Returns:
            unicode: The URL.

        Raises:
            django.core.exceptions.ValidationError:
                The URL was missing a scheme.
        """
        hosting_url = self.cleaned_data['hosting_url']
        result = urlparse(hosting_url)

        if not result.scheme:
            raise ValidationError(
                _('Invalid hosting URL "%(url)s": missing scheme (e.g., HTTP '
                  'or HTTPS)')
                % {
                    'url': hosting_url,
                }
            )

        return hosting_url

    def get_credentials(self):
        """Return the credentials for the form.

        Returns:
            dict:
            A dict containing the values of the ``username`` and
            ``private_token`` fields.
        """
        credentials = {
            'username': self.cleaned_data['hosting_account_username'],
            'private_token': self.cleaned_data['private_token'],
        }

        two_factor_auth_code = \
            self.cleaned_data.get('hosting_account_two_factor_auth_code')

        if two_factor_auth_code:
            credentials['two_factor_auth_code'] = two_factor_auth_code

        return credentials


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

    # The maximum number of commits returned from each call to get_commits()
    COMMITS_PER_PAGE = 20

    self_hosted = True
    needs_authorization = True
    supports_bug_trackers = True
    supports_post_commit = True
    supports_repositories = True
    supported_scmtools = ['Git']

    # Pagination links (in GitLab 6.8.0+) take the form:
    # '<http://gitlab/api/v3/projects?page=2&per_page=100>; rel="next"'
    LINK_HEADER_RE = re.compile(r'\<(?P<url>[^\>]+)\>; rel="next"')

    auth_form = GitLabAuthForm

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

    def authorize(self, username, credentials, hosting_url, *args, **kwargs):
        """Authorize the GitLab repository.

        GitLab uses HTTP Basic Auth for the API, so this will store the
        provided password, encrypted, for use in later API requests.

        Args:
            username (unicode):
                The username of the account being linked.

            credentials (dict):
                Authentication credentials.

            hosting_url (unicode):
                The URL of the GitLab server.

            *args (tuple, unused):
                Ignored positional arguments.

            **kwargs (dict, unused):
                Ignored keyword arguments.

        Raises:
            reviewboard.hostingsvcs.errors.AuthorizationError:
                Authorization could not be completed successfully.

            reviewboard.hostingsvcs.errors.HostingServiceError:
                An HTTP or other unexpected error occurred.
        """
        # This will raise an exception if it fails, which the form will
        # catch.
        try:
            self._try_api_versions(
                hosting_url,
                path='/projects?per_page=1',
                headers={
                    'PRIVATE-TOKEN': credentials['private_token'],
                })
        except (AuthorizationError, GitLabAPIVersionError):
            raise
        except HTTPError as e:
            if e.code == 404:
                raise HostingServiceError(
                    ugettext('A GitLab server was not found at the '
                             'provided URL.'))
            else:
                logging.exception('Unexpected HTTP error when linking GitLab '
                                  'account for %s: %s',
                                  username, e)
                raise HostingServiceError(
                    ugettext('Unexpected HTTP error %s.')
                    % e.code)
        except Exception as e:
            logging.exception('Unexpected error when linking GitLab account '
                              'for %s: %s',
                              username, e)
            raise HostingServiceError(
                ugettext('Unexpected error "%s"') % e)

        self.account.data['private_token'] = \
            encrypt_password(credentials['private_token'])
        self.account.save()

    def is_authorized(self):
        """Determine if the account has supported authorization tokens.

        This checks if we have previously stored a private token for the
        account. It does not validate that the token still works.

        Returns:
            bool:
            Whether or not the account is authorized with GitLab.
        """
        return 'private_token' in self.account.data

    def get_file(self, repository, path, revision, base_commit_id=None,
                 *args, **kwargs):
        """Fetch a file from GitLab.

        This will perform an API request to fetch the contents of a file.

        Args:
            repository (reviewboard.scmtools.models.Repository):
                The repository to fetch the file from.

            path (unicode):
                The file path.

            revision (unicode):
                The SHA1 of the file blob.

            base_commit_id (unicode, optional):
                An optional commit SHA1.

            *args (tuple, unused):
                Ignored positional arguments.

            **kwargs (dict, unused):
                Ignored keyword arguments.

        Returns:
            bytes:
            The file data at the requested revision.

        Raises:
            reviewboard.scmtools.errors.FileNotFoundError:
                The file could not be retrieved.
        """
        try:
            data, headers = self._api_get(
                repository.hosting_account.hosting_url,
                self._get_blob_url(repository, path, revision, base_commit_id),
                raw_content=True)
            return data
        except (HTTPError, URLError):
            raise FileNotFoundError(path, revision)

    def get_file_exists(self, repository, path, revision, base_commit_id=None,
                        *args, **kwargs):
        """Determine if a file exists.

        This will perform an API request to fetch the metadata for a file.

        Args:
            repository (reviewboard.scmtools.models.Repository):
                The repository to fetch the file from.

            path (unicode):
                The file path.

            revision (unicode):
                The SHA1 of the file blob.

            base_commit_id (unicode, optional):
                An optional commit SHA1.

            *args (tuple, unused):
                Ignored positional arguments.

            **kwargs (dict, unused):
                Ignored keyword arguments.

        Returns:
            bool:
            Whether or not the file exists.

        Raises:
            reviewboard.scmtools.errors.AuthorizationError:
                There was an issue with the authorization credentials.

            reviewboard.scmtools.errors.FileNotFoundError:
                The file could not be retrieved.
        """
        try:
            self._api_get(
                repository.hosting_account.hosting_url,
                self._get_blob_url(repository, path, revision, base_commit_id),
                raw_content=True)

            return True
        except (HTTPError, URLError):
            return False

    def get_branches(self, repository):
        """Return a list of branches.

        This will perform an API request to fetch a list of branches.

        Args:
            repository (reviewboard.scmtools.models.Repository):
                The repository to get branches from.

        Returns:
            list of reviewboard.scmtools.core.Branch:
            The branches available.

        Raises:
            reviewboard.scmtools.errors.AuthorizationError:
                There was an issue with the authorization credentials.

            urllib2.HTTPError:
                There was an error communicating with the server.
        """
        repo_api_url = ('%s/repository/branches'
                        % self._get_repo_api_url(repository))
        refs = self._api_get_list(repository.hosting_account.hosting_url,
                                  repo_api_url)

        results = []

        for ref in refs:
            if 'name' in ref:
                name = ref['name']
                results.append(Branch(id=name,
                                      commit=ref['commit']['id'],
                                      default=(name == 'master')))

        return results

    def get_commits(self, repository, branch=None, start=None):
        """Return a list of commits

        This will perform an API request to fetch a list of commits.

        Args:
            repository (reviewboard.scmtools.models.Repository):
                The repository to fetch commits from.

            branch (unicode, optional):
                The branch to fetch commits from. If not provided, the default
                branch will be used.

            start (unicode, optional):
                The commit to start fetching form.

                If provided, this argument will override ``branch``. Otherwise,
                if neither are provided, the default branch will be used.

        Returns:
            list of reviewboard.scmtools.core.Commit:
            The commits from the API.

        Raises:
            reviewboard.scmtools.errors.AuthorizationError:
                There was an issue with the authorization credentials.

            urllib2.HTTPError:
                There was an error communicating with the server.
        """
        # Ask GitLab for 21 commits per page. GitLab's API doesn't
        # include the parent IDs, so we use subsequent commits to fill
        # them in (allowing us to return 20 commits with parent IDs).
        page_size = self.COMMITS_PER_PAGE + 1

        repo_api_url = ('%s/repository/commits?per_page=%s'
                        % (self._get_repo_api_url(repository),
                           page_size))

        if start:
            # If start parameter is given, use it as the latest commit to log
            # from, so that we fetch a page of commits, and the first commit id
            # on the page is the start parameter.
            repo_api_url += '&ref_name=%s' % start
        elif branch:
            # The branch is optional. If it is not given, use the default
            # branch. The default branch is set to 'master' in get_branches()
            repo_api_url += '&ref_name=%s' % branch

        # The GitLab API will return a tuple consists of two elements.
        # The first one is a list of commits, and the other one is an instance
        # type object containing all kinds of headers, which is not required.
        commits = self._api_get(repository.hosting_account.hosting_url,
                                repo_api_url)[0]

        results = []

        for idx, item in enumerate(commits):
            commit = self._parse_commit(item)

            if idx > 0:
                # Note that GitLab API documents do not show any returned
                # 'parent_id' from the query for a list of commits. So we use
                # the current commit id as the previous commit's parent id, and
                # remove the last commit from results.
                results[idx - 1].parent = commit.id

            results.append(commit)

        # Strip off the last commit since we don't know its parent id yet.
        if len(commits) == page_size:
            results.pop()

        return results

    def get_change(self, repository, revision):
        """Fetch a single commit from GitLab.

        Args:
            repository (reviewboard.scmtools.models.Repository):
                The repository in question.

            revision (unicode):
                The SHA1 hash of the commit to fetch.

        Returns:
            reviewboard.scmtools.core.Commit:
            The commit in question.

        Raises:
            reviewboard.scmtools.errors.AuthorizationError:
                There was an issue with the authorization credentials.

            reviewboard.hostingsvcs.errors.HostingServiceError:
                There was an error fetching information on the commit or
                diff.

            urllib2.HTTPError:
                There was an error communicating with the server.
        """
        repo_api_url = self._get_repo_api_url(repository)
        private_token = self._get_private_token()

        # Step 1: Fetch the commit itself that we want to review, to get
        # the parent SHA and the commit message. Hopefully this information
        # is still in cache so we don't have to fetch it again. However, the
        # parent SHA is probably empty.
        commit = cache.get(repository.get_commit_cache_key(revision))

        if commit is None:
            commit_api_url = ('%s/repository/commits/%s'
                              % (repo_api_url, revision))

            # This response from GitLab consists of one dict type commit and
            # on instance type header object. Only the first element is needed.
            commit_data = self._api_get(repository.hosting_account.hosting_url,
                                        commit_api_url)[0]

            commit = self._parse_commit(commit_data)
            commit.parent = commit_data['parent_ids'][0]

        # Step 2: Get the diff. The revision is the commit header in here.
        # Firstly, a diff url should be built up, which has the format of
        # <hosting_url>/<user-name>/<project-name>/commit/<revision>.diff,
        # then append the private_token to the end of the url and get the diff.

        hosting_url = self.account.hosting_url

        if not hosting_url.endswith('/'):
            hosting_url += '/'

        # Get the project path with the namespace.
        path_api_url = ('%s?private_token=%s'
                        % (repo_api_url, private_token))
        project = self._api_get(repository.hosting_account.hosting_url,
                                path_api_url)[0]
        path_with_namespace = project['path_with_namespace']

        # Build up diff url and get diff.
        diff_url = ('%s%s/commit/%s.diff?private_token=%s'
                    % (hosting_url, path_with_namespace, revision,
                       private_token))

        try:
            response = self.client.http_get(
                diff_url,
                headers={
                    'Accept': 'text/plain',
                    'PRIVATE-TOKEN': private_token,
                })
        except HTTPError as e:
            if e.code in (401, 403, 404):
                kb_url = get_kb_url(3000100782)

                raise HostingServiceError(
                    _('Review Board cannot post commits from private '
                      'repositories with this version of GitLab, due to '
                      'GitLab API limitations. Please post this commit '
                      '(%(commit)s) with RBTools. See %(kb_url)s.')
                    % {
                        'commit': revision,
                        'kb_url': kb_url,
                    },
                    help_link=kb_url,
                    help_link_text=_('Learn more'))
            else:
                raise HostingServiceError(
                    _('Unable to fetch the diff for this commit. Received '
                      'an HTTP %(http_code)s error, saying: %(error)s')
                    % {
                        'http_code': e.code,
                        'error': e,
                    })

        diff = response.data

        # Remove the last two lines. The last line is 'libgit <version>',
        # and the second last line is '--', ending with '\n'. To avoid the
        # error from parsing the empty file (size is 0), split the string into
        # two parts using the delimiter '--\nlibgit'. If only use '\n' or '--'
        # delimiter, more characters might be stripped out from file
        # modification commit diff.
        diff = diff.rsplit(b'--\nlibgit', 2)[0]

        # Make sure there's a trailing newline.
        if not diff.endswith(b'\n'):
            diff += b'\n'

        commit.diff = diff
        return commit

    def _find_repository_id(self, plan, owner, repo_name):
        """Find the ID of a repository matching the given name and owner.

        If the repository could not be found, an appropriate error will be
        raised.

        Args:
            plan (unicode):
                The plan name.

            owner (unicode):
                The name of the owning group or user.

            repo_name (unicode):
                The name of the repository.

        Returns:
            int:
            The ID of the repository.

        Raises:
            reviewboard.scmtools.errors.AuthorizationError:
                There was an issue with the authorization credentials.

            reviewboard.scmtools.errors.RepositoryError:
                The repository could be found or accessed.

            urllib2.HTTPError:
                There was an error communicating with the server.
        """
        if self._get_api_version(self.account.hosting_url) == '3':
            return self._find_repository_id_v3(plan, owner, repo_name)
        else:
            return self._find_repository_id_v4(plan, owner, repo_name)

    def _find_repository_id_v4(self, plan, owner, repo_name):
        """Find the ID of a repository matching the given name and owner.

        If the repository could not be found, an appropriate error will be
        raised.

        Args:
            plan (unicode):
                The plan name.

            owner (unicode):
                The name of the owning group or user.

            repo_name (unicode):
                The name of the repository.

        Returns:
            int:
            The ID of the repository.

        Raises:
            reviewboard.scmtools.errors.AuthorizationError:
                There was an issue with the authorization credentials.

            reviewboard.scmtools.errors.RepositoryError:
                The repository could be found or accessed.

            urllib2.HTTPError:
                There was an error communicating with the server.
        """
        project = '%s/%s' % (owner, repo_name)

        try:
            data, headers = self._api_get(self.account.hosting_url,
                                          'projects/%s' % quote_plus(project))
            return data['id']
        except HTTPError as e:
            if e.code == 404:
                raise RepositoryError(
                    ugettext('A repository with this name was not found, or '
                             'your user may not own it.'))

            raise

    def _find_repository_id_v3(self, plan, owner, repo_name):
        """Find the ID of a repository matching the given name and owner.

        If the repository could not be found, an appropriate error will be
        raised.

        Args:
            plan (unicode):
                The plan name.

            owner (unicode):
                The name of the owning group or user.

            repo_name (unicode):
                The name of the repository.

        Returns:
            int:
            The ID of the repository.

        Raises:
            reviewboard.scmtools.errors.AuthorizationError:
                There was an issue with the authorization credentials.

            reviewboard.scmtools.errors.RepositoryError:
                The repository could be found or accessed.

            urllib2.HTTPError:
                There was an error communicating with the server.
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
        if plan == 'personal':
            repositories = self._api_get_repositories()

            for repository_entry in repositories:
                namespace = repository_entry['namespace']

                if (namespace['path'] == owner and
                    repository_entry['path'] == repo_name):
                    # This is the repository we wanted to find.
                    return repository_entry['id']

            raise RepositoryError(
                ugettext('A repository with this name was not found, or your '
                         'user may not own it.'))
        elif plan == 'group':
            groups = self._api_get_groups()

            for group_entry in groups:
                # If the full path is available, use that (to support nested
                # groups). Otherwise fall back on the group name.
                group_name = group_entry.get('full_path', group_entry['name'])

                if group_name == owner:
                    group_id = group_entry['id']
                    group_data = self._api_get_group(group_id)
                    repositories = group_data['projects']

                    for repository_entry in repositories:
                        if repository_entry['name'] == repo_name:
                            return repository_entry['id']

                    raise RepositoryError(
                        ugettext('A repository with this name was not '
                                 'found on this group, or your user may '
                                 'not have access to it.'))
            raise RepositoryError(
                ugettext('A group with this name was not found, or your user '
                         'may not have access to it.'))
        else:
            raise InvalidPlanError(plan)

    def _api_get_group(self, group_id):
        """Return information about a given group.

        Args:
            group_id (int):
                The ID of the group to fetch repositories for.

        Returns:
            dict:
            Information about the requested group.

        Raises:
            reviewboard.scmtools.errors.AuthorizationError:
                There was an issue with the authorization credentials.

            urllib2.HTTPError:
                There was an error communicating with the server.
        """
        return self._api_get(self.account.hosting_url,
                             'groups/%s' % group_id)[0]

    def _api_get_groups(self):
        """Return a list of groups the user has access to.

        This will fetch all available groups on GitLab. These are all groups
        the user has any form of access to.

        Returns:
            list of dict:
            The list of group information.

        Raises:
            reviewboard.scmtools.errors.AuthorizationError:
                There was an issue with the authorization credentials.

            urllib2.HTTPError:
                There was an error communicating with the server.
        """
        return self._api_get_list(self.account.hosting_url,
                                  'groups?per_page=100')

    def _api_get_repositories(self):
        """Return a list of repositories the user has access to.

        These are all repositories the user has any form of access to.

        Returns:
            list of dict:
            A list of the parsed JSON responses.

        Raises:
            reviewboard.scmtools.errors.AuthorizationError:
                There was an issue with the authorization credentials.

            urllib2.HTTPError:
                There was an error communicating with the server.
        """
        return self._api_get_list(self.account.hosting_url,
                                  'projects?per_page=100')

    def _build_api_url(self, hosting_url, path, api_version=None):
        """Build an API URL.

        Args:
            hosting_url (unicode):
                The URL of the GitLab server.

            path (unicode):
                The API path (not including :samp:`/api/v{version}/`) to build
                the URL for.

            api_version (int, optional):
                The version of the API (3 or 4) to build the URL for.

                If not provided, it will be determined via the cache or, if
                uncached, from the server itself.

        Returns:
            unicode:
            The URL.
        """
        if api_version is None:
            api_version = self._get_api_version(hosting_url)

        return '%s/api/v%s/%s' % (hosting_url.rstrip('/'), api_version,
                                  path.lstrip('/'))

    def _get_blob_url(self, repository, path, revision, base_commit_id=None):
        """Return the URL for accessing the contents of a file.

        Args:
            repository (reviewboard.scmtools.models.Repository):
                The repository.

            path (unicode):
                The path to the file.

            revision (unicode):
                The SHA1 of the blob.

            base_commit_id (unicode, optional):
                The SHA1 of the commit to fetch the file at.

                If provided, this will use their standard blob API, which takes
                a commit ID and a file path.

                If not provided, it will try the newer API for accessing based
                on a blob SHA1. This requires a new enough version of GitLab,
                which we unfortunately cannot detect through their API.

        Returns:
            unicode:
            The blob URL.
        """
        repo_api_url = self._get_repo_api_url(repository)
        api_version = self._get_api_version(self.account.hosting_url)

        if api_version == '3':
            # Not all versions of GitLab support a blob ID, so if a base commit
            # ID is provided, we're going to use that instead.
            if base_commit_id:
                return ('%s/repository/blobs/%s?filepath=%s'
                        % (repo_api_url, base_commit_id, quote(path)))
            else:
                return ('%s/repository/raw_blobs/%s'
                        % (repo_api_url, revision))
        else:
            return ('%s/repository/blobs/%s/raw'
                    % (repo_api_url, revision))

    def _get_repo_api_url(self, repository):
        """Return the base URL for a repository's API.

        The first time this is called, it will look up the repository ID
        through the API. This may take time, but only has to be done once
        per repository.

        Args:
            repository (reviewboard.scmtools.models.Repository):
                The repository.

        Returns:
            unicode:
            The URL of the repository.
        """
        return 'projects/%s' % self._get_repository_id(repository)

    def _get_repository_id(self, repository):
        """Return the ID of a repository.

        If the ID is unknown, this will attempt to look up the ID in the
        list of repositories the user has access to. It will then store the
        ID for later requests, to prevent further lookups.

        Args:
            repository (reviewboard.scmtools.models.Repository):
                The repository.

        Returns:
            int:
            The ID of the repository in GitLab.
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
        """Return the owner of a repository.

        Args:
            plan (unicode):
                The plan name. This should be one of either ``'personal'`` or
                ``'group'``.

            extra_data (dict):
                The
                :py:attr:`~reviewboard.scmtools.models.Repository.extra_data`
                attribute.

        Returns:
            unicode:
            The owner of the repository.

            If this is a personal repository, the owner will be the user who
            has linked their account to GitLab.

            If this is a group repository, the owner will be the group name.

        Raises:
              reviewboard.hostingsvcs.errors.InvalidPlanError:
                  Raised when the plan is not a valid choice.
        """
        if plan == 'personal':
            return self.account.username
        elif plan == 'group':
            return extra_data['gitlab_group_name']
        else:
            raise InvalidPlanError(plan)

    def _get_repository_name(self, plan, extra_data):
        """Return the name of the repository.

        Args:
            plan (unicode):
                The repository plan.

            extra_data (dict):
                The ``extra_data`` attribute of the corresponding
                :py:class:`reviewboard.scmtools.models.Repository`.

        Returns:
            unicode:
            The name of the plan.

        Raises:
            reviewboard.hostingsvcs.errors.InvalidPlanError:
                An invalid plan was given.
        """
        if plan == 'personal':
            return extra_data['gitlab_personal_repo_name']
        elif plan == 'group':
            return extra_data['gitlab_group_repo_name']
        else:
            raise InvalidPlanError(plan)

    def _get_private_token(self):
        """Return the private token used for authentication.

        Returns:
            unicode:
            The API token.
        """
        return decrypt_password(self.account.data['private_token'])

    def _api_get(self, hosting_url=None, path=None, url=None,
                 raw_content=False):
        """Make a request to the GitLab API and return the result.

        If ``hosting_url`` and ``path`` are provided, the API version will be
        deduced from the server. Otherwise, the full URL given in ``url`` will
        be used.

        Args:
            hosting_url (unicode, optional):
                The host of the repository.

            path (unicode, optional):
                The path after :samp:`/api/v{version}`.

            url (unicode, optional):
                If provided, the full URL to retrieve. Passing ``hosting_url``
                and ``path`` should be preferred over this argument.

            raw_content (bool, optional):
                Whether or not to return the raw content (if ``True``) or to
                parse it as JSON (if ``False``).

                Defaults to ``False``.

        Returns:
            object:
            The response.

        Raises:
            reviewboard.scmtools.errors.AuthorizationError:
                There was an issue with the authorization credentials.

            urllib2.HTTPError:
                There was an error communicating with the server.
        """
        if url:
            assert not hosting_url
            assert not path
        else:
            url = self._build_api_url(hosting_url, path)

        headers = {
            'PRIVATE-TOKEN': self._get_private_token(),
        }

        if not raw_content:
            headers['Accept'] = 'application/json'

        try:
            response = self.client.http_get(url, headers)

            if raw_content:
                return response.data, response.headers
            else:
                return response.json, response.headers
        except HTTPError as e:
            if e.code == 401:
                raise AuthorizationError(
                    ugettext('The login or password is incorrect.'))

            raise

    def _api_get_list(self, hosting_url, path):
        """Make a request to a GitLab list API and return the full list.

        If the server provides a "next" link in the headers (GitLab 6.8.0+),
        this will follow that link and fetch all the results. Otherwise, this
        will provide only the first page of results.

        Args:
            hosting_url (unicode):
                The GitLab server URL.

            path (unicode):
                The path to list resource to fetch.

        Returns:
            list of dict:
            The list of all objects retrieved from the path and its subsequent
            pages.

        Raises:
            reviewboard.scmtools.errors.AuthorizationError:
                There was an issue with the authorization credentials.

            urllib2.HTTPError:
                There was an error communicating with the server.
        """
        all_data = []
        url = self._build_api_url(hosting_url, path)

        while url:
            data, headers = self._api_get(url=url)

            all_data += data

            url = None

            for link in headers.get('Link', '').split(', '):
                m = self.LINK_HEADER_RE.match(link)

                if m:
                    url = m.group('url')
                    break

        return all_data

    def _get_api_version(self, hosting_url):
        """Return the version of the API supported by the given server.

        This method will cache the result.

        Args:
            hosting_url (unicode):
                The URL of the GitLab server.

        Returns:
            unicode:
            The version of the API as a string.

            It is returned as a string because
            :py:func:`djblets.cache.backend.cache_memoize` does not work on
            integer results.
        """
        headers = {}

        if self.account.data and 'private_token' in self.account.data:
            headers['PRIVATE-TOKEN'] = decrypt_password(
                self.account.data['private_token']).encode('utf-8')

        return cache_memoize(
            'gitlab-api-version:%s' % hosting_url,
            expiration=3600,
            lookup_callable=lambda: self._try_api_versions(
                hosting_url,
                headers=headers,
                path='/projects?per_page=1',
            )[0])

    def _try_api_versions(self, hosting_url, path, http_method='get',
                          use_json=False, **request_kwargs):
        """Try different API versions and return the first valid response.

        Args:
            hosting_url (unicode):
                The URL of the GitLab server.

            path (unicode):
                The API path to retrieve, not including
                :samp:`/api/v{version}`.

            http_method (unicode, optional):
                The method to use. Defaults to ``GET``.

            use_json (bool, optional):
                Whether or not to interpret the results as JSON.

            **request_kwargs (dict):
                Additional keyword arguments to pass to the request method.

        Returns:
            tuple:
            A 3-tuple of:

            * The API version (:py:class:`unicode`).
            * The response body (:py:class:`bytes` or :py:class:`dict`).
            * The response headers (:py:class:`dict`).

        Raises:
            reviewboard.scmtools.errors.AuthorizationError:
                There was an issue with the authorization credentials.

            GitLabAPIVersionError:
                The API version could be determined.
        """
        http_method = http_method.lower()

        if use_json:
            method = getattr(self.client, 'json_%s' % http_method)
        else:
            method = getattr(self.client, 'http_%s' % http_method)

        errors = []

        for api_version in ('4', '3'):
            url = self._build_api_url(hosting_url, path,
                                      api_version=api_version)

            try:
                rsp, headers = method(url, **request_kwargs)
            except HTTPError as e:
                if e.code == 401:
                    raise AuthorizationError('The API token is invalid.')

                errors.append(e)
            except Exception as e:
                errors.append(e)
            else:
                return api_version, rsp, headers

        # Note that we're only going to list the error found in the first
        # HTTP GET attempt. It's more than likely that if we're unable to
        # look up any version URLs, the root cause will be the same.
        raise GitLabAPIVersionError(
            ugettext(
                'Could not determine the GitLab API version for %(url)s '
                'due to an unexpected error (%(errors)s). Check to make sure '
                'the URL can be resolved from this server and that any SSL '
                'certificates are valid and trusted.'
            ) % {
                'url': hosting_url,
                'errors': errors[0],
            },
            causes=errors,
        )

    def _parse_commit(self, commit_data):
        """Return a Commit object based on data return from the API.

        Args:
            commit_data (dict):
                The data returned from the GitLab API.

        Returns
            reviewboard.scmtools.core.Commit:
            The parsed commit.
        """
        # Older versions of GitLab don't have a ``message`` field and
        # instead only offer the ``title`` (i.e., the first line of the
        # commit message).
        return Commit(
            author_name=commit_data['author_name'],
            id=commit_data['id'],
            date=commit_data['created_at'],
            message=commit_data.get('message', commit_data.get('title', '')))
