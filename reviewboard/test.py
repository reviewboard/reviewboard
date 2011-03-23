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

import os
import platform
import shutil
import sys
import tempfile

import pkg_resources
import nose

try:
    # Make sure to pre-load all the image handlers. If we do this later during
    # unit tests, we don't seem to always get our list, causing tests to fail.
    from PIL import Image
    Image.init()
except ImportError:
    try:
        from Image import Image
        Image.init()
    except ImportError:
        pass

from django.conf import settings
from django.core import management
from django.db import connection
from django.test.utils import setup_test_environment, teardown_test_environment
from djblets.util.misc import generate_media_serial


def setup_media_dirs():
    settings.MEDIA_ROOT = tempfile.mkdtemp(prefix='rb-tests-')

    if os.path.exists(settings.MEDIA_ROOT):
        destroy_media_dirs()

    images_dir = os.path.join(settings.MEDIA_ROOT, "uploaded", "images")

    if not os.path.exists(images_dir):
        os.makedirs(images_dir)

    # Set up symlinks to the other directories for the web-based tests
    bundled_media_dir = os.path.join(os.path.dirname(__file__),
                                     'htdocs', 'media')

    for path in os.listdir(bundled_media_dir):
        if path == 'uploaded':
            continue

        if not hasattr(os, 'symlink'):
            shutil.copytree(os.path.join(bundled_media_dir, path),
                            os.path.join(settings.MEDIA_ROOT, path))
        else:
            os.symlink(os.path.join(bundled_media_dir, path),
                       os.path.join(settings.MEDIA_ROOT, path))

    if not os.path.exists(os.path.join(settings.MEDIA_ROOT, 'djblets')):
        if not pkg_resources.resource_exists("djblets", "media"):
            sys.stderr.write("Unable to find a valid Djblets installation.\n")
            sys.stderr.write("Make sure you've installed Djblets.")
            sys.exit(1)

        src_dir = pkg_resources.resource_filename('djblets', 'media')
        dest_dir = os.path.join(settings.MEDIA_ROOT, 'djblets')

        if platform.system() == 'windows':
            shutil.copytree(src_dir, dest_dir)
        else:
            try:
                os.symlink(src_dir, dest_dir)
            except OSError:
                pass

    generate_media_serial()


def destroy_media_dirs():
    for root, dirs, files in os.walk(settings.MEDIA_ROOT, topdown=False):
        for name in files:
            os.remove(os.path.join(root, name))

        for name in dirs:
            path = os.path.join(root, name)

            if os.path.islink(path):
                os.remove(path)
            else:
                os.rmdir(path)

    os.rmdir(settings.MEDIA_ROOT)


def runner(module_list, verbosity=1, interactive=True, extra_tests=[]):
    setup_test_environment()
    settings.DEBUG = False

    # Default to testing in a non-subdir install.
    settings.SITE_ROOT = "/"

    settings.MEDIA_URL = settings.SITE_ROOT + 'media/'
    settings.ADMIN_MEDIA_PREFIX = settings.MEDIA_URL + 'admin/'
    settings.RUNNING_TEST = True

    setup_media_dirs()

    old_name = settings.DATABASE_NAME
    connection.creation.create_test_db(verbosity, autoclobber=not interactive)
    management.call_command('syncdb', verbosity=verbosity, interactive=interactive)

    # Nose uses all local modules, which is really silly.  These were getting
    # tested (and failing), so turn them off.
    exclusion = '|'.join(['setup_test_environment',
                          'teardown_test_environment'])

    nose_argv = ['test.py', '-v',
                 '--with-doctest', '--doctest-extension=.txt',
                 '-e', exclusion]

    if '--with-coverage' in sys.argv:
        nose_argv += ['--with-coverage',
                      '--cover-package=reviewboard']
        sys.argv.remove('--with-coverage')

    for package in settings.TEST_PACKAGES:
        nose_argv.append('--where=%s' % package)

    if '--with-webtests' in sys.argv:
        nose_argv.append('--where=webtests')
        sys.argv.remove('--with-webtests')

    # manage.py captures everything before "--"
    if len(sys.argv) > 2 and sys.argv.__contains__("--"):
        nose_argv += sys.argv[(sys.argv.index("--") + 1):]

    nose.main(argv=nose_argv, exit=False)

    destroy_media_dirs()

    connection.creation.destroy_test_db(old_name, verbosity=0)
    teardown_test_environment()
