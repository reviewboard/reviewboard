"""Hosting service for Bugzilla."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from django import forms
from django.utils.translation import gettext_lazy as _
from housekeeping import deprecate_non_keyword_only_args

from reviewboard.deprecation import RemovedInReviewBoard11_0Warning
from reviewboard.hostingsvcs.base.bug_tracker import BaseBugTracker
from reviewboard.hostingsvcs.base.forms import BaseHostingServiceRepositoryForm
from reviewboard.hostingsvcs.base.hosting_service import BaseHostingService
from reviewboard.admin.validation import validate_bug_tracker_base_hosting_url

if TYPE_CHECKING:
    from reviewboard.hostingsvcs.base.bug_tracker import BugInfo
    from reviewboard.hostingsvcs.models import ConfiguredBugTracker
    from reviewboard.scmtools.models import Repository


logger = logging.getLogger(__name__)


class BugzillaForm(BaseHostingServiceRepositoryForm):
    """Form for Bugzilla."""

    bugzilla_url = forms.CharField(
        label=_('Bugzilla URL'),
        max_length=64,
        required=True,
        widget=forms.TextInput(attrs={'size': '60'}),
        validators=[validate_bug_tracker_base_hosting_url])

    def clean_bugzilla_url(self) -> str:
        """Clean the bugzilla URL field.

        Returns:
            str:
            The cleaned data.
        """
        return self.cleaned_data['bugzilla_url'].rstrip('/')


class Bugzilla(BaseHostingService, BaseBugTracker):
    """Hosting service for Bugzilla."""

    hosting_service_id = 'bugzilla'
    name = 'Bugzilla'

    bug_tracker_label = _('Bugzilla Bugs')
    form = BugzillaForm
    supports_bug_info = True
    supports_bug_trackers = True
    _logo_image = 'rb/images/services/bugzilla.svg'

    bug_tracker_field = '%(bugzilla_url)s/show_bug.cgi?id=%%s'

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
        # This requires making two HTTP requests: one for the summary and
        # status, and one to get the "first comment" (description).
        bug_id = str(bug_id)

        result: BugInfo = {
            'summary': '',
            'description': '',
            'status': '',
        }

        if config is not None:
            bugzilla_url = config.settings.get('bugzilla_url')
        elif repository is not None:
            bugzilla_url = repository.extra_data.get(
                'bug_tracker-bugzilla_url')
        else:
            bugzilla_url = None

        if not bugzilla_url:
            return result

        url = f'{bugzilla_url}/rest/bug/{bug_id}'

        try:
            rsp = self.client.http_get(
                f'{url}?include_fields=summary,status')
            data = rsp.json

            result['summary'] = data['bugs'][0]['summary']
            result['status'] = data['bugs'][0]['status']
        except Exception as e:
            logger.warning('Unable to fetch bugzilla data from %s: %s',
                           url, e, exc_info=True)

        try:
            rsp = self.client.http_get(f'{url}/comment')

            data = rsp.json
            result['description'] = data['bugs'][bug_id]['comments'][0]['text']
        except Exception as e:
            logger.warning('Unable to fetch bugzilla data from %s: %s',
                           url, e, exc_info=True)

        return result
