#!/usr/bin/env python
#
# Utility script to run pyflakes with the modules we care about and
# exclude errors we know to be fine.

import os
import subprocess
import sys


module_exclusions = [
    'djblets',
    'django_evolution',
    'dist',
    'ez_setup.py',
    'settings_local.py',
    'ReviewBoard.egg-info',
]


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
    fp = open(os.path.join(cur_dir, "pyflakes.exclude"), "r")

    for line in fp.readlines():
        exclusions[line.rstrip()] = 1

    fp.close()

    # Now filter thin
    for line in contents:
        line = line.rstrip()
        if line not in exclusions:
            print line


if __name__ == "__main__":
    main()
