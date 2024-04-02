"""A Review UI for Markdown files."""

from __future__ import annotations

import logging
from typing import Iterator

from django.utils.translation import gettext as _
from djblets.markdown import iter_markdown_lines
from pygments.lexers import TextLexer

from reviewboard.attachments.models import FileAttachment
from reviewboard.reviews.chunk_generators import MarkdownDiffChunkGenerator
from reviewboard.reviews.ui.text import TextBasedReviewUI
from reviewboard.reviews.markdown_utils import render_markdown


logger = logging.getLogger(__name__)


class MarkdownReviewUI(TextBasedReviewUI):
    """A Review UI for Markdown files.

    This renders the markdown to HTML, and allows users to comment on each
    top-level block (header, paragraph, list, code block, etc).
    """

    supported_mimetypes = ['text/markdown', 'text/x-markdown']
    object_key = 'markdown'
    can_render_text = True
    rendered_chunk_generator_cls = MarkdownDiffChunkGenerator

    extra_css_classes = ['markdown-review-ui']

    js_view_class = 'RB.MarkdownReviewableView'

    def generate_render(self) -> Iterator[str]:
        """Generate a render of the text.

        Yields:
            str:
            The rendered lines of content.
        """
        assert isinstance(self.obj, FileAttachment)

        with self.obj.file as f:
            f.open()
            rendered = render_markdown(f.read())

        try:
            for line in iter_markdown_lines(rendered):
                yield line
        except Exception as e:
            logger.error('Failed to parse resulting Markdown XHTML for '
                         'file attachment %d: %s',
                         self.obj.pk, e,
                         exc_info=True)
            yield _('Error while rendering Markdown content: %s') % e

    def get_source_lexer(self, filename, data):
        return TextLexer()
