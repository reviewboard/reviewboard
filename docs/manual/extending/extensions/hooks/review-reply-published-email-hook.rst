.. _review-reply-published-email-hook:

=============================
ReviewReplyPublishedEmailHook
=============================

:py:class:`reviewboard.extensions.hooks.ReviewPublishedEmailHook` allows
extensions to modify the recipients of e-mails generated from review reply
publishing activity.

:py:class:`ReviewReplyPublishedEmailHook` requires one arguments for
initialization: the extension instance.

:py:class:`ReviewReplyPublishedEmailHook` should be sub-classed to provide the
desired behaviour. The default behaviour of the :py:meth:`get_to_field` and
:py:meth:`get_cc_field` methods is to return the field unmodified.


Example
=======

.. code-block:: python

    from typing import TYPE_CHECKING

    from reviewboard.extensions.base import Extension
    from reviewboard.extensions.hooks import ReviewReplyPublishedEmailHook

    if TYPE_CHECKING:
        from django.contrib.auth.models import User
        from reviewboard.notifications.email.utils import RecipientList
        from reviewboard.reviews.models import Review, ReviewRequest


    class SampleEmailHook(ReviewReplyPublishedEmailHook):
        def get_to_field(
            self,
            to_field: RecipientList,
            reply: Review,
            user: User,
            review: Review,
            review_request: ReviewRequest,
        ) -> RecipientList:
            to_field.add(user)
            return to_field

        def get_cc_field(
            self,
            cc_field: RecipientList,
            reply: Review,
            user: User,
            review: Review,
            review_request: ReviewRequest,
        ) -> RecipientList:
            return set()

    class SampleExtension(Extension):
        def initialize(self) -> None:
            SampleEmailHook(self)
