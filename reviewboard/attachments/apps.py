"""The app definition for reviewboard.attachments.

Version Added:
    6.0
"""

from __future__ import annotations

from django.apps import AppConfig


class AttachmentsAppConfig(AppConfig):
    """App configuration for reviewboard.attachments.

    Version Added:
        6.0
    """

    name = 'reviewboard.attachments'

    def ready(self) -> None:
        """Configure the app once it's ready.

        This will connect signal handlers for the app.
        """
        from reviewboard.attachments.signal_handlers import \
            connect_signal_handlers

        connect_signal_handlers()
