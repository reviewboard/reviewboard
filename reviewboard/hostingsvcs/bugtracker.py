"""Legacy imports for bug trackers."""

from __future__ import annotations

from housekeeping import ClassMovedMixin

from reviewboard.deprecation import RemovedInReviewBoard90Warning
from reviewboard.hostingsvcs.base import bug_tracker


class BugTracker(ClassMovedMixin,
                 bug_tracker.BaseBugTracker,
                 warning_cls=RemovedInReviewBoard90Warning):
    """An interface to a bug tracker.

    Deprecated:
        7.1:
        This has been moved to :py:class:`reviewboard.hostingsvcs.base.
        bug_tracker.BaseBugTracker`. The legacy import will be removed in
        Review Board 9.
    """
