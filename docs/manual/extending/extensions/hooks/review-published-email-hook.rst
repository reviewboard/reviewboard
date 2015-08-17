.. _review-published-email-hook:

========================
ReviewPublishedEmailHook
========================

:py:class:`reviewboard.extensions.hooks.ReviewPublishedEmailHook` allows
extensions to modify the recipients of e-mails generated from review publishing
activity.

:py:class:`ReviewPublishedEmailHook` requires one arguments for initialization:
the extension instance.

:py:class:`ReviewPublishedEmailHook` should be sub-classed to provide the
desired behaviour. The default behaviour of the :py:meth:`get_to_field` and
:py:meth:`get_cc_field` methods is to return the field unmodified.


Example
=======

.. code-block:: python

    from reviewboard.extensions.base import Extension
    from reviewboard.extensions.hooks import ReviewPublishedEmailHook

    class SampleEmailHook(Review PublishedEmailHook):
        def get_to_field(self, to_field, reply, user, review, review_request):
            to_field.add(user)

        def get_cc_field(self, cc_field, reply, user, review, review_request):
            return set([])

    class SampleExtension(Extension):
        def initialize(self):
            SampleEmailHook(self)
