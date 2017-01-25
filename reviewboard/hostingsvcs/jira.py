from __future__ import unicode_literals, absolute_import

import logging

from django import forms
from django.utils.translation import ugettext_lazy as _
try:
    from jira.client import JIRA as JIRAClient
    from jira.exceptions import JIRAError
    has_jira = True
except ImportError:
    has_jira = False

from reviewboard.admin.validation import validate_bug_tracker_base_hosting_url
from reviewboard.hostingsvcs.bugtracker import BugTracker
from reviewboard.hostingsvcs.forms import HostingServiceForm
from reviewboard.hostingsvcs.service import HostingService


class JIRAForm(HostingServiceForm):
    jira_url = forms.CharField(
        label=_('JIRA URL'),
        max_length=64,
        required=True,
        widget=forms.TextInput(attrs={'size': '60'}),
        validators=[validate_bug_tracker_base_hosting_url])

    def clean_jira_url(self):
        return self.cleaned_data['jira_url'].rstrip('/ ')


class JIRA(HostingService, BugTracker):
    name = 'JIRA'
    form = JIRAForm
    bug_tracker_field = '%(jira_url)s/browse/%%s'
    supports_bug_trackers = True

    def __init__(self, account):
        super(JIRA, self).__init__(account)

        self.jira_client = None

    def get_bug_info_uncached(self, repository, bug_id):
        """Get the bug info from the server."""
        result = {
            'summary': '',
            'description': '',
            'status': '',
        }

        if has_jira:
            if not self.jira_client:
                self.jira_client = JIRAClient(options={
                    'server': repository.extra_data['bug_tracker-jira_url'],
                })

            try:
                jira_issue = self.jira_client.issue(bug_id)
                result = {
                    'description': jira_issue.fields.description,
                    'summary': jira_issue.fields.summary,
                    'status': jira_issue.fields.status
                }
            except JIRAError as e:
                logging.warning('Unable to fetch JIRA data for issue %s: %s',
                                bug_id, e, exc_info=1)

        return result
