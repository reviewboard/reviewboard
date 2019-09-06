#!/usr/bin/env python

from __future__ import unicode_literals

import os
import sys

scripts_dir = os.path.abspath(os.path.dirname(__file__))

# Source root directory
sys.path.insert(0, os.path.abspath(os.path.join(scripts_dir, '..', '..')))

# Script config directory
sys.path.insert(0, os.path.join(scripts_dir, 'conf'))

from reviewboard.dependencies import django_version

import __main__
__main__.__requires__ = ['Django' + django_version]
import pkg_resources

import django
from django.core.management import call_command


if __name__ == '__main__':
    os.putenv(str('FORCE_BUILD_MEDIA'), str('1'))
    os.environ.setdefault(str('DJANGO_SETTINGS_MODULE'),
                          str('reviewboard.settings'))

    if hasattr(django, 'setup'):
        # Django >= 1.7
        django.setup()

    # This will raise a CommandError or call sys.exit(1) on failure.
    call_command('collectstatic', interactive=False, verbosity=2)
