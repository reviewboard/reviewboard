from __future__ import unicode_literals

import json
import logging
from collections import defaultdict

from django import forms
from django.conf.urls import url
from django.core.cache import cache
from django.http import (HttpResponse,
                         HttpResponseBadRequest,
                         HttpResponseForbidden)
from django.utils.six.moves.urllib.error import HTTPError
from django.utils.six.moves.urllib.parse import quote
from django.utils.translation import ugettext_lazy as _, ugettext
from django.views.decorators.http import require_POST
from djblets.util.compat.django.template.loader import render_to_string

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
from reviewboard.hostingsvcs.service import (HostingService,
                                             HostingServiceClient)
from reviewboard.hostingsvcs.utils.paginator import APIPaginator
from reviewboard.scmtools.core import Branch, Commit
from reviewboard.scmtools.crypto_utils import encrypt_password
from reviewboard.scmtools.errors import (FileNotFoundError,
                                         RepositoryNotFoundError)
from reviewboard.site.urlresolvers import local_site_reverse


class BitbucketAuthForm(HostingServiceAuthForm):
    """Authentication form for linking a Bitbucket account."""

    def clean_hosting_account_username(self):
        """Clean the username field for the Bitbucket account.

        This will ensure that the user hasn't provided their Atlassian
        e-mail address.

        Returns:
            unicode:
            The account username.

        Raises:
            django.core.exceptions.ValidationError:
                An e-mail address was provided instead of a username.
        """
        username = self.cleaned_data['hosting_account_username']

        if '@' in username:
            raise forms.ValidationError(
                ugettext('This must be your Bitbucket username (the same one '
                         'you would see in URLs for your own repositories), '
                         'not your Atlassian e-mail address.'))

        return username.strip()

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
            payload = json.loads(request.body.decode('utf-8'))
        except ValueError as e:
            logging.error('The payload is not in JSON format: %s', e)
            return HttpResponseBadRequest('Invalid payload format')

        server_url = get_server_url(request=request)

        try:
            review_request_id_to_commits = \
                BitbucketHookViews._get_review_request_id_to_commits_map(
                    payload=payload,
                    server_url=server_url,
                    repository=repository)
        except AuthorizationError as e:
            return HttpResponseForbidden(
                'Incorrect username or password configured for this '
                'repository on Review Board.')

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

        try:
            changes = payload['push']['changes']
        except KeyError:
            return results

        seen_commits_urls = set()

        for change in changes:
            change_new = change.get('new') or {}

            if (change_new and
                change_new['type'] not in ('branch', 'named_branch',
                                           'bookmark')):
                continue

            # These should always be here, but we want to be defensive.
            truncated = change.get('truncated', False)
            commits = change.get('commits') or []
            target_name = change_new.get('name')

            if not target_name or not commits:
                continue

            if truncated:
                try:
                    commits_url = change['links']['commits']['href']
                except KeyError:
                    commits_url = None

                if commits_url is not None:
                    commits = cls._iter_commits(
                        repository.hosting_service,
                        commits_url,
                        seen_commits_urls=seen_commits_urls)

            for commit in commits:
                commit_hash = commit.get('hash')
                commit_message = commit.get('message')

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
    def _iter_commits(cls, hosting_service, commits_url, seen_commits_urls,
                      max_pages=5):
        """Iterate through all pages of commits for a URL.

        This will go through each page of commits corresponding to a Push
        event, yielding each commit for further processing.

        Args:
            hosting_service (Bitbucket):
                The hosting service instance.

            commits_url (unicode):
                The beginning URL to page through.

            seen_commits_urls (set):
                The URLs that have already been seen. If a URL from this set
                is encountered, pagination will stop.

            max_pages (int, optional):
                The maximum number of pages to iterate through.

        Yields:
            dict:
            A payload for an individual commit.
        """
        if commits_url in seen_commits_urls:
            return

        paginator = BitbucketAPIPaginator(client=hosting_service.client,
                                          url=commits_url,
                                          per_page=100)

        for page_data in paginator.iter_pages(max_pages=max_pages):
            seen_commits_urls.add(paginator.url)

            for commit_rsp in page_data:
                yield commit_rsp

            if paginator.next_url in seen_commits_urls:
                break


class BitbucketAPIPaginator(APIPaginator):
    """Paginator for multi-page API responses on Bitbucket.

    This is returned by some :py:classs:`BitbucketClient` functions in order
    to handle iteration over pages of results.
    """

    start_query_param = 'page'
    per_page_query_param = 'pagelen'

    def fetch_url(self, url):
        """Fetch the page data for a URL.

        Args:
            url (unicode):
                The URL to fetch.

        Returns:
            dict:
            Information on the page of results.
        """
        response = self.client.http_get(url, **self.request_kwargs)
        rsp = response.json

        return {
            'data': rsp.get('values'),
            'headers': response.headers,
            'total_count': rsp.get('size'),
            'prev_url': rsp.get('previous'),
            'next_url': rsp.get('next'),
        }


class BitbucketClient(HostingServiceClient):
    """Client interface to the Bitbucket Cloud API."""

    def __init__(self, *args, **kwargs):
        """Initialize the client.

        Args:
            *args (tuple):
                Positional arguments for the parent class.

            **kwargs (dict):
                Keyword arguments for the parent class.
        """
        super(BitbucketClient, self).__init__(*args, **kwargs)

        self.api_url = 'https://bitbucket.org/api/2.0'

    def api_get_user_session(self, **kwargs):
        """Return information on the user's session.

        Args:
            **kwargs (dict):
                Additional keyword arguments to pass in the request.

        Returns:
            dict:
            The user session data.

        Raises:
            reviewboard.hostingsvcs.errors.HostingServiceError:
                Error retrieving the file contents. There may be a more
                specific subclass raised. See :py:meth:`process_http_error`.

            reviewboard.scmtools.errors.UnverifiedCertificateError:
                The SSL certificate was not able to be verified.
        """
        url = '%s/user' % self.api_url

        return self.http_get(url, **kwargs).json

    def api_get_repository(self, repo_owner, repo_name, **kwargs):
        """Return information on a repository.

        Args:
            repo_owner (unicode):
                The owner of the repository.

            repo_name (unicode):
                The name of the repository.

            **kwargs (dict):
                Additional keyword arguments to pass in the request.

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
        url = self._get_repositories_api_url(repo_owner, repo_name)

        return self.http_get(url, **kwargs).json

    def api_get_file_contents(self, repo_owner, repo_name, revision, path,
                              base_commit_id):
        """Return a file from a repository.

        This will perform an API request to fetch the contents of a file.

        Args:
            repo_owner (unicode):
                The owner of the repository.

            repo_name (unicode):
                The name of the repository.

            path (unicode):
                The file path.

            revision (unicode):
                The revision of the file to retrieve.

            base_commit_id (unicode):
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
        url = self._get_file_api_url(repo_owner=repo_owner,
                                     repo_name=repo_name,
                                     revision=revision,
                                     base_commit_id=base_commit_id,
                                     path=path)

        try:
            return self.http_get(url).data
        except HostingServiceAPIError as e:
            if e.http_code == 404:
                raise FileNotFoundError(path=path,
                                        revision=revision,
                                        base_commit_id=base_commit_id)

    def api_get_file_exists(self, repo_owner, repo_name, revision, path,
                            base_commit_id):
        """Return whether a file exists in a repository.

        This will perform an API request to fetch information on the file,
        using that to determine if the file exists.

        Args:
            repo_owner (unicode):
                The owner of the repository.

            repo_name (unicode):
                The name of the repository.

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
        url = self._get_file_api_url(repo_owner=repo_owner,
                                     repo_name=repo_name,
                                     revision=revision,
                                     base_commit_id=base_commit_id,
                                     path=path)

        try:
            self.http_head(url)
            return True
        except HostingServiceAPIError as e:
            if e.http_code == 404:
                return False

            raise

    def api_get_branches(self, repo_owner, repo_name, per_page=100, **kwargs):
        """Return a paginator of all branches for a repository.

        Args:
            repo_owner (unicode):
                The owner of the repository.

            repo_name (unicode):
                The name of the repository.

            per_page (int, optional):
                The number of branches to return per page.

            **kwargs (dict):
                Additional keyword arguments for the request.

        Returns:
            BitbucketAPIPaginator:
            A paginator for fetching branches on the repository.

        Raises:
            reviewboard.hostingsvcs.errors.HostingServiceError:
                Error retrieving the branch information. There may be a more
                specific subclass raised. See :py:meth:`process_http_error`.
        """
        url = ('%s/refs/branches'
               % self._get_repositories_api_url(repo_owner, repo_name))

        return BitbucketAPIPaginator(client=self,
                                     url=url,
                                     per_page=per_page,
                                     request_kwargs=kwargs)

    def api_get_commits(self, repo_owner, repo_name, start=None, per_page=20,
                        **kwargs):
        """Return a list of commits for a repository.

        Args:
            repo_owner (unicode):
                The owner of the repository.

            repo_name (unicode):
                The name of the repository.

            start (unicode, optional):
                The optional starting commit ID or branch for the list. This
                may be used for pagination purposes.

            per_page (int, optional):
                The number of branches to return per page.

            **kwargs (dict):
                Additional keyword arguments for the request.

        Returns:
            BitbucketAPIPaginator:
            A paginator for fetching commits on the repository.

        Raises:
            reviewboard.hostingsvcs.errors.HostingServiceError:
                Error retrieving the branch information. There may be a more
                specific subclass raised. See :py:meth:`process_http_error`.

            reviewboard.scmtools.errors.UnverifiedCertificateError:
                The SSL certificate was not able to be verified.
        """
        url = ('%s/commits'
               % self._get_repositories_api_url(repo_owner, repo_name))

        if start:
            url = '%s/%s' % (url, quote(start))

        return BitbucketAPIPaginator(client=self,
                                     url=url,
                                     per_page=per_page,
                                     request_kwargs=kwargs)

    def api_get_commit(self, repo_owner, repo_name, revision, **kwargs):
        """Return a commit at a given revision/commit ID.

        Args:
            repo_owner (unicode):
                The owner of the repository.

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
        url = ('%s/commit/%s'
               % (self._get_repositories_api_url(repo_owner, repo_name),
                  quote(revision)))

        return self.http_get(url, **kwargs).json

    def api_get_commit_diff(self, repo_owner, repo_name, revision):
        """Return the diff for a commit at a given revision/commit ID.

        This will normalize the diff to ensure it always ends with a trailing
        newline.

        Args:
            repo_owner (unicode):
                The owner of the repository.

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
        url = ('%s/diff/%s'
               % (self._get_repositories_api_url(repo_owner, repo_name),
                  quote(revision)))

        diff = self.http_get(url).data

        if not diff.endswith(b'\n'):
            diff += b'\n'

        return diff

    def build_http_request(self, query=None, only_fields=None, **kwargs):
        """Build a request object for an HTTP request.

        Args:
            query (dict, optional):
                Query arguments for the URL.

            only_fields (list, optional):
                A list of specific fields in the payload to include. All
                other fields will be excluded.

            **kwargs (dict):
                Additional keyword arguments used to build the request.

        Returns:
            reviewboard.hostingsvcs.service.HostingServiceHTTPRequest:
            The resulting request object for use in the HTTP request.
        """
        if only_fields:
            if query is None:
                query = {}

            query['fields'] = ','.join(only_fields)

        return super(BitbucketClient, self).build_http_request(query=query,
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
        super(BitbucketClient, self).process_http_error(request, e)

        if isinstance(e, HTTPError):
            data = e.read()

            try:
                rsp = json.loads(data.decode('utf-8'))
            except Exception:
                rsp = None

            message = None
            detail = None

            if rsp:
                rsp_error = rsp.get('error')

                if rsp_error:
                    message = rsp_error.get('message')
                    detail = rsp_error.get('detail')

            if e.code == 401:
                raise AuthorizationError(
                    message or ugettext(
                        'Invalid Bitbucket username or password. Make sure '
                        'you are using your Bitbucket username and not e-mail '
                        'address, and are using an app password if two-factor '
                        'authentication is enabled.'))
            else:
                raise HostingServiceAPIError(
                    detail or message or data,
                    http_code=e.code,
                    rsp=rsp)
        else:
            raise HostingServiceError(e.reason)

    def _get_repositories_api_url(self, repo_owner, repo_name=None):
        """Return the API URL for working with repositories.

        Args:
            repo_owner (unicode):
                The owner of the repositories.

            repo_name (unicode, optional):
                The optional name of a repository to include in the URL.

        Returns:
            unicode:
            The URL for working with a list of repositories or the specified
            repository.
        """
        url = '%s/repositories/%s' % (self.api_url, repo_owner)

        if repo_name is not None:
            url = '%s/%s' % (url, quote(repo_name))

        return url

    def _get_file_api_url(self, repo_owner, repo_name, revision,
                          base_commit_id, path):
        """Return the API URL for working with files in a repository.

        Args:
            repo_owner (unicode):
                The owner of the repositories.

            repo_name (unicode):
                The name of a repository to include in the URL.

            revision (unicode):
                The revision of the file.

            base_commit_id (unicode):
                The ID of the commit that the file was changed in. This may
                not be provided, and is dependent on the type of repository.

            path (unicode):
                The path to the file.

        Returns:
            unicode:
            The URL for working with a file in the repository.
        """
        return ('%s/src/%s/%s'
                % (self._get_repositories_api_url(repo_owner, repo_name),
                   quote(base_commit_id or revision),
                   quote(path)))


class Bitbucket(HostingService):
    """Hosting service support for Bitbucket.

    Bitbucket is a hosting service that supports Git and Mercurial
    repositories, and provides issue tracker support. It's available
    at https://bitbucket.org/.
    """

    name = 'Bitbucket'

    client_class = BitbucketClient
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
    visible_scmtools = ['Git']

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
        """Check the validity of a repository configuration.

        This will ensure that the configuration data being provided by the
        user is correct and doesn't contain URLs or repository names with
        ``.git`` in the name.

        It will then perform an API request against Bitbucket to get
        information on the repository. This will throw an exception if
        the repository was not found, or does not match the expected
        repository type, and return cleanly if it was found.

        Args:
            plan (unicode, optional):
                The configured repository plan.

            tool_name (unicode, optional):
                The name of the tool selected to communicate with the
                repository.

            *args (tuple, unused):
                Unused positional arguments.

            **kwargs (dict, unused):
                Additional information passed by the repository form.

        Raises:
            reviewboard.hostingsvcs.errors.RepositoryError:
                The repository configuration is not valid.

            reviewboard.scmtools.errors.RepositoryNotFoundError:
                The repository was not found.
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
            rsp = self.client.api_get_repository(
                repo_owner=self._get_repository_owner_raw(plan, kwargs),
                repo_name=self._get_repository_name_raw(plan, kwargs),
                only_fields=['scm'])
        except HostingServiceAPIError as e:
            if e.http_code == 404:
                raise RepositoryNotFoundError()

            raise

        scm = rsp['scm']

        if ((scm == 'git' and tool_name != 'Git') or
            (scm == 'hg' and tool_name != 'Mercurial')):
            raise RepositoryError(
                ugettext('The Bitbucket repository being configured does not '
                         'match the type of repository you have selected.'))

    def authorize(self, username, password, *args, **kwargs):
        """Authorize an account on Bitbucket.

        This will attempt to access the user session resource using the
        provided credentials, determining if they're valid. Those credentials
        may be one of:

        1. A username (not e-mail address) and standard password
        2. A username and an app password (recommended, and required if using
           two-factor authentication)

        If successful, the password is stored in an encrypted form.

        Args:
            username (unicode):
                The username for the account.

            password (unicode):
                The user's password or app password.

            *args (tuple, unused):
                Unused positional arguments.

            **kwargs (dict, unused):
                Unused keyword arguments.

        Raises:
            reviewboard.hostingsvcs.errors.HostingServiceError:
                Error retrieving the branch information. There may be a more
                specific subclass raised.
        """
        # If this fails, an exception will be raised.
        self.client.api_get_user_session(username=username,
                                         password=password)

        self.account.data['password'] = encrypt_password(password)
        self.account.save()

    def is_authorized(self):
        """Return if the account has a stored auth token.

        This will check if we have previously stored password for the
        account. It does not validate that the credentials still work.
        """
        return self.account.data.get('password') is not None

    def get_file(self, repository, path, revision, base_commit_id=None,
                 *args, **kwargs):
        """Return a file from a repository.

        This will perform an API request to fetch the contents of a file.

        If using Git, this will expect a base commit ID to be provided.

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
        if repository.tool.name == 'Git' and not base_commit_id:
            raise FileNotFoundError(
                path,
                revision,
                detail=ugettext('The necessary revision information needed '
                                'to find this file was not provided. Use '
                                'RBTools 0.5.2 or newer.'))

        return self.client.api_get_file_contents(
            repo_owner=self._get_repository_owner(repository),
            repo_name=self._get_repository_name(repository),
            revision=revision,
            path=path,
            base_commit_id=base_commit_id)

    def get_file_exists(self, repository, path, revision, base_commit_id,
                        *args, **kwargs):
        """Return whether a file exists in a repository.

        This will perform an API request to fetch information on the file,
        using that to determine if the file exists.

        If using Git, this will expect a base commit ID to be provided.

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
        if repository.tool.name == 'Git' and not base_commit_id:
            return False

        return self.client.api_get_file_exists(
            repo_owner=self._get_repository_owner(repository),
            repo_name=self._get_repository_name(repository),
            revision=revision,
            path=path,
            base_commit_id=base_commit_id)

    def get_repository_hook_instructions(self, request, repository):
        """Return instructions for setting up incoming webhooks.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            repository (reviewboard.scmtools.models.Repository):
                The repository to configure webhooks for.

        Returns:
            django.utils.safestring.SafeText:
            The HTML to display with instructions.
        """
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
            template_name='hostingsvcs/bitbucket/repo_hook_instructions.html',
            request=request,
            context={
                'example_id': example_id,
                'example_url': example_url,
                'repository': repository,
                'server_url': get_server_url(),
                'add_webhook_url': add_webhook_url,
                'webhook_endpoint_url': webhook_endpoint_url,
            })

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

        Raises:
            reviewboard.hostingsvcs.errors.HostingServiceError:
                Error retrieving the branch information. There may be a more
                specific subclass raised.
        """
        repo_owner = self._get_repository_owner(repository)
        repo_name = self._get_repository_name(repository)

        repo_info = self.client.api_get_repository(
            repo_owner=repo_owner,
            repo_name=repo_name,
            only_fields=['mainbranch.name'])

        try:
            default_branch_name = repo_info['mainbranch']['name']
        except KeyError:
            # No default branch was set in this repository. It may be an
            # empty repository.
            return None

        branches = []
        found_default_branch = False

        paginator = self.client.api_get_branches(
            repo_owner=repo_owner,
            repo_name=repo_name,
            only_fields=['values.name', 'values.target.hash', 'next'])

        for page in paginator:
            for branch_info in page:
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
        paginator = self.client.api_get_commits(
            repo_owner=self._get_repository_owner(repository),
            repo_name=self._get_repository_name(repository),
            start=start or branch,
            only_fields=self._get_commit_fields(prefix='values.'))

        # Note that we're only building commits for one page worth of data.
        return [
            self._build_commit_from_rsp(commit_info)
            for commit_info in paginator.page_data
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
        repo_owner = self._get_repository_owner(repository)
        repo_name = self._get_repository_name(repository)

        # We try to pull the commit's metadata out of the cache. The diff API
        # endpoint is just the raw content of the diff and contains no
        # metadata.
        commit = cache.get(repository.get_commit_cache_key(revision))

        if not commit:
            # However, if it is not in the cache, we have to hit the API to
            # get the metadata.
            commit_rsp = self.client.api_get_commit(
                repo_owner=repo_owner,
                repo_name=repo_name,
                revision=revision,
                only_fields=self._get_commit_fields())
            commit = self._build_commit_from_rsp(commit_rsp)

        # Now fetch the diff.
        diff = self.client.api_get_commit_diff(repo_owner=repo_owner,
                                               repo_name=repo_name,
                                               revision=revision)

        return Commit(author_name=commit.author_name,
                      id=commit.id,
                      date=commit.date,
                      message=commit.message,
                      diff=diff,
                      parent=commit.parent)

    def _get_commit_fields(self, prefix=''):
        """Return the fields needed in a query string for commit parsing.

        This is needed by APIs that want to limit the fields in the payload
        and need to parse commits.

        Args:
            prefix (unicode, optional):
                An optional prefix for each field.

        Returns:
            list of unicode:
            The fields to include in an ``only_fields=`` parameter.
        """
        return [
            prefix + name
            for name in ('author.raw', 'hash', 'date', 'message',
                         'parents.hash')
        ]

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

    def _get_repository_plan(self, repository):
        """Return the stored plan for a repository.

        Args:
            repository (reviewboard.scmtools.models.Repository):
                The repository containing the stored data.

        Returns:
            unicode:
            The plan ID.
        """
        return (repository.extra_data.get('repository_plan') or
                self.DEFAULT_PLAN)

    def _get_repository_name(self, repository):
        """Return the stored Bitbucket name for a repository.

        Args:
            repository (reviewboard.scmtools.models.Repository):
                The repository containing the stored data.

        Returns:
            unicode:
            The name of the repository on Bitbucket.
        """
        return self._get_repository_name_raw(
            self._get_repository_plan(repository),
            repository.extra_data)

    def _get_repository_name_raw(self, plan, extra_data):
        """Return the Bitbucket name for a plan and repository data.

        Args:
            plan (unicode):
                The plan ID.

            extra_data (dict):
                The stored data on the repository.

        Returns:
            unicode:
            The name of the repository on Bitbucket.

        Raises:
            reviewboard.hostingsvcs.errors.InvalidPlanError:
                The provided ``plan`` value is invalid.
        """
        if plan == 'personal':
            return extra_data['bitbucket_repo_name']
        elif plan == 'team':
            return extra_data['bitbucket_team_repo_name']
        elif plan == 'other-user':
            return extra_data['bitbucket_other_user_repo_name']
        else:
            raise InvalidPlanError(plan)

    def _get_repository_owner(self, repository):
        """Return the stored owner for a repository.

        Args:
            repository (reviewboard.scmtools.models.Repository):
                The repository containing the stored data.

        Returns:
            unicode:
            The name of the repository on Bitbucket.
        """
        return self._get_repository_owner_raw(
            self._get_repository_plan(repository),
            repository.extra_data)

    def _get_repository_owner_raw(self, plan, extra_data):
        """Return the repository owner for a plan and repository data.

        Args:
            plan (unicode):
                The plan ID.

            extra_data (dict):
                The stored data on the repository.

        Returns:
            unicode:
            The owner of the repository on Bitbucket.

        Raises:
            reviewboard.hostingsvcs.errors.InvalidPlanError:
                The provided ``plan`` value is invalid.
        """
        if plan == 'personal':
            return self.account.username
        elif plan == 'team':
            return extra_data['bitbucket_team_name']
        elif plan == 'other-user':
            return extra_data['bitbucket_other_user_username']
        else:
            raise InvalidPlanError(plan)
