#!/usr/bin/env python

from __future__ import unicode_literals

import os
import sys

scripts_dir = os.path.abspath(os.path.dirname(__file__))

# Source root directory
sys.path.insert(0, os.path.abspath(os.path.join(scripts_dir, '..', '..')))

# Script config directory
sys.path.insert(0, os.path.join(scripts_dir, 'conf'))

from reviewboard import django_version

import __main__
__main__.__requires__ = [django_version]
import pkg_resources

from django.core.management import call_command


if __name__ == '__main__':
    os.putenv('FORCE_BUILD_MEDIA', '1')
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reviewboard.settings')

    ret = call_command('collectstatic', interactive=False, verbosity=2)
    sys.exit(ret)
