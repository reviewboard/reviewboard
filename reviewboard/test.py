"""Test runner for the Review Board test suite.

This is used by :file:`manage.py` or when running ``./tests/runtests.py`` from
the top of the source tree.
"""

from __future__ import unicode_literals

import os
import sys

from django.conf import settings
from djblets.testing.testrunners import TestRunner


class RBTestRunner(TestRunner):
    """Test runner for the Review Board and related test suites."""

    cover_packages = settings.TEST_PACKAGES
    test_packages = settings.TEST_PACKAGES

    needs_collect_static = True

    def run_tests(self, *args, **kwargs):
        """Run the test suite.

        This is a light wrapper around
        :py:meth:`~djblets.testing.testrunners.TestRunner.run_tests` that
        just checks for deprecated options. See that method for arguments.

        Args:
            *args (tuple, unused):
                Positional arguments for the test runner.

            **kwargs (dict, unused):
                Keyword arguments for the test runner.

        Returns:
            int:
            The exit code. 0 means all tests passed, while 1 means there were
            failures.
        """
        if '--with-profiling' in sys.argv:
            sys.stderr.write('--with-profiling is no longer supported. Use '
                             '--with-profile instead.\n')
            sys.exit(1)

        return super(RBTestRunner, self).run_tests(*args, **kwargs)

    def setup_dirs(self):
        settings.SITE_DATA_DIR = os.path.join(self.tempdir, 'data')
        images_dir = os.path.join(settings.MEDIA_ROOT, 'uploaded', 'images')

        return super(RBTestRunner, self).setup_dirs() + [
            settings.SITE_DATA_DIR,
            images_dir,
        ]
