import logging

from django import forms
from django.utils.translation import gettext_lazy as _

from reviewboard.hostingsvcs.bugtracker import BugTracker
from reviewboard.hostingsvcs.forms import HostingServiceForm
from reviewboard.hostingsvcs.service import HostingService
from reviewboard.admin.validation import validate_bug_tracker_base_hosting_url


class BugzillaForm(HostingServiceForm):
    bugzilla_url = forms.CharField(
        label=_('Bugzilla URL'),
        max_length=64,
        required=True,
        widget=forms.TextInput(attrs={'size': '60'}),
        validators=[validate_bug_tracker_base_hosting_url])

    def clean_bugzilla_url(self):
        return self.cleaned_data['bugzilla_url'].rstrip('/')


class Bugzilla(HostingService, BugTracker):
    name = 'Bugzilla'
    hosting_service_id = 'bugzilla'
    form = BugzillaForm
    bug_tracker_field = '%(bugzilla_url)s/show_bug.cgi?id=%%s'
    supports_bug_trackers = True

    def get_bug_info_uncached(self, repository, bug_id):
        """Get the bug info from the server."""
        # This requires making two HTTP requests: one for the summary and
        # status, and one to get the "first comment" (description).
        bug_id = str(bug_id)

        result = {
            'summary': '',
            'description': '',
            'status': '',
        }

        url = '%s/rest/bug/%s' % (
            repository.extra_data['bug_tracker-bugzilla_url'],
            bug_id)

        try:
            rsp, headers = self.client.json_get(
                '%s?include_fields=summary,status'
                % url)
            result['summary'] = rsp['bugs'][0]['summary']
            result['status'] = rsp['bugs'][0]['status']
        except Exception as e:
            logging.warning('Unable to fetch bugzilla data from %s: %s',
                            url, e, exc_info=True)

        try:
            url += '/comment'
            rsp, headers = self.client.json_get(url)
            result['description'] = rsp['bugs'][bug_id]['comments'][0]['text']
        except Exception as e:
            logging.warning('Unable to fetch bugzilla data from %s: %s',
                            url, e, exc_info=True)

        return result
