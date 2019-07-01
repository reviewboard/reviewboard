from __future__ import unicode_literals

from django.conf import settings
from django.core.management import call_command
from django.db.models import signals


def _register_scmtools(app_config=None, app=None, **kwargs):
    """Register any missing default SCMTools after a database install/upgrade.

    This will only register if we're not in the middle of a unit test run.

    Args:
        app_config (django.apps.AppConfig, optional):
            The app configuration that was migrated. This is only provided on
            Django 1.11.

        app (module, optional):
            The app that was synced. This is only provided on Django 1.6.

        **kwargs (dict):
            Additional keyword arguments passed in the signal.
    """
    if (not getattr(settings, 'RUNNING_TEST', False) and
        ((app_config is not None and app_config.label == 'scmtools') or
         (app is not None and app.__name__ == 'reviewboard.scmtools.models'))):
        call_command('registerscmtools')


if hasattr(signals, 'post_migrate'):
    signals.post_migrate.connect(_register_scmtools)
elif hasattr(signals, 'post_syncdb'):
    signals.post_syncdb.connect(_register_scmtools)
