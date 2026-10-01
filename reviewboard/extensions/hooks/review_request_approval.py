"""A hook for determining if a review request is approved."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from djblets.extensions.hooks import ExtensionHook, ExtensionHookPoint

if TYPE_CHECKING:
    from reviewboard.reviews.approval import ReviewRequestApproval
    from reviewboard.reviews.models import ReviewRequest


logger = logging.getLogger(__name__)


class ReviewRequestApprovalHook(ExtensionHook, metaclass=ExtensionHookPoint):
    """A hook for determining if a review request is approved.

    Extensions can use this to hook into the process for determining
    review request approval, which may impact any scripts integrating
    with Review Board to, for example, allow committing to a repository.

    .. seealso::

       * :ref:`ReviewRequestApprovalHook Developer Guide
         <review-request-approval-hook>`
    """

    def get_approval(
        self,
        *,
        review_request: ReviewRequest,
        prev_approval: ReviewRequestApproval,
    ) -> ReviewRequestApproval:
        """Return an approval decision for a review request.

        Subclasses can augment or replace the previous approval decision.
        Following hooks may override this decision.

        Either ``prev_approval`` or a brand-new dictionary must be returned.
        This dictionary is owned by the caller and may be changed, so don't
        reuse dictionaries.

        The default implementation supports legacy :py:meth:`is_approved`
        implementations. New subclasses should override this method.

        Version Added:
            9.0

        Args:
            review_request (reviewboard.reviews.models.ReviewRequest):
                The review request being checked for approval.

            prev_approval (reviewboard.reviews.approval.ReviewRequestApproval):
                The approval decision from Review Board or a previous hook.

        Returns:
            reviewboard.reviews.approval.ReviewRequestApproval:
            The approval decision.

        Raises:
            NotImplementedError:
                Neither approval method is implemented.
        """
        approval: ReviewRequestApproval

        try:
            result = self.is_approved(
                review_request,
                prev_approval['approved'],
                prev_approval.get('reason'),
            )

            if isinstance(result, tuple):
                approved, failure = result
            elif isinstance(result, bool):
                approved = result
                failure = prev_approval.get('reason')
            else:
                raise ValueError(
                    f'{self!r} returned an invalid value {result!r} '
                    f'from is_approved'
                )

            if approved:
                failure = None

            approval = {
                'approved': approved,
                'reason': failure,
            }
        except NotImplementedError:
            # Neither method was implemented, so just raise a straight
            # NotImplementedError. We want to flag this function as not
            # implemented, not the legacy one, so we're not re-raising.
            raise NotImplementedError
        except Exception as e:
            logger.exception(
                'Error when running ReviewRequestApprovalHook.'
                'is_approved function in extension "%s": %s',
                self.extension.id, e,
            )
            approval = prev_approval

        return approval

    def is_approved(
        self,
        review_request: ReviewRequest,
        prev_approved: bool,
        prev_failure: str | None,
    ) -> bool | tuple[bool, str | None]:
        """Determine if the review request is approved.

        This function is provided with the review request and the previously
        calculated approved state (either from a prior hook, or from the
        base state of ``ship_it_count > 0 and issue_open_count == 0``).

        If approved, this should return True. If unapproved, it should
        return a tuple with False and a string briefly explaining why it's
        not approved. This may be displayed to the user.

        It generally should also take the previous approved state into
        consideration in this choice (such as returning False if the previous
        state is False). This is, however, fully up to the hook.

        The approval decision may be overridden by any following hooks.

        Version Changed:
            9.0:
            This is soft-deprecated. Implementations can still use it, but
            it may be deprecated and scheduled for removal in an upcoming
            release.

        Args:
            review_request (reviewboard.reviews.models.review_request.
                            ReviewRequest):
                The review request being checked for approval.

            prev_approved (bool):
                The previously-calculated approval result, either from another
                hook or by Review Board.

            prev_failure (str):
                The previously-calculated approval failure message, either
                from another hook or by Review Board.

        Returns:
            bool or tuple:
            Either a boolean indicating approval (re-using ``prev_failure``,
            if not approved), or a tuple in the form of
            ``(approved, failure_message)``.
        """
        raise NotImplementedError
