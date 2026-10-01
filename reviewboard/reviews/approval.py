"""Approval information for review requests.

Version Added:
    9.0
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from typing_extensions import NotRequired

    from reviewboard.reviews.models import ReviewRequest


logger = logging.getLogger(__name__)


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


def get_default_review_request_approval(
    review_request: ReviewRequest,
    *,
    run_hooks: bool = True,
) -> ReviewRequestApproval:
    """Return the approval state for a review request using the default logic.

    This can be used to calculate the default approval for a given review
    request based on the Ship It! counts and issue counts and any hooks
    that may be registered.

    Initially, the approval state will show approved if there's at least one
    Ship It! and no open or unverified issues, and not approved otherwise
    (with a suitable reason set).

    That approval state will then be run through approval hooks for further
    processing, unless ``run_hooks=False`` is passed. This can augment or
    replace the initial state, giving hooks full control over policy. Hooks
    are run in order, with each hook determining its result based on or
    independent of the calculated state provided to it. The final hook's
    result will be used as the final approval state returned by this
    function.

    Callers should directly call :py:meth:`ReviewRequest.get_approval()
    <reviewboard.reviews.models.ReviewRequest.get_approval>` instead of
    this function to get the approval state for a given review request.
    This function should only be called directly by functions that provide
    an approval result to the review request (such as flow phases).

    Version Added:
        9.0

    Args:
        review_request (reviewboard.reviews.models.ReviewRequest):
            The review request to calculate approval for.

        run_hooks (bool, optional):
            Whether to run approval hooks on the default.

            Hooks are enabled by default.

    Returns:
        ReviewRequestApproval:
        The resulting approval state.
    """
    approval: ReviewRequestApproval

    # Perform some default checks to set an initial approval state.
    # These can be augmented or replaced by hooks.
    if review_request.shipit_count == 0:
        approval = {
            'approved': False,
            'reason': (
                'The review request has not been marked "Ship It!"'
            ),
        }
    elif review_request.issue_open_count > 0:
        approval = {
            'approved': False,
            'reason': 'The review request has open issues.',
        }
    elif review_request.issue_verifying_count > 0:
        approval = {
            'approved': False,
            'reason': 'The review request has unverified issues.',
        }
    else:
        approval = {
            'approved': True,
            'reason': None,
        }

    if run_hooks:
        approval = run_approval_hooks(
            default_approval=approval,
            review_request=review_request,
        )

    return approval


def run_approval_hooks(
    *,
    default_approval: ReviewRequestApproval,
    review_request: ReviewRequest,
) -> ReviewRequestApproval:
    """Run all approval hooks on an approval state.

    This takes an approval state that would be returned and runs it through
    all registered approval hooks, allowing that state to be modified or
    replaced.

    Version Added:
        9.0

    Args:
        default_approval (ReviewRequestApproval):
            The review request approval state to return by default.

        review_request (reviewboard.reviews.models.ReviewRequest):
            The review request the approval state applies to.

    Returns:
        ReviewRequestApproval:
        The resulting approval state after being processed by hooks.

        This will be the default state if no hooks are registered.
    """
    from reviewboard.extensions.hooks import ReviewRequestApprovalHook

    approval = default_approval

    for hook in ReviewRequestApprovalHook.hooks:
        try:
            new_approval = hook.get_approval(
                prev_approval=approval,
                review_request=review_request,
            )

            # If the approval state didn't change but the new
            # approval reason wasn't set, inherit from the previous
            # approval.
            if ('reason' not in new_approval and
                approval['approved'] == new_approval['approved']):
                # Inherit the reason, if it's set.
                new_approval['reason'] = approval.get('reason')

            approval = new_approval
        except NotImplementedError:
            # The hook didn't implement approval checks.
            pass
        except Exception as e:
            logger.exception(
                'Error when running ReviewRequestApprovalHook.'
                'get_approval function in extension "%s": %s',
                hook.extension.id, e,
            )

    return approval
