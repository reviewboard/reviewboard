.. _email_hook:

=========
EmailHook
=========

:py:class:`reviewboard.extensions.hooks.EmailHook` allows extensions to modify
the recipients of e-mails generated from review request activity

:py:class:`EmailHook` requires two arguments for initialization: the extension
instance and the list of review request signals to listen for. It can listen
for the following signals:

 * :py:ref:`reviewboard.reviews.signals.review_request_published`;
 * :py:ref:`reviewboard.reviews.signals.review_request_closed`;
 * :py:ref:`reviewboard.reviews.signals.review_published`; and
 * :py:ref:`reviewboard.reviews.siganls.reply_published`.

Attempting to use any other signal will trigger an exception.

:py:class:`EmailHook` should be sub-classed to provide the desired behaviour.
Convenient sub-classes exist for each of the above signals so that only the
:py:meth:`get_to_field` and :py:meth:`get_cc_field` methods have to be
defined. The default behaviour of these methods is to return the field
unmodified.

These sub-classes are:

.. toctree::
   :maxdepth: 1

   review_request_published_email_hook
   review_request_closed_email_hook
   review_published_email_hook
   review_reply_published_email_hook


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
