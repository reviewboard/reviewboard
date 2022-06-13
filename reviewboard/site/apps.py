"""Django app information for reviewboard.site."""

from django.apps import AppConfig


class SiteAppConfig(AppConfig):
    """App configuration for reviewboard.site."""

    name = 'reviewboard.site'

    def ready(self):
        """Configure the app once it's ready.

        This will connect signal handlers for the app.
        """
        from reviewboard.site.signal_handlers import connect_signal_handlers

        connect_signal_handlers()
