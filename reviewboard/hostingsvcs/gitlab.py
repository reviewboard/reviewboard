from __future__ import unicode_literals

import json
import logging
import re

from django import forms
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.template.loader import render_to_string
from django.utils import six
from django.utils.six.moves.urllib.error import HTTPError, URLError
from django.utils.six.moves.urllib.parse import quote, urlparse
from django.utils.translation import ugettext_lazy as _, ugettext

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


class GitLabHostingURLWidget(forms.Widget):
    """"A custom input widget for selecting a GitLab host.

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

        return render_to_string('hostingsvcs/gitlab/url_widget.html', {
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

    def clean_hosting_url(self):
        """Clean the hosting_url field.

        This method ensures that the URL has a scheme.

        Returns:
            unicode: The URL.

        Raises:
            django.core.exceptions.ValidationError:
                Raised when the URL is missing a scheme.
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
            rsp, headers = self.client.json_post(
                url=self._build_api_url(hosting_url, 'session'),
                fields={
                    login_key: username,
                    'password': password,
                })
        except HTTPError as e:
            if e.code == 404:
                raise HostingServiceError(
                    ugettext('A GitLab server was not found at the '
                             'provided URL.'))
            elif e.code == 401:
                raise AuthorizationError(
                    ugettext('The username or password is incorrect.'))
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
            data, headers = self._api_get(
                self._get_blob_url(repository, path, revision, base_commit_id),
                raw_content=True)
            return data
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

    def get_branches(self, repository):
        """Get a list of branches.

        This will perform an API request to fetch a list of branches.
        """
        repo_api_url = ('%s/repository/branches?private_token=%s'
                        % (self._get_repo_api_url(repository),
                           self._get_private_token()))
        refs = self._api_get(repo_api_url)[0]

        results = []

        for ref in refs:
            if 'name' in ref:
                name = ref['name']
                results.append(Branch(id=name,
                                      commit=ref['commit']['id'],
                                      default=(name == 'master')))

        return results

    def get_commits(self, repository, branch=None, start=None):
        """Get a list of commits

        This will perform an API request to fetch a list of commits.
        The start parameter is a 40-character commit id.
        """

        # Ask GitLab for 21 commits per page. GitLab's API doesn't
        # include the parent IDs, so we use subsequent commits to fill
        # them in (allowing us to return 20 commits with parent IDs).
        page_size = self.COMMITS_PER_PAGE + 1

        repo_api_url = ('%s/repository/commits?private_token=%s&per_page=%s'
                        % (self._get_repo_api_url(repository),
                           self._get_private_token(),
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
        commits = self._api_get(repo_api_url)[0]

        results = []

        for idx, item in enumerate(commits):
            commit = Commit(
                author_name=item['author_name'],
                id=item['id'],
                date=item['created_at'],
                message=item.get('message', ''),
                parent='')

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
        """Get the diff of one commit with given commit ID.

        Revision is a commit ID, which is a long SHA consisting of 40
        characters.
        """
        repo_api_url = self._get_repo_api_url(repository)
        private_token = self._get_private_token()

        # Step 1: Fetch the commit itself that we want to review, to get
        # the parent SHA and the commit message. Hopefully this information
        # is still in cache so we don't have to fetch it again. However, the
        # parent SHA is probably empty.
        commit = cache.get(repository.get_commit_cache_key(revision))

        if commit:
            author_name = commit.author_name
            date = commit.date
            parent_revision = commit.parent
            message = commit.message
        else:
            commit_api_url = ('%s/repository/commits/%s?private_token=%s'
                              % (repo_api_url, revision, private_token))

            # This response from GitLab consists of one dict type commit and
            # on instance type header object. Only the first element is needed.
            commit = self._api_get(commit_api_url)[0]

            author_name = commit['author_name']
            date = commit['created_at']
            parent_revision = commit['parent_ids'][0]
            message = commit.get('message', '')

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
        project = self._api_get(path_api_url)[0]
        path_with_namespace = project['path_with_namespace']

        # Build up diff url and get diff.
        diff_url = ('%s%s/commit/%s.diff?private_token=%s'
                    % (hosting_url, path_with_namespace, revision,
                       private_token))
        diff, headers = self.client.http_get(
            diff_url,
            headers={'Accept': 'text/plain'})

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

        return Commit(author_name, revision, date, message, parent_revision,
                      diff=diff)

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
                if group_entry['name'] == owner:
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
        """Returns a list of projects in the given group."""
        return self._api_get(
            self._build_api_url(self.account.hosting_url, 'groups',
                                six.text_type(group_id)))[0]

    def _api_get_groups(self):
        """Returns a list of groups the user has access to.

        This will fetch up to 100 groups from GitLab. These are all groups the
        user has any form of access to.
        """
        return self._api_get(
            '%s?per_page=100'
            % self._build_api_url(self.account.hosting_url, 'groups'))[0]

    def _api_get_repositories(self):
        """Returns a list of repositories the user has access to.

        These are all repositories the user has any form of access to.

        """
        return self._api_get_list(
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
            data, headers = self.client.http_get(
                url,
                headers={
                    b'Accept': b'application/json',
                    b'PRIVATE-TOKEN': self._get_private_token(),
                })

            if raw_content:
                return data, headers
            else:
                return json.loads(data), headers
        except HTTPError as e:
            if e.code == 401:
                raise AuthorizationError(
                    ugettext('The login or password is incorrect.'))

            raise

    def _api_get_list(self, url):
        """Makes a request to a GitLab list API and returns the full list.

        If the server provides a "next" link in the headers (GitLab 6.8.0+),
        this will follow that link and fetch all the results. Otherwise, this
        will provide only the first page of results.
        """
        all_data = []

        while url:
            data, headers = self._api_get(url)

            all_data += data

            url = None
            for link in headers.get('link', '').split(', '):
                m = self.LINK_HEADER_RE.match(link)
                if m:
                    url = m.group('url')
                    break

        return all_data

    def _is_email(self, email):
        """Returns True if given string is valid e-mail address"""
        try:
            validate_email(email)
            return True
        except ValidationError:
            return False
