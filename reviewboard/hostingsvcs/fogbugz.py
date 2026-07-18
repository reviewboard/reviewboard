from __future__ import annotations

from django import forms
from django.utils.translation import gettext_lazy as _

from reviewboard.hostingsvcs.base.forms import (
    BaseBugTrackerConfigForm,
    BaseHostingServiceRepositoryForm,
)
from reviewboard.hostingsvcs.base.hosting_service import BaseHostingService


class FogBugzForm(BaseHostingServiceRepositoryForm):
    """The legacy repository form for FogBugz settings.

    This collects FogBugz settings stored on a repository (``bug_tracker-*``
    keys in ``extra_data``). It exists only for compatibility with legacy
    per-repository bug tracker settings written through the repository form
    and the Web API.
    """

    fogbugz_account_domain = forms.CharField(
        label=_('Account domain'),
        max_length=64,
        required=True,
        help_text=_('The domain used for your FogBugz site, as in '
                    'https://&lt;domain&gt;.fogbugz.com/'),
        widget=forms.TextInput(attrs={'size': '60'}))


class FogBugzBugTrackerConfigForm(BaseBugTrackerConfigForm):
    """Settings form for FogBugz bug tracker configurations.

    Version Added:
        9.0
    """

    fogbugz_account_domain = forms.CharField(
        label=_('Account domain'),
        max_length=64,
        required=True,
        help_text=_('The domain used for your FogBugz site, as in '
                    'https://&lt;domain&gt;.fogbugz.com/'),
        widget=forms.TextInput(attrs={'size': '60'}))


class FogBugz(BaseHostingService):
    """Bug tracker support for FogBugz.

    FogBugz is a bug tracker service provided by Fog Creek. This integration
    supports linking bug numbers to reports on a FogBugz account.
    """

    hosting_service_id = 'fogbugz'
    name = _('FogBugz')

    bug_tracker_config_form = FogBugzBugTrackerConfigForm
    form = FogBugzForm
    supports_bug_trackers = True

    bug_tracker_field = \
        'https://%(fogbugz_account_domain)s.fogbugz.com/f/cases/%%s'
