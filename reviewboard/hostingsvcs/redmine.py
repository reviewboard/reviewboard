from django import forms
from django.utils.translation import gettext_lazy as _

from reviewboard.admin.validation import validate_bug_tracker_base_hosting_url
from reviewboard.hostingsvcs.base.forms import BaseHostingServiceRepositoryForm
from reviewboard.hostingsvcs.base.hosting_service import BaseHostingService


class RedmineForm(BaseHostingServiceRepositoryForm):
    redmine_url = forms.CharField(
        label=_('Redmine URL'),
        max_length=64,
        required=True,
        widget=forms.TextInput(attrs={'size': '60'}),
        validators=[validate_bug_tracker_base_hosting_url])


class Redmine(BaseHostingService):
    name = 'Redmine'
    hosting_service_id = 'redmine'
    form = RedmineForm
    bug_tracker_field = '%(redmine_url)s/issues/%%s'
    supports_bug_trackers = True
