"""OAuth initialization.

This module loads the WebAPI scopes when Review Board initializes.
"""

from __future__ import unicode_literals

from djblets.webapi.oauth2_scopes import enable_web_api_scopes
from reviewboard.signals import initializing


default_app_config = 'reviewboard.oauth.apps.OAuthAppConfig'


initializing.connect(enable_web_api_scopes)
