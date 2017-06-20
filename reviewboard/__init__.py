from __future__ import unicode_literals


# The version of Review Board.
#
# This is in the format of:
#
#   (Major, Minor, Micro, Patch, alpha/beta/rc/final, Release Number, Released)
#
VERSION = (2, 0, 29, 1, 'final', 0, True)


def get_version_string():
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
    version = '%s.%s' % (VERSION[0], VERSION[1])

    if VERSION[2] or VERSION[3]:
        version += ".%s" % VERSION[2]

    if VERSION[3]:
        version += ".%s" % VERSION[3]

    if VERSION[4] != 'final':
        version += '%s%s' % (VERSION[4], VERSION[5])

    return version


def is_release():
    return VERSION[6]


def get_manual_url():
    if VERSION[2] == 0 and VERSION[4] != 'final':
        manual_ver = 'dev'
    else:
        manual_ver = '%s.%s' % (VERSION[0], VERSION[1])

    return 'https://www.reviewboard.org/docs/manual/%s/' % manual_ver


def initialize():
    """Begins initialization of Review Board.

    This sets up the logging, generates cache serial numbers, and then
    fires an initializing signal that other parts of the codebase can
    connect to. This must be called for such features as e-mail notification
    to work.
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


__version_info__ = VERSION[:-1]
__version__ = get_package_version()
