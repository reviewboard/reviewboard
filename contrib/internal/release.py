#!/usr/bin/env python
#
# Performs a release of Review Board. This can only be run by the core
# developers with release permissions.
#

import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from reviewboard import get_package_version, is_release, VERSION


PY_VERSIONS = ["2.4", "2.5", "2.6"]

LATEST_PY_VERSION = PY_VERSIONS[-1]

PACKAGE_NAME = 'ReviewBoard'

RELEASES_URL = \
    'review-board.org:/var/www/downloads.review-board.org/' \
    'htdocs/releases/%s/%s.%s/' % (PACKAGE_NAME, VERSION[0], VERSION[1])


built_files = []


def execute(cmdline):
    print ">>> %s" % cmdline

    if os.system(cmdline) != 0:
        print "!!! Error invoking command."
        sys.exit(1)


def run_setup(target, pyver = LATEST_PY_VERSION):
    execute("python%s ./setup.py release %s" % (pyver, target))


def clean():
    execute("rm -rf build dist")


def build_targets():
    for pyver in PY_VERSIONS:
        run_setup("bdist_egg", pyver)
        built_files.append("dist/%s-%s-py%s.egg" %
                           (PACKAGE_NAME, get_package_version(), pyver))

    run_setup("sdist")
    built_files.append("dist/%s-%s.tar.gz" %
                       (PACKAGE_NAME, get_package_version()))


def upload_files():
    execute("scp %s %s" % (" ".join(built_files), RELEASES_URL))


def tag_release():
    execute("git tag release-%s" % get_package_version())


def register_release():
    run_setup("register")


def main():
    if not os.path.exists("setup.py"):
        sys.stderr.write("This must be run from the root of the "
                         "Review Board tree.\n")
        sys.exit(1)

    if not is_release():
        sys.stderr.write("This version is not listed as a release.\n")
        sys.exit(1)

    clean()
    build_targets()
    upload_files()
    tag_release()

    if VERSION[3] == 'final':
        register_release()


if __name__ == "__main__":
    main()
