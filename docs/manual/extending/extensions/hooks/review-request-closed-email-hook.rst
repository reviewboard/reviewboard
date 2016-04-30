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

    from reviewboard.extensions.base import Extension
    from reviewboard.extensions.hooks import ReviewRequestClosedEmailHook
    from reviewboard.reviews.models import ReviewRequest

    class SampleEmailHook(ReviewRequestPublishedEmailHook):
        def get_to_field(self, to_field, review_request, user, close_type):
            if close_type == ReviewRequest.DISCARDED:
                # Do not send discarded review request e-mails.
                to_field.clear()

            return to_field

        def get_cc_field(self, cc_field, review_request, user, close_type):
            if close_type == ReviewRequest.DISCARDED:
                # Do not send discarded review request e-mails.
                cc_field.clear()

            return cc_field

    class SampleExtension(Extension):
        def initialize(self):
            SampleEmailHook(self)
