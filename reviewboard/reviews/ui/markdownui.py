"""A Review UI for Markdown files."""

from __future__ import annotations

import logging
import re
from bisect import bisect_right
from html import unescape
from typing import Literal, TYPE_CHECKING, cast
from xml.dom.minidom import Element, Node, Text

from django.utils.encoding import force_bytes, force_str
from django.utils.html import escape, strip_tags
from django.utils.translation import gettext as _
from djblets.cache.backend import cache_memoize
from djblets.markdown import get_markdown_element_tree
from markdown import markdown
from markdown.extensions.codehilite import CodeHilite
from pygments import highlight
from pygments.lexers import TextLexer, get_lexer_by_name
from pygments.util import ClassNotFound

from reviewboard.attachments.models import FileAttachment
from reviewboard.diffviewer.chunk_generator import NoWrapperHtmlFormatter
from reviewboard.reviews.chunk_generators import MarkdownDiffChunkGenerator
from reviewboard.reviews.markdown_utils import (
    MARKDOWN_KWARGS,
    clean_markdown_html,
    render_markdown,
)
from reviewboard.reviews.ui.legacy_markdown import iter_legacy_markdown_lines
from reviewboard.reviews.ui.text import TextBasedReviewUI
from reviewboard.treesitter.core import get_parser
from reviewboard.treesitter.highlight import highlight as ts_highlight
from reviewboard.treesitter.language import get_language_name_for_info_string

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator, Sequence
    from typing import TypeAlias

    from pygments.lexers import Lexer
    from typelets.json import JSONDict

    from reviewboard.reviews.models import FileAttachmentComment
    from reviewboard.reviews.ui.text import SerializedTextComment


logger = logging.getLogger(__name__)


#: Options for rendering Markdown file attachments.
#:
#: This drops the following extensions:
#:
#: ``nl2br`` and ``wysiwig``
#:     These extensions keep the render lined up with the source text, and we
#:     use them in comments and review request fields. For reviewing the actual
#:     content of markdown files, we want to render as blocks instead of making
#:     it look like the source.
#:
#: ``codehilite``
#:     Code blocks are highlighted via treesitter while splitting rows.
#:
#: ``fenced_code``
#:     We replace this with ``pymdownx.superfences``, which also handles fenced
#:     code blocks inside lists and blockquotes.
#:
#: Version Added:
#:     9.0
_MARKDOWN_KWARGS = {
    **MARKDOWN_KWARGS,
    'extensions': [
        *(
            extension
            for extension in cast(list[str], MARKDOWN_KWARGS['extensions'])
            if extension not in {
                'djblets.markdown.extensions.wysiwyg',
                'markdown.extensions.codehilite',
                'markdown.extensions.fenced_code',
                'markdown.extensions.nl2br',
            }
        ),
        'pymdownx.highlight',
        'pymdownx.magiclink',
        'pymdownx.quotes',
        'pymdownx.superfences',
        'pymdownx.tasklist',
    ],
    'extension_configs': {
        **MARKDOWN_KWARGS['extension_configs'],
        'pymdownx.highlight': {
            'use_pygments': False,
        },
        'pymdownx.quotes': {
            'callouts': True,
        },
    },
}


#: Regex for a row with a code block.
#:
#: Version Added:
#:     9.0
_CODE_ROW_RE = re.compile(
    r'^<div class="codehilite[^"]*"[^>]*><pre>(?P<content>.*)</pre></div>$',
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

#: Regex to find tasklist checkboxes.
#:
#: Version Added:
#:     9.0
_TASK_CHECKBOX_RE = re.compile(
    r'<input type="checkbox" disabled(?P<checked> checked)?/>')

#: The smallest width of a table column, in characters.
#:
#: Version Added:
#:     9.0
_MIN_COLUMN_WIDTH = 3

#: The largest width of a table column, in characters.
#:
#: Any columns longer than this will wrap.
#:
#: Version Added:
#:     9.0
_MAX_COLUMN_WIDTH = 40

#: Extra width for each table column's padding, in characters.
#:
#: Version Added:
#:     9.0
_COLUMN_PADDING = 2

#: Type for where a gap goes before a row.
#:
#: This is a 2-tuple of:
#:
#: Tuple:
#:     0 (str):
#:         The kind of gap. This will be "block" for a block after another
#:         block in the same container, or "item" for a list item after
#:         another list item.
#:
#:     1 (int):
#:         The blockquote depth of the container that the gap is in.
#:
#: Version Added:
#:     9.0
_Gap: TypeAlias = tuple[Literal['block', 'item'], int]

#: A character that stands in for content without text.
_PLACEHOLDER = '￼'


def render_markdown_blocks(
    text: str | bytes,
) -> Sequence[str]:
    """Render Markdown and split it into reviewable rows.

    Each heading, paragraph, list item, table row, and line of code becomes a
    row. Blocks inside a blockquote or alert become their own rows, each
    wrapped in a blockquote. Alerts will keep their classes.

    A row that starts a block after another block in the same container gets a
    ``data-md-gap`` attribute, so CSS can space blocks apart. This works like
    a ``* + *`` rule in normal HTML, which can't be used here since each row
    is in its own table cell. The attribute goes on the element for the block
    at that container's level, which is the blockquote for a quote, and is
    ``"item"`` between list items or ``"block"`` otherwise.

    Version Added:
        9.0

    Args:
        text (str or bytes):
            The Markdown text.

    Returns:
        list of str:
        The HTML for each row.
    """
    html = markdown(force_str(text), **_MARKDOWN_KWARGS)

    # Task checkboxes aren't allowed through the sanitizer, so they're shown as
    # characters instead. HTML typed in the text is escaped by now, so only
    # checkboxes from task lists match.
    html = _TASK_CHECKBOX_RE.sub(_replace_task_checkbox, html)

    html = clean_markdown_html(html)
    rows: list[str] = []

    for i, node in enumerate(
        _get_block_nodes(get_markdown_element_tree(html))
    ):
        if i == 0:
            gap = None
        else:
            gap = ('block', 0)

        _split_node(node, rows, gap=gap)

    # Rows are shown inside <pre> in diffs, so line breaks from the source
    # would show there. In HTML, they're only spaces.
    #
    # Rows containing a <pre> (such as list items holding a code block) are
    # left alone. Handle those if they show line breaks.
    for i, row in enumerate(rows):
        if '<pre' not in row:
            rows[i] = _NEWLINE_RE.sub(' ', row)

    return rows


def _replace_task_checkbox(
    m: re.Match[str],
) -> str:
    """Return a character to show in place of a task's checkbox.

    Version Added:
        9.0

    Args:
        m (re.Match):
            The match for the checkbox.

    Returns:
        str:
        The HTML for the checkbox.
    """
    if m.group('checked'):
        return '<span class="task-list-checkbox -is-checked">\u2611</span>'
    else:
        return '<span class="task-list-checkbox">\u2610</span>'


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


def _get_block_nodes(
    nodes: Iterable[Node],
) -> list[Node]:
    """Return the nodes that are blocks.

    This skips whitespace between blocks, and empty paragraphs.

    Version Added:
        9.0

    Args:
        nodes (list of xml.dom.minidom.Node):
            The nodes to filter.

    Returns:
        list of xml.dom.minidom.Node:
        The nodes that are blocks.
    """
    result: list[Node] = []

    for node in nodes:
        if isinstance(node, Text):
            if node.data.strip():
                result.append(node)
        elif isinstance(node, Element):
            if node.tagName != 'p' or node.hasChildNodes():
                result.append(node)

    return result


def _split_node(
    node: Node,
    rows: list[str],
    list_depth: int = 0,
    quotes: tuple[str, ...] = (),
    gap: (_Gap | None) = None,
) -> None:
    """Split a node of rendered Markdown into rows.

    Version Changed:
        9.0:
        - Added the ``gap`` argument.
        - Changed the ``quote_depth`` argument to ``quotes``.

    Args:
        node (xml.dom.minidom.Node):
            The node to split.

        rows (list of str):
            The list of rows to add to.

        list_depth (int, optional):
            How deeply nested lists are at this point.

        quotes (tuple of str, optional):
            The class of each blockquote this is in, from the outside in.
            Normal blockquotes have an empty class.

        gap (tuple, optional):
            The gap to put before the node's first row, if any.

            Version Added:
                9.0
    """
    if isinstance(node, Text):
        rows.append(_wrap_quote(node.toxml(), quotes, gap))
        return
    elif not isinstance(node, Element):
        return

    element = node
    tag = element.tagName

    if tag == 'pre':
        for i, row in enumerate(_split_code(element)):
            if i > 0:
                gap = None

            rows.append(_wrap_quote(row, quotes, gap))
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
                    quotes=quotes,
                    gap=gap,
                )
                number += 1
                gap = ('item', len(quotes))
    elif tag == 'table':
        for i, row in enumerate(_split_table(element)):
            if i > 0:
                gap = None

            rows.append(_wrap_quote(row, quotes, gap))
    elif tag == 'blockquote' or _is_alert(element):
        if tag == 'blockquote':
            inner_quotes = (*quotes, '')
        else:
            inner_quotes = (*quotes, element.getAttribute('class'))

        # The first block in the quote takes the quote's own gap, which
        # goes on the quote's blockquote wrapper.
        for child in _get_block_nodes(element.childNodes):
            _split_node(child, rows, list_depth, inner_quotes, gap)
            gap = ('block', len(inner_quotes))
    else:
        rows.append(_wrap_quote(element.toxml(), quotes, gap))


def _is_alert(
    element: Element,
) -> bool:
    """Return whether an element is an alert.

    Alerts are blockquotes starting with "[!NOTE]" or another type. They're
    rendered as ``<div class="admonition note">``.

    Version Added:
        9.0

    Args:
        element (xml.dom.minidom.Element):
            The element.

    Returns:
        bool:
        Whether the element is an alert.
    """
    return (element.tagName == 'div' and
            'admonition' in element.getAttribute('class').split())


def _split_code(
    element: Element,
) -> Sequence[str]:
    """Split a code block into one highlighted row per line.

    Args:
        element (xml.dom.minidom.Element):
            The ``<pre>`` element.

    Returns:
        list of str:
        The HTML for each line.
    """
    code_elements = element.getElementsByTagName('code')

    if code_elements:
        code_element = code_elements[0]
    else:
        code_element = element

    # Fenced code blocks name their language as "language-<name>".
    info_string = ''

    for css_class in code_element.getAttribute('class').split():
        if css_class.startswith('language-'):
            info_string = css_class[len('language-'):]
            break

    # Trim the code the same way codehilite did for the original rows, so
    # comments on those rows still line up. It strips blank lines around the
    # code. For code without a language, it also reads the language from a
    # first line like ":::python" or "#!python" and removes it.
    hiliter = CodeHilite(_get_element_text(code_element).strip('\n'))

    if not info_string:
        # This is private, but it's the same code that made the original rows,
        # so the two always agree.
        hiliter._parseHeader()  # type: ignore
        info_string = hiliter.lang or ''

    code = hiliter.src

    code_lines = code.split('\n')
    lines = _highlight_code(code, code_lines, info_string)

    if lines is None:
        lines = [
            escape(line)
            for line in code_lines
        ]

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


def _split_table(
    element: Element,
) -> list[str]:
    """Split a table into one row per table row.

    Each row is its own table. They all get the same column widths, based
    on the longest text in each column, so the columns line up.

    Args:
        element (xml.dom.minidom.Element):
            The ``<table>`` element.

    Returns:
        list of str:
        The HTML for each row.
    """
    table_rows: list[tuple[str, list[Element]]] = []
    col_widths: list[int] = []

    for tr in element.getElementsByTagName('tr'):
        parent = tr.parentNode

        if isinstance(parent, Element) and parent.tagName == 'thead':
            section = 'thead'
        else:
            section = 'tbody'

        cells = [
            cell
            for cell in tr.childNodes
            if isinstance(cell, Element)
        ]
        table_rows.append((section, cells))

        for i, cell in enumerate(cells):
            text_len = len(unescape(strip_tags(cell.toxml())).strip())
            width = min(max(text_len, _MIN_COLUMN_WIDTH), _MAX_COLUMN_WIDTH)

            if i < len(col_widths):
                col_widths[i] = max(col_widths[i], width)
            else:
                col_widths.append(width)

    # Widths are in "ch" units, with room for cell padding.
    widths = [
        width + _COLUMN_PADDING
        for width in col_widths
    ]
    cols = ''.join(
        f'<col style="width: {width}ch"/>'
        for width in widths
    )
    table_start = (
        f'<table style="table-layout: fixed; width: {sum(widths)}ch">'
        f'<colgroup>{cols}</colgroup>'
    )

    return [
        '%s<%s><tr>%s</tr></%s></table>' % (
            table_start,
            section,
            ''.join(
                cell.toxml()
                for cell in cells
            ),
            section,
        )
        for section, cells in table_rows
    ]


def _highlight_code(
    code: str,
    code_lines: Sequence[str],
    info_string: str,
) -> Sequence[str] | None:
    """Return syntax-highlighted lines for a code block.

    This uses tree-sitter when it supports the language, and Pygments
    otherwise.

    Args:
        code (str):
            The code to highlight.

        code_lines (list of str):
            The code, split into lines.

        info_string (str):
            The language named on the code fence. This may be empty.

    Returns:
        list of str:
        The highlighted lines, or ``None`` if the code can't be highlighted.
    """
    if not info_string:
        return None

    language_name = get_language_name_for_info_string(info_string)

    if language_name:
        content = code.encode()

        try:
            tree = get_parser(language_name).parse(content)
            lines = ts_highlight(content, code_lines, tree, language_name)

            if lines:
                return lines
        except Exception as e:
            logger.exception('Tree-sitter highlighting failed for a %s code '
                             'block in Markdown: %s',
                             language_name, e)

    try:
        lexer = get_lexer_by_name(info_string)
    except ClassNotFound:
        return None

    lines = highlight(code, lexer, NoWrapperHtmlFormatter()).splitlines()

    if len(lines) != len(code_lines):
        # Line counts must match, or rows would be lost.
        return None

    return lines


def _get_element_text(
    element: Element,
) -> str:
    """Return all text inside an element.

    Args:
        element (xml.dom.minidom.Element):
            The element.

    Returns:
        str:
        The text.
    """
    parts: list[str] = []

    for child in element.childNodes:
        if isinstance(child, Text):
            parts.append(child.data)
        elif isinstance(child, Element):
            parts.append(_get_element_text(child))

    return ''.join(parts)


def _split_list_item(
    *,
    li: Element,
    list_tag: str,
    number: int,
    rows: list[str],
    list_depth: int,
    quotes: tuple[str, ...],
    gap: _Gap | None,
) -> None:
    """Split a list item into rows.

    The item's own content is one row. Nested lists become their own rows.

    Version Changed:
        9.0:
        - Added the ``gap`` argument.
        - Changed the ``quote_depth`` argument to ``quotes``.

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

        quotes (tuple of str):
            The class of each blockquote this is in, from the outside in.

        gap (tuple):
            The gap to put before the item, if any.

            Version Added:
                9.0
    """
    if list_tag == 'ol':
        start_attr = f' start="{number}"'
    else:
        start_attr = ''

    # Task list items have a class, so they can be shown without bullets.
    li_class = li.getAttribute('class')
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
            if not is_first_row:
                li_attrs = ' class="md-list-continuation"'
                row_gap = ('block', len(quotes))
            elif li_class:
                li_attrs = f' class="{escape(li_class)}"'
                row_gap = gap
            else:
                li_attrs = ''
                row_gap = gap

            rows.append(_wrap_quote(
                f'<{list_tag}{start_attr}'
                f' style="--md-list-depth: {list_depth}">'
                f'<li{li_attrs}>{html}</li>'
                f'</{list_tag}>',
                quotes,
                row_gap))

        content = []
        is_first_row = False

        if child is not None:
            _split_node(child, rows, list_depth + 1, quotes,
                        ('item', len(quotes)))


def _wrap_quote(
    row: str,
    quotes: tuple[str, ...],
    gap: (_Gap | None) = None,
) -> str:
    """Wrap a row in blockquotes, and mark its gap.

    Version Changed:
        9.0:
        - Added the ``gap`` argument.
        - Changed the ``quote_depth`` argument to ``quotes``.

    Args:
        row (str):
            The HTML for the row.

        quotes (tuple of str):
            The class of each blockquote to wrap the row in, from the
            outside in.

        gap (tuple, optional):
            The gap to put before the row, if any.

            Version Added:
                9.0

    Returns:
        str:
        The wrapped row.
    """
    gap_kind = ''
    gap_depth = -1

    if gap is not None:
        gap_kind, gap_depth = gap

    if gap_depth == len(quotes):
        row = _add_gap(row, gap_kind)

    # The blockquote at each level is a block in the container one level
    # up, so it holds the gap for that container.
    for level in range(len(quotes), 0, -1):
        attrs = ''
        quote_class = quotes[level - 1]

        if quote_class:
            attrs += f' class="{escape(quote_class)}"'

        if gap_depth == level - 1:
            attrs += f' data-md-gap="{gap_kind}"'

        row = f'<blockquote{attrs}>{row}</blockquote>'

    return row


def _add_gap(
    row: str,
    gap_kind: str,
) -> str:
    """Add a gap attribute to the first element in a row.

    Version Added:
        9.0

    Args:
        row (str):
            The HTML for the row.

        gap_kind (str):
            The kind of gap.

    Returns:
        str:
        The row with the attribute added.
    """
    attr = f' data-md-gap="{gap_kind}"'

    if not row.startswith('<'):
        # Bare text needs a block to hold the gap.
        return f'<div{attr}>{row}</div>'

    tag_end = row.index('>')

    if row[tag_end - 1] == '/':
        tag_end -= 1

    return row[:tag_end] + attr + row[tag_end:]


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

    def generate_highlighted_text(self) -> Sequence[str]:
        """Generate syntax-highlighted text for the file.

        This highlights the Markdown with tree-sitter, including code in fenced
        code blocks. If that fails, we'll fall back to the Pygments
        implementation in the parent class.

        Version Added:
            9.0

        Returns:
            list of str:
            The syntax-highlighted text, split into lines.
        """
        try:
            text = force_str(self.get_text())
        except UnicodeDecodeError:
            return super().generate_highlighted_text()

        # Split lines the way Pygments did before, so comments on the source
        # view stay on the same lines.
        text = text.replace('\r\n', '\n').replace('\r', '\n').strip('\n')
        lines = text.split('\n')
        content = text.encode()

        try:
            tree = get_parser('markdown').parse(content)
            highlighted = ts_highlight(content, lines, tree, 'markdown')
        except Exception as e:
            logger.exception('Tree-sitter highlighting failed for file '
                             'attachment %d: %s',
                             self.obj.pk, e)
            highlighted = None

        if not highlighted or len(highlighted) != len(lines):
            return super().generate_highlighted_text()

        return [
            f'<pre>{line}</pre>'
            for line in highlighted
        ]

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
