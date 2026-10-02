"""A bug in a tracker, linkable to review requests.

Version Added:
    9.0
"""

from __future__ import annotations

import logging
import re
from datetime import timedelta
from typing import TYPE_CHECKING, TypedDict

from django.db import IntegrityError, models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from djblets.db.fields import JSONField

from reviewboard.hostingsvcs.base import BaseHostingService
from reviewboard.hostingsvcs.base.bug_tracker import BaseBugTracker
from reviewboard.hostingsvcs.errors import MissingHostingServiceError
from reviewboard.hostingsvcs.models import (
    ConfiguredBugTracker,
    SENTINEL_BUG_TRACKER_SERVICE_NAME,
)

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence
    from typing import ClassVar

    from reviewboard.reviews.models.base_review_request_details import \
        BaseReviewRequestDetails


logger = logging.getLogger(__name__)


#: How long cached bug metadata is considered fresh.
#:
#: Version Added:
#:     9.0
BUG_METADATA_MAX_AGE = timedelta(hours=1)


class BugMetadata(TypedDict):
    """Cached display metadata for a bug.

    Version Added:
        9.0
    """

    #: A one-line summary of the bug.
    summary: str

    #: The bug's status.
    status: str


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

    def get_cached_bug_info(
        self,
        *,
        bug_tracker: ConfiguredBugTracker,
        bug_ids: Sequence[str],
        max_age: timedelta = BUG_METADATA_MAX_AGE,
    ) -> tuple[Mapping[str, BugMetadata], Sequence[str]]:
        """Return locally-cached metadata for bugs on a tracker.

        This never contacts the bug tracker, making it safe to call while
        rendering a page.

        Version Added:
            9.0

        Args:
            bug_tracker (reviewboard.hostingsvcs.models.ConfiguredBugTracker):
                The bug tracker the bugs belong to.

            bug_ids (list of str):
                The IDs of the bugs to look up.

            max_age (datetime.timedelta, optional):
                How old cached metadata may be before it's considered
                stale.

        Returns:
            tuple:
            A 2-tuple of:

            Tuple:
                0 (dict):
                    A mapping of bug ID to :py:class:`BugMetadata`, for
                    every bug with cached metadata. Stale metadata is
                    included.

                1 (list of str):
                    The IDs of the bugs with missing or stale metadata.
        """
        bugs = self._get_bugs_by_id(bug_tracker=bug_tracker,
                                    bug_ids=bug_ids)

        return self._split_cached_bug_info(bugs=bugs,
                                           bug_ids=bug_ids,
                                           max_age=max_age)

    def fetch_bug_info(
        self,
        *,
        bug_tracker: ConfiguredBugTracker,
        bug_ids: Sequence[str],
        max_age: timedelta = BUG_METADATA_MAX_AGE,
    ) -> Mapping[str, BugMetadata]:
        """Return metadata for bugs, refreshing it when stale.

        Bugs with fresh cached metadata are served from the database.
        The rest are fetched from the bug tracker in as few requests as
        the service supports, and the results are cached.

        Only existing rows are updated. A bug with no row is fetched and
        returned, but not stored, so that callers cannot create rows for
        arbitrary bug IDs.

        Version Added:
            9.0

        Args:
            bug_tracker (reviewboard.hostingsvcs.models.ConfiguredBugTracker):
                The bug tracker the bugs belong to.

            bug_ids (list of str):
                The IDs of the bugs to look up.

            max_age (datetime.timedelta, optional):
                How old cached metadata may be before it's refreshed.

        Returns:
            dict:
            A mapping of bug ID to :py:class:`BugMetadata`, for every bug
            metadata could be provided for.
        """
        bugs = self._get_bugs_by_id(bug_tracker=bug_tracker,
                                    bug_ids=bug_ids)
        metadata, stale_bug_ids = self._split_cached_bug_info(
            bugs=bugs,
            bug_ids=bug_ids,
            max_age=max_age)

        if not stale_bug_ids:
            return metadata

        try:
            service = bug_tracker.service
            assert isinstance(service, BaseHostingService)

            if not service.supports_bug_info:
                return metadata

            fetched = service.get_bugs_info(config=bug_tracker,
                                            bug_ids=stale_bug_ids)
        except Exception as e:
            logger.exception('Error fetching bug information from bug '
                             'tracker %s: %s',
                             bug_tracker.pk, e)

            return metadata

        timestamp = timezone.now()
        updated_bugs: list[Bug] = []

        for bug_id, bug_info in fetched.items():
            summary = str(bug_info.get('summary') or '')[:500]
            status = str(bug_info.get('status') or '')[:64]

            metadata[bug_id] = {
                'status': status,
                'summary': summary,
            }

            bug = bugs.get(bug_id)

            if bug is not None:
                bug.summary = summary
                bug.status = status
                bug.metadata_timestamp = timestamp
                updated_bugs.append(bug)

        if updated_bugs:
            self.bulk_update(
                updated_bugs,
                fields=('summary', 'status', 'metadata_timestamp'))

        return metadata

    def _get_bugs_by_id(
        self,
        *,
        bug_tracker: ConfiguredBugTracker,
        bug_ids: Sequence[str],
    ) -> Mapping[str, Bug]:
        """Return the bug rows for IDs on a tracker, keyed off the ID.

        Version Added:
            9.0

        Args:
            bug_tracker (reviewboard.hostingsvcs.models.ConfiguredBugTracker):
                The bug tracker the bugs belong to.

            bug_ids (list of str):
                The IDs of the bugs to look up.

        Returns:
            dict:
            A mapping of bug ID to :py:class:`Bug`, for the bugs that
            have rows.
        """
        return {
            bug.bug_id: bug
            for bug in self.filter(bug_tracker=bug_tracker,
                                   bug_id__in=list(bug_ids))
        }

    def _split_cached_bug_info(
        self,
        *,
        bugs: Mapping[str, Bug],
        bug_ids: Sequence[str],
        max_age: timedelta,
    ) -> tuple[dict[str, BugMetadata], Sequence[str]]:
        """Return cached metadata and the IDs needing a refresh.

        Version Added:
            9.0

        Args:
            bugs (dict):
                A mapping of bug ID to :py:class:`Bug`.

            bug_ids (list of str):
                The IDs of the bugs to look up.

            max_age (datetime.timedelta):
                How old cached metadata may be before it's considered
                stale.

        Returns:
            tuple:
            A 2-tuple of the cached metadata and the stale bug IDs. See
            :py:meth:`get_cached_bug_info` for details.
        """
        metadata: dict[str, BugMetadata] = {}
        stale_bug_ids: list[str] = []
        oldest = timezone.now() - max_age

        for bug_id in bug_ids:
            bug = bugs.get(bug_id)

            if bug is None or bug.metadata_timestamp is None:
                stale_bug_ids.append(bug_id)
                continue

            metadata[bug_id] = {
                'status': bug.status,
                'summary': bug.summary,
            }

            if bug.metadata_timestamp < oldest:
                stale_bug_ids.append(bug_id)

        return metadata, stale_bug_ids

    def sync_legacy_bug_list(
        self,
        *,
        review_request_details: BaseReviewRequestDetails,
        bug_ids: Sequence[str],
    ) -> None:
        """Sync the legacy view of bugs on a review request or draft.

        The legacy ``bugs_closed`` view covers bugs attributed to the
        repository's default bug tracker plus unattributed (sentinel)
        bugs. This replaces that scope with the given bug IDs: new IDs
        are attributed to the default tracker (or the sentinel without
        one), and stale links in the scope are removed. Links to other
        trackers are never touched.

        This marks the review request or draft as migrated. The caller
        is responsible for saving ``extra_data``.

        Args:
            review_request_details (BaseReviewRequestDetails):
                The review request or draft to sync.

            bug_ids (list of str):
                The new bug IDs for the legacy view.
        """
        details = review_request_details
        repository = details.repository

        tracker = None

        if repository is not None:
            tracker = repository.get_default_bug_tracker()

        if tracker is None:
            tracker = ConfiguredBugTracker.objects.get_sentinel()

        new_ids = set(bug_ids)
        current_bugs = list(details._get_legacy_visible_bugs())
        current_ids = {
            bug.bug_id
            for bug in current_bugs
        }

        removed_bugs = [
            bug
            for bug in current_bugs
            if bug.bug_id not in new_ids
        ]

        if removed_bugs:
            details.bugs.remove(*removed_bugs)

        added_bugs = [
            self.get_or_create_bug(bug_tracker=tracker, bug_id=bug_id)
            for bug_id in sorted(new_ids - current_ids)
        ]

        if added_bugs:
            details.bugs.add(*added_bugs)

        if details.extra_data is None:
            details.extra_data = {}

        details.extra_data[BUGS_MIGRATED_KEY] = True

    def materialize_for(
        self,
        review_request_details: BaseReviewRequestDetails,
    ) -> None:
        """Materialize bug relations from the stored bugs_closed string.

        This parses the legacy string (regardless of any migration
        marker) and performs a true sync of the legacy view: links
        missing from the string are removed, not just added, so
        re-materializing after legacy edits is always correct.

        The caller is responsible for saving ``extra_data``.

        Version Added:
            9.0

        Args:
            review_request_details (BaseReviewRequestDetails):
                The review request or draft to materialize bugs for.
        """
        bugs_closed = review_request_details.bugs_closed or ''

        if bugs_closed:
            bug_ids = [
                bug_id
                for bug_id in re.split(r'[, ]+', bugs_closed)
                if bug_id
            ]
        else:
            bug_ids = []

        self.sync_legacy_bug_list(
            review_request_details=review_request_details,
            bug_ids=bug_ids)


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

    # Cached metadata from the bug tracker, populated by
    # BugManager.fetch_bug_info(). The timestamp is null until metadata
    # has been fetched at least once.
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
