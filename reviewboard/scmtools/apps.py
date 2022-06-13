"""App definition for reviewboard.scmtools.

Version Added:
    5.0
"""

from django.apps import AppConfig


class SCMToolsAppConfig(AppConfig):
    """App condfiguration for reviewboard.scmtools.

    Version Added:
        5.0
    """

    name = 'reviewboard.scmtools'

    def ready(self):
        """Configure the app once it's ready.

        This will populate the SCMTools registry.
        """
        from reviewboard.scmtools import scmtools_registry
        scmtools_registry.populate()
