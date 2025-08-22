from django import forms
from django.utils.translation import gettext_lazy as _

from reviewboard.admin.validation import validate_bug_tracker_base_hosting_url
from reviewboard.hostingsvcs.base.forms import BaseHostingServiceRepositoryForm
from reviewboard.hostingsvcs.base.hosting_service import BaseHostingService


class VersionOneForm(BaseHostingServiceRepositoryForm):
    versionone_url = forms.CharField(
        label=_('VersionOne URL'),
        max_length=64,
        required=True,
        widget=forms.TextInput(attrs={'size': '60'}),
        validators=[validate_bug_tracker_base_hosting_url])


class VersionOne(BaseHostingService):
    name = 'VersionOne'
    hosting_service_id = 'versionone'
    form = VersionOneForm
    bug_tracker_field = '%(versionone_url)s/assetdetail.v1?Number=%%s'
    supports_bug_trackers = True
