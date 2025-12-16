#!/usr/bin/env python

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import django
from django.core.management import CommandError, call_command
from pipeline.exceptions import CompilerError


scripts_dir = os.path.abspath(os.path.dirname(__file__))

# Source root directory
root_dir = os.path.abspath(os.path.join(scripts_dir, '..', '..'))
sys.path.insert(0, root_dir)

# Script config directory
sys.path.insert(0, os.path.join(scripts_dir, 'conf'))


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

        from django.conf import settings

        jquery_ui_dir: (Path | None) = None

        for node_path in settings.NODE_PATH.split(':'):
            jquery_ui = Path(node_path) / 'jquery-ui'

            if jquery_ui.is_dir():
                jquery_ui_dir = jquery_ui

        # We currently bundle jquery-ui.css out of the base theme. This
        # stylesheet references a few images, which need to be collected.
        #
        # This can go away once we get rid of our jquery-ui dependency.
        assert jquery_ui_dir is not None
        jquery_ui_images = \
            jquery_ui_dir / 'dist' / 'themes' / 'base' / 'images'

        settings.STATICFILES_FINDERS.append(
            'django.contrib.staticfiles.finders.FileSystemFinder',
        )

        # We completely override STATICFILES_DIRS in this case because we don't
        # want warnings about duplicate files between the regular finders and
        # the FileSystemFinder.
        settings.STATICFILES_DIRS = [
            ('lib/css/images', str(jquery_ui_images)),
        ]

        # Build the static media.
        #
        # This will raise a CommandError or call sys.exit(1) on failure.
        try:
            call_command('collectstatic', interactive=False, verbosity=2)
        except CompilerError as e:
            sys.stderr.write(e.error_output)
            sys.stderr.write('\n')

            raise CommandError('Failed to build static media')
