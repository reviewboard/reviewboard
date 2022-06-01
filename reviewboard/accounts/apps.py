"""App definition for reviewboard.accounts.

Version Added:
    5.0
"""

from django.apps import AppConfig


class AccountsAppConfig(AppConfig):
    """App configuration for reviewboard.accounts.

    Version Added
        5.0
    """

    name = 'reviewboard.accounts'

    def ready(self):
        """Configure the app once it's ready.

        This will populate the SSO backends registry.
        """
        from reviewboard.accounts.sso.backends import sso_backends
        sso_backends.populate()
