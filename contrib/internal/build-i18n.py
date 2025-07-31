#!/usr/bin/env python

import os
import sys

scripts_dir = os.path.abspath(os.path.dirname(__file__))

# Source root directory
sys.path.insert(0, os.path.abspath(os.path.join(scripts_dir, '..', '..')))

# Script config directory
sys.path.insert(0, os.path.join(scripts_dir, 'conf'))

import django
from django.core.management import call_command

import reviewboard


if __name__ == '__main__':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reviewboard.settings')

    django.setup()

    os.chdir(os.path.dirname(reviewboard.__file__))
    sys.exit(call_command('compilemessages', verbosity=2))
