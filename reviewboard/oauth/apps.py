"""The app definition for reviewboard.oauth."""

from __future__ import unicode_literals

try:
    from django.apps import AppConfig
except ImportError:
    # Django < 1.7
    AppConfig = object


class OAuthAppConfig(AppConfig):
    name = 'reviewboard.oauth'
    label = 'reviewboard_oauth'