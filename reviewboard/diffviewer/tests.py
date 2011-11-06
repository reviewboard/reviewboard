import os
import unittest

from django.test import TestCase
from djblets.siteconfig.models import SiteConfiguration

from reviewboard.diffviewer.models import DiffSet, FileDiff
from reviewboard.diffviewer.templatetags.difftags import highlightregion
import reviewboard.diffviewer.diffutils as diffutils
import reviewboard.diffviewer.parser as diffparser
from reviewboard.scmtools.models import Repository


class MyersDifferTest(TestCase):
    def testDiff(self):
        """Testing myers differ"""
        self.__test_diff(["1", "2", "3"],
                         ["1", "2", "3"],
                         [("equal", 0, 3, 0, 3), ])

        self.__test_diff(["1", "2", "3"],
                         [],
                         [("delete", 0, 3, 0, 0), ])

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

    def __test_diff(self, a, b, expected):
        opcodes = list(diffutils.MyersDiffer(a, b).get_opcodes())
        self.assertEquals(opcodes, expected)


class InterestingLinesTest(TestCase):
    PREFIX = os.path.join(os.path.dirname(__file__), 'testdata')

    def testCSharp(self):
        """Testing interesting lines scanner with a C# file"""
        lines = self.__get_lines("helloworld.cs")

        self.assertEqual(len(lines[0]), 2)
        self.assertEqual(lines[0][0], (0, 'public class HelloWorld {\n'))
        self.assertEqual(lines[0][1], (1, '\tpublic static void Main() {\n'))

        self.assertEqual(lines[1][0], (3, 'public class HelloWorld\n'))
        self.assertEqual(lines[1][1], (8, '\tpublic static void Main()\n'))

    def testJava(self):
        """Testing interesting lines scanner with a Java file"""
        lines = self.__get_lines("helloworld.java")

        self.assertEqual(len(lines[0]), 2)
        self.assertEqual(lines[0][0], (0, 'class HelloWorld {\n'))
        self.assertEqual(lines[0][1],
                         (1, '\tpublic static void main(String[] args) {\n'))

        self.assertEqual(len(lines[1]), 2)
        self.assertEqual(lines[1][0], (3, 'class HelloWorld\n'))
        self.assertEqual(lines[1][1],
                         (8, '\tpublic static void main(String[] args)\n'))

    def testJavaScript(self):
        """Testing interesting lines scanner with a JavaScript file"""
        lines = self.__get_lines("helloworld.js")

        self.assertEqual(len(lines[0]), 3)
        self.assertEqual(lines[0][0], (0, 'function helloWorld() {\n'))
        self.assertEqual(lines[0][1], (5, '\thelloWorld2: function() {\n'))
        self.assertEqual(lines[0][2], (10, 'var helloWorld3 = function() {\n'))

        self.assertEqual(len(lines[1]), 3)
        self.assertEqual(lines[1][0], (3, 'function helloWorld()\n'))
        self.assertEqual(lines[1][1], (12, '\thelloWorld2: function()\n'))
        self.assertEqual(lines[1][2], (18, 'var helloWorld3 = function()\n'))

    def testObjectiveC(self):
        """Testing interesting lines scanner with an Objective C file"""
        lines = self.__get_lines("helloworld.m")

        self.assertEqual(len(lines[0]), 3)
        self.assertEqual(lines[0][0], (0, '@interface MyClass : Object\n'))
        self.assertEqual(lines[0][1], (4, '@implementation MyClass\n'))
        self.assertEqual(lines[0][2], (5, '- (void) sayHello {\n'))

        self.assertEqual(len(lines[1]), 3)
        self.assertEqual(lines[1][0], (0, '@interface MyClass : Object\n'))
        self.assertEqual(lines[1][1], (4, '@implementation MyClass\n'))
        self.assertEqual(lines[1][2], (8, '- (void) sayHello\n'))

    def testPerl(self):
        """Testing interesting lines scanner with a Perl file"""
        lines = self.__get_lines("helloworld.pl")

        self.assertEqual(len(lines[0]), 1)
        self.assertEqual(lines[0][0], (0, 'sub helloWorld {\n'))

        self.assertEqual(len(lines[1]), 1)
        self.assertEqual(lines[1][0], (1, 'sub helloWorld\n'))

    def testPHP(self):
        """Testing interesting lines scanner with a PHP file"""
        lines = self.__get_lines("helloworld.php")

        self.assertEqual(len(lines[0]), 2)
        self.assertEqual(lines[0][0], (1, 'class HelloWorld {\n'))
        self.assertEqual(lines[0][1], (2, '\tfunction helloWorld() {\n'))

        self.assertEqual(len(lines[1]), 2)
        self.assertEqual(lines[1][0], (4, 'class HelloWorld\n'))
        self.assertEqual(lines[1][1], (9, '\tfunction helloWorld()\n'))

    def testPython(self):
        """Testing interesting lines scanner with a Python file"""
        lines = self.__get_lines("helloworld.py")

        self.assertEqual(len(lines[0]), 2)
        self.assertEqual(lines[0][0], (0, 'class HelloWorld:\n'))
        self.assertEqual(lines[0][1], (1, '    def main(self):\n'))

        self.assertEqual(len(lines[1]), 2)
        self.assertEqual(lines[1][0], (0, 'class HelloWorld:\n'))
        self.assertEqual(lines[1][1], (3, '    def main(self):\n'))

    def testRuby(self):
        """Testing interesting lines scanner with a Ruby file"""
        lines = self.__get_lines("helloworld.rb")

        self.assertEqual(len(lines[0]), 2)
        self.assertEqual(lines[0][0], (0, 'class HelloWorld\n'))
        self.assertEqual(lines[0][1], (1, '\tdef helloWorld\n'))

        self.assertEqual(len(lines[1]), 2)
        self.assertEqual(lines[1][0], (1, 'class HelloWorld\n'))
        self.assertEqual(lines[1][1], (3, '\tdef helloWorld()\n'))

    def __get_lines(self, filename):
        f = open(os.path.join(self.PREFIX, "orig_src", filename), "r")
        a = f.readlines()
        f.close()

        f = open(os.path.join(self.PREFIX, "new_src", filename), "r")
        b = f.readlines()
        f.close()

        differ = diffutils.MyersDiffer(a, b)
        diffutils.register_interesting_lines_for_filename(differ, filename)

        # Begin the scan.
        list(differ.get_opcodes())

        result = (differ.get_interesting_lines('header', False),
                  differ.get_interesting_lines('header', True))

        print result

        return result


class DiffParserTest(unittest.TestCase):
    PREFIX = os.path.join(os.path.dirname(__file__), 'testdata')

    def diff(self, options=''):
        f = os.popen('diff -rN -x .svn %s %s/orig_src %s/new_src' %
                     (options, self.PREFIX, self.PREFIX))
        data = f.read()
        f.close()
        return data

    def compareDiffs(self, files, testdir):
        self.assertEqual(len(files), 14)

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

        file = 'foo.c'

        old = self._get_file('orig_src', file)
        new = self._get_file('new_src', file)
        diff = self._get_file('diffs', 'unified', 'foo.c.diff')

        patched = diffutils.patch(diff, old, file)
        self.assertEqual(patched, new)

        diff = self._get_file('diffs', 'unified', 'README.diff')
        self.assertRaises(Exception, lambda: diffutils.patch(diff, old, file))

    def testEmptyPatch(self):
        """Testing patching with an empty diff"""
        old = 'This is a test'
        diff = ''
        patched = diffutils.patch(diff, old, 'test.c')
        self.assertEqual(patched, old)

    def testPatchCRLFFileCRLFDiff(self):
        """Testing patching a CRLF file with a CRLF diff"""
        old = self._get_file('orig_src', 'README.crlf')
        new = self._get_file('new_src', 'README')
        diff = self._get_file('diffs', 'unified', 'README.crlf.diff')
        patched = diffutils.patch(diff, old, new)
        self.assertEqual(patched, new)

    def testPatchCRFileCRLFDiff(self):
        """Testing patching a CR file with a CRLF diff"""
        old = self._get_file('orig_src', 'README')
        new = self._get_file('new_src', 'README')
        diff = self._get_file('diffs', 'unified', 'README.crlf.diff')
        patched = diffutils.patch(diff, old, new)
        self.assertEqual(patched, new)

    def testPatchCRLFFileCRDiff(self):
        """Testing patching a CRLF file with a CR diff"""
        old = self._get_file('orig_src', 'README.crlf')
        new = self._get_file('new_src', 'README')
        diff = self._get_file('diffs', 'unified', 'README.diff')
        patched = diffutils.patch(diff, old, new)
        self.assertEqual(patched, new)

    def testPatchFileWithFakeNoNewline(self):
        """Testing patching a file indicating no newline with a trailing \\r"""
        old = self._get_file('orig_src', 'README.nonewline')
        new = self._get_file('new_src', 'README.nonewline')
        diff = self._get_file('diffs', 'unified', 'README.nonewline.diff')
        files = diffparser.DiffParser(diff).parse()
        patched = diffutils.patch(files[0].data, old, new)
        self.assertEqual(diff, files[0].data)
        self.assertEqual(patched, new)

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

    def testMoveDetection(self):
        """Testing move detection"""
        # movetest1 has two blocks of code that would appear to be moves:
        # a function, and an empty comment block. Only the function should
        # be seen as a move, whereas the empty comment block is less useful
        # (since it's content-less) and shouldn't be seen as once.
        old = self._get_file('orig_src', 'movetest1.c')
        new = self._get_file('new_src', 'movetest1.c')
        differ = diffutils.Differ(old.splitlines(), new.splitlines())

        r_moves = []
        i_moves = []

        for opcodes in diffutils.opcodes_with_metadata(differ):
            tag = opcodes[0]
            meta = opcodes[-1]

            if tag == 'delete':
                if 'moved' in meta:
                    r_moves.append(meta['moved'])
            elif tag == 'insert':
                if 'moved' in meta:
                    i_moves.append(meta['moved'])

        self.assertEqual(len(r_moves), 1)
        self.assertEqual(len(i_moves), 1)

        moves = [
            (15, 28),
            (16, 29),
            (17, 30),
            (18, 31),
            (19, 32)
        ]

        for i, j in moves:
            self.assertTrue(j in i_moves[0])
            self.assertTrue(i in r_moves[0])
            self.assertEqual(i_moves[0][j], i)
            self.assertEqual(r_moves[0][i], j)

    def _get_file(self, *relative):
        f = open(os.path.join(*tuple([self.PREFIX] + list(relative))))
        data = f.read()
        f.close()
        return data


class HighlightRegionTest(TestCase):
    def setUp(self):
        siteconfig = SiteConfiguration.objects.get_current()
        siteconfig.set('diffviewer_syntax_highlighting', True)

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


class DbTests(TestCase):
    """Unit tests for database operations."""
    fixtures = ['test_scmtools.json']
    PREFIX = os.path.join(os.path.dirname(__file__), 'testdata')

    def testLongFilenames(self):
        """Testing using long filenames (1024 characters) in FileDiff."""
        long_filename = 'x' * 1024

        repository = Repository.objects.get(pk=1)
        diffset = DiffSet.objects.create(name='test',
                                         revision=1,
                                         repository=repository)
        filediff = FileDiff(source_file=long_filename,
                            dest_file='foo',
                            diffset=diffset)
        filediff.save()

        filediff = FileDiff.objects.get(pk=filediff.id)
        self.assertEquals(filediff.source_file, long_filename)

    def testDiffHashes(self):
        """
        Testing that uploading two of the same diff will result in only
        one database entry.
        """
        repository = Repository.objects.get(pk=1)
        diffset = DiffSet.objects.create(name='test',
                                         revision=1,
                                         repository=repository)
        f = open(os.path.join(self.PREFIX, "diffs", "context", "foo.c.diff"),
                 "r")
        data = f.read()
        f.close()

        filediff1 = FileDiff(diff=data,
                             diffset=diffset)
        filediff1.save()
        filediff2 = FileDiff(diff=data,
                             diffset=diffset)
        filediff2.save()

        self.assertEquals(filediff1.diff_hash, filediff2.diff_hash)
