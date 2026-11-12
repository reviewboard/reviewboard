"""Unit tests for reviewboard.reviews.markdown_lists.

Version Added:
    9.0
"""

from __future__ import annotations

from reviewboard.reviews.markdown_lists import normalize_list_indentation
from reviewboard.testing import TestCase


class NormalizeListIndentationTests(TestCase):
    """Unit tests for normalize_list_indentation.

    Version Added:
        9.0
    """

    def _normalize(
        self,
        text: str,
    ) -> str:
        """Return normalized Markdown text.

        Args:
            text (str):
                The Markdown text.

        Returns:
            str:
            The normalized text.
        """
        return '\n'.join(normalize_list_indentation(text.split('\n')))

    def test_two_space_nesting(self) -> None:
        """Testing normalize_list_indentation with 2-space nested items"""
        self.assertEqual(
            self._normalize('- a\n'
                            '  - b\n'
                            '    - c\n'
                            '- d'),
            '- a\n'
            '    - b\n'
            '        - c\n'
            '- d')

    def test_ordered_list_content(self) -> None:
        """Testing normalize_list_indentation with content under "1." items
        """
        self.assertEqual(
            self._normalize('1. a\n'
                            '\n'
                            '   ```sh\n'
                            '   echo hi\n'
                            '   ```\n'
                            '\n'
                            '2. b'),
            '1. a\n'
            '\n'
            '    ```sh\n'
            '    echo hi\n'
            '    ```\n'
            '\n'
            '2. b')

    def test_four_space_nesting(self) -> None:
        """Testing normalize_list_indentation keeps 4-space nesting"""
        self.assertEqual(
            self._normalize('- a\n'
                            '    - b'),
            '- a\n'
            '    - b')

    def test_indented_code(self) -> None:
        """Testing normalize_list_indentation leaves indented code alone"""
        text = (
            '    - a\n'
            '      - b'
        )

        self.assertEqual(self._normalize(text), text)

    def test_fenced_code(self) -> None:
        """Testing normalize_list_indentation leaves fenced code alone"""
        text = (
            '```\n'
            '- a\n'
            '  - b\n'
            '> - c\n'
            '>   - d\n'
            '```'
        )

        self.assertEqual(self._normalize(text), text)

    def test_blockquote(self) -> None:
        """Testing normalize_list_indentation with lists in a blockquote"""
        self.assertEqual(
            self._normalize('> - a\n'
                            '>   - b\n'
                            '\n'
                            '- c\n'
                            '  - d'),
            '> - a\n'
            '>     - b\n'
            '\n'
            '- c\n'
            '    - d')

    def test_blockquote_after_list(self) -> None:
        """Testing normalize_list_indentation with a blockquote closing a
        list
        """
        self.assertEqual(
            self._normalize('- a\n'
                            '  - b\n'
                            '\n'
                            '> c\n'
                            '\n'
                            '    code'),
            '- a\n'
            '    - b\n'
            '\n'
            '> c\n'
            '\n'
            '    code')

    def test_thematic_break(self) -> None:
        """Testing normalize_list_indentation with a thematic break"""
        text = (
            '- a\n'
            '\n'
            '- - -\n'
            '\n'
            '  b'
        )

        self.assertEqual(self._normalize(text), text)
