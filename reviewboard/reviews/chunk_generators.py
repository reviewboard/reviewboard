from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

from django.utils.html import format_html, strip_tags
from django.utils.translation import gettext as _

from reviewboard.diffviewer.chunk_generator import (
    DiffChunkGenerator,
    RawDiffChunkGenerator,
)
from reviewboard.diffviewer.opcode_generator import get_diff_opcode_generator

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence
    from typing import ClassVar

    from reviewboard.diffviewer.chunk_generator import DiffChunk
    from reviewboard.diffviewer.diffutils import DiffRegions
    from reviewboard.diffviewer.opcode_generator import DiffOpcodeGenerator
    from reviewboard.reviews.ui.text import TextBasedReviewUI


logger = logging.getLogger(__name__)


#: Matches the attribute marking the gap before a rendered Markdown block.
#:
#: This must match what :py:mod:`reviewboard.reviews.ui.markdownui` adds.
#:
#: Version Added:
#:     9.0
_BLOCK_GAP_RE = re.compile(r' data-md-gap="[a-z]*"')


class MarkdownDiffChunkGenerator(RawDiffChunkGenerator):
    """A chunk generator for rendered Markdown content.

    This works like a standard RawDiffChunkGenerator, but handles showing
    changes within a line for HTML-rendered Markdown.
    """

    def get_comparison_lines(
        self,
        lines: Sequence[str],
    ) -> Sequence[str]:
        """Return the lines to compare when finding changes.

        A block's gap depends on the block before it, so it can change when
        the block itself didn't. Gaps are ignored when comparing.

        Version Added:
            9.0

        Args:
            lines (list of str):
                The lines of one side of the diff.

        Returns:
            list of str:
            The lines to compare.
        """
        return [
            _BLOCK_GAP_RE.sub('', line)
            for line in lines
        ]

    def get_line_changed_regions(
        self,
        old_line_num: int | None,
        old_line: str | None,
        new_line_num: int | None,
        new_line: str | None,
    ) -> tuple[DiffRegions, DiffRegions]:
        """Return information on changes between two lines.

        This returns the regions between lines of rendered Markdown that
        have changed.

        Only text changes are highlighted, and not formatting changes (such as
        the addition of bold text).

        Args:
            old_line_num (int):
                The line number for the old line.

            old_line (str):
                The contents of the old line.

            new_line_num (int):
                The line number for the new line.

            new_line (str):
                The contents of the new line.

        Returns:
            tuple:
            A 2-tuple of:

            Tuple:
                0 (reviewboard.diffviewer.diffutils.DiffRegions):
                    A list of (int, int) for changed regions in the old line.

                1 (reviewboard.diffviewer.diffutils.DiffRegions):
                    A list of (int, int) for changed regions in the new line.
        """
        return super().get_line_changed_regions(
            old_line_num,
            strip_tags(old_line or ''),
            new_line_num,
            strip_tags(new_line or ''))


class RenderedDiffChunkGenerator(DiffChunkGenerator):
    """A chunk generator showing a FileDiff's rendered text as rows.

    This loads both sides of the file the same way as
    :py:class:`~reviewboard.diffviewer.chunk_generator.DiffChunkGenerator`.
    That includes base FileDiffs and interdiffs. Each side is then rendered
    into rows by a text review UI, and the rows are diffed instead of the
    source lines.

    Do not use this class directly. Use :py:meth:`TextBasedReviewUI.
    get_rendered_diff_chunk_generator_cls() <reviewboard.reviews.ui.text.
    TextBasedReviewUI.get_rendered_diff_chunk_generator_cls>` to get one for a
    given review UI.

    This does not support interdiff filtering. That only works with source
    lines, which don't map cleanly to rendered rows.

    Version Added:
        9.0
    """

    stores_line_counts = False

    #: The text review UI that renders the rows.
    review_ui_cls: ClassVar[type[TextBasedReviewUI]]

    def make_cache_key(self) -> str:
        """Return a new cache key for any generated chunks.

        Returns:
            str:
            The new cache key.
        """
        review_ui_cls = self.review_ui_cls

        return (
            f'{super().make_cache_key()}-rendered-{review_ui_cls.__name__}-'
            f'v{review_ui_cls.rendered_lines_version}'
        )

    def get_opcode_generator(self) -> DiffOpcodeGenerator:
        """Return the DiffOpcodeGenerator used to generate diff opcodes.

        This skips interdiff filtering, which only works on source lines.

        Returns:
            reviewboard.diffviewer.opcode_generator.DiffOpcodeGenerator:
            The opcode generator.
        """
        return get_diff_opcode_generator(self.differ)

    def generate_chunks(
        self,
        old: bytes | Sequence[bytes],
        new: bytes | Sequence[bytes],
        old_encoding_list: (Sequence[str] | None) = None,
        new_encoding_list: (Sequence[str] | None) = None,
    ) -> Iterator[DiffChunk]:
        """Generate chunks for the difference between two rendered files.

        If a side fails to render, it's shown as a single row with the
        error.

        Args:
            old (bytes):
                The old file content.

            new (bytes):
                The new file content.

            old_encoding_list (list of str, optional):
                The encodings that ``old`` may be encoded in.

            new_encoding_list (list of str, optional):
                The encodings that ``new`` may be encoded in.

        Yields:
            reviewboard.diffviewer.chunk_generator.DiffChunk:
            A rendered chunk.
        """
        assert isinstance(old, bytes)
        assert isinstance(new, bytes)

        if old_encoding_list is None:
            old_encoding_list = self.encoding_list

        if new_encoding_list is None:
            new_encoding_list = self.encoding_list

        old_text = self.normalize_source_string(old, old_encoding_list)[0]
        new_text = self.normalize_source_string(new, new_encoding_list)[0]

        yield from super().generate_chunks(
            self._render_rows(old_text),
            self._render_rows(new_text),
            old_encoding_list=['utf-8'],
            new_encoding_list=['utf-8'])

    def _render_rows(
        self,
        text: str,
    ) -> list[bytes]:
        """Render one side of the diff into rows.

        Version Added:
            9.0

        Args:
            text (str):
                The text to render.

        Returns:
            list of bytes:
            The UTF-8-encoded HTML for each row.
        """
        try:
            rows = self.review_ui_cls.render_text_rows(text)
        except Exception as e:
            logger.exception(
                'Failed to render text for FileDiff %s with %s: %s',
                self.filediff.pk, self.review_ui_cls.__name__, e)
            rows = [
                format_html(
                    _('Error while rendering content: {error}'),
                    error=e),
            ]

        return [
            row.encode('utf-8')
            for row in rows
        ]
