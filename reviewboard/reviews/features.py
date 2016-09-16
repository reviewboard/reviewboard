"""Feature definitions for reviews."""

from __future__ import unicode_literals

from django.utils.translation import ugettext_lazy as _
from djblets.features import Feature


class StatusUpdatesFeature(Feature):
    """A feature for status updates.

    A status update is a way for third-party tools to provide feedback on a
    review request. In the past, this was done just as a normal review. Status
    updates allow those tools (via some integration like Review Bot) to mark
    their state (such as pending, success, failure, or error) and then
    associate that with a review.
    """

    feature_id = 'reviews.status_updates'
    name = _('Status Updates')
    summary = _('A way for external tools to do checks on a review request '
                'and report the results of those checks.')


status_updates_feature = StatusUpdatesFeature()
