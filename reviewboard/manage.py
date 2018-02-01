#!/usr/bin/env python

from __future__ import unicode_literals

import os
import subprocess
import sys
from os.path import abspath, dirname
from wsgiref import simple_server

from django.core.management import execute_from_command_line


def check_dependencies(settings):
    # We're now safe to import anything that might touch Django settings,
    # such as code utilizing the database. Start importing what we need for
    # dependency checks.
    from djblets.util.filesystem import is_exe_in_path

    from reviewboard.admin.import_utils import has_module
    from reviewboard.dependencies import (dependency_error,
                                          dependency_warning,
                                          fail_if_missing_dependencies)

    # Make sure the correct version of Python is being used. This should be
    # covered by setup.py, but it's best to make sure here.
    if sys.version_info[0] != 2 or sys.version_info[1] != 7:
        dependency_error('Python 2.7 is required.')

    # Check for NodeJS and installed modules, to make sure these weren't
    # missed during installation.
    if not is_exe_in_path('node'):
        dependency_error('node (from NodeJS) was not found. It must be '
                         'installed from your package manager or from '
                         'https://nodejs.org/')

    if not os.path.exists('node_modules'):
        dependency_error('The node_modules directory is missing. Please '
                         're-run `./setup.py develop` to install all NodeJS '
                         'dependencies.')

    for key in ('UGLIFYJS_BINARY', 'LESS_BINARY', 'BABEL_BINARY'):
        path = settings.PIPELINE[key]

        if not os.path.exists(path):
            dependency_error('%s is missing. Please re-run `./setup.py '
                             'develop` to install all NodeJS dependencies.'
                             % os.path.abspath(path))

    # The following checks are non-fatal warnings, since these dependencies
    # are merely recommended, not required. These are primarily for SCM
    # support.
    if not has_module('pysvn') and not has_module('subvertpy'):
        dependency_warning('Neither the subvertpy nor pysvn Python modules '
                           'were found. Subversion integration will not work. '
                           'For pysvn, see your package manager for the '
                           'module or download from '
                           'http://pysvn.tigris.org/project_downloads.html. '
                           'For subvertpy, run `pip install subvertpy`. We '
                           'recommend pysvn for better compatibility.')

    if has_module('P4'):
        try:
            subprocess.call(['p4', '-h'],
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        except OSError:
            dependency_warning('The p4 command not found. Perforce '
                               'integration will not work. To enable support, '
                               'download p4 from '
                               'http://cdist2.perforce.com/perforce/ and '
                               'place it in your PATH.')
    else:
        dependency_warning('The p4python module was not found. Perforce '
                           'integration will not work. To enable support, '
                           'run `pip install p4python`')

    if not is_exe_in_path('hg'):
        dependency_warning('The hg command was not found. Mercurial '
                           'integration will not work. To enable support, '
                           'run `pip install mercurial`')

    if not is_exe_in_path('bzr'):
        dependency_warning('The bzr command was not found. Bazaar integration '
                           'will not work. To enable support, run '
                           '`pip install bzr`')

    if not is_exe_in_path('cvs'):
        dependency_warning('The cvs command was not found. CVS integration '
                           'will not work. To enable support, install cvs '
                           'from your package manager or from '
                           'http://www.nongnu.org/cvs/')

    if not is_exe_in_path('git'):
        dependency_warning('The git command not found. Git integration '
                           'will not work. To enable support, install git '
                           'from your package manager or from '
                           'https://git-scm.com/downloads')

    # Along with all those, Django will print warnings/errors for database
    # backend modules if the configuration requires it.
    #
    # Now that that's all done, check if anything was missing and, if so,
    # fail with some helpful text.
    fail_if_missing_dependencies()


def include_enabled_extensions(settings):
    """
    This adds enabled extensions to the INSTALLED_APPS cache
    so that operations like syncdb and evolve will take extensions
    into consideration.
    """
    from django.db.models.loading import load_app
    from django.db import DatabaseError

    from reviewboard.extensions.base import get_extension_manager

    try:
        manager = get_extension_manager()
    except DatabaseError:
        # This database is from a time before extensions, so don't attempt to
        # load any extensions yet.
        return

    for extension in manager.get_enabled_extensions():
        load_app(extension.info.app_name)


def main(settings, in_subprocess):
    if dirname(settings.__file__) == os.getcwd():
        sys.stderr.write("manage.py should not be run from within the "
                         "'reviewboard' Python package directory.\n")
        sys.stderr.write("Make sure to run this from the top of the "
                         "Review Board source tree.\n")
        sys.exit(1)

    if (len(sys.argv) > 1 and
        (sys.argv[1] == 'runserver' or sys.argv[1] == 'test')):
        if settings.DEBUG and not in_subprocess:
            sys.stderr.write('Running dependency checks (set DEBUG=False '
                             'to turn this off)...\n')
            check_dependencies(settings)

        if sys.argv[1] == 'runserver':
            # Force using HTTP/1.1 for all responses, in order to work around
            # some browsers (Chrome) failing to consistently handle some
            # cache headers.
            simple_server.ServerHandler.http_version = '1.1'
    else:
        # Some of our checks require access to django.conf.settings, so
        # tell Django about our settings.
        #
        # Initialize Review Board, so we're in a state ready to load
        # extensions and run management commands.
        from reviewboard import initialize
        initialize()

        include_enabled_extensions(settings)

    execute_from_command_line(sys.argv)


def run():
    # Add the parent directory of 'manage.py' to the python path, so
    # manage.py can be run from any directory.
    # From http://www.djangosnippets.org/snippets/281/
    sys.path.insert(0, dirname(dirname(abspath(__file__))))

    # Python may insert the directory that manage.py is in into the Python
    # path, which can cause conflicts with other modules (such as Python's
    # "site" module). We don't want this, so it's important that we remove
    # this directory from the path.
    try:
        sys.path.remove(dirname(abspath(__file__)))
    except ValueError:
        pass

    if b'DJANGO_SETTINGS_MODULE' not in os.environ:
        in_subprocess = False
        os.environ.setdefault(b'DJANGO_SETTINGS_MODULE',
                              b'reviewboard.settings')
    else:
        in_subprocess = True

    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        # We're running unit tests, so we need to be sure to mark this in
        # order for the settings to reflect that. Otherwise, the test runner
        # will do things like load extensions or compile static media.
        os.environ[b'RB_RUNNING_TESTS'] = b'1'

    try:
        from reviewboard import settings
    except ImportError as e:
        sys.stderr.write("Error: Can't find the file 'settings.py' in the "
                         "directory containing %r. It appears you've "
                         "customized things.\n"
                         "You'll have to run django-admin.py, passing it your "
                         "settings module.\n"
                         "(If the file settings.py does indeed exist, it's "
                         "causing an ImportError somehow.)\n" % __file__)
        sys.stderr.write("The error we got was: %s\n" % e)
        sys.exit(1)

    main(settings, in_subprocess)


if __name__ == "__main__":
    run()
