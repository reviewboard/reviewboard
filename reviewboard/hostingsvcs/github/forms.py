"""Forms for GitHub.

Version Added:
    9.0:
    Split up :py:mod:`reviewboard.hostingsvcs.github`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django import forms
from django.utils.text import format_lazy
from django.utils.translation import gettext_lazy as _

from reviewboard import get_manual_url
from reviewboard.hostingsvcs.base.forms import (
    BaseHostingServiceAuthForm,
    BaseHostingServiceRepositoryForm,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

    from typelets.django.strings import StrOrPromise


class GitHubAuthForm(BaseHostingServiceAuthForm):
    """Form for authenticating to GitHub."""

    class Meta:
        """Metadata for the GitHubAuthForm."""

        labels: Mapping[str, StrOrPromise] = {
            'hosting_account_username': _('GitHub Username'),
            'hosting_account_password': _('Personal Access Token'),
        }

        help_texts: Mapping[str, StrOrPromise] = {
            'hosting_account_username': _(
                'Your GitHub username. This must <em>not</em> be your '
                'e-mail address!'
            ),
            'hosting_account_password': format_lazy(
                _(
                    'This must be a fine-grained access token (recommended) '
                    'or a classic access token. See the '
                    '<a href="{docs_url}" target="_blank">documentation</a> '
                    'for details on the trade-offs and how to choose the '
                    'right token for your needs.'
                ),
                docs_url=(
                    get_manual_url() +
                    'admin/configuration/repositories/github/'
                ),
            ),
        }


class GitHubPublicForm(BaseHostingServiceRepositoryForm):
    """Sub-form for public repositories owned by a user."""

    github_public_repo_name = forms.CharField(
        label=_('Repository name'),
        max_length=64,
        required=True,
        widget=forms.TextInput(attrs={'size': '60'}),
        help_text=_('The name of the repository. This is the '
                    '<code>&lt;repo_name&gt;</code> in '
                    '<code>http://github.com/&lt;username&gt;/'
                    '&lt;repo_name&gt;/</code>'))


class GitHubPrivateForm(BaseHostingServiceRepositoryForm):
    """Sub-form for private repositories owned by a user."""

    github_private_repo_name = forms.CharField(
        label=_('Repository name'),
        max_length=64,
        required=True,
        widget=forms.TextInput(attrs={'size': '60'}),
        help_text=_('The name of the repository. This is the '
                    '<code>&lt;repo_name&gt;</code> in '
                    '<code>http://github.com/&lt;username&gt;/'
                    '&lt;repo_name&gt;/</code>'))


class GitHubPublicOrgForm(BaseHostingServiceRepositoryForm):
    """Sub-form for public repositories owned by an organization."""

    github_public_org_name = forms.CharField(
        label=_('Organization name'),
        max_length=64,
        required=True,
        widget=forms.TextInput(attrs={'size': '60'}),
        help_text=_('The name of the organization. This is the '
                    '<code>&lt;org_name&gt;</code> in '
                    '<code>http://github.com/&lt;org_name&gt;/'
                    '&lt;repo_name&gt;/</code>'))

    github_public_org_repo_name = forms.CharField(
        label=_('Repository name'),
        max_length=64,
        required=True,
        widget=forms.TextInput(attrs={'size': '60'}),
        help_text=_('The name of the repository. This is the '
                    '<code>&lt;repo_name&gt;</code> in '
                    '<code>http://github.com/&lt;org_name&gt;/'
                    '&lt;repo_name&gt;/</code>'))


class GitHubPrivateOrgForm(BaseHostingServiceRepositoryForm):
    """Sub-form for private repositories owned by an organization."""

    github_private_org_name = forms.CharField(
        label=_('Organization name'),
        max_length=64,
        required=True,
        widget=forms.TextInput(attrs={'size': '60'}),
        help_text=_('The name of the organization. This is the '
                    '<code>&lt;org_name&gt;</code> in '
                    '<code>http://github.com/&lt;org_name&gt;/'
                    '&lt;repo_name&gt;/</code>'))

    github_private_org_repo_name = forms.CharField(
        label=_('Repository name'),
        max_length=64,
        required=True,
        widget=forms.TextInput(attrs={'size': '60'}),
        help_text=_('The name of the repository. This is the '
                    '<code>&lt;repo_name&gt;</code> in '
                    '<code>http://github.com/&lt;org_name&gt;/'
                    '&lt;repo_name&gt;/</code>'))
