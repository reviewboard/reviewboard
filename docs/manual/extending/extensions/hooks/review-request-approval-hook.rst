.. _review-request-approval-hook:

=========================
ReviewRequestApprovalHook
=========================

In Review Board 2.0, review requests have a concept of "approval." This is a
flag exposed in the API on :ref:`webapi2.0-review-request-resource` that
indicates if the change on the review request has met the necessary
requirements to be committed to the codebase. Pre-commit hooks on the
repository can use this to allow or prevent check-ins.

.. note::

   Note that this is purely for integration with extensions and consumers of
   the API. Review Board does not use approval to enforce any actions itself.)

By default, the flag is set if there's at least one Ship It! and no open
issues, but custom logic can be provided by an extension.

:py:class:`reviewboard.extensions.hooks.ReviewRequestApprovalHook` allows
an extension to make a decision on whether a review request is approved.

To use it, simply subclass and provide a custom :py:meth:`is_approved`
function. This takes the review request, the previously calculated approved
state, and the previously calculated approval failure string. (Both the
previously calculated values may come from another
:py:class:`ReviewRequestApprovalHook` or the initial approval checks.)

Based on that information and its calculations, it can return the new
approval state and optional failure reason, which will be reflected in the
API.

Most often, a hook will want to return ``False`` if the previous approved
value is ``False``, and pass along the previous failure reason as well.


Example
=======

.. code-block:: python

    from reviewboard.extensions.base import Extension
    from reviewboard.extensions.hooks import ReviewRequestApprovalHook


    class SampleApprovalHook(ReviewRequestApprovalHook):
        def is_approved(self, review_request, prev_approved, prev_failure):
            # Require at least 2 Ship It!'s from everyone but Bob. Bob needs
            # at least 3.
            if not prev_approved:
                return prev_approved, prev_failure
            elif (review_request.submitter.username == 'bob' and
                  review_request.shipit_count < 3):
                return False, 'Bob, you need at least 3 "Ship It!\'s."'
            elif review_request.shipit_count < 2:
                return False, 'You need at least 2 "Ship It!\'s."'
            else:
                return True


    class SampleExtension(Extension):
        def initialize(self):
            SampleApprovalHook(self)
