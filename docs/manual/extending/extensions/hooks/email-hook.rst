.. _email-hook:

=========
EmailHook
=========

:py:class:`reviewboard.extensions.hooks.EmailHook` allows extensions to modify
the recipients of e-mails generated from review request activity.

:py:class:`EmailHook` requires two arguments for initialization: the extension
instance and the list of review request signals to listen for. It can listen
for the following signals:

* :py:data:`~reviewboard.reviews.signals.review_request_published`
* :py:data:`~reviewboard.reviews.signals.review_request_closed`
* :py:data:`~reviewboard.reviews.signals.review_published`
* :py:data:`~reviewboard.reviews.signals.reply_published`

Attempting to use any other signal will trigger an exception.

:py:class:`EmailHook` should be sub-classed to provide the desired behaviour.
Convenient sub-classes exist for each of the above signals so that only the
:py:meth:`get_to_field` and :py:meth:`get_cc_field` methods have to be
defined. The default behaviour of these methods is to return the field
unmodified.

These sub-classes are:

.. toctree::
   :maxdepth: 1

   review-request-published-email-hook
   review-request-closed-email-hook
   review-published-email-hook
   review-reply-published-email-hook


Example
=======

.. code-block:: python

    from reviewboard.extensions.base import Extension
    from reviewboard.extensions.hooks import EmailHook
    from reviewboard.reviews.signals import (review_request_published,
                                             review_published, reply_published,
                                             review_request_closed)

    class SampleEmailHook(EmailHook):
        def __init__(self, extension):
            super(EmailHook).__init__(extension,
                                      signals=[
                                          review_request_published,
                                          review_request_closed,
                                          review_published,
                                          reply_published,
                                      ])

        def get_to_field(self, to_field, **kwargs):
            if 'user' in kwargs:
                to_field.add(kwargs['user'])

        def get_cc_field(self, cc_field, **kwargs):
            return set([])

    class SampleExtension(Extension):
        def initialize(self):
            SampleEmailHook(self)
