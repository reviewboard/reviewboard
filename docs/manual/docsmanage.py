#!/usr/bin/env python

import os
import sys
sys.path.insert(0, os.path.join(__file__, '..', '..'))
sys.path.insert(0, os.path.dirname(__file__))

from django.core.management import execute_from_command_line
from reviewboard import finalize_setup


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reviewboard.settings')


def scan_resource(resource):
    for child in resource.item_child_resources:
        scan_resource(child)

    for child in resource.list_child_resources:
        scan_resource(child)


if __name__ == '__main__':
    if sys.argv[1] == 'createdb':
        execute_from_command_line([sys.argv[0]] +
                                  ['evolve', '--noinput', '--execute'])
        finalize_setup(register_scmtools=False)
    else:
        execute_from_command_line()
