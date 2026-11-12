"""Hosting service for JIRA.

Version Added:
    9.0:
    Split up ``reviewboard.hostingsvcs.jira``.
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils.translation import gettext, gettext_lazy as _
from housekeeping import deprecate_non_keyword_only_args

from reviewboard.deprecation import RemovedInReviewBoard11_0Warning
try:
    from jira.client import JIRA as JIRAClient
    from jira.exceptions import JIRAError
    from requests import RequestException
    has_jira = True
except ImportError:
    has_jira = False

from reviewboard.hostingsvcs.base.bug_tracker import BaseBugTracker
from reviewboard.hostingsvcs.base.connect_ui import BaseHostingServiceConnectUI
from reviewboard.hostingsvcs.base.hosting_service import BaseHostingService
from reviewboard.hostingsvcs.errors import AuthorizationError
from reviewboard.hostingsvcs.jira.forms import (
    JIRAAuthForm,
    JIRABugTrackerConfigForm,
    JIRAForm,
    get_jira_cloud_site,
)
from reviewboard.scmtools.crypto_utils import (
    decrypt_password,
    encrypt_password,
)

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from typing import Any

    from django.http import HttpRequest
    from django.utils.safestring import SafeString

    from reviewboard.hostingsvcs.base.bug_tracker import (
        BugInfo,
        BugSearchResult,
    )
    from reviewboard.hostingsvcs.base.forms import BaseHostingServiceAuthForm
    from reviewboard.hostingsvcs.models import (
        ConfiguredBugTracker,
        HostingServiceAccount,
    )
    from reviewboard.scmtools.models import Repository


logger = logging.getLogger(__name__)


#: A pattern matching JIRA issue keys, such as ``ENG-42``.
#:
#: The project key and issue number are captured as groups.
#:
#: Version Added:
#:     9.0
_ISSUE_KEY_RE = re.compile(r'^([A-Za-z][A-Za-z0-9_]*)-(\d+)$')


#: The issue fields loaded for bug metadata and search results.
#:
#: Loading only these avoids fetching every field of every issue.
#:
#: This is a string rather than a list, because the jira library edits
#: lists of fields in place.
#:
#: Version Added:
#:     9.0
_ISSUE_FIELDS = 'summary,status'


#: The timeout for requests to the JIRA server, in seconds.
#:
#: This keeps a slow or unresponsive server from tying up a web worker.
#:
#: Version Added:
#:     9.0
_REQUEST_TIMEOUT_SECS = 10


class JIRAConnectUI(BaseHostingServiceConnectUI):
    """Connect UI for JIRA.

    Version Added:
        9.0
    """

    def render_connect_ui(
        self,
        request: HttpRequest,
        *,
        form: (BaseHostingServiceAuthForm | None) = None,
    ) -> SafeString:
        """Render the connect UI for JIRA.

        By default, this shows a choice between JIRA Cloud and JIRA Data
        Center. Existing accounts are offered first, to create a bug tracker
        with them. When requested with ``?deployment=cloud`` or
        ``?deployment=dc``, it shows the credentials form for that deployment.

        Version Added:
            9.0

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            form (JIRAAuthForm, optional):
                The authentication form to render.

        Returns:
            django.utils.safestring.SafeString:
            The rendered connect UI.
        """
        deployment = request.GET.get('deployment')

        if deployment not in {'cloud', 'dc'}:
            if form is None:
                form = self.get_auth_form_class()(
                    hosting_service_cls=self._hosting_service_cls,
                    local_site=request.local_site)

            context = self.make_connect_ui_context(request, form=form)

            return mark_safe(render_to_string(
                'hostingsvcs/jira/connect_choice.html',
                context,
                request=request))

        if form is None:
            form = self.get_auth_form_class()(
                hosting_service_cls=self._hosting_service_cls,
                local_site=request.local_site,
                initial={
                    'jira_deployment': deployment,
                })

        self._adjust_auth_form(form, deployment)

        return super().render_connect_ui(request, form=form)

    def make_connect_ui_context(
        self,
        request: HttpRequest,
        *,
        form: BaseHostingServiceAuthForm,
    ) -> dict[str, Any]:
        """Return template context for rendering the connect UI.

        This adds the URLs for the JIRA Cloud and JIRA Data Center connect
        pages, and the actions for existing accounts.

        Version Added:
            9.0

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            form (JIRAAuthForm):
                The authentication form to render.

        Returns:
            dict:
            Template context to use when rendering the connect UI.
        """
        context = super().make_connect_ui_context(request, form=form)

        connect_url = reverse(
            'connected-services-connect',
            kwargs={
                'service_id': self._hosting_service_cls.hosting_service_id,
            })
        context['jira_cloud_connect_url'] = \
            f'{connect_url}?deployment=cloud'
        context['jira_dc_connect_url'] = f'{connect_url}?deployment=dc'
        context['existing_account_actions'] = \
            self.get_existing_account_actions(request)

        return context

    def render_edit_credentials_ui(
        self,
        request: HttpRequest,
        account: HostingServiceAccount,
        *,
        form: (BaseHostingServiceAuthForm | None) = None,
    ) -> SafeString:
        """Render the edit-credentials UI for an existing account.

        The form is adjusted for the account's deployment (JIRA Cloud or JIRA
        Data Center), so only the relevant fields are shown.

        Version Added:
            9.0

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            account (reviewboard.hostingsvcs.models.HostingServiceAccount):
                The account whose credentials are being edited.

            form (JIRAAuthForm, optional):
                The authentication form to render.

        Returns:
            django.utils.safestring.SafeString:
            The rendered edit-credentials UI.
        """
        if form is None:
            form = self.get_auth_form_class()(
                hosting_service_cls=self._hosting_service_cls,
                hosting_account=account,
                local_site=account.local_site)
            form.load()

        if form.is_bound:
            deployment = form.data.get('jira_deployment') or 'dc'
        elif get_jira_cloud_site(account.hosting_url) is not None:
            deployment = 'cloud'
        else:
            deployment = 'dc'

        self._adjust_auth_form(form, deployment)

        context = self.make_connect_ui_context(request, form=form)
        context['wizard_title'] = _('Edit Credentials')
        context['wizard_action_label'] = _('Save')

        return mark_safe(render_to_string(
            self.connect_ui_template,
            context,
            request=request))

    def get_bug_tracker_display_path(
        self,
        bug_tracker: ConfiguredBugTracker,
    ) -> str:
        """Return the path to display for a bug tracker in the admin UI.

        This is the URL of a self-hosted (JIRA Data Center) server. Nothing is
        shown for JIRA Cloud sites.

        Version Added:
            9.0

        Args:
            bug_tracker (reviewboard.hostingsvcs.models.ConfiguredBugTracker):
                The bug tracker configuration to return a display path for.

        Returns:
            str:
            The JIRA server URL, or an empty string.
        """
        service = bug_tracker.service
        assert isinstance(service, JIRA)

        jira_url = service._get_jira_url(bug_tracker) or ''

        if get_jira_cloud_site(jira_url) is not None:
            return ''

        return jira_url

    def _adjust_auth_form(
        self,
        form: BaseHostingServiceAuthForm,
        deployment: str,
    ) -> None:
        """Adjust the auth form's fields for a deployment.

        The other deployment's URL field is removed, and the credential labels
        are tweaked for the deployment. This only affects how the form renders.
        Validation is driven by the form values.

        Version Added:
            9.0

        Args:
            form (JIRAAuthForm):
                The form to adjust.

            deployment (str):
                The chosen deployment: ``cloud`` or ``dc``.
        """
        fields = form.fields

        if deployment == 'cloud':
            fields.pop('jira_server_url', None)
            fields['jira_cloud_site'].required = True

            username_field = fields['hosting_account_username']
            username_field.label = _('Atlassian account e-mail address')
            username_field.help_text = ''

            password_field = fields['hosting_account_password']
            password_field.label = _('API token')
            password_field.help_text = _(
                'An API token without scopes, created at the <a href="'
                'https://id.atlassian.com/manage-profile/security/api-tokens" '
                'target="_blank" nofollow noreferrer>API Tokens Management '
                'Page</a>. Account passwords do not work with JIRA Cloud.')
        else:
            fields.pop('jira_cloud_site', None)
            fields['jira_server_url'].required = True

            username_field = fields['hosting_account_username']
            username_field.label = _('Username')
            username_field.help_text = ''

            password_field = fields['hosting_account_password']
            password_field.label = _('Password or personal access token')
            password_field.help_text = ''


class JIRA(BaseHostingService, BaseBugTracker):
    """Hosting service for JIRA."""

    hosting_service_id = 'jira'
    name = 'JIRA'

    auth_form = JIRAAuthForm
    bug_tracker_config_form = JIRABugTrackerConfigForm
    bug_tracker_label = _('JIRA Issues')
    bug_tracker_requires_account = True
    connect_ui_cls = JIRAConnectUI
    form = JIRAForm
    needs_authorization = True
    supports_bug_info = True
    supports_bug_search = True
    supports_bug_trackers = True
    _logo_image = 'rb/images/services/jira.svg'

    bug_tracker_field = '%(jira_url)s/browse/%%s'

    ######################
    # Instance variables #
    ######################

    #: The JIRA client, once one has been built.
    jira_client: JIRAClient | None

    #: The server URL that :py:attr:`jira_client` was built for.
    _jira_client_url: str | None

    def __init__(
        self,
        account: HostingServiceAccount,
    ) -> None:
        """Initialize the hosting service.

        Args:
            account (reviewboard.hostingsvcs.models.HostingServiceAccount):
                The hosting service account.
        """
        super().__init__(account)

        self.jira_client = None
        self._jira_client_url = None

    def authorize(
        self,
        *,
        username: str | None,
        password: str | None,
        hosting_url: (str | None) = None,
        **kwargs,
    ) -> None:
        """Authorize an account for JIRA.

        JIRA uses HTTP Basic Auth for its API, with either an API token
        (Atlassian Cloud) or a password (self-hosted servers). The credentials
        are verified against the server, and the token or password is stored,
        encrypted, for later API requests.

        Version Added:
            9.0

        Args:
            username (str):
                The username or Atlassian account e-mail address.

            password (str):
                The API token or password.

            hosting_url (str, optional):
                The JIRA server URL.

            **kwargs (dict, unused):
                Additional keyword arguments.

        Raises:
            reviewboard.hostingsvcs.errors.AuthorizationError:
                The credentials could not be verified.
        """
        if not has_jira:
            raise AuthorizationError(gettext(
                'JIRA support requires the "jira" Python package to be '
                'installed.'
            ))

        server_url = hosting_url

        if not username or not password or not server_url:
            raise AuthorizationError(gettext(
                'A JIRA server URL, username, and API token or password '
                'are required.'
            ))

        try:
            client = JIRAClient(
                options={
                    'server': server_url,
                },
                basic_auth=(username, password),
                max_retries=0,
                timeout=_REQUEST_TIMEOUT_SECS)

            # This performs an authenticated request, verifying the
            # credentials.
            client.myself()
        except JIRAError as e:
            if getattr(e, 'status_code', None) == 401:
                if get_jira_cloud_site(server_url) is not None:
                    # The most common cause on JIRA Cloud is using an
                    # account password, which Atlassian no longer
                    # accepts for the API.
                    raise AuthorizationError(gettext(
                        'JIRA rejected the credentials. JIRA Cloud requires '
                        'an API token instead of a password. Create one '
                        '(choose "without scopes") at '
                        'https://id.atlassian.com/manage-profile/security/'
                        'api-tokens, and use it together with the e-mail '
                        'address of your Atlassian account.'
                    ))

                raise AuthorizationError(gettext(
                    'JIRA rejected the username and API token or password.'
                ))

            raise AuthorizationError(
                gettext('Unable to authenticate with JIRA: {error}')
                .format(error=getattr(e, 'text', None) or e))
        except (RequestException, ValueError) as e:
            raise AuthorizationError(
                gettext('Unable to communicate with JIRA: {error}')
                .format(error=e))

        account = self.account
        account.data['password'] = encrypt_password(password)
        account.save()

    def is_authorized(self) -> bool:
        """Return whether the account has stored credentials.

        Version Added:
            9.0

        Returns:
            bool:
            ``True`` if the account has a stored API token or password.
        """
        return 'password' in self.account.data

    @classmethod
    def is_bug_tracker_account_required(
        cls,
        settings: Mapping[str, Any],
    ) -> bool:
        """Return whether a bug tracker configuration needs an account.

        Migrated legacy configurations carrying their own server URL are
        grandfathered in without an account.

        Version Added:
            9.0

        Args:
            settings (dict):
                The configuration's settings.

        Returns:
            bool:
            ``True`` if the configuration requires a linked account.
        """
        return not settings.get('jira_url')

    def _get_jira_url(
        self,
        config: ConfiguredBugTracker,
    ) -> str | None:
        """Return the JIRA server URL for a configuration.

        When the configuration has a linked account, the account's server is
        always used. Migrated legacy configurations may also carry a URL in
        their settings, but it is ignored once an account is linked, so the
        account's credentials are only ever sent to the server they were
        created for. Without an account, the settings URL is used.

        Version Added:
            9.0

        Args:
            config (reviewboard.hostingsvcs.models.ConfiguredBugTracker):
                The bug tracker configuration.

        Returns:
            str:
            The server URL, or ``None`` if one is not available.
        """
        account = config.hosting_account

        if account is not None:
            return account.hosting_url or None

        return config.settings.get('jira_url') or None

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
            The URL for the bug, or ``None`` if no server URL is
            available.
        """
        jira_url = self._get_jira_url(config)

        if jira_url:
            return f'{jira_url}/browse/{bug_id}'

        return None

    def get_bug_id_sort_key(
        self,
        *,
        bug_id: str,
    ) -> tuple[str | int, ...] | None:
        """Return a sort key for a JIRA issue key.

        Well-formed issue keys (such as ``ENG-42``) sort by project and then
        numerically by issue number, so ``ENG-5`` orders before ``ENG-12``.

        Version Added:
            9.0

        Args:
            bug_id (str):
                The ID of the bug.

        Returns:
            tuple:
            The ``(project, number)`` sort key, or ``None`` for IDs that are
            not issue keys.
        """
        m = _ISSUE_KEY_RE.match(bug_id)

        if m:
            return (m.group(1).upper(), int(m.group(2)))

        return None

    def _get_jira_client(
        self,
        jira_url: str,
    ) -> JIRAClient | None:
        """Return a JIRA client for a server URL.

        The client is built on first use and reused for the same server after
        that.

        The account's stored credentials are only used when the server is the
        account's own server. Any other server (such as a legacy URL stored on
        a repository) is connected to anonymously, so the credentials are
        never sent anywhere else.

        Version Added:
            9.0

        Args:
            jira_url (str):
                The root URL of the JIRA server.

        Returns:
            jira.client.JIRA:
            The client, or ``None`` if one could not be built.
        """
        if (self.jira_client is not None and
            self._jira_client_url == jira_url):
            return self.jira_client

        account = self.account

        try:
            if (account is not None and
                'password' in account.data and
                account.hosting_url == jira_url):
                jira_client = JIRAClient(
                    options={
                        'server': jira_url,
                    },
                    basic_auth=(account.username,
                                decrypt_password(account.data['password'])),
                    max_retries=0,
                    timeout=_REQUEST_TIMEOUT_SECS)
            else:
                jira_client = JIRAClient(
                    options={
                        'server': jira_url,
                    },
                    max_retries=0,
                    timeout=_REQUEST_TIMEOUT_SECS)
        except (JIRAError, RequestException, ValueError) as e:
            # Building the client contacts the server, so this fails if the
            # server is unreachable or rejects the credentials.
            logger.warning(
                'Unable to initialize JIRAClient for server %s: %s',
                jira_url, e)
            return None

        self.jira_client = jira_client
        self._jira_client_url = jira_url

        return jira_client

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
        result: BugInfo = {
            'summary': '',
            'description': '',
            'status': '',
        }

        if config is not None:
            jira_url = self._get_jira_url(config)
        elif repository is not None:
            jira_url = repository.extra_data.get('bug_tracker-jira_url')
        else:
            jira_url = None

        if not jira_url:
            return result

        if has_jira:
            jira_client = self._get_jira_client(jira_url)

            if jira_client is None:
                return result

            try:
                jira_issue = jira_client.issue(
                    bug_id,
                    fields=f'{_ISSUE_FIELDS},description')
                result = {
                    'description': jira_issue.fields.description or '',
                    'summary': jira_issue.fields.summary or '',
                    'status': str(jira_issue.fields.status),
                }
            except (JIRAError, RequestException) as e:
                logger.warning('Unable to fetch JIRA data for issue %s: %s',
                               bug_id, e, exc_info=True)

        return result

    def get_bugs_info(
        self,
        *,
        config: ConfiguredBugTracker,
        bug_ids: Sequence[str],
    ) -> Mapping[str, BugInfo]:
        """Return the information for several issues at once.

        This loads every issue in a single JQL query, rather than one request
        per issue. If that query fails, each issue is fetched separately
        instead.

        IDs that are not well-formed issue keys are skipped.

        The descriptions are not included. Callers needing a description should
        use :py:meth:`get_bug_info`.

        Version Added:
            9.0

        Args:
            config (reviewboard.hostingsvcs.models.ConfiguredBugTracker):
                The bug tracker configuration.

            bug_ids (list of str):
                The keys of the issues to fetch.

        Returns:
            dict:
            A mapping of issue key to
            :py:class:`~reviewboard.hostingsvcs.base.bug_tracker.BugInfo`.
        """
        if not has_jira:
            return {}

        # Bug IDs are typed in by users. Only well-formed issue keys are put
        # into the JQL query. Anything else could change the query, or make it
        # invalid and fail the whole batch.
        keys = [
            bug_id
            for bug_id in bug_ids
            if _ISSUE_KEY_RE.match(bug_id)
        ]

        if not keys:
            return {}

        jira_url = self._get_jira_url(config)

        if not jira_url:
            return {}

        jira_client = self._get_jira_client(jira_url)

        if jira_client is None:
            return {}

        try:
            results = self._load_bugs_by_key(jira_client, keys)
        except JIRAError as e:
            if e.status_code != 400:
                # Fetching each issue would fail the same way (bad
                # credentials, rate limits, server errors).
                logger.warning('Unable to load JIRA issues %s: %s',
                               keys, e, exc_info=True)

                return {}

            # JIRA Cloud rejects the whole query with an HTTP 400 if any key
            # does not exist or is not visible (for example, a deleted
            # issue). validate_query is ignored on Cloud. Fetch each issue on
            # its own instead, so the others still load.
            logger.warning(
                'Unable to load JIRA issues %s in one query. Fetching them '
                'separately: %s',
                keys, e)

            return super().get_bugs_info(config=config,
                                         bug_ids=keys)

        return {
            result['bug_id']: {
                'description': '',
                'status': result.get('status', ''),
                'summary': result['summary'],
            }
            for result in results
        }

    def search_bugs(
        self,
        *,
        config: ConfiguredBugTracker,
        query: str,
        limit: int = 25,
    ) -> Sequence[BugSearchResult]:
        """Return issues matching a search query.

        This searches through JIRA's issue picker, which matches full and
        partial issue keys ("ENG", "ENG-1") and summary word prefixes, using
        JIRA's own ranking. An exact key match is promoted to the top. When
        the picker is unavailable, this falls back to JQL, matching an exact
        issue key and then summary text.

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
            The matching issues.
        """
        query = query.strip()

        if not has_jira or not query:
            return []

        jira_url = self._get_jira_url(config)

        if not jira_url:
            return []

        jira_client = self._get_jira_client(jira_url)

        if jira_client is None:
            return []

        project = (config.settings.get('jira_project') or '').upper()

        picker_keys = self._search_bug_keys(
            jira_client,
            jira_url=jira_url,
            query=query,
            project=project)

        if picker_keys and project:
            # The configuration is limited to a project. Every key in a project
            # starts with its key, so other projects' issues are filtered out.
            picker_keys = [
                key
                for key in picker_keys
                if key.startswith(f'{project}-')
            ]

        if picker_keys:
            # An exact key match goes first. The rest keep the picker's
            # ranking.
            exact_key = query.upper()

            if exact_key in picker_keys:
                picker_keys.remove(exact_key)
                picker_keys.insert(0, exact_key)

            picker_keys = picker_keys[:limit]

            try:
                return self._load_bugs_by_key(jira_client, picker_keys)
            except JIRAError as e:
                logger.warning(
                    'Unable to load JIRA issues %s: %s',
                    picker_keys, e, exc_info=True)

                return []

        # The picker is unavailable or found nothing. Fall back to JQL,
        # matching an exact issue key and then summary text. Searching all
        # text fields (descriptions, comments) is too noisy for a typeahead.
        escaped_query = (
            query
            .replace('\\', '\\\\')
            .replace('"', '\\"')
        )

        jql_queries: list[str] = []

        if (_ISSUE_KEY_RE.match(query) and
            (not project or query.upper().startswith(f'{project}-'))):
            jql_queries.append(f'key = "{query.upper()}"')

        summary_jql = f'summary ~ "{escaped_query}*"'

        if project:
            summary_jql += f' AND project = "{project}"'

        jql_queries.append(summary_jql)

        results: list[BugSearchResult] = []
        seen_keys: set[str] = set()

        for jql in jql_queries:
            remaining = limit - len(results)

            if remaining <= 0:
                break

            try:
                # validate_query is off so that a key that doesn't exist
                # returns no results instead of erroring. This only works
                # on Server/Data Center. Cloud ignores it and returns an
                # HTTP 400, which is logged below.
                issues = jira_client.search_issues(
                    jql,
                    maxResults=remaining,
                    validate_query=False,
                    fields=_ISSUE_FIELDS)
            except JIRAError as e:
                logger.warning(
                    'Unable to search JIRA issues with "%s": %s',
                    jql, e, exc_info=True)
                continue

            for issue in issues:
                if issue.key not in seen_keys:
                    seen_keys.add(issue.key)
                    results.append({
                        'bug_id': issue.key,
                        'status': str(issue.fields.status),
                        'summary': issue.fields.summary,
                    })

        return results

    def _search_bug_keys(
        self,
        jira_client: JIRAClient,
        *,
        jira_url: str,
        query: str,
        project: str,
    ) -> list[str] | None:
        """Return issue keys matching a query through the issue picker.

        The issue picker is JIRA's own typeahead: it matches full and partial
        issue keys and summary word prefixes, ranked the same way JIRA's UI
        ranks them. JQL offers no equivalent (key comparisons require both
        operands to be existing issues, so prefix ranges cannot be expressed).

        Version Added:
            9.0

        Args:
            jira_client (jira.client.JIRA):
                The JIRA client.

            jira_url (str):
                The root URL of the JIRA server.

            query (str):
                The typed query.

            project (str):
                The project key to limit matches to, or an empty string for
                all projects. This only limits the "current search" section.
                The "history" section may still include other projects' issues.

        Returns:
            list of str:
            The matching issue keys, in the picker's order, or ``None`` if the
            picker could not be queried.
        """
        session = jira_client._session
        assert session is not None

        if project:
            current_jql = f'project = "{project}"'
        else:
            current_jql = ''

        try:
            rsp = session.get(
                f'{jira_url}/rest/api/2/issue/picker',
                params={
                    'query': query,

                    # Without this, the "current search" section (the
                    # actual matches) is omitted from the response.
                    'currentJQL': current_jql,
                })
            rsp.raise_for_status()
            data = rsp.json()
        except Exception as e:
            logger.warning(
                'Unable to query the JIRA issue picker for "%s": %s',
                query, e)

            return None

        keys: list[str] = []

        for section in data.get('sections', []):
            for issue in section.get('issues', []):
                key = issue.get('key')

                if key and key not in keys:
                    keys.append(key)

        return keys

    def _load_bugs_by_key(
        self,
        jira_client: JIRAClient,
        keys: list[str],
    ) -> Sequence[BugSearchResult]:
        """Return search results for a list of issue keys.

        Args:
            jira_client (jira.client.JIRA):
                The JIRA client.

            keys (list of str):
                The issue keys, in the order results should appear. These
                must be well-formed issue keys, since they are placed
                directly into a JQL query.

        Returns:
            list of reviewboard.hostingsvcs.base.bug_tracker.
            BugSearchResult:
            The results, in key order. Keys that could not be loaded
            are omitted.

        Raises:
            jira.exceptions.JIRAError:
                The issues could not be loaded.
        """
        jql_keys = ', '.join(f'"{key}"' for key in keys)
        issues = jira_client.search_issues(
            f'key in ({jql_keys})',
            maxResults=len(keys),
            validate_query=False,
            fields=_ISSUE_FIELDS)

        issues_by_key = {
            issue.key: issue
            for issue in issues
        }

        return [
            {
                'bug_id': issue.key,
                'status': str(issue.fields.status),
                'summary': issue.fields.summary,
            }
            for issue in (issues_by_key.get(key) for key in keys)
            if issue is not None
        ]
