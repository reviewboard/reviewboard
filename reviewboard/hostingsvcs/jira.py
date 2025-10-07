"""Hosting service for JIRA."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from django import forms
from django.utils.translation import gettext_lazy as _
try:
    from jira.client import JIRA as JIRAClient
    from jira.exceptions import JIRAError
    has_jira = True
except ImportError:
    has_jira = False

from reviewboard.admin.validation import validate_bug_tracker_base_hosting_url
from reviewboard.hostingsvcs.base.bug_tracker import BaseBugTracker
from reviewboard.hostingsvcs.base.forms import BaseHostingServiceRepositoryForm
from reviewboard.hostingsvcs.base.hosting_service import BaseHostingService

if TYPE_CHECKING:
    from reviewboard.hostingsvcs.base.bug_tracker import BugInfo
    from reviewboard.scmtools.models import Repository


logger = logging.getLogger(__name__)


class JIRAForm(BaseHostingServiceRepositoryForm):
    jira_url = forms.CharField(
        label=_('JIRA URL'),
        max_length=64,
        required=True,
        widget=forms.TextInput(attrs={'size': '60'}),
        validators=[validate_bug_tracker_base_hosting_url])

    def clean_jira_url(self):
        return self.cleaned_data['jira_url'].rstrip('/ ')


class JIRA(BaseHostingService, BaseBugTracker):
    """Hosting service for JIRA."""

    name = 'JIRA'
    hosting_service_id = 'jira'
    form = JIRAForm
    bug_tracker_field = '%(jira_url)s/browse/%%s'
    supports_bug_trackers = True

    def __init__(self, account):
        super(JIRA, self).__init__(account)

        self.jira_client = None

    def get_bug_info_uncached(
        self,
        repository: Repository,
        bug_id: str,
    ) -> BugInfo:
        """Return the information for the specified bug.

        Args:
            repository (reviewboard.scmtools.models.Repository):
                The repository object.

            bug_id (str):
                The ID of the bug to fetch.

        Returns:
            reviewboard.hostingsvcs.base.bug_tracker.BugInfo:
            Information about the bug.
        """
        result: BugInfo = {
            'summary': '',
            'description': '',
            'status': '',
        }

        if has_jira:
            if not self.jira_client:
                try:
                    jira_url = repository.extra_data['bug_tracker-jira_url']
                    self.jira_client = JIRAClient(options={
                        'server': jira_url,
                    }, max_retries=0)
                except ValueError as e:
                    logger.warning(
                        'Unable to initialize JIRAClient for server %s: %s',
                        repository.extra_data['bug_tracker-jira_url'], e)
                    return result

            try:
                jira_issue = self.jira_client.issue(bug_id)
                result = {
                    'description': jira_issue.fields.description,
                    'summary': jira_issue.fields.summary,
                    'status': jira_issue.fields.status
                }
            except JIRAError as e:
                logger.warning('Unable to fetch JIRA data for issue %s: %s',
                               bug_id, e, exc_info=True)

        return result
