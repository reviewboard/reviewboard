"""Unit tests for reviewboard.reviews.ui.text.TextBasedReviewUI."""

from __future__ import annotations

from typing import TYPE_CHECKING

import kgb
from django.core.cache import cache
from django.test.client import RequestFactory
from django.utils.translation import get_language
from djblets.cache.backend import make_cache_key

from reviewboard.diffviewer.chunk_generator import RawDiffChunkGenerator
from reviewboard.diffviewer.settings import DiffSettings
from reviewboard.reviews.chunk_generators import RenderedDiffChunkGenerator
from reviewboard.reviews.ui import review_ui_registry
from reviewboard.reviews.ui.markdownui import MarkdownReviewUI
from reviewboard.reviews.ui.text import (
    TextBasedReviewUI,
    get_rendered_text_review_ui,
)
from reviewboard.testing import TestCase

if TYPE_CHECKING:
    from collections.abc import Sequence


class TextBasedReviewUITests(kgb.SpyAgency, TestCase):
    """Unit tests for reviewboard.reviews.ui.text.TextBasedReviewUI."""

    fixtures = ['test_users']

    def setUp(self):
        super(TextBasedReviewUITests, self).setUp()

        self.review_request = self.create_review_request()
        self.attachment_history = self.create_file_attachment_history(
            self.review_request)
        self.attachment = self.create_file_attachment(
            self.review_request,
            attachment_history=self.attachment_history,
            attachment_revision=0,
            caption='Revision 1 caption',
            orig_filename='revision1.txt',
            mimetype='text/plain',
            file_content=b'This is revision 1.')
        self.review = self.create_review(self.review_request)

    def test_get_extra_context(self):
        """Testing TextBasedReviewUI.get_extra_context"""
        new_attachment = self.create_file_attachment(
            self.review_request,
            attachment_history=self.attachment_history,
            attachment_revision=1,
            caption='Revision 2 caption',
            orig_filename='revision2.txt',
            mimetype='text/plain',
            file_content=b'And this is revision 2.')

        review_ui = TextBasedReviewUI(review_request=self.review_request,
                                      obj=new_attachment)

        request = RequestFactory().get('/')
        extra_context = review_ui.get_extra_context(request)

        self.assertFalse(extra_context['is_diff'])
        self.assertFalse(extra_context['diff_type_mismatch'])
        self.assertEqual(extra_context['filename'], 'revision2.txt')
        self.assertEqual(extra_context['revision'], 1)
        self.assertEqual(extra_context['num_revisions'], 2)
        self.assertNotIn('diff_caption', extra_context)
        self.assertNotIn('diff_filename', extra_context)
        self.assertNotIn('diff_revision', extra_context)
        self.assertNotIn('source_chunks', extra_context)
        self.assertNotIn('rendered_chunks', extra_context)
        self.assertEqual(extra_context['text_lines'],
                         ['<pre>And this is revision 2.</pre>'])
        self.assertEqual(extra_context['rendered_lines'], [])

    def test_get_extra_context_with_diff(self) -> None:
        """Testing TextBasedReviewUI.get_extra_context with diff_against_obj"""
        new_attachment = self.create_file_attachment(
            self.review_request,
            attachment_history=self.attachment_history,
            attachment_revision=1,
            caption='Revision 2 caption',
            orig_filename='revision2.txt',
            mimetype='text/plain',
            file_content=b'And this is revision 2.')

        review_ui = TextBasedReviewUI(review_request=self.review_request,
                                      obj=new_attachment)
        review_ui.set_diff_against(self.attachment)

        request = RequestFactory().get('/')
        extra_context = review_ui.get_extra_context(request)

        self.assertTrue(extra_context['is_diff'])
        self.assertFalse(extra_context['diff_type_mismatch'])
        self.assertEqual(extra_context['filename'], 'revision2.txt')
        self.assertEqual(extra_context['revision'], 1)
        self.assertEqual(extra_context['num_revisions'], 2)
        self.assertEqual(extra_context['diff_caption'], 'Revision 1 caption')
        self.assertEqual(extra_context['diff_filename'], 'revision1.txt')
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
                            'This is revision 1.',
                            [(0, 1), (17, 18)],
                            1,
                            'And this is revision 2.',
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
        self.assertEqual(list(extra_context['rendered_chunks']), [])
        self.assertNotIn('text_lines', extra_context)
        self.assertNotIn('rendered_lines', extra_context)

    def test_get_extra_context_with_diff_cached(self) -> None:
        """Testing TextBasedReviewUI.get_extra_context with diff_against_obj
        caches diff chunks
        """
        new_attachment = self.create_file_attachment(
            self.review_request,
            attachment_history=self.attachment_history,
            attachment_revision=1,
            caption='Revision 2 caption',
            orig_filename='revision2.txt',
            mimetype='text/plain',
            file_content=b'And this is revision 2.')

        self.spy_on(RawDiffChunkGenerator.get_chunks_uncached,
                    owner=RawDiffChunkGenerator)

        request = RequestFactory().get('/')

        for i in range(2):
            review_ui = TextBasedReviewUI(review_request=self.review_request,
                                          obj=new_attachment)
            review_ui.set_diff_against(self.attachment)
            extra_context = review_ui.get_extra_context(request)

            self.assertEqual(len(list(extra_context['source_chunks'])), 1)
            self.assertEqual(list(extra_context['rendered_chunks']), [])

        # One call each for source and rendered, on the first pass only.
        self.assertSpyCallCount(RawDiffChunkGenerator.get_chunks_uncached, 2)

        state_hash = DiffSettings.create().state_hash

        for view_mode in ('source', 'rendered'):
            self.assertIn(
                make_cache_key([
                    'text-attachment-diff',
                    view_mode,
                    '1',
                    str(self.attachment.pk),
                    str(new_attachment.pk),
                    state_hash,
                    get_language(),
                ]),
                cache,
            )

    def test_get_extra_context_too_large(self) -> None:
        """Testing TextBasedReviewUI.get_extra_context with a file over
        max_display_file_size
        """
        self.spy_on(TextBasedReviewUI.get_text_lines,
                    owner=TextBasedReviewUI)

        review_ui = TextBasedReviewUI(review_request=self.review_request,
                                      obj=self.attachment)
        review_ui.max_display_file_size = 5

        request = RequestFactory().get('/')
        extra_context = review_ui.get_extra_context(request)

        self.assertTrue(extra_context['too_large'])
        self.assertNotIn('text_lines', extra_context)
        self.assertNotIn('rendered_lines', extra_context)
        self.assertSpyNotCalled(TextBasedReviewUI.get_text_lines)

    def test_get_extra_context_with_diff_too_large(self) -> None:
        """Testing TextBasedReviewUI.get_extra_context with diff_against_obj
        over max_display_file_size
        """
        new_attachment = self.create_file_attachment(
            self.review_request,
            attachment_history=self.attachment_history,
            attachment_revision=1,
            caption='Revision 2 caption',
            orig_filename='revision2.txt',
            mimetype='text/plain',
            file_content=b'Short.')

        self.spy_on(RawDiffChunkGenerator.get_chunks_uncached,
                    owner=RawDiffChunkGenerator)

        review_ui = TextBasedReviewUI(review_request=self.review_request,
                                      obj=new_attachment)
        review_ui.set_diff_against(self.attachment)
        review_ui.max_display_file_size = 10

        request = RequestFactory().get('/')
        extra_context = review_ui.get_extra_context(request)

        self.assertTrue(extra_context['too_large'])
        self.assertNotIn('source_chunks', extra_context)
        self.assertNotIn('rendered_chunks', extra_context)
        self.assertSpyNotCalled(RawDiffChunkGenerator.get_chunks_uncached)

    def test_render_comment_thumbnail_too_large(self) -> None:
        """Testing TextBasedReviewUI.render_comment_thumbnail with a file
        over max_display_file_size
        """
        comment = self.create_file_attachment_comment(
            self.review,
            self.attachment,
            extra_fields={
                'beginLineNum': 1,
                'endLineNum': 1,
                'viewMode': 'source',
            })

        review_ui = TextBasedReviewUI(review_request=self.review_request,
                                      obj=self.attachment)
        review_ui.max_display_file_size = 5

        self.assertEqual(
            review_ui.render_comment_thumbnail(comment, 1, 1, 'source'),
            '')

    def test_render_too_large(self) -> None:
        """Testing TextBasedReviewUI.render_to_string with a file over
        max_display_file_size
        """
        review_ui = TextBasedReviewUI(review_request=self.review_request,
                                      obj=self.attachment)
        review_ui.max_display_file_size = 5

        request = RequestFactory().get('/')
        request.user = self.review_request.submitter

        html = review_ui.render_to_string(request)

        self.assertIn('This file is too large to display.', html)
        self.assertNotIn('This is revision 1.', html)


class RenderedDiffChunkGeneratorTests(TestCase):
    """Unit tests for TextBasedReviewUI.get_rendered_diff_chunk_generator_cls.

    Version Added:
        9.0
    """

    fixtures = ['test_scmtools']

    def test_get_chunks(self) -> None:
        """Testing TextBasedReviewUI.get_rendered_diff_chunk_generator_cls
        with a review UI that renders text
        """
        class UpperCaseReviewUI(TextBasedReviewUI):
            can_render_text = True

            @classmethod
            def render_text_rows(
                cls,
                text: str,
            ) -> Sequence[str]:
                return [
                    f'<p>{line.upper()}</p>'
                    for line in text.splitlines()
                ]

        generator_cls = \
            UpperCaseReviewUI.get_rendered_diff_chunk_generator_cls()
        self.assertIs(
            generator_cls,
            UpperCaseReviewUI.get_rendered_diff_chunk_generator_cls())
        self.assertTrue(issubclass(generator_cls, RenderedDiffChunkGenerator))

        # The Test SCM returns "Hello, world!" for the original file.
        repository = self.create_repository(tool_name='Test')
        filediff = self.create_filediff(
            diffset=self.create_diffset(repository=repository),
            diff=(
                b'--- README\n'
                b'+++ README\n'
                b'@@ -1 +1 @@\n'
                b'-Hello, world!\n'
                b'+Goodbye, world!\n'
            ))

        generator = generator_cls(request=None,
                                  filediff=filediff,
                                  diff_settings=DiffSettings.create())

        self.assertEqual(
            [
                (line[2], line[5])
                for chunk in generator.get_chunks()
                for line in chunk['lines']
            ],
            [
                ('<p>HELLO, WORLD!</p>', '<p>GOODBYE, WORLD!</p>'),
            ])


class GetRenderedTextReviewUITests(TestCase):
    """Unit tests for get_rendered_text_review_ui.

    Version Added:
        9.0
    """

    def test_with_markdown(self) -> None:
        """Testing get_rendered_text_review_ui with Markdown files"""
        self.assertIs(get_rendered_text_review_ui('README.md'),
                      MarkdownReviewUI)
        self.assertIs(get_rendered_text_review_ui('docs/guide.md'),
                      MarkdownReviewUI)

    def test_without_rendered_view(self) -> None:
        """Testing get_rendered_text_review_ui with files that can't be
        rendered
        """
        self.assertIsNone(get_rendered_text_review_ui('README.rst'))
        self.assertIsNone(get_rendered_text_review_ui('README.txt'))
        self.assertIsNone(get_rendered_text_review_ui('image.png'))
        self.assertIsNone(get_rendered_text_review_ui('README'))

    def test_with_registered_review_ui(self) -> None:
        """Testing get_rendered_text_review_ui with a registered review UI
        that renders text
        """
        class CSVReviewUI(TextBasedReviewUI):
            supported_mimetypes = ['text/csv']
            can_render_text = True

        review_ui_registry.register(CSVReviewUI)

        try:
            self.assertIs(get_rendered_text_review_ui('data.csv'),
                          CSVReviewUI)
        finally:
            review_ui_registry.unregister(CSVReviewUI)
