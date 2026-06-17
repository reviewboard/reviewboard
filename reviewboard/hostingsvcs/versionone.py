"""Hosting service for VersionOne."""

from __future__ import annotations

from django import forms
from django.utils.translation import gettext_lazy as _

from reviewboard.admin.validation import validate_bug_tracker_base_hosting_url
from reviewboard.hostingsvcs.base.forms import BaseHostingServiceRepositoryForm
from reviewboard.hostingsvcs.base.hosting_service import BaseHostingService


class VersionOneForm(BaseHostingServiceRepositoryForm):
    """Form service for VersionOne."""

    versionone_url = forms.CharField(
        label=_('VersionOne URL'),
        max_length=64,
        required=True,
        widget=forms.TextInput(attrs={'size': '60'}),
        validators=[validate_bug_tracker_base_hosting_url])


class VersionOne(BaseHostingService):
    """Hosting service for VersionOne."""

    hosting_service_id = 'versionone'
    name = 'VersionOne'
    visible = False

    form = VersionOneForm
    supports_bug_trackers = True

    bug_tracker_field = '%(versionone_url)s/assetdetail.v1?Number=%%s'
