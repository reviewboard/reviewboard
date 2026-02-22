#!/usr/bin/env python

import os
import shutil
import subprocess
import sys

scripts_dir = os.path.abspath(os.path.dirname(__file__))

# Source root directory
root_dir = os.path.abspath(os.path.join(scripts_dir, '..', '..'))
sys.path.insert(0, root_dir)

# Script config directory
sys.path.insert(0, os.path.join(scripts_dir, 'conf'))

import django
from django.core.management import call_command


if __name__ == '__main__':
    os.chdir(root_dir)

    # Verify that we have npm.
    npm_command = 'npm'

    try:
        subprocess.check_call([npm_command, '--version'],
                              stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        raise RuntimeError(
            f'Unable to locate {npm_command} in the path, which is needed to '
            f'compile static media.'
        )

    # Install dependencies.
    subprocess.call([npm_command, 'install'])

    # Set up the Django environment.
    os.environ['FORCE_BUILD_MEDIA'] = '1'
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reviewboard.settings')

    django.setup()

    # Check if we're actually building media. This internal flag is used to
    # by the package build backend to better control setup vs. building of
    # static media.
    if os.environ.get('RUN_COLLECT_STATIC') != '0':
        # Remove any stale htdocs files.
        htdocs_static_dir = os.path.join(root_dir, 'reviewboard', 'htdocs',
                                         'static')

        if os.path.exists(htdocs_static_dir):
            shutil.rmtree(htdocs_static_dir)

        # Build the static media.
        #
        # This will raise a CommandError or call sys.exit(1) on failure.
        call_command('collectstatic', interactive=False, verbosity=2)
