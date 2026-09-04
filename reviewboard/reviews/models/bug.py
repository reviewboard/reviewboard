"""A bug in a tracker, linkable to review requests.

Version Added:
    9.0
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import IntegrityError, models
from django.utils.translation import gettext_lazy as _
from djblets.db.fields import JSONField

from reviewboard.hostingsvcs.base.bug_tracker import BaseBugTracker
from reviewboard.hostingsvcs.errors import MissingHostingServiceError
from reviewboard.hostingsvcs.models import (
    ConfiguredBugTracker,
    SENTINEL_BUG_TRACKER_SERVICE_NAME,
)

if TYPE_CHECKING:
    from collections.abc import Iterable
    from typing import ClassVar


#: The extra_data key marking a review request's bugs as migrated.
#:
#: When set on a review request or draft, bug reads derive from the
#: ``bugs`` relation. When unset, reads use the legacy ``bugs_closed``
#: string.
#:
#: Version Added:
#:     9.0
BUGS_MIGRATED_KEY = '__bugs_migrated'


def sort_bug_ids(
    bug_ids: Iterable[str],
    *,
    tracker: (ConfiguredBugTracker | None) = None,
) -> list[str]:
    """Return bug IDs sorted for display.

    When a tracker is provided and its service defines sort keys for
    every ID (:py:meth:`BaseBugTracker.get_bug_id_sort_key
    <reviewboard.hostingsvcs.base.bug_tracker.BaseBugTracker
    .get_bug_id_sort_key>`), the IDs are ordered by those keys.

    Otherwise, this first tries a numeric sort, to show the best
    results for the majority case of bug trackers with numeric IDs. If
    that fails, it sorts alphabetically.

    Version Added:
        9.0

    Args:
        bug_ids (iterable of str):
            The bug IDs to sort.

        tracker (reviewboard.hostingsvcs.models.ConfiguredBugTracker,
                 optional):
            The bug tracker configuration the IDs belong to.

    Returns:
        list of str:
        The sorted bug IDs.
    """
    result = list(bug_ids)

    if tracker is not None:
        service = None

        if tracker.service_name != SENTINEL_BUG_TRACKER_SERVICE_NAME:
            try:
                service = tracker.service
            except MissingHostingServiceError:
                pass

        if service is not None:
            assert isinstance(service, BaseBugTracker)

            keys = {
                bug_id: service.get_bug_id_sort_key(bug_id=bug_id)
                for bug_id in result
            }

            if all(key is not None for key in keys.values()):
                result.sort(key=keys.__getitem__)

                return result

    try:
        result.sort(key=int)
    except ValueError:
        result.sort()

    return result


class BugManager(models.Manager['Bug']):
    """A manager for Bug models.

    Version Added:
        9.0
    """

    def get_or_create_bug(
        self,
        *,
        bug_tracker: ConfiguredBugTracker,
        bug_id: str,
    ) -> Bug:
        """Return the bug for a tracker and ID, creating it if needed.

        This is safe against concurrent creation. If another process
        creates the same bug first, the unique constraint is hit and the
        existing row is returned.

        Args:
            bug_tracker (reviewboard.hostingsvcs.models.ConfiguredBugTracker):
                The bug tracker the bug belongs to.

            bug_id (str):
                The ID of the bug on the tracker.

        Returns:
            reviewboard.reviews.models.bug.Bug:
            The bug row.
        """
        try:
            bug, _created = self.get_or_create(bug_tracker=bug_tracker,
                                               bug_id=bug_id)
        except IntegrityError:
            bug = self.get(bug_tracker=bug_tracker, bug_id=bug_id)

        return bug


class Bug(models.Model):
    """A bug in a tracker, linkable to review requests.

    Rows are deduplicated: there is one row per unique
    ``(bug_tracker, bug_id)`` pair. Review requests and drafts link to
    bugs through their ``bugs`` relations.

    Bugs with no known tracker point at the sentinel bug tracker (see
    :py:meth:`ConfiguredBugTrackerManager.get_sentinel()
    <reviewboard.hostingsvcs.managers.ConfiguredBugTrackerManager.get_sentinel>`).

    Version Added:
        9.0
    """

    bug_tracker = models.ForeignKey(
        ConfiguredBugTracker,
        on_delete=models.PROTECT,
        related_name='bugs')

    bug_id = models.CharField(
        max_length=255,
        db_index=True)

    # These are reserved for future metadata caching. They are nullable
    # or blank and unpopulated for now.
    summary = models.CharField(max_length=500, blank=True)
    status = models.CharField(max_length=64, blank=True)
    metadata_timestamp = models.DateTimeField(null=True, blank=True)

    extra_data = JSONField()

    objects: ClassVar[BugManager] = BugManager()

    def __str__(self) -> str:
        """Return a string representation of the bug.

        Returns:
            str:
            A string representation of the object.
        """
        return self.bug_id

    class Meta:
        """Metadata for the Bug model."""

        app_label = 'reviews'
        db_table = 'reviews_bug'
        unique_together = (('bug_tracker', 'bug_id'),)
        verbose_name = _('Bug')
        verbose_name_plural = _('Bugs')
