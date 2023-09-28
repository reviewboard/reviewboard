"""The app definition for reviewboard.reviews.

Version Added:
    6.0
"""

from __future__ import annotations

from django.apps import AppConfig


class ReviewsAppConfig(AppConfig):
    """App configuration for reviewboard.reviews."""

    name = 'reviewboard.reviews'

    def ready(self) -> None:
        """Configure the app once it's ready.

        This will connect signal handlers for the app.

        Version Added:
            6.0
        """
        from reviewboard.reviews.signal_handlers import connect_signal_handlers

        connect_signal_handlers()
