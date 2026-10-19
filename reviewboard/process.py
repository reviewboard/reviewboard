"""Process setup and management for Review Board.

Version Added:
    9.0
"""

# NOTE: Imports for anything that touches Django/database functionality must
#       be done within a function. Importing at the module level can cause
#       problems with apps being loaded in the wrong order.
#
#       The exceptions are the parent reviewboard module and
#       reviewboard.deprecation.

from __future__ import annotations

import logging
import os

from housekeeping import deprecate_non_keyword_only_args

from reviewboard import get_version_string
from reviewboard.deprecation import RemovedInReviewBoard11_0Warning


@deprecate_non_keyword_only_args(RemovedInReviewBoard11_0Warning)
def initialize(
    *,
    load_extensions: bool = True,
    setup_logging: bool = True,
    setup_templates: bool = True,
) -> None:
    """Begin initialization of Review Board.

    This sets up the logging, generates cache serial numbers, loads extensions,
    and sets up other aspects of Review Board. Once it has finished, it will
    fire the :py:data:`reviewboard.signals.initializing` signal.

    This must be called at some point before most features will work, but it
    will be called automatically in a standard install. If you are writing
    an extension or management command, you do not need to call this yourself.

    Version Added:
        9.0:
        This moved from :py:mod:`reviewboard`. The old function wraps this.

    Args:
        load_extensions (bool, optional):
            Whether extensions should be automatically loaded upon
            initialization. If set, extensions will only load if the site
            has been upgraded to the latest version of Review Board.

        setup_logging (bool, optional):
            Whether to set up logging based on the configured settings.
            This can be disabled if the caller has their own logging
            configuration.

        setup_templates (bool, optional):
            Whether to set up state for template rendering. This can be
            disabled if the caller has no need for template rendering of
            any kind. This does not prevent template rendering from
            happening, but may change the output of some templates.

            Keep in mind that many pieces of functionality, such as avatars
            and some management commands, may be impacted by this setting.
    """
    os.environ.setdefault('DJANGO_SETTINGS_MODULE',
                          'reviewboard.settings')

    import settings_local

    # Set RBSITE_PYTHON_PATH to the path we need for any RB-bundled
    # scripts we may call.
    os.environ['RBSITE_PYTHONPATH'] = os.path.dirname(settings_local.__file__)

    from django import setup
    from django.apps import apps

    if not apps.ready:
        setup()

    from django.conf import settings
    from django.db import DatabaseError
    from djblets import log
    from djblets.cache.serials import generate_ajax_serial
    from djblets.siteconfig.models import SiteConfiguration

    from reviewboard import signals
    from reviewboard.admin.siteconfig import load_site_config
    from reviewboard.extensions.base import get_extension_manager

    is_running_test = getattr(settings, 'RUNNING_TEST', False)

    if setup_logging and not is_running_test:
        # Set up logging.
        log.init_logging()

    load_site_config()

    if (setup_templates or load_extensions) and not is_running_test:
        if settings.DEBUG:
            logging.debug('Log file for Review Board v%s (PID %s)' %
                          (get_version_string(), os.getpid()))

        # Generate the AJAX serial, used for AJAX request caching.
        generate_ajax_serial()

        # Store the AJAX serial as a template serial, so we have a reference
        # to the real serial last modified timestamp of our templates. This
        # is useful since the extension manager will be modifying AJAX_SERIAL
        # to prevent stale caches for templates using hooks. Not all templates
        # use hooks, and may want to base cache keys off TEMPLATE_SERIAL
        # instead.
        #
        # We only want to do this once, so we don't end up replacing it
        # later with a modified AJAX_SERIAL later.
        if not getattr(settings, 'TEMPLATE_SERIAL', None):
            settings.TEMPLATE_SERIAL = settings.AJAX_SERIAL

    siteconfig = SiteConfiguration.objects.get_current()

    if load_extensions and not is_running_test:
        installed_version = get_version_string()

        if siteconfig.version == installed_version:
            # Load all extensions
            try:
                get_extension_manager().load()
            except DatabaseError:
                # This database is from a time before extensions, so don't
                # attempt to load any extensions yet.
                pass
        else:
            logging.warning('Extensions will not be loaded. The site must '
                            'be upgraded from Review Board %s to %s.',
                            siteconfig.version, installed_version)

    signals.initializing.send(sender=None)
