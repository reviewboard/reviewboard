"""Django app information for reviewboard.admin."""

from __future__ import unicode_literals

from django.apps import AppConfig


class AdminAppConfig(AppConfig):
    """App configuration for reviewboard.admin."""

    name = 'reviewboard.admin'
    label = 'reviewboard_admin'
