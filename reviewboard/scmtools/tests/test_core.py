from __future__ import unicode_literals

from reviewboard.scmtools.core import ChangeSet, Commit
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


class CommitTests(TestCase):
    """Tests for reviewboard.scmtools.core.Commit"""

    def test_diff_byte_string(self):
        """Testing Commit initialization with diff as byte string"""
        commit = Commit(diff=b'hi \xe2\x80\xa6 there')

        self.assertIsInstance(commit.diff, bytes)
        self.assertEqual(commit.diff, b'hi \xe2\x80\xa6 there')
