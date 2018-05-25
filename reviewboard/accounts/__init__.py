"""Initialization for the Review Board accounts module."""

from __future__ import unicode_literals

from django.dispatch import receiver

from reviewboard.signals import initializing


@receiver(initializing)
def _on_initializing(**kwargs):
    """Set up account-related objects during Review Board initialization.

    This will register all main consent requirements needed by Review Board.

    Args:
        **kwargs (dict):
            Keyword arguments from the signal.
    """
    from reviewboard.accounts.privacy import register_privacy_consents

    register_privacy_consents()
