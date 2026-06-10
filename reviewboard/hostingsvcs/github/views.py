"""Views for GitHub.

Version Added:
    9.0:
    Split up :py:mod:`reviewboard.hostingsvcs.github`.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import secrets
from collections import defaultdict
from typing import TYPE_CHECKING, Literal, cast
from urllib.parse import quote as urlquote, urlencode, urlparse

from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.http import (
    Http404,
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseRedirect,
)
from django.shortcuts import get_object_or_404, render
from django.templatetags.static import static
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _, ngettext
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.views.generic.base import View

from reviewboard.admin.server import build_server_url, get_server_url
from reviewboard.hostingsvcs.base.http import HostingServiceHTTPRequest
from reviewboard.hostingsvcs.errors import (
    InvalidPlanError,
    MissingHostingServiceError,
)
from reviewboard.hostingsvcs.github import api
from reviewboard.hostingsvcs.github.accounts import (
    GitHubAppInstallationData,
    GitHubAppRecordData,
    get_github_app_data,
    is_app_record_data,
    is_installation_account,
    is_installation_data,
    set_github_app_data,
)
from reviewboard.hostingsvcs.hook_utils import (
    close_all_review_requests,
    get_git_branch_name,
    get_repository_for_hook,
    get_review_request_id,
)
from reviewboard.hostingsvcs.models import HostingServiceAccount
from reviewboard.scmtools.crypto_utils import encrypt_password
from reviewboard.scmtools.models import Repository
from reviewboard.site.urlresolvers import local_site_reverse

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from typing import Final

    from django.http import HttpRequest
    from typelets.json import JSONDict


logger = logging.getLogger(__name__)


#: The session key used to store state across the app-creation redirect.
#:
#: Version Added:
#:     9.0
_CREATE_SESSION_KEY: Final[str] = 'github_app_create'

#: The session key used to store state across the installation redirect.
#:
#: Version Added:
#:     9.0
_INSTALL_SESSION_KEY: Final[str] = 'github_app_install'

#: The timeout, in seconds, for the manifest conversion request to GitHub.
#:
#: Version Added:
#:     9.0
_MANIFEST_CONVERT_TIMEOUT: Final[int] = 30


class GitHubHookViews:
    """Container class for hook views."""

    @staticmethod
    @require_POST
    def post_receive_hook_close_submitted(
        request: HttpRequest,
        local_site_name: (str | None) = None,
        repository_id: (int | None) = None,
        hosting_service_id: (str | None) = None,
    ) -> HttpResponse:
        """Close review requests as submitted automatically after a push.

        Args:
            request (django.http.HttpRequest):
                The request from the Bitbucket webhook.

            local_site_name (str, optional):
                The local site name, if available.

            repository_id (int, optional):
                The pk of the repository, if available.

            hosting_service_id (str, optional):
                The name of the hosting service.

        Returns:
            django.http.HttpResponse:
            A response for the request.
        """
        hook_event = request.META.get('HTTP_X_GITHUB_EVENT')

        if hook_event == 'ping':
            # GitHub is checking that this hook is valid, so accept the request
            # and return.
            return HttpResponse()
        elif hook_event != 'push':
            return HttpResponseBadRequest(
                'Only "ping" and "push" events are supported.')

        assert repository_id is not None
        assert hosting_service_id is not None

        repository = get_repository_for_hook(
            repository_id=repository_id,
            hosting_service_id=hosting_service_id,
            local_site_name=local_site_name)

        # Validate the hook against the stored UUID.
        m = hmac.new(repository.get_or_create_hooks_uuid().encode('utf-8'),
                     request.body, hashlib.sha1)

        sig_parts = request.META.get('HTTP_X_HUB_SIGNATURE', '').split('=')

        if sig_parts[0] != 'sha1' or len(sig_parts) != 2:
            # We don't know what this is.
            return HttpResponseBadRequest('Unsupported HTTP_X_HUB_SIGNATURE')

        if m.hexdigest() != sig_parts[1]:
            return HttpResponseBadRequest('Bad signature.')

        try:
            payload = json.loads(request.body.decode('utf-8'))
        except ValueError as e:
            logger.error('The payload is not in JSON format: %s', e)
            return HttpResponseBadRequest('Invalid payload format')

        server_url = get_server_url(request=request)
        review_request_id_to_commits = \
            GitHubHookViews._get_review_request_id_to_commits_map(
                payload, server_url, repository)

        if review_request_id_to_commits:
            close_all_review_requests(
                review_request_id_to_commits=review_request_id_to_commits,
                local_site_name=local_site_name,
                repository=repository,
                hosting_service_id=hosting_service_id)

        return HttpResponse()

    @staticmethod
    def _get_review_request_id_to_commits_map(
        payload: JSONDict,
        server_url: str,
        repository: Repository,
    ) -> Mapping[int | None, Sequence[str]] | None:
        """Return a mapping of review request ID to a list of commits.

        If a commit's commit message does not contain a review request ID,
        we append the commit to the key None.

        Args:
            payload (dict):
                The decoded webhook payload.

            server_url (str):
                The URL of the Review Board server.

            repository (reviewboard.scmtools.models.Repository):
                The repository object.

        Returns:
            dict:
            A mapping from review request ID to a list of matching commits from
            the payload.
        """
        review_request_id_to_commits_map = defaultdict(list)

        ref_name = payload.get('ref')

        if not ref_name:
            return None

        assert isinstance(ref_name, str)

        branch_name = get_git_branch_name(ref_name)
        if not branch_name:
            return None

        commits = payload.get('commits', [])
        assert isinstance(commits, list)

        for commit in commits:
            assert isinstance(commit, dict)

            commit_hash = commit.get('id')
            assert isinstance(commit_hash, str)

            commit_message = commit.get('message')
            assert isinstance(commit_message, str)

            review_request_id = get_review_request_id(
                commit_message=commit_message,
                server_url=server_url,
                commit_id=commit_hash,
                repository=repository)

            review_request_id_to_commits_map[review_request_id].append(
                f'{branch_name} ({commit_hash[:7]})')

        return review_request_id_to_commits_map


@method_decorator(staff_member_required, name='dispatch')
class GitHubAppView(View):
    """Base class for views for creating and working with a GitHub App.

    Version Added:
        9.0
    """

    @staticmethod
    def _get_github_urls(
        hosting_url: str | None,
    ) -> Mapping[str, str]:
        """Return the base URLs to use for a GitHub connection.

        Args:
            hosting_url (str):
                The GitHub server URL, or ``None`` for github.com.

        Returns:
            dict:
            A dictionary with ``app_base`` and ``api_url`` keys.
        """
        if hosting_url:
            app_base = hosting_url.rstrip('/')

            return {
                'api_url': f'{app_base}/api/v3',
                'app_base': app_base,
            }

        return {
            'api_url': 'https://api.github.com',
            'app_base': 'https://github.com',
        }

    def _show_error(
        self,
        request: HttpRequest,
        message: str,
    ) -> HttpResponse:
        """Report an error and return to the connected services list.

        The GitHub App flow is a sequence of redirects through GitHub. When a
        step fails there is nothing meaningful to render on the callback URL
        itself, so the error is shown on the connected services list, where the
        administrator can try connecting again. This is friendlier than a 404,
        which wrongly suggests the page does not exist.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            message (str):
                The error message to show.

        Returns:
            django.http.HttpResponse:
            A redirect to the connected services list.
        """
        messages.error(request, message)

        return HttpResponseRedirect(
            local_site_reverse('connected-services-list', request=request))

    @staticmethod
    def _get_account_or_none(
        **filters,
    ) -> HostingServiceAccount | None:
        """Return a hosting service account, or ``None`` if not found.

        Args:
            **filters (dict):
                Lookup arguments for the account query.

        Returns:
            reviewboard.hostingsvcs.models.HostingServiceAccount:
            The matching account, or ``None`` if no account matched or the
            lookup value was invalid.
        """
        # The filters can come from user-supplied URLs, so we catch a couple
        # extra exception types to guard against problems.
        try:
            return HostingServiceAccount.objects.get(**filters)
        except (HostingServiceAccount.DoesNotExist, TypeError, ValueError):
            return None


class GitHubAppCreateView(GitHubAppView):
    """Begin the GitHub App manifest flow.

    This generates a manifest describing the GitHub App to create and sends the
    administrator to GitHub to create it.

    Version Added:
        9.0
    """

    def get(
        self,
        request: HttpRequest,
        *args,
        **kwargs,
    ) -> HttpResponse:
        """Handle HTTP GET requests.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            *args (tuple, unused):
                Unused positional arguments.

            **kwargs (dict, unused):
                Unused keyword arguments.

        Returns:
            django.http.HttpResponse:
            A confirmation page that, once approved, sends the administrator to
            GitHub to create the app.
        """
        local_site = request.local_site
        hosting_url = request.GET.get('hosting_url') or None

        # Generate a single-use state token to guard the redirect.
        state = secrets.token_urlsafe(32)

        if local_site:
            local_site_id = local_site.pk
        else:
            local_site_id = None

        request.session[_CREATE_SESSION_KEY] = {
            'hosting_url': hosting_url,
            'local_site_id': local_site_id,
            'state': state,
        }

        urls = self._get_github_urls(hosting_url)
        server_hostname = urlparse(build_server_url()).hostname
        assert server_hostname is not None

        default_events = ['push']
        default_permissions = {
            'contents': 'read',
            'metadata': 'read',
            'pull_requests': 'read',
        }

        manifest = {
            'default_events': default_events,
            'default_permissions': default_permissions,
            'hook_attributes': {
                'url': build_server_url(
                    local_site_reverse(
                        'github-app-webhook',
                        local_site=local_site,
                        kwargs={
                            'hosting_service_id': 'github',
                        },
                    )),
            },
            'name': _('Review Board ({server})').format(
                server=server_hostname),

            # Make the app public so it can be installed on any account the
            # administrator has access to (their user plus any organizations),
            # not just the account that owns the app. "Public" here only
            # controls installability. It does not list the app in the GitHub
            # Marketplace.
            'public': True,
            'redirect_url': build_server_url(
                local_site_reverse(
                    'github-app-callback',
                    local_site=local_site,
                    kwargs={
                        'hosting_service_id': 'github',
                    },
                )),
            'setup_url': build_server_url(
                local_site_reverse(
                    'github-app-install-callback',
                    local_site=local_site,
                    kwargs={
                        'hosting_service_id': 'github',
                    },
                )),
            'url': build_server_url(),
        }

        # Build human-readable descriptions of the access being requested, so
        # the administrator can review it before anything is created. These are
        # derived from the manifest above to keep the two in sync.
        permission_labels = {
            'contents': _('Repository contents'),
            'metadata': _('Repository metadata'),
            'pull_requests': _('Pull requests'),
        }
        access_labels = {
            'read': _('Read-only'),
            'write': _('Read and write'),
        }
        event_labels = {
            'pull_request': _('Pull request'),
            'push': _('Push'),
        }

        permissions = [
            {
                'access': access_labels.get(value, value),
                'name': permission_labels.get(key, key),
            }
            for key, value in default_permissions.items()
        ]
        events = [
            event_labels.get(event, event)
            for event in default_events
        ]

        return render(
            request=request,
            template_name='hostingsvcs/github/app_create_confirm.html',
            context={
                'app_name': manifest['name'],
                'events': events,
                'github_label': hosting_url or 'github.com',
                'github_new_app_url': f'{urls["app_base"]}/settings/apps/new',
                'manifest_json': json.dumps(manifest),
                'permissions': permissions,
                'server_url': manifest['url'],
                'state': state,
            })


@method_decorator(staff_member_required, name='dispatch')
class GitHubAppCallbackView(GitHubAppView):
    """Handle the redirect back from creating a GitHub App.

    This exchanges the temporary code for the app's credentials, stores them on
    a new account, and sends the administrator on to install the app.

    Version Added:
        9.0
    """

    def get(
        self,
        request: HttpRequest,
        *args,
        **kwargs,
    ) -> HttpResponse:
        """Handle HTTP GET requests.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            *args (tuple, unused):
                Unused positional arguments.

            **kwargs (dict, unused):
                Unused keyword arguments.

        Returns:
            django.http.HttpResponse:
            A redirect to the GitHub App installation page.
        """
        session_data = request.session.pop(_CREATE_SESSION_KEY, None)
        state = request.GET.get('state')
        code = request.GET.get('code')

        if (not session_data or
            not state or
            not secrets.compare_digest(state, session_data.get('state', ''))):
            return self._show_error(
                request,
                _(
                    'The GitHub connection state was invalid or has expired. '
                    'Please try connecting again.'
                ))

        if not code:
            return self._show_error(
                request,
                _(
                    'GitHub did not provide a setup code. Please try '
                    'connecting again.'
                ))

        hosting_url = session_data.get('hosting_url')
        local_site_id = session_data.get('local_site_id')
        urls = self._get_github_urls(hosting_url)

        try:
            rsp = self._convert_manifest(urls['api_url'], code)
        except Exception as e:
            logger.exception('Error converting GitHub App manifest: %s', e)

            return self._show_error(
                request,
                _(
                    'Could not retrieve the GitHub App details from GitHub. '
                    'Please try connecting again.'
                ))

        owner = rsp.owner or api.AppManifestOwner()
        username = owner.login or rsp.slug

        owner_type = owner.type.lower()

        if owner_type not in {'user', 'organization'}:
            owner_type = ''

        # The PEM private key is multi-line. decrypt_password() rejects
        # non-printable content, so Base64-encode the key first to keep it
        # on a single printable line. Decode with
        # base64.b64decode(decrypt_password(...)) when reading it back.
        private_key = encrypt_password(
            base64.b64encode(
                rsp.pem.encode('utf-8')).decode('ascii'))
        webhook_secret = encrypt_password(rsp.webhook_secret)

        # This is the hidden app-record account. It holds the app credentials
        # (stored once) and is not used for repositories. The installation
        # accounts created later reference it for those credentials. It is
        # hidden from repository configuration via visible=False.
        account = HostingServiceAccount.objects.create(
            service_name='github',
            username=username,
            hosting_url=hosting_url or '',
            local_site_id=local_site_id,
            visible=False,
            data={
                'github_app': GitHubAppRecordData(
                    role='app',
                    app_id=rsp.id,
                    app_slug=rsp.slug,
                    owner_login=owner.login,
                    owner_type=cast(Literal['user', 'organization', ''],
                                    owner.type.lower()),
                    client_id=rsp.client_id,
                    client_secret=encrypt_password(rsp.client_secret),
                    private_key=private_key,
                    webhook_secret=webhook_secret,
                    html_url=rsp.html_url,
                ).model_dump(),
            })

        # Store state for the installation redirect.
        install_state = secrets.token_urlsafe(32)

        request.session[_INSTALL_SESSION_KEY] = {
            'account_id': account.pk,
            'state': install_state,
        }

        return HttpResponseRedirect(
            f'{urls["app_base"]}/apps/{urlquote(rsp.slug)}/installations/'
            f'new?state={install_state}'
        )

    @staticmethod
    def _convert_manifest(
        api_url: str,
        code: str,
    ) -> api.AppManifestResponse:
        """Exchange a temporary manifest code for the app's credentials.

        Args:
            api_url (str):
                The base API URL for the GitHub server.

            code (str):
                The temporary code provided by GitHub.

        Returns:
            reviewboard.hostingsvcs.github.api.AppManifestResponse:
            The parsed conversion response from GitHub.

        Raises:
            Exception:
                The request to GitHub failed, the response could not be parsed,
                or the response was missing the required app credentials.
        """
        url = f'{api_url}/app-manifests/{urlquote(code)}/conversions'

        request = HostingServiceHTTPRequest(
            url=url,
            method='POST',
            headers={
                'Accept': 'application/vnd.github+json',
            })

        rsp = request.open(timeout=_MANIFEST_CONVERT_TIMEOUT)

        return api.AppManifestResponse.model_validate_json(rsp.data)


@method_decorator(staff_member_required, name='dispatch')
class GitHubAppInstallView(GitHubAppView):
    """Begin installing an existing GitHub App onto another account.

    This sends the administrator to GitHub to install an already-created app
    onto another user or organization. The app credentials are read from the
    hidden app-record account. The returning installation is handled by
    :py:class:`GitHubAppInstallCallbackView`.

    Version Added:
        9.0
    """

    def get(
        self,
        request: HttpRequest,
        *args,
        account_id: int,
        **kwargs,
    ) -> HttpResponse:
        """Handle HTTP GET requests.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            *args (tuple, unused):
                Unused positional arguments.

            account_id (int):
                The ID of the hidden app-record account holding the app's
                credentials.

            **kwargs (dict, unused):
                Unused keyword arguments.

        Returns:
            django.http.HttpResponse:
            A redirect to the GitHub App installation page.
        """
        app_account = self._get_account_or_none(pk=account_id,
                                                service_name='github')

        if app_account is None:
            return self._show_error(
                request,
                _(
                    'The GitHub App connection was not found. Please try '
                    'connecting again.'
                ))

        app_data = get_github_app_data(app_account)

        if not is_app_record_data(app_data):
            return self._show_error(
                request,
                _(
                    'The GitHub App connection was not found. Please try '
                    'connecting again.'
                ))

        if not (app_slug := app_data.app_slug):
            return self._show_error(
                request,
                _(
                    'The GitHub App is missing its configuration. Please try '
                    'connecting again.'
                ))

        # Set up state for the installation redirect, mirroring the handoff
        # used right after the app is created.
        install_state = secrets.token_urlsafe(32)

        request.session[_INSTALL_SESSION_KEY] = {
            'account_id': app_account.pk,
            'state': install_state,
        }

        urls = self._get_github_urls(app_account.hosting_url or None)

        return HttpResponseRedirect(
            f'{urls["app_base"]}/apps/{urlquote(app_slug)}/installations/'
            f'new?state={install_state}'
        )


@method_decorator(staff_member_required, name='dispatch')
class GitHubAppInstallCallbackView(GitHubAppView):
    """Handle the redirect back from installing a GitHub App.

    This looks up which account (user or organization) the app was installed
    on and records it as an installation account that references the app
    record, completing the connection. An app can be installed on multiple
    accounts, each becoming its own installation account.

    Version Added:
        9.0
    """

    def get(
        self,
        request: HttpRequest,
        *args,
        **kwargs,
    ) -> HttpResponse:
        """Handle HTTP GET requests.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            *args (tuple, unused):
                Unused positional arguments.

            **kwargs (dict):
                Additional keyword arguments from the URL. This includes the
                ``hosting_service_id`` captured by the URL pattern.

        Returns:
            django.http.HttpResponse:
            A redirect to the connected services list, where the wizard opens
            on the install success step. The ``?step=reassign`` request instead
            returns that step's HTML fragment for the wizard to load.
        """
        from reviewboard.hostingsvcs.github.client import GitHubClient

        hosting_service_id = kwargs['hosting_service_id']

        # The wizard loads the install success step from this same URL via
        # ?step=reassign. Return the bare fragment for the requested
        # installation account.
        if request.GET.get('step') == 'reassign':
            installation_account = self._get_account_or_none(
                pk=request.GET.get('account_id'),
                service_name='github')

            if (installation_account is None or
                not is_installation_account(installation_account)):
                raise Http404(
                    _('The specified GitHub App installation was not found.'))

            return self._render_success_fragment(
                request=request,
                installation_account=installation_account,
                hosting_service_id=hosting_service_id)

        # Development-only preview. When DEBUG is on, ?test_account=<pk> opens
        # the wizard on the success step for an existing installation account,
        # bypassing the GitHub round-trip so the step can be iterated on.
        #
        # TODO: This is temporary dev-only scaffolding for building out the
        #       success step. Remove it before this feature ships (9.0 GA).
        if settings.DEBUG:
            test_account_id = request.GET.get('test_account')

            if test_account_id:
                installation_account = get_object_or_404(
                    HostingServiceAccount,
                    pk=test_account_id,
                    service_name='github')

                return self._redirect_to_success_step(
                    request=request,
                    installation_account=installation_account,
                    hosting_service_id=hosting_service_id)

        session_data = request.session.pop(_INSTALL_SESSION_KEY, None)
        state = request.GET.get('state')
        installation_id = request.GET.get('installation_id')

        if (not session_data or
            not state or
            not secrets.compare_digest(state, session_data.get('state', ''))):
            return self._show_error(
                request,
                _(
                    'The GitHub installation state was invalid or has '
                    'expired. Please try connecting again.'
                ))

        if not installation_id:
            return self._show_error(
                request,
                _(
                    'GitHub did not provide an installation ID. Please try '
                    'connecting again.'
                ))

        app_account = self._get_account_or_none(pk=session_data['account_id'])

        if app_account is None:
            return self._show_error(
                request,
                _(
                    'The GitHub App connection could not be found. Please try '
                    'connecting again.'
                ))

        try:
            installation_id = int(installation_id)
        except ValueError:
            return self._show_error(
                request,
                _(
                    'The GitHub installation state was invalid. Please try '
                    'connecting again.'
                ))

        # Authenticate as the app and look up the installation, so we can
        # record which account (user or organization) it was installed on.
        app_client = app_account.service.client
        assert isinstance(app_client, GitHubClient)

        try:
            install_info = app_client.get_installation_info(installation_id)
        except Exception as e:
            logger.exception('Error retrieving GitHub App installation %s: %s',
                             installation_id, e)

            return self._show_error(
                request,
                _(
                    'Could not retrieve the GitHub App installation details '
                    'from GitHub. Please try connecting again.'
                ))

        account = install_info.account
        owner_id = account.id
        owner_login = account.login
        owner_type = account.type.lower()
        owner_avatar_url = account.avatar_url
        repository_selection = install_info.repository_selection

        if owner_type not in {'user', 'organization'}:
            owner_type = ''

        if repository_selection not in {'all', 'selected'}:
            repository_selection = ''

        installation_data = GitHubAppInstallationData(
            role='installation',
            app_account_id=app_account.pk,
            installation_id=installation_id,
            owner_id=owner_id,
            owner_login=owner_login,
            owner_type=cast(Literal['user', 'organization', ''], owner_type),
            owner_avatar_url=owner_avatar_url,
            repository_selection=cast(Literal['all', 'selected', ''],
                                      repository_selection),
        )

        # If we already have an installation account for this app, it means
        # that we're re-installing it (perhaps it got removed from the org),
        # and we can just update it with the new date. Otherwise, create a new
        # one.
        #
        # Match on the owner the app is installed on, not the installation ID.
        # GitHub issues a new installation ID on each uninstall/reinstall, so
        # the ID does not identify the prior account across a reinstall. The
        # owner's stable numeric ID does, and it survives a user or
        # organization rename.
        installation_account = None
        local_site = app_account.local_site

        candidate_apps = HostingServiceAccount.objects.filter(
            service_name='github',
            hosting_url=app_account.hosting_url or '',
            local_site=local_site)

        for candidate in candidate_apps:
            candidate_app = get_github_app_data(candidate)

            if (not is_installation_data(candidate_app) or
                candidate_app.app_account_id != app_account.pk):
                continue

            if candidate_app.owner_id == owner_id:
                installation_account = candidate
                break

        if installation_account is None:
            installation_account = HostingServiceAccount.objects.create(
                service_name='github',
                username=owner_login,
                hosting_url=app_account.hosting_url or '',
                local_site=local_site,
                data={'github_app': installation_data.model_dump()})
        else:
            installation_account.username = owner_login
            set_github_app_data(installation_account, installation_data)
            installation_account.save(update_fields=('username', 'data'))

        return self._redirect_to_success_step(
            request=request,
            installation_account=installation_account,
            hosting_service_id=hosting_service_id)

    def post(
        self,
        request: HttpRequest,
        *args,
        **kwargs,
    ) -> HttpResponse:
        """Handle HTTP POST requests.

        This reassigns the selected repositories from their current Personal
        Access Token accounts to the GitHub App installation account.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            *args (tuple, unused):
                Unused positional arguments.

            **kwargs (dict, unused):
                Unused keyword arguments.

        Returns:
            django.http.HttpResponse:
            A redirect to the connected services list.
        """
        installation_account = self._get_account_or_none(
            pk=request.POST.get('account_id'),
            service_name='github')

        if (installation_account is None or
            not is_installation_account(installation_account)):
            return self._show_error(
                request,
                _(
                    'The specified GitHub App installation was not found. '
                    'Please try connecting again.'
                ))

        # Recompute the eligible repositories and only reassign ones that are
        # genuinely candidates. No session state survives from the GET, so this
        # recomputation is what authorizes the reassignment. If GitHub can't
        # confirm which repositories the app can access, reassign nothing
        # rather than risk moving a repository the app cannot read.
        lookup_failed = False

        try:
            candidates = {
                repository.pk: repository
                for repository in self._get_reassignable_repositories(
                    installation_account)
            }
        except Exception as e:
            logger.exception(
                'Error retrieving accessible repositories for GitHub App '
                'installation account %s: %s',
                installation_account.pk, e)

            candidates = {}
            lookup_failed = True

        requested_ids = request.POST.getlist('repositories')
        selected_repositories = []

        for raw_id in requested_ids:
            try:
                repository = candidates[int(raw_id)]
            except (KeyError, ValueError):
                continue

            selected_repositories.append(repository)

        if selected_repositories:
            Repository.objects.filter(
                pk__in=[
                    repository.pk
                    for repository in selected_repositories
                ]).update(hosting_account=installation_account)

        count = len(selected_repositories)

        if count:
            messages.success(
                request,
                ngettext(
                    'Review Board is now connected to GitHub, and %(count)d '
                    'repository was moved to the new connection.',
                    'Review Board is now connected to GitHub, and %(count)d '
                    'repositories were moved to the new connection.',
                    count) % {'count': count})
        elif lookup_failed and requested_ids:
            # The connection itself succeeded, but the repositories the
            # administrator asked to move were left on their old credentials.
            # Reporting plain success here would hide that.
            messages.warning(
                request,
                _(
                    'Review Board is now connected to GitHub, but the '
                    'repositories you selected could not be moved to the new '
                    'connection. They are still using their old credentials. '
                    'Please try moving them again.'
                ))
        else:
            messages.success(
                request,
                _('Review Board is now connected to GitHub.'))

        return HttpResponseRedirect(
            local_site_reverse('connected-services-list',
                               local_site=installation_account.local_site))

    def _redirect_to_success_step(
        self,
        request: HttpRequest,
        installation_account: HostingServiceAccount,
        hosting_service_id: str,
    ) -> HttpResponse:
        """Redirect to the connected services list, opening the success step.

        The wizard auto-opens on the install success step once the list loads.
        The fragment URL is stashed in the session (rather than passed as a
        query parameter) so that the URL the wizard fetches and injects stays
        server-controlled. It is single-use: the list view pops it.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            installation_account (reviewboard.hostingsvcs.models.
                                  HostingServiceAccount):
                The installation account the app was installed onto.

            hosting_service_id (str):
                The hosting service ID, used to build the success step URL.

        Returns:
            django.http.HttpResponse:
            A redirect to the connected services list.
        """
        local_site = installation_account.local_site

        callback_url = local_site_reverse(
            'github-app-install-callback',
            request=request,
            kwargs={
                'hosting_service_id': hosting_service_id,
            })

        params = urlencode({
            'step': 'reassign',
            'account_id': installation_account.pk,
        })

        request.session['connect_wizard_url'] = f'{callback_url}?{params}'

        return HttpResponseRedirect(
            local_site_reverse('connected-services-list',
                               local_site=local_site))

    def _render_success_fragment(
        self,
        request: HttpRequest,
        installation_account: HostingServiceAccount,
        hosting_service_id: str,
    ) -> HttpResponse:
        """Render the installation success step as a wizard fragment.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            installation_account (reviewboard.hostingsvcs.models.
                                  HostingServiceAccount):
                The installation account the app was installed onto.

            hosting_service_id (str):
                The hosting service ID, used to build the reassignment form
                action.

        Returns:
            django.http.HttpResponse:
            The rendered success step fragment.
        """
        from reviewboard.hostingsvcs.github.service import GitHub

        app_data = get_github_app_data(installation_account)

        if is_installation_data(app_data):
            owner_login = app_data.owner_login
        else:
            owner_login = ''

        # If GitHub can't tell us which repositories the app can access, show
        # the plain confirmation with a note rather than suggesting any repos.
        # Suggesting an unverified repo could lead to reassigning one the app
        # cannot read.
        try:
            repositories = self._get_reassignable_repositories(
                installation_account)
            verification_failed = False
        except Exception as e:
            logger.exception(
                'Error retrieving accessible repositories for GitHub App '
                'installation account %s: %s',
                installation_account.pk, e)

            repositories = []
            verification_failed = True

        logo_image = GitHub.logo_image
        assert logo_image is not None

        return render(
            request=request,
            template_name='hostingsvcs/github/app_install_success.html',
            context={
                'form_action': local_site_reverse(
                    'github-app-install-callback',
                    request=request,
                    kwargs={
                        'hosting_service_id': hosting_service_id,
                    }),
                'installation_account': installation_account,
                'owner_login': owner_login or '',
                'repositories': repositories,
                'service_logo': static(logo_image),
                'verification_failed': verification_failed,
            })

    @staticmethod
    def _get_reassignable_repositories(
        installation_account: HostingServiceAccount,
    ) -> Sequence[Repository]:
        """Return repositories that can be reassigned to an install account.

        These are repositories owned by the same GitHub user or organization as
        the installation, but currently configured against a Personal Access
        Token account rather than the GitHub App. Reassigning them moves their
        authentication onto the app.

        The candidates are also limited to repositories the app can actually
        access. When the app was installed against selected repositories, this
        asks GitHub which repositories the installation can read and drops any
        the app cannot reach.

        Args:
            installation_account (reviewboard.hostingsvcs.models.
                                  HostingServiceAccount):
                The installation account the repositories would move to. The
                ``owner_login`` stored on the account identifies the user or
                organization to match.

        Returns:
            list of reviewboard.scmtools.models.Repository:
            The repositories eligible for reassignment.

        Raises:
            reviewboard.hostingsvcs.base.errors.HostingServiceError:
                The app's accessible repositories could not be retrieved from
                GitHub.
        """
        from reviewboard.hostingsvcs.github.service import GitHub

        app_data = get_github_app_data(installation_account)

        if not is_installation_data(app_data):
            return []

        owner_login = app_data.owner_login.lower()

        if not owner_login:
            return []

        hosting_url = installation_account.hosting_url or ''

        candidates = (
            Repository.objects
            .filter(
                hosting_account__service_name='github',
                local_site=installation_account.local_site,
                archived=False)
            .exclude(hosting_account=installation_account)
            .select_related('hosting_account')
            .order_by('-pk')
        )

        # Owner-matched PAT repositories, paired with their lowercased
        # owner/name full name for the accessibility check below.
        matched: list[tuple[Repository, str]] = []

        for repository in candidates:
            account = repository.hosting_account

            # Match the same GitHub server. hosting_url is nullable, so treat a
            # missing value and an empty string as the same (github.com).
            if (account.hosting_url or '') != hosting_url:
                continue

            # Only offer repositories backed by a Personal Access Token
            # account. Accounts created for the app (the hidden app record or
            # installation accounts) carry 'github_app' data.
            if get_github_app_data(account) is not None:
                continue

            try:
                plan = repository.extra_data['repository_plan']
                service = repository.hosting_service
                owner = service._get_repository_owner_raw(
                    plan, repository.extra_data)
                name = service._get_repository_name_raw(
                    plan, repository.extra_data)
            except (KeyError, InvalidPlanError, MissingHostingServiceError):
                continue

            if owner.lower() == owner_login:
                matched.append((repository, name.lower()))

        # When the app can access all repositories on the account, every
        # owner-matched candidate is accessible by definition, so skip the API
        # call. Otherwise ask GitHub which repositories the installation can
        # read and keep only those.
        if app_data.repository_selection == 'all':
            return [
                repository
                for repository, _name in matched
            ]

        service = installation_account.service
        assert isinstance(service, GitHub)

        accessible = {
            name
            for owner, name in service.get_accessible_repositories()
            if owner == owner_login
        }

        return [
            repository
            for repository, full_name in matched
            if full_name in accessible
        ]


@method_decorator(csrf_exempt, name='dispatch')
class GitHubAppWebhookView(View):
    """Receive webhook events from a GitHub App.

    A GitHub App has a single, app-wide webhook URL that receives events from
    every account the app is installed on.

    This is currently a stub. It acknowledges deliveries so GitHub considers
    the webhook healthy, but does not yet act on any events.

    Version Added:
        9.0
    """

    def post(
        self,
        request: HttpRequest,
        *args,
        **kwargs,
    ) -> HttpResponse:
        """Handle HTTP POST requests.

        Args:
            request (django.http.HttpRequest):
                The webhook request from GitHub.

            *args (tuple, unused):
                Unused positional arguments.

            **kwargs (dict, unused):
                Unused keyword arguments.

        Returns:
            django.http.HttpResponse:
            An empty response acknowledging the delivery.
        """
        event = request.META.get('HTTP_X_GITHUB_EVENT', '')

        # TODO: Verify the X-Hub-Signature-256 header against the app's stored
        # webhook secret and dispatch events once handlers exist.
        logger.debug('Received GitHub App webhook event: %s', event)

        return HttpResponse(status=204)
