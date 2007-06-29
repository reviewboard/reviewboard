import os
import unittest

from django.conf import settings
from django.test import TestCase

from reviewboard.diffviewer.templatetags.difftags import highlightregion
import reviewboard.diffviewer.diffutils as diffutils
import reviewboard.diffviewer.parser as diffparser


class MyersDifferTest(TestCase):
    def testDiff(self):
        """Testing myers differ"""
        self.__test_diff(["1", "2", "3"],
                         ["1", "2", "3"],
                         [("equal", 0, 3, 0, 3),])

        self.__test_diff(["1", "2", "3"],
                         [],
                         [("delete", 0, 3, 0, 0),])

        self.__test_diff("1\n2\n3\n",
                         "0\n1\n2\n3\n",
                         [("insert", 0, 0, 0, 2),
                          ("equal",  0, 6, 2, 8)])

        self.__test_diff("1\n2\n3\n7\n",
                         "1\n2\n4\n5\n6\n7\n",
                         [("equal",   0, 4, 0, 4),
                          ("replace", 4, 5, 4, 5),
                          ("insert",  5, 5, 5, 9),
                          ("equal",   5, 8, 9, 12)])

        self.__test_diff([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15,
                          16, 15, 17, 13, 17],
                         [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 18, 19, 20, 21,
                          22, 13, 14, 15, 16, 15, 23, 13, 24, 25, 26, 27, 13,
                          28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40,
                          41, 42, 43, 44, 45, 13, 46, 47, 48, 17, 13, 49, 50,
                          51, 17, 13, 52, 53, 54, 55, 56, 57, 58, 17, 59, 60,
                          17, 17, 61, 13, 62, 63, 53, 54, 55, 64, 57, 65, 17,
                          59, 66, 17, 17, 13, 53, 54, 55, 67, 57, 68, 17, 59,
                          69, 17, 17, 13, 53, 54, 55, 70, 57, 71, 17, 59, 72,
                          17, 17, 13, 53, 54, 55, 73, 57, 74, 17, 59, 75, 17,
                          17, 13, 53, 54, 55, 76, 57, 77, 17, 59, 78, 17, 17,
                          13, 53, 54, 55, 79, 57, 80, 17, 59, 81, 17, 17, 13,
                          53, 54, 55, 82, 57, 83, 17, 59, 84, 17, 17, 13, 53,
                          54, 55, 85, 57, 86, 17, 59, 87, 17, 17, 13, 53, 54,
                          55, 88, 57, 89, 17, 59, 90, 17, 17, 13, 53, 54, 55,
                          91, 57, 92, 17, 59, 93, 17, 17, 13, 53, 54, 55, 94,
                          57, 95, 17, 59, 96, 17, 17, 13, 53, 54, 55, 97, 57,
                          98, 17, 59, 99, 17, 17, 13, 53, 54, 55, 100, 57, 101,
                          17, 59, 102, 17, 17, 13, 53, 54, 55, 103, 57, 104, 17,
                          59, 105, 17, 17, 13, 53, 54, 55, 106, 57, 107, 17, 59,
                          108, 17, 17, 61, 13, 109, 110, 111, 112, 13, 113, 114,
                          115, 116, 117, 118, 119, 120, 121, 122, 123, 124, 125,
                          126, 127, 128, 129, 130, 13, 131, 13, 132, 133, 134,
                          13, 135, 136, 137, 138, 139, 140, 141, 142, 143, 17,
                          17, 144, 17, 17, 13, 145, 146, 17, 13, 147, 148, 149,
                          150, 151, 17, 13, 152, 153, 154, 13, 155, 156, 157,
                          158, 13, 17, 61, 13, 159, 160, 161, 162, 17, 13, 163,
                          13, 17, 13, 164, 13, 17, 13, 165, 13, 17, 61, 13, 166,
                          167, 168, 169, 17, 61, 13, 170, 171, 172, 173, 17, 13,
                          174, 13, 17, 61, 13, 175, 176, 177, 178, 17, 61, 13,
                          179, 180, 181, 182, 17, 61, 13, 183, 184, 185, 186,
                          17, 61, 13, 187, 188, 189, 190, 17, 61, 13, 191, 192,
                          110, 193, 194, 17, 13, 195, 110, 196, 197, 17, 61, 17,
                          17],
                         [("equal",   0, 12, 0, 12),
                          ("insert", 12, 12, 12, 17),
                          ("equal",  12, 17, 17, 22),
                          ("insert", 17, 17, 22, 331),
                          ("equal",  17, 19, 331, 333),
                          ("insert", 19, 19, 333, 402),
                          ("equal",  19, 20, 402, 403)])


    def __test_diff(self, a, b, expected):
        opcodes = list(diffutils.MyersDiffer(a, b).get_opcodes())
        self.assertEquals(opcodes, expected)


class DiffParserTest(unittest.TestCase):
    PREFIX = 'diffviewer/testdata'

    def diff(self, options=''):
        f = os.popen('diff -rN -x .svn %s %s/orig_src %s/new_src' %
                     (options, self.PREFIX, self.PREFIX))
        data = f.read()
        f.close()
        return data

    def compareDiffs(self, files, testdir):
        self.failUnless(len(files) == 3)
        for file in files:
            f = open("%s/diffs/%s/%s.diff" %
                     (self.PREFIX, testdir, os.path.basename(file.newFile)))
            data = f.read()
            f.close()

            self.failUnless(file.origFile.startswith("%s/orig_src/" %
                                                     self.PREFIX))
            self.failUnless(file.newFile.startswith("%s/new_src/" %
                                                    self.PREFIX))
            self.assertNotEquals(file.origInfo, "")
            self.assertNotEquals(file.newInfo, "")

            self.assertNotEquals(file.data, "")
            self.assertNotEquals(data, "")

            # Can't really compare the strings because of timestamps...

    def testUnifiedDiff(self):
        """Testing parse on a unified diff"""
        data = self.diff('-u')
        files = diffparser.DiffParser(data).parse()
        self.compareDiffs(files, "unified")

    def testContextDiff(self):
        """Testing parse on a context diff"""
        data = self.diff('-c')
        files = diffparser.DiffParser(data).parse()
        self.compareDiffs(files, "context")

    def testPatch(self):
        """Testing patching"""

        def get_file(*relative):
            f = open(os.path.join(*tuple([self.PREFIX] + list(relative))))
            data = f.read()
            f.close()
            return data

        file = 'foo.c'

        old = get_file('orig_src', file)
        new = get_file('new_src', file)
        diff = get_file('diffs', 'unified', 'foo.c.diff')

        patched = diffutils.patch(diff, old, file)
        self.assertEqual(patched, new)

        diff = get_file('diffs', 'unified', 'README.diff')
        self.assertRaises(Exception, lambda: diffutils.patch(diff, old, file))

    def testInterline(self):
        """Testing inter-line diffs"""

        def deepEqual(A, B):
            typea, typeb = type(A), type(B)
            self.assertEqual(typea, typeb)
            if typea is tuple or typea is list:
                for a, b in map(None, A, B):
                    deepEqual(a, b)
            else:
                self.assertEqual(A, B)

        deepEqual(diffutils.get_line_changed_regions(None, None),
                  (None, None))

        old = 'submitter = models.ForeignKey(Person, verbose_name="Submitter")'
        new = 'submitter = models.ForeignKey(User, verbose_name="Submitter")'
        regions = diffutils.get_line_changed_regions(old, new)
        deepEqual(regions, ([(30, 36)], [(30, 34)]))


        old = '-from reviews.models import ReviewRequest, Person, Group'
        new = '+from .reviews.models import ReviewRequest, Group'
        regions = diffutils.get_line_changed_regions(old, new)
        deepEqual(regions, ([(0, 1), (6, 6), (43, 51)],
                            [(0, 1), (6, 7), (44, 44)]))

        old = 'abcdefghijklm'
        new = 'nopqrstuvwxyz'
        regions = diffutils.get_line_changed_regions(old, new)
        deepEqual(regions, (None, None))


class HighlightRegionTest(TestCase):
    def setUp(self):
        settings.DIFF_SYNTAX_HIGHLIGHTING = True

    def testHighlightRegion(self):
        """Testing highlightregion"""
        self.assertEquals(highlightregion("", None), "")

        self.assertEquals(highlightregion("abc", None), "abc")

        self.assertEquals(highlightregion("abc", [(0, 3)]),
                                          '<span class="hl">abc</span>')

        self.assertEquals(highlightregion("abc", [(0, 1)]),
                                          '<span class="hl">a</span>bc')

        self.assertEquals(highlightregion(
            '<span class="xy">a</span>bc',
            [(0, 1)]),
            '<span class="xy"><span class="hl">a</span></span>bc')

        self.assertEquals(highlightregion(
            '<span class="xy">abc</span>123',
            [(1, 4)]),
            '<span class="xy">a<span class="hl">bc</span></span>' +
            '<span class="hl">1</span>23')

        self.assertEquals(highlightregion(
            '<span class="xy">abc</span><span class="z">12</span>3',
            [(1, 4)]),
            '<span class="xy">a<span class="hl">bc</span></span>' +
            '<span class="z"><span class="hl">1</span>2</span>3')

        self.assertEquals(highlightregion(
            'foo<span class="xy">abc</span><span class="z">12</span>3',
            [(0, 6), (7, 9)]),
            '<span class="hl">foo</span><span class="xy">' +
            '<span class="hl">abc</span></span><span class="z">1' +
            '<span class="hl">2</span></span><span class="hl">3</span>')

        self.assertEquals(highlightregion(
            'foo&quot;bar',
            [(0, 7)]),
            '<span class="hl">foo&quot;bar</span>')

        self.assertEquals(highlightregion(
            '&quot;foo&quot;',
            [(0, 1)]),
            '<span class="hl">&quot;</span>foo&quot;')

        self.assertEquals(highlightregion(
            '&quot;foo&quot;',
            [(2, 5)]),
            '&quot;f<span class="hl">oo&quot;</span>')

        self.assertEquals(highlightregion(
            'foo=<span class="ab">&quot;foo&quot;</span>)',
            [(4, 9)]),
            'foo=<span class="ab"><span class="hl">&quot;foo&quot;' +
            '</span></span>)')
