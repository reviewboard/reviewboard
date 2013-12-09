from __future__ import unicode_literals

import os
import unittest

from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import HttpResponse
from djblets.cache.backend import cache_memoize
from djblets.siteconfig.models import SiteConfiguration
from djblets.util.compat.six.moves import zip_longest
from kgb import SpyAgency
import nose

import reviewboard.diffviewer.diffutils as diffutils
import reviewboard.diffviewer.parser as diffparser
from reviewboard.diffviewer.chunk_generator import DiffChunkGenerator
from reviewboard.diffviewer.errors import UserVisibleError
from reviewboard.diffviewer.forms import UploadDiffForm
from reviewboard.diffviewer.models import DiffSet, FileDiff
from reviewboard.diffviewer.myersdiff import MyersDiffer
from reviewboard.diffviewer.opcode_generator import get_diff_opcode_generator
from reviewboard.diffviewer.renderers import DiffRenderer
from reviewboard.diffviewer.processors import (filter_interdiff_opcodes,
                                               merge_adjacent_chunks)
from reviewboard.diffviewer.templatetags.difftags import highlightregion
from reviewboard.scmtools.models import Repository, Tool
from reviewboard.testing import TestCase


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
                          ("equal", 0, 6, 2, 8)])

        self.__test_diff("1\n2\n3\n7\n",
                         "1\n2\n4\n5\n6\n7\n",
                         [("equal", 0, 4, 0, 4),
                          ("replace", 4, 5, 4, 5),
                          ("insert", 5, 5, 5, 9),
                          ("equal", 5, 8, 9, 12)])

    def __test_diff(self, a, b, expected):
        opcodes = list(MyersDiffer(a, b).get_opcodes())
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
        with open(os.path.join(self.PREFIX, "orig_src", filename), "r") as f:
            a = f.readlines()

        with open(os.path.join(self.PREFIX, "new_src", filename), "r") as f:
            b = f.readlines()

        differ = MyersDiffer(a, b)
        differ.add_interesting_lines_for_headers(filename)

        # Begin the scan.
        list(differ.get_opcodes())

        result = (differ.get_interesting_lines('header', False),
                  differ.get_interesting_lines('header', True))

        return result


class DiffParserTest(TestCase):
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

            self.assertTrue(file.origFile.startswith("%s/orig_src/" %
                                                     self.PREFIX))
            self.assertTrue(file.newFile.startswith("%s/new_src/" %
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

    def test_move_detection(self):
        """Testing diff viewer move detection"""
        # movetest1 has two blocks of code that would appear to be moves:
        # a function, and an empty comment block. Only the function should
        # be seen as a move, whereas the empty comment block is less useful
        # (since it's content-less) and shouldn't be seen as once.
        old = self._get_file('orig_src', 'movetest1.c')
        new = self._get_file('new_src', 'movetest1.c')

        self._test_move_detection(
            old.splitlines(),
            new.splitlines(),
            [
                {
                    28: 15,
                    29: 16,
                    30: 17,
                    31: 18,
                }
            ],
            [
                {
                    15: 28,
                    16: 29,
                    17: 30,
                    18: 31,
                }
            ])

    def test_move_detection_with_replace_lines(self):
        """Testing diff viewer move detection with replace lines"""
        self._test_move_detection(
            [
                'this is line 1, and it is sufficiently long',
                '-------------------------------------------',
                '-------------------------------------------',
                'this is line 2, and it is sufficiently long',
            ],
            [
                'this is line 2, and it is sufficiently long',
                '-------------------------------------------',
                '-------------------------------------------',
                'this is line 1, and it is sufficiently long',
            ],
            [
                {1: 4},
                {4: 1},
            ],
            [
                {1: 4},
                {4: 1},
            ]
        )

    def test_move_detection_with_adjacent_regions(self):
        """Testing diff viewer move detection with adjacent regions"""
        self._test_move_detection(
            [
                '1. Lorem ipsum dolor sit amet, consectetur adipiscing elit.',
                '2. Phasellus et lectus vulputate, dictum mi id, auctor ante.',
                '3. Nulla accumsan tellus ut felis ultrices euismod.',
                '4. Donec quis augue sed arcu tristique pellentesque.',
                '5. Fusce rutrum diam vel viverra sagittis.',
                '6. Nam tincidunt sapien vitae lorem vestibulum tempor.',
                '7. Donec fermentum tortor ut egestas convallis.',
            ],
            [
                '6. Nam tincidunt sapien vitae lorem vestibulum tempor.',
                '7. Donec fermentum tortor ut egestas convallis.',
                '4. Donec quis augue sed arcu tristique pellentesque.',
                '5. Fusce rutrum diam vel viverra sagittis.',
                '1. Lorem ipsum dolor sit amet, consectetur adipiscing elit.',
                '2. Phasellus et lectus vulputate, dictum mi id, auctor ante.',
                '3. Nulla accumsan tellus ut felis ultrices euismod.',
            ],
            [
                {
                    1: 6,
                    2: 7,
                    3: 4,
                    4: 5,
                }
            ],
            [
                {
                    4: 3,
                    5: 4,
                    6: 1,
                    7: 2,
                }
            ],
        )

    def test_move_detection_single_line_thresholds(self):
        """Testing diff viewer move detection with a single line and
        line length threshold
        """
        self._test_move_detection(
            [
                '0123456789012345678',
                '----',
                '----',
                'abcdefghijklmnopqrst',
            ],
            [
                'abcdefghijklmnopqrst',
                '----',
                '----',
                '0123456789012345678',
            ],
            [
                {1: 4},
            ],
            [
                {4: 1},
            ]
        )

    def test_move_detection_multi_line_thresholds(self):
        """Testing diff viewer move detection with a multiple lines and
        line count threshold
        """
        self._test_move_detection(
            [
                '123',
                '456',
                '789',
                'ten',
                'abcdefghijk',
                'lmno',
                'pqr',
            ],
            [
                'abcdefghijk',
                'lmno',
                'pqr',
                '123',
                '456',
                '789',
                'ten',
            ],
            [
                {
                    1: 5,
                    2: 6,
                },
            ],
            [
                {
                    5: 1,
                    6: 2,
                },
            ]
        )

    def test_line_counts(self):
        """Testing DiffParser with insert/delete line counts"""
        diff = (
            b'+ This is some line before the change\n'
            b'- And another line\n'
            b'Index: foo\n'
            b'- One last.\n'
            b'--- README  123\n'
            b'+++ README  (new)\n'
            b'@ -1,1 +1,1 @@\n'
            b'-blah blah\n'
            b'-blah\n'
            b'+blah!\n'
            b'-blah...\n'
            b'+blah?\n'
            b'-blah!\n'
            b'+blah?!\n')
        files = diffparser.DiffParser(diff).parse()

        self.assertEqual(len(files), 1)
        self.assertEqual(files[0].insert_count, 3)
        self.assertEqual(files[0].delete_count, 4)

    def _get_file(self, *relative):
        path = os.path.join(*tuple([self.PREFIX] + list(relative)))
        with open(path, 'rb') as f:
            return f.read()

    def _test_move_detection(self, a, b, expected_i_moves, expected_r_moves):
        differ = MyersDiffer(a, b)
        opcode_generator = get_diff_opcode_generator(differ)

        r_moves = []
        i_moves = []

        for opcodes in opcode_generator:
            tag = opcodes[0]
            meta = opcodes[-1]

            if 'moved-to' in meta:
                r_moves.append(meta['moved-to'])

            if 'moved-from' in meta:
                i_moves.append(meta['moved-from'])

        self.assertEqual(i_moves, expected_i_moves)
        self.assertEqual(r_moves, expected_r_moves)


class FileDiffMigrationTests(TestCase):
    fixtures = ['test_scmtools']

    def setUp(self):
        self.diff = (
            b'diff --git a/README b/README\n'
            b'index d6613f5..5b50866 100644\n'
            b'--- README\n'
            b'+++ README\n'
            b'@ -1,1 +1,1 @@\n'
            b'-blah blah\n'
            b'+blah!\n')
        self.parent_diff = (
            b'diff --git a/README b/README\n'
            b'index d6613f5..5b50866 100644\n'
            b'--- README\n'
            b'+++ README\n'
            b'@ -1,1 +1,1 @@\n'
            b'-blah..\n'
            b'+blah blah\n')

        repository = self.create_repository(tool_name='Test')
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
    fixtures = ['test_scmtools']
    PREFIX = os.path.join(os.path.dirname(__file__), 'testdata')

    def test_long_filenames(self):
        """Testing using long filenames (1024 characters) in FileDiff."""
        long_filename = 'x' * 1024

        repository = self.create_repository()
        diffset = DiffSet.objects.create(name='test',
                                         revision=1,
                                         repository=repository)
        filediff = FileDiff(source_file=long_filename,
                            dest_file='foo',
                            diffset=diffset)
        filediff.save()

        filediff = FileDiff.objects.get(pk=filediff.id)
        self.assertEquals(filediff.source_file, long_filename)

    def test_diff_hashes(self):
        """
        Testing that uploading two of the same diff will result in only
        one database entry.
        """
        repository = self.create_repository()
        diffset = DiffSet.objects.create(name='test',
                                         revision=1,
                                         repository=repository)
        with open(os.path.join(self.PREFIX, "diffs", "context",
                               "foo.c.diff")) as f:
            data = f.read()

        filediff1 = FileDiff(diff=data,
                             diffset=diffset)
        filediff1.save()
        filediff2 = FileDiff(diff=data,
                             diffset=diffset)
        filediff2.save()

        self.assertEquals(filediff1.diff_hash, filediff2.diff_hash)


class DiffSetManagerTests(SpyAgency, TestCase):
    """Unit tests for DiffSetManager."""
    fixtures = ['test_scmtools']

    def test_creating_with_diff_data(self):
        """Test creating a DiffSet from diff file data"""
        diff = (
            b'diff --git a/README b/README\n'
            b'index d6613f5..5b50866 100644\n'
            b'--- README\n'
            b'+++ README\n'
            b'@ -1,1 +1,1 @@\n'
            b'-blah..\n'
            b'+blah blah\n'
        )

        repository = self.create_repository(tool_name='Test')

        self.spy_on(repository.get_file_exists,
                    call_fake=lambda *args, **kwargs: True)

        diffset = DiffSet.objects.create_from_data(
            repository, 'diff', diff, None, None, None, '/', None)

        self.assertEqual(diffset.files.count(), 1)


class UploadDiffFormTests(SpyAgency, TestCase):
    """Unit tests for UploadDiffForm."""
    fixtures = ['test_scmtools']

    def test_creating_diffsets(self):
        """Test creating a DiffSet from form data"""
        diff = (
            b'diff --git a/README b/README\n'
            b'index d6613f5..5b50866 100644\n'
            b'--- README\n'
            b'+++ README\n'
            b'@ -1,1 +1,1 @@\n'
            b'-blah..\n'
            b'+blah blah\n'
        )

        diff_file = SimpleUploadedFile('diff', diff,
                                       content_type='text/x-patch')

        repository = self.create_repository(tool_name='Test')

        self.spy_on(repository.get_file_exists,
                    call_fake=lambda *args, **kwargs: True)

        form = UploadDiffForm(
            repository=repository,
            data={
                'basedir': '/',
                'base_commit_id': '1234',
            },
            files={
                'path': diff_file,
            })
        self.assertTrue(form.is_valid())

        diffset = form.create(diff_file)
        self.assertEqual(diffset.files.count(), 1)
        self.assertEqual(diffset.basedir, '/')
        self.assertEqual(diffset.base_commit_id, '1234')

    def test_parent_diff_filtering(self):
        """Testing UploadDiffForm and filtering parent diff files"""
        saw_file_exists = {}

        def get_file_exists(repository, filename, revision, *args, **kwargs):
            saw_file_exists[(filename, revision)] = True
            return True

        diff = (
            b'diff --git a/README b/README\n'
            b'index d6613f5..5b50866 100644\n'
            b'--- README\n'
            b'+++ README\n'
            b'@ -1,1 +1,1 @@\n'
            b'-blah blah\n'
            b'+blah!\n'
        )
        parent_diff_1 = (
            b'diff --git a/README b/README\n'
            b'index d6613f4..5b50865 100644\n'
            b'--- README\n'
            b'+++ README\n'
            b'@ -1,1 +1,1 @@\n'
            b'-blah..\n'
            b'+blah blah\n'
        )
        parent_diff_2 = (
            b'diff --git a/UNUSED b/UNUSED\n'
            b'index 1234567..5b50866 100644\n'
            b'--- UNUSED\n'
            b'+++ UNUSED\n'
            b'@ -1,1 +1,1 @@\n'
            b'-foo\n'
            b'+bar\n'
        )
        parent_diff = parent_diff_1 + parent_diff_2

        diff_file = SimpleUploadedFile('diff', diff,
                                       content_type='text/x-patch')
        parent_diff_file = SimpleUploadedFile('parent_diff', parent_diff,
                                              content_type='text/x-patch')

        repository = self.create_repository(tool_name='Test')
        self.spy_on(repository.get_file_exists, call_fake=get_file_exists)

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

        self.assertTrue(('/README', 'd6613f4') in saw_file_exists)
        self.assertFalse(('/UNUSED', '1234567') in saw_file_exists)
        self.assertEqual(len(saw_file_exists), 1)

    def test_mercurial_parent_diff_base_rev(self):
        """Testing that the correct base revision is used for Mercurial diffs"""
        diff = (
            b'# Node ID a6fc203fee9091ff9739c9c00cd4a6694e023f48\n'
            b'# Parent  7c4735ef51a7c665b5654f1a111ae430ce84ebbd\n'
            b'diff --git a/doc/readme b/doc/readme\n'
            b'--- a/doc/readme\n'
            b'+++ b/doc/readme\n'
            b'@@ -1,3 +1,3 @@\n'
            b' Hello\n'
            b'-\n'
            b'+...\n'
            b' goodbye\n'
        )

        parent_diff = (
            b'# Node ID 7c4735ef51a7c665b5654f1a111ae430ce84ebbd\n'
            b'# Parent  661e5dd3c4938ecbe8f77e2fdfa905d70485f94c\n'
            b'diff --git a/doc/newfile b/doc/newfile\n'
            b'new file mode 100644\n'
            b'--- /dev/null\n'
            b'+++ b/doc/newfile\n'
            b'@@ -0,0 +1,1 @@\n'
            b'+Lorem ipsum\n'
        )

        try:
            import mercurial
        except ImportError:
            raise nose.SkipTest("Hg is not installed")

        diff_file = SimpleUploadedFile('diff', diff,
                                       content_type='text/x-patch')
        parent_diff_file = SimpleUploadedFile('parent_diff', parent_diff,
                                              content_type='text/x-patch')

        repository = Repository.objects.create(
            name='Test HG',
            path='scmtools/testdata/hg_repo',
            tool=Tool.objects.get(name='Mercurial'))

        form = UploadDiffForm(
            repository=repository,
            files={
                'path': diff_file,
                'parent_diff_path': parent_diff_file,
            })
        self.assertTrue(form.is_valid())

        diffset = form.create(diff_file, parent_diff_file)
        self.assertEqual(diffset.files.count(), 1)

        filediff = diffset.files.get()

        self.assertEqual(filediff.source_revision,
                         '661e5dd3c4938ecbe8f77e2fdfa905d70485f94c')


class ProcessorsTests(TestCase):
    """Unit tests for diff processors."""

    def test_filter_interdiff_opcodes(self):
        """Testing filter_interdiff_opcodes"""
        opcodes = [
            ('insert', 0, 0, 0, 1),
            ('equal', 0, 5, 1, 5),
            ('delete', 5, 10, 5, 5),
            ('equal', 10, 25, 5, 20),
            ('replace', 25, 26, 20, 26),
            ('equal', 26, 40, 26, 40),
            ('insert', 40, 40, 40, 45),
        ]

        # NOTE: Only the "@@" lines in the diff matter below for this
        #       processor, so the rest can be left out.
        orig_diff = '@@ -22,7 +22,7 @@\n'
        new_diff = (
            '@@ -2,11 +2,6 @@\n'
            '@@ -22,7 +22,7 @@\n'
        )

        new_opcodes = list(filter_interdiff_opcodes(opcodes, orig_diff,
                                                    new_diff))

        self.assertEqual(new_opcodes, [
            ('equal', 0, 0, 0, 1),
            ('equal', 0, 5, 1, 5),
            ('delete', 5, 10, 5, 5),
            ('equal', 10, 25, 5, 20),
            ('replace', 25, 26, 20, 26),
            ('equal', 26, 40, 26, 40),
            ('equal', 40, 40, 40, 45),
        ])

    def test_filter_interdiff_opcodes_with_inserts_right(self):
        """Testing filter_interdiff_opcodes with inserts on the right"""
        # These opcodes were taken from the r1-r2 interdiff at
        # http://reviews.reviewboard.org/r/4221/
        opcodes = [
            ('equal', 0, 141, 0, 141),
            ('replace', 141, 142, 141, 142),
            ('insert', 142, 142, 142, 144),
            ('equal', 142, 165, 144, 167),
            ('replace', 165, 166, 167, 168),
            ('insert', 166, 166, 168, 170),
            ('equal', 166, 190, 170, 194),
            ('insert', 190, 190, 194, 197),
            ('equal', 190, 232, 197, 239),
        ]

        # NOTE: Only the "@@" lines in the diff matter below for this
        #       processor, so the rest can be left out.
        orig_diff = '@@ -0,0 +1,232 @@\n'
        new_diff = '@@ -0,0 +1,239 @@\n'

        new_opcodes = list(filter_interdiff_opcodes(opcodes, orig_diff,
                                                    new_diff))

        self.assertEqual(new_opcodes, [
            ('equal', 0, 141, 0, 141),
            ('replace', 141, 142, 141, 142),
            ('insert', 142, 142, 142, 144),
            ('equal', 142, 165, 144, 167),
            ('replace', 165, 166, 167, 168),
            ('insert', 166, 166, 168, 170),
            ('equal', 166, 190, 170, 194),
            ('insert', 190, 190, 194, 197),
            ('equal', 190, 232, 197, 239),
        ])

    def test_filter_interdiff_opcodes_with_many_ignorable_ranges(self):
        """Testing filter_interdiff_opcodes with many ignorable ranges"""
        # These opcodes were taken from the r1-r2 interdiff at
        # http://reviews.reviewboard.org/r/4257/
        opcodes = [
            ('equal', 0, 631, 0, 631),
            ('replace', 631, 632, 631, 632),
            ('insert', 632, 632, 632, 633),
            ('equal', 632, 882, 633, 883),
        ]

        # NOTE: Only the "@@" lines in the diff matter below for this
        #       processor, so the rest can be left out.
        orig_diff = (
            '@@ -413,6 +413,8 @@\n'
            '@@ -422,9 +424,13 @@\n'
            '@@ -433,6 +439,8 @@\n'
            '@@ -442,6 +450,9 @@\n'
            '@@ -595,6 +605,205 @@\n'
            '@@ -636,6 +845,36 @@\n'
        )
        new_diff = (
            '@@ -413,6 +413,8 @@\n'
            '@@ -422,9 +424,13 @@\n'
            '@@ -433,6 +439,8 @@\n'
            '@@ -442,6 +450,8 @@\n'
            '@@ -595,6 +605,206 @@\n'
            '@@ -636,6 +846,36 @@\n'
        )

        new_opcodes = list(filter_interdiff_opcodes(opcodes, orig_diff,
                                                    new_diff))

        self.assertEqual(new_opcodes, [
            ('equal', 0, 631, 0, 631),
            ('replace', 631, 632, 631, 632),
            ('insert', 632, 632, 632, 633),
            ('equal', 632, 882, 633, 883),
        ])

    def test_merge_adjacent_chunks(self):
        """Testing merge_adjacent_chunks"""
        opcodes = [
            ('equal', 0, 0, 0, 1),
            ('equal', 0, 5, 1, 5),
            ('delete', 5, 10, 5, 5),
            ('equal', 10, 25, 5, 20),
            ('replace', 25, 26, 20, 26),
            ('equal', 26, 40, 26, 40),
            ('equal', 40, 40, 40, 45),
        ]

        new_opcodes = list(merge_adjacent_chunks(opcodes))

        self.assertEqual(new_opcodes, [
            ('equal', 0, 5, 0, 5),
            ('delete', 5, 10, 5, 5),
            ('equal', 10, 25, 5, 20),
            ('replace', 25, 26, 20, 26),
            ('equal', 26, 40, 26, 45),
        ])


class DiffChunkGeneratorTests(TestCase):
    """Unit tests for DiffChunkGenerator."""
    def test_get_line_changed_regions(self):
        """Testing DiffChunkGenerator._get_line_changed_regions"""
        def deep_equal(A, B):
            typea, typeb = type(A), type(B)
            self.assertEqual(typea, typeb)
            if typea is tuple or typea is list:
                for a, b in zip_longest(A, B):
                    deep_equal(a, b)
            else:
                self.assertEqual(A, B)

        filediff = FileDiff(source_file='foo', diffset=DiffSet())
        generator = DiffChunkGenerator(None, filediff)

        deep_equal(generator._get_line_changed_regions(None, None),
                   (None, None))

        old = 'submitter = models.ForeignKey(Person, verbose_name="Submitter")'
        new = 'submitter = models.ForeignKey(User, verbose_name="Submitter")'
        regions = generator._get_line_changed_regions(old, new)
        deep_equal(regions, ([(30, 36)], [(30, 34)]))

        old = '-from reviews.models import ReviewRequest, Person, Group'
        new = '+from .reviews.models import ReviewRequest, Group'
        regions = generator._get_line_changed_regions(old, new)
        deep_equal(regions, ([(0, 1), (6, 6), (43, 51)],
                             [(0, 1), (6, 7), (44, 44)]))

        old = 'abcdefghijklm'
        new = 'nopqrstuvwxyz'
        regions = generator._get_line_changed_regions(old, new)
        deep_equal(regions, (None, None))


class DiffRendererTests(SpyAgency, TestCase):
    """Unit tests for DiffRenderer."""
    def test_construction_with_invalid_chunks(self):
        """Testing DiffRenderer construction with invalid chunks"""
        diff_file = {
            'chunks': [{}]
        }

        self.assertRaises(
            UserVisibleError,
            lambda: DiffRenderer(diff_file, chunk_index=-1))
        self.assertRaises(
            UserVisibleError,
            lambda: DiffRenderer(diff_file, chunk_index=1))

    def test_construction_with_valid_chunks(self):
        """Testing DiffRenderer construction with valid chunks"""
        diff_file = {
            'chunks': [{}]
        }

        # Should not assert.
        renderer = DiffRenderer(diff_file, chunk_index=0)
        self.assertEqual(renderer.num_chunks, 1)
        self.assertEqual(renderer.chunk_index, 0)

    def test_render_to_response(self):
        """Testing DiffRenderer.render_to_response"""
        diff_file = {
            'chunks': [{}]
        }

        renderer = DiffRenderer(diff_file)
        self.spy_on(renderer.render_to_string, call_fake=lambda self: 'Foo')

        response = renderer.render_to_response()

        self.assertTrue(renderer.render_to_string.called)
        self.assertTrue(isinstance(response, HttpResponse))
        self.assertEqual(response.content, 'Foo')

    def test_render_to_string(self):
        """Testing DiffRenderer.render_to_string"""
        diff_file = {
            'chunks': [{}]
        }

        renderer = DiffRenderer(diff_file)
        self.spy_on(renderer.render_to_string_uncached,
                    call_fake=lambda self: 'Foo')
        self.spy_on(renderer.make_cache_key,
                    call_fake=lambda self: 'my-cache-key')
        self.spy_on(cache_memoize)

        response = renderer.render_to_response()

        self.assertEqual(response.content, 'Foo')
        self.assertTrue(renderer.render_to_string_uncached.called)
        self.assertTrue(renderer.make_cache_key.called)
        self.assertTrue(cache_memoize.spy.called)

    def test_render_to_string_uncached(self):
        """Testing DiffRenderer.render_to_string_uncached"""
        diff_file = {
            'chunks': [{}]
        }

        renderer = DiffRenderer(diff_file, lines_of_context=[5, 5])
        self.spy_on(renderer.render_to_string_uncached,
                    call_fake=lambda self: 'Foo')
        self.spy_on(renderer.make_cache_key,
                    call_fake=lambda self: 'my-cache-key')
        self.spy_on(cache_memoize)

        response = renderer.render_to_response()

        self.assertEqual(response.content, 'Foo')
        self.assertTrue(renderer.render_to_string_uncached.called)
        self.assertFalse(renderer.make_cache_key.called)
        self.assertFalse(cache_memoize.spy.called)

    def test_make_context_with_chunk_index(self):
        """Testing DiffRenderer.make_context with chunk_index"""
        diff_file = {
            'newfile': True,
            'interfilediff': None,
            'filediff': FileDiff(),
            'chunks': [
                {
                    'lines': [],
                    'meta': {},
                    'change': 'insert',
                },
                {
                    # This is not how lines really look, but it's fine for
                    # current usage tests.
                    'lines': range(10),
                    'meta': {},
                    'change': 'replace',
                },
                {
                    'lines': [],
                    'meta': {},
                    'change': 'delete',
                }
            ],
        }

        renderer = DiffRenderer(diff_file, chunk_index=1)
        context = renderer.make_context()

        self.assertEqual(context['standalone'], True)
        self.assertEqual(context['file'], diff_file)
        self.assertEqual(len(diff_file['chunks']), 1)

        chunk = diff_file['chunks'][0]
        self.assertEqual(chunk['change'], 'replace')
