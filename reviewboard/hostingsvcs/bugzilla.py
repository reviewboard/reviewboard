"""Hosting service for Bugzilla."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING
from urllib.error import HTTPError
from urllib.parse import quote, urlencode

from django import forms
from django.utils.translation import gettext, gettext_lazy as _
from housekeeping import deprecate_non_keyword_only_args

from reviewboard.deprecation import RemovedInReviewBoard11_0Warning
from reviewboard.certs.errors import CertificateVerificationError
from reviewboard.hostingsvcs.base.bug_tracker import BaseBugTracker
from reviewboard.hostingsvcs.base.client import HostingServiceClient
from reviewboard.hostingsvcs.base.connect_ui import BaseHostingServiceConnectUI
from reviewboard.hostingsvcs.base.forms import (
    BaseBugTrackerConfigForm,
    BaseHostingServiceAuthForm,
    BaseHostingServiceRepositoryForm,
)
from reviewboard.hostingsvcs.base.hosting_service import BaseHostingService
from reviewboard.hostingsvcs.errors import AuthorizationError
from reviewboard.admin.validation import validate_bug_tracker_base_hosting_url
from reviewboard.scmtools.crypto_utils import (
    decrypt_password,
    encrypt_password,
)
from reviewboard.scmtools.errors import (
    UnverifiedCertificateError as LegacyUnverifiedCertificateError,
)

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from typing import Any

    from typelets.json import JSONDict

    from reviewboard.hostingsvcs.base.bug_tracker import (
        BugInfo,
        BugSearchResult,
    )
    from reviewboard.hostingsvcs.base.hosting_service import (
        HostingServiceCredentials,
    )
    from reviewboard.hostingsvcs.models import (
        ConfiguredBugTracker,
        HostingServiceAccount,
    )
    from reviewboard.scmtools.models import Repository


logger = logging.getLogger(__name__)


class BugzillaForm(BaseHostingServiceRepositoryForm):
    """The legacy repository form for Bugzilla settings.

    This collects Bugzilla settings stored on a repository
    (``bug_tracker-*`` keys in ``extra_data``). It exists only for
    compatibility with legacy per-repository bug tracker settings
    written through the repository form and the Web API. Standalone
    configurations use :py:class:`BugzillaBugTrackerConfigForm`.
    """

    bugzilla_url = forms.CharField(
        label=_('Bugzilla URL'),
        max_length=64,
        required=True,
        widget=forms.TextInput(attrs={'size': '60'}),
        validators=[validate_bug_tracker_base_hosting_url])

    def clean_bugzilla_url(self) -> str:
        """Clean the bugzilla URL field.

        Returns:
            str:
            The cleaned data.
        """
        return self.cleaned_data['bugzilla_url'].rstrip('/')


class BugzillaAuthForm(BaseHostingServiceAuthForm):
    """Authentication form for Bugzilla accounts.

    Bugzilla accounts use the account's login and an API key. API keys are
    available in Bugzilla 5.0 and newer.

    Version Added:
        9.0
    """

    bugzilla_url = forms.CharField(
        label=_('Bugzilla URL'),
        required=True,
        widget=forms.TextInput(attrs={'size': 30}),
        validators=[validate_bug_tracker_base_hosting_url],
        help_text=_(
            'The root URL of the Bugzilla server (for example, '
            'https://bugzilla.example.com).'
        ))

    field_order = [
        'bugzilla_url',
        'hosting_account_username',
        'hosting_account_password',
    ]

    class Meta:
        """Metadata for the form."""

        labels = {
            'hosting_account_username': _('Login'),
            'hosting_account_password': _('API key'),
        }

        help_texts = {
            'hosting_account_username': _(
                'The login of the Bugzilla account that owns the API key. '
                'This is usually an e-mail address.'
            ),
            'hosting_account_password': _(
                'An API key for the account. This can be created in '
                'Bugzilla under <code>Preferences > API Keys.</code>'
            ),
        }

    def clean_bugzilla_url(self) -> str:
        """Clean the Bugzilla URL field.

        Returns:
            str:
            The Bugzilla URL, without any trailing slashes.
        """
        return self.cleaned_data['bugzilla_url'].rstrip('/')

    def get_hosting_url(self) -> str | None:
        """Return the hosting URL for the account.

        This is the Bugzilla URL, so that the same login on two Bugzilla
        servers gets two separate accounts.

        Returns:
            str:
            The Bugzilla URL.
        """
        return self.cleaned_data.get('bugzilla_url') or None

    def get_initial_data(self) -> JSONDict:
        """Return initial data for the form, based on the account.

        This adds the account's Bugzilla URL to the default initial data.

        Returns:
            dict:
            Initial data for the form. Keys are field names.
        """
        initial = super().get_initial_data()
        account = self.hosting_account

        if account is not None:
            initial['bugzilla_url'] = account.hosting_url or ''

        return initial


class BugzillaBugTrackerConfigForm(BaseBugTrackerConfigForm):
    """Settings form for Bugzilla bug tracker configurations.

    Version Added:
        9.0
    """

    bugzilla_url = forms.CharField(
        label=_('Bugzilla URL'),
        max_length=64,
        required=False,
        widget=forms.TextInput(attrs={'size': '60'}),
        validators=[validate_bug_tracker_base_hosting_url],
        help_text=_(
            'The root URL of the Bugzilla server. This is only needed when no '
            'account is linked. A linked account always uses its own server.'
        ))

    def clean_bugzilla_url(self) -> str:
        """Clean the bugzilla URL field.

        Returns:
            str:
            The cleaned data.
        """
        return self.cleaned_data['bugzilla_url'].rstrip('/')


class BugzillaConnectUI(BaseHostingServiceConnectUI):
    """Connect UI for Bugzilla.

    Version Added:
        9.0
    """

    def get_bug_tracker_display_path(
        self,
        bug_tracker: ConfiguredBugTracker,
    ) -> str:
        """Return the path to display for a bug tracker in the admin UI.

        This is the URL of the Bugzilla server that the bug tracker uses.

        Args:
            bug_tracker (reviewboard.hostingsvcs.models.ConfiguredBugTracker):
                The bug tracker configuration to return a display path for.

        Returns:
            str:
            The Bugzilla URL, or an empty string if there isn't one.
        """
        service = bug_tracker.service
        assert isinstance(service, Bugzilla)

        return service._get_server(bug_tracker)[0] or ''


class BugzillaClient(HostingServiceClient['Bugzilla']):
    """API client for Bugzilla.

    Version Added:
        9.0
    """

    def get_http_credentials(
        self,
        account: HostingServiceAccount,
        username: (str | None) = None,
        password: (str | None) = None,
        **kwargs,
    ) -> HostingServiceCredentials:
        """Return credentials used to authenticate with the service.

        Bugzilla takes its API key as a request parameter, which
        :py:meth:`Bugzilla._api_get` adds. The stored key is never sent
        as HTTP Basic Auth.

        Args:
            account (reviewboard.hostingsvcs.models.HostingServiceAccount):
                The stored authentication data for the service.

            username (str, unused):
                An explicit username passed by the caller.

            password (str, unused):
                An explicit password passed by the caller.

            **kwargs (dict, unused):
                Additional keyword arguments.

        Returns:
            dict:
            An empty dictionary.
        """
        return {}


class Bugzilla(BaseHostingService, BaseBugTracker):
    """Hosting service for Bugzilla.

    Bugzilla servers can be used anonymously, or with a linked account for
    servers that require a login. Linked accounts authenticate with an API
    key.

    Version Changed:
        9.0:
        Added support for linked accounts.
    """

    hosting_service_id = 'bugzilla'
    name = 'Bugzilla'

    auth_form = BugzillaAuthForm
    bug_tracker_config_form = BugzillaBugTrackerConfigForm
    bug_tracker_label = _('Bugzilla Bugs')
    client_class = BugzillaClient
    connect_ui_cls = BugzillaConnectUI
    form = BugzillaForm
    needs_authorization = True
    supports_bug_info = True
    supports_bug_search = True
    supports_bug_trackers = True
    _logo_image = 'rb/images/services/bugzilla.svg'

    bug_tracker_field = '%(bugzilla_url)s/show_bug.cgi?id=%%s'

    def authorize(
        self,
        *,
        username: str | None,
        password: str | None,
        hosting_url: (str | None) = None,
        **kwargs,
    ) -> None:
        """Authorize an account for Bugzilla.

        The API key is checked with Bugzilla's ``valid_login`` API, which
        confirms that the key is valid and belongs to the login. The key is
        then stored, encrypted, for later API requests.

        Version Added:
            9.0

        Args:
            username (str):
                The Bugzilla login.

            password (str):
                The API key.

            hosting_url (str, optional):
                The Bugzilla URL.

            **kwargs (dict, unused):
                Additional keyword arguments.

        Raises:
            reviewboard.certs.errors.CertificateVerificationError:
                A remote certificate could not be verified.

            reviewboard.hostingsvcs.errors.AuthorizationError:
                The credentials could not be verified.

            reviewboard.scmtools.errors.UnverifiedCertificateError:
                A remote certificate could not be verified.
        """
        bugzilla_url = hosting_url

        if not username or not password or not bugzilla_url:
            raise AuthorizationError(
                gettext('A Bugzilla URL, login, and API key are required.'))

        try:
            data = self._api_get(bugzilla_url=bugzilla_url,
                                 path='valid_login',
                                 params={
                                     'login': username,
                                 },
                                 api_key=password)
        except HTTPError as e:
            raise AuthorizationError(
                gettext('Bugzilla rejected the login or API key: {error}')
                .format(error=self._get_error_message(e)))
        except (CertificateVerificationError,
                LegacyUnverifiedCertificateError):
            # Let these propagate up.
            raise
        except Exception as e:
            raise AuthorizationError(
                gettext('Unable to communicate with Bugzilla: {error}')
                .format(error=e))

        if data.get('result') is not True:
            raise AuthorizationError(
                gettext('This API key does not belong to the login {user}.')
                .format(user=username))

        account = self.account
        account.data['password'] = encrypt_password(password)
        account.save()

    def is_authorized(self) -> bool:
        """Return whether the account has a stored API key.

        Version Added:
            9.0

        Returns:
            bool:
            ``True`` if the account has a stored API key.
        """
        return 'password' in self.account.data

    @classmethod
    def is_bug_tracker_account_required(
        cls,
        settings: Mapping[str, Any],
    ) -> bool:
        """Return whether a bug tracker configuration needs an account.

        A configuration needs either its own Bugzilla URL or a linked
        account to provide one.

        Version Added:
            9.0

        Args:
            settings (dict):
                The configuration's settings.

        Returns:
            bool:
            ``True`` if the configuration requires a linked account.
        """
        return not settings.get('bugzilla_url')

    def get_bug_url(
        self,
        *,
        config: ConfiguredBugTracker,
        bug_id: str,
    ) -> str | None:
        """Return the public URL for a bug.

        Version Added:
            9.0

        Args:
            config (reviewboard.hostingsvcs.models.ConfiguredBugTracker):
                The bug tracker configuration.

            bug_id (str):
                The ID of the bug.

        Returns:
            str:
            The URL for the bug, or ``None`` if no Bugzilla URL is
            available.
        """
        bugzilla_url = self._get_server(config)[0]

        if bugzilla_url:
            return f'{bugzilla_url}/show_bug.cgi?id={quote(bug_id)}'

        return None

    @deprecate_non_keyword_only_args(RemovedInReviewBoard11_0Warning)
    def get_bug_info_uncached(
        self,
        *,
        repository: (Repository | None) = None,
        bug_id: str,
        config: (ConfiguredBugTracker | None) = None,
    ) -> BugInfo:
        """Return the information for the specified bug.

        Version Changed:
            9.0:
            Added the new ``config`` argument and made arguments keyword-only.

        Args:
            repository (reviewboard.scmtools.models.Repository, optional):
                The repository object, for legacy repository-based calls.

            bug_id (str):
                The ID of the bug to fetch.

            config (reviewboard.hostingsvcs.models.ConfiguredBugTracker,
                    optional):
                The bug tracker configuration.

                Version Added:
                    9.0

        Returns:
            reviewboard.hostingsvcs.base.bug_tracker.BugInfo:
            Information about the bug.
        """
        # This requires making two HTTP requests: one for the summary and
        # status, and one to get the "first comment" (description).
        bug_id = str(bug_id)

        result: BugInfo = {
            'summary': '',
            'description': '',
            'status': '',
        }

        api_key: (str | None) = None

        if config is not None:
            bugzilla_url, api_key = self._get_server(config)
        elif repository is not None:
            bugzilla_url = repository.extra_data.get(
                'bug_tracker-bugzilla_url')
        else:
            bugzilla_url = None

        if not bugzilla_url:
            return result

        # Bug IDs come from users, so they're escaped to keep them from
        # changing the rest of the URL.
        path = f'bug/{quote(bug_id, safe="")}'

        try:
            data = self._api_get(bugzilla_url=bugzilla_url,
                                 path=path,
                                 params={
                                     'include_fields': 'summary,status',
                                 },
                                 api_key=api_key)

            result['summary'] = data['bugs'][0]['summary']
            result['status'] = data['bugs'][0]['status']
        except Exception as e:
            logger.warning('Unable to fetch bugzilla data from %s/rest/%s: '
                           '%s',
                           bugzilla_url, path, e, exc_info=True)

        try:
            data = self._api_get(bugzilla_url=bugzilla_url,
                                 path=f'{path}/comment',
                                 api_key=api_key)

            # Comments are keyed by the bug's numeric ID, even when the bug
            # was requested by alias, so take the only entry.
            bug_comments = next(iter(data['bugs'].values()))
            result['description'] = bug_comments['comments'][0]['text']
        except Exception as e:
            logger.warning('Unable to fetch bugzilla data from %s/rest/%s: '
                           '%s',
                           bugzilla_url, path, e, exc_info=True)

        return result

    def get_bugs_info(
        self,
        *,
        config: ConfiguredBugTracker,
        bug_ids: Sequence[str],
    ) -> Mapping[str, BugInfo]:
        """Return the information for several bugs at once.

        This loads every bug in a single request, rather than one request
        per bug. Bugs that don't exist or can't be viewed are left out.

        The descriptions are not included. Callers needing a description
        should use :py:meth:`get_bug_info`.

        Version Added:
            9.0

        Args:
            config (reviewboard.hostingsvcs.models.ConfiguredBugTracker):
                The bug tracker configuration.

            bug_ids (list of str):
                The IDs or aliases of the bugs to fetch.

        Returns:
            dict:
            A mapping of bug ID to
            :py:class:`~reviewboard.hostingsvcs.base.bug_tracker.BugInfo`.
        """
        bugzilla_url, api_key = self._get_server(config)

        if not bugzilla_url or not bug_ids:
            return {}

        try:
            # With permissive set, Bugzilla reports missing or private bugs
            # in "faults" instead of failing the whole request.
            data = self._api_get(bugzilla_url=bugzilla_url,
                                 path='bug',
                                 params={
                                     'id': ','.join(bug_ids),
                                     'include_fields':
                                         'id,alias,summary,status',
                                     'permissive': 1,
                                 },
                                 api_key=api_key)
        except Exception as e:
            logger.warning('Unable to fetch bugzilla data from %s/rest/bug: '
                           '%s',
                           bugzilla_url, e, exc_info=True)
            return {}

        requested_ids = set(bug_ids)
        results: dict[str, BugInfo] = {}

        for bug in data.get('bugs', []):
            bug_info: BugInfo = {
                'description': '',
                'status': bug.get('status', ''),
                'summary': bug.get('summary', ''),
            }

            # Bugs can be requested by alias, so match on those too.
            for bug_id in [str(bug['id']), *(bug.get('alias') or [])]:
                if bug_id in requested_ids:
                    results[bug_id] = bug_info

        return results

    def search_bugs(
        self,
        *,
        config: ConfiguredBugTracker,
        query: str,
        limit: int = 25,
    ) -> Sequence[BugSearchResult]:
        """Return bugs matching a search query.

        This uses Bugzilla's quicksearch REST API. Both open and closed bugs
        are searched.

        Version Added:
            9.0

        Args:
            config (reviewboard.hostingsvcs.models.ConfiguredBugTracker):
                The bug tracker configuration.

            query (str):
                The search query.

            limit (int, optional):
                The maximum number of results to return.

        Returns:
            list of reviewboard.hostingsvcs.base.bug_tracker.
            BugSearchResult:
            The matching bugs.
        """
        bugzilla_url, api_key = self._get_server(config)
        query = query.strip()

        if not bugzilla_url or not query:
            return []

        # Quicksearch only matches open bugs, unless the query starts with
        # "ALL". A bare bug number already finds that bug whether it's open
        # or closed, and "ALL" would turn it into a text search instead, so
        # it's left as-is.
        if not query.isdigit():
            query = f'ALL {query}'

        try:
            data = self._api_get(bugzilla_url=bugzilla_url,
                                 path='bug',
                                 params={
                                     'include_fields':
                                         'id,summary,status,is_open',
                                     'limit': limit,
                                     'quicksearch': query,
                                 },
                                 api_key=api_key)
        except Exception as e:
            logger.warning('Unable to search bugzilla at %s/rest/bug: %s',
                           bugzilla_url, e, exc_info=True)
            return []

        return [
            {
                'bug_id': str(bug['id']),
                'closed': not bug.get('is_open', True),
                'status': bug.get('status', ''),
                'summary': bug.get('summary', ''),
            }
            for bug in data.get('bugs', [])
        ]

    def _get_server(
        self,
        config: ConfiguredBugTracker,
    ) -> tuple[str | None, str | None]:
        """Return the Bugzilla URL and API key for a configuration.

        When the configuration has a linked account, the account's URL and
        API key are used. The configuration's own URL is ignored, so the key
        is only ever sent to the server it was created on. Without an
        account, the configuration's URL is used with no API key.

        Version Added:
            9.0

        Args:
            config (reviewboard.hostingsvcs.models.ConfiguredBugTracker):
                The bug tracker configuration.

        Returns:
            tuple:
            A 2-tuple of:

            Tuple:
                0 (str):
                    The Bugzilla URL, or ``None`` if one is not available.

                1 (str):
                    The API key, or ``None`` for anonymous requests.
        """
        account = config.hosting_account

        if account is None:
            return config.settings.get('bugzilla_url') or None, None

        account_data = account.data
        api_key: (str | None) = None

        if 'password' in account_data:
            api_key = decrypt_password(account_data['password'])

        return account.hosting_url or None, api_key

    def _api_get(
        self,
        *,
        bugzilla_url: str,
        path: str,
        params: (dict[str, Any] | None) = None,
        api_key: (str | None) = None,
    ) -> Any:
        """Perform a GET request on the Bugzilla REST API.

        The API key is sent as the ``api_key`` query parameter. Bugzilla 6.0
        also accepts an ``X-BUGZILLA-API-KEY`` header, but Bugzilla 5.x only
        accepts the parameter.

        Callers should not log the full request URL, since it may contain
        the API key.

        Version Added:
            9.0

        Args:
            bugzilla_url (str):
                The root URL of the Bugzilla server.

            path (str):
                The path of the API endpoint, relative to ``/rest/``.

            params (dict, optional):
                Query parameters for the request.

            api_key (str, optional):
                The API key to authenticate with, if any.

        Returns:
            object:
            The decoded JSON response.

        Raises:
            urllib.error.URLError:
                The request failed.
        """
        query = dict(params or {})

        if api_key:
            query['api_key'] = api_key

        url = f'{bugzilla_url}/rest/{path}'

        if query:
            url = f'{url}?{urlencode(query)}'

        return self.client.http_get(url).json

    def _get_error_message(
        self,
        error: HTTPError,
    ) -> str:
        """Return a readable message from a Bugzilla HTTP error.

        Bugzilla returns errors as JSON with a ``message`` key. If the
        response is not in that form, the HTTP error itself is used.

        Version Added:
            9.0

        Args:
            error (urllib.error.HTTPError):
                The HTTP error.

        Returns:
            str:
            The error message.
        """
        try:
            message = json.loads(error.read()).get('message')
        except Exception:
            message = None

        return message or str(error)
