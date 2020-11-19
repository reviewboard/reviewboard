"""Unit tests for ClearCase support."""

from __future__ import unicode_literals

from django.test.utils import override_settings

from reviewboard.scmtools import clearcase
from reviewboard.scmtools.clearcase import get_cleartool
from reviewboard.scmtools.tests.testcases import SCMTestCase


class ClearCaseTests(SCMTestCase):
    """Unit tests for ClearCase support."""

    def setUp(self):
        """Initialize test cases."""
        super(ClearCaseTests, self).setUp()

        # Reset global to prevent cross-test pollution.
        clearcase._cleartool = None

    def test_get_cleartool_default(self):
        """Testing get_cleartool default"""
        self.assertEqual(get_cleartool(), 'cleartool')

    @override_settings(CC_CTEXEC='')
    def test_get_cleartool_blank(self):
        """Testing get_cleartool with empty setting"""
        self.assertEqual(get_cleartool(), 'cleartool')

    @override_settings(CC_CTEXEC='/usr/local/bin/cleartool')
    def test_get_cleartool_custom(self):
        """Testing get_cleartool with custom setting"""
        self.assertEqual(get_cleartool(), '/usr/local/bin/cleartool')
