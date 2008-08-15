#!/usr/bin/env python

import imp
import sys
import os
from os.path import abspath, dirname

from django.core.management import execute_manager, setup_environ

# Add the parent directory of 'manage.py' to the python path, so manage.py can
# be run from any directory.  From http://www.djangosnippets.org/snippets/281/
sys.path.insert(0, dirname(dirname(abspath(__file__))))

try:
    import settings # Assumed to be in the same directory.
except ImportError:
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n(If the file settings.py does indeed exist, it's causing an ImportError somehow.)\n" % __file__)
    sys.exit(1)


warnings_found = 0
def check_dependencies():
    from settings import dependency_error

    # Python 2.4
    if sys.version_info[0] < 2 or \
       (sys.version_info[0] == 2 and sys.version_info[1] < 4):
        dependency_error('Python 2.4 or newer is required.')

    # Django 1.0 alpha
    try:
        import django
        if not (django.VERSION[0] == 1 and django.VERSION[1] >= 0 and
                django.VERSION[2] == "alpha_2"):
            raise ImportError
    except ImportError:
        dependency_error("Django >= 1.0 alpha 2 is required.")

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
        dependency_error('The Python Imaging Library (PIL) is required.')

    import subprocess

    # pygments
    if settings.DIFF_SYNTAX_HIGHLIGHTING:
        try:
            import pygments
            version = pygments.__version__.split(".")
            if version[0] == 0 and version[1] < 9:
                dependency_error('Pygments is installed, but is an old version. '
                                 'Versions prior to 0.9 are known to have '
                                 'serious problems.')
        except ImportError:
            dependency_error('The Pygments library is required when ' +
                             'DIFF_SYNTAX_HIGHLIGHTING is enabled.')

    # PyLucene
    if settings.ENABLE_SEARCH:
        try:
            imp.find_module('lucene')
        except ImportError:
            dependency_error('PyLucene (with JCC) is required when '
                             'ENABLE_SEARCH is set.')

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
        dependency_warning('p4python (>=08.1) not found.  Perforce integration will not work.')
    except OSError:
        dependency_error('p4 command not found.  Perforce integration will not work.')

    try:
        imp.find_module('mercurial')
    except ImportError:
        dependency_warning('hg not found.  Mercurial integration will not work.')

    found = False
    for dir in os.environ['PATH'].split(os.environ.get('IFS', ':')):
        if os.path.exists(os.path.join(dir, 'git')):
            found = True
            break
    if not found:
        dependency_warning('git binary not found.  Git integration will not work.')

    # Django will print warnings/errors for database backend modules and flup
    # if the configuration requires it.

    if warnings_found:
        sys.stderr.write(settings.install_help)
        sys.stderr.write('\n\n')


# XXX Ugliness needed due to weak refs for dispatch callbacks. This can be
#     reomved when fix_django_evolution_issues() goes away.
_signal_connections = []

def fix_django_evolution_issues():
    # XXX Django r8244 moves django.db.models.fields.files.ImageField and
    # FileField into django.db.models.files, causing existing
    # signatures to fail. For the purpose of loading, temporarily
    # place these back into fields. The next time the signature is
    # generated in Django Evolution, the correct, new location will be
    # written.
    #
    # TODO: Remove this when Django Evolution works again.
    project_directory = setup_environ(settings)
    import django.db.models.fields as model_fields
    import django.db.models.fields.files as model_files
    model_fields.ImageField = model_files.ImageField
    model_fields.FileField = model_files.FileField

    # XXX Temporary fix for Django Evolution's signal handler.
    #     Remove when they update to use the new signal code.
    from django.dispatch import dispatcher

    def custom_connect(function, signal):
        def wrapper_func(app, created_models, verbosity=1, **kwargs):
            function(app, created_models, verbosity=verbosity)

        dispatch_uid = "%s.%s" % (function.__module__, function.__name__)
        dispatch_uid = dispatch_uid.replace("..", ".")
        func = wrapper_func
        signal.connect(func, dispatch_uid=dispatch_uid)
        _signal_connections.append(func)

    dispatcher.connect = custom_connect


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

    fix_django_evolution_issues()

    execute_manager(settings)
