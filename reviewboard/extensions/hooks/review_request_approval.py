"""A hook for determining if a review request is approved."""

from __future__ import annotations

from djblets.extensions.hooks import ExtensionHook, ExtensionHookPoint


class ReviewRequestApprovalHook(ExtensionHook, metaclass=ExtensionHookPoint):
    """A hook for determining if a review request is approved.

    Extensions can use this to hook into the process for determining
    review request approval, which may impact any scripts integrating
    with Review Board to, for example, allow committing to a repository.
    """

    def is_approved(self, review_request, prev_approved, prev_failure):
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

        Args:
            review_request (reviewboard.reviews.models.review_request.
                            ReviewRequest):
                The review request being checked for approval.

            prev_approved (bool):
                The previously-calculated approval result, either from another
                hook or by Review Board.

            prev_failure (unicode):
                The previously-calculated approval failure message, either
                from another hook or by Review Board.

        Returns:
            bool or tuple:
            Either a boolean indicating approval (re-using ``prev_failure``,
            if not approved), or a tuple in the form of
            ``(approved, failure_message)``.
        """
        raise NotImplementedError
