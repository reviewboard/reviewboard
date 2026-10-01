"""Approval information for review requests.

Version Added:
    9.0
"""

from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from typing_extensions import NotRequired


class ReviewRequestApproval(TypedDict):
    """State representing calculated approval for a review request or phase.

    Version Added:
        9.0
    """

    #: Whether the review request or phase is approved.
    approved: bool

    #: The reason the review request or phase was approved or not approved.
    #:
    #: This is intentionally not localized, in order to ensure that its
    #: results can be used in logging or error reporting.
    reason: NotRequired[str | None]
