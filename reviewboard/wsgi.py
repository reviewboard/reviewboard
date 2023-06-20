"""WSGI application for Review Board.

This is the main WSGI entrypoint for loading Review Board. This configures the
Review Board environment based on your system and site directory configuration.

This MUST NOT be modified or copied from the version shipped with Review Board!
If you need to make changes, create your own file that imports from
:py:mod:`reviewboard.wsgi`.

To use this, make sure you set the :envvar:`REVIEWBOARD_SITEDIR` environment
variable to point to the absolute path of the Review Board site directory.
"""

import os
import sys


sitedir = os.environ.get('REVIEWBOARD_SITEDIR')

if not sitedir:
    raise RuntimeError(
        'The REVIEWBOARD_SITEDIR environment variable must be set to the '
        'Review Board site directory.'
    )

# Check for a virtualenv configuration.
#
# If a $sitedir/venv is present, and a virtualenv is not already activated,
# this will perform some sanity-checks on the version and virtualenv setup
# and then activate the environment.
if not os.environ.get('VIRTUAL_ENV'):
    venv_dir = (os.environ.get('REVIEWBOARD_VENV_DIR') or
                os.path.join(sitedir, 'venv'))

    if os.path.exists(venv_dir):
        # We have a virtual environment to check and activate.
        activate_script = os.path.realpath(
            os.path.join(venv_dir, 'bin', 'activate_this.py'))

        if not os.path.exists(activate_script):
            raise RuntimeError(
                f'Your Review Board site directory has "{venv_dir}", but '
                f'"{activate_script}" is missing. This can happen if you '
                f'created this using `python -m venv` instead of '
                f'`virtualenv`. Please delete the old one and create a new '
                f'one with `virtualenv`. Then re-install Review Board in '
                f'that environment.'
            )

        # This is available to activate. First, sanity-check the version of
        # Python in the environment.
        pyver = '%s.%s' % sys.version_info[:2]

        if not os.path.exists(os.path.join(venv_dir, 'bin', f'python{pyver}')):
            raise RuntimeError(
                f'Your web server uses Python {pyver}, but this version '
                f'is not available in the Python virtual environment for '
                f'Review Board located at "{venv_dir}". You may need to '
                f'reinstall your virtual environment, your web server, or '
                f'your web server\'s Python support.'
            )

        try:
            with open(activate_script, 'r') as fp:
                exec(fp.read(), {
                    '__file__': activate_script,
                })
        except Exception as e:
            raise RuntimeError(
                f'There was an error activating the virtual environment '
                f'for Review Board at "{venv_dir}": {e}'
            ) from e


# Set the necessary variables to find Python modules, binaries, settings,
# and to store home directory data.
sys.path.insert(0, os.path.join(sitedir, 'conf'))

os.environ.update({
    'DJANGO_SETTINGS_MODULE': 'reviewboard.settings',
    'HOME': os.path.join(sitedir, 'data'),
    'PATH': os.pathsep.join([
        os.path.join(sitedir, 'bin'),
        os.environ.get('PATH', ''),
    ]),
    'PYTHONPATH': os.pathsep.join(sys.path),
    'PYTHON_EGG_CACHE': os.path.join(sitedir, 'tmp', 'egg_cache'),
})

# Construct the WSGI application.
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
