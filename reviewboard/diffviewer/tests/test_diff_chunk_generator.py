from __future__ import unicode_literals

from reviewboard.diffviewer.chunk_generator import DiffChunkGenerator
from reviewboard.scmtools.core import PRE_CREATION
from reviewboard.testing import TestCase


class DiffChunkGeneratorTests(TestCase):
    """Unit tests for DiffChunkGenerator."""

    fixtures = ['test_scmtools']

    def setUp(self):
        self.repository = self.create_repository()
        self.diffset = self.create_diffset(repository=self.repository)
        self.filediff = self.create_filediff(diffset=self.diffset)
        self.generator = DiffChunkGenerator(None, self.filediff)

    def test_get_chunks_with_empty_added_file(self):
        """Testing DiffChunkGenerator.get_chunks with empty added file"""
        self.filediff.source_revision = PRE_CREATION
        self.filediff.extra_data.update({
            'raw_insert_count': 0,
            'raw_delete_count': 0,
        })

        self.assertEqual(len(self.generator.get_chunks()), 0)

    def test_get_chunks_with_replace_in_added_file_with_parent_diff(self):
        """Testing DiffChunkGenerator.get_chunks with replace chunks in
        added file with parent diff
        """
        self.filediff.diff = (
            b'--- README\n'
            b'+++ README\n'
            b'@@ -1,1 +1,1 @@\n'
            b'-line\n'
            b'+line.\n'
        )
        self.filediff.parent_diff = (
            b'--- README\n'
            b'+++ README\n'
            b'@@ -0,0 +1,1 @@\n'
            b'+line\n'
        )
        self.filediff.source_revision = PRE_CREATION
        self.filediff.extra_data.update({
            'raw_insert_count': 1,
            'raw_delete_count': 1,
            'insert_count': 0,
            'delete_count': 0,
        })

        self.assertEqual(len(self.generator.get_chunks()), 1)

    def test_get_move_info_with_new_range_no_preceding(self):
        """Testing DiffChunkGenerator._get_move_info with new move range and
        no adjacent preceding move range
        """
        self.assertEqual(
            self.generator._get_move_info(10, {
                8: 100,
                10: 200,
                11: 201,
            }),
            (200, True))

    def test_get_move_info_with_new_range_preceding(self):
        """Testing DiffChunkGenerator._get_move_info with new move range and
        adjacent preceding move range
        """
        self.assertEqual(
            self.generator._get_move_info(10, {
                8: 100,
                9: 101,
                10: 200,
                11: 201,
            }),
            (200, True))

    def test_get_move_info_with_existing_range(self):
        """Testing DiffChunkGenerator._get_move_info with existing move
        range
        """
        self.assertEqual(
            self.generator._get_move_info(11, {
                8: 100,
                9: 101,
                10: 200,
                11: 201,
            }),
            (201, False))

    def test_get_move_info_with_no_move(self):
        """Testing DiffChunkGenerator._get_move_info with no move range"""
        self.assertIsNone(self.generator._get_move_info(500, {
            8: 100,
            9: 101,
            10: 200,
            11: 201,
        }))

    def test_indent_spaces(self):
        """Testing DiffChunkGenerator._serialize_indentation with spaces"""
        self.assertEqual(
            self.generator._serialize_indentation('    ', 4),
            ('&gt;&gt;&gt;&gt;', ''))

    def test_indent_tabs(self):
        """Testing DiffChunkGenerator._serialize_indentation with tabs"""
        self.assertEqual(
            self.generator._serialize_indentation('\t', 8),
            ('&mdash;&mdash;&mdash;&mdash;&mdash;&mdash;&gt;|', ''))

    def test_indent_spaces_and_tabs(self):
        """Testing DiffChunkGenerator._serialize_indentation
        with spaces and tabs
        """
        self.assertEqual(
            self.generator._serialize_indentation('   \t', 8),
            ('&gt;&gt;&gt;&mdash;&mdash;&mdash;&gt;|', ''))

    def test_indent_tabs_and_spaces(self):
        """Testing DiffChunkGenerator._serialize_indentation
        with tabs and spaces
        """
        self.assertEqual(
            self.generator._serialize_indentation('\t   ', 11),
            ('&mdash;&mdash;&mdash;&mdash;&mdash;&mdash;&gt;|&gt;&gt;&gt;',
             ''))

    def test_indent_9_spaces_and_tab(self):
        """Testing DiffChunkGenerator._serialize_indentation
        with 9 spaces and tab
        """
        self.assertEqual(
            self.generator._serialize_indentation('       \t', 8),
            ('&gt;&gt;&gt;&gt;&gt;&gt;&gt;|', ''))

    def test_indent_8_spaces_and_tab(self):
        """Testing DiffChunkGenerator._serialize_indentation
        with 8 spaces and tab
        """
        self.assertEqual(
            self.generator._serialize_indentation('      \t', 8),
            ('&gt;&gt;&gt;&gt;&gt;&gt;&gt;|', ''))

    def test_indent_7_spaces_and_tab(self):
        """Testing DiffChunkGenerator._serialize_indentation
        with 7 spaces and tab
        """
        self.assertEqual(
            self.generator._serialize_indentation('     \t', 8),
            ('&gt;&gt;&gt;&gt;&gt;&mdash;&gt;|', ''))

    def test_unindent_spaces(self):
        """Testing DiffChunkGenerator._serialize_unindentation with spaces"""
        self.assertEqual(
            self.generator._serialize_unindentation('    ', 4),
            ('&lt;&lt;&lt;&lt;', ''))

    def test_unindent_tabs(self):
        """Testing DiffChunkGenerator._serialize_unindentation with tabs"""
        self.assertEqual(
            self.generator._serialize_unindentation('\t', 8),
            ('|&lt;&mdash;&mdash;&mdash;&mdash;&mdash;&mdash;', ''))

    def test_unindent_spaces_and_tabs(self):
        """Testing DiffChunkGenerator._serialize_unindentation
        with spaces and tabs
        """
        self.assertEqual(
            self.generator._serialize_unindentation('   \t', 8),
            ('&lt;&lt;&lt;|&lt;&mdash;&mdash;&mdash;', ''))

    def test_unindent_tabs_and_spaces(self):
        """Testing DiffChunkGenerator._serialize_unindentation
        with tabs and spaces
        """
        self.assertEqual(
            self.generator._serialize_unindentation('\t   ', 11),
            ('|&lt;&mdash;&mdash;&mdash;&mdash;&mdash;&mdash;&lt;&lt;&lt;',
             ''))

    def test_unindent_9_spaces_and_tab(self):
        """Testing DiffChunkGenerator._serialize_unindentation
        with 9 spaces and tab
        """
        self.assertEqual(
            self.generator._serialize_unindentation('       \t', 8),
            ('&lt;&lt;&lt;&lt;&lt;&lt;&lt;|', ''))

    def test_unindent_8_spaces_and_tab(self):
        """Testing DiffChunkGenerator._serialize_unindentation
        with 8 spaces and tab
        """
        self.assertEqual(
            self.generator._serialize_unindentation('      \t', 8),
            ('&lt;&lt;&lt;&lt;&lt;&lt;|&lt;', ''))

    def test_unindent_7_spaces_and_tab(self):
        """Testing DiffChunkGenerator._serialize_unindentation
        with 7 spaces and tab
        """
        self.assertEqual(
            self.generator._serialize_unindentation('     \t', 8),
            ('&lt;&lt;&lt;&lt;&lt;|&lt;&mdash;', ''))

    def test_highlight_indent(self):
        """Testing DiffChunkGenerator._highlight_indentation
        with indentation
        """
        self.assertEqual(
            self.generator._highlight_indentation(
                '',
                '        foo',
                True, 4, 4),
            ('', '<span class="indent">&gt;&gt;&gt;&gt;</span>    foo'))

    def test_highlight_indent_with_adjacent_tag(self):
        """Testing DiffChunkGenerator._highlight_indentation
        with indentation and adjacent tag wrapping whitespace
        """
        self.assertEqual(
            self.generator._highlight_indentation(
                '',
                '<span class="s"> </span>foo',
                True, 1, 1),
            ('',
             '<span class="s"><span class="indent">&gt;</span></span>foo'))

    def test_highlight_indent_with_unexpected_chars(self):
        """Testing DiffChunkGenerator._highlight_indentation
        with indentation and unexpected markup chars
        """
        self.assertEqual(
            self.generator._highlight_indentation(
                '',
                ' <span>  </span> foo',
                True, 4, 2),
            ('', ' <span>  </span> foo'))

    def test_highlight_unindent(self):
        """Testing DiffChunkGenerator._highlight_indentation
        with unindentation
        """
        self.assertEqual(
            self.generator._highlight_indentation(
                '        foo',
                '',
                False, 4, 4),
            ('<span class="unindent">&lt;&lt;&lt;&lt;</span>    foo', ''))

    def test_highlight_unindent_with_adjacent_tag(self):
        """Testing DiffChunkGenerator._highlight_indentation
        with unindentation and adjacent tag wrapping whitespace
        """
        self.assertEqual(
            self.generator._highlight_indentation(
                '<span class="s"> </span>foo',
                '',
                False, 1, 1),
            ('<span class="s"><span class="unindent">&lt;</span></span>foo',
             ''))

    def test_highlight_unindent_with_unexpected_chars(self):
        """Testing DiffChunkGenerator._highlight_indentation
        with unindentation and unexpected markup chars
        """
        self.assertEqual(
            self.generator._highlight_indentation(
                ' <span>  </span> foo',
                '',
                False, 4, 2),
            (' <span>  </span> foo', ''))

    def test_highlight_unindent_with_replacing_last_tab_with_spaces(self):
        """Testing DiffChunkGenerator._highlight_indentation
        with unindentation and replacing last tab with spaces
        """
        self.assertEqual(
            self.generator._highlight_indentation(
                '<span>\t\t        </span> foo',
                '',
                False, 2, 16),
            ('<span><span class="unindent">'
             '|&lt;&mdash;&mdash;&mdash;&mdash;&mdash;&mdash;'
             '|&lt;&mdash;&mdash;&mdash;&mdash;&mdash;&mdash;'
             '</span>        </span> foo', ''))

    def test_highlight_unindent_with_replacing_3_tabs_with_tab_spaces(self):
        """Testing DiffChunkGenerator._highlight_indentation
        with unindentation and replacing 3 tabs with 1 tab and 8 spaces
        """
        self.assertEqual(
            self.generator._highlight_indentation(
                '<span>\t        </span> foo',
                '',
                False, 1, 24),
            ('<span><span class="unindent">'
             '|&lt;&mdash;&mdash;&mdash;&mdash;&mdash;&mdash;'
             '</span>        </span> foo', ''))
