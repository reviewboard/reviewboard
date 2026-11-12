"""Django app information for reviewboard.hostingsvcs.

Version Added:
    9.0
"""

from __future__ import annotations

from django.apps import AppConfig


class HostingServicesAppConfig(AppConfig):
    """App configuration for reviewboard.hostingsvcs.

    Version Added:
        9.0
    """

    name = 'reviewboard.hostingsvcs'

    def ready(self) -> None:
        """Configure the app once it's ready.

        This will connect signal handlers for the app.
        """
        from reviewboard.hostingsvcs.signal_handlers import \
            connect_signal_handlers

        connect_signal_handlers()
