"""The original rendering for Markdown file attachments.

This is a copy of the row splitter implementation that was used for comments
that were created on markdown files with render version 1 (see
:py:attr:`~reviewboard.reviews.ui.text.TextBasedReviewUI.
rendered_lines_version`).

Version Added:
    9.0
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pymdownx.emoji
from django.utils.encoding import force_str
from djblets.markdown import get_markdown_element_tree
from markdown import markdown

from reviewboard.reviews.markdown_utils import clean_markdown_html

if TYPE_CHECKING:
    from collections.abc import Iterator


#: The Markdown options used to render rows before render version 2.
#:
#: This is a frozen copy of ``MARKDOWN_KWARGS`` from Review Board 8.
#: Comments made before render version 2 store row numbers from this
#: rendering, so it must not change.
#:
#: Version Added:
#:     9.0
_LEGACY_MARKDOWN_KWARGS = {
    'enable_attributes': False,
    'output_format': 'xhtml',
    'lazy_ol': False,
    'extensions': [
        'markdown.extensions.fenced_code',
        'markdown.extensions.codehilite',
        'markdown.extensions.sane_lists',
        'markdown.extensions.tables',
        'markdown.extensions.nl2br',
        'pymdownx.tilde',
        'pymdownx.emoji',
        'djblets.markdown.extensions.escape_html',
        'djblets.markdown.extensions.wysiwyg',
    ],
    'extension_configs': {
        'markdown.extensions.codehilite': {
            'guess_lang': False,
            'linenums': False,
        },
        'pymdownx.emoji': {
            'emoji_index': pymdownx.emoji.gemoji,
            'options': {
                'classes': 'emoji',
                'image_path': ('https://github.githubassets.com/images/icons/'
                               'emoji/unicode/'),
                'non_standard_image_path': ('https://github.githubassets.com/'
                                            'images/icons/emoji/'),
            },
        },
    },
}


def render_legacy_markdown(
    text: str | bytes,
) -> str:
    """Render Markdown the way rows were rendered before version 2.

    Version Added:
        9.0

    Args:
        text (str or bytes):
            The Markdown text.

            If this is bytes, it must be UTF-8.

    Returns:
        str:
        The sanitized XHTML.
    """
    return clean_markdown_html(markdown(force_str(text),
                                        **_LEGACY_MARKDOWN_KWARGS))


def iter_legacy_markdown_lines(
    markdown_html: str,
) -> Iterator[str]:
    """Split rendered Markdown into rows using the original layout.

    This is a frozen copy of :py:func:`djblets.markdown.iter_markdown_lines`
    from Djblets 7.0. Comments made on the rendered view of Markdown file
    attachments before render version 2 store row numbers from this layout,
    so it must not change, even if Djblets changes.

    Version Added:
        9.0

    Args:
        markdown_html (str):
            The rendered Markdown HTML.

    Yields:
        str:
        Each row of HTML.
    """
    nodes = get_markdown_element_tree(markdown_html)

    for node in nodes:
        if node.nodeType == node.ELEMENT_NODE:
            if (node.tagName == 'div' and
                node.attributes.get('class', 'codehilite')):
                # This is a code block, which will consist of a bunch of lines
                # for the source code. It contains a single <pre> element
                # within it that contains the full code block. We want to split
                # that up into individual lines which are each wrapped in their
                # own <div class="codehilite"><pre> elements.
                child_lines = node.firstChild.toxml().splitlines()

                # The first and last lines in child_lines begin and end with
                # <pre> and </pre>, respectively. Clear that out.
                assert child_lines[0].startswith('<pre>')
                assert child_lines[-1].endswith('</pre>')
                child_lines[0] = child_lines[0][len('<pre>'):]
                child_lines[-1] = child_lines[-1][:-len('</pre>')]

                if not child_lines[-1]:
                    child_lines = child_lines[:-1]

                fmt = '<div class="codehilite%s"><pre>%s</pre></div>'

                # If there's just a single line, output that directly
                if len(child_lines) == 1:
                    yield fmt % ('', child_lines[0])
                elif len(child_lines) > 1:
                    yield fmt % (' codehilite-multiline-start',
                                 child_lines[0])

                    for line in child_lines[1:-1]:
                        yield fmt % (' codehilite-multiline-middle', line)

                    yield fmt % (' codehilite-multiline-end', child_lines[-1])
            elif node.tagName in {'ul', 'ol'}:
                # This is a list. We'll need to split all of its items
                # into individual lists, in order to retain bullet points
                # or the numbers.
                #
                # For the case of numbers, we can set each list to start
                # at the appropriate number so that they don't all say "1."
                start = node.attributes.get('start')

                if start is not None:
                    try:
                        i = int(start.value)
                    except ValueError:
                        i = 1
                else:
                    i = 1

                for child_node in node.childNodes:
                    if (child_node.nodeType == child_node.ELEMENT_NODE and
                        child_node.tagName == 'li'):
                        # This is a list item element. It may be multiple
                        # lines, but we'll have to treat it as one line.
                        yield (
                            f'<{node.tagName} start="{i}">{child_node.toxml()}'
                            f'</{node.tagName}>'
                        )

                        i += 1
            elif node.tagName == 'p':
                # This is a paragraph, possibly containing multiple lines.
                for line in node.toxml().splitlines():
                    yield line
            else:
                # Whatever this is, treat it as one block.
                yield node.toxml()
        elif node.nodeType == node.TEXT_NODE:
            # This may be several blank extraneous blank lines, due to
            # Markdown's generation from invisible markup like fences.
            # We want to condense this down to one blank line.
            yield '\n'
