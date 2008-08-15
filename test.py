#
# test.py -- Nose based tester
#
# Copyright (c) 2007  David Trowbridge
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

import os.path
import sys

import nose

try:
    # Make sure to pre-load all the image handlers. If we do this later during
    # unit tests, we don't seem to always get our list, causing tests to fail.
    from PIL import Image
    Image.init()
except ImportError:
    pass

from django.conf import settings
from django.core import management
from django.test.utils import setup_test_environment, teardown_test_environment

# XXX Switch to using connection.creation.* directly once we require
#     Django 1.0 beta 1.
try:
    from django.test.utils import create_test_db, destroy_test_db
except ImportError:
    from django.db import connection
    create_test_db = connection.creation.create_test_db
    destroy_test_db = connection.creation.destroy_test_db


def runner(module_list, verbosity=1, interactive=True, extra_tests=[]):
    setup_test_environment()
    settings.DEBUG = False

    # Default to testing in a non-subdir install.
    settings.SITE_ROOT = "/"
    settings.MEDIA_ROOT = "/tmp/reviewboard-tests"

    images_dir = os.path.join(settings.MEDIA_ROOT, "uploaded", "images")

    if not os.path.exists(images_dir):
        os.makedirs(images_dir)

    settings.MEDIA_URL = settings.SITE_ROOT + 'media/'
    settings.ADMIN_MEDIA_PREFIX = settings.MEDIA_URL + 'admin/'

    old_name = settings.DATABASE_NAME
    create_test_db(verbosity, autoclobber=not interactive)
    management.call_command('syncdb', verbosity=verbosity, interactive=interactive)

    # Nose uses all local modules, which is really silly.  These were getting
    # tested (and failing), so turn them off.
    exclusion = '|'.join(['setup_test_environment',
                          'teardown_test_environment',
                          'create_test_db',
                          'destroy_test_db'])

    nose_argv=['test.py', '-v',
               '--with-coverage',
               '--with-doctest', '--doctest-extension=.txt',
               '-e', exclusion]

    for cover in ['reviewboard', 'djblets']:
        nose_argv += ['--cover-package=' + cover]

    if len(sys.argv) > 2:
        nose_argv += sys.argv[2:]
    nose.main(argv=nose_argv)

    for root, dirs, files in os.walk(settings.MEDIA_ROOT, topdown=False):
        for name in files:
            os.remove(os.path.join(root, name))

        for name in dirs:
            os.rmdir(os.path.join(root, name))

    destroy_test_db(old_name, verbosity)
    teardown_test_environment()
