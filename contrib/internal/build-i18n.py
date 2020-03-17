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
__main__.__requires__ = ['Django%s' % django_version]
import pkg_resources

import django
from django.core.management import call_command

import reviewboard


if __name__ == '__main__':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reviewboard.settings')

    if hasattr(django, 'setup'):
        # Django >= 1.7
        django.setup()

    os.chdir(os.path.dirname(reviewboard.__file__))
    sys.exit(call_command('compilemessages', interactive=False, verbosity=2))
