"""Forms for JIRA.

Version Added:
    9.0:
    Split up ``reviewboard.hostingsvcs.jira``.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING
from urllib.parse import urlparse

from django import forms
from django.utils.translation import gettext_lazy as _

from reviewboard.admin.validation import validate_bug_tracker_base_hosting_url
from reviewboard.hostingsvcs.base.forms import (
    BaseBugTrackerConfigForm,
    BaseHostingServiceAuthForm,
    BaseHostingServiceRepositoryForm,
)

if TYPE_CHECKING:
    from typing import Any


class JIRAForm(BaseHostingServiceRepositoryForm):
    """The legacy repository form for JIRA settings.

    This collects JIRA settings stored on a repository (``bug_tracker-*`` keys
    in ``extra_data``). It exists only for compatibility with legacy
    per-repository bug tracker settings written through the repository form
    and the Web API. Standalone configurations use
    :py:class:`JIRABugTrackerConfigForm`.
    """

    jira_url = forms.CharField(
        label=_('JIRA URL'),
        max_length=64,
        required=True,
        widget=forms.TextInput(attrs={'size': '60'}),
        validators=[validate_bug_tracker_base_hosting_url])

    def clean_jira_url(self) -> str:
        """Clean the JIRA URL field.

        Returns:
            str:
            The cleaned field data.
        """
        return self.cleaned_data['jira_url'].rstrip('/ ')


#: The Atlassian Cloud domain suffix for JIRA Cloud sites.
#:
#: Version Added:
#:     9.0
_ATLASSIAN_CLOUD_DOMAIN = '.atlassian.net'


def get_jira_cloud_site(
    url: str | None,
) -> str | None:
    """Return the Atlassian site name for a JIRA Cloud URL.

    Version Added:
        9.0

    Args:
        url (str):
            The JIRA server URL.

    Returns:
        str:
        The site name (the "yourteam" in yourteam.atlassian.net), or
        ``None`` if the URL is not for a JIRA Cloud site.
    """
    hostname = urlparse(url or '').hostname or ''

    if hostname.endswith(_ATLASSIAN_CLOUD_DOMAIN):
        return hostname.removesuffix(_ATLASSIAN_CLOUD_DOMAIN)

    return None


class JIRAAuthForm(BaseHostingServiceAuthForm):
    """Authentication form for JIRA accounts.

    This covers both JIRA Cloud (identified by an Atlassian site name) and
    JIRA Data Center (identified by a server URL). The deployment is chosen on
    the connect page and carried in a hidden field, and only the chosen
    deployment's fields are shown.

    This uses its own URL fields, rather than marking the service as
    self-hosted, so the legacy repository form's bug tracker fields are
    unaffected.

    Version Added:
        9.0
    """

    jira_deployment = forms.ChoiceField(
        required=False,
        choices=(
            ('cloud', _('JIRA Cloud')),
            ('dc', _('JIRA Data Center')),
        ),
        widget=forms.HiddenInput())

    jira_cloud_site = forms.CharField(
        label=_('Atlassian site name'),
        required=False,
        widget=forms.TextInput(attrs={'size': 30}),
        help_text=_(
            'The name of the Atlassian Cloud site: the <code>yourteam</code> '
            'in <code>yourteam.atlassian.net</code>.'
        ))

    jira_server_url = forms.CharField(
        label=_('JIRA server URL'),
        required=False,
        widget=forms.TextInput(attrs={'size': 30}),
        validators=[validate_bug_tracker_base_hosting_url],
        help_text=_(
            'The root URL of the JIRA server (for example, '
            'https://jira.example.com).'
        ))

    field_order = [
        'jira_deployment',
        'jira_cloud_site',
        'jira_server_url',
        'hosting_account_username',
        'hosting_account_password',
    ]

    class Meta:
        """Metadata for the form."""

        labels = {
            'hosting_account_username': _('Username or e-mail address'),
            'hosting_account_password': _('API token or password'),
        }

        help_texts = {
            'hosting_account_username': _(
                'The JIRA username for self-hosted servers, or the e-mail '
                'address of the Atlassian account for JIRA Cloud.'
            ),
            'hosting_account_password': _(
                'An API token (required for JIRA Cloud) or the account '
                'password for self-hosted servers. API tokens can be '
                'created at the <a href="https://id.atlassian.com/'
                'manage-profile/security/api-tokens" target="_blank" '
                'nofollow noreferrer">API Tokens Management Page</a>.'
            ),
        }

    def __init__(self, *args, **kwargs) -> None:
        """Initialize the form.

        For a submitted form, the chosen deployment's URL field is
        marked required, driving validation.

        Args:
            *args (tuple):
                Positional arguments for the parent form.

            **kwargs (dict):
                Keyword arguments for the parent form.
        """
        super().__init__(*args, **kwargs)

        if self.is_bound:
            if self.data.get('jira_deployment') == 'cloud':
                self.fields['jira_cloud_site'].required = True
            else:
                self.fields['jira_server_url'].required = True

    def clean_jira_cloud_site(self) -> str:
        """Clean the Atlassian site name field.

        Pasted URLs and full domains are normalized down to the bare
        site name.

        Returns:
            str:
            The site name.

        Raises:
            django.forms.ValidationError:
                The site name is not valid.
        """
        site = self.cleaned_data['jira_cloud_site'].strip().lower()
        site = re.sub(r'^https?://', '', site)
        site = site.split('/')[0]

        site = site.removesuffix(_ATLASSIAN_CLOUD_DOMAIN)

        if site and not re.match(r'^[a-z0-9][a-z0-9-]*$', site):
            raise forms.ValidationError(
                _(
                    'Enter the Atlassian site name (the part before '
                    '".atlassian.net").'
                ))

        return site

    def clean_jira_server_url(self) -> str:
        """Clean the server URL field.

        Returns:
            str:
            The server URL, without any trailing slashes.

        Raises:
            django.forms.ValidationError:
                The server URL is not a full HTTP or HTTPS URL.
        """
        server_url = self.cleaned_data['jira_server_url'].strip().rstrip('/')

        if server_url:
            try:
                parsed = urlparse(server_url)
                is_valid = (parsed.scheme in {'http', 'https'} and
                            bool(parsed.hostname))
            except ValueError:
                is_valid = False

            if not is_valid:
                raise forms.ValidationError(
                    _(
                        'Enter the full URL of the JIRA server, starting '
                        'with https:// or http://.'
                    ))

        return server_url

    def clean(self) -> dict[str, Any]:
        """Clean the form fields.

        This resolves the JIRA Cloud site name into a server URL.

        Returns:
            dict:
            The cleaned form data.
        """
        cleaned_data = super().clean() or self.cleaned_data

        if cleaned_data.get('jira_deployment') == 'cloud':
            site = cleaned_data.get('jira_cloud_site')

            if site:
                cleaned_data['jira_server_url'] = \
                    f'https://{site}{_ATLASSIAN_CLOUD_DOMAIN}'

        return cleaned_data

    def get_hosting_url(self) -> str | None:
        """Return the hosting URL for the account.

        This is the JIRA server URL, so that the same username on two JIRA
        servers gets two separate accounts.

        Returns:
            str:
            The JIRA server URL.
        """
        return self.cleaned_data.get('jira_server_url') or None

    def load(self) -> None:
        """Load form fields from the account."""
        super().load()

        account = self.hosting_account

        if account is not None:
            server_url = account.hosting_url or ''
            cloud_site = get_jira_cloud_site(server_url)
            fields = self.fields

            if cloud_site is not None:
                fields['jira_deployment'].initial = 'cloud'
                fields['jira_cloud_site'].initial = cloud_site
            else:
                fields['jira_deployment'].initial = 'dc'

            fields['jira_server_url'].initial = server_url


class JIRABugTrackerConfigForm(BaseBugTrackerConfigForm):
    """Settings form for JIRA bug tracker configurations.

    The JIRA server comes from the configuration's linked account, so this only
    offers scoping the tracker to a project.

    Version Added:
        9.0
    """

    jira_project = forms.CharField(
        label=_('Limit to project'),
        required=False,
        widget=forms.TextInput(attrs={'size': 30}),
        help_text=_(
            "A JIRA project key (for example, ENG) to limit this bug tracker "
            "to. Only that project's issues will be offered in bug searches. "
            "Leave blank to include all projects on the server."
        ))

    def clean_jira_project(self) -> str:
        """Clean the project key field.

        Returns:
            str:
            The project key, uppercased.

        Raises:
            django.forms.ValidationError:
                The project key is not valid.
        """
        project = self.cleaned_data['jira_project'].strip().upper()

        if project and not re.match(r'^[A-Z][A-Z0-9_]*$', project):
            raise forms.ValidationError(
                _('Enter a valid JIRA project key (such as ENG).'))

        return project
