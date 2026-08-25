"""A bug tracker service for custom bug URL templates.

Version Added:
    9.0
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django import forms
from django.utils.translation import gettext_lazy as _

from reviewboard.hostingsvcs.base.bug_tracker import BaseBugTracker
from reviewboard.hostingsvcs.base.forms import BaseBugTrackerConfigForm
from reviewboard.hostingsvcs.base.hosting_service import BaseHostingService

if TYPE_CHECKING:
    from reviewboard.hostingsvcs.models import ConfiguredBugTracker


class CustomBugTrackerForm(BaseBugTrackerConfigForm):
    """The custom bug tracker configuration form.

    Version Added:
        9.0
    """

    url_template = forms.CharField(
        label=_('Bug URL template'),
        max_length=256,
        required=True,
        widget=forms.TextInput(attrs={'size': 60}),
        help_text=_("The full path to a bug in the bug tracker, using "
                    "'%s' in place of the bug ID."))


class CustomBugTracker(BaseHostingService, BaseBugTracker):
    """A bug tracker using a custom URL template.

    This covers bug trackers with no dedicated service integration. The
    configuration stores a URL template in ``settings['url_template']``,
    with ``%s`` in place of the bug ID. It replaces the bare
    ``Repository.bug_tracker`` URL template.

    Version Added:
        9.0
    """

    name = 'Custom Bug Tracker'
    hosting_service_id = 'custom-bug-tracker'
    bug_tracker_config_form = CustomBugTrackerForm

    supports_bug_trackers = True
    supports_repositories = False
    needs_authorization = False

    bug_tracker_label = _('Bugs')

    def get_bug_url(
        self,
        *,
        config: ConfiguredBugTracker,
        bug_id: str,
    ) -> str | None:
        """Return the public URL for a bug.

        Args:
            config (reviewboard.hostingsvcs.models.ConfiguredBugTracker):
                The bug tracker configuration.

            bug_id (str):
                The ID of the bug.

        Returns:
            str:
            The URL for the bug, or ``None`` if the template has no
            ``%s`` placeholder.
        """
        url_template = (config.settings or {}).get('url_template', '')

        if url_template and '%s' in url_template:
            return url_template % bug_id

        return None
