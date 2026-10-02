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
    from typing import ClassVar, Final

    from typelets.django.strings import StrOrPromise

    from reviewboard.scmtools.models import Repository


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


class GitHubRepositoryForm(BaseHostingServiceRepositoryForm):
    """Base sub-form for GitHub repository plans.

    On save, this resolves the repository's owner and name from the
    plan-specific fields and stores them under canonical ``github_owner``
    and ``github_repo_name`` keys in the repository's ``extra_data``.
    Consumers read these through :py:meth:`GitHub.get_repository_ids()
    <reviewboard.hostingsvcs.github.service.GitHub.get_repository_ids>`.

    Version Added:
        9.0
    """

    #: The name of the form field holding the repository owner.
    #:
    #: ``None`` means the owner is the linked account's username.
    owner_field: ClassVar[str | None] = None

    #: The name of the form field holding the repository name.
    repo_name_field: ClassVar[str]

    def save(
        self,
        repository: (Repository | None) = None,
        **kwargs,
    ) -> None:
        """Save information from the form back to the repository.

        In addition to the plan-specific fields, this writes the resolved
        owner and repository name to the canonical ``github_owner`` and
        ``github_repo_name`` keys in the repository's ``extra_data``.

        Args:
            repository (reviewboard.scmtools.models.Repository, optional):
                The repository being saved.

            **kwargs (dict):
                Additional keyword arguments to pass to the parent method.
        """
        super().save(repository=repository, **kwargs)

        if self.prefix:
            # This instance is configuring a legacy bug tracker, not the
            # repository itself. Its fields don't describe the repository,
            # so the canonical keys must not be written.
            return

        if repository is None:
            repository = self.repository
            assert repository is not None

        owner_field = self.owner_field

        if owner_field is None:
            owner = repository.hosting_account.username
        else:
            owner = self.cleaned_data[owner_field]

        repository.extra_data.update({
            'github_owner': owner,
            'github_repo_name': self.cleaned_data[self.repo_name_field],
        })


class GitHubPublicForm(GitHubRepositoryForm):
    """Sub-form for public repositories owned by a user."""

    repo_name_field = 'github_public_repo_name'

    github_public_repo_name = forms.CharField(
        label=_('Repository name'),
        max_length=64,
        required=True,
        widget=forms.TextInput(attrs={'size': '60'}),
        help_text=_('The name of the repository. This is the '
                    '<code>&lt;repo_name&gt;</code> in '
                    '<code>http://github.com/&lt;username&gt;/'
                    '&lt;repo_name&gt;/</code>'))


class GitHubPrivateForm(GitHubRepositoryForm):
    """Sub-form for private repositories owned by a user."""

    repo_name_field = 'github_private_repo_name'

    github_private_repo_name = forms.CharField(
        label=_('Repository name'),
        max_length=64,
        required=True,
        widget=forms.TextInput(attrs={'size': '60'}),
        help_text=_('The name of the repository. This is the '
                    '<code>&lt;repo_name&gt;</code> in '
                    '<code>http://github.com/&lt;username&gt;/'
                    '&lt;repo_name&gt;/</code>'))


class GitHubPublicOrgForm(GitHubRepositoryForm):
    """Sub-form for public repositories owned by an organization."""

    owner_field = 'github_public_org_name'
    repo_name_field = 'github_public_org_repo_name'

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


class GitHubPrivateOrgForm(GitHubRepositoryForm):
    """Sub-form for private repositories owned by an organization."""

    owner_field = 'github_private_org_name'
    repo_name_field = 'github_private_org_repo_name'

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
