from __future__ import unicode_literals

from reviewboard.diffviewer.chunk_generator import RawDiffChunkGenerator
from reviewboard.testing import TestCase


class RawDiffChunkGeneratorTests(TestCase):
    """Unit tests for RawDiffChunkGenerator."""

    @property
    def generator(self):
        """Create a dummy generator for tests that need it.

        This generator will be void of any content. It's intended for
        use in tests that need to operate on its utility functions.
        """
        return RawDiffChunkGenerator(old=b'',
                                     new=b'',
                                     orig_filename='',
                                     modified_filename='')

    def test_get_chunks(self):
        """Testing RawDiffChunkGenerator.get_chunks"""
        old = (
            b'This is line 1\n'
            b'Another line\n'
            b'Line 3.\n'
            b'la de da.\n'
        )

        new = (
            b'This is line 1\n'
            b'Line 3.\n'
            b'la de doo.\n'
        )

        generator = RawDiffChunkGenerator(old, new, 'file1', 'file2')
        chunks = list(generator.get_chunks())

        self.assertEqual(len(chunks), 4)
        self.assertEqual(
            chunks[0],
            {
                'change': 'equal',
                'collapsable': False,
                'index': 0,
                'lines': [
                    [
                        1,
                        1,
                        'This is line 1',
                        [],
                        1,
                        'This is line 1',
                        [],
                        False,
                    ],
                ],
                'meta': {
                    'left_headers': [],
                    'right_headers': [],
                    'whitespace_chunk': False,
                    'whitespace_lines': [],
                },
                'numlines': 1,
            })
        self.assertEqual(
            chunks[1],
            {
                'change': 'delete',
                'collapsable': False,
                'index': 1,
                'lines': [
                    [
                        2,
                        2,
                        'Another line',
                        [],
                        '',
                        '',
                        [],
                        False,
                    ],
                ],
                'meta': {
                    'left_headers': [],
                    'right_headers': [],
                    'whitespace_chunk': False,
                    'whitespace_lines': [],
                },
                'numlines': 1,
            })
        self.assertEqual(
            chunks[2],
            {
                'change': 'equal',
                'collapsable': False,
                'index': 2,
                'lines': [
                    [
                        3,
                        3,
                        'Line 3.',
                        [],
                        2,
                        'Line 3.',
                        [],
                        False,
                    ],
                ],
                'meta': {
                    'left_headers': [],
                    'right_headers': [],
                    'whitespace_chunk': False,
                    'whitespace_lines': [],
                },
                'numlines': 1,
            })
        self.assertEqual(
            chunks[3],
            {
                'change': 'replace',
                'collapsable': False,
                'index': 3,
                'lines': [
                    [
                        4,
                        4,
                        'la de da.',
                        [(7, 8)],
                        3,
                        'la de doo.',
                        [(7, 9)],
                        False,
                    ],
                ],
                'meta': {
                    'left_headers': [],
                    'right_headers': [],
                    'whitespace_chunk': False,
                    'whitespace_lines': [],
                },
                'numlines': 1,
            })

    def test_get_chunks_with_enable_syntax_highlighting_true(self):
        """Testing RawDiffChunkGenerator.get_chunks with
        enable_syntax_highlighting=True and syntax highlighting
        available for file
        """
        old = b'This is **bold**'
        new = b'This is *italic*'

        generator = RawDiffChunkGenerator(old=old,
                                          new=new,
                                          orig_filename='file1.md',
                                          modified_filename='file2.md')
        chunks = list(generator.get_chunks())

        self.assertEqual(len(chunks), 1)
        self.assertEqual(
            chunks[0],
            {
                'change': 'replace',
                'collapsable': False,
                'index': 0,
                'lines': [
                    [
                        1,
                        1,
                        'This is <span class="gs">**bold**</span>',
                        [(9, 16)],
                        1,
                        'This is <span class="ge">*italic*</span>',
                        [(9, 16)],
                        False,
                    ],
                ],
                'meta': {
                    'left_headers': [],
                    'right_headers': [],
                    'whitespace_chunk': False,
                    'whitespace_lines': [],
                },
                'numlines': 1,
            }
        )

    def test_get_chunks_with_enable_syntax_highlighting_false(self):
        """Testing RawDiffChunkGenerator.get_chunks with
        enable_syntax_highlighting=False
        """
        old = b'This is **bold**'
        new = b'This is *italic*'

        generator = RawDiffChunkGenerator(old=old,
                                          new=new,
                                          orig_filename='file1.md',
                                          modified_filename='file2.md',
                                          enable_syntax_highlighting=False)
        chunks = list(generator.get_chunks())

        self.assertEqual(len(chunks), 1)
        self.assertEqual(
            chunks[0],
            {
                'change': 'replace',
                'collapsable': False,
                'index': 0,
                'lines': [
                    [
                        1,
                        1,
                        'This is **bold**',
                        [(9, 16)],
                        1,
                        'This is *italic*',
                        [(9, 16)],
                        False,
                    ],
                ],
                'meta': {
                    'left_headers': [],
                    'right_headers': [],
                    'whitespace_chunk': False,
                    'whitespace_lines': [],
                },
                'numlines': 1,
            }
        )

    def test_get_chunks_with_syntax_highlighting_blacklisted(self):
        """Testing RawDiffChunkGenerator.get_chunks with syntax highlighting
        blacklisted for file
        """
        class MyRawDiffChunkGenerator(RawDiffChunkGenerator):
            STYLED_EXT_BLACKLIST = (
                '.md',
            )

        old = b'This is **bold**'
        new = b'This is *italic*'

        generator = MyRawDiffChunkGenerator(old=old,
                                            new=new,
                                            orig_filename='file1.md',
                                            modified_filename='file2.md')
        chunks = list(generator.get_chunks())

        self.assertEqual(len(chunks), 1)
        self.assertEqual(
            chunks[0],
            {
                'change': 'replace',
                'collapsable': False,
                'index': 0,
                'lines': [
                    [
                        1,
                        1,
                        'This is **bold**',
                        [(9, 16)],
                        1,
                        'This is *italic*',
                        [(9, 16)],
                        False,
                    ],
                ],
                'meta': {
                    'left_headers': [],
                    'right_headers': [],
                    'whitespace_chunk': False,
                    'whitespace_lines': [],
                },
                'numlines': 1,
            }
        )

    def test_generate_chunks_with_encodings(self):
        """Testing RawDiffChunkGenerator.generate_chunks with explicit
        encodings for old and new
        """
        old = (
            'This is line 1\n'
            'Another line\n'
            'Line 3.\n'
            'la de da.\n'
        ).encode('utf-8')

        new = (
            'This is line 1\n'
            'Line 3.\n'
            'la de doo.\n'
        ).encode('utf-16')

        generator = RawDiffChunkGenerator(old=old,
                                          new=new,
                                          orig_filename='file1',
                                          modified_filename='file2')
        chunks = list(generator.generate_chunks(
            old=old,
            new=new,
            old_encoding_list=['utf-8'],
            new_encoding_list=['utf-16']
        ))

        self.assertEqual(len(chunks), 4)
        self.assertEqual(
            chunks[0],
            {
                'change': 'equal',
                'collapsable': False,
                'index': 0,
                'lines': [
                    [
                        1,
                        1,
                        'This is line 1',
                        [],
                        1,
                        'This is line 1',
                        [],
                        False,
                    ],
                ],
                'meta': {
                    'left_headers': [],
                    'right_headers': [],
                    'whitespace_chunk': False,
                    'whitespace_lines': [],
                },
                'numlines': 1,
            })
        self.assertEqual(
            chunks[1],
            {
                'change': 'delete',
                'collapsable': False,
                'index': 1,
                'lines': [
                    [
                        2,
                        2,
                        'Another line',
                        [],
                        '',
                        '',
                        [],
                        False,
                    ],
                ],
                'meta': {
                    'left_headers': [],
                    'right_headers': [],
                    'whitespace_chunk': False,
                    'whitespace_lines': [],
                },
                'numlines': 1,
            })
        self.assertEqual(
            chunks[2],
            {
                'change': 'equal',
                'collapsable': False,
                'index': 2,
                'lines': [
                    [
                        3,
                        3,
                        'Line 3.',
                        [],
                        2,
                        'Line 3.',
                        [],
                        False,
                    ],
                ],
                'meta': {
                    'left_headers': [],
                    'right_headers': [],
                    'whitespace_chunk': False,
                    'whitespace_lines': [],
                },
                'numlines': 1,
            })
        self.assertEqual(
            chunks[3],
            {
                'change': 'replace',
                'collapsable': False,
                'index': 3,
                'lines': [
                    [
                        4,
                        4,
                        'la de da.',
                        [(7, 8)],
                        3,
                        'la de doo.',
                        [(7, 9)],
                        False,
                    ],
                ],
                'meta': {
                    'left_headers': [],
                    'right_headers': [],
                    'whitespace_chunk': False,
                    'whitespace_lines': [],
                },
                'numlines': 1,
            })

    def test_apply_pygments_with_lexer(self):
        """Testing RawDiffChunkGenerator._apply_pygments with valid lexer"""
        chunk_generator = RawDiffChunkGenerator(old=[],
                                                new=[],
                                                orig_filename='file1',
                                                modified_filename='file2')
        self.assertEqual(
            chunk_generator._apply_pygments(data='This is **bold**\n',
                                            filename='test.md'),
            ['This is <span class="gs">**bold**</span>'])

    def test_apply_pygments_without_lexer(self):
        """Testing RawDiffChunkGenerator._apply_pygments without valid lexer"""
        chunk_generator = RawDiffChunkGenerator(old=[],
                                                new=[],
                                                orig_filename='file1',
                                                modified_filename='file2')
        self.assertIsNone(
            chunk_generator._apply_pygments(data='This is **bold**',
                                            filename='test'))

    def test_apply_pygments_with_blacklisted_file(self):
        """Testing RawDiffChunkGenerator._apply_pygments with blacklisted
        file extension
        """
        class MyRawDiffChunkGenerator(RawDiffChunkGenerator):
            STYLED_EXT_BLACKLIST = (
                '.md',
            )

        chunk_generator = MyRawDiffChunkGenerator(old=[],
                                                  new=[],
                                                  orig_filename='file1',
                                                  modified_filename='file2')
        self.assertIsNone(
            chunk_generator._apply_pygments(data='This is **bold**',
                                            filename='test.md'))

    def test_get_move_info_with_new_range_no_preceding(self):
        """Testing RawDiffChunkGenerator._get_move_info with new move range and
        no adjacent preceding move range
        """
        generator = RawDiffChunkGenerator([], [], 'file1', 'file2')

        self.assertEqual(
            generator._get_move_info(10, {
                8: 100,
                10: 200,
                11: 201,
            }),
            (200, True))

    def test_get_move_info_with_new_range_preceding(self):
        """Testing RawDiffChunkGenerator._get_move_info with new move range and
        adjacent preceding move range
        """
        generator = RawDiffChunkGenerator([], [], 'file1', 'file2')

        self.assertEqual(
            generator._get_move_info(10, {
                8: 100,
                9: 101,
                10: 200,
                11: 201,
            }),
            (200, True))

    def test_get_move_info_with_existing_range(self):
        """Testing RawDiffChunkGenerator._get_move_info with existing move
        range
        """
        generator = RawDiffChunkGenerator([], [], 'file1', 'file2')

        self.assertEqual(
            generator._get_move_info(11, {
                8: 100,
                9: 101,
                10: 200,
                11: 201,
            }),
            (201, False))

    def test_get_move_info_with_no_move(self):
        """Testing RawDiffChunkGenerator._get_move_info with no move range"""
        generator = RawDiffChunkGenerator([], [], 'file1', 'file2')

        self.assertIsNone(generator._get_move_info(500, {
            8: 100,
            9: 101,
            10: 200,
            11: 201,
        }))

    def test_indent_spaces(self):
        """Testing RawDiffChunkGenerator._serialize_indentation with spaces"""
        self.assertEqual(
            self.generator._serialize_indentation('    ', 4),
            ('&gt;&gt;&gt;&gt;', ''))

    def test_indent_tabs(self):
        """Testing RawDiffChunkGenerator._serialize_indentation with tabs"""
        self.assertEqual(
            self.generator._serialize_indentation('\t', 8),
            ('&mdash;&mdash;&mdash;&mdash;&mdash;&mdash;&gt;|', ''))

    def test_indent_spaces_and_tabs(self):
        """Testing RawDiffChunkGenerator._serialize_indentation
        with spaces and tabs
        """
        self.assertEqual(
            self.generator._serialize_indentation('   \t', 8),
            ('&gt;&gt;&gt;&mdash;&mdash;&mdash;&gt;|', ''))

    def test_indent_tabs_and_spaces(self):
        """Testing RawDiffChunkGenerator._serialize_indentation
        with tabs and spaces
        """
        self.assertEqual(
            self.generator._serialize_indentation('\t   ', 11),
            ('&mdash;&mdash;&mdash;&mdash;&mdash;&mdash;&gt;|&gt;&gt;&gt;',
             ''))

    def test_indent_9_spaces_and_tab(self):
        """Testing RawDiffChunkGenerator._serialize_indentation
        with 9 spaces and tab
        """
        self.assertEqual(
            self.generator._serialize_indentation('       \t', 8),
            ('&gt;&gt;&gt;&gt;&gt;&gt;&gt;|', ''))

    def test_indent_8_spaces_and_tab(self):
        """Testing RawDiffChunkGenerator._serialize_indentation
        with 8 spaces and tab
        """
        self.assertEqual(
            self.generator._serialize_indentation('      \t', 8),
            ('&gt;&gt;&gt;&gt;&gt;&gt;&gt;|', ''))

    def test_indent_7_spaces_and_tab(self):
        """Testing RawDiffChunkGenerator._serialize_indentation
        with 7 spaces and tab
        """
        self.assertEqual(
            self.generator._serialize_indentation('     \t', 8),
            ('&gt;&gt;&gt;&gt;&gt;&mdash;&gt;|', ''))

    def test_unindent_spaces(self):
        """Testing RawDiffChunkGenerator._serialize_unindentation with spaces
        """
        self.assertEqual(
            self.generator._serialize_unindentation('    ', 4),
            ('&lt;&lt;&lt;&lt;', ''))

    def test_unindent_tabs(self):
        """Testing RawDiffChunkGenerator._serialize_unindentation with tabs"""
        self.assertEqual(
            self.generator._serialize_unindentation('\t', 8),
            ('|&lt;&mdash;&mdash;&mdash;&mdash;&mdash;&mdash;', ''))

    def test_unindent_spaces_and_tabs(self):
        """Testing RawDiffChunkGenerator._serialize_unindentation
        with spaces and tabs
        """
        self.assertEqual(
            self.generator._serialize_unindentation('   \t', 8),
            ('&lt;&lt;&lt;|&lt;&mdash;&mdash;&mdash;', ''))

    def test_unindent_tabs_and_spaces(self):
        """Testing RawDiffChunkGenerator._serialize_unindentation
        with tabs and spaces
        """
        self.assertEqual(
            self.generator._serialize_unindentation('\t   ', 11),
            ('|&lt;&mdash;&mdash;&mdash;&mdash;&mdash;&mdash;&lt;&lt;&lt;',
             ''))

    def test_unindent_9_spaces_and_tab(self):
        """Testing RawDiffChunkGenerator._serialize_unindentation
        with 9 spaces and tab
        """
        self.assertEqual(
            self.generator._serialize_unindentation('       \t', 8),
            ('&lt;&lt;&lt;&lt;&lt;&lt;&lt;|', ''))

    def test_unindent_8_spaces_and_tab(self):
        """Testing RawDiffChunkGenerator._serialize_unindentation
        with 8 spaces and tab
        """
        self.assertEqual(
            self.generator._serialize_unindentation('      \t', 8),
            ('&lt;&lt;&lt;&lt;&lt;&lt;|&lt;', ''))

    def test_unindent_7_spaces_and_tab(self):
        """Testing RawDiffChunkGenerator._serialize_unindentation
        with 7 spaces and tab
        """
        self.assertEqual(
            self.generator._serialize_unindentation('     \t', 8),
            ('&lt;&lt;&lt;&lt;&lt;|&lt;&mdash;', ''))

    def test_highlight_indent(self):
        """Testing RawDiffChunkGenerator._highlight_indentation
        with indentation
        """
        self.assertEqual(
            self.generator._highlight_indentation(
                '',
                '        foo',
                True, 4, 4),
            ('', '<span class="indent">&gt;&gt;&gt;&gt;</span>    foo'))

    def test_highlight_indent_with_adjacent_tag(self):
        """Testing RawDiffChunkGenerator._highlight_indentation
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
        """Testing RawDiffChunkGenerator._highlight_indentation
        with indentation and unexpected markup chars
        """
        self.assertEqual(
            self.generator._highlight_indentation(
                '',
                ' <span>  </span> foo',
                True, 4, 2),
            ('', ' <span>  </span> foo'))

    def test_highlight_unindent(self):
        """Testing RawDiffChunkGenerator._highlight_indentation
        with unindentation
        """
        self.assertEqual(
            self.generator._highlight_indentation(
                '        foo',
                '',
                False, 4, 4),
            ('<span class="unindent">&lt;&lt;&lt;&lt;</span>    foo', ''))

    def test_highlight_unindent_with_adjacent_tag(self):
        """Testing RawDiffChunkGenerator._highlight_indentation
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
        """Testing RawDiffChunkGenerator._highlight_indentation
        with unindentation and unexpected markup chars
        """
        self.assertEqual(
            self.generator._highlight_indentation(
                ' <span>  </span> foo',
                '',
                False, 4, 2),
            (' <span>  </span> foo', ''))

    def test_highlight_unindent_with_replacing_last_tab_with_spaces(self):
        """Testing RawDiffChunkGenerator._highlight_indentation
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
        """Testing RawDiffChunkGenerator._highlight_indentation
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

