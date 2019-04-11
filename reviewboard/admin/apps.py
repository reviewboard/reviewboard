"""Django app information for reviewboard.admin."""

from __future__ import unicode_literals

try:
    from django.apps import AppConfig
except ImportError:
    # Django < 1.7
    AppConfig = object


class AdminAppConfig(AppConfig):
    """App configuration for reviewboard.admin."""

    name = 'reviewboard.admin'
    label = 'reviewboard_admin'
