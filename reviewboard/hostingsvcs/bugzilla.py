"""Hosting service for Bugzilla."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from django import forms
from django.utils.translation import gettext_lazy as _

from reviewboard.hostingsvcs.base.bug_tracker import BaseBugTracker
from reviewboard.hostingsvcs.base.forms import BaseHostingServiceRepositoryForm
from reviewboard.hostingsvcs.base.hosting_service import BaseHostingService
from reviewboard.admin.validation import validate_bug_tracker_base_hosting_url

if TYPE_CHECKING:
    from reviewboard.hostingsvcs.base.bug_tracker import BugInfo
    from reviewboard.scmtools.models import Repository


logger = logging.getLogger(__name__)


class BugzillaForm(BaseHostingServiceRepositoryForm):
    bugzilla_url = forms.CharField(
        label=_('Bugzilla URL'),
        max_length=64,
        required=True,
        widget=forms.TextInput(attrs={'size': '60'}),
        validators=[validate_bug_tracker_base_hosting_url])

    def clean_bugzilla_url(self):
        return self.cleaned_data['bugzilla_url'].rstrip('/')


class Bugzilla(BaseHostingService, BaseBugTracker):
    """Hosting service for Bugzilla."""

    name = 'Bugzilla'
    hosting_service_id = 'bugzilla'
    form = BugzillaForm
    bug_tracker_field = '%(bugzilla_url)s/show_bug.cgi?id=%%s'
    supports_bug_trackers = True

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
        # This requires making two HTTP requests: one for the summary and
        # status, and one to get the "first comment" (description).
        bug_id = str(bug_id)

        result: BugInfo = {
            'summary': '',
            'description': '',
            'status': '',
        }

        bugzilla_url = repository.extra_data['bug_tracker-bugzilla_url']
        url = f'{bugzilla_url}/rest/bug/{bug_id}'

        try:
            rsp = self.client.json_get(
                f'{url}?include_fields=summary,status')[0]
            result['summary'] = rsp['bugs'][0]['summary']
            result['status'] = rsp['bugs'][0]['status']
        except Exception as e:
            logger.warning('Unable to fetch bugzilla data from %s: %s',
                           url, e, exc_info=True)

        try:
            url += '/comment'
            rsp = self.client.json_get(url)[0]
            result['description'] = rsp['bugs'][bug_id]['comments'][0]['text']
        except Exception as e:
            logger.warning('Unable to fetch bugzilla data from %s: %s',
                           url, e, exc_info=True)

        return result
