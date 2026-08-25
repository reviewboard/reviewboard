"""Hosting service for JIRA."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from django import forms
from django.utils.translation import gettext_lazy as _
from housekeeping import deprecate_non_keyword_only_args

from reviewboard.deprecation import RemovedInReviewBoard11_0Warning
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
    from reviewboard.hostingsvcs.models import ConfiguredBugTracker
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

    hosting_service_id = 'jira'
    name = 'JIRA'

    bug_tracker_label = _('JIRA Issues')
    form = JIRAForm
    supports_bug_info = True
    supports_bug_trackers = True
    _logo_image = 'rb/images/services/jira.svg'

    bug_tracker_field = '%(jira_url)s/browse/%%s'

    def __init__(self, account):
        super(JIRA, self).__init__(account)

        self.jira_client = None

    @deprecate_non_keyword_only_args(RemovedInReviewBoard11_0Warning)
    def get_bug_info_uncached(
        self,
        *,
        repository: (Repository | None) = None,
        bug_id: str,
        config: (ConfiguredBugTracker | None) = None,
    ) -> BugInfo:
        """Return the information for the specified bug.

        Version Changed:
            9.0:
            Added the new ``config`` argument and made arguments keyword-only.

        Args:
            repository (reviewboard.scmtools.models.Repository, optional):
                The repository object, for legacy repository-based calls.

            bug_id (str):
                The ID of the bug to fetch.

            config (reviewboard.hostingsvcs.models.ConfiguredBugTracker,
                    optional):
                The bug tracker configuration.

                Version Added:
                    9.0

        Returns:
            reviewboard.hostingsvcs.base.bug_tracker.BugInfo:
            Information about the bug.
        """
        result: BugInfo = {
            'summary': '',
            'description': '',
            'status': '',
        }

        if config is not None:
            jira_url = config.settings.get('jira_url')
        elif repository is not None:
            jira_url = repository.extra_data.get('bug_tracker-jira_url')
        else:
            jira_url = None

        if not jira_url:
            return result

        if has_jira:
            if not self.jira_client:
                try:
                    self.jira_client = JIRAClient(options={
                        'server': jira_url,
                    }, max_retries=0)
                except ValueError as e:
                    logger.warning(
                        'Unable to initialize JIRAClient for server %s: %s',
                        jira_url, e)
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
