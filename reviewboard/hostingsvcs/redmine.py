"""Hosting service for Redmine."""

from __future__ import annotations

from django import forms
from django.utils.translation import gettext_lazy as _

from reviewboard.admin.validation import validate_bug_tracker_base_hosting_url
from reviewboard.hostingsvcs.base.forms import BaseHostingServiceRepositoryForm
from reviewboard.hostingsvcs.base.hosting_service import BaseHostingService


class RedmineForm(BaseHostingServiceRepositoryForm):
    """Configuration form for Redmine."""

    redmine_url = forms.CharField(
        label=_('Redmine URL'),
        max_length=64,
        required=True,
        widget=forms.TextInput(attrs={'size': '60'}),
        validators=[validate_bug_tracker_base_hosting_url])


class Redmine(BaseHostingService):
    """Hosting service for Redmine."""

    hosting_service_id = 'redmine'
    name = 'Redmine'

    form = RedmineForm
    supports_bug_trackers = True
    _logo_image = 'rb/images/services/redmine.svg'

    bug_tracker_field = '%(redmine_url)s/issues/%%s'
