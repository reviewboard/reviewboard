"""A bug in a tracker, linkable to review requests.

Version Added:
    9.0
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import IntegrityError, models
from django.utils.translation import gettext_lazy as _
from djblets.db.fields import JSONField

from reviewboard.hostingsvcs.models import ConfiguredBugTracker

if TYPE_CHECKING:
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
