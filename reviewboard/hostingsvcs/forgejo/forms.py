"""Hosting service support for Forgejo.

Version Added:
    7.1
"""

from __future__ import annotations

from django import forms
from django.utils.translation import gettext_lazy as _

from reviewboard.hostingsvcs.base.forms import BaseHostingServiceRepositoryForm


class ForgejoForm(BaseHostingServiceRepositoryForm):
    """Hosting service form for Forgejo.

    Version Added:
        7.1
    """

    repository_owner = forms.CharField(
        label=_('Repository owner'),
        max_length=128,
        required=True,
        widget=forms.TextInput(attrs={'size': '60'}),
        help_text=_('The username of the owner of the repository.'),
    )

    repository_name = forms.CharField(
        label=_('Repository name'),
        max_length=128,
        required=True,
        widget=forms.TextInput(attrs={'size': '60'}),
        help_text=_('The name of the repository.'),
    )
