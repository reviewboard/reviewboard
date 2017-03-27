from __future__ import unicode_literals

from reviewboard.diffviewer.myersdiff import MyersDiffer
from reviewboard.testing import TestCase


class MyersDifferTest(TestCase):
    def test_diff(self):
        """Testing MyersDiffer"""
        self._test_diff(["1", "2", "3"],
                        ["1", "2", "3"],
                        [("equal", 0, 3, 0, 3), ])

        self._test_diff(["1", "2", "3"],
                        [],
                        [("delete", 0, 3, 0, 0), ])

        self._test_diff("1\n2\n3\n",
                        "0\n1\n2\n3\n",
                        [("insert", 0, 0, 0, 2),
                         ("equal", 0, 6, 2, 8)])

        self._test_diff("1\n2\n3\n7\n",
                        "1\n2\n4\n5\n6\n7\n",
                        [("equal", 0, 4, 0, 4),
                         ("replace", 4, 5, 4, 5),
                         ("insert", 5, 5, 5, 9),
                         ("equal", 5, 8, 9, 12)])

    def _test_diff(self, a, b, expected):
        opcodes = list(MyersDiffer(a, b).get_opcodes())
        self.assertEqual(opcodes, expected)
