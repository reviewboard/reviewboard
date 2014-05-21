from __future__ import unicode_literals

from django import forms
from django.utils.translation import ugettext_lazy as _

from reviewboard.hostingsvcs.forms import HostingServiceForm
from reviewboard.hostingsvcs.service import HostingService
from reviewboard.admin.validation import validate_bug_tracker_base_hosting_url


class TracForm(HostingServiceForm):
    trac_url = forms.CharField(
        label=_('Trac URL'),
        max_length=64,
        required=True,
        widget=forms.TextInput(attrs={'size': '60'}),
        validators=[validate_bug_tracker_base_hosting_url])

    def clean_trac_url(self):
        return self.cleaned_data['trac_url'].rstrip('/')


class Trac(HostingService):
    name = 'Trac'
    form = TracForm
    bug_tracker_field = '%(trac_url)s/ticket/%%s'
    supports_bug_trackers = True
