from __future__ import unicode_literals

from django import forms
from django.utils.translation import ugettext_lazy as _

from reviewboard.admin.validation import validate_bug_tracker_base_hosting_url
from reviewboard.hostingsvcs.forms import HostingServiceForm
from reviewboard.hostingsvcs.service import HostingService


class VersionOneForm(HostingServiceForm):
    versionone_url = forms.CharField(
        label=_('VersionOne URL'),
        max_length=64,
        required=True,
        widget=forms.TextInput(attrs={'size': '60'}),
        validators=[validate_bug_tracker_base_hosting_url])


class VersionOne(HostingService):
    name = 'VersionOne'
    form = VersionOneForm
    bug_tracker_field = '%(versionone_url)s/assetdetail.v1?Number=%%s'
    supports_bug_trackers = True
