"""Hosting service for Redmine."""

from __future__ import annotations

from django import forms
from django.utils.translation import gettext_lazy as _

from reviewboard.admin.validation import validate_bug_tracker_base_hosting_url
from reviewboard.hostingsvcs.base.forms import (
    BaseBugTrackerConfigForm,
    BaseHostingServiceRepositoryForm,
)
from reviewboard.hostingsvcs.base.hosting_service import BaseHostingService


class RedmineForm(BaseHostingServiceRepositoryForm):
    """The legacy repository form for Redmine settings.

    This collects Redmine settings stored on a repository (``bug_tracker-*``
    keys in ``extra_data``). It exists only for compatibility with legacy
    per-repository bug tracker settings written through the repository form
    and the Web API. Standalone configurations use
    :py:class:`RedmineBugTrackerConfigForm`.
    """

    redmine_url = forms.CharField(
        label=_('Redmine URL'),
        max_length=64,
        required=True,
        widget=forms.TextInput(attrs={'size': '60'}),
        validators=[validate_bug_tracker_base_hosting_url])


class RedmineBugTrackerConfigForm(BaseBugTrackerConfigForm):
    """Settings form for Redmine bug tracker configurations.

    Version Added:
        9.0
    """

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

    bug_tracker_config_form = RedmineBugTrackerConfigForm
    form = RedmineForm
    supports_bug_trackers = True
    _logo_image = 'rb/images/services/redmine.svg'

    bug_tracker_field = '%(redmine_url)s/issues/%%s'
