"""Hosting service for GitHub.

Version Added:
    9.0:
    Split up :py:mod:`reviewboard.hostingsvcs.github`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import urljoin

from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from django.template.loader import render_to_string
from django.urls import path
from django.utils.translation import gettext, gettext_lazy as _
from housekeeping import deprecate_non_keyword_only_args

from reviewboard.admin.server import build_server_url, get_server_url
from reviewboard.deprecation import RemovedInReviewBoard10_0Warning
from reviewboard.hostingsvcs.base.bug_tracker import BaseBugTracker
from reviewboard.hostingsvcs.base.hosting_service import BaseHostingService
from reviewboard.hostingsvcs.errors import (
    AuthorizationError,
    HostingServiceError,
    InvalidPlanError,
    RepositoryError,
)
from reviewboard.hostingsvcs.github.client import GitHubClient
from reviewboard.hostingsvcs.github.forms import (
    GitHubAuthForm,
    GitHubPublicForm,
    GitHubPublicOrgForm,
    GitHubPrivateForm,
    GitHubPrivateOrgForm,
)
from reviewboard.hostingsvcs.github.views import GitHubHookViews
from reviewboard.hostingsvcs.repository import RemoteRepository
from reviewboard.hostingsvcs.utils.paginator import ProxyPaginator
from reviewboard.scmtools.core import Branch, Commit
from reviewboard.scmtools.crypto_utils import encrypt_password
from reviewboard.site.urlresolvers import local_site_reverse

if TYPE_CHECKING:
    from reviewboard.hostingsvcs.base.bug_tracker import BugInfo
    from reviewboard.scmtools.models import Repository


#: A list of the scopes that Review Board requires for classic tokens.
#:
#: Fine-grained Personal Access Tokens use a different permission model and
#: don't return scopes via the ``X-OAuth-Scopes`` header, so this list only
#: applies to classic Personal Access Tokens.
_REQUIRED_SCOPES = ['repo']


def _is_fine_grained_pat(
    token: str,
) -> bool:
    """Return whether a GitHub token is a fine-grained Personal Access Token.

    Fine-grained Personal Access Tokens are prefixed with ``github_pat_``.
    Everything else is treated as classic and validated via the X-Oauth-Scopes
    header.

    Version Added:
        8.0

    Args:
        token (str):
            The token to check.

    Returns:
        bool:
        ``True`` if the token is a fine-grained PAT, ``False`` otherwise.
    """
    return token.startswith('github_pat_')


class GitHub(BaseHostingService, BaseBugTracker):
    """Hosting service for GitHub."""

    name = _('GitHub')
    hosting_service_id = 'github'
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

    auth_form = GitHubAuthForm

    needs_authorization = True
    supports_bug_trackers = True
    supports_post_commit = True
    supports_repositories = True
    supports_list_remote_repositories = True
    supported_scmtools = ['Git']

    has_repository_hook_instructions = True

    client_class = GitHubClient

    repository_url_patterns = [
        path('hooks/close-submitted/',
             GitHubHookViews.post_receive_hook_close_submitted,
             name='github-hooks-close-submitted')
    ]

    # This should be the prefix for every field on the plan forms.
    plan_field_prefix = 'github'

    #: A list of the scopes that Review Board requires.
    REQUIRED_SCOPES = _REQUIRED_SCOPES

    _ORG_ACCESS_SUPPORT_URL = (
        'https://beanbag.freshdesk.com/solution/articles/3000045767'
        '-granting-organization-access-on-github'
    )

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

    @deprecate_non_keyword_only_args(RemovedInReviewBoard10_0Warning)
    def check_repository(
        self,
        *,
        plan: str,
        **kwargs,
    ) -> None:
        """Check the validity of a repository.

        This will perform an API request against GitHub to get
        information on the repository. This will throw an exception if
        the repository was not found, and return cleanly if it was found.

        Version Changed:
            8.0:
            Made arguments keyword-only.

        Args:
            plan (str):
                The ID of the plan that the repository is on.

            **kwargs (dict, unused):
                Additional keyword arguments passed by the repository form.

        Raises:
            reviewboard.hostingsvcs.errors.RepositoryError:
                The repository is not valid.
        """
        repo_api_url = self._get_repo_api_url_raw(
            self._get_repository_owner_raw(plan, kwargs),
            self._get_repository_name_raw(plan, kwargs))

        try:
            rsp = self.client.http_get(repo_api_url)
            repo_info = rsp.json
        except HostingServiceError as e:
            if e.http_code == 404:
                if plan in {'public', 'private'}:
                    raise RepositoryError(
                        gettext('A repository with this name was not found, '
                                'or your user may not own it.'))
                elif plan == 'public-org':
                    raise RepositoryError(
                        gettext('A repository with this organization or '
                                'name was not found.'))
                elif plan == 'private-org':
                    raise RepositoryError(
                        gettext('A repository with this organization or name '
                                'was not found, or your user may not have '
                                'access to it.'),
                        help_link=self._ORG_ACCESS_SUPPORT_URL,
                        help_link_text=gettext(
                            'Get help on granting access.'))

            raise

        if 'private' in repo_info:
            is_private = repo_info['private']

            if is_private and plan in {'public', 'public-org'}:
                raise RepositoryError(
                    gettext('This is a private repository, but you have '
                            'selected a public plan.'))
            elif not is_private and plan in {'private', 'private-org'}:
                raise RepositoryError(
                    gettext('This is a public repository, but you have '
                            'selected a private plan.'))

        # Make a request to an endpoint that requires the "Contents" permission
        # to verify that a fine-grained PAT has the correct permissions. We
        # use /branches rather than /git/refs/heads because the latter returns
        # HTTP 409 on empty repositories.
        try:
            self.client.http_get(f'{repo_api_url}/branches')
        except HostingServiceError as e:
            if (e.http_code == 403 and
                'Resource not accessible by personal access token' in str(e)):
                raise RepositoryError(gettext(
                    'Your token can access this repository\'s metadata but '
                    'cannot read its contents. For fine-grained Personal '
                    'Access Tokens, ensure "Contents: Read" is granted on '
                    'this repository.'
                ))

            raise

    @deprecate_non_keyword_only_args(RemovedInReviewBoard10_0Warning)
    def authorize(
        self,
        *,
        username: str | None,
        password: str | None,
        hosting_url: (str | None) = None,
        local_site_name: (str | None) = None,
        **kwargs,
    ) -> None:
        """Authorize an account for the hosting service.

        Version Changed:
            8.0:
            Made arguments keyword-only.

        Args:
            username (str):
                The username for the account.

            password (str):
                The Personal Access Token for the account.

            hosting_url (str, optional):
                The hosting URL for the service, if self-hosted.

            local_site_name (str, optional):
                The Local Site name, if any, that the account should be
                bound to.

            **kwargs (dict, unused):
                Extra keyword arguments containing values from the
                repository's configuration.

        Raises:
            reviewboard.hostingsvcs.errors.AuthorizationError:
                The credentials provided were not valid.
        """
        api_url = self.get_api_url(hosting_url)

        # Try to reach an API resource with the provided credentials.
        rsp = self.client.http_get(
            f'{api_url}user',
            username=username,
            password=password)

        # Fine-grained Personal Access Tokens don't return scopes via the
        # X-OAuth-Scopes header. The /user call above already validated the
        # token; per-repository permission errors will surface naturally
        # during check_repository or normal SCM operations.
        if not _is_fine_grained_pat(password or ''):
            # Check to make sure this classic token has all the necessary
            # scopes.
            scopes_header = rsp.get_header('x-oauth-scopes', '')
            assert scopes_header is not None

            token_scopes = set(scopes_header.split(', '))
            missing_scopes = set(self.REQUIRED_SCOPES) - token_scopes

            if missing_scopes:
                raise AuthorizationError(
                    _('This GitHub classic Personal Access Token must have '
                      'the following scopes enabled: %(scopes)s')
                    % {
                        'scopes': ', '.join(sorted(missing_scopes)),
                    })

        if 'authorization' in self.account.data:
            # This is an older GitHub linked account, which used the legacy
            # authorizations API to generate the token. This stopped being
            # supported in Review Board 3.0.18.
            del self.account.data['authorization']

        self.account.data['personal_token'] = encrypt_password(password)
        self.account.save()

    def is_authorized(self):
        """Return whether or not the account is currently authorized.

        This will check for both a configured Personal Access Token
        (introduced in Review Board 3.0.18) and a legacy
        authorizations-generated OAuth Token.

        Returns:
            bool:
            Whether or not the associated account is authorized.
        """
        account_data = self.account.data

        if account_data.get('personal_token'):
            # This is a newer linked account using a GitHub user's custom
            # Personal Access Token. Support for this was introduced in
            # Review Board 3.0.18.
            return True

        # Check for a legacy authorizations-generated API token.
        return ('authorization' in account_data and
                'token' in account_data['authorization'])

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

        # A lot of repositories are starting to use alternative names for
        # their mainline branch, and GitHub doesn't have a good way for us to
        # know which one is which. Until this is better defined, we'll still
        # prefer "master" when available, then look for "main", and finally
        # make sure that at least one branch is marked as default.
        master_ref = None
        main_ref = None

        for i, ref in enumerate(refs):
            name = ref['ref'][len('refs/heads/'):]
            results.append(Branch(id=name,
                                  commit=ref['object']['sha']))

            if name == 'master':
                master_ref = i
            elif name == 'main':
                main_ref = i

        if master_ref is not None:
            results[master_ref].default = True
        elif main_ref is not None:
            results[main_ref].default = True
        elif len(results) > 0:
            results[0].default = True

        return results

    def get_commits(self, repository, branch=None, start=None):
        repo_api_url = self._get_repo_api_url(repository)
        commits = self.client.api_get_commits(repo_api_url, branch=branch,
                                              start=start)

        results = []

        for item in commits:
            commit = Commit(
                author_name=item['commit']['author']['name'],
                id=item['sha'],
                date=item['commit']['committer']['date'],
                message=item['commit']['message'])

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

        file_shas = {
            f['path'].encode('utf-8'): f['sha'].encode('utf-8')
            for f in tree['tree']
        }

        diff = []

        for f in files:
            filename = f['filename'].encode('utf-8')
            status = f['status']

            try:
                patch = f['patch'].encode('utf-8')
            except KeyError:
                continue

            diff.append(b'diff --git a/%s b/%s' % (filename, filename))

            if status == 'modified':
                old_sha = file_shas[filename]
                new_sha = f['sha'].encode('utf-8')
                diff.append(b'index %s..%s 100644' % (old_sha, new_sha))
                diff.append(b'--- a/%s' % filename)
                diff.append(b'+++ b/%s' % filename)
            elif status == 'added':
                new_sha = f['sha'].encode('utf-8')

                diff.append(b'new file mode 100644')
                diff.append(b'index %s..%s' % (b'0' * 40, new_sha))
                diff.append(b'--- /dev/null')
                diff.append(b'+++ b/%s' % filename)
            elif status == 'removed':
                old_sha = file_shas[filename]

                diff.append(b'deleted file mode 100644')
                diff.append(b'index %s..%s' % (old_sha, b'0' * 40))
                diff.append(b'--- a/%s' % filename)
                diff.append(b'+++ /dev/null')
            elif status == 'renamed':
                old_filename = f['previous_filename'].encode('utf-8')
                old_sha = file_shas[old_filename]
                new_sha = f['sha'].encode('utf-8')

                diff.append(b'rename from %s' % old_filename)
                diff.append(b'rename to %s' % filename)
                diff.append(b'index %s..%s' % (old_sha, new_sha))
                diff.append(b'--- a/%s' % old_filename)
                diff.append(b'+++ b/%s' % filename)

            diff.append(patch)

        if diff and not diff[-1].endswith(b'\n'):
            # Make sure there's a trailing newline.
            diff.append(b'')

        diff = b'\n'.join(diff)

        return Commit(author_name=author_name,
                      id=revision,
                      date=date,
                      message=message,
                      parent=parent_revision,
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

    def get_bug_info_uncached(
        self,
        repository: Repository,
        bug_id: str,
    ) -> BugInfo:
        """Return the information for the specified bug.

        Args:
            repository (reviewboard.scmtools.models.Repository):
                The repository object.

            bug_id (str):
                The ID of the bug to fetch.

        Returns:
            reviewboard.hostingsvcs.base.bug_tracker.BugInfo:
            Information about the bug.
        """
        result: BugInfo = {
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
        except Exception:
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
            template_name='hostingsvcs/github/repo_hook_instructions.html',
            request=request,
            context={
                'example_id': example_id,
                'example_url': example_url,
                'repository': repository,
                'server_url': get_server_url(),
                'add_webhook_url': add_webhook_url,
                'webhook_endpoint_url': webhook_endpoint_url,
                'hook_uuid': repository.get_or_create_hooks_uuid(),
            })

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
