"""Unit tests for reviewboard.reviews.ui.text.MarkdownReviewUI."""

from __future__ import annotations

from django.test.client import RequestFactory

from reviewboard.reviews.ui.markdownui import (
    MarkdownReviewUI,
    get_row_text_ranges,
    map_text_ranges,
)
from reviewboard.testing import TestCase


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
