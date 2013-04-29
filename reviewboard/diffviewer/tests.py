import os
import unittest

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from djblets.siteconfig.models import SiteConfiguration

from reviewboard.diffviewer.forms import UploadDiffForm
from reviewboard.diffviewer.models import DiffSet, FileDiff
from reviewboard.diffviewer.templatetags.difftags import highlightregion
import reviewboard.diffviewer.diffutils as diffutils
import reviewboard.diffviewer.parser as diffparser
from reviewboard.scmtools.models import Repository, Tool


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

    def test_line_counts(self):
        """Testing DiffParser with insert/delete line counts"""
        diff = (
            '+ This is some line before the change\n'
            '- And another line\n'
            'Index: foo\n'
            '- One last.\n'
            '--- README  123\n'
            '+++ README  (new)\n'
            '@ -1,1 +1,1 @@\n'
            '-blah blah\n'
            '-blah\n'
            '+blah!\n'
            '-blah...\n'
            '+blah?\n'
            '-blah!\n'
            '+blah?!\n')
        files = diffparser.DiffParser(diff).parse()

        self.assertEqual(len(files), 1)
        self.assertEqual(files[0].insert_count, 3)
        self.assertEqual(files[0].delete_count, 4)

    def _get_file(self, *relative):
        f = open(os.path.join(*tuple([self.PREFIX] + list(relative))))
        data = f.read()
        f.close()
        return data


class FileDiffMigrationTests(TestCase):
    fixtures = ['test_scmtools.json']

    def setUp(self):
        self.diff = (
            '--- README  123\n'
            '+++ README  (new)\n'
            '@ -1,1 +1,1 @@\n'
            '-blah blah\n'
            '+blah!\n')
        self.parent_diff = (
            '--- README  123\n'
            '+++ README  (new)\n'
            '@ -1,1 +1,1 @@\n'
            '-blah..\n'
            '+blah blah\n')

        repository = Repository.objects.get(pk=1)
        diffset = DiffSet.objects.create(name='test',
                                         revision=1,
                                         repository=repository)
        self.filediff = FileDiff(source_file='README',
                                 dest_file='README',
                                 diffset=diffset,
                                 diff64='',
                                 parent_diff64='')

    def test_migration_by_diff(self):
        """Testing FileDiffData migration accessing FileDiff.diff"""
        self.filediff.diff64 = self.diff

        self.assertEqual(self.filediff.diff_hash, None)
        self.assertEqual(self.filediff.parent_diff_hash, None)

        # This should prompt the migration
        diff = self.filediff.diff

        self.assertEqual(self.filediff.parent_diff_hash, None)
        self.assertNotEqual(self.filediff.diff_hash, None)

        self.assertEqual(diff, self.diff)
        self.assertEqual(self.filediff.diff64, '')
        self.assertEqual(self.filediff.diff_hash.binary, self.diff)
        self.assertEqual(self.filediff.diff, diff)
        self.assertEqual(self.filediff.parent_diff, None)
        self.assertEqual(self.filediff.parent_diff_hash, None)

    def test_migration_by_parent_diff(self):
        """Testing FileDiffData migration accessing FileDiff.parent_diff"""
        self.filediff.diff64 = self.diff
        self.filediff.parent_diff64 = self.parent_diff

        self.assertEqual(self.filediff.parent_diff_hash, None)

        # This should prompt the migration
        parent_diff = self.filediff.parent_diff

        self.assertNotEqual(self.filediff.parent_diff_hash, None)

        self.assertEqual(parent_diff, self.parent_diff)
        self.assertEqual(self.filediff.parent_diff64, '')
        self.assertEqual(self.filediff.parent_diff_hash.binary,
                         self.parent_diff)
        self.assertEqual(self.filediff.parent_diff, self.parent_diff)

    def test_migration_by_delete_count(self):
        """Testing FileDiffData migration accessing FileDiff.delete_count"""
        self.filediff.diff64 = self.diff

        self.assertEqual(self.filediff.diff_hash, None)

        # This should prompt the migration
        delete_count = self.filediff.delete_count

        self.assertNotEqual(self.filediff.diff_hash, None)
        self.assertEqual(delete_count, 1)
        self.assertEqual(self.filediff.diff_hash.delete_count, 1)

    def test_migration_by_insert_count(self):
        """Testing FileDiffData migration accessing FileDiff.insert_count"""
        self.filediff.diff64 = self.diff

        self.assertEqual(self.filediff.diff_hash, None)

        # This should prompt the migration
        insert_count = self.filediff.insert_count

        self.assertNotEqual(self.filediff.diff_hash, None)
        self.assertEqual(insert_count, 1)
        self.assertEqual(self.filediff.diff_hash.insert_count, 1)

    def test_migration_by_set_line_counts(self):
        """Testing FileDiffData migration calling FileDiff.set_line_counts"""
        self.filediff.diff64 = self.diff

        self.assertEqual(self.filediff.diff_hash, None)

        # This should prompt the migration, but with our line counts.
        self.filediff.set_line_counts(10, 20)

        self.assertNotEqual(self.filediff.diff_hash, None)
        self.assertEqual(self.filediff.insert_count, 10)
        self.assertEqual(self.filediff.delete_count, 20)
        self.assertEqual(self.filediff.diff_hash.insert_count, 10)
        self.assertEqual(self.filediff.diff_hash.delete_count, 20)


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


class UploadDiffFormTests(TestCase):
    """Unit tests for UploadDiffForm."""
    fixtures = ['test_scmtools']

    def test_parent_diff_filtering(self):
        """Testing UploadDiffForm and filtering parent diff files"""
        saw_file_exists = {}

        def get_file_exists(filename, revision, request):
            saw_file_exists[(filename, revision)] = True
            return True

        diff = (
            'Index: README\n'
            '==========================================================='
            '========\n'
            '--- README  (revision 124)\n'
            '+++ README  (new)\n'
            '@ -1,1 +1,1 @@\n'
            '-blah blah\n'
            '+blah!\n'
        )
        parent_diff_1 = (
            'Index: README\n'
            '==========================================================='
            '========\n'
            '--- README  (revision 123)\n'
            '+++ README  (new)\n'
            '@ -1,1 +1,1 @@\n'
            '-blah..\n'
            '+blah blah\n'
        )
        parent_diff_2 = (
            'Index: UNUSED\n'
            '==========================================================='
            '========\n'
            '--- UNUSED  (revision 123)\n'
            '+++ UNUSED  (new)\n'
            '@ -1,1 +1,1 @@\n'
            '-foo\n'
            '+bar\n'
        )
        parent_diff = parent_diff_1 + parent_diff_2

        diff_file = SimpleUploadedFile('diff', diff,
                                       content_type='text/x-patch')
        parent_diff_file = SimpleUploadedFile('parent_diff', parent_diff,
                                              content_type='text/x-patch')

        # Note that we're using SVN here for the test just because it's
        # a bit easier to test with than Git (easier diff parsing logic
        # and revision numbers).
        repository = Repository.objects.create(
            name='Subversion SVN',
            path='file://%s' % (os.path.join(os.path.dirname(__file__),
                                             '..', 'scmtools', 'testdata',
                                             'svn_repo')),
            tool=Tool.objects.get(name='Subversion'))
        repository.get_file_exists = get_file_exists

        form = UploadDiffForm(
            repository=repository,
            data={
                'basedir': '/',
            },
            files={
                'path': diff_file,
                'parent_diff_path': parent_diff_file,
            })
        self.assertTrue(form.is_valid())

        diffset = form.create(diff_file, parent_diff_file)
        self.assertEqual(diffset.files.count(), 1)

        filediff = diffset.files.get()
        self.assertEqual(filediff.diff, diff)
        self.assertEqual(filediff.parent_diff, parent_diff_1)

        self.assertTrue(('/README', '123') in saw_file_exists)
        self.assertFalse(('/UNUSED', '123') in saw_file_exists)
        self.assertEqual(len(saw_file_exists), 1)
