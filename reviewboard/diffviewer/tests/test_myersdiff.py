from __future__ import unicode_literals

from reviewboard.diffviewer.myersdiff import MyersDiffer
from reviewboard.testing import TestCase


class MyersDifferTest(TestCase):
    """Unit tests for MyersDiffer."""

    def test_equals(self):
        """Testing MyersDiffer with equal chunk"""
        self._test_diff(['1', '2', '3'],
                        ['1', '2', '3'],
                        [('equal', 0, 3, 0, 3), ])

    def test_delete(self):
        """Testing MyersDiffer with delete chunk"""
        self._test_diff(['1', '2', '3'],
                        [],
                        [('delete', 0, 3, 0, 0), ])

    def test_insert_before_lines(self):
        """Testing MyersDiffer with insert before existing lines"""
        self._test_diff('1\n2\n3\n',
                        '0\n1\n2\n3\n',
                        [('insert', 0, 0, 0, 2),
                         ('equal', 0, 6, 2, 8)])

    def test_replace_insert_between_lines(self):
        """Testing MyersDiffer with replace and insert between existing lines
        """
        self._test_diff('1\n2\n3\n7\n',
                        '1\n2\n4\n5\n6\n7\n',
                        [('equal', 0, 4, 0, 4),
                         ('replace', 4, 5, 4, 5),
                         ('insert', 5, 5, 5, 9),
                         ('equal', 5, 8, 9, 12)])

    def _test_diff(self, a, b, expected):
        opcodes = list(MyersDiffer(a, b).get_opcodes())
        self.assertEqual(opcodes, expected)
