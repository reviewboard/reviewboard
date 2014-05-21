from __future__ import unicode_literals

from django import forms
from django.utils.translation import ugettext_lazy as _

from reviewboard.hostingsvcs.forms import HostingServiceForm
from reviewboard.hostingsvcs.service import HostingService
from reviewboard.admin.validation import validate_bug_tracker_base_hosting_url


class RedmineForm(HostingServiceForm):
    redmine_url = forms.CharField(
        label=_('Redmine URL'),
        max_length=64,
        required=True,
        widget=forms.TextInput(attrs={'size': '60'}),
        validators=[validate_bug_tracker_base_hosting_url])


class Redmine(HostingService):
    name = 'Redmine'
    form = RedmineForm
    bug_tracker_field = '%(redmine_url)s/issues/%%s'
    supports_bug_trackers = True
