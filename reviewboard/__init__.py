"""Review Board version and package information.

These variables and functions can be used to identify the version of
Review Board. They're largely used for packaging purposes.
"""

from __future__ import unicode_literals


#: The version of Review Board.
#:
#: This is in the format of:
#:
#: (Major, Minor, Micro, Patch, alpha/beta/rc/final, Release Number, Released)
#:
VERSION = (4, 0, 0, 0, 'final', 0, True)


def get_version_string():
    """Return the Review Board version as a human-readable string."""
    version = '%s.%s' % (VERSION[0], VERSION[1])

    if VERSION[2] or VERSION[3]:
        version += ".%s" % VERSION[2]

    if VERSION[3]:
        version += ".%s" % VERSION[3]

    if VERSION[4] != 'final':
        if VERSION[4] == 'rc':
            version += ' RC%s' % VERSION[5]
        else:
            version += ' %s %s' % (VERSION[4], VERSION[5])

    if not is_release():
        version += " (dev)"

    return version


def get_package_version():
    """Return the Review Board version as a Python package version string.

    Returns:
        unicode:
        The Review Board package version.
    """
    version = '%s.%s' % (VERSION[0], VERSION[1])

    if VERSION[2] or VERSION[3]:
        version = '%s.%s' % (version, VERSION[2])

    if VERSION[3]:
        version = '%s.%s' % (version, VERSION[3])

    tag = VERSION[4]

    if tag != 'final':
        if tag == 'alpha':
            tag = 'a'
        elif tag == 'beta':
            tag = 'b'

        version = '%s%s%s' % (version, tag, VERSION[5])

    return version


def is_release():
    """Return whether this is a released version of Review Board."""
    return VERSION[6]


def get_manual_url():
    """Return the URL to the Review Board manual for this version."""
    if VERSION[2] == 0 and VERSION[4] != 'final':
        manual_ver = 'dev'
    else:
        manual_ver = '%s.%s' % (VERSION[0], VERSION[1])

    return 'https://www.reviewboard.org/docs/manual/%s/' % manual_ver


def initialize(load_extensions=True,
               setup_logging=True,
               setup_templates=True):
    """Begin initialization of Review Board.

    This sets up the logging, generates cache serial numbers, loads extensions,
    and sets up other aspects of Review Board. Once it has finished, it will
    fire the :py:data:`reviewboard.signals.initializing` signal.

    This must be called at some point before most features will work, but it
    will be called automatically in a standard install. If you are writing
    an extension or management command, you do not need to call this yourself.

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
    import importlib
    import logging
    import os

    os.environ.setdefault(str('DJANGO_SETTINGS_MODULE'),
                          str('reviewboard.settings'))

    import settings_local

    # Set RBSITE_PYTHON_PATH to the path we need for any RB-bundled
    # scripts we may call.
    os.environ[str('RBSITE_PYTHONPATH')] = \
        os.path.dirname(settings_local.__file__)

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
            logging.debug("Log file for Review Board v%s (PID %s)" %
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


def finalize_setup(is_upgrade=False,
                   register_scmtools=True):
    """Internal function to upgrade internal state after installs/upgrades.

    This should only be called by Review Board install or upgrade code.

    Args:
        is_upgrade (bool, optional):
            Whether this is finalizing an upgrade, rather than a new install.

        register_scmtools (bool, optional):
            Whether to register SCMTools when finalizing.

    Version Added:
        4.0:
    """
    from reviewboard import signals
    from reviewboard.admin.management.sites import init_siteconfig
    from reviewboard.scmtools.models import Tool

    # Add/update any SCMTool registrations.
    if register_scmtools:
        Tool.objects.register_from_entrypoints()

    # Update the recorded product version.
    init_siteconfig()

    # Notify anything else that needs to listen.
    signals.finalized_setup.send(sender=None,
                                 is_upgrade=is_upgrade)


#: An alias for the the version information from :py:data:`VERSION`.
#:
#: This does not include the last entry in the tuple (the released state).
__version_info__ = VERSION[:-1]

#: An alias for the version used for the Python package.
__version__ = get_package_version()
