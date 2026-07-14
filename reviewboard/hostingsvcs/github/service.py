"""Hosting service for GitHub.

Version Added:
    9.0:
    Split up :py:mod:`reviewboard.hostingsvcs.github`.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import TYPE_CHECKING
from urllib.parse import quote as urlquote, urljoin, urlparse

from django.db.models import ObjectDoesNotExist
from django.template.loader import render_to_string
from django.urls import path
from django.utils.translation import gettext, gettext_lazy as _
from housekeeping import deprecate_non_keyword_only_args

from reviewboard.admin.server import build_server_url, get_server_url
from reviewboard.deprecation import RemovedInReviewBoard10_0Warning
from reviewboard.hostingsvcs.base.bug_tracker import BaseBugTracker
from reviewboard.hostingsvcs.base.connect_ui import BaseHostingServiceConnectUI
from reviewboard.hostingsvcs.base.hosting_service import BaseHostingService
from reviewboard.hostingsvcs.base.paginator import ProxyPaginator
from reviewboard.hostingsvcs.errors import (
    AuthorizationError,
    HostingServiceError,
    InvalidPlanError,
    RepositoryError,
)
from reviewboard.hostingsvcs.github import views
from reviewboard.hostingsvcs.github.accounts import (
    GitHubAppInstallationData,
    InstallationStatus,
    get_app_settings_url,
    get_github_app_data,
    get_github_app_role,
    is_app_record_account,
    is_app_record_data,
    is_installation_account,
    is_installation_data,
)
from reviewboard.hostingsvcs.github.client import GitHubClient, get_github_urls
from reviewboard.hostingsvcs.github.forms import (
    GitHubAuthForm,
    GitHubPrivateForm,
    GitHubPrivateOrgForm,
    GitHubPublicForm,
    GitHubPublicOrgForm,
)
from reviewboard.hostingsvcs.models import HostingServiceAccount
from reviewboard.hostingsvcs.repository import RemoteRepository
from reviewboard.scmtools.core import Branch, Commit
from reviewboard.scmtools.crypto_utils import encrypt_password
from reviewboard.site.urlresolvers import local_site_reverse

if TYPE_CHECKING:
    from collections.abc import Mapping
    from typing import Any, ClassVar, Literal, TypeAlias

    from django.http import HttpRequest
    from django.urls import _AnyURL
    from django.utils.safestring import SafeString
    from typelets.django.strings import StrOrPromise

    from reviewboard.hostingsvcs.base.bug_tracker import BugInfo
    from reviewboard.hostingsvcs.base.connect_ui import (
        AdminServicesListAccountMenuItem,
        AdminServicesListAttentionItem,
    )
    from reviewboard.hostingsvcs.base.forms import BaseHostingServiceAuthForm
    from reviewboard.hostingsvcs.base.hosting_service import HostingServicePlan
    from reviewboard.hostingsvcs.utils.paginator import BasePaginator
    from reviewboard.scmtools.models import Repository

    GitHubPlanName: TypeAlias = Literal[
        'public',
        'public-org',
        'private',
        'private-org',
    ]


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


def _get_installation_status_label(
    status: InstallationStatus,
) -> StrOrPromise | None:
    """Return the human-readable label for an installation status.

    This is the text shown for a suspended or removed install, both on the
    account's badge and in the "needs attention" alert.

    Version Added:
        9.0

    Args:
        status (reviewboard.hostingsvcs.github.accounts.InstallationStatus):
            The installation status.

    Returns:
        str:
        The label, or ``None`` if the status is active or unrecognized.
    """
    if status == InstallationStatus.SUSPENDED:
        return _('Suspended on GitHub')

    if status == InstallationStatus.REMOVED:
        return _('Removed on GitHub')

    return None


class GitHubConnectUI(BaseHostingServiceConnectUI):
    """Connect UI for GitHub.

    Version Added:
        9.0
    """

    connected_services_list_entry_template: ClassVar[str] = \
        'hostingsvcs/github/connected_services_list_entry.html'

    def render_connect_ui(
        self,
        request: HttpRequest,
        *,
        form: (BaseHostingServiceAuthForm | None) = None,
    ) -> SafeString:
        """Render the connect UI for GitHub.

        By default, this shows the list of connection methods. When requested
        with ``?method=pat``, it shows the Personal Access Token form on its
        own page instead.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            form (reviewboard.hostingsvcs.base.forms.
                  BaseHostingServiceAuthForm, optional):
                The authentication form to render.

        Returns:
            django.utils.safestring.SafeString:
            The rendered connect UI.
        """
        if request.GET.get('method') == 'pat':
            return super().render_connect_ui(request, form=form)

        if form is None:
            form = self.get_auth_form_class()(
                hosting_service_cls=self._hosting_service_cls,
                local_site=request.local_site)

        return render_to_string(
            'hostingsvcs/github/connect_choice.html',
            self.make_connect_ui_context(request, form=form),
            request=request)

    def make_connect_ui_context(
        self,
        request: HttpRequest,
        *,
        form: BaseHostingServiceAuthForm,
    ) -> dict[str, Any]:
        """Return template context for rendering the connect UI.

        This adds the URLs for the GitHub App flows, which are offered
        alongside the standard Personal Access Token form. If no GitHub App
        has been created yet, the "Create a GitHub App" flow is offered;
        otherwise, the "Connect another organization" (install) flow is
        offered.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            form (reviewboard.hostingsvcs.base.forms.
                  BaseHostingServiceAuthForm):
                The authentication form to render.

        Returns:
            dict:
            Template context to use when rendering the connect UI.
        """
        context = super().make_connect_ui_context(request, form=form)

        # Find the hidden app-record account (if any) and build the list of
        # connected accounts a repository can be added to. The app-record
        # account holds the app's credentials and is what the install link
        # acts on; it is not a usable connection on its own, so it is
        # excluded from the connected accounts.
        app_account: (HostingServiceAccount | None) = None
        connected_accounts: list[dict[str, Any]] = []

        service = self._hosting_service_cls

        accounts = HostingServiceAccount.objects.filter(
            service_name=service.hosting_service_id,
            local_site=request.local_site)

        for account in accounts:
            app_data = get_github_app_data(account)

            if is_app_record_data(app_data):
                app_account = account
            else:
                if is_installation_data(app_data):
                    avatar_url = app_data.owner_avatar_url
                    is_app_install = True
                else:
                    avatar_url = ''
                    is_app_install = False

                connected_accounts.append({
                    'avatar_url': avatar_url,
                    'is_app_install': is_app_install,
                    'username': account.username,
                })

        github_app_create_url: (str | None) = None
        github_app_install_url: (str | None) = None

        if app_account is None:
            github_app_create_url = local_site_reverse(
                'github-app-create',
                request=request,
                kwargs={
                    'hosting_service_id': service.hosting_service_id,
                })
        else:
            github_app_install_url = local_site_reverse(
                'github-app-install',
                local_site=app_account.local_site,
                kwargs={
                    'hosting_service_id': service.hosting_service_id,
                    'account_id': app_account.pk,
                })

        context['connected_accounts'] = connected_accounts
        context['github_app_create_url'] = github_app_create_url
        context['github_app_install_url'] = github_app_install_url
        context['github_logo'] = service.logo_image

        return context

    def make_connected_services_list_entry_context(
        self,
        request: HttpRequest,
        *,
        accounts: Sequence[HostingServiceAccount],
    ) -> dict[str, Any]:
        """Return template context for rendering the accounts list entry.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            accounts (list of
                      reviewboard.hostingsvcs.models.HostingServiceAccount):
                The connected hosting service accounts.

        Returns:
            dict:
            Template context to use when rendering the entry.
        """
        for account in accounts:
            if is_app_record_account(account):
                app_account = account
                break
        else:
            app_account = None

        github_app_create_url: (str | None) = None
        github_app_install_url: (str | None) = None
        github_app_replace_key_url: (str | None) = None
        github_app_settings_url: (str | None) = None

        service = self._hosting_service_cls

        if app_account is None:
            github_app_create_url = local_site_reverse(
                'github-app-create',
                request=request,
                kwargs={
                    'hosting_service_id': service.hosting_service_id,
                })
        else:
            github_app_install_url = local_site_reverse(
                'github-app-install',
                local_site=app_account.local_site,
                kwargs={
                    'account_id': app_account.pk,
                    'hosting_service_id': service.hosting_service_id,
                })
            github_app_replace_key_url = local_site_reverse(
                'github-app-replace-key',
                local_site=app_account.local_site,
                kwargs={
                    'account_id': app_account.pk,
                    'hosting_service_id': service.hosting_service_id,
                })
            github_app_settings_url = get_app_settings_url(app_account)

        context = super().make_connected_services_list_entry_context(
            request,
            accounts=accounts)

        # Flag each account entry as either a GitHub App installation or a
        # Personal Access Token, so the template can group them, and build a
        # sized avatar URL for the app installs.
        for entry in context['accounts_data']:
            account = entry['account']
            app_data = get_github_app_data(account)

            if is_installation_data(app_data):
                avatar_url = app_data.owner_avatar_url
                entry['is_app_install'] = True

                status = app_data.status
                entry['app_status'] = status
                entry['app_status_label'] = _get_installation_status_label(
                    status)
                entry['app_needs_reconnect'] = (
                    status != InstallationStatus.ACTIVE)
            else:
                avatar_url = None
                entry['is_app_install'] = False

            if avatar_url:
                # Request a 40px avatar. Merge into the existing query string
                # if the URL already has one (the avatar URL is an opaque value
                # that we get from GitHub, and they've been known to change
                # them around in the past).
                if '?' in avatar_url:
                    avatar_url = f'{avatar_url}&s=40'
                else:
                    avatar_url = f'{avatar_url}?s=40'

            entry['avatar_url'] = avatar_url

        return {
            **context,
            'github_app_create_url': github_app_create_url,
            'github_app_install_url': github_app_install_url,
            'github_app_installed': app_account is not None,
            'github_app_replace_key_url': github_app_replace_key_url,
            'github_app_settings_url': github_app_settings_url,
        }

    def get_connected_services_list_account_menu_items(
        self,
        request: HttpRequest,
        *,
        account: HostingServiceAccount,
    ) -> Sequence[AdminServicesListAccountMenuItem]:
        """Return the menu items for an account in the admin list.

        App installation accounts have no stored credentials to edit, so they
        do not get the default "Edit Credentials" item. Installations that
        have been suspended or removed on GitHub get a "Reconnect" item (see
        :py:meth:`get_reconnect_url`).

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            account (reviewboard.hostingsvcs.models.HostingServiceAccount):
                The account the menu is for.

        Returns:
            list of reviewboard.hostingsvcs.base.hosting_service.
            AdminServicesListAccountMenuItem:
            The menu items to show for the account.
        """
        if is_installation_account(account):
            if (reconnect_item := self._get_reconnect_menu_item(account)):
                return [reconnect_item]
            else:
                return []

        return super().get_connected_services_list_account_menu_items(
            request,
            account=account)

    def get_connected_services_list_attention_items(
        self,
        request: HttpRequest,
        *,
        accounts: Sequence[HostingServiceAccount],
    ) -> Sequence[AdminServicesListAttentionItem]:
        """Return installations needing attention for the admin list.

        Installations that GitHub has suspended or removed are reported, each
        with the "Reconnect" action that resolves the problem, so the page can
        list them in the aggregate "needs attention" alert.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            accounts (list of
                      reviewboard.hostingsvcs.models.HostingServiceAccount):
                The connected accounts for this service.

        Returns:
            list of reviewboard.hostingsvcs.base.hosting_service.
            AdminServicesListAttentionItem:
            The installations needing attention.
        """
        service = self._hosting_service_cls
        service_name = service.name
        service_id = service.hosting_service_id
        assert service_name is not None
        assert service_id is not None

        items: list[AdminServicesListAttentionItem] = []

        for account in accounts:
            app_data = get_github_app_data(account)

            if not is_installation_data(app_data):
                continue

            message = _get_installation_status_label(app_data.status)

            if message is None:
                continue

            item: AdminServicesListAttentionItem = {
                'account_id': account.pk,
                'account_label': account.username,
                'message': message,
                'service_id': service_id,
                'service_name': service_name,
            }

            reconnect_item = self._get_reconnect_menu_item(account)

            if reconnect_item is not None:
                item['action'] = reconnect_item

            items.append(item)

        return items

    def _get_reconnect_menu_item(
        self,
        account: HostingServiceAccount,
    ) -> AdminServicesListAccountMenuItem | None:
        """Return the "Reconnect" menu item for an installation, or None.

        Args:
            account (reviewboard.hostingsvcs.models.HostingServiceAccount):
                The installation account.

        Returns:
            reviewboard.hostingsvcs.base.hosting_service.
            AdminServicesListAccountMenuItem:
            The reconnect item, or ``None`` if the install does not need
            reconnecting.
        """
        app_data = get_github_app_data(account)

        if (not is_installation_data(app_data) or
            app_data.status == InstallationStatus.ACTIVE):
            return None

        service = self._hosting_service_cls

        # This links to the reconnect view rather than directly to GitHub.
        # The stored status may be stale (webhook deliveries can be missed),
        # so the view first verifies the state with GitHub, repairing it if
        # the problem was already resolved, and only forwards to GitHub if
        # the problem still exists (see get_reconnect_url).
        return {
            'id': 'reconnect',
            'label': _('Reconnect'),
            'url': local_site_reverse(
                'github-app-reconnect',
                local_site=account.local_site,
                kwargs={
                    'hosting_service_id': service.hosting_service_id,
                    'account_id': account.pk,
                }),
        }

    def get_reconnect_url(
        self,
        account: HostingServiceAccount,
    ) -> str | None:
        """Return the URL that resolves an installation's problem, or None.

        This is where the reconnect view forwards the administrator once it
        has confirmed with GitHub that the problem still exists. A suspended
        install still exists on GitHub, so this links straight to that
        installation's settings page, where it can be reviewed and
        unsuspended. A removed install is gone from GitHub, so this sends the
        administrator back through the install flow to reinstall it.

        Args:
            account (reviewboard.hostingsvcs.models.HostingServiceAccount):
                The installation account.

        Returns:
            str:
            The reconnect URL, or ``None`` if the install does not need
            reconnecting or is missing the data needed to build the URL.
        """
        app_data = get_github_app_data(account)

        if not is_installation_data(app_data):
            return None

        status = app_data.status

        if status == InstallationStatus.SUSPENDED:
            return self._get_installation_settings_url(account)

        if status == InstallationStatus.REMOVED:
            # A removed install no longer exists on GitHub. Send the admin back
            # through the install flow, keyed on the hidden app-record account
            # that the installation stores by primary key.
            app_data = get_github_app_data(account)
            assert isinstance(app_data, GitHubAppInstallationData)

            service = self._hosting_service_cls

            url = local_site_reverse(
                'github-app-install',
                local_site=account.local_site,
                kwargs={
                    'hosting_service_id': service.hosting_service_id,
                    'account_id': app_data.app_account_id,
                })

            # Deep-link to the account the app was removed from, so GitHub
            # pre-selects it instead of showing the account chooser.
            owner_id = app_data.owner_id

            if owner_id is not None:
                url = f'{url}?target_id={owner_id}'

            return url

        return None

    def get_repository_display_path(
        self,
        repository: Repository,
    ) -> str:
        """Return the ``owner/repo`` identifier for a repository.

        Version Added:
            9.0

        Args:
            repository (reviewboard.scmtools.models.Repository):
                The repository to return a display path for.

        Returns:
            str:
            The ``owner/repo`` identifier, or the raw path if it could not
            be parsed.
        """
        path = repository.path or ''
        parsed = urlparse(path)

        if parsed.netloc:
            # A full URL. urlparse has already separated off the host, along
            # with any credentials and port.
            name = parsed.path
        else:
            # Not a URL, so look for a host to strip off the front.
            m = GitHub._HOST_PREFIX_RE.match(path)

            if m is None:
                return path

            name = path[m.end():]

        name = name.strip('/').removesuffix('.git')

        return name or path

    def get_account_filter_label(
        self,
        account: HostingServiceAccount,
    ) -> str:
        """Return the account label, marking Personal Access Token accounts.

        A GitHub account can be an app installation or a Personal Access
        Token (PAT). When a PAT and an app installation share a username,
        their plain names are identical, so PAT accounts are tagged with
        "(PAT)" to tell them apart.

        Version Added:
            9.0

        Args:
            account (reviewboard.hostingsvcs.models.HostingServiceAccount):
                The account to return a label for.

        Returns:
            str:
            The label to show for the account.
        """
        label = super().get_account_filter_label(account)

        if get_github_app_role(account) is None:
            # An account with no GitHub App role is a Personal Access Token.
            label = gettext('{account} (PAT)').format(account=label)

        return label

    def _get_installation_settings_url(
        self,
        account: HostingServiceAccount,
    ) -> str | None:
        """Return the GitHub settings URL for an installation.

        This is the page on GitHub that manages a single app installation. The
        path differs for installs on an organization versus a user account.

        Args:
            account (reviewboard.hostingsvcs.models.HostingServiceAccount):
                The installation account.

        Returns:
            str:
            The installation's settings URL, or ``None`` if the account is
            missing the installation ID needed to build it.
        """
        app_data = get_github_app_data(account)

        if not isinstance(app_data, GitHubAppInstallationData):
            return None

        installation_id = app_data.installation_id
        base = (account.hosting_url or 'https://github.com').rstrip('/')

        if app_data.owner_type == 'organization':
            return (f'{base}/organizations/{urlquote(account.username)}'
                    f'/settings/installations/{installation_id}')

        return f'{base}/settings/installations/{installation_id}'


class GitHub(BaseHostingService[GitHubClient], BaseBugTracker):
    """Hosting service for GitHub."""

    hosting_service_id = 'github'
    name = _('GitHub')

    auth_form = GitHubAuthForm
    client_class = GitHubClient
    connect_ui_cls = GitHubConnectUI
    has_repository_hook_instructions = True
    needs_authorization = True
    supported_scmtools: ClassVar[Sequence[str]] = ['Git']
    supports_bug_trackers = True
    supports_list_remote_repositories = True
    supports_post_commit = True
    supports_repositories = True

    plans: ClassVar[Sequence[tuple[str, HostingServicePlan]] | None] = [
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

    hosting_service_url_patterns: ClassVar[Sequence[_AnyURL] | None] = [
        path('app/create/',
             views.GitHubAppCreateView.as_view(),
             name='github-app-create'),
        path('app/callback/',
             views.GitHubAppCallbackView.as_view(),
             name='github-app-callback'),
        path('github-app/<int:account_id>/install/',
             views.GitHubAppInstallView.as_view(),
             name='github-app-install'),
        path('github-app/<int:account_id>/replace-key/',
             views.GitHubAppReplaceKeyView.as_view(),
             name='github-app-replace-key'),
        path('github-app/install-callback/',
             views.GitHubAppInstallCallbackView.as_view(),
             name='github-app-install-callback'),
        path('github-app/<int:account_id>/reconnect/',
             views.GitHubAppReconnectView.as_view(),
             name='github-app-reconnect'),
        path('github-app/webhook/',
             views.GitHubAppWebhookView.as_view(),
             name='github-app-webhook'),
    ]
    repository_url_patterns: ClassVar[Sequence[_AnyURL] | None] = [
        path('hooks/close-submitted/',
             views.GitHubHookViews.post_receive_hook_close_submitted,
             name='github-hooks-close-submitted'),
    ]

    # This should be the prefix for every field on the plan forms.
    plan_field_prefix: ClassVar[str] = 'github'

    #: A list of the scopes that Review Board requires.
    REQUIRED_SCOPES: ClassVar[Sequence[str]] = _REQUIRED_SCOPES

    _ORG_ACCESS_SUPPORT_URL: ClassVar[str] = (
        'https://beanbag.freshdesk.com/solution/articles/3000045767'
        '-granting-organization-access-on-github'
    )

    #: Matches the host at the front of a non-URL repository path.
    #:
    #: This covers the ``user@host:`` and bare ``host/`` forms, which are not
    #: URLs and so cannot be parsed by :py:func:`~urllib.parse.urlparse`.
    _HOST_PREFIX_RE = re.compile(r'^(?:[^@/:]+@)?[^/:]+[:/]')

    def get_api_url(
        self,
        hosting_url: str | None,
    ) -> str:
        """Return the API URL for GitHub.

        This can be overridden to provide more advanced lookup.

        Args:
            hosting_url (str):
                The provided URL for the server.

        Returns:
            str:
            The API URL to use.
        """
        assert not hosting_url

        api_url = get_github_urls(None)['api_url']

        return f'{api_url}/'

    def get_plan_field(
        self,
        plan: str,
        plan_data: Mapping[str, Any],
        name: str,
    ) -> Any:
        """Return the value of a field for plan-specific data.

        This takes into account the plan type and hosting service ID.

        Args:
            plan (str):
                The ID of the plan.

            plan_data (dict):
                The data from the plan-specific section of the form.

            name (str):
                The field name to return.

        Returns:
            object:
            The value of the field.
        """
        plan = plan.replace('-', '_')
        key = f'{self.plan_field_prefix}_{plan}_{name}'

        return plan_data[key]

    @deprecate_non_keyword_only_args(RemovedInReviewBoard10_0Warning)
    def check_repository(
        self,
        *,
        plan: (GitHubPlanName | None) = None,
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
        assert plan is not None

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

    def is_authorized(self) -> bool:
        """Return whether or not the account is currently authorized.

        This will check for both a configured Personal Access Token
        (introduced in Review Board 3.0.18) and a legacy
        authorizations-generated OAuth Token.

        Returns:
            bool:
            Whether or not the associated account is authorized.
        """
        account = self.account

        if get_github_app_role(account) in {'app', 'installation'}:
            # This is a GitHub App account. Authorization is provided by the
            # app's credentials, not a stored token. Whether the installation
            # is still live on GitHub's side is tracked separately and surfaces
            # when minting an installation token.
            return True

        account_data = account.data

        if account_data.get('personal_token'):
            # This is a newer linked account using a GitHub user's custom
            # Personal Access Token. Support for this was introduced in
            # Review Board 3.0.18.
            return True

        # Check for a legacy authorizations-generated API token.
        return ('authorization' in account_data and
                'token' in account_data['authorization'])

    def get_accessible_repositories(
        self,
    ) -> set[tuple[str, str]]:
        """Return the repositories which are accessible from the account.

        Version Added:
            9.0

        Returns:
            set of tuple:
            A set of 2-tuples for each accessible repository, in the form of:

            Tuple:
                0 (str):
                    The repository owner.

                1 (str):
                    The repository name.

        Raises:
            reviewboard.hostingsvcs.errors.HostingServiceError:
                An error occurred while fetching the data.
        """
        repos = self.client.get_installation_accessible_repositories(
            api_url=self.get_api_url(self.account.hosting_url))

        return {
            (repo.owner.login.lower(), repo.name.lower())
            for repo in repos.iter_items()
        }

    def get_file(
        self,
        repository: Repository,
        path: str,
        revision: str,
        *args,
        **kwargs,
    ) -> bytes:
        """Return the requested file.

        Args:
            repository (reviewboard.scmtools.models.Repository):
                The repository to retrieve the file from.

            path (str):
                The file path.

            revision (str):
                The revision the file should be retrieved from.

            *args (tuple):
                Unused positional arguments.

            **kwargs (dict):
                Unused keyword arguments.

        Returns:
            bytes:
            The contents of the file.
        """
        repo_api_url = self._get_repo_api_url(repository)
        return self.client.get_blob(
            repo_api_url=repo_api_url,
            path=path,
            sha=revision)

    def get_file_exists(
        self,
        repository: Repository,
        path: str,
        revision: str,
        *args,
        **kwargs,
    ) -> bool:
        """Return whether or not the given path exists in the repository.

        Args:
            repository (reviewboard.scmtools.models.Repository):
                The repository to check for file existence.

            path (str):
                The file path.

            revision (str):
                The revision to check for file existence.

            *args (tuple):
                Unused positional arguments.

            **kwargs (dict):
                Unused keyword arguments.

        Returns:
            bool:
            Whether or not the file exists at the given revision in the
            repository.
        """
        try:
            repo_api_url = self._get_repo_api_url(repository)
            self.client.get_blob(
                repo_api_url=repo_api_url,
                path=path,
                sha=revision)

            return True
        except FileNotFoundError:
            return False

    def get_branches(
        self,
        repository: Repository,
    ) -> Sequence[Branch]:
        """Return a list of all branches in the repository.

        Args:
            repository (reviewboard.scmtools.models.Repository):
                The repository for which branches should be returned.

        Returns:
            list of reviewboard.scmtools.core.Branch:
            The branches.

        Raises:
            reviewboard.hostingsvcs.errors.HostingServiceError:
                There was an error fetching branches.
        """
        repo_api_url = self._get_repo_api_url(repository)
        branches_rsp = self.client.get_branches(
            repo_api_url=repo_api_url,
            repository=repository)
        repository_rsp = self.client.get_repository(
            repo_api_url=repo_api_url,
            repository=repository)

        # There *should* always be a default_branch in the response, but if
        # not, default to the more-modern "main"
        default_branch = repository_rsp.default_branch or 'main'

        branches = [
            Branch(
                id=branch_data.name,
                commit=branch_data.commit.sha,
                default=(branch_data.name == default_branch),
            )
            for branch_data in branches_rsp.iter_items()
        ]

        # If we didn't find the default branch at all, something was super
        # weird. Fall back to the first one in the list.
        if not any(branch.default for branch in branches):
            branches[0].default = True

        return branches

    def get_commits(
        self,
        repository: Repository,
        branch: (str | None) = None,
        start: (str | None) = None,
    ) -> Sequence[Commit]:
        """Return a list of commits backward in history from a given point.

        This can be called multiple times in succession using the "parent"
        field of the last entry as the start parameter in order to paginate
        through the history of commits in the repository.

        Args:
            repository (reviewboard.scmtools.models.Repository):
                The repository to retrieve commits from.

            branch (str, optional):
                The branch to retrieve from.

                If this is not provided, the default branch will be used.

            start (str, optional):
                An optional starting revision.

                If this is not provided, the most recent commits will be
                returned.

        Returns:
            list of reviewboard.scmtools.core.Commit:
            The retrieved commits.

        Raises:
            reviewboard.hostingsvcs.errors.HostingServiceError:
                There was an error fetching commits.
        """
        # Note that we don't always use the branch, since the GitHub API
        # doesn't support limiting by branch *and* starting at a SHA. So,
        # the branch argument can be safely ignored if a sha is provided.
        rsp_pages = self.client.get_commits(
            repo_api_url=self._get_repo_api_url(repository),
            start=start or branch,
            repository=repository)

        # We only care about the first page of results for this API.
        page = rsp_pages.page_data

        if not page:
            return []

        commits = []

        for item in page:
            if item.parents:
                parent = item.parents[0].sha
            else:
                parent = ''

            commits.append(Commit(
                author_name=item.commit.author.name,
                id=item.sha,
                date=item.commit.committer.date,
                message=item.commit.message,
                parent=parent,
            ))

        return commits

    def get_change(
        self,
        repository: Repository,
        revision: str,
    ) -> Commit:
        """Return an individual change.

        Args:
            repository (reviewboard.scmtools.models.Repository):
                The repository to get the change from.

            revision (str):
                The revision to retrieve.

        Returns:
            reviewboard.scmtools.core.Commit:
            The change.

        Raises:
            reviewboard.hostingsvcs.errors.HostingServiceError:
                There was an error fetching the commit.
        """
        repo_api_url = self._get_repo_api_url(repository)

        # Step 1: fetch the commit itself that we want to review, to get the
        # parent SHA and the commit message.
        commit_rsp = self.client.get_commit(
            repo_api_url=repo_api_url,
            commit_id=revision,
            repository=repository)

        commit = commit_rsp.commit
        parent_revision = commit_rsp.parents[0].sha

        # Step 2: Get the diff and tree from the "compare commits" API.
        # If the commit has a parent commit, use GitHub's "compare two commits"
        # API to get the diff. Otherwise, just use the commit we already have.
        if parent_revision:
            comparison = self.client.get_compare_commits(
                repo_api_url=repo_api_url,
                parent_id=parent_revision,
                commit_id=revision,
                repository=repository)
            tree_sha = comparison.base_commit.commit.tree.sha
            files = comparison.files
        else:
            tree_sha = commit.tree.sha
            files = commit_rsp.files

        # Step 3: Fetch the tree for the original commit, so that we can get
        # full blob SHAs for each of the files in the diff.
        tree_rsp = self.client.get_tree(
            repo_api_url=repo_api_url,
            tree_sha=tree_sha,
            recursive=True,
            repository=repository)

        file_shas = {
            entry.path.encode('utf-8'): entry.sha.encode('utf-8')
            for entry in tree_rsp.tree
        }

        diff = []

        assert files is not None

        for f in files:
            filename = f.filename.encode('utf-8')
            status = f.status

            if not f.patch:
                continue

            diff.append(b'diff --git a/%s b/%s' % (filename, filename))

            if status == 'modified':
                old_sha = file_shas[filename]
                new_sha = f.sha.encode('utf-8')
                diff.append(b'index %s..%s 100644' % (old_sha, new_sha))
                diff.append(b'--- a/%s' % filename)
                diff.append(b'+++ b/%s' % filename)
            elif status == 'added':
                new_sha = f.sha.encode('utf-8')

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
                assert f.previous_filename is not None
                old_filename = f.previous_filename.encode('utf-8')
                old_sha = file_shas[old_filename]
                new_sha = f.sha.encode('utf-8')

                diff.append(b'rename from %s' % old_filename)
                diff.append(b'rename to %s' % filename)
                diff.append(b'index %s..%s' % (old_sha, new_sha))
                diff.append(b'--- a/%s' % old_filename)
                diff.append(b'+++ b/%s' % filename)

            diff.append(f.patch.encode('utf-8'))

        if diff and not diff[-1].endswith(b'\n'):
            # Make sure there's a trailing newline.
            diff.append(b'')

        diff = b'\n'.join(diff)

        return Commit(author_name=commit.author.name,
                      id=revision,
                      date=commit.committer.date,
                      message=commit.message,
                      parent=parent_revision,
                      diff=diff)

    def get_remote_repositories(
        self,
        owner: (str | None) = None,
        owner_type: (str | None) = None,
        filter_type: (str | None) = None,
        start: (int | None) = None,
        per_page: (int | None) = None,
        **kwargs,
    ) -> BasePaginator[RemoteRepository, Any]:
        """Return a list of remote repositories matching the given criteria.

        This will look up each remote repository on GitHub that the given
        owner either owns or is a member of.

        Args:
            owner (str, optional):
                If the plan is an organization plan, then this is expected
                to be an organization name, and the resulting repositories
                will be ones either owned by that organization or that the
                organization is a member of, and can be accessed by the
                authenticated user.

                If the plan is a public or private plan, and `owner` is the
                current user, then that user's public and private repositories
                or ones they're a member of will be returned.

                Otherwise, this is assumed to be another GitHub user, and
                their accessible repositories that they own or are a member
                of will be returned.

                If not provided, this defaults to the linked account's
                username.

            owner_type (str, optional):
                A hosting service-specific indicator of what the owner is (such
                as a user or a group).

            filter_type (str, optional):
                Some hosting service-specific criteria to filter by.

            start (int, optional):
                The index to start at.

            per_page (int, optional):
                The number of results per page.

            **kwargs (dict):
                Additional keyword arguments.

        Returns:
            reviewboard.hostingsvcs.utils.BasePaginator:
            A paginator for the returned repositories.

        Raises:
            ValueError:
                The owner type was not valid.

            reviewboard.hostingsvcs.errors.HostingServiceError:
                There was an error fetching branches.
        """
        if owner_type is None:
            owner_type = 'user'

        if owner is None and owner_type == 'user':
            owner = self.account.username

        assert owner

        url = self.get_api_url(self.account.hosting_url)

        if owner_type == 'organization':
            url += f'orgs/{owner}/repos'
        elif owner_type == 'user':
            if owner == self.account.username:
                # All repositories belonging to an authenticated user.
                url += 'user/repos'
            else:
                # Only public repositories for the user.
                url += f'users/{owner}/repos'
        else:
            raise ValueError(
                f'owner_type must be "organization" or "user", not '
                f'{owner_type!r}'
            )

        return ProxyPaginator[RemoteRepository, Sequence[RemoteRepository]](
            self.client.get_repositories(
                repos_api_url=url,
                filter_type=filter_type,
                start=start,
                per_page=per_page),
            normalize_page_data_func=lambda page_data: [
                RemoteRepository(
                    self,
                    repository_id=f'{repo.owner.login}/{repo.name}',
                    name=repo.name,
                    owner=repo.owner.login,
                    scm_type='Git',
                    path=repo.clone_url,
                    mirror_path=repo.mirror_url,
                    extra_data=repo.__pydantic_extra__,
                )
                for repo in page_data
            ])

    def get_remote_repository(
        self,
        repository_id: str,
    ) -> RemoteRepository:
        """Get the remote repository for the ID.

        Args:
            repository_id (str):
                The repository's identifier.

                This is expected to be an ID returned from
                :py:meth:`get_remote_repositories`, in the form of
                "owner/repo_id".

        Returns:
            reviewboard.hostingsvcs.repository.RemoteRepository:
            The remote repository.

        Raises:
            django.core.excptions.ObjectDoesNotExist:
                If the remote repository does not exist.

            reviewboard.hostingsvcs.errors.HostingServiceError:
                There was an error fetching the repository.
        """
        api_url = self.get_api_url(self.account.hosting_url)

        try:
            repository_rsp = self.client.get_repository(
                repo_api_url=f'{api_url}repos/{repository_id}',
                repository=None)
        except HostingServiceError as e:
            if e.http_code == 404:
                raise ObjectDoesNotExist

            raise

        return RemoteRepository(
            hosting_service=self,
            repository_id=repository_id,
            name=repository_rsp.name,
            owner=repository_rsp.owner.login,
            scm_type='Git',
            path=repository_rsp.clone_url,
            mirror_path=repository_rsp.mirror_url,
            extra_data=repository_rsp.__pydantic_extra__,
        )

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

        Raises:
            reviewboard.hostingsvcs.errors.HostingServiceError:
                There was an error fetching the bug.
        """
        issue = self.client.get_issue(
            repo_api_url=self._get_repo_api_url(repository),
            bug_id=bug_id,
            repository=repository)

        return {
            'description': issue.body,
            'status': issue.state,
            'summary': issue.title,
        }

    def get_repository_hook_instructions(
        self,
        request: HttpRequest,
        repository: Repository,
    ) -> SafeString:
        """Returns instructions for setting up incoming webhooks."""
        plan = repository.extra_data['repository_plan']

        owner = self._get_repository_owner_raw(plan, repository.extra_data)
        name = self._get_repository_name_raw(plan, repository.extra_data)
        add_webhook_url = urljoin(
            self.account.hosting_url or 'https://github.com/',
            f'{owner}/{name}/settings/hooks/new')

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

    def _get_repo_api_url(
        self,
        repository: Repository,
    ) -> str:
        """Return the API URL for a repository.

        Args:
            repository (reviewboard.scmtools.models.Repository):
                The repository object.

        Returns:
            str:
            The URL to the API endpoint for the repository.
        """
        plan = repository.extra_data['repository_plan']

        return self._get_repo_api_url_raw(
            self._get_repository_owner_raw(plan, repository.extra_data),
            self._get_repository_name_raw(plan, repository.extra_data))

    def _get_repo_api_url_raw(
        self,
        owner: str,
        repo_name: str,
    ) -> str:
        """Return the API URL for a repository given owner and repo name.

        Args:
            owner (str):
                The name of the repository's owner.

            repo_name (str):
                The repository's name.

        Returns:
            str:
            The URL to the API endpoint for the repository.
        """
        api_url = self.get_api_url(self.account.hosting_url)

        return f'{api_url}repos/{owner}/{repo_name}'

    def _get_repository_owner_raw(
        self,
        plan: GitHubPlanName,
        extra_data: dict[str, Any],
    ) -> str:
        """Return the repository owner from the repository extra data.

        Args:
            plan (str):
                The selected plan.

            extra_data (dict):
                The repository extra data.

        Returns:
            str:
            The repository owner given the selected plan and provided data.

        Raises:
            reviewboard.hostingsvcs.errors.InvalidPlanError:
                The provided plan was not valid.
        """
        if plan in {'public', 'private'}:
            return self.account.username
        elif plan in {'public-org', 'private-org'}:
            return self.get_plan_field(plan, extra_data, 'name')
        else:
            raise InvalidPlanError(plan)

    def _get_repository_name_raw(
        self,
        plan: str,
        extra_data: dict[str, Any],
    ) -> str:
        """Return the repository name from the repository extra data.

        Args:
            plan (str):
                The selected plan.

            extra_data (dict):
                The repository extra data.

        Returns:
            str:
            The repository owner given the selected plan and provided data.

        Raises:
            reviewboard.hostingsvcs.errors.InvalidPlanError:
                The provided plan was not valid.
        """
        return self.get_plan_field(plan, extra_data, 'repo_name')

    @classmethod
    def get_protected_objects_for_account_deletion(
        cls,
        accounts: Sequence[HostingServiceAccount],
    ) -> Sequence[HostingServiceAccount]:
        """Return installations that deleting these accounts would orphan.

        Installation accounts reference their hidden app-record account by
        primary key stored in JSON data rather than a database foreign key, so
        nothing at the database level stops the record from being deleted out
        from under them. An installation left without its app record can no
        longer authenticate.

        Installations being deleted alongside their app record are not
        reported, so deleting a record together with everything depending on
        it is allowed.

        Version Added:
            9.0

        Args:
            accounts (list of
                      reviewboard.hostingsvcs.models.HostingServiceAccount):
                The GitHub accounts being deleted.

        Returns:
            list of reviewboard.hostingsvcs.models.HostingServiceAccount:
            The installation accounts blocking the deletion.
        """
        app_account_pks = {
            account.pk
            for account in accounts
            if is_app_record_account(account)
        }

        if not app_account_pks:
            return []

        deleting_pks = {
            account.pk
            for account in accounts
        }
        blocked: list[HostingServiceAccount] = []

        for account in HostingServiceAccount.objects.filter(
                service_name='github'):
            app_data = get_github_app_data(account)

            if (account.pk not in deleting_pks and
                is_installation_data(app_data) and
                app_data.app_account_id in app_account_pks):
                blocked.append(account)

        return blocked
