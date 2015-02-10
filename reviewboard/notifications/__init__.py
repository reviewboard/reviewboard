from __future__ import unicode_literals

from reviewboard.signals import initializing


def connect_signals(**kwargs):
    """
    Listens to the ``initializing`` signal and tells other modules to
    connect their signals. This is done so as to guarantee that django
    is loaded first.
    """
    from reviewboard.notifications import email, webhooks

    email.connect_signals()
    webhooks.connect_signals()


initializing.connect(connect_signals)
