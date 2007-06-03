#!/usr/bin/env python
from django.core.management import execute_manager
try:
    import settings # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n(If the file settings.py does indeed exist, it's causing an ImportError somehow.)\n" % __file__)
    sys.exit(1)


warnings_found = 0
def check_dependencies():
    from settings import dependency_error

    # Python 2.4
    import sys
    if sys.version_info[0] < 2 or \
       (sys.version_info[0] == 2 and sys.version_info[1] < 4):
        dependency_error('Python 2.4 or newer is required.')

    # Django 0.96
    try:
        import django
        if django.VERSION[0] == 0 and django.VERSION[1] < 96:
            dependency_error('Django 0.96 or newer is required.')
    except ImportError:
        dependency_error('Django 0.96 or newer is required.')

    # PIL
    try:
        import PIL
    except ImportError:
        dependency_error('The Python Imaging Library (PIL) is required.')

    import subprocess

    # patchutils
    try:
        subprocess.call(['lsdiff', '--version'], stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE, close_fds=True)
    except OSError:
        dependency_error('Patchutils not found.')

    # The following checks are non-fatal warnings, since these dependencies are
    # merely recommended, not required.
    def dependency_warning(string):
        sys.stderr.write('Warning: %s\n' % string)
        global warnings_found
        warnings_found += 1

    try:
        import pysvn
    except ImportError:
        dependency_warning('pysvn not found.  SVN integration will not work.')

    try:
        import p4
    except ImportError:
        dependency_warning('p4python not found.  Perforce integration will not work.')

    # Django will print warnings/errors for database backend modules and flup
    # if the configuration requires it.

    if warnings_found:
        sys.stderr.write(settings.install_help)
        sys.stderr.write('\n\n')


if __name__ == "__main__":
    if settings.DEBUG:
        # If DJANGO_SETTINGS_MODULE is in our environment, we're in
        # execute_manager's sub-process.  It doesn't make sense to do this
        # check twice, so just return.
        import os
        if 'DJANGO_SETTINGS_MODULE' not in os.environ:
            print 'Running depdendency checks (set DEBUG=False to turn this off)...'
            check_dependencies()

    execute_manager(settings)
