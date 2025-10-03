.. _signal-hook:

==========
SignalHook
==========

:py:class:`reviewboard.extensions.hooks.SignalHook` allows extensions to
easily connect to :djangodoc:`signals <topics/signals>` without worrying about
manually disconnecting when the extension is disabled.

There are many signals built in to Review Board and Django, allowing your
extension to run code when certain events occur, such as when database models
are saved, review requests are published, etc.

To connect to a signal, the extension needs to instantiate
:py:class:`SignalHook` and pass in the signal to connect to, the callback
function, and an optional :djangodoc:`sender
<topics/signals#connecting-to-signals-sent-by-specific-senders>`.


Example
=======

.. code-block:: python

    import logging
    from typing import TYPE_CHECKING

    from reviewboard.extensions.base import Extension
    from reviewboard.extensions.hooks import SignalHook
    from reviewboard.reviews.signals import review_request_published

    if TYPE_CHECKING:
        from reviewboard.reviews.models import ReviewRequest


    class SampleExtension(Extension):
        def initialize(self) -> None:
            SignalHook(self, review_request_published, self.on_published)

        def on_published(
            self,
            review_request: (ReviewRequest | None) = None,
            **kwargs,
        ) -> None:
            logging.info('Review request %s was published!',
                         review_request.display_id)
