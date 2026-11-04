"""Unit tests for reviewboard.reviews.ui.legacy_markdown.

Version Added:
    9.0
"""

from __future__ import annotations

from reviewboard.reviews.ui.legacy_markdown import iter_legacy_markdown_lines
from reviewboard.testing import TestCase


class IterLegacyMarkdownLinesTests(TestCase):
    """Unit tests for iter_legacy_markdown_lines.

    Version Added:
        9.0
    """

    def test_layout(self) -> None:
        """Testing iter_legacy_markdown_lines keeps the original layout"""
        html = (
            '<h1>Title</h1>\n'
            '<p></p>\n'
            '<p>Some <em>text</em><br />\n'
            'wrapped.</p>\n'
            '<ul>\n'
            '<li>one</li>\n'
            '<li>two</li>\n'
            '</ul>\n'
            '<ol start="3">\n'
            '<li>three</li>\n'
            '</ol>\n'
            '<div class="codehilite"><pre><span></span><code>a\n'
            '\n'
            'b\n'
            '</code></pre></div>\n'
            '<blockquote>\n'
            '<p>Quote</p>\n'
            '</blockquote>'
        )

        self.assertEqual(
            list(iter_legacy_markdown_lines(html)),
            [
                '<h1>Title</h1>',
                '\n',
                '<p/>',
                '\n',
                '<p>Some <em>text</em><br/>',
                'wrapped.</p>',
                '\n',
                '<ul start="1"><li>one</li></ul>',
                '<ul start="2"><li>two</li></ul>',
                '\n',
                '<ol start="3"><li>three</li></ol>',
                '\n',
                '<div class="codehilite codehilite-multiline-start">'
                '<pre><span/><code>a</pre></div>',
                '<div class="codehilite codehilite-multiline-middle">'
                '<pre></pre></div>',
                '<div class="codehilite codehilite-multiline-middle">'
                '<pre>b</pre></div>',
                '<div class="codehilite codehilite-multiline-end">'
                '<pre></code></pre></div>',
                '\n',
                '<blockquote>\n<p>Quote</p>\n</blockquote>',
            ])
