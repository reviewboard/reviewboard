from __future__ import unicode_literals

from django.db.models import signals

from reviewboard.admin.management.sites import init_siteconfig


def _init_siteconfig(app_config=None, app=None, **kwargs):
    """Create/upgrade the SiteConfiguration after a database install/upgrade.

    Args:
        app_config (django.apps.AppConfig, optional):
            The app configuration that was migrated. This is only provided on
            Django 1.11.

        app (module, optional):
            The app that was synced. This is only provided on Django 1.6.

        **kwargs (dict):
            Additional keyword arguments passed in the signal.
    """
    if ((app_config is not None and
         app_config.label == 'djblets_siteconfig') or
        (app is not None and app.__name__ == 'djblets.siteconfig.models')):
        init_siteconfig()


if hasattr(signals, 'post_migrate'):
    signals.post_migrate.connect(_init_siteconfig)
elif hasattr(signals, 'post_syncdb'):
    signals.post_syncdb.connect(_init_siteconfig)
