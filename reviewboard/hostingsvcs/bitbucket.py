from __future__ import unicode_literals

import json
import logging
from collections import defaultdict

from django import forms
from django.conf.urls import url
from django.core.cache import cache
from django.http import HttpResponse, HttpResponseBadRequest
from django.template import RequestContext
from django.template.loader import render_to_string
from django.utils import six
from django.utils.six.moves.urllib.error import HTTPError, URLError
from django.utils.six.moves.urllib.parse import quote, urlencode
from django.utils.translation import ugettext_lazy as _, ugettext
from django.views.decorators.http import require_POST

from reviewboard.admin.server import build_server_url, get_server_url
from reviewboard.hostingsvcs.errors import (AuthorizationError,
                                            HostingServiceAPIError,
                                            HostingServiceError,
                                            InvalidPlanError,
                                            RepositoryError)
from reviewboard.hostingsvcs.forms import (HostingServiceAuthForm,
                                           HostingServiceForm)
from reviewboard.hostingsvcs.hook_utils import (close_all_review_requests,
                                                get_repository_for_hook,
                                                get_review_request_id)
from reviewboard.hostingsvcs.service import HostingService
from reviewboard.scmtools.core import Branch, Commit
from reviewboard.scmtools.crypto_utils import (decrypt_password,
                                               encrypt_password)
from reviewboard.scmtools.errors import FileNotFoundError
from reviewboard.site.urlresolvers import local_site_reverse


class BitbucketAuthForm(HostingServiceAuthForm):
    class Meta(object):
        help_texts = {
            'hosting_account_username': _(
                'Your Bitbucket username. This must <em>not</em> be your '
                'e-mail address! You can find your username in your '
                '<a href="https://bitbucket.org/account/admin/">Bitbucket '
                'Account Settings</a>.'
            ),
            'hosting_account_password': _(
                'The password used for your account, or a '
                '<a href="https://bitbucket.org/account/admin/app-passwords">'
                'configured app password</a>. <strong>Important:</strong> If '
                'using two-factor authentication, you <em>must</em> use an '
                'app password configured with read access to repositories, '
                'accounts, and projects.'
            ),
        }


class BitbucketPersonalForm(HostingServiceForm):
    bitbucket_repo_name = forms.CharField(
        label=_('Repository name'),
        max_length=64,
        required=True,
        widget=forms.TextInput(attrs={'size': '60'}),
        help_text=_('The name of the repository. This is the '
                    '&lt;repo_name&gt; in https://bitbucket.org/'
                    '&lt;username&gt;/&lt;repo_name&gt;/'))


class BitbucketOtherUserForm(HostingServiceForm):
    bitbucket_other_user_username = forms.CharField(
        label=_('Username'),
        max_length=64,
        required=True,
        widget=forms.TextInput(attrs={'size': '60'}),
        help_text=_('The username of the user who owns the repository. This '
                    'is the &lt;username&gt; in '
                    'https://bitbucket.org/&lt;username&gt;/'
                    '&lt;repo_name&gt;/'))

    bitbucket_other_user_repo_name = forms.CharField(
        label=_('Repository name'),
        max_length=64,
        required=True,
        widget=forms.TextInput(attrs={'size': '60'}),
        help_text=_('The name of the repository. This is the '
                    '&lt;repo_name&gt; in '
                    'https://bitbucket.org/&lt;username&gt;/'
                    '&lt;repo_name&gt;/'))


class BitbucketTeamForm(HostingServiceForm):
    bitbucket_team_name = forms.CharField(
        label=_('Team name'),
        max_length=64,
        required=True,
        widget=forms.TextInput(attrs={'size': '60'}),
        help_text=_('The name of the team. This is the &lt;team_name&gt; in '
                    'https://bitbucket.org/&lt;team_name&gt;/'
                    '&lt;repo_name&gt;/'))

    bitbucket_team_repo_name = forms.CharField(
        label=_('Repository name'),
        max_length=64,
        required=True,
        widget=forms.TextInput(attrs={'size': '60'}),
        help_text=_('The name of the repository. This is the '
                    '&lt;repo_name&gt; in '
                    'https://bitbucket.org/&lt;team_name&gt;/'
                    '&lt;repo_name&gt;/'))


class BitbucketHookViews(object):
    """Container class for hook views."""

    @staticmethod
    @require_POST
    def post_receive_hook_close_submitted(request, local_site_name=None,
                                          repository_id=None,
                                          hosting_service_id=None,
                                          hooks_uuid=None):
        """Close review requests as submitted automatically after a push.

        Args:
            request (django.http.HttpRequest):
                The request from the Bitbucket webhook.

            local_site_name (unicode, optional):
                The local site name, if available.

            repository_id (int, optional):
                The pk of the repository, if available.

            hosting_service_id (unicode, optional):
                The name of the hosting service.

            hooks_uuid (unicode, optional):
                The UUID of the configured webhook.

        Returns:
            django.http.HttpResponse:
            A response for the request.
        """
        repository = get_repository_for_hook(
            repository_id=repository_id,
            hosting_service_id=hosting_service_id,
            local_site_name=local_site_name,
            hooks_uuid=hooks_uuid)

        try:
            payload = json.loads(request.body)
        except ValueError as e:
            logging.error('The payload is not in JSON format: %s', e)
            return HttpResponseBadRequest('Invalid payload format')

        server_url = get_server_url(request=request)
        review_request_id_to_commits = \
            BitbucketHookViews._get_review_request_id_to_commits_map(
                payload, server_url, repository)

        if review_request_id_to_commits:
            close_all_review_requests(review_request_id_to_commits,
                                      local_site_name, repository,
                                      hosting_service_id)

        return HttpResponse()

    @classmethod
    def _get_review_request_id_to_commits_map(cls, payload, server_url,
                                              repository):
        """Return a mapping of review request ID to a list of commits.

        If a commit's commit message does not contain a review request ID, we
        append the commit to the key None.

        Args:
            payload (dict):
                The decoded webhook payload.

            server_url (unicode):
                The URL of the Review Board server.

            repository (reviewboard.scmtools.models.Repository):
                The repository object.

        Returns:
            dict:
            A mapping from review request ID to a list of matching commits from
            the payload.
        """
        results = defaultdict(list)
        changes = payload.get('push', {}).get('changes', [])

        for change in changes:
            change_new = change['new']

            if change_new['type'] not in ('branch', 'named_branch',
                                          'bookmark'):
                continue

            # These should always be here, but we want to be defensive.
            truncated = change.get('truncated', False)
            commits = change.get('commits', [])
            target_name = change_new.get('name')

            if not target_name or not commits:
                continue

            if truncated:
                commits = cls._iter_commits(repository.hosting_service,
                                            change['links']['commits']['href'])

            for commit in commits:
                commit_hash = commit.get('hash')
                commit_message = commit.get('message')
                branch_name = commit.get('branch')

                review_request_id = get_review_request_id(
                    commit_message=commit_message,
                    server_url=server_url,
                    commit_id=commit_hash,
                    repository=repository)

                if review_request_id is not None:
                    results[review_request_id].append(
                        '%s (%s)' % (target_name, commit_hash[:7]))

        return results

    @classmethod
    def _iter_commits(cls, hosting_service, commits_url):
        """Iterate through all pages of commits for a URL.

        This will go through each page of commits corresponding to a Push
        event, yielding each commit for further processing.

        Args:
            hosting_service (Bitbucket):
                The hosting service instance.

            commits_url (unicode):
                The beginning URL to page through.

        Yields:
            dict:
            A payload for an individual commit.
        """
        while commits_url:
            commits_rsp = hosting_service.api_get(commits_url)

            for commit_rsp in commits_rsp['values']:
                yield commit_rsp

            commits_url = commits_rsp.get('next')


class Bitbucket(HostingService):
    """Hosting service support for Bitbucket.

    Bitbucket is a hosting service that supports Git and Mercurial
    repositories, and provides issue tracker support. It's available
    at https://www.bitbucket.org/.
    """

    name = 'Bitbucket'
    auth_form = BitbucketAuthForm

    needs_authorization = True
    supports_repositories = True
    supports_bug_trackers = True
    supports_post_commit = True

    has_repository_hook_instructions = True

    repository_url_patterns = [
        url(r'^hooks/(?P<hooks_uuid>[a-z0-9]+)/close-submitted/$',
            BitbucketHookViews.post_receive_hook_close_submitted,
            name='bitbucket-hooks-close-submitted'),
    ]

    supported_scmtools = ['Git', 'Mercurial']
    plans = [
        ('personal', {
            'name': _('Personal'),
            'form': BitbucketPersonalForm,
            'repository_fields': {
                'Git': {
                    'path': 'git@bitbucket.org:%(hosting_account_username)s/'
                            '%(bitbucket_repo_name)s.git',
                    'mirror_path': 'https://%(hosting_account_username)s@'
                                   'bitbucket.org/'
                                   '%(hosting_account_username)s/'
                                   '%(bitbucket_repo_name)s.git',
                },
                'Mercurial': {
                    'path': 'https://%(hosting_account_username)s@'
                            'bitbucket.org/%(hosting_account_username)s/'
                            '%(bitbucket_repo_name)s',
                    'mirror_path': 'ssh://hg@bitbucket.org/'
                                   '%(hosting_account_username)s/'
                                   '%(bitbucket_repo_name)s',
                },
            },
            'bug_tracker_field': ('https://bitbucket.org/'
                                  '%(hosting_account_username)s/'
                                  '%(bitbucket_repo_name)s/issue/%%s/'),
        }),
        ('other-user', {
            'name': _('Other User'),
            'form': BitbucketOtherUserForm,
            'repository_fields': {
                'Git': {
                    'path': 'git@bitbucket.org:'
                            '%(bitbucket_other_user_username)s/'
                            '%(bitbucket_other_user_repo_name)s.git',
                    'mirror_path': 'https://%(hosting_account_username)s@'
                                   'bitbucket.org/'
                                   '%(bitbucket_other_user_username)s/'
                                   '%(bitbucket_other_user_repo_name)s.git',
                },
                'Mercurial': {
                    'path': 'https://%(hosting_account_username)s@'
                            'bitbucket.org/%(bitbucket_other_user_username)s/'
                            '%(bitbucket_other_user_repo_name)s',
                    'mirror_path': 'ssh://hg@bitbucket.org/'
                                   '%(bitbucket_other_user_username)s/'
                                   '%(bitbucket_other_user_repo_name)s',
                },
            },
            'bug_tracker_field': ('https://bitbucket.org/'
                                  '%(bitbucket_other_user_username)s/'
                                  '%(bitbucket_other_user_repo_name)s/'
                                  'issue/%%s/'),
        }),
        ('team', {
            'name': _('Team'),
            'form': BitbucketTeamForm,
            'repository_fields': {
                'Git': {
                    'path': 'git@bitbucket.org:%(bitbucket_team_name)s/'
                            '%(bitbucket_team_repo_name)s.git',
                    'mirror_path': 'https://%(hosting_account_username)s@'
                                   'bitbucket.org/%(bitbucket_team_name)s/'
                                   '%(bitbucket_team_repo_name)s.git',
                },
                'Mercurial': {
                    'path': 'https://%(hosting_account_username)s@'
                            'bitbucket.org/%(bitbucket_team_name)s/'
                            '%(bitbucket_team_repo_name)s',
                    'mirror_path': 'ssh://hg@bitbucket.org/'
                                   '%(bitbucket_team_name)s/'
                                   '%(bitbucket_team_repo_name)s',
                },
            },
            'bug_tracker_field': ('https://bitbucket.org/'
                                  '%(bitbucket_team_name)s/'
                                  '%(bitbucket_team_repo_name)s/issue/%%s/'),

        }),
    ]

    DEFAULT_PLAN = 'personal'

    def check_repository(self, plan=DEFAULT_PLAN, tool_name=None,
                         *args, **kwargs):
        """Checks the validity of a repository.

        This will perform an API request against Bitbucket to get
        information on the repository. This will throw an exception if
        the repository was not found, and return cleanly if it was found.
        """
        repo_name = self._get_repository_name_raw(plan, kwargs)

        if '/' in repo_name:
            raise RepositoryError(ugettext(
                'Please specify just the name of the repository, not '
                'a path.'))

        if '.git' in repo_name:
            raise RepositoryError(ugettext(
                'Please specify just the name of the repository without '
                '".git".'))

        try:
            rsp = self.api_get(self._build_api_url(
                'repositories/%s/%s'
                % (self._get_repository_owner_raw(plan, kwargs),
                   self._get_repository_name_raw(plan, kwargs)),
                query={
                    'fields': 'scm',
                }))
        except HostingServiceError as e:
            if six.text_type(e) == 'Resource not found':
                raise RepositoryError(
                    ugettext('A repository with this name was not found.'))

            raise

        scm = rsp['scm']

        if ((scm == 'git' and tool_name != 'Git') or
            (scm == 'hg' and tool_name != 'Mercurial')):
            raise RepositoryError(
                ugettext('The Bitbucket repository being configured does not '
                         'match the type of repository you have selected.'))

    def authorize(self, username, password, *args, **kwargs):
        """Authorizes the Bitbucket repository.

        Bitbucket supports HTTP Basic Auth or OAuth for the API. We use
        HTTP Basic Auth for now, and we store provided password,
        encrypted, for use in later API requests.
        """
        self.account.data['password'] = encrypt_password(password)

        try:
            self.api_get(self._build_api_url('user'))
            self.account.save()
        except HostingServiceError as e:
            del self.account.data['password']

            if e.http_code in (401, 403):
                self._raise_auth_error()
            else:
                raise
        except Exception:
            del self.account.data['password']
            raise

    def is_authorized(self):
        """Determines if the account has supported authorization tokens.

        This just checks if there's a password set on the account.
        """
        return self.account.data.get('password', None) is not None

    def get_file(self, repository, path, revision, base_commit_id=None,
                 *args, **kwargs):
        """Fetches a file from Bitbucket.

        This will perform an API request to fetch the contents of a file.

        If using Git, this will expect a base commit ID to be provided.
        """
        try:
            return self._api_get_src(repository, path, revision,
                                     base_commit_id)
        except (URLError, HTTPError):
            raise FileNotFoundError(path, revision)

    def get_file_exists(self, repository, path, revision, base_commit_id=None,
                        *args, **kwargs):
        """Determines if a file exists.

        This will perform an API request to fetch the metadata for a file.

        If using Git, this will expect a base commit ID to be provided.
        """
        try:
            self._api_get_src(repository, path, revision, base_commit_id)

            return True
        except (URLError, HTTPError, FileNotFoundError):
            return False

    def get_repository_hook_instructions(self, request, repository):
        """Returns instructions for setting up incoming webhooks."""
        webhook_endpoint_url = build_server_url(local_site_reverse(
            'bitbucket-hooks-close-submitted',
            local_site=repository.local_site,
            kwargs={
                'repository_id': repository.pk,
                'hosting_service_id': repository.hosting_account.service_name,
                'hooks_uuid': repository.get_or_create_hooks_uuid(),
            }))
        add_webhook_url = (
            'https://bitbucket.org/%s/%s/admin/addon/admin/'
            'bitbucket-webhooks/bb-webhooks-repo-admin'
            % (self._get_repository_owner(repository),
               self._get_repository_name(repository)))

        example_id = 123
        example_url = build_server_url(local_site_reverse(
            'review-request-detail',
            local_site=repository.local_site,
            kwargs={
                'review_request_id': example_id,
            }))

        return render_to_string(
            'hostingsvcs/bitbucket/repo_hook_instructions.html',
            RequestContext(request, {
                'example_id': example_id,
                'example_url': example_url,
                'repository': repository,
                'server_url': get_server_url(),
                'add_webhook_url': add_webhook_url,
                'webhook_endpoint_url': webhook_endpoint_url,
            }))

    def _get_default_branch_name(self, repository):
        """Return the name of the repository's default branch.

        Args:
            repository (reviewboard.scmtools.models.Repository):
                The repository whose default branch is to be looked up.

        Returns:
            unicode: The name of the default branch.
        """
        repository_rsp = self.api_get(self._build_repository_api_url(
            repository,
            query={
                'fields': 'mainbranch.name',
            }))

        try:
            return repository_rsp['mainbranch']['name']
        except KeyError:
            # No default branch was set in this repository. It may be an
            # empty repository.
            return None

    def get_branches(self, repository):
        """Return all upstream branches in the repository.

        This will paginate through all the results, 100 entries at a time,
        returning all branches listed in the repository.

        Args:
            repository (reviewboard.scmtools.models.Repository):
                The repository to retrieve branches from.

        Returns:
            list of reviewboard.scmtools.core.Branch:
            The list of branches found in the repository.
        """
        default_branch_name = self._get_default_branch_name(repository)
        found_default_branch = False
        branches = []

        branches_url = self._build_repository_api_url(
            repository,
            'refs/branches',
            query={
                'pagelen': '100',
                'fields': 'values.name,values.target.hash,next',
            })

        while branches_url:
            branches_rsp = self.api_get(branches_url)

            for branch_info in branches_rsp['values']:
                try:
                    branch_name = branch_info['name']
                    is_default = (branch_name == default_branch_name)

                    if is_default:
                        found_default_branch = True

                    branches.append(Branch(
                        id=branch_name,
                        commit=branch_info['target']['hash'],
                        default=is_default))
                except KeyError as e:
                    logging.error('Missing "%s" key in Bitbucket branch '
                                  'definition %r for repository %s. Skipping '
                                  'branch.',
                                  e, branch_info, repository.pk)

            # If there's a "next", it will automatically include any ?fields=
            # entries we specified above.
            branches_url = branches_rsp.get('next')

        if not found_default_branch:
            branches[0].default = True

        return branches

    def get_commits(self, repository, branch=None, start=None):
        """Return a page of commits in the repository.

        This will return 20 commits at a time. The list of commits can start
        on a given branch (for branch filtering) or commit (for pagination).

        Args:
            repository (reviewboard.scmtools.models.Repository):
                The repository to retrieve branches from.

            branch (unicode, optional):
                The branch to retrieve commits from.

            start (unicode, optional):
                The first commit to retrieve in the page, for pagination.

        Returns:
            list of reviewboard.scmtools.core.Commit:
            The list of commits found in the repository.
        """
        path = 'commits'
        start = start or branch

        if start:
            path += '/%s' % start

        url = self._build_repository_api_url(repository, path, query={
            'pagelen': 20,
            'fields': self._get_commit_fields_query('values.'),
        })

        return [
            self._build_commit_from_rsp(commit_rsp)
            for commit_rsp in self.api_get(url)['values']
        ]

    def get_change(self, repository, revision):
        # We try to pull the commit's metadata out of the cache. The diff API
        # endpoint is just the raw content of the diff and contains no
        # metadata.
        commit = cache.get(repository.get_commit_cache_key(revision))

        if not commit:
            # However, if it is not in the cache, we have to hit the API to
            # get the metadata.
            commit_rsp = self.api_get(self._build_repository_api_url(
                repository,
                'commit/%s' % revision,
                query={
                    'fields': self._get_commit_fields_query(),
                }))
            commit = self._build_commit_from_rsp(commit_rsp)

        # Now fetch the diff and normalize it to always end with a newline,
        # so patch is happy.
        diff_url = self._build_repository_api_url(repository,
                                                  'diff/%s' % revision)
        diff = self.api_get(diff_url, raw_content=True)

        if not diff.endswith(b'\n'):
            diff += b'\n'

        return Commit(author_name=commit.author_name,
                      id=commit.id,
                      date=commit.date,
                      message=commit.message,
                      diff=diff,
                      parent=commit.parent)

    def _get_commit_fields_query(self, prefix=''):
        """Return the fields needed in a query string for commit parsing.

        This is needed by APIs that want to limit the fields in the payload
        and need to parse commits.

        Args:
            prefix (unicode, optional):
                An optional prefix for each field.

        Returns:
            unicode:
            The fields to include in a ``?fields=`` query string.
        """
        return ','.join(
            prefix + name
            for name in ('author.raw', 'hash', 'date', 'message',
                         'parents.hash')
        )

    def _build_commit_from_rsp(self, commit_rsp):
        """Return a Commit from an API reesponse.

        This will parse a response from the API and return a structured
        commit.

        Args:
            commit_rsp (dict):
                The API payload for a commit.

        Returns:
            reviewboard.scmtools.core.Commit:
            A commit based on the payload.
        """
        commit = Commit(
            author_name=commit_rsp['author']['raw'],
            id=commit_rsp['hash'],
            date=commit_rsp['date'],
            message=commit_rsp['message'])

        if commit_rsp['parents']:
            commit.parent = commit_rsp['parents'][0]['hash']

        return commit

    def _build_repository_api_url(self, repository, path='', **kwargs):
        """Build an API URL for the given repository.

        This is a wrapper around :py:meth:`_build_api_url` for
        repository-based APIs.

        Args:
            repository (reviewboard.scmtools.models.Repository):
                The repository.

            path (unicode, optional):
                Optional extra path relative to the resource for this
                repository. If left blank, the repository's resource URL
                will be returned.

            **kwargs (dict):
                Extra positional argument to pass to :py:meth:`_build_api_url`.

        Returns:
            unicode:
            The API URL.
        """
        username = self._get_repository_owner(repository)
        repo_name = self._get_repository_name(repository)

        return self._build_api_url('repositories/%s/%s/%s'
                                   % (quote(username), quote(repo_name), path),
                                   **kwargs)

    def _api_get_src(self, repository, path, revision, base_commit_id):
        # If a base commit ID is provided, use it. It may not be provided,
        # though, and in this case, we need to use the provided revision,
        # which will work for Mercurial but not for Git.
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

        # NOTE: As of this writing, the 2.0 API does not support fetching
        #       the raw contents of files. We have to use the 1.0 API for
        #       this instead.
        url = self._build_repository_api_url(
            repository,
            'raw/%s/%s' % (quote(revision), quote(path)),
            version='1.0')

        try:
            return self.api_get(url, raw_content=True)
        except FileNotFoundError:
            raise FileNotFoundError(path, revision=revision,
                                    base_commit_id=base_commit_id)

    def _build_api_url(self, path, query={}, version=None):
        """Return the URL for an API.

        By default, this uses the 2.0 API. The version can be overridden
        if the 1.0 API is needed.

        Args:
            path (unicode):
                The path relative to the root of the API.

            query (dict, optional):
                Optional query arguments for the request.

            version (unicode, optional):
                The optional custom API version to use. If not specified,
                the 2.0 API will be used.

        Returns:
            unicode:
            The absolute URL for the API.
        """
        url = 'https://bitbucket.org/api/%s/%s' % (version or '2.0', path)

        if query:
            url += '?%s' % urlencode(query)

        return url

    def _get_repository_plan(self, repository):
        return (repository.extra_data.get('repository_plan') or
                self.DEFAULT_PLAN)

    def _get_repository_name(self, repository):
        return self._get_repository_name_raw(
            self._get_repository_plan(repository),
            repository.extra_data)

    def _get_repository_name_raw(self, plan, extra_data):
        if plan == 'personal':
            return extra_data['bitbucket_repo_name']
        elif plan == 'team':
            return extra_data['bitbucket_team_repo_name']
        elif plan == 'other-user':
            return extra_data['bitbucket_other_user_repo_name']
        else:
            raise InvalidPlanError(plan)

    def _get_repository_owner(self, repository):
        return self._get_repository_owner_raw(
            self._get_repository_plan(repository),
            repository.extra_data)

    def _get_repository_owner_raw(self, plan, extra_data):
        if plan == 'personal':
            return self.account.username
        elif plan == 'team':
            return extra_data['bitbucket_team_name']
        elif plan == 'other-user':
            return extra_data['bitbucket_other_user_username']
        else:
            raise InvalidPlanError(plan)

    def api_get(self, url, raw_content=False):
        try:
            data, headers = self.client.http_get(
                url,
                username=self.account.username,
                password=decrypt_password(self.account.data['password']))

            if raw_content:
                return data
            else:
                return json.loads(data)
        except HTTPError as e:
            self._check_api_error(e)

    def _check_api_error(self, e):
        data = e.read()

        try:
            rsp = json.loads(data)
        except:
            rsp = None

        message = data

        if rsp and 'error' in rsp:
            error = rsp['error']

            if 'message' in error:
                message = error['message']

        if message:
            message = six.text_type(message)

        if e.code == 401:
            self._raise_auth_error(message)
        elif e.code == 404:
            if message.startswith('Repository'):
                raise HostingServiceError(message, http_code=e.code)

            # We don't have a path here, but it will be filled in inside
            # _api_get_src.
            raise FileNotFoundError('')
        else:
            raise HostingServiceAPIError(
                message or (
                    ugettext('Unexpected HTTP %s error when talking to '
                             'Bitbucket')
                    % e.code),
                http_code=e.code,
                rsp=e)

    def _raise_auth_error(self, message=None):
        raise AuthorizationError(
            message or ugettext(
                'Invalid Bitbucket username or password. Make sure '
                'you are using your Bitbucket username and not e-mail '
                'address, and are using an app password if two-factor '
                'authentication is enabled.'))
