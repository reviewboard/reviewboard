"""Administration form for review workflow.

Version Added:
    7.1
"""

from __future__ import annotations

from django import forms
from django.utils.translation import gettext_lazy as _
from djblets.siteconfig.forms import SiteSettingsForm


class ReviewSettingsForm(SiteSettingsForm):
    """Review workflow settings for Review Board.

    Version Added:
        7.1
    """

    css_bundle_names = ['djblets-forms']
    js_bundle_names = ['djblets-forms']

    reviews_allow_self_shipit = forms.BooleanField(
        label=_('Allow users to mark "Ship It!" on their own review requests'),
        help_text=_(
            'If selected, users will be allowed to mark their own review '
            'requests as "Ship It!".'
        ),
        required=False,
    )

    class Meta:
        """Metadata for the form."""

        title = _('Review Workflow Settings')
