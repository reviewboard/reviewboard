"""Django app information for reviewboard.scmtools.

Version Added:
    5.0
"""

from django.apps import AppConfig


class SCMToolsAppConfig(AppConfig):
    """App configuration for reviewboard.scmtools.

    Version Added:
        5.0
    """

    name = 'reviewboard.scmtools'

    def ready(self):
        """Configure the app once it's ready.

        This will connect signal handlers needed for repository and SCMTool
        management.
        """
        from reviewboard.scmtools.signal_handlers import \
            connect_signal_handlers

        connect_signal_handlers()
