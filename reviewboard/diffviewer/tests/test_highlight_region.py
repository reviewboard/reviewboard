from __future__ import unicode_literals

from djblets.siteconfig.models import SiteConfiguration

from reviewboard.diffviewer.templatetags.difftags import highlightregion
from reviewboard.testing import TestCase


class HighlightRegionTest(TestCase):
    """Unit tests for highlightregion template tag."""

    def setUp(self):
        super(HighlightRegionTest, self).setUp()

        siteconfig = SiteConfiguration.objects.get_current()
        siteconfig.set('diffviewer_syntax_highlighting', True)

    def test_empty_string(self):
        """Testing highlightregion with empty string and no range"""
        self.assertEqual(highlightregion('', None), '')

    def test_plain_text(self):
        """Testing highlightregion with plain text string and no range"""
        self.assertEqual(highlightregion('abc', None), 'abc')

    def test_plain_text_and_full_range(self):
        """Testing highlightregion with plain text string and full text range
        """
        self.assertEqual(highlightregion('abc', [(0, 3)]),
                         '<span class="hl">abc</span>')

    def test_plain_text_and_range(self):
        """Testing highlightregion with plain text string and range"""
        self.assertEqual(highlightregion('abc', [(0, 1)]),
                         '<span class="hl">a</span>bc')

    def test_html_and_range(self):
        """Testing highlightregion with HTML string and range"""
        self.assertEqual(
            highlightregion('<span class="xy">a</span>bc', [(0, 1)]),
            '<span class="xy"><span class="hl">a</span></span>bc')

    def test_html_and_range_spanning_tags(self):
        """Testing highlightregion with HTML string and range spanning tags"""
        self.assertEqual(
            highlightregion('<span class="xy">abc</span>123', [(1, 4)]),
            '<span class="xy">a<span class="hl">bc</span></span>'
            '<span class="hl">1</span>23')

        self.assertEqual(
            highlightregion('<span class="xy">abc</span>'
                            '<span class="z">12</span>3',
                            [(1, 4)]),
            '<span class="xy">a<span class="hl">bc</span></span>'
            '<span class="z"><span class="hl">1</span>2</span>3')

    def test_html_and_multiple_ranges_spanning_tags(self):
        """Testing highlightregion with HTML string and multiple ranges
        spanning tags
        """
        self.assertEqual(
            highlightregion('foo<span class="xy">abc</span>'
                            '<span class="z">12</span>3',
                            [(0, 6), (7, 9)]),
            '<span class="hl">foo</span><span class="xy">'
            '<span class="hl">abc</span></span><span class="z">1'
            '<span class="hl">2</span></span><span class="hl">3</span>')

    def test_html_and_full_range_spanning_entities(self):
        """Testing highlightregion with HTML string and full text range
        spanning entities
        """
        self.assertEqual(
            highlightregion('foo&quot;bar', [(0, 7)]),
            '<span class="hl">foo&quot;bar</span>')

    def test_html_and_range_spanning_entities(self):
        """Testing highlightregion with HTML string and range spanning
        entities
        """
        self.assertEqual(
            highlightregion('&quot;foo&quot;', [(0, 1)]),
            '<span class="hl">&quot;</span>foo&quot;')

        self.assertEqual(
            highlightregion('&quot;foo&quot;', [(2, 5)]),
            '&quot;f<span class="hl">oo&quot;</span>')

    def test_html_and_range_spanning_entities_inside_tag(self):
        """Testing highlightregion with HTML string and range spanning
        entities inside tag
        """
        self.assertEqual(
            highlightregion('foo=<span class="ab">&quot;foo&quot;</span>)',
                            [(4, 9)]),
            'foo=<span class="ab"><span class="hl">&quot;foo&quot;'
            '</span></span>)')
