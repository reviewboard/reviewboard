"""OAuth initialization.

This module loads the WebAPI scopes when Review Board initializes.
"""

from __future__ import unicode_literals

from django.dispatch import receiver

from reviewboard.signals import initializing


default_app_config = 'reviewboard.oauth.apps.OAuthAppConfig'


@receiver(initializing)
def _on_initializing(**kwargs):
    """Enable OAuth scopes for the API when initializing Review Board.

    Args:
        **kwargs (dict):
            Keyword arguments from the signal.
    """
    from djblets.webapi.oauth2_scopes import enable_web_api_scopes

    enable_web_api_scopes()
