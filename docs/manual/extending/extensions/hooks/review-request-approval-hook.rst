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
   by extensions. Call :py:meth:`~reviewboard.reviews.models.ReviewRequest.
   get_approval` to get the approval information.
   :py:attr:`~reviewboard.reviews.models.ReviewRequest.approved` and
   :py:attr:`~reviewboard.reviews.models.ReviewRequest.approval_failure`
   properties are also available.

By default, a review request is considered approved if it has at least one
:ref:`Ship It! <ship-it>` and no open or unverified
:ref:`issues <issue-tracking>`. Extensions can override or extend this logic
using :py:class:`~reviewboard.extensions.hooks.ReviewRequestApprovalHook`.


.. _RBTools's repository hooks:
   https://github.com/reviewboard/rbtools/tree/master/contrib/tools


Overview
========

:py:class:`~reviewboard.extensions.hooks.ReviewRequestApprovalHook`
participates in a *chain* of approval checks. Each hook:

* Receives the review request
* Receives the previously-computed approval dictionary
* Returns a new approval dictionary, or leaves the previous result unchanged

Multiple approval hooks may be registered. Hooks are evaluated in
registration order, starting with Review Board's default approval result.


Execution Model
===============

.. versionchanged:: 9.0

   Review Board 9 introduced the newer approval method detailed here.
   Legacy approval implementations will continue to work.

Each approval hook must implement an
:py:meth:`~reviewboard.extensions.hooks.ReviewRequestApprovalHook.
get_approval` method with the following signature. This method will be part of
a chain of calls used to determine approval.

.. code-block:: python

   def get_approval(
       self,
       *,
       review_request: ReviewRequest,
       prev_approval: ReviewRequestApproval,
   ) -> ReviewRequestApproval:
       ...

It's called with the following keyword arguments:

* ``review_request``: The review request being evaluated
* ``prev_approval``: The approval dictionary computed so far

The dictionary uses the
:py:class:`~reviewboard.reviews.approval.ReviewRequestApproval` type, with
these keys:

* ``approved`` (``bool``)

  Whether the review request is approved.

* ``reason`` (``str`` or ``None``)

  An optional reason for the approval decision. When rejecting a review
  request, provide a short message explaining what's required for approval.

  Omit this key when there's no reason to provide. If the ``approved``
  value hasn't changed, the previous reason will be inherited.

A hook may return:

* ``prev_approval`` to preserve the previous result
* A new approval dictionary to replace the previous result

A new dictionary replaces the whole result. Its keys are not merged with
the previous dictionary. You must return a new dictionary when changing the
result, rather than modifying ``prev_approval`` in place.

.. important::

   All hooks will get a chance to override previous results. This means that
   if your hook does not approve, another hook still might.

   Most hooks should preserve a previous rejection by returning
   ``prev_approval`` when ``prev_approval['approved']`` is ``False``. This
   allows multiple hooks to cooperatively build approval policy.

   The resulting dictionary may be modified, so the extension hook must
   always be sure either ``prev_approval`` or a fresh dictionary is returned.


Approval Reasons
================

Reasons are exposed through the API and may be surfaced by external tools
or extensions.

* Only one reason is retained at a time.
* Return ``prev_approval`` when preserving a previous decision and its reason.
* Messages should be short, actionable, and user-facing.
* Do not localize reasons. They must be consistent for logging and error
  reporting.


Best Practices
==============

* Treat ``prev_approval['approved'] == False`` as authoritative unless you
  have a strong reason not to.

* Keep approval logic fast and side-effect-free.

* Do not assume your hook is the only one installed.


Example
=======

.. code-block:: python

    from __future__ import annotations

    from typing import TYPE_CHECKING

    from reviewboard.extensions.base import Extension
    from reviewboard.extensions.hooks import ReviewRequestApprovalHook

    if TYPE_CHECKING:
        from reviewboard.reviews.approval import ReviewRequestApproval
        from reviewboard.reviews.models import ReviewRequest


    class SampleApprovalHook(ReviewRequestApprovalHook):
        def get_approval(
            self,
            *,
            review_request: ReviewRequest,
            prev_approval: ReviewRequestApproval,
        ) -> ReviewRequestApproval:
            # Always preserve prior failures.
            if not prev_approval['approved']:
                return prev_approval

            # Require stricter approval rules for Bob. He requires at least
            # 3 Ship It!'s.
            if (review_request.submitter.username == 'bob' and
                review_request.shipit_count < 3):
                return {
                    'approved': False,
                    'reason': 'Bob, you need at least 3 "Ship It!s."',
                }

            # Everyone else needs at least 2 Ship It!'s.
            if review_request.shipit_count < 2:
                return {
                    'approved': False,
                    'reason': 'You need at least 2 "Ship It!s."',
                }

            # This has met all of this hook's requirements.
            return prev_approval


    class SampleExtension(Extension):
        def initialize(self) -> None:
            SampleApprovalHook(self)


.. tip::

   The Python type hints shown above are optional. Your own hooks can leave
   them out. For example:

   .. code-block:: python

      def get_approval(self, *, review_request, prev_approval):
          ...


Common Patterns
===============

Pass-through with additional checks (recommended)
-------------------------------------------------

Most hooks should preserve previous failures and only add new requirements:

.. code-block:: python

   def get_approval(
       self,
       *,
       review_request: ReviewRequest,
       prev_approval: ReviewRequestApproval,
   ) -> ReviewRequestApproval:
       if not prev_approval['approved']:
           return prev_approval

       if not review_request.testing_done:
           return {
               'approved': False,
               'reason': 'Testing must be completed.',
           }

       return prev_approval


Override previous failures (use with caution)
---------------------------------------------

Hooks that ignore ``prev_approval`` override all prior approval logic. This
is rarely appropriate and can lead to unexpected behavior when multiple
extensions are installed.

.. code-block:: python

   def get_approval(
       self,
       *,
       review_request: ReviewRequest,
       prev_approval: ReviewRequestApproval,
   ) -> ReviewRequestApproval:
       # Approve this author's changes regardless of previous failures.
       if review_request.submitter.username == 'special-user':
           return {
               'approved': True,
               'reason': None,
           }

       return prev_approval


Updating from Older Hooks
=========================

Before Review Board 9.0, approval hooks implemented
:py:meth:`~reviewboard.extensions.hooks.ReviewRequestApprovalHook.
is_approved` and returned a boolean or an ``(approved, failure_reason)``
tuple. This is still supported today, but you may want to move to the newer
method.

To update a hook for Review Board 9.0 and newer:

1. Change the signature from:

   .. code-block:: python

      def is_approved(self, review_request, prev_approved, prev_failure):
          ...

   to:

   .. code-block:: python

      def get_approval(
          self,
          *,
          review_request: ReviewRequest,
          prev_approval: ReviewRequestApproval,
      ) -> ReviewRequestApproval:
          ...

2. Return a :py:class:`reviewboard.reviews.approval.ReviewRequestApproval`
   dictionary instead of a boolean or tuple.

   Return ``prev_approval`` if not overriding the result (whether approved
   or not).

For example, this older hook method:

.. code-block:: python

   def is_approved(self, review_request, prev_approved, prev_failure):
       if not prev_approved:
           return prev_approved, prev_failure

       if not review_request.testing_done:
           return False, 'Testing must be completed.'

       return True

Becomes:

.. code-block:: python

   def get_approval(
       self,
       *,
       review_request: ReviewRequest,
       prev_approval: ReviewRequestApproval,
   ) -> ReviewRequestApproval:
       if not prev_approval['approved']:
           return prev_approval

       if not review_request.testing_done:
           return {
               'approved': False,
               'reason': 'Testing must be completed.',
           }

       # This would be approved, and may include an approval reason.
       return prev_approval


Old hooks will behave as they did before. Here's how legacy values will be
converted for the newer approval results:

.. list-table::
   :header-rows: 1

   * - Legacy return value
     - Modern result

   * - ``True``
     - ``{'approved': True, 'reason': None}``

   * - ``(True, 'message')``
     - ``{'approved': True, 'reason': None}``

   * - ``(True, None)``
     - ``{'approved': True, 'reason': None}``

   * - ``False``
     - ``{'approved': False, 'reason': prev_approval.get('reason')}``

   * - ``(False, 'message')``
     - ``{'approved': False, 'reason': 'message'}``

   * - ``(False, None)``
     - ``{'approved': False, 'reason': None}``

.. note::

   With legacy hooks, approval failures would get thrown out if returning
   an ``approved`` value of ``False``. Modern hooks support a ``reason``
   field for both ``True`` and ``False`` results.

   Make sure you're careful about when you set or inherit a reason.


If an extension must support Review Board versions older than 9, keep its
``is_approved()`` implementation. If both the older and newer methods are
implemented, only the newer one will be used on Review Board 9 or higher.


Useful Data and Resources
=========================

When writing approval hooks, the following attributes and resources are
commonly useful.


Review Request Attributes
-------------------------

The ``review_request`` argument provides access to the review request being
evaluated, with these useful attributes/methods:

* :py:attr:`~reviewboard.reviews.models.ReviewRequest.submitter`

  The :py:class:`~django.contrib.auth.models.User` who submitted the
  review request.

* :py:attr:`~reviewboard.reviews.models.ReviewRequest.shipit_count`

  The number of current :ref:`Ship It!s <ship-it>`.

* :py:attr:`~reviewboard.reviews.models.ReviewRequest.issue_open_count`

  The number of open :ref:`issues <issue-tracking>`.

* :py:attr:`~reviewboard.reviews.models.ReviewRequest.issue_resolved_count`

  The number of resolved issues.

* :py:attr:`~reviewboard.reviews.models.ReviewRequest.target_groups`

  The review groups targeted by this review request (a queryset of
  :py:class:`~reviewboard.reviews.models.Group`).

* :py:attr:`~reviewboard.reviews.models.ReviewRequest.target_people`

  The individual reviewers targeted by this review request (a queryset of
  :py:class:`~django.contrib.auth.models.User`).

* :py:meth:`~reviewboard.reviews.models.ReviewRequest.get_public_reviews()`

  Returns a queryset of all public
  :py:class:`~reviewboard.reviews.models.Review` objects for this review
  request. Useful for inspecting reviewer identities and review details.


User Roles
----------

:ref:`User Roles <user-roles>` let you assign named roles to users and check
for them in your approval hook. This allows for powerful role-based approval
policies.

For example, you can enforce that each review request must be approved by
at least one Team Lead:

.. code-block:: python

    from __future__ import annotations

    from typing import TYPE_CHECKING

    from reviewboard.extensions.base import Extension
    from reviewboard.extensions.hooks import ReviewRequestApprovalHook
    from reviewboard.reviews.models import Review

    from rbpowerpack.roles.models import UserRole

    if TYPE_CHECKING:
        from reviewboard.reviews.approval import ReviewRequestApproval
        from reviewboard.reviews.models import ReviewRequest


    class TeamLeadApprovalHook(ReviewRequestApprovalHook):
        def get_approval(
            self,
            *,
            review_request: ReviewRequest,
            prev_approval: ReviewRequestApproval,
        ) -> ReviewRequestApproval:
            # Always preserve prior failures.
            if not prev_approval['approved']:
                return prev_approval

            try:
                team_lead_role = UserRole.objects.get(
                    slug='team-lead',
                    local_site=review_request.local_site)
            except UserRole.DoesNotExist:
                return {
                    'approved': False,
                    'reason': 'No Team Lead role is configured.',
                }

            has_team_lead_ship_it = Review.objects.filter(
                review_request=review_request,
                public=True,
                ship_it=True,
                user__in=team_lead_role.users.all(),
            ).exists()

            if has_team_lead_ship_it:
                return prev_approval

            return {
                'approved': False,
                'reason': 'A Team Lead must approve this review request.',
            }


    class ApprovalExtension(Extension):
        def initialize(self) -> None:
            TeamLeadApprovalHook(self)

There's also a useful :py:meth:`UserRole.objects.for_user()
<rbpowerpack.roles.managers.UserRoleManager.for_user>` method which returns
all user roles assigned to a given user.
