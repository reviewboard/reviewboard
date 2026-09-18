"""Forms for GitHub.

Version Added:
    9.0:
    Split up :py:mod:`reviewboard.hostingsvcs.github`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django import forms
from django.core.exceptions import ValidationError
from django.utils.text import format_lazy
from django.utils.translation import gettext_lazy as _

from reviewboard import get_manual_url
from reviewboard.hostingsvcs.base.forms import (
    BaseHostingServiceAuthForm,
    BaseHostingServiceRepositoryForm,
)

if TYPE_CHECKING:
    from collections.abc import Mapping
    from typing import Final

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


class GitHubAppReplaceKeyForm(forms.Form):
    """Form for replacing a GitHub App's private key.

    This is used to recover from a private key that GitHub can no longer
    validate, such as after the key is regenerated and the old one revoked on
    the GitHub side.

    Version Added:
        9.0
    """

    #: The largest private key file that will be read, in bytes.
    #:
    #: A PEM-encoded RSA private key is a few kilobytes. This is generous
    #: enough for any real key, and rejects an unrelated file before its
    #: contents are read into memory.
    MAX_PRIVATE_KEY_SIZE: Final[int] = 64 * 1024

    private_key = forms.FileField(
        label=_('Private key file'),
        required=True,
        widget=forms.FileInput(attrs={'accept': '.pem'}),
        help_text=_(
            'The <code>.pem</code> file that was saved when the new private '
            'key was generated.'
        ))

    def clean_private_key(self) -> str:
        """Return the PEM contents of the uploaded private key file.

        This only checks that the file is small enough to be a private key
        and that it is text. Whether the contents are a usable RSA key is
        checked when the key is stored.

        Returns:
            str:
            The contents of the file, with surrounding whitespace stripped.

        Raises:
            django.core.exceptions.ValidationError:
                The file was too large to be a private key, or was not text.
        """
        uploaded_file = self.cleaned_data['private_key']

        if uploaded_file.size > self.MAX_PRIVATE_KEY_SIZE:
            raise ValidationError(
                _('This file is too large to be a private key. Upload the '
                  '.pem file that GitHub downloaded.'))

        try:
            return uploaded_file.read().decode('utf-8').strip()
        except UnicodeDecodeError:
            raise ValidationError(
                _('This file is not a PEM-encoded private key. Upload the '
                  '.pem file that GitHub downloaded.'))

    class Meta:
        """Metadata for the form."""

        title = _('Rotate GitHub App private key')
