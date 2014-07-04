#!/usr/bin/env python
#
# Utility script to run pyflakes with the modules we care about and
# exclude errors we know to be fine.

from __future__ import print_function, unicode_literals

import os
import re
import subprocess
import sys


module_exclusions = (
    'build',
    'djblets',
    'django_evolution',
    'dist',
    'ez_setup.py',
    'fabfile.py',
    'settings_local.py',
    'reviewboard/htdocs',
    'ReviewBoard.egg-info',
)


def scan_for_modules():
    return [entry
            for entry in os.listdir(os.getcwd())
            if ((os.path.isdir(entry) or entry.endswith(".py")) and
                entry not in module_exclusions)]


def main():
    cur_dir = os.path.dirname(__file__)
    os.chdir(os.path.join(cur_dir, "..", ".."))
    modules = sys.argv[1:]

    if not modules:
        # The user didn't specify anything specific. Scan for modules.
        modules = scan_for_modules()

    p = subprocess.Popen(['pyflakes'] + modules,
                         stderr=subprocess.PIPE,
                         stdout=subprocess.PIPE,
                         close_fds=True)

    contents = p.stdout.readlines()

    # Read in the exclusions file
    exclusions = {}
    with open(os.path.join(cur_dir, "pyflakes.exclude"), "r") as fp:
        for line in fp:
            if not line.startswith("#"):
                exclusions[line.rstrip()] = 1

    # Now filter things
    for line in contents:
        line = line.rstrip()
        test_line = re.sub(r':[0-9]+:', r':*:', line, 1)
        test_line = re.sub(r'line [0-9]+', r'line *', test_line)

        if (test_line not in exclusions and
            not test_line.startswith(module_exclusions)):
            print(line)


if __name__ == "__main__":
    main()
