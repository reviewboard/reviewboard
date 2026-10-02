"""Hosting service for Trac."""

from __future__ import annotations

from django import forms
from django.utils.translation import gettext_lazy as _

from reviewboard.admin.validation import validate_bug_tracker_base_hosting_url
from reviewboard.hostingsvcs.base.forms import (
    BaseBugTrackerConfigForm,
    BaseHostingServiceRepositoryForm,
)
from reviewboard.hostingsvcs.base.hosting_service import BaseHostingService


class TracForm(BaseHostingServiceRepositoryForm):
    """The legacy repository form for Trac settings.

    This collects Trac settings stored on a repository (``bug_tracker-*`` keys
    in ``extra_data``). It exists only for compatibility with legacy
    per-repository bug tracker settings written through the repository form
    and the Web API. Standalone configurations use
    :py:class:`TracBugTrackerConfigForm`.
    """

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


class TracBugTrackerConfigForm(BaseBugTrackerConfigForm):
    """Settings form for Trac bug tracker configurations.

    Version Added:
        9.0
    """

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

    bug_tracker_config_form = TracBugTrackerConfigForm
    form = TracForm
    supports_bug_trackers = True
    _logo_image = 'rb/images/services/trac.svg'

    bug_tracker_field = '%(trac_url)s/ticket/%%s'
