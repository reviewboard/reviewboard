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

from __future__ import unicode_literals

import os
import stat
import sys
import tempfile

import nose
from django.core.management import execute_from_command_line
from django.test.simple import DjangoTestSuiteRunner

try:
    # Make sure to pre-load all the image handlers. If we do this later during
    # unit tests, we don't seem to always get our list, causing tests to fail.
    from PIL import Image
    Image.init()
except ImportError:
    try:
        import Image
        Image.init()
    except ImportError:
        pass

from django.conf import settings
from djblets.cache.serials import generate_media_serial


class RBTestRunner(DjangoTestSuiteRunner):
    def setup_test_environment(self, *args, **kwargs):
        super(RBTestRunner, self).setup_test_environment(*args, **kwargs)

        # Default to testing in a non-subdir install.
        settings.SITE_ROOT = "/"

        settings.AJAX_SERIAL = 123
        settings.TEMPLATE_SERIAL = 123
        settings.STATIC_URL = settings.SITE_ROOT + 'static/'
        settings.MEDIA_URL = settings.SITE_ROOT + 'media/'
        settings.PASSWORD_HASHERS = (
            'django.contrib.auth.hashers.SHA1PasswordHasher',
        )
        settings.RUNNING_TEST = True
        os.environ[b'RB_RUNNING_TESTS'] = b'1'

        self._setup_media_dirs()

    def teardown_test_environment(self, *args, **kwargs):
        self._destroy_media_dirs()
        super(RBTestRunner, self).teardown_test_environment(*args, **kwargs)

    def run_tests(self, test_labels, extra_tests=None, **kwargs):
        if '--with-profiling' in sys.argv:
            sys.stderr.write('--with-profiling is no longer supported. Use '
                             '--with-profile instead.\n')
            sys.exit(1)

        self.setup_test_environment()
        old_config = self.setup_databases()

        self.nose_argv = [
            sys.argv[0],
            '-v',
            '--match=^test',
            '--with-id',
            '--with-doctest',
            '--doctest-extension=.txt',
        ]

        if '--with-coverage' in sys.argv:
            self.nose_argv += ['--with-coverage',
                               '--cover-package=reviewboard']
            sys.argv.remove('--with-coverage')

        for package in settings.TEST_PACKAGES:
            self.nose_argv.append('--where=%s' % package)

        # If the test files are executable on the file system, nose will need
        # the --exe argument to run them
        known_file = os.path.join(os.path.dirname(__file__), 'settings.py')

        if (os.path.exists(known_file) and
            os.stat(known_file).st_mode & stat.S_IXUSR):
            self.nose_argv.append('--exe')

        # manage.py captures everything before "--"
        if len(sys.argv) > 2 and '--' in sys.argv:
            self.nose_argv += sys.argv[(sys.argv.index("--") + 1):]

        self.run_nose()

        self.teardown_databases(old_config)
        self.teardown_test_environment()

        if self.result.success:
            return 0
        else:
            return 1

    def run_nose(self):
        self.result = nose.main(argv=self.nose_argv, exit=False)

    def _setup_media_dirs(self):
        self.tempdir = tempfile.mkdtemp(prefix='rb-tests-')

        # Don't go through Pipeline for everything, since we're not
        # triggering pipelining of our media.
        settings.STATICFILES_STORAGE = \
            'django.contrib.staticfiles.storage.StaticFilesStorage'

        if os.path.exists(self.tempdir):
            self._destroy_media_dirs()

        settings.STATIC_ROOT = os.path.join(self.tempdir, 'static')
        settings.MEDIA_ROOT = os.path.join(self.tempdir, 'media')
        settings.SITE_DATA_DIR = os.path.join(self.tempdir, 'data')
        images_dir = os.path.join(settings.MEDIA_ROOT, "uploaded", "images")
        legacy_extensions_media = os.path.join(settings.MEDIA_ROOT, 'ext')
        extensions_media = os.path.join(settings.STATIC_ROOT, 'ext')

        for dirname in (images_dir, legacy_extensions_media, extensions_media):
            if not os.path.exists(dirname):
                os.makedirs(dirname)

        # Collect all static media needed for tests, including web-based tests.
        execute_from_command_line([
            __file__, 'collectstatic', '--noinput', '-v', '0',
        ])

        generate_media_serial()

    def _destroy_media_dirs(self):
        for root, dirs, files in os.walk(self.tempdir, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))

            for name in dirs:
                path = os.path.join(root, name)

                if os.path.islink(path):
                    os.remove(path)
                else:
                    os.rmdir(path)

        os.rmdir(self.tempdir)
