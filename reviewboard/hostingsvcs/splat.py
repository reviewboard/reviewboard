"""Support for Splat as a bug tracker."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from django import forms
from django.utils.translation import gettext_lazy as _

from reviewboard.hostingsvcs.base.bug_tracker import BaseBugTracker
from reviewboard.hostingsvcs.base.forms import BaseHostingServiceRepositoryForm
from reviewboard.hostingsvcs.base.hosting_service import BaseHostingService

if TYPE_CHECKING:
    from reviewboard.hostingsvcs.base.bug_tracker import BugInfo
    from reviewboard.scmtools.models import Repository


logger = logging.getLogger(__name__)


class SplatForm(BaseHostingServiceRepositoryForm):
    """The Splat bug tracker configuration form."""

    splat_org_name = forms.SlugField(
        label=_('Splat Organization Name'),
        max_length=64,
        required=True,
        widget=forms.TextInput(attrs={'size': 60}))


class Splat(BaseHostingService, BaseBugTracker):
    """The Splat bug tracker.

    Splat is a SaaS bugtracker hosted at https://hellosplat.com. It is owned
    and run by Beanbag, Inc. and is used as the official bug tracker for
    Review Board.
    """

    name = 'Splat'
    hosting_service_id = 'splat'
    form = SplatForm
    bug_tracker_field = \
        'https://hellosplat.com/s/%(splat_org_name)s/tickets/%%s/'
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
        result: BugInfo = {
            'summary': '',
            'description': '',
            'description_text_format': '',
            'status': '',
        }

        org_name = repository.extra_data['bug_tracker-splat_org_name']
        url = (
            f'https://hellosplat.com/api/orgs/{org_name}/tickets/{bug_id}/'
            f'?only-fields=status,summary,text,text_format'
        )

        try:
            rsp = self.client.http_get(url)
            data = rsp.json
            ticket = data['ticket']
        except Exception as e:
            logger.warning('Unable to fetch Splat data from %s: %s',
                           url, e, exc_info=True)
        else:
            text = ticket['text']

            # Normalize the text format. For Splat, this is going to look
            # a bit silly, but we don't want to make the assumption in code
            # that we can just pass through the text format here.
            text_format = {
                'plain': 'plain',
                'markdown': 'markdown',
                'html': 'html',
            }.get(ticket['text_format'], 'plain')

            result = {
                'description': text,
                'description_text_format': text_format,
                'status': ticket['status'],
                'summary': ticket['summary'],
            }

        return result
