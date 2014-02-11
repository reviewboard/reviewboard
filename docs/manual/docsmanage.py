#!/usr/bin/env python

import os
import sys
sys.path.insert(0, os.path.join(__file__, "..", ".."))
sys.path.insert(0, os.path.dirname(__file__))

from django.core.management import execute_from_command_line


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reviewboard.settings')


def scan_resource(resource):
    for child in resource.item_child_resources:
        scan_resource(child)

    for child in resource.list_child_resources:
        scan_resource(child)


if __name__ == "__main__":
    execute_from_command_line()
