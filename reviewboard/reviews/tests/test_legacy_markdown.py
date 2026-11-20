"""Unit tests for reviewboard.reviews.ui.legacy_markdown.

Version Added:
    9.0
"""

from __future__ import annotations

from reviewboard.reviews.ui.legacy_markdown import (
    iter_legacy_markdown_lines,
    render_legacy_markdown,
)
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
            '<ol start="3">\n'
            '<li>three</li>\n'
            '</ol>\n'
            '<ul>\n'
            '<li>one</li>\n'
            '<li>two</li>\n'
            '</ul>\n'
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
                '<ol start="3"><li>three</li></ol>',
                '\n',
                '<ul start="1"><li>one</li></ul>',
                '<ul start="2"><li>two</li></ul>',
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

    def test_ordered_list_after_unordered_list(self) -> None:
        """Testing iter_legacy_markdown_lines with an ordered list after an
        unordered list keeps the same rows as when they were joined
        """
        joined_html = (
            '<ul>\n'
            '<li>a</li>\n'
            '<li>\n'
            '<p>b</p>\n'
            '</li>\n'
            '<li>\n'
            '<p>c</p>\n'
            '</li>\n'
            '</ul>\n'
            '<p>after</p>'
        )
        split_html = (
            '<ul>\n'
            '<li>a</li>\n'
            '<li>b</li>\n'
            '</ul>\n'
            '<ol>\n'
            '<li>c</li>\n'
            '</ol>\n'
            '<p>after</p>'
        )

        self.assertEqual(
            list(iter_legacy_markdown_lines(joined_html)),
            [
                '<ul start="1"><li>a</li></ul>',
                '<ul start="2"><li>\n<p>b</p>\n</li></ul>',
                '<ul start="3"><li>\n<p>c</p>\n</li></ul>',
                '\n',
                '<p>after</p>',
            ])
        self.assertEqual(
            list(iter_legacy_markdown_lines(split_html)),
            [
                '<ul start="1"><li>a</li></ul>',
                '<ul start="2"><li>b</li></ul>',
                '<ol start="1"><li>c</li></ol>',
                '\n',
                '<p>after</p>',
            ])

    def test_ordered_list_after_paragraph(self) -> None:
        """Testing iter_legacy_markdown_lines keeps the blank row between
        an unordered list and other blocks
        """
        self.assertEqual(
            list(iter_legacy_markdown_lines(
                '<ul>\n'
                '<li>a</li>\n'
                '</ul>\n'
                '<p></p>\n'
                '<ol>\n'
                '<li>b</li>\n'
                '</ol>'
            )),
            [
                '<ul start="1"><li>a</li></ul>',
                '\n',
                '<p/>',
                '\n',
                '<ol start="1"><li>b</li></ol>',
            ])


class RenderLegacyMarkdownTests(TestCase):
    """Unit tests for render_legacy_markdown.

    Version Added:
        9.0
    """

    def test_render(self) -> None:
        """Testing render_legacy_markdown keeps the original rendering"""
        self.assertEqual(
            render_legacy_markdown(
                'One\n'
                'two\n'
                '\n'
                '```python\n'
                'x = 1\n'
                '```\n'
                '\n'
                '- a\n'
                '  - b\n'
            ),
            '<p>One<br />\ntwo</p>\n'
            '<p></p>\n'
            '<div class="codehilite"><pre><span></span><code>'
            '<span class="n">x</span> <span class="o">=</span> '
            '<span class="mi">1</span>\n'
            '</code></pre></div>\n'
            '<p></p>\n'
            '<ul>\n'
            '<li>a</li>\n'
            '<li>b</li>\n'
            '</ul>')
