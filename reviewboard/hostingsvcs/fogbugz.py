from __future__ import unicode_literals

from django import forms
from django.utils.translation import ugettext_lazy as _

from reviewboard.hostingsvcs.forms import HostingServiceForm
from reviewboard.hostingsvcs.service import HostingService


class FogBugzForm(HostingServiceForm):
    fogbugz_account_domain = forms.CharField(
        label=_('Account domain'),
        max_length=64,
        required=True,
        help_text=_('The domain used for your FogBugz site, as in '
                    'https://&lt;domain&gt;.fogbugz.com/'),
        widget=forms.TextInput(attrs={'size': '60'}))


class FogBugz(HostingService):
    """Bug tracker support for FogBugz.

    FogBugz is a bug tracker service provided by Fog Creek. This integration
    supports linking bug numbers to reports on a FogBugz account.
    """
    name = _('FogBugz')
    supports_bug_trackers = True

    form = FogBugzForm
    bug_tracker_field = \
        'https://%(fogbugz_account_domain)s.fogbugz.com/f/cases/%%s'
