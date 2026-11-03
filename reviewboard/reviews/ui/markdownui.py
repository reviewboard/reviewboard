"""A Review UI for Markdown files."""

from __future__ import annotations

import logging
import re
from bisect import bisect_right
from html import unescape
from typing import TYPE_CHECKING, cast
from xml.dom.minidom import Element, Node, Text

from django.utils.encoding import force_bytes, force_str
from django.utils.html import strip_tags
from django.utils.translation import gettext as _
from djblets.cache.backend import cache_memoize
from djblets.markdown import get_markdown_element_tree
from markdown import markdown
from pygments.lexers import TextLexer

from reviewboard.attachments.models import FileAttachment
from reviewboard.reviews.chunk_generators import MarkdownDiffChunkGenerator
from reviewboard.reviews.markdown_utils import (
    MARKDOWN_KWARGS,
    clean_markdown_html,
    render_markdown,
)
from reviewboard.reviews.ui.legacy_markdown import iter_legacy_markdown_lines
from reviewboard.reviews.ui.text import TextBasedReviewUI

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence

    from pygments.lexers import Lexer
    from typelets.json import JSONDict

    from reviewboard.reviews.models import FileAttachmentComment
    from reviewboard.reviews.ui.text import SerializedTextComment


logger = logging.getLogger(__name__)


#: Options for rendering Markdown file attachments.
#:
#: This drops the extensions that keep the render lined up with the source
#: text, so paragraphs are shown as normal flowing text.
#:
#: Version Added:
#:     9.0
_MARKDOWN_KWARGS = {
    **MARKDOWN_KWARGS,
    'extensions': [
        extension
        for extension in cast(list[str], MARKDOWN_KWARGS['extensions'])
        if extension not in {
            'markdown.extensions.nl2br',
            'djblets.markdown.extensions.wysiwyg',
        }
    ],
}


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

#: Regex to find newlines.
#:
#: Version Added:
#:     9.0
_NEWLINE_RE = re.compile(r'\s*\n\s*')

#: A character that stands in for content without text.
_PLACEHOLDER = '￼'


def render_markdown_blocks(
    text: str | bytes,
) -> Sequence[str]:
    """Render Markdown and split it into reviewable rows.

    Each heading, paragraph, list item, table row, and line of code becomes a
    row. Blocks inside a blockquote become their own rows, each wrapped in a
    blockquote.

    Version Added:
        9.0

    Args:
        text (str or bytes):
            The Markdown text.

    Returns:
        list of str:
        The HTML for each row.
    """
    html = clean_markdown_html(markdown(force_str(text), **_MARKDOWN_KWARGS))
    rows: list[str] = []

    for node in get_markdown_element_tree(html):
        _split_node(node, rows)

    # Rows are shown inside <pre> in diffs, so line breaks from the source
    # would show there. In HTML, they're only spaces.
    #
    # Rows containing a <pre> (such as list items holding a code block) are
    # left alone. Handle those if they show line breaks.
    for i, row in enumerate(rows):
        if '<pre' not in row:
            rows[i] = _NEWLINE_RE.sub(' ', row)

    return rows


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


def _split_node(
    node: Node,
    rows: list[str],
    list_depth: int = 0,
    quote_depth: int = 0,
) -> None:
    """Split a node of rendered Markdown into rows.

    Args:
        node (xml.dom.minidom.Node):
            The node to split.

        rows (list of str):
            The list of rows to add to.

        list_depth (int, optional):
            How deeply nested lists are at this point.

        quote_depth (int, optional):
            How deeply nested blockquotes are at this point.
    """
    if isinstance(node, Text):
        if node.data.strip():
            rows.append(_wrap_quote(node.toxml(), quote_depth))

        return
    elif not isinstance(node, Element):
        return

    element = node
    tag = element.tagName

    if tag == 'div' and 'codehilite' in element.getAttribute('class'):
        for row in _split_code(element):
            rows.append(_wrap_quote(row, quote_depth))
    elif tag in {'ul', 'ol'}:
        try:
            number = int(element.getAttribute('start') or 1)
        except ValueError:
            number = 1

        for child in element.childNodes:
            if isinstance(child, Element) and child.tagName == 'li':
                _split_list_item(
                    li=child,
                    list_tag=tag,
                    number=number,
                    rows=rows,
                    list_depth=list_depth,
                    quote_depth=quote_depth,
                )
                number += 1
    elif tag == 'table':
        for tr in element.getElementsByTagName('tr'):
            parent = tr.parentNode

            if isinstance(parent, Element) and parent.tagName == 'thead':
                section = 'thead'
            else:
                section = 'tbody'

            cells = ''.join(
                cell.toxml()
                for cell in tr.childNodes
                if isinstance(cell, Element)
            )

            rows.append(_wrap_quote(
                f'<table><{section}><tr>{cells}</tr></{section}></table>',
                quote_depth))
    elif tag == 'blockquote':
        for child in element.childNodes:
            _split_node(child, rows, list_depth, quote_depth + 1)
    elif tag == 'p' and not element.hasChildNodes():
        # Skip empty paragraphs.
        pass
    else:
        rows.append(_wrap_quote(element.toxml(), quote_depth))


def _split_code(
    element: Element,
) -> Sequence[str]:
    """Split a highlighted code block into one row per line.

    Args:
        element (xml.dom.minidom.Element):
            The ``<div class="codehilite">`` element.

    Returns:
        list of str:
        The HTML for each line.
    """
    content = element.getElementsByTagName('pre')[0].toxml()

    # Strip the <pre> and the <code> wrapper. The wrapper spans the whole
    # block, so it can't be split across rows.
    content = re.sub(r'^<pre>(?:<span/>)?(?:<code>)?', '', content)
    content = re.sub(r'(?:</code>)?</pre>$', '', content)
    content = content.removesuffix('\n')

    lines = content.split('\n')
    num_lines = len(lines)
    rows: list[str] = []

    for i, line in enumerate(lines):
        if num_lines == 1:
            css_class = 'codehilite'
        elif i == 0:
            css_class = 'codehilite codehilite-multiline-start'
        elif i == num_lines - 1:
            css_class = 'codehilite codehilite-multiline-end'
        else:
            css_class = 'codehilite codehilite-multiline-middle'

        rows.append(f'<div class="{css_class}"><pre>{line}</pre></div>')

    return rows


def _split_list_item(
    *,
    li: Element,
    list_tag: str,
    number: int,
    rows: list[str],
    list_depth: int,
    quote_depth: int,
) -> None:
    """Split a list item into rows.

    The item's own content is one row. Nested lists become their own rows.

    Args:
        li (xml.dom.minidom.Element):
            The list item.

        list_tag (str):
            The tag of the list, either ``ul`` or ``ol``.

        number (int):
            The item's number in the list.

        rows (list of str):
            The list of rows to add to.

        list_depth (int):
            How deeply nested this item's list is.

        quote_depth (int):
            How deeply nested blockquotes are at this point.
    """
    if list_tag == 'ol':
        start_attr = f' start="{number}"'
    else:
        start_attr = ''

    content: list[str] = []
    is_first_row = True

    # Nested lists split the item into rows, in the order they appear. The
    # None at the end handles any content after the last nested list.
    for child in [*li.childNodes, None]:
        if (child is not None and
            not (isinstance(child, Element) and
                 child.tagName in {'ul', 'ol'})):
            content.append(child.toxml())
            continue

        html = ''.join(content).strip()

        # The first row always shows, so the item keeps its bullet. Later
        # rows continue the item without a bullet.
        if is_first_row or html:
            if is_first_row:
                li_attrs = ''
            else:
                li_attrs = ' class="md-list-continuation"'

            rows.append(_wrap_quote(
                f'<{list_tag}{start_attr}'
                f' style="--md-list-depth: {list_depth}">'
                f'<li{li_attrs}>{html}</li>'
                f'</{list_tag}>',
                quote_depth))

        content = []
        is_first_row = False

        if child is not None:
            _split_node(child, rows, list_depth + 1, quote_depth)


def _wrap_quote(
    row: str,
    quote_depth: int,
) -> str:
    """Wrap a row in blockquotes.

    Args:
        row (str):
            The HTML for the row.

        quote_depth (int):
            The number of blockquotes to wrap the row in.

    Returns:
        str:
        The wrapped row.
    """
    open_quotes = '<blockquote>' * quote_depth
    close_quotes = '</blockquote>' * quote_depth

    return f'{open_quotes}{row}{close_quotes}'


class MarkdownReviewUI(TextBasedReviewUI):
    """A Review UI for Markdown files.

    This renders the markdown to HTML, and allows users to comment on each
    block (heading, paragraph, list item, table row, line of code, etc).
    """

    supported_mimetypes = ['text/markdown', 'text/x-markdown']
    object_key = 'markdown'
    can_render_text = True
    rendered_chunk_generator_cls = MarkdownDiffChunkGenerator

    #: The current version of the line rendering.
    #:
    #: Version Added:
    #:     9.0:
    #:     Created version 2 for new block-level row splitting.
    rendered_lines_version = 2

    extra_css_classes = ['markdown-review-ui']

    js_view_class = 'RB.MarkdownReviewableView'

    #: A cached mapping of legacy row numbers to current row numbers.
    #:
    #: Version Added:
    #:     9.0
    _legacy_row_map: (list[tuple[int, int]] | None) = None

    def generate_render(self) -> Iterator[str]:
        """Generate a render of the text.

        Yields:
            str:
            The rendered lines of content.
        """
        try:
            rows = render_markdown_blocks(self.get_text())
        except Exception as e:
            logger.exception(
                'Failed to parse resulting Markdown XHTML for file attachment '
                '%d: %s',
                self.obj.pk, e)
            rows = [
                _('Error while rendering Markdown content: {error}')
                .format(error=e),
            ]

        yield from rows

    def get_comment_line_range(
        self,
        extra_data: JSONDict,
    ) -> tuple[int, int]:
        """Return the first and last row numbers for a comment.

        Comments on the rendered view made before version 2 are mapped to
        the current rows.

        Version Added:
            9.0

        Args:
            extra_data (dict):
                The comment's extra data.

        Returns:
            tuple:
            A 2-tuple of the first and last row numbers.

        Raises:
            KeyError:
                The extra data is missing the line numbers.

            ValueError:
                A line number is not an integer.
        """
        begin, end = super().get_comment_line_range(extra_data)
        render_version = extra_data.get('renderVersion')

        if not isinstance(render_version, int):
            render_version = 1

        if (extra_data.get('viewMode') == 'rendered' and
            render_version < self.rendered_lines_version):
            row_map = self._get_legacy_row_map()

            if row_map:
                num_rows = len(row_map)
                begin = row_map[min(max(begin, 1), num_rows) - 1][0]
                end = row_map[min(max(end, 1), num_rows) - 1][1]

        return begin, end

    def serialize_comment(
        self,
        comment: FileAttachmentComment,
    ) -> SerializedTextComment:
        """Serialize a comment.

        Version Added:
            9.0

        Args:
            comment (reviewboard.reviews.models.FileAttachmentComment):
                The comment to serialize.

        Returns:
            SerializedTextComment:
            The serialized comment data.
        """
        data = cast('SerializedTextComment',
                    super().serialize_comment(comment))
        extra_data = comment.extra_data

        if extra_data.get('viewMode') == 'rendered':
            try:
                begin, end = self.get_comment_line_range(extra_data)
            except (KeyError, ValueError):
                return data

            data['beginLineNum'] = begin
            data['endLineNum'] = end

            # Saving this comment again from the page will store the new
            # row numbers, so mark them as the current version.
            data['renderVersion'] = self.rendered_lines_version

        return data

    def get_source_lexer(
        self,
        filename: str,
        data: str,
    ) -> Lexer:
        """Return the lexer for the Source tab.

        This shows the source as plain text.

        Version Added:
            9.0

        Args:
            filename (str):
                The filename of the file.

            data (str):
                The contents of the file.

        Returns:
            pygments.lexers.TextLexer:
            The plain-text lexer.
        """
        return TextLexer()

    def _iter_legacy_rendered_lines(self) -> Iterator[str]:
        """Generate the rendered rows in the version 1 layout.

        Version Added:
            9.0

        Yields:
            str:
            Each legacy rendered row.
        """
        assert isinstance(self.obj, FileAttachment)

        with self.obj.file as f:
            f.open()
            rendered = render_markdown(f.read())

        try:
            yield from iter_legacy_markdown_lines(rendered)
        except Exception as e:
            logger.exception(
                'Failed to parse resulting Markdown XHTML for file attachment '
                '%d: %s',
                self.obj.pk, e)

            yield _('Error while rendering Markdown content: %s') % e

    def _get_legacy_rendered_lines(self) -> Sequence[str]:
        """Return the rendered rows in the version 1 layout.

        These are needed to map comments made before version 2.

        Version Added:
            9.0

        Returns:
            list of str:
            The legacy rendered rows.
        """
        # This uses the same cache key that version 1 used.
        return cache_memoize(
            f'text-attachment-{self.obj.pk}-rendered',
            lambda: list(self._iter_legacy_rendered_lines()),
            large_data=True)

    def _get_legacy_row_map(self) -> Sequence[tuple[int, int]]:
        """Return a mapping of legacy row numbers to current row numbers.

        Rows are lined up by the position of their text in the document.
        Without a diff, these are rows of the document. With a diff, these
        are rows of the side-by-side diff, and each side is lined up
        separately.

        Version Added:
            9.0

        Returns:
            list of tuple:
            A ``(first, last)`` tuple of 1-based current row numbers for
            each legacy row.
        """
        if self._legacy_row_map is not None:
            return self._legacy_row_map

        new_legacy_lines = self._get_legacy_rendered_lines()
        new_map = map_text_ranges(
            get_row_text_ranges(new_legacy_lines),
            get_row_text_ranges(self.get_rendered_lines()))
        diff_against_obj = self.diff_against_obj
        row_map: list[tuple[int, int]]

        if diff_against_obj is None:
            row_map = [
                (first + 1, last + 1)
                for first, last in new_map
            ]
        else:
            old_review_ui = diff_against_obj.review_ui
            assert isinstance(old_review_ui, MarkdownReviewUI)

            old_legacy_lines = old_review_ui._get_legacy_rendered_lines()
            old_map = map_text_ranges(
                get_row_text_ranges(old_legacy_lines),
                get_row_text_ranges(old_review_ui.get_rendered_lines()))

            # Find the current diff row for each line on each side.
            chunk_generator = self._get_rendered_diff_chunk_generator()
            old_line_rows: dict[int, int] = {}
            new_line_rows: dict[int, int] = {}

            for chunk in chunk_generator.get_chunks(
                self._make_diff_chunks_cache_key('rendered',
                                                 chunk_generator)):
                for diff_line in chunk['lines']:
                    if diff_line[1]:
                        old_line_rows[diff_line[1]] = diff_line[0]

                    if diff_line[4]:
                        new_line_rows[diff_line[4]] = diff_line[0]

            # Map each legacy diff row through the lines on one side.
            legacy_chunk_generator = self._get_diff_chunk_generator(
                self.rendered_chunk_generator_cls,
                [
                    force_bytes(line)
                    for line in old_legacy_lines
                ],
                [
                    force_bytes(line)
                    for line in new_legacy_lines
                ])
            row_map = []

            for chunk in legacy_chunk_generator.get_chunks():
                for diff_line in chunk['lines']:
                    old_line_num = diff_line[1]
                    new_line_num = diff_line[4]

                    if new_line_num:
                        first, last = new_map[new_line_num - 1]
                        line_rows = new_line_rows
                    elif old_line_num:
                        first, last = old_map[old_line_num - 1]
                        line_rows = old_line_rows
                    else:
                        row_map.append((1, 1))
                        continue

                    row_map.append((line_rows.get(first + 1, 1),
                                    line_rows.get(last + 1, 1)))

        self._legacy_row_map = row_map

        return row_map
