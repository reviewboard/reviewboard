"""Unit tests for reviewboard.reviews.ui.text.MarkdownReviewUI."""
from __future__ import unicode_literals

from django.test.client import RequestFactory

from reviewboard.reviews.ui.markdownui import MarkdownReviewUI
from reviewboard.testing import TestCase


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

    def test_get_extra_context_with_diff(self):
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
                        [
                            1,
                            1,
                            'This is revision <span class="ge">*1*</span>.',
                            [(0, 1), (4, 4), (17, 20)],
                            1,
                            'And <span class="gs">**this**</span> is '
                            'revision 2.',
                            [(0, 7), (10, 12), (25, 26)],
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
                        [
                            1,
                            1,
                            '<p>This is revision <em>1</em>.</p>',
                            [(0, 1), (17, 18)],
                            1,
                            '<p>And <strong>this</strong> is revision 2.</p>',
                            [(0, 5), (21, 22)],
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
                },
            ])
        self.assertNotIn('text_lines', extra_context)
        self.assertNotIn('rendered_lines', extra_context)
