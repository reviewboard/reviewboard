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
VERSION = (2, 5, 5, 0, 'final', 0, True)


#: The major version of Django we're using.
django_major_version = '1.6'

#: The required version of Django.
django_version = 'Django>=1.6.11,<1.7'


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
    """Return the Review Board version as a Python package version string."""
    version = '%s.%s' % (VERSION[0], VERSION[1])

    if VERSION[2] or VERSION[3]:
        version += ".%s" % VERSION[2]

    if VERSION[3]:
        version += ".%s" % VERSION[3]

    if VERSION[4] != 'final':
        version += '%s%s' % (VERSION[4], VERSION[5])

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


def initialize():
    """Begin initialization of Review Board.

    This sets up the logging, generates cache serial numbers, loads extensions,
    and sets up other aspects of Review Board. Once it has finished, it will
    fire the :py:data:`reviewboard.signals.initializing` signal.

    This must be called at some point before most features will work, but it
    will be called automatically in a standard install. If you are writing
    an extension or management command, you do not need to call this yourself.
    """
    import logging
    import os

    import settings_local

    # Set RBSITE_PYTHON_PATH to the path we need for any RB-bundled
    # scripts we may call.
    os.environ[b'RBSITE_PYTHONPATH'] = \
        os.path.dirname(settings_local.__file__)

    from Crypto import Random
    from django.conf import settings
    from django.db import DatabaseError
    from djblets import log
    from djblets.cache.serials import generate_ajax_serial

    from reviewboard import signals
    from reviewboard.admin.siteconfig import load_site_config
    from reviewboard.extensions.base import get_extension_manager

    # This overrides a default django templatetag (url), and we want to make
    # sure it will always get loaded in every python instance.
    import reviewboard.site.templatetags

    is_running_test = getattr(settings, 'RUNNING_TEST', False)

    if not is_running_test:
        # Force PyCrypto to re-initialize the random number generator.
        Random.atfork()

        # Set up logging.
        log.init_logging()

    load_site_config()

    if not is_running_test:
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

        # Load all extensions
        try:
            get_extension_manager().load()
        except DatabaseError:
            # This database is from a time before extensions, so don't attempt
            # to load any extensions yet.
            pass

    signals.initializing.send(sender=None)


#: An alias for the the version information from :py:data:`VERSION`.
#:
#: This does not include the last entry in the tuple (the released state).
__version_info__ = VERSION[:-1]

#: An alias for the version used for the Python package.
__version__ = get_package_version()
