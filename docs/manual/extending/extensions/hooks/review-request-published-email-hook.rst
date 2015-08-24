.. _review-request-published-email-hook:

===============================
ReviewRequestPublishedEmailHook
===============================

:py:class:`reviewboard.extensions.hooks.ReviewRequestPublishedEmailHook` allows
extensions to modify the recipients of e-mails generated from review publishing
actvity

:py:class:`ReviewRequestPublishedEmailHook` requires one arguments for
initialization: the extension instance.

:py:class:`ReviewRequestPublishedEmailHook` should be sub-classed to provide
the desired behaviour. The default behaviour of the :py:meth:`get_to_field` and
:py:meth:`get_cc_field` methods is to return the field unmodified.


Example
=======

.. code-block:: python

    from reviewboard.extensions.base import Extension
    from reviewboard.extensions.hooks import ReviewRequestPublishedEmailHook

    class SampleEmailHook(ReviewRequestPublishedEmailHook):
        def get_to_field(self, to_field, review_request, user):
            to_field.add(user)

        def get_cc_field(self, cc_field, review_request, user):
            return set([])

    class SampleExtension(Extension):
        def initialize(self):
            SampleEmailHook(self)
