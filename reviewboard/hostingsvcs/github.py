from __future__ import unicode_literals

import hashlib
import hmac
import json
import logging
import re
import uuid
from collections import defaultdict

from django import forms
from django.conf import settings
from django.conf.urls import patterns, url
from django.contrib.sites.models import Site
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse, HttpResponseBadRequest
from django.template import RequestContext
from django.template.loader import render_to_string
from django.utils import six
from django.utils.six.moves.urllib.error import HTTPError, URLError
from django.utils.six.moves.urllib.parse import urljoin
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.http import require_POST
from djblets.siteconfig.models import SiteConfiguration

from reviewboard.admin.server import build_server_url, get_server_url
from reviewboard.hostingsvcs.bugtracker import BugTracker
from reviewboard.hostingsvcs.errors import (AuthorizationError,
                                            HostingServiceError,
                                            InvalidPlanError,
                                            RepositoryError,
                                            TwoFactorAuthCodeRequiredError)
from reviewboard.hostingsvcs.forms import HostingServiceForm
from reviewboard.hostingsvcs.hook_utils import (close_all_review_requests,
                                                get_git_branch_name,
                                                get_repository_for_hook,
                                                get_review_request_id)
from reviewboard.hostingsvcs.repository import RemoteRepository
from reviewboard.hostingsvcs.service import (HostingService,
                                             HostingServiceClient)
from reviewboard.hostingsvcs.utils.paginator import (APIPaginator,
                                                     ProxyPaginator)
from reviewboard.scmtools.core import Branch, Commit
from reviewboard.scmtools.errors import FileNotFoundError, SCMError
from reviewboard.site.urlresolvers import local_site_reverse


class GitHubPublicForm(HostingServiceForm):
    github_public_repo_name = forms.CharField(
        label=_('Repository name'),
        max_length=64,
        required=True,
        widget=forms.TextInput(attrs={'size': '60'}),
        help_text=_('The name of the repository. This is the '
                    '&lt;repo_name&gt; in '
                    'http://github.com/&lt;username&gt;/&lt;repo_name&gt;/'))


class GitHubPrivateForm(HostingServiceForm):
    github_private_repo_name = forms.CharField(
        label=_('Repository name'),
        max_length=64,
        required=True,
        widget=forms.TextInput(attrs={'size': '60'}),
        help_text=_('The name of the repository. This is the '
                    '&lt;repo_name&gt; in '
                    'http://github.com/&lt;username&gt;/&lt;repo_name&gt;/'))


class GitHubPublicOrgForm(HostingServiceForm):
    github_public_org_name = forms.CharField(
        label=_('Organization name'),
        max_length=64,
        required=True,
        widget=forms.TextInput(attrs={'size': '60'}),
        help_text=_('The name of the organization. This is the '
                    '&lt;org_name&gt; in '
                    'http://github.com/&lt;org_name&gt;/&lt;repo_name&gt;/'))

    github_public_org_repo_name = forms.CharField(
        label=_('Repository name'),
        max_length=64,
        required=True,
        widget=forms.TextInput(attrs={'size': '60'}),
        help_text=_('The name of the repository. This is the '
                    '&lt;repo_name&gt; in '
                    'http://github.com/&lt;org_name&gt;/&lt;repo_name&gt;/'))


class GitHubPrivateOrgForm(HostingServiceForm):
    github_private_org_name = forms.CharField(
        label=_('Organization name'),
        max_length=64,
        required=True,
        widget=forms.TextInput(attrs={'size': '60'}),
        help_text=_('The name of the organization. This is the '
                    '&lt;org_name&gt; in '
                    'http://github.com/&lt;org_name&gt;/&lt;repo_name&gt;/'))

    github_private_org_repo_name = forms.CharField(
        label=_('Repository name'),
        max_length=64,
        required=True,
        widget=forms.TextInput(attrs={'size': '60'}),
        help_text=_('The name of the repository. This is the '
                    '&lt;repo_name&gt; in '
                    'http://github.com/&lt;org_name&gt;/&lt;repo_name&gt;/'))


class GitHubAPIPaginator(APIPaginator):
    """Paginates over GitHub API list resources.

    This is returned by some GitHubClient functions in order to handle
    iteration over pages of results, without resorting to fetching all
    pages at once or baking pagination into the functions themselves.
    """
    start_query_param = 'page'
    per_page_query_param = 'per_page'

    LINK_RE = re.compile(r'\<(?P<url>[^>]+)\>; rel="(?P<rel>[^"]+)",? *')

    def fetch_url(self, url):
        """Fetches the page data from a URL."""
        data, headers = self.client.api_get(url, return_headers=True)

        # Find all the links in the Link header and key off by the link
        # name ('prev', 'next', etc.).
        links = dict(
            (m.group('rel'), m.group('url'))
            for m in self.LINK_RE.finditer(headers.get('Link', ''))
        )

        return {
            'data': data,
            'headers': headers,
            'prev_url': links.get('prev'),
            'next_url': links.get('next'),
        }


class GitHubClient(HostingServiceClient):
    RAW_MIMETYPE = 'application/vnd.github.v3.raw'

    def __init__(self, hosting_service):
        super(GitHubClient, self).__init__(hosting_service)
        self.account = hosting_service.account

    #
    # HTTP method overrides
    #

    def http_delete(self, url, *args, **kwargs):
        data, headers = super(GitHubClient, self).http_delete(
            url, *args, **kwargs)
        self._check_rate_limits(headers)
        return data, headers

    def http_get(self, url, *args, **kwargs):
        data, headers = super(GitHubClient, self).http_get(
            url, *args, **kwargs)
        self._check_rate_limits(headers)
        return data, headers

    def http_post(self, url, *args, **kwargs):
        data, headers = super(GitHubClient, self).http_post(
            url, *args, **kwargs)
        self._check_rate_limits(headers)
        return data, headers

    #
    # API wrappers around HTTP/JSON methods
    #

    def api_delete(self, url, *args, **kwargs):
        try:
            data, headers = self.json_delete(url, *args, **kwargs)
            return data
        except (URLError, HTTPError) as e:
            self._check_api_error(e)

    def api_get(self, url, return_headers=False, *args, **kwargs):
        """Performs an HTTP GET to the GitHub API and returns the results.

        If `return_headers` is True, then the result of each call (or
        each generated set of data, if using pagination) will be a tuple
        of (data, headers). Otherwise, the result will just be the data.
        """
        try:
            data, headers = self.json_get(url, *args, **kwargs)

            if return_headers:
                return data, headers
            else:
                return data
        except (URLError, HTTPError) as e:
            self._check_api_error(e)

    def api_get_list(self, url, start=None, per_page=None, *args, **kwargs):
        """Performs an HTTP GET to a GitHub API and returns a paginator.

        This returns a GitHubAPIPaginator that's used to iterate over the
        pages of results. Each page contains information on the data and
        headers from that given page.

        The ``start`` and ``per_page`` parameters can be used to control
        where pagination begins and how many results are returned per page.
        ``start`` is a 0-based index representing a page number.
        """
        if start is not None:
            # GitHub uses 1-based indexing, so add one.
            start += 1

        return GitHubAPIPaginator(self, url, start=start, per_page=per_page)

    def api_post(self, url, *args, **kwargs):
        try:
            data, headers = self.json_post(url, *args, **kwargs)
            return data
        except (URLError, HTTPError) as e:
            self._check_api_error(e)

    #
    # Higher-level API methods
    #

    def api_get_blob(self, repo_api_url, path, sha):
        url = self._build_api_url(repo_api_url, 'git/blobs/%s' % sha)

        try:
            return self.http_get(url, headers={
                'Accept': self.RAW_MIMETYPE,
            })[0]
        except (URLError, HTTPError):
            raise FileNotFoundError(path, sha)

    def api_get_commits(self, repo_api_url, branch=None, start=None):
        url = self._build_api_url(repo_api_url, 'commits')

        # Note that we don't always use the branch, since the GitHub API
        # doesn't support limiting by branch *and* starting at a SHA. So, the
        # branch argument can be safely ignored if a sha is provided.
        start = start or branch

        if start:
            url += '&sha=%s' % start

        try:
            return self.api_get(url)
        except Exception as e:
            logging.warning('Failed to fetch commits from %s: %s',
                            url, e, exc_info=1)
            raise SCMError(six.text_type(e))

    def api_get_compare_commits(self, repo_api_url, parent_revision, revision):
        # If the commit has a parent commit, use GitHub's "compare two commits"
        # API to get the diff. Otherwise, fetch the commit itself.
        if parent_revision:
            url = self._build_api_url(
                repo_api_url,
                'compare/%s...%s' % (parent_revision, revision))
        else:
            url = self._build_api_url(repo_api_url, 'commits/%s' % revision)

        try:
            comparison = self.api_get(url)
        except Exception as e:
            logging.warning('Failed to fetch commit comparison from %s: %s',
                            url, e, exc_info=1)
            raise SCMError(six.text_type(e))

        if parent_revision:
            tree_sha = comparison['base_commit']['commit']['tree']['sha']
        else:
            tree_sha = comparison['commit']['tree']['sha']

        return comparison['files'], tree_sha

    def api_get_heads(self, repo_api_url):
        url = self._build_api_url(repo_api_url, 'git/refs/heads')

        try:
            rsp = self.api_get(url)
            return [ref for ref in rsp if ref['ref'].startswith('refs/heads/')]
        except Exception as e:
            logging.warning('Failed to fetch commits from %s: %s',
                            url, e, exc_info=1)
            raise SCMError(six.text_type(e))

    def api_get_issue(self, repo_api_url, issue_id):
        url = self._build_api_url(repo_api_url, 'issues/%s' % issue_id)

        try:
            return self.api_get(url)
        except Exception as e:
            logging.warning('GitHub: Failed to fetch issue from %s: %s',
                            url, e, exc_info=1)
            raise SCMError(six.text_type(e))

    def api_get_remote_repositories(self, api_url, owner, owner_type,
                                    filter_type=None, start=None,
                                    per_page=None):
        url = api_url

        if owner_type == 'organization':
            url += 'orgs/%s/repos' % owner
        elif owner_type == 'user':
            if owner == self.account.username:
                # All repositories belonging to an authenticated user.
                url += 'user/repos'
            else:
                # Only public repositories for the user.
                url += 'users/%s/repos' % owner
        else:
            raise ValueError(
                "owner_type must be 'organization' or 'user', not %r'"
                % owner_type)

        if filter_type:
            url += '?type=%s' % (filter_type or 'all')

        return self.api_get_list(self._build_api_url(url),
                                 start=start, per_page=per_page)

    def api_get_remote_repository(self, api_url, owner, repository_id):
        try:
            return self.api_get(self._build_api_url(
                '%srepos/%s/%s' % (api_url, owner, repository_id)))
        except HostingServiceError as e:
            if e.http_code == 404:
                return None
            else:
                raise

    def api_get_tree(self, repo_api_url, sha, recursive=False):
        url = self._build_api_url(repo_api_url, 'git/trees/%s' % sha)

        if recursive:
            url += '&recursive=1'

        try:
            return self.api_get(url)
        except Exception as e:
            logging.warning('Failed to fetch tree from %s: %s',
                            url, e, exc_info=1)
            raise SCMError(six.text_type(e))

    #
    # Internal utilities
    #

    def _build_api_url(self, *api_paths):
        url = '/'.join(api_paths)

        if '?' in url:
            url += '&'
        else:
            url += '?'

        url += 'access_token=%s' % self.account.data['authorization']['token']

        return url

    def _check_rate_limits(self, headers):
        rate_limit_remaining = headers.get('X-RateLimit-Remaining', None)

        try:
            if (rate_limit_remaining is not None and
                int(rate_limit_remaining) <= 100):
                logging.warning('GitHub rate limit for %s is down to %s',
                                self.account.username, rate_limit_remaining)
        except ValueError:
            pass

    def _check_api_error(self, e):
        data = e.read()

        try:
            rsp = json.loads(data)
        except:
            rsp = None

        if rsp and 'message' in rsp:
            response_info = e.info()
            x_github_otp = response_info.get('X-GitHub-OTP', '')

            if x_github_otp.startswith('required;'):
                raise TwoFactorAuthCodeRequiredError(
                    _('Enter your two-factor authentication code. '
                      'This code will be sent to you by GitHub.'),
                    http_code=e.code)

            if e.code == 401:
                raise AuthorizationError(rsp['message'], http_code=e.code)

            raise HostingServiceError(rsp['message'], http_code=e.code)
        else:
            raise HostingServiceError(six.text_type(e), http_code=e.code)


class GitHub(HostingService, BugTracker):
    name = _('GitHub')
    plans = [
        ('public', {
            'name': _('Public'),
            'form': GitHubPublicForm,
            'repository_fields': {
                'Git': {
                    'path': 'git://github.com/%(hosting_account_username)s/'
                            '%(github_public_repo_name)s.git',
                    'mirror_path': 'git@github.com:'
                                   '%(hosting_account_username)s/'
                                   '%(github_public_repo_name)s.git',
                }
            },
            'bug_tracker_field': 'http://github.com/'
                                 '%(hosting_account_username)s/'
                                 '%(github_public_repo_name)s/'
                                 'issues#issue/%%s',
        }),
        ('public-org', {
            'name': _('Public Organization'),
            'form': GitHubPublicOrgForm,
            'repository_fields': {
                'Git': {
                    'path': 'git://github.com/%(github_public_org_name)s/'
                            '%(github_public_org_repo_name)s.git',
                    'mirror_path': 'git@github.com:%(github_public_org_name)s/'
                                   '%(github_public_org_repo_name)s.git',
                }
            },
            'bug_tracker_field': 'http://github.com/'
                                 '%(github_public_org_name)s/'
                                 '%(github_public_org_repo_name)s/'
                                 'issues#issue/%%s',
        }),
        ('private', {
            'name': _('Private'),
            'form': GitHubPrivateForm,
            'repository_fields': {
                'Git': {
                    'path': 'git@github.com:%(hosting_account_username)s/'
                            '%(github_private_repo_name)s.git',
                    'mirror_path': '',
                },
            },
            'bug_tracker_field': 'http://github.com/'
                                 '%(hosting_account_username)s/'
                                 '%(github_private_repo_name)s/'
                                 'issues#issue/%%s',
        }),
        ('private-org', {
            'name': _('Private Organization'),
            'form': GitHubPrivateOrgForm,
            'repository_fields': {
                'Git': {
                    'path': 'git@github.com:%(github_private_org_name)s/'
                            '%(github_private_org_repo_name)s.git',
                    'mirror_path': '',
                },
            },
            'bug_tracker_field': 'http://github.com/'
                                 '%(github_private_org_name)s/'
                                 '%(github_private_org_repo_name)s/'
                                 'issues#issue/%%s',
        }),
    ]

    needs_authorization = True
    supports_bug_trackers = True
    supports_post_commit = True
    supports_repositories = True
    supports_two_factor_auth = True
    supports_list_remote_repositories = True
    supported_scmtools = ['Git']

    has_repository_hook_instructions = True

    client_class = GitHubClient

    repository_url_patterns = patterns(
        '',

        url(r'^hooks/close-submitted/$',
            'reviewboard.hostingsvcs.github.post_receive_hook_close_submitted',
            name='github-hooks-close-submitted')
    )

    # This should be the prefix for every field on the plan forms.
    plan_field_prefix = 'github'

    def get_api_url(self, hosting_url):
        """Returns the API URL for GitHub.

        This can be overridden to provide more advanced lookup (intended
        for the GitHub Enterprise support).
        """
        assert not hosting_url
        return 'https://api.github.com/'

    def get_plan_field(self, plan, plan_data, name):
        """Returns the value of a field for plan-specific data.

        This takes into account the plan type and hosting service ID.
        """
        key = '%s_%s_%s' % (self.plan_field_prefix, plan.replace('-', '_'),
                            name)
        return plan_data[key]

    def check_repository(self, plan=None, *args, **kwargs):
        """Checks the validity of a repository.

        This will perform an API request against GitHub to get
        information on the repository. This will throw an exception if
        the repository was not found, and return cleanly if it was found.
        """
        try:
            repo_info = self.client.api_get(
                self._build_api_url(
                    self._get_repo_api_url_raw(
                        self._get_repository_owner_raw(plan, kwargs),
                        self._get_repository_name_raw(plan, kwargs))))
        except HostingServiceError as e:
            if e.http_code == 404:
                if plan in ('public', 'private'):
                    raise RepositoryError(
                        _('A repository with this name was not found, or your '
                          'user may not own it.'))
                elif plan == 'public-org':
                    raise RepositoryError(
                        _('A repository with this organization or name was '
                          'not found.'))
                elif plan == 'private-org':
                    raise RepositoryError(
                        _('A repository with this organization or name was '
                          'not found, or your user may not have access to '
                          'it.'))

            raise

        if 'private' in repo_info:
            is_private = repo_info['private']

            if is_private and plan in ('public', 'public-org'):
                raise RepositoryError(
                    _('This is a private repository, but you have selected '
                      'a public plan.'))
            elif not is_private and plan in ('private', 'private-org'):
                raise RepositoryError(
                    _('This is a public repository, but you have selected '
                      'a private plan.'))

    def authorize(self, username, password, hosting_url,
                  two_factor_auth_code=None, local_site_name=None,
                  *args, **kwargs):
        site = Site.objects.get_current()
        siteconfig = SiteConfiguration.objects.get_current()

        site_base_url = '%s%s' % (
            site.domain,
            local_site_reverse('root', local_site_name=local_site_name))

        site_url = '%s://%s' % (siteconfig.get('site_domain_method'),
                                site_base_url)

        note = 'Access for Review Board (%s - %s)' % (
            site_base_url,
            uuid.uuid4().hex[:7])

        try:
            body = {
                'scopes': [
                    'user',
                    'repo',
                ],
                'note': note,
                'note_url': site_url,
            }

            # If the site is using a registered GitHub application,
            # send it in the requests. This will gain the benefits of
            # a GitHub application, such as higher rate limits.
            if (hasattr(settings, 'GITHUB_CLIENT_ID') and
                hasattr(settings, 'GITHUB_CLIENT_SECRET')):
                body.update({
                    'client_id': settings.GITHUB_CLIENT_ID,
                    'client_secret': settings.GITHUB_CLIENT_SECRET,
                })

            headers = {}

            if two_factor_auth_code:
                headers['X-GitHub-OTP'] = two_factor_auth_code

            rsp, headers = self.client.json_post(
                url=self.get_api_url(hosting_url) + 'authorizations',
                username=username,
                password=password,
                headers=headers,
                body=json.dumps(body))
        except (HTTPError, URLError) as e:
            data = e.read()

            try:
                rsp = json.loads(data)
            except:
                rsp = None

            if rsp and 'message' in rsp:
                response_info = e.info()
                x_github_otp = response_info.get('X-GitHub-OTP', '')

                if x_github_otp.startswith('required;'):
                    raise TwoFactorAuthCodeRequiredError(
                        _('Enter your two-factor authentication code '
                          'and re-enter your password to link your account. '
                          'This code will be sent to you by GitHub.'))

                raise AuthorizationError(rsp['message'])
            else:
                raise AuthorizationError(six.text_type(e))

        self._save_auth_data(rsp)

    def is_authorized(self):
        return ('authorization' in self.account.data and
                'token' in self.account.data['authorization'])

    def get_reset_auth_token_requires_password(self):
        """Returns whether or not resetting the auth token requires a password.

        A password will be required if not using a GitHub client ID or
        secret.
        """
        if not self.is_authorized():
            return True

        app_info = self.account.data['authorization']['app']
        client_id = app_info.get('client_id', '')
        has_client = (client_id.strip('0') != '')

        return (not has_client or
                (not (hasattr(settings, 'GITHUB_CLIENT_ID') and
                      hasattr(settings, 'GITHUB_CLIENT_SECRET'))))

    def reset_auth_token(self, password=None, two_factor_auth_code=None):
        """Resets the authorization token for the linked account.

        This will attempt to reset the token in a few different ways,
        depending on how the token was granted.

        Tokens linked to a registered GitHub OAuth app can be reset without
        requiring any additional credentials.

        Tokens linked to a personal account (which is the case on most
        installations) require a password and possibly a two-factor auth
        code. Callers should call get_reset_auth_token_requires_password()
        before determining whether to pass a password, and should pass
        a two-factor auth code if this raises TwoFactorAuthCodeRequiredError.
        """
        if self.is_authorized():
            token = self.account.data['authorization']['token']
        else:
            token = None

        if self.get_reset_auth_token_requires_password():
            assert password

            if self.account.local_site:
                local_site_name = self.account.local_site.name
            else:
                local_site_name = None

            if token:
                try:
                    self._delete_auth_token(
                        self.account.data['authorization']['id'],
                        password=password,
                        two_factor_auth_code=two_factor_auth_code)
                except HostingServiceError as e:
                    # If we get a 404 Not Found, then the authorization was
                    # probably already deleted.
                    if e.http_code != 404:
                        raise

                self.account.data['authorization'] = ''
                self.account.save()

            # This may produce errors, which we want to bubble up.
            self.authorize(self.account.username, password,
                           self.account.hosting_url,
                           two_factor_auth_code=two_factor_auth_code,
                           local_site_name=local_site_name)
        else:
            # We can use the new API for resetting the token without
            # re-authenticating.
            auth_data = self._reset_authorization(
                settings.GITHUB_CLIENT_ID,
                settings.GITHUB_CLIENT_SECRET,
                token)
            self._save_auth_data(auth_data)

    def get_file(self, repository, path, revision, *args, **kwargs):
        repo_api_url = self._get_repo_api_url(repository)
        return self.client.api_get_blob(repo_api_url, path, revision)

    def get_file_exists(self, repository, path, revision, *args, **kwargs):
        try:
            repo_api_url = self._get_repo_api_url(repository)
            self.client.api_get_blob(repo_api_url, path, revision)
            return True
        except FileNotFoundError:
            return False

    def get_branches(self, repository):
        repo_api_url = self._get_repo_api_url(repository)
        refs = self.client.api_get_heads(repo_api_url)

        results = []
        for ref in refs:
            name = ref['ref'][len('refs/heads/'):]
            results.append(Branch(id=name,
                                  commit=ref['object']['sha'],
                                  default=(name == 'master')))

        return results

    def get_commits(self, repository, branch=None, start=None):
        repo_api_url = self._get_repo_api_url(repository)
        commits = self.client.api_get_commits(repo_api_url, branch=branch,
                                              start=start)

        results = []
        for item in commits:
            commit = Commit(
                item['commit']['author']['name'],
                item['sha'],
                item['commit']['committer']['date'],
                item['commit']['message'])
            if item['parents']:
                commit.parent = item['parents'][0]['sha']

            results.append(commit)

        return results

    def get_change(self, repository, revision):
        repo_api_url = self._get_repo_api_url(repository)

        # Step 1: fetch the commit itself that we want to review, to get
        # the parent SHA and the commit message. Hopefully this information
        # is still in cache so we don't have to fetch it again.
        commit = cache.get(repository.get_commit_cache_key(revision))
        if commit:
            author_name = commit.author_name
            date = commit.date
            parent_revision = commit.parent
            message = commit.message
        else:
            commit = self.client.api_get_commits(repo_api_url, revision)[0]

            author_name = commit['commit']['author']['name']
            date = commit['commit']['committer']['date']
            parent_revision = commit['parents'][0]['sha']
            message = commit['commit']['message']

        # Step 2: Get the diff and tree from the "compare commits" API
        files, tree_sha = self.client.api_get_compare_commits(
            repo_api_url, parent_revision, revision)

        # Step 3: fetch the tree for the original commit, so that we can get
        # full blob SHAs for each of the files in the diff.
        tree = self.client.api_get_tree(repo_api_url, tree_sha, recursive=True)

        file_shas = {}
        for file in tree['tree']:
            file_shas[file['path']] = file['sha']

        diff = []

        for file in files:
            filename = file['filename']
            status = file['status']
            try:
                patch = file['patch']
            except KeyError:
                continue

            diff.append('diff --git a/%s b/%s' % (filename, filename))

            if status == 'modified':
                old_sha = file_shas[filename]
                new_sha = file['sha']
                diff.append('index %s..%s 100644' % (old_sha, new_sha))
                diff.append('--- a/%s' % filename)
                diff.append('+++ b/%s' % filename)
            elif status == 'added':
                new_sha = file['sha']

                diff.append('new file mode 100644')
                diff.append('index %s..%s' % ('0' * 40, new_sha))
                diff.append('--- /dev/null')
                diff.append('+++ b/%s' % filename)
            elif status == 'removed':
                old_sha = file_shas[filename]

                diff.append('deleted file mode 100644')
                diff.append('index %s..%s' % (old_sha, '0' * 40))
                diff.append('--- a/%s' % filename)
                diff.append('+++ /dev/null')

            diff.append(patch)

        diff = '\n'.join(diff)

        # Make sure there's a trailing newline
        if not diff.endswith('\n'):
            diff += '\n'

        return Commit(author_name, revision, date, message, parent_revision,
                      diff=diff)

    def get_remote_repositories(self, owner=None, owner_type='user',
                                filter_type=None, start=None, per_page=None):
        """Return a list of remote repositories matching the given criteria.

        This will look up each remote repository on GitHub that the given
        owner either owns or is a member of.

        If the plan is an organization plan, then `owner` is expected to be
        an organization name, and the resulting repositories with be ones
        either owned by that organization or that the organization is a member
        of, and can be accessed by the authenticated user.

        If the plan is a public or private plan, and `owner` is the current
        user, then that user's public and private repositories or ones
        they're a member of will be returned.

        Otherwise, `owner` is assumed to be another GitHub user, and their
        accessible repositories that they own or are a member of will be
        returned.

        `owner` defaults to the linked account's username, and `plan`
        defaults to 'public'.
        """
        if owner is None and owner_type == 'user':
            owner = self.account.username

        assert owner

        url = self.get_api_url(self.account.hosting_url)
        paginator = self.client.api_get_remote_repositories(
            url, owner, owner_type, filter_type, start, per_page)

        return ProxyPaginator(
            paginator,
            normalize_page_data_func=lambda page_data: [
                RemoteRepository(
                    self,
                    repository_id='%s/%s' % (repo['owner']['login'],
                                             repo['name']),
                    name=repo['name'],
                    owner=repo['owner']['login'],
                    scm_type='Git',
                    path=repo['clone_url'],
                    mirror_path=repo['mirror_url'],
                    extra_data=repo)
                for repo in page_data
            ])

    def get_remote_repository(self, repository_id):
        """Get the remote repository for the ID.

        The ID is expected to be an ID returned from get_remote_repositories(),
        in the form of "owner/repo_id".

        If the repository is not found, ObjectDoesNotExist will be raised.
        """
        parts = repository_id.split('/')
        repo = None

        if len(parts) == 2:
            repo = self.client.api_get_remote_repository(
                self.get_api_url(self.account.hosting_url),
                *parts)

        if not repo:
            raise ObjectDoesNotExist

        return RemoteRepository(self,
                                repository_id=repository_id,
                                name=repo['name'],
                                owner=repo['owner']['login'],
                                scm_type='Git',
                                path=repo['clone_url'],
                                mirror_path=repo['mirror_url'],
                                extra_data=repo)

    def get_bug_info_uncached(self, repository, bug_id):
        """Get the bug info from the server."""
        result = {
            'summary': '',
            'description': '',
            'status': '',
        }

        repo_api_url = self._get_repo_api_url(repository)
        try:
            issue = self.client.api_get_issue(repo_api_url, bug_id)
            result = {
                'summary': issue['title'],
                'description': issue['body'],
                'status': issue['state'],
            }
        except:
            # Errors in fetching are already logged in api_get_issue
            pass

        return result

    def get_repository_hook_instructions(self, request, repository):
        """Returns instructions for setting up incoming webhooks."""
        plan = repository.extra_data['repository_plan']
        add_webhook_url = urljoin(
            self.account.hosting_url or 'https://github.com/',
            '%s/%s/settings/hooks/new'
            % (self._get_repository_owner_raw(plan, repository.extra_data),
               self._get_repository_name_raw(plan, repository.extra_data)))

        webhook_endpoint_url = build_server_url(local_site_reverse(
            'github-hooks-close-submitted',
            local_site=repository.local_site,
            kwargs={
                'repository_id': repository.pk,
                'hosting_service_id': repository.hosting_account.service_name,
            }))

        example_id = 123
        example_url = build_server_url(local_site_reverse(
            'review-request-detail',
            local_site=repository.local_site,
            kwargs={
                'review_request_id': example_id,
            }))

        return render_to_string(
            'hostingsvcs/github/repo_hook_instructions.html',
            RequestContext(request, {
                'example_id': example_id,
                'example_url': example_url,
                'repository': repository,
                'server_url': get_server_url(),
                'add_webhook_url': add_webhook_url,
                'webhook_endpoint_url': webhook_endpoint_url,
                'hook_uuid': repository.get_or_create_hooks_uuid(),
            }))

    def _reset_authorization(self, client_id, client_secret, token):
        """Resets the authorization info for an OAuth app-linked token.

        If the token is associated with a registered OAuth application,
        its token will be reset, without any authentication details required.
        """
        url = '%sapplications/%s/tokens/%s' % (
            self.get_api_url(self.account.hosting_url),
            client_id,
            token)

        # Allow any errors to bubble up
        return self.client.api_post(url=url,
                                    username=client_id,
                                    password=client_secret)

    def _delete_auth_token(self, auth_id, password, two_factor_auth_code=None):
        """Requests that an authorization token be deleted.

        This will delete the authorization token with the given ID. It
        requires a password and, depending on the settings, a two-factor
        authentication code to perform the deletion.
        """
        headers = {}

        if two_factor_auth_code:
            headers['X-GitHub-OTP'] = two_factor_auth_code

        url = self._build_api_url(
            '%sauthorizations/%s' % (
                self.get_api_url(self.account.hosting_url),
                auth_id))

        self.client.api_delete(url=url,
                               headers=headers,
                               username=self.account.username,
                               password=password)

    def _save_auth_data(self, auth_data):
        """Saves authorization data sent from GitHub."""
        self.account.data['authorization'] = auth_data
        self.account.save()

    def _build_api_url(self, *api_paths):
        return self.client._build_api_url(*api_paths)

    def _get_repo_api_url(self, repository):
        plan = repository.extra_data['repository_plan']

        return self._get_repo_api_url_raw(
            self._get_repository_owner_raw(plan, repository.extra_data),
            self._get_repository_name_raw(plan, repository.extra_data))

    def _get_repo_api_url_raw(self, owner, repo_name):
        return '%srepos/%s/%s' % (self.get_api_url(self.account.hosting_url),
                                  owner, repo_name)

    def _get_repository_owner_raw(self, plan, extra_data):
        if plan in ('public', 'private'):
            return self.account.username
        elif plan in ('public-org', 'private-org'):
            return self.get_plan_field(plan, extra_data, 'name')
        else:
            raise InvalidPlanError(plan)

    def _get_repository_name_raw(self, plan, extra_data):
        return self.get_plan_field(plan, extra_data, 'repo_name')


@require_POST
def post_receive_hook_close_submitted(request, local_site_name=None,
                                      repository_id=None,
                                      hosting_service_id=None):
    """Closes review requests as submitted automatically after a push."""
    hook_event = request.META.get('HTTP_X_GITHUB_EVENT')

    if hook_event == 'ping':
        # GitHub is checking that this hook is valid, so accept the request
        # and return.
        return HttpResponse()
    elif hook_event != 'push':
        return HttpResponseBadRequest(
            'Only "ping" and "push" events are supported.')

    repository = get_repository_for_hook(repository_id, hosting_service_id,
                                         local_site_name)

    # Validate the hook against the stored UUID.
    m = hmac.new(bytes(repository.get_or_create_hooks_uuid()), request.body,
                 hashlib.sha1)

    sig_parts = request.META.get('HTTP_X_HUB_SIGNATURE').split('=')

    if sig_parts[0] != 'sha1' or len(sig_parts) != 2:
        # We don't know what this is.
        return HttpResponseBadRequest('Unsupported HTTP_X_HUB_SIGNATURE')

    if m.hexdigest() != sig_parts[1]:
        return HttpResponseBadRequest('Bad signature.')

    try:
        payload = json.loads(request.body)
    except ValueError as e:
        logging.error('The payload is not in JSON format: %s', e)
        return HttpResponseBadRequest('Invalid payload format')

    server_url = get_server_url(request=request)
    review_request_id_to_commits = \
        _get_review_request_id_to_commits_map(payload, server_url, repository)

    if review_request_id_to_commits:
        close_all_review_requests(review_request_id_to_commits,
                                  local_site_name, repository,
                                  hosting_service_id)

    return HttpResponse()


def _get_review_request_id_to_commits_map(payload, server_url, repository):
    """Returns a dictionary, mapping a review request ID to a list of commits.

    If a commit's commit message does not contain a review request ID,
    we append the commit to the key None.
    """
    review_request_id_to_commits_map = defaultdict(list)

    ref_name = payload.get('ref')
    if not ref_name:
        return None

    branch_name = get_git_branch_name(ref_name)
    if not branch_name:
        return None

    commits = payload.get('commits', [])

    for commit in commits:
        commit_hash = commit.get('id')
        commit_message = commit.get('message')
        review_request_id = get_review_request_id(commit_message, server_url,
                                                  commit_hash, repository)

        review_request_id_to_commits_map[review_request_id].append(
            '%s (%s)' % (branch_name, commit_hash[:7]))

    return review_request_id_to_commits_map
