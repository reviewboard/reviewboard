from __future__ import unicode_literals

from django import forms
from django.utils.translation import ugettext_lazy as _

from reviewboard.hostingsvcs.forms import HostingServiceForm
from reviewboard.hostingsvcs.service import HostingService


class BugzillaForm(HostingServiceForm):
    bugzilla_url = forms.CharField(
        label=_('Bugzilla URL'),
        max_length=64,
        required=True,
        widget=forms.TextInput(attrs={'size': '60'}))

    def clean_bugzilla_url(self):
        return self.cleaned_data['bugzilla_url'].rstrip('/')


class Bugzilla(HostingService):
    name = 'Bugzilla'
    form = BugzillaForm
    bug_tracker_field = '%(bugzilla_url)s/show_bug.cgi?id=%%s'
    supports_bug_trackers = True
