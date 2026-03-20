.. _review-request-approval-hook:

=========================
ReviewRequestApprovalHook
=========================

Review Board exposes an *approval* state for review requests through the
API. This state indicates whether a change has met whatever criteria an
organization requires before it can be committed or merged.

Review Board itself **does not enforce** approval. Approval states are
instead made available to tooling such as:

* Pre-commit, pre-push, or pre-receive hooks (for example, `RBTools's
  repository hooks`_).

* CI or merge gate systems

* :ref:`Extensions <extensions-overview>`, bots,
  :ref:`integrations <integrations>`, or in-house tools

The results of approval are available in two places:

1. The :ref:`review request API <webapi2.0-review-request-resource>` (as
   ``approved`` and ``approval_failure`` fields).

2. The :py:class:`~reviewboard.reviews.models.ReviewRequest` model accessible
   by extensions (as :py:attr:`~reviewboard.reviews.models.ReviewRequest.
   approved` and :py:attr:`~reviewboard.reviews.models.ReviewRequest.
   approval_failure` properties).

By default, a review request is considered approved if it has at least one
:ref:`Ship It! <ship-it>` and no :ref:`open issues <issue-tracking>`.
Extensions can override or extend this logic using
:py:class:`~reviewboard.extensions.hooks.ReviewRequestApprovalHook`.


.. _RBTools's repository hooks:
   https://github.com/reviewboard/rbtools/tree/master/contrib/tools


Overview
========

:py:class:`~reviewboard.extensions.hooks.ReviewRequestApprovalHook`
participates in a *chain* of approval checks. Each hook:

* Receives the review request
* Receives the previously-computed approval state
* Receives the previous failure reason (if any)
* Returns a new approval state and optional failure reason

Multiple approval hooks may be registered. Hooks are evaluated in
registration order.


Execution Model
===============

Each approval hook must implement an ``is_approved`` method with the
following signature. This method will be part of a chain of calls used to
determine approval.

.. code-block:: python

   def is_approved(
       self,
       review_request: ReviewRequest,
       prev_approved: bool,
       prev_failure: str | None,
   ) -> bool | tuple[bool, str | None]:
       ...

It's called with the following arguments:

* ``review_request``: The review request being evaluated
* ``prev_approved``: The approval result computed so far
* ``prev_failure``: The failure message associated with the most recent
  ``prev_approved=False`` result

A hook may do any of the following:

* Preserve the existing approval state
* Add additional requirements for approval
* Override previous results (though this must be done with great care)

The result may be one of the following:

1. A boolean result (``True`` to approve, ``False`` to reject while
   preserving any existing failure reason, if present).

2. A tuple in the form of ``(approved, failure_reason)``.

   This form is preferred over simply returning ``False``.

.. important::

   If a hook returns ``False``, later hooks will still be called. The value
   returned by each hook becomes the input to the next hook.

   Hooks must explicitly preserve failure state if that is the desired
   behavior.

   Most hooks should treat ``prev_approved=False`` as a hard stop. This allows
   multiple hooks to cooperatively build approval policy, but also means hooks
   must be written to coexist with others.


Failure Messages
================

Failure messages are exposed through the API and may be surfaced by
external tools or extensions.

* Only one failure message is retained at a time.
* Hooks should always propagate ``prev_failure`` when preserving failures.
* Messages should be short, actionable, and user-facing.


Best Practices
==============

* Treat ``prev_approved=False`` as authoritative unless you have a strong
  reason not to.

* Keep approval logic fast and side-effect-free.

* Do not assume your hook is the only one installed.


Example
=======

.. code-block:: python

    from typing import TYPE_CHECKING

    from reviewboard.extensions.base import Extension
    from reviewboard.extensions.hooks import ReviewRequestApprovalHook

    if TYPE_CHECKING:
        from reviewboard.reviews.models import ReviewRequest


    class SampleApprovalHook(ReviewRequestApprovalHook):
        def is_approved(
            self,
            review_request: ReviewRequest,
            prev_approved: bool,
            prev_failure: str | None,
        ) -> bool | tuple[bool, str | None]:
            # Always preserve prior failures.
            if not prev_approved:
                return prev_approved, prev_failure

            # Require stricter approval rules for Bob. He requires at least
            # 3 Ship It!'s.
            if (review_request.submitter.username == 'bob' and
                review_request.shipit_count < 3):
                return False, 'Bob, you need at least 3 "Ship It!s."'

            # Default requirements are at least 2 Ship It!'s.
            if review_request.shipit_count < 2:
                return False, 'You need at least 2 "Ship It!s."'

            # This has met all of this hook's requirements.
            return True


    class SampleExtension(Extension):
        def initialize(self) -> None:
            SampleApprovalHook(self)


.. tip::

   The Python type hints shown above are shown here for demonstrative
   purposes only. Your own hooks can leave them out. For example:

   .. code-block:: python

      def is_approved(self, review_request, prev_approved, prev_failure):
          ...


Common Patterns
===============

Pass-through with additional checks (recommended)
-------------------------------------------------

Most hooks should preserve previous failures and only add new requirements:

.. code-block:: python

   def is_approved(
       self,
       review_request: ReviewRequest,
       prev_approved: bool,
       prev_failure: str | None,
   ) -> bool | tuple[bool, str | None]:
       # Preserve any previous failures.
       if not prev_approved:
           return prev_approved, prev_failure

       # An example new requirement.
       if not review_request.testing_done:
           return False, 'Testing must be completed.'

       # This has met all of this hook's requirements.
       return True


Override previous failures (use with caution)
---------------------------------------------

Hooks that ignore ``prev_approved`` override all prior approval logic. This
is rarely appropriate and can lead to unexpected behavior when multiple
extensions are installed.

.. code-block:: python

   def is_approved(
       self,
       review_request: ReviewRequest,
       prev_approved: bool,
       prev_failure: str | None,
   ) -> bool | tuple[bool, str | None]:
       # If the review request's author is a special user, ignore any
       # previous failures and approve this change.
       if review_request.submitter.username == 'special-user':
           return True

       # Return the result from any previous hook, if any.
       return prev_approved, prev_failure
