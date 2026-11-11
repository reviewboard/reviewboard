"""Unit tests for reviewboard.reviews.ui.markdownui."""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.test.client import RequestFactory
from django.utils.html import strip_tags

from reviewboard.attachments.models import FileAttachment
from reviewboard.diffviewer.settings import DiffSettings
from reviewboard.reviews.chunk_generators import MarkdownDiffChunkGenerator
from reviewboard.reviews.ui.markdownui import (
    MarkdownReviewUI,
    get_row_text_ranges,
    map_text_ranges,
    render_markdown_blocks,
)
from reviewboard.testing import TestCase

if TYPE_CHECKING:
    from collections.abc import Sequence

    from reviewboard.attachments.models import FileAttachment


class RenderMarkdownBlocksTests(TestCase):
    """Unit tests for render_markdown_blocks.

    Version Added:
        9.0
    """

    def test_paragraphs(self) -> None:
        """Testing render_markdown_blocks with paragraphs"""
        self.assertEqual(
            render_markdown_blocks('# Title\n\nOne\ntwo.\n\n\nThree.\n'),
            [
                '<h1>Title</h1>',
                '<p data-md-gap="block">One two.</p>',
                '<p data-md-gap="block">Three.</p>',
            ])

    def test_lists(self) -> None:
        """Testing render_markdown_blocks with lists"""
        self.assertEqual(
            render_markdown_blocks('- a\n'
                                   '    - b\n'
                                   '- c\n'
                                   '\n'
                                   'Text\n'
                                   '\n'
                                   '1. x\n'
                                   '2. y\n'),
            [
                '<ul style="--md-list-depth: 0"><li>a</li></ul>',
                '<ul style="--md-list-depth: 1" data-md-gap="item">'
                '<li>b</li></ul>',
                '<ul style="--md-list-depth: 0" data-md-gap="item">'
                '<li>c</li></ul>',
                '<p data-md-gap="block">Text</p>',
                '<ol start="1" style="--md-list-depth: 0" data-md-gap="block">'
                '<li>x</li></ol>',
                '<ol start="2" style="--md-list-depth: 0" data-md-gap="item">'
                '<li>y</li></ol>',
            ])

    def test_lists_with_content_after_nested_list(self) -> None:
        """Testing render_markdown_blocks with list item content after a
        nested list
        """
        self.assertEqual(
            render_markdown_blocks('- a\n'
                                   '    - b\n'
                                   '\n'
                                   '    Text\n'),
            [
                '<ul style="--md-list-depth: 0"><li><p>a</p></li></ul>',
                '<ul style="--md-list-depth: 1" data-md-gap="item">'
                '<li>b</li></ul>',
                '<ul style="--md-list-depth: 0" data-md-gap="block">'
                '<li class="md-list-continuation"><p>Text</p></li></ul>',
            ])

    def test_task_list(self) -> None:
        """Testing render_markdown_blocks with a task list"""
        self.assertEqual(
            render_markdown_blocks('- [ ] a <input type=checkbox>\n'
                                   '- [x] b\n'),
            [
                '<ul style="--md-list-depth: 0">'
                '<li class="task-list-item">'
                '<span class="task-list-checkbox">\u2610</span> a '
                '&lt;input type=checkbox&gt;</li></ul>',
                '<ul style="--md-list-depth: 0" data-md-gap="item">'
                '<li class="task-list-item">'
                '<span class="task-list-checkbox -is-checked">\u2611</span> '
                'b</li></ul>',
            ])

    def test_blockquote(self) -> None:
        """Testing render_markdown_blocks with a blockquote"""
        self.assertEqual(
            render_markdown_blocks('> a\n'
                                   '>\n'
                                   '> - b\n'),
            [
                '<blockquote><p>a</p></blockquote>',
                '<blockquote><ul style="--md-list-depth: 0" '
                'data-md-gap="block"><li>b</li></ul></blockquote>',
            ])

    def test_bare_urls(self) -> None:
        """Testing render_markdown_blocks links bare URLs"""
        self.assertEqual(
            render_markdown_blocks('See https://example.com/a and '
                                   'www.example.com.\n'),
            [
                '<p>See <a href="https://example.com/a">'
                'https://example.com/a</a> and '
                '<a href="http://www.example.com">www.example.com</a>.</p>',
            ])

    def test_alert(self) -> None:
        """Testing render_markdown_blocks with an alert"""
        self.assertEqual(
            render_markdown_blocks('> [!TIP]\n'
                                   '> a\n'
                                   '>\n'
                                   '> > b\n'
                                   '\n'
                                   '> c\n'),
            [
                '<blockquote class="admonition tip">'
                '<p class="admonition-title">Tip</p></blockquote>',
                '<blockquote class="admonition tip">'
                '<p data-md-gap="block">a</p></blockquote>',
                '<blockquote class="admonition tip">'
                '<blockquote data-md-gap="block"><p>b</p></blockquote>'
                '</blockquote>',
                '<blockquote data-md-gap="block"><p>c</p></blockquote>',
            ])

    def test_table(self) -> None:
        """Testing render_markdown_blocks with a table"""
        self.assertEqual(
            render_markdown_blocks('| A | B |\n'
                                   '|---|---|\n'
                                   '| 1 | 2 |\n'
                                   '| 3 | 4 |\n'),
            [
                '<table style="table-layout: fixed; width: 10ch">'
                '<colgroup><col style="width: 5ch"/><col style="width: 5ch"/>'
                '</colgroup>'
                '<thead><tr><th>A</th><th>B</th></tr></thead></table>',
                '<table style="table-layout: fixed; width: 10ch">'
                '<colgroup><col style="width: 5ch"/><col style="width: 5ch"/>'
                '</colgroup>'
                '<tbody><tr><td>1</td><td>2</td></tr></tbody></table>',
                '<table style="table-layout: fixed; width: 10ch">'
                '<colgroup><col style="width: 5ch"/><col style="width: 5ch"/>'
                '</colgroup>'
                '<tbody><tr><td>3</td><td>4</td></tr></tbody></table>',
            ])

    def test_table_column_widths(self) -> None:
        """Testing render_markdown_blocks sizes table columns by their
        longest text
        """
        long_text = 'x' * 50
        rows = render_markdown_blocks(
            f'| A | Longer header |\n'
            f'|---|---|\n'
            f'| 1 | {long_text} |\n')

        # Column 1 is the minimum width. Column 2 is capped.
        for row in rows:
            self.assertTrue(row.startswith(
                '<table style="table-layout: fixed; width: 47ch">'
                '<colgroup><col style="width: 5ch"/>'
                '<col style="width: 42ch"/></colgroup>'))

    def test_code(self) -> None:
        """Testing render_markdown_blocks with code blocks"""
        self.assertEqual(
            render_markdown_blocks('```\n'
                                   'a\n'
                                   '\n'
                                   'b\n'
                                   '```\n'
                                   '\n'
                                   '```\n'
                                   'c\n'
                                   '```\n'),
            [
                '<div class="codehilite codehilite-multiline-start">'
                '<pre>a</pre></div>',
                '<div class="codehilite codehilite-multiline-middle">'
                '<pre></pre></div>',
                '<div class="codehilite codehilite-multiline-end">'
                '<pre>b</pre></div>',
                '<div class="codehilite" data-md-gap="block">'
                '<pre>c</pre></div>',
            ])

    def test_code_in_blockquote(self) -> None:
        """Testing render_markdown_blocks with a code fence in a blockquote"""
        self.assertEqual(
            render_markdown_blocks('> ```\n'
                                   '> <a>\n'
                                   '> b\n'
                                   '> ```\n'),
            [
                '<blockquote><div class="codehilite '
                'codehilite-multiline-start"><pre>&lt;a&gt;</pre></div>'
                '</blockquote>',
                '<blockquote><div class="codehilite '
                'codehilite-multiline-end"><pre>b</pre></div>'
                '</blockquote>',
            ])

    def test_gaps(self) -> None:
        """Testing render_markdown_blocks marks gaps between blocks"""
        self.assertEqual(
            render_markdown_blocks('# Title\n'
                                   '\n'
                                   '- a\n'
                                   '    - b\n'
                                   '\n'
                                   '> q1\n'
                                   '>\n'
                                   '> > nested\n'
                                   '> >\n'
                                   '> > n2\n'
                                   '\n'
                                   '```\n'
                                   'x\n'
                                   'y\n'
                                   '```\n'
                                   '\n'
                                   '---\n'),
            [
                '<h1>Title</h1>',
                '<ul style="--md-list-depth: 0" data-md-gap="block">'
                '<li>a</li></ul>',
                '<ul style="--md-list-depth: 1" data-md-gap="item">'
                '<li>b</li></ul>',

                # The quote's gap goes on its blockquote.
                '<blockquote data-md-gap="block"><p>q1</p></blockquote>',

                # The nested quote's gap goes on its own blockquote, inside
                # the outer one.
                '<blockquote><blockquote data-md-gap="block">'
                '<p>nested</p></blockquote></blockquote>',
                '<blockquote><blockquote><p data-md-gap="block">n2</p>'
                '</blockquote></blockquote>',

                # Only the first line of code gets a gap.
                '<div class="codehilite codehilite-multiline-start" '
                'data-md-gap="block"><pre>x</pre></div>',
                '<div class="codehilite codehilite-multiline-end">'
                '<pre>y</pre></div>',
                '<hr data-md-gap="block"/>',
            ])

    def test_code_with_tree_sitter(self) -> None:
        """Testing render_markdown_blocks highlights code with tree-sitter"""
        self.assertEqual(
            render_markdown_blocks('```py\n'
                                   's = """a\n'
                                   'b"""\n'
                                   '```\n'),
            [
                '<div class="codehilite codehilite-multiline-start"><pre>'
                '<span class="ts-variable">s</span> '
                '<span class="ts-operator">=</span> '
                '<span class="ts-string">&quot;&quot;&quot;a</span>'
                '</pre></div>',
                '<div class="codehilite codehilite-multiline-end"><pre>'
                '<span class="ts-string">b&quot;&quot;&quot;</span>'
                '</pre></div>',
            ])

    def test_code_with_pygments(self) -> None:
        """Testing render_markdown_blocks highlights code with Pygments for
        languages tree-sitter doesn't support
        """
        self.assertEqual(
            render_markdown_blocks('```apl\n'
                                   '1 2\n'
                                   '```\n'),
            [
                '<div class="codehilite"><pre>'
                '<span class="m">1</span><span class="w"> </span>'
                '<span class="m">2</span>'
                '</pre></div>',
            ])

    def test_code_with_unknown_language(self) -> None:
        """Testing render_markdown_blocks with code in an unknown language"""
        self.assertEqual(
            render_markdown_blocks('```xyzzy\n'
                                   '<b>\n'
                                   '```\n'),
            [
                '<div class="codehilite"><pre>&lt;b&gt;</pre></div>',
            ])

    def test_code_with_language_marker(self) -> None:
        """Testing render_markdown_blocks with a language marker line in
        indented code
        """
        for marker in (':::python', '#!python'):
            with self.subTest(marker=marker):
                self.assertEqual(
                    render_markdown_blocks(f'    {marker}\n'
                                           f'    x = 1\n'),
                    [
                        '<div class="codehilite"><pre>'
                        '<span class="ts-variable">x</span> '
                        '<span class="ts-operator">=</span> '
                        '<span class="ts-number">1</span>'
                        '</pre></div>',
                    ])

    def test_code_with_blank_lines_around_code(self) -> None:
        """Testing render_markdown_blocks with blank lines at the start and
        end of a code block
        """
        self.assertEqual(
            render_markdown_blocks('```\n'
                                   '\n'
                                   'x\n'
                                   '\n'
                                   '```\n'),
            [
                '<div class="codehilite"><pre>x</pre></div>',
            ])


class MarkdownDiffChunkGeneratorTests(TestCase):
    """Unit tests for MarkdownDiffChunkGenerator.

    Version Added:
        9.0
    """

    def test_ignores_gaps(self) -> None:
        """Testing MarkdownDiffChunkGenerator ignores gaps when comparing
        rows
        """
        old_rows = render_markdown_blocks('Intro\n\nText\n')
        new_rows = render_markdown_blocks('Text\n')

        # Only the gap differs on the "Text" row.
        self.assertEqual(old_rows[1], '<p data-md-gap="block">Text</p>')
        self.assertEqual(new_rows[0], '<p>Text</p>')

        generator = MarkdownDiffChunkGenerator(
            old=[row.encode() for row in old_rows],
            new=[row.encode() for row in new_rows],
            orig_filename='old.md',
            modified_filename='new.md',
            diff_settings=DiffSettings.create())
        chunks = list(generator.get_chunks())

        self.assertEqual(
            [
                chunk['change']
                for chunk in chunks
            ],
            ['delete', 'equal'])

        # Each side still shows its own gap.
        line = chunks[1]['lines'][0]
        self.assertEqual(line[2], '<p data-md-gap="block">Text</p>')
        self.assertEqual(line[5], '<p>Text</p>')


class GetRowTextRangesTests(TestCase):
    """Unit tests for get_row_text_ranges.

    Version Added:
        9.0
    """

    def test_get_row_text_ranges(self) -> None:
        """Testing get_row_text_ranges"""
        self.assertEqual(
            get_row_text_ranges([
                '<p>Two words</p>',
                '\n',
                '<p><img alt="" src="https://example.com/i.png"/></p>',
                '<hr/>',
                '<p>&lt;b&gt;</p>',
                '<div class="codehilite"><pre>x = 1</pre></div>',
                '<div class="codehilite"><pre></pre></div>',
            ]),
            [
                (0, 8),
                (8, 8),
                (8, 9),
                (9, 10),
                (10, 13),
                (13, 17),
                (17, 18),
            ])

    def test_get_row_text_ranges_legacy_code_end(self) -> None:
        """Testing get_row_text_ranges with the legacy row closing a code
        block
        """
        self.assertEqual(
            get_row_text_ranges([
                '<div class="codehilite codehilite-multiline-start">'
                '<pre><span/><code>a</pre></div>',
                '<div class="codehilite codehilite-multiline-end">'
                '<pre></code></pre></div>',
            ]),
            [
                (0, 2),
                (2, 2),
            ])


class MapTextRangesTests(TestCase):
    """Unit tests for map_text_ranges.

    Version Added:
        9.0
    """

    def test_merged(self) -> None:
        """Testing map_text_ranges with rows merged together"""
        self.assertEqual(
            map_text_ranges([(0, 3), (3, 6), (6, 9)],
                            [(0, 6), (6, 9)]),
            [(0, 0), (0, 0), (1, 1)])

    def test_split(self) -> None:
        """Testing map_text_ranges with a row split apart"""
        self.assertEqual(
            map_text_ranges([(0, 3), (3, 9)],
                            [(0, 3), (3, 5), (5, 9)]),
            [(0, 0), (1, 2)])

    def test_rows_without_text(self) -> None:
        """Testing map_text_ranges with rows without text"""
        self.assertEqual(
            map_text_ranges([(0, 0), (0, 3), (3, 3), (3, 3), (3, 6)],
                            [(0, 3), (3, 6)]),
            [(0, 0), (0, 0), (0, 0), (0, 0), (1, 1)])

    def test_no_new_rows(self) -> None:
        """Testing map_text_ranges with no new rows"""
        self.assertEqual(
            map_text_ranges([(0, 3)], []),
            [(0, 0)])


class MarkdownReviewUITests(TestCase):
    """Unit tests for reviewboard.reviews.ui.text.MarkdownReviewUI."""

    fixtures = ['test_users']

    def setUp(self):
        super(MarkdownReviewUITests, self).setUp()

        self.review_request = self.create_review_request()
        self.attachment_history = self.create_file_attachment_history(
            self.review_request)
        self.attachment = self.create_file_attachment(
            self.review_request,
            attachment_history=self.attachment_history,
            attachment_revision=0,
            caption='Revision 1 caption',
            orig_filename='revision1.md',
            mimetype='text/x-markdown',
            file_content=b'This is revision *1*.')
        self.review = self.create_review(self.review_request)

    def test_get_extra_context(self):
        """Testing MarkdownReviewUI.get_extra_context"""
        new_attachment = self.create_file_attachment(
            self.review_request,
            attachment_history=self.attachment_history,
            attachment_revision=1,
            caption='Revision 2 caption',
            orig_filename='revision2.md',
            mimetype='text/x-markdown',
            file_content=b'And **this** is revision 2.')

        review_ui = MarkdownReviewUI(review_request=self.review_request,
                                     obj=new_attachment)

        request = RequestFactory().get('/')
        extra_context = review_ui.get_extra_context(request)

        self.assertFalse(extra_context['is_diff'])
        self.assertFalse(extra_context['diff_type_mismatch'])
        self.assertEqual(extra_context['filename'], 'revision2.md')
        self.assertEqual(extra_context['revision'], 1)
        self.assertEqual(extra_context['num_revisions'], 2)
        self.assertNotIn('diff_caption', extra_context)
        self.assertNotIn('diff_filename', extra_context)
        self.assertNotIn('diff_revision', extra_context)
        self.assertNotIn('source_chunks', extra_context)
        self.assertNotIn('rendered_chunks', extra_context)
        self.assertEqual(
            extra_context['text_lines'],
            [
                '<pre>And <span class="ts-markup-strong">**this**</span> is '
                'revision 2.</pre>',
            ])
        self.assertEqual(extra_context['rendered_lines'],
                         ['<p>And <strong>this</strong> is revision 2.</p>'])

    def test_generate_highlighted_text_lines(self) -> None:
        """Testing MarkdownReviewUI.generate_highlighted_text splits lines the
        same way Pygments did
        """
        attachment = self.create_file_attachment(
            self.review_request,
            attachment_history=self.attachment_history,
            attachment_revision=1,
            orig_filename='revision2.md',
            mimetype='text/x-markdown',
            file_content=b'\n\n# Title\r\nText\r\n\n\n')
        review_ui = MarkdownReviewUI(review_request=self.review_request,
                                     obj=attachment)

        # Blank lines at the start and end are dropped, and Windows line
        # endings are normalized, so source comments stay on their lines.
        self.assertEqual(
            review_ui.generate_highlighted_text(),
            [
                '<pre><span class="ts-markup-heading"># Title</span></pre>',
                '<pre>Text</pre>',
            ])

    def test_get_extra_context_with_diff(self) -> None:
        """Testing MarkdownReviewUI.get_extra_context with diff_against_obj"""
        new_attachment = self.create_file_attachment(
            self.review_request,
            attachment_history=self.attachment_history,
            attachment_revision=1,
            caption='Revision 2 caption',
            orig_filename='revision2.md',
            mimetype='text/x-markdown',
            file_content=b'And **this** is revision 2.')

        review_ui = MarkdownReviewUI(review_request=self.review_request,
                                     obj=new_attachment)
        review_ui.set_diff_against(self.attachment)

        request = RequestFactory().get('/')
        extra_context = review_ui.get_extra_context(request)

        self.assertTrue(extra_context['is_diff'])
        self.assertFalse(extra_context['diff_type_mismatch'])
        self.assertEqual(extra_context['filename'], 'revision2.md')
        self.assertEqual(extra_context['revision'], 1)
        self.assertEqual(extra_context['num_revisions'], 2)
        self.assertEqual(extra_context['diff_caption'], 'Revision 1 caption')
        self.assertEqual(extra_context['diff_filename'], 'revision1.md')
        self.assertEqual(extra_context['diff_revision'], 0)
        self.assertEqual(
            list(extra_context['source_chunks']),
            [
                {
                    'change': 'replace',
                    'collapsable': False,
                    'index': 0,
                    'lines': [
                        (
                            1,
                            1,
                            'This is revision '
                            '<span class="ts-markup-italic">*1*</span>.',
                            [(0, 1), (4, 4), (17, 20)],
                            1,
                            'And <span class="ts-markup-strong">**this**'
                            '</span> is revision 2.',
                            [(0, 7), (10, 12), (25, 26)],
                            False,
                            None,
                        ),
                    ],
                    'meta': {
                        'left_headers': [],
                        'right_headers': [],
                        'whitespace_chunk': False,
                        'whitespace_lines': [],
                    },
                    'numlines': 1,
                },
            ])
        self.assertEqual(
            list(extra_context['rendered_chunks']),
            [
                {
                    'change': 'replace',
                    'collapsable': False,
                    'index': 0,
                    'lines': [
                        (
                            1,
                            1,
                            '<p>This is revision <em>1</em>.</p>',
                            [(0, 1), (17, 18)],
                            1,
                            '<p>And <strong>this</strong> is revision 2.</p>',
                            [(0, 5), (21, 22)],
                            False,
                            None,
                        ),
                    ],
                    'meta': {
                        'left_headers': [],
                        'right_headers': [],
                        'whitespace_chunk': False,
                        'whitespace_lines': [],
                    },
                    'numlines': 1,
                },
            ])
        self.assertNotIn('text_lines', extra_context)
        self.assertNotIn('rendered_lines', extra_context)

    def test_get_comment_line_range_legacy(self) -> None:
        """Testing MarkdownReviewUI.get_comment_line_range with a legacy
        rendered comment
        """
        review_ui = MarkdownReviewUI(
            review_request=self.review_request,
            obj=self._create_new_revision())

        self.assertEqual(
            review_ui._get_legacy_rendered_lines(),
            [
                '<h1>Title</h1>',
                '\n',
                '<p/>',
                '\n',
                '<p>New text</p>',
                '\n',
                '<p/>',
                '\n',
                '<p>More</p>',
            ])
        self.assertEqual(
            review_ui.get_rendered_lines(),
            [
                '<h1>Title</h1>',
                '<p data-md-gap="block">New text</p>',
                '<p data-md-gap="block">More</p>',
            ])
        self.assertEqual(
            review_ui.get_comment_line_range({
                'beginLineNum': 3,
                'endLineNum': 9,
                'viewMode': 'rendered',
            }),
            (1, 3))
        self.assertEqual(
            review_ui.get_comment_line_range({
                'beginLineNum': 7,
                'endLineNum': 7,
                'viewMode': 'rendered',
            }),
            (2, 2))

    def test_get_comment_line_range_legacy_merged_and_split(self) -> None:
        """Testing MarkdownReviewUI.get_comment_line_range with a legacy
        rendered comment on rows that were merged or split
        """
        attachment = self.create_file_attachment(
            self.review_request,
            attachment_history=self.attachment_history,
            attachment_revision=1,
            orig_filename='revision2.md',
            mimetype='text/x-markdown',
            file_content=(b'First line\n'
                          b'second line.\n'
                          b'\n'
                          b'| A | B |\n'
                          b'|---|---|\n'
                          b'| 1 | 2 |\n'
                          b'| 3 | 4 |\n'))
        review_ui = MarkdownReviewUI(review_request=self.review_request,
                                     obj=attachment)

        # Legacy rows 1-2 are the lines of the paragraph, 3 is blank, and
        # 4 is the whole table.
        self.assertEqual(len(review_ui._get_legacy_rendered_lines()), 4)
        self.assertEqual(len(review_ui.get_rendered_lines()), 4)

        self.assertEqual(
            review_ui.get_comment_line_range({
                'beginLineNum': 2,
                'endLineNum': 2,
                'viewMode': 'rendered',
            }),
            (1, 1))
        self.assertEqual(
            review_ui.get_comment_line_range({
                'beginLineNum': 4,
                'endLineNum': 4,
                'viewMode': 'rendered',
            }),
            (2, 4))

    def test_get_comment_line_range_legacy_after_code(self) -> None:
        """Testing MarkdownReviewUI.get_comment_line_range with legacy
        rendered comments after code blocks that codehilite trimmed
        """
        contents = {
            'colon marker': b'    :::python\n    x = 1\n',
            'shebang marker': b'    #!python\n    x = 1\n',
            'shebang path': b'    #!/usr/bin/env python\n    x = 1\n',
            'blank lines': b'```\n\nx = 1\n\n```\n',
        }

        for name, code in contents.items():
            with self.subTest(name):
                attachment = self.create_file_attachment(
                    self.review_request,
                    orig_filename='code.md',
                    mimetype='text/x-markdown',
                    file_content=code + b'\nA\n\nB\n\nC\n')
                review_ui = MarkdownReviewUI(
                    review_request=self.review_request,
                    obj=attachment)
                legacy_rows = review_ui._get_legacy_rendered_lines()
                rows = review_ui.get_rendered_lines()

                # Each paragraph's legacy row maps to its current row.
                for text in ('A', 'B', 'C'):
                    legacy_row_num = self._find_row_num(legacy_rows, text)
                    row_num = self._find_row_num(rows, text)

                    self.assertEqual(
                        review_ui.get_comment_line_range({
                            'beginLineNum': legacy_row_num,
                            'endLineNum': legacy_row_num,
                            'viewMode': 'rendered',
                        }),
                        (row_num, row_num))

    def test_get_comment_line_range_legacy_with_diff(self) -> None:
        """Testing MarkdownReviewUI.get_comment_line_range with a legacy
        rendered comment on a diff
        """
        review_ui = MarkdownReviewUI(
            review_request=self.review_request,
            obj=self._create_new_revision(old_content=b'# Title\n\n\n'
                                                      b'Old text\n'))
        review_ui.set_diff_against(self.attachment)

        # Legacy diff rows 1-4 are the heading and blank rows, 5 is the
        # changed paragraph, and 6-9 are inserted.
        self.assertEqual(
            review_ui.get_comment_line_range({
                'beginLineNum': 5,
                'endLineNum': 9,
                'viewMode': 'rendered',
            }),
            (2, 3))
        self.assertEqual(
            review_ui.get_comment_line_range({
                'beginLineNum': 2,
                'endLineNum': 6,
                'viewMode': 'rendered',
            }),
            (1, 2))

    def test_get_comment_line_range_current(self) -> None:
        """Testing MarkdownReviewUI.get_comment_line_range with a current
        rendered comment
        """
        review_ui = MarkdownReviewUI(
            review_request=self.review_request,
            obj=self._create_new_revision())

        self.assertEqual(
            review_ui.get_comment_line_range({
                'beginLineNum': 2,
                'endLineNum': 3,
                'renderVersion': 2,
                'viewMode': 'rendered',
            }),
            (2, 3))

    def test_get_comment_line_range_source(self) -> None:
        """Testing MarkdownReviewUI.get_comment_line_range with a source
        comment
        """
        review_ui = MarkdownReviewUI(
            review_request=self.review_request,
            obj=self._create_new_revision())

        self.assertEqual(
            review_ui.get_comment_line_range({
                'beginLineNum': 5,
                'endLineNum': 6,
                'viewMode': 'source',
            }),
            (5, 6))

    def test_serialize_comment_legacy(self) -> None:
        """Testing MarkdownReviewUI.serialize_comment with a legacy rendered
        comment
        """
        new_attachment = self._create_new_revision()
        comment = self.create_file_attachment_comment(
            self.review,
            new_attachment,
            extra_fields={
                'beginLineNum': 5,
                'endLineNum': 9,
                'viewMode': 'rendered',
            })

        request = RequestFactory().get('/')
        request.user = User.objects.get(username='doc')

        review_ui = MarkdownReviewUI(review_request=self.review_request,
                                     obj=new_attachment)
        review_ui.request = request

        data = review_ui.serialize_comment(comment)

        self.assertEqual(data['beginLineNum'], 2)
        self.assertEqual(data['endLineNum'], 3)
        self.assertEqual(data.get('renderVersion'), 2)
        self.assertEqual(data['viewMode'], 'rendered')

    def _find_row_num(
        self,
        rows: Sequence[str],
        text: str,
    ) -> int:
        """Return the 1-based number of the row with the given text.

        Version Added:
            9.0

        Args:
            rows (list of str):
                The rendered rows.

            text (str):
                The text of the row to find.

        Returns:
            int:
            The row number.
        """
        for i, row in enumerate(rows):
            if strip_tags(row) == text:
                return i + 1

        self.fail(f'No row has the text {text!r}')

    def _create_new_revision(
        self,
        old_content: (bytes | None) = None,
    ) -> FileAttachment:
        """Create a new revision of the attachment for comment tests.

        Version Added:
            9.0

        Args:
            old_content (bytes, optional):
                New content for the first revision, if it should be changed.

        Returns:
            reviewboard.attachments.models.FileAttachment:
            The new attachment revision.
        """
        if old_content is not None:
            self.attachment.file.save(self.attachment.file.name,
                                      ContentFile(old_content))

        return self.create_file_attachment(
            self.review_request,
            attachment_history=self.attachment_history,
            attachment_revision=1,
            orig_filename='revision2.md',
            mimetype='text/x-markdown',
            file_content=b'# Title\n\n\nNew text\n\n\nMore\n')
