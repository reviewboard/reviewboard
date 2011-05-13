#!/usr/bin/env python

import imp
import sys
import os
from os.path import abspath, dirname

# Add the parent directory of 'manage.py' to the python path, so manage.py can
# be run from any directory.  From http://www.djangosnippets.org/snippets/281/
sys.path.insert(0, dirname(dirname(abspath(__file__))))

try:
    import settings # Assumed to be in the same directory.
except ImportError:
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n(If the file settings.py does indeed exist, it's causing an ImportError somehow.)\n" % __file__)
    sys.exit(1)

from django.core.management import execute_manager, setup_environ
from reviewboard.admin.migration import fix_django_evolution_issues


warnings_found = 0
def check_dependencies():
    # Some of our checks require access to django.conf.settings, so
    # tell Django about our settings.
    #
    # This must go before the imports.
    setup_environ(settings)


    from django.template.defaultfilters import striptags
    from djblets.util.filesystem import is_exe_in_path

    from reviewboard.admin import checks

    from settings import dependency_error


    # Python 2.4
    if sys.version_info[0] < 2 or \
       (sys.version_info[0] == 2 and sys.version_info[1] < 4):
        dependency_error('Python 2.4 or newer is required.')

    # Django 1.0
    try:
        # Django 1.0 final has VERSION (1, 0, "final").
        # All subsequent versions have a 5-tuple, e.g. (1, 1, 0, "alpha", 0).
        import django
        if not (django.VERSION == (1, 0, "final") or
                (len(django.VERSION) == 5 and django.VERSION[1] >= 0)):
            raise ImportError
    except ImportError:
        dependency_error("Django 1.0 or newer is required.")

    # django-evolution
    try:
        imp.find_module('django_evolution')
    except ImportError:
        dependency_error("django_evolution is required.\n"
                         "http://code.google.com/p/django-evolution/")

    # PIL
    try:
        imp.find_module('PIL')
    except ImportError:
        try:
            imp.find_module('Image')
        except ImportError:
            dependency_error('The Python Imaging Library (PIL) is required.')


    # ReCaptcha
    try:
        import recaptcha
    except ImportError:
        dependency_error('The recaptcha python module is required.')

    import subprocess

    # The following checks are non-fatal warnings, since these dependencies are
    # merely recommended, not required.
    def dependency_warning(string):
        sys.stderr.write('Warning: %s\n' % string)
        global warnings_found
        warnings_found += 1

    try:
        imp.find_module('pysvn')
    except ImportError:
        dependency_warning('pysvn not found.  SVN integration will not work.')

    try:
        imp.find_module('P4')
        subprocess.call(['p4', '-h'],
                        stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    except ImportError:
        dependency_warning('p4python (>=07.3) not found.  Perforce integration will not work.')
    except OSError:
        dependency_error('p4 command not found.  Perforce integration will not work.')

    try:
        imp.find_module('mercurial')
    except ImportError:
        dependency_warning('hg not found.  Mercurial integration will not work.')

    try:
        imp.find_module('bzrlib')
    except ImportError:
        dependency_warning('bzrlib not found.  Bazaar integration will not work.')

    for check_func in (checks.get_can_enable_search,
                       checks.get_can_enable_syntax_highlighting):
        success, reason = check_func()

        if not success:
            dependency_warning(striptags(reason))

    if not is_exe_in_path('cvs'):
        dependency_warning('cvs binary not found.  CVS integration '
                           'will not work.')

    if not is_exe_in_path('git'):
        dependency_warning('git binary not found.  Git integration '
                           'will not work.')

    if not is_exe_in_path('mtn'):
        dependency_warning('mtn binary not found.  Monotone integration '
                           'will not work.')

    # Django will print warnings/errors for database backend modules and flup
    # if the configuration requires it.

    if warnings_found:
        sys.stderr.write(settings.install_help)
        sys.stderr.write('\n\n')


if __name__ == "__main__":
    if settings.DEBUG:
        if len(sys.argv) > 1 and \
           (sys.argv[1] == 'runserver' or sys.argv[1] == 'test'):
            # If DJANGO_SETTINGS_MODULE is in our environment, we're in
            # execute_manager's sub-process.  It doesn't make sense to do this
            # check twice, so just return.
            if 'DJANGO_SETTINGS_MODULE' not in os.environ:
                sys.stderr.write('Running dependency checks (set DEBUG=False to turn this off)...\n')
                check_dependencies()

    fix_django_evolution_issues(settings)

    execute_manager(settings)
