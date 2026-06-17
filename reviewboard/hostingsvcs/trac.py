"""Hosting service for Trac."""

from __future__ import annotations

from django import forms
from django.utils.translation import gettext_lazy as _

from reviewboard.admin.validation import validate_bug_tracker_base_hosting_url
from reviewboard.hostingsvcs.base.forms import BaseHostingServiceRepositoryForm
from reviewboard.hostingsvcs.base.hosting_service import BaseHostingService


class TracForm(BaseHostingServiceRepositoryForm):
    """Form for Trac."""

    trac_url = forms.CharField(
        label=_('Trac URL'),
        max_length=64,
        required=True,
        widget=forms.TextInput(attrs={'size': '60'}),
        validators=[validate_bug_tracker_base_hosting_url])

    def clean_trac_url(self) -> str:
        """Clean the trac_url field.

        Returns:
            str:
            The cleaned data.
        """
        return self.cleaned_data['trac_url'].rstrip('/')


class Trac(BaseHostingService):
    """Hosting service for Trac."""

    hosting_service_id = 'trac'
    name = 'Trac'

    form = TracForm
    supports_bug_trackers = True

    bug_tracker_field = '%(trac_url)s/ticket/%%s'
