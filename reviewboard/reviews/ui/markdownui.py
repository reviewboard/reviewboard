from __future__ import unicode_literals

import logging

from django.utils.translation import ugettext as _
from djblets.markdown import iter_markdown_lines
from pygments.lexers import TextLexer

from reviewboard.reviews.chunk_generators import MarkdownDiffChunkGenerator
from reviewboard.reviews.ui.text import TextBasedReviewUI
from reviewboard.reviews.markdown_utils import render_markdown_from_file


class MarkdownReviewUI(TextBasedReviewUI):
    """A Review UI for markdown files.

    This renders the markdown to HTML, and allows users to comment on each
    top-level block (header, paragraph, list, code block, etc).
    """
    supported_mimetypes = ['text/x-markdown']
    object_key = 'markdown'
    can_render_text = True
    rendered_chunk_generator_cls = MarkdownDiffChunkGenerator

    extra_css_classes = ['markdown-review-ui']

    js_view_class = 'RB.MarkdownReviewableView'

    def generate_render(self):
        with self.obj.file as f:
            f.open()
            rendered = render_markdown_from_file(f)

        try:
            for line in iter_markdown_lines(rendered):
                yield line
        except Exception as e:
            logging.error('Failed to parse resulting Markdown XHTML for '
                          'file attachment %d: %s',
                          self.obj.pk, e,
                          exc_info=True)
            yield _('Error while rendering Markdown content: %s') % e

    def get_source_lexer(self, filename, data):
        return TextLexer()
