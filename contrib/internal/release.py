#!/usr/bin/env python
#
# Performs a release of Review Board. This can only be run by the core
# developers with release permissions.
#

from __future__ import print_function, unicode_literals

import os
import sys

from beanbag_tools.utils.builds import build_checksums
from beanbag_tools.utils.builds_python import (python_build_releases,
                                               python_check_can_release)
from beanbag_tools.utils.git import (git_get_tag_sha, git_tag_release,
                                     git_use_clone)
from beanbag_tools.utils.pypi import pypi_register_release
from beanbag_tools.utils.rbwebsite import (rbwebsite_load_config,
                                           rbwebsite_register_release)
from beanbag_tools.utils.s3 import s3_upload_files

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from reviewboard import __version__, __version_info__, is_release


PY_VERSIONS = ["2.6", "2.7"]

PACKAGE_NAME = 'ReviewBoard'

RELEASES_BUCKET_NAME = 'downloads.reviewboard.org'
RELEASES_BUCKET_KEY = '/releases/%s/%s.%s/' % (PACKAGE_NAME,
                                               __version_info__[0],
                                               __version_info__[1])


def build_settings():
    with open('settings_local.py', 'w') as f:
        f.write('DATABASES = {\n')
        f.write('    "default": {\n')
        f.write('        "ENGINE": "django.db.backends.sqlite3",\n')
        f.write('        "NAME": "reviewboard.db",\n')
        f.write('    }\n')
        f.write('}\n\n')
        f.write('PRODUCTION = True\n')
        f.write('DEBUG = False\n')


def build_targets():
    built_files = python_build_releases(PACKAGE_NAME, __version__, PY_VERSIONS)
    built_files += build_checksums(PACKAGE_NAME, __version__, built_files)

    return built_files


def register_release():
    if __version_info__[4] == 'final':
        pypi_register_release()

    scm_revision = git_get_tag_sha('release-%s' % __version__)
    rbwebsite_register_release(__version_info__, scm_revision)


def main():
    python_check_can_release(is_release())

    rbwebsite_load_config()

    with git_use_clone('.'):
        build_settings()
        built_files = build_targets()
        s3_upload_files(RELEASES_BUCKET_NAME, RELEASES_BUCKET_KEY, built_files,
                        build_index=True)

    git_tag_release(__version__)
    register_release()


if __name__ == "__main__":
    main()
