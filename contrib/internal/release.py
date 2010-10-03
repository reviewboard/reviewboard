#!/usr/bin/env python
#
# Performs a release of Review Board. This can only be run by the core
# developers with release permissions.
#

import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from reviewboard import __version__, __version_info__, is_release


PY_VERSIONS = ["2.4", "2.5", "2.6", "2.7"]

LATEST_PY_VERSION = PY_VERSIONS[-1]

PACKAGE_NAME = 'ReviewBoard'

RELEASES_URL = \
    'reviewboard.org:/var/www/downloads.reviewboard.org/' \
    'htdocs/releases/%s/%s.%s/' % (PACKAGE_NAME,
                                   __version_info__[0],
                                   __version_info__[1])


built_files = []


def execute(cmdline):
    print ">>> %s" % cmdline

    if os.system(cmdline) != 0:
        print "!!! Error invoking command."
        sys.exit(1)


def run_setup(target, pyver=LATEST_PY_VERSION):
    execute("python%s ./setup.py release %s" % (pyver, target))


def clone_git_tree(git_dir):
    new_git_dir = tempfile.mkdtemp(prefix='reviewboard-release.')

    os.chdir(new_git_dir)
    execute('git clone %s .' % git_dir)

    return new_git_dir


def build_targets():
    for pyver in PY_VERSIONS:
        run_setup("bdist_egg", pyver)
        built_files.append("dist/%s-%s-py%s.egg" %
                           (PACKAGE_NAME, __version__, pyver))

    run_setup("sdist")
    built_files.append("dist/%s-%s.tar.gz" %
                       (PACKAGE_NAME, __version__))


def upload_files():
    execute("scp %s %s" % (" ".join(built_files), RELEASES_URL))


def tag_release():
    execute("git tag release-%s" % __version__)


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

    cur_dir = os.getcwd()
    git_dir = clone_git_tree(cur_dir)

    build_targets()
    upload_files()

    os.chdir(cur_dir)
    shutil.rmtree(git_dir)

    tag_release()

    if __version_info__[4] == 'final':
        register_release()


if __name__ == "__main__":
    main()
