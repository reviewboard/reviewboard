#!/usr/bin/env python

import os
import sys
sys.path.insert(0, os.path.join(__file__, "..", ".."))
sys.path.insert(0, os.path.dirname(__file__))

from reviewboard import settings
from django.core.management import execute_manager, setup_environ
setup_environ(settings)


def scan_resource(resource):
    for child in resource.item_child_resources:
        scan_resource(child)

    for child in resource.list_child_resources:
        scan_resource(child)


if __name__ == "__main__":
    execute_manager(settings)
