"""Review Board version and package information.

These variables and functions can be used to identify the version of
Review Board. They're largely used for packaging purposes.
"""

from __future__ import annotations


#: The version of Review Board.
#:
#: This is in the format of:
#:
#: (Major, Minor, Micro, Patch, alpha/beta/rc/final, Release Number, Released)
#:
VERSION: tuple[int, int, int, int, str, int, bool] = \
    (8, 0, 0, 0, 'alpha', 0, False)


def get_version_string() -> str:
    """Return the Review Board version as a human-readable string.

    Returns:
        str:
        The Review Board version string.
    """
    major, minor, micro, patch, tag, release_num, released = VERSION
    version = f'{major}.{minor}'

    if micro or patch:
        version += f'.{micro}'

    if patch:
        version += f'.{patch}'

    if tag != 'final':
        if tag == 'rc':
            version += f' RC{release_num}'
        else:
            version += f' {tag} {release_num}'

    if not released:
        version += ' (dev)'

    return version


def get_package_version() -> str:
    """Return the Review Board version as a Python package version string.

    Returns:
        str:
        The Review Board package version.
    """
    major, minor, micro, patch, tag, release_num = VERSION[:-1]
    version = f'{major}.{minor}'

    if micro or patch:
        version += f'.{micro}'

    if patch:
        version += f'.{patch}'

    if tag != 'final':
        if tag == 'alpha':
            tag = 'a'
        elif tag == 'beta':
            tag = 'b'

        version += f'{tag}{release_num}'

    return version


def is_release() -> bool:
    """Return whether this is a released version of Review Board.

    Returns:
        bool:
        True if the current version of Review Board is a release.
    """
    return VERSION[-1]


def get_manual_url() -> str:
    """Return the URL to the Review Board manual for this version.

    Returns:
        str:
        The URL to the user manual.
    """
    if VERSION[2] == 0 and VERSION[4] != 'final':
        manual_ver = 'dev'
    else:
        manual_ver = f'{VERSION[0]}.{VERSION[1]}'

    return f'https://www.reviewboard.org/docs/manual/{manual_ver}/'


def initialize(
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
    import logging
    import os

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


def finalize_setup(
    is_upgrade: bool = False,
) -> None:
    """Internal function to upgrade internal state after installs/upgrades.

    This should only be called by Review Board install or upgrade code.

    Version Changed:
        5.0:
            Removed the ``register_scmtools`` argument.

    Version Added:
        4.0:

    Args:
        is_upgrade (bool, optional):
            Whether this is finalizing an upgrade, rather than a new install.
    """
    from reviewboard import signals
    from reviewboard.admin.management.sites import init_siteconfig

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
