"""A Review UI for Markdown files."""

from __future__ import annotations

import logging
import re
from bisect import bisect_right
from html import unescape
from typing import TYPE_CHECKING

from django.utils.html import strip_tags
from django.utils.translation import gettext as _
from djblets.markdown import iter_markdown_lines
from pygments.lexers import TextLexer

from reviewboard.attachments.models import FileAttachment
from reviewboard.reviews.chunk_generators import MarkdownDiffChunkGenerator
from reviewboard.reviews.ui.text import TextBasedReviewUI
from reviewboard.reviews.markdown_utils import render_markdown

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence


logger = logging.getLogger(__name__)


#: Regex for a row with a code block.
#:
#: Version Added:
#:     9.0
_CODE_ROW_RE = re.compile(
    r'^<div class="codehilite[^"]*"><pre>(?P<content>.*)</pre></div>$',
    re.S)

#: Regex to find a row that does not include any text content.
#:
#: Version Added:
#:     9.0
_CONTENT_WITHOUT_TEXT_RE = re.compile(r'<(?:img|hr)\b[^>]*>')

#: Regex to find whitespace.
#:
#: Version Added:
#:     9.0
_WHITESPACE_RE = re.compile(r'\s+')

#: A character that stands in for content without text.
_PLACEHOLDER = '￼'


def get_row_text_ranges(
    rows: Sequence[str],
) -> Sequence[tuple[int, int]]:
    """Return the position of each row's text in the whole document.

    Positions count text without whitespace, so that rows from different
    layouts of the same document can be lined up. Images and horizontal
    rules count as one character. Each line of code also gets one extra
    character, so empty lines still have a position.

    Version Added:
        9.0

    Args:
        rows (list of str):
            The HTML for each row.

    Returns:
        list of tuple:
        A ``(start, end)`` tuple for each row.
    """
    ranges: list[tuple[int, int]] = []
    pos = 0

    for row in rows:
        size = len(_get_row_text(row))
        ranges.append((pos, pos + size))
        pos += size

    return ranges


def map_text_ranges(
    old_ranges: Sequence[tuple[int, int]],
    new_ranges: Sequence[tuple[int, int]],
) -> list[tuple[int, int]]:
    """Map rows from one layout to rows of another by text position.

    Each old row maps to the new rows its text overlaps. Old rows without
    text map to the new row before them.

    Version Added:
        9.0

    Args:
        old_ranges (list of tuple):
            The text ranges of the old rows.

        new_ranges (list of tuple):
            The text ranges of the new rows.

    Returns:
        list of tuple:
        A ``(first, last)`` tuple of 0-based new row indexes for each old
        row.
    """
    num_new = len(new_ranges)

    if num_new == 0:
        return [(0, 0)] * len(old_ranges)

    new_starts = [
        start
        for start, end in new_ranges
    ]
    result: list[tuple[int, int]] = []

    for start, end in old_ranges:
        # Find the last new row starting at or before this position.
        first = max(bisect_right(new_starts, start) - 1, 0)

        if start == end:
            # Rows without text belong to the row before them.
            while first > 0 and new_ranges[first][0] >= start:
                first -= 1

            result.append((first, first))
            continue

        # Skip past new rows that end before this text starts.
        while new_ranges[first][1] <= start and first + 1 < num_new:
            first += 1

        last = first

        while last + 1 < num_new and new_ranges[last + 1][0] < end:
            last += 1

        result.append((first, last))

    return result


def _get_row_text(
    row: str,
) -> str:
    """Return a row's text for positioning.

    Args:
        row (str):
            The HTML for the row.

    Returns:
        str:
        The text, without whitespace.
    """
    m = _CODE_ROW_RE.match(row)
    suffix = ''

    # The original layout ends each code block with a row holding only
    # "</code>". That row isn't a line of code.
    if m and m.group('content') != '</code>':
        suffix = '\n'

    text = _CONTENT_WITHOUT_TEXT_RE.sub(_PLACEHOLDER, row)
    text = unescape(strip_tags(text))

    return _WHITESPACE_RE.sub('', text) + suffix


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
