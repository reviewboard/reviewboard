from __future__ import unicode_literals

from reviewboard.scmtools.core import ChangeSet
from reviewboard.testing.testcase import TestCase


class CoreTests(TestCase):
    """Tests for the scmtools.core module"""

    def test_empty_changeset(self):
        """Testing ChangeSet defaults"""
        cs = ChangeSet()
        self.assertEqual(cs.changenum, None)
        self.assertEqual(cs.summary, '')
        self.assertEqual(cs.description, '')
        self.assertEqual(cs.branch, '')
        self.assertTrue(len(cs.bugs_closed) == 0)
        self.assertTrue(len(cs.files) == 0)
