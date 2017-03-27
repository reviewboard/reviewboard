from __future__ import unicode_literals

from djblets.siteconfig.models import SiteConfiguration

from reviewboard.diffviewer.templatetags.difftags import highlightregion
from reviewboard.testing import TestCase


class HighlightRegionTest(TestCase):
    def setUp(self):
        super(HighlightRegionTest, self).setUp()

        siteconfig = SiteConfiguration.objects.get_current()
        siteconfig.set('diffviewer_syntax_highlighting', True)

    def test_highlight_region(self):
        """Testing highlightregion"""
        self.assertEqual(highlightregion("", None), "")

        self.assertEqual(highlightregion("abc", None), "abc")

        self.assertEqual(highlightregion("abc", [(0, 3)]),
                          '<span class="hl">abc</span>')

        self.assertEqual(highlightregion("abc", [(0, 1)]),
                          '<span class="hl">a</span>bc')

        self.assertEqual(highlightregion(
            '<span class="xy">a</span>bc',
            [(0, 1)]),
            '<span class="xy"><span class="hl">a</span></span>bc')

        self.assertEqual(highlightregion(
            '<span class="xy">abc</span>123',
            [(1, 4)]),
            '<span class="xy">a<span class="hl">bc</span></span>' +
            '<span class="hl">1</span>23')

        self.assertEqual(highlightregion(
            '<span class="xy">abc</span><span class="z">12</span>3',
            [(1, 4)]),
            '<span class="xy">a<span class="hl">bc</span></span>' +
            '<span class="z"><span class="hl">1</span>2</span>3')

        self.assertEqual(highlightregion(
            'foo<span class="xy">abc</span><span class="z">12</span>3',
            [(0, 6), (7, 9)]),
            '<span class="hl">foo</span><span class="xy">' +
            '<span class="hl">abc</span></span><span class="z">1' +
            '<span class="hl">2</span></span><span class="hl">3</span>')

        self.assertEqual(highlightregion(
            'foo&quot;bar',
            [(0, 7)]),
            '<span class="hl">foo&quot;bar</span>')

        self.assertEqual(highlightregion(
            '&quot;foo&quot;',
            [(0, 1)]),
            '<span class="hl">&quot;</span>foo&quot;')

        self.assertEqual(highlightregion(
            '&quot;foo&quot;',
            [(2, 5)]),
            '&quot;f<span class="hl">oo&quot;</span>')

        self.assertEqual(highlightregion(
            'foo=<span class="ab">&quot;foo&quot;</span>)',
            [(4, 9)]),
            'foo=<span class="ab"><span class="hl">&quot;foo&quot;' +
            '</span></span>)')
