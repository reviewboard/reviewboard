"""Unit tests for reviewboard.reviews.ui.markdownui."""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.test.client import RequestFactory

from reviewboard.reviews.ui.markdownui import (
    MarkdownReviewUI,
    get_row_text_ranges,
    map_text_ranges,
    render_markdown_blocks,
)
from reviewboard.testing import TestCase

if TYPE_CHECKING:
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
                '<p>One two.</p>',
                '<p>Three.</p>',
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
                '<ul style="--md-list-depth: 1"><li>b</li></ul>',
                '<ul style="--md-list-depth: 0"><li>c</li></ul>',
                '<p>Text</p>',
                '<ol start="1" style="--md-list-depth: 0"><li>x</li></ol>',
                '<ol start="2" style="--md-list-depth: 0"><li>y</li></ol>',
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
                '<ul style="--md-list-depth: 1"><li>b</li></ul>',
                '<ul style="--md-list-depth: 0">'
                '<li class="md-list-continuation"><p>Text</p></li></ul>',
            ])

    def test_blockquote(self) -> None:
        """Testing render_markdown_blocks with a blockquote"""
        self.assertEqual(
            render_markdown_blocks('> a\n'
                                   '>\n'
                                   '> - b\n'),
            [
                '<blockquote><p>a</p></blockquote>',
                '<blockquote><ul style="--md-list-depth: 0"><li>b</li></ul>'
                '</blockquote>',
            ])

    def test_table(self) -> None:
        """Testing render_markdown_blocks with a table"""
        self.assertEqual(
            render_markdown_blocks('| A | B |\n'
                                   '|---|---|\n'
                                   '| 1 | 2 |\n'
                                   '| 3 | 4 |\n'),
            [
                '<table><thead><tr><th>A</th><th>B</th></tr></thead>'
                '</table>',
                '<table><tbody><tr><td>1</td><td>2</td></tr></tbody>'
                '</table>',
                '<table><tbody><tr><td>3</td><td>4</td></tr></tbody>'
                '</table>',
            ])

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
                '<div class="codehilite"><pre>c</pre></div>',
            ])


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
        self.assertEqual(extra_context['text_lines'],
                         ['<pre>And **this** is revision 2.</pre>'])
        self.assertEqual(extra_context['rendered_lines'],
                         ['<p>And <strong>this</strong> is revision 2.</p>'])

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
                '<p>New text</p>',
                '<p>More</p>',
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
