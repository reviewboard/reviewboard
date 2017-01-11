"""Tests for top level Review Board modules."""

from __future__ import unicode_literals

import os

from django.utils import six
from djblets.staticbundles import (
    PIPELINE_JAVASCRIPT as DJBLETS_PIPELINE_JAVASCRIPT,
    PIPELINE_STYLESHEETS as DJBLETS_PIPELINE_STYLESHEETS)

from reviewboard.staticbundles import PIPELINE_JAVASCRIPT, PIPELINE_STYLESHEETS
from reviewboard.testing import TestCase


class StaticBundlesTests(TestCase):
    """Tests the static bundles in reviewboard.staticbundles."""

    def _check_file_groups(self, groups, exclude):
        """Checks that all source files in the given groups exist.

        Args:
            groups (dict):
                The groups to check.

            exclude (list):
                List of group names to exclude from the check.
        """
        missing = set()

        for name, group in six.iteritems(groups):
            if name in exclude:
                continue

            for path in group['source_filenames']:
                static_path = os.path.join('reviewboard', 'static', path)

                if not os.path.exists(static_path):
                    missing.add(path)

        self.assertSetEqual(missing, set())

    def test_static_javascript_files(self):
        """Testing that all static javascript files exist"""
        self._check_file_groups(PIPELINE_JAVASCRIPT,
                                DJBLETS_PIPELINE_JAVASCRIPT.keys())

    def test_static_stylesheet_files(self):
        """Testing that all static stylesheet files exist"""
        self._check_file_groups(PIPELINE_STYLESHEETS,
                                DJBLETS_PIPELINE_STYLESHEETS.keys())
