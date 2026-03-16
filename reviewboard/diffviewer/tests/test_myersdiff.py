"""Unit tests for MyersDiffer."""

from __future__ import annotations

from typing import TYPE_CHECKING

from reviewboard.diffviewer.myersdiff import MyersDiffer
from reviewboard.testing import TestCase

if TYPE_CHECKING:
    from collections.abc import Sequence

    from reviewboard.diffviewer.differ import DiffOpcode


class MyersDifferTest(TestCase):
    """Unit tests for MyersDiffer."""

    def test_equals(self) -> None:
        """Testing MyersDiffer with equal chunk"""
        self._test_diff(
            ['1', '2', '3'],
            ['1', '2', '3'],
            [
                ('equal', 0, 3, 0, 3),
            ])

    def test_delete(self) -> None:
        """Testing MyersDiffer with delete chunk"""
        self._test_diff(
            ['1', '2', '3'],
            [],
            [
                ('delete', 0, 3, 0, 0),
            ])

    def test_insert_before_lines(self) -> None:
        """Testing MyersDiffer with insert before existing lines"""
        self._test_diff(
            '1\n2\n3\n',
            '0\n1\n2\n3\n',
            [
                ('insert', 0, 0, 0, 2),
                ('equal', 0, 6, 2, 8),
            ])

    def test_replace_insert_between_lines(self) -> None:
        """Testing MyersDiffer with replace and insert between existing lines
        """
        self._test_diff(
            '1\n2\n3\n7\n',
            '1\n2\n4\n5\n6\n7\n',
            [
                ('equal', 0, 4, 0, 4),
                ('replace', 4, 5, 4, 5),
                ('insert', 5, 5, 5, 9),
                ('equal', 5, 8, 9, 12),
            ])

    def _test_diff(
        self,
        a: str | list[str],
        b: str | list[str],
        expected: Sequence[DiffOpcode],
    ) -> None:
        """Perform a specific test case.

        Args:
            a (str or list of str):
                The contents of the original version of the file.

            b (str or list of str):
                The contents of the modified version of the file.

            expected (list of reviewboard.diffviewer.differ.DiffOpcode):
                The expected opcodes.
        """
        opcodes = list(MyersDiffer(a, b).get_opcodes())
        self.assertEqual(opcodes, expected)
