.. _review-request-closed-email-hook:

============================
ReviewRequestClosedEmailHook
============================

:py:class:`reviewboard.extensions.hooks.ReviewRequestClosedEmailHook` allows
extensions to modify the recipients of e-mails generated from review publishing
activity.

:py:class:`ReviewRequestClosedEmailHook` requires one arguments for
initialization: the extension instance.

:py:class:`ReviewRequestClosedEmailHook` should be sub-classed to provide the
desired behaviour. The default behaviour of the :py:meth:`get_to_field` and
:py:meth:`get_cc_field` methods is to return the field unmodified.


Example
=======

.. code-block:: python

    from typing import TYPE_CHECKING

    from reviewboard.extensions.base import Extension
    from reviewboard.extensions.hooks import ReviewRequestClosedEmailHook
    from reviewboard.reviews.models import ReviewRequest

    if TYPE_CHECKING:
        from django.contrib.auth.models import User
        from reviewboard.notifications.email.utils import RecipientList
        from reviewboard.reviews.models import ReviewRequest


    class SampleEmailHook(ReviewRequestPublishedEmailHook):
        def get_to_field(
            self,
            to_field: RecipientList,
            review_request: ReviewRequest,
            user: User,
            close_type: str | None,
        ) -> RecipientList:
            if close_type == ReviewRequest.DISCARDED:
                # Do not send discarded review request e-mails.
                to_field.clear()

            return to_field

        def get_cc_field(
            self,
            cc_field: RecipientList,
            review_request: ReviewRequest,
            user: User,
            close_type: str | None,
        ) -> RecipientList:
            if close_type == ReviewRequest.DISCARDED:
                # Do not send discarded review request e-mails.
                cc_field.clear()

            return cc_field

    class SampleExtension(Extension):
        def initialize(self) -> None:
            SampleEmailHook(self)
