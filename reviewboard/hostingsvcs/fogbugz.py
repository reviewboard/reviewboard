from django import forms
from django.utils.translation import gettext_lazy as _

from reviewboard.hostingsvcs.base.forms import BaseHostingServiceRepositoryForm
from reviewboard.hostingsvcs.base.hosting_service import BaseHostingService


class FogBugzForm(BaseHostingServiceRepositoryForm):
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
    name = _('FogBugz')
    hosting_service_id = 'fogbugz'
    supports_bug_trackers = True

    form = FogBugzForm
    bug_tracker_field = \
        'https://%(fogbugz_account_domain)s.fogbugz.com/f/cases/%%s'
