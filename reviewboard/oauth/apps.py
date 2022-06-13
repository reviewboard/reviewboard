"""The app definition for reviewboard.oauth."""

from django.apps import AppConfig


class OAuthAppConfig(AppConfig):
    """App configuration for reviewboard.oauth."""

    name = 'reviewboard.oauth'

    def ready(self):
        """Configure the app once it's ready.

        This will connect signal handlers for the app.

        Version Added:
            5.0
        """
        from reviewboard.oauth.signal_handlers import connect_signal_handlers

        connect_signal_handlers()
