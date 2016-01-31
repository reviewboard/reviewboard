#!/usr/bin/env python

from __future__ import unicode_literals

import os
import subprocess
import sys
from os.path import abspath, dirname
from wsgiref import simple_server

from django.core.management import execute_from_command_line


warnings_found = 0


def check_dependencies(settings):
    # Some of our checks require access to django.conf.settings, so
    # tell Django about our settings.
    #
    from djblets.util.filesystem import is_exe_in_path

    from reviewboard.admin.import_utils import has_module

    dependency_error = settings.dependency_error

    # Python 2.6
    if sys.version_info[0] < 2 or \
       (sys.version_info[0] == 2 and sys.version_info[1] < 6):
        dependency_error('Python 2.6 or newer is required.')

    # django-evolution
    if not has_module('django_evolution'):
        dependency_error("django_evolution is required.\n"
                         "http://code.google.com/p/django-evolution/")

    # PIL
    if not has_module('PIL') and not has_module('Image'):
        dependency_error('The Python Imaging Library (Pillow or PIL) '
                         'is required.')

    # ReCaptcha
    if not has_module('recaptcha'):
        dependency_error('The recaptcha python module is required.')

    # The following checks are non-fatal warnings, since these dependencies are
    # merely recommended, not required.
    def dependency_warning(string):
        sys.stderr.write('Warning: %s\n' % string)
        global warnings_found
        warnings_found += 1

    if not has_module('pysvn') and not has_module('subvertpy'):
        dependency_warning('Neither subvertpy nor pysvn found. '
                           'SVN integration will not work.')

    if has_module('P4'):
        try:
            subprocess.call(['p4', '-h'],
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        except OSError:
            dependency_error('p4 command not found. Perforce integration '
                             'will not work.')
    else:
        dependency_warning('p4python (>=07.3) not found. Perforce integration '
                           'will not work.')

    if not has_module('mercurial'):
        dependency_warning('hg not found. Mercurial integration will not '
                           'work.')

    if not has_module('bzrlib'):
        dependency_warning('bzrlib not found. Bazaar integration will not '
                           'work.')

    if not is_exe_in_path('cvs'):
        dependency_warning('cvs binary not found. CVS integration '
                           'will not work.')

    if not is_exe_in_path('git'):
        dependency_warning('git binary not found. Git integration '
                           'will not work.')

    if not is_exe_in_path('mtn'):
        dependency_warning('mtn binary not found. Monotone integration '
                           'will not work.')

    # Django will print warnings/errors for database backend modules and flup
    # if the configuration requires it.

    if warnings_found:
        sys.stderr.write(settings.install_help)
        sys.stderr.write('\n\n')


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
