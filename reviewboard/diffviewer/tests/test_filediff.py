"""Unit tests for reviewboard.diffviewer.models.filediff."""

from __future__ import unicode_literals

from itertools import chain

from django.utils import six

from reviewboard.diffviewer.models import DiffSet, FileDiff
from reviewboard.diffviewer.tests.test_diffutils import \
    BaseFileDiffAncestorTests
from reviewboard.testing import TestCase


class FileDiffTests(TestCase):
    """Unit tests for FileDiff."""

    fixtures = ['test_scmtools']

    def setUp(self):
        super(FileDiffTests, self).setUp()

        diff = (
            b'diff --git a/README b/README\n'
            b'index 3d2b777..48272a3 100644\n'
            b'--- README\n'
            b'+++ README\n'
            b'@@ -2 +2,2 @@\n'
            b'-blah blah\n'
            b'+blah!\n'
            b'+blah!!\n'
        )

        self.repository = self.create_repository(tool_name='Test')
        self.diffset = DiffSet.objects.create(name='test',
                                              revision=1,
                                              repository=self.repository)
        self.filediff = FileDiff(source_file='README',
                                 dest_file='README',
                                 diffset=self.diffset,
                                 diff64=diff,
                                 parent_diff64=b'')

    def test_get_line_counts_with_defaults(self):
        """Testing FileDiff.get_line_counts with default values"""
        counts = self.filediff.get_line_counts()

        self.assertIn('raw_insert_count', counts)
        self.assertIn('raw_delete_count', counts)
        self.assertIn('insert_count', counts)
        self.assertIn('delete_count', counts)
        self.assertIn('replace_count', counts)
        self.assertIn('equal_count', counts)
        self.assertIn('total_line_count', counts)
        self.assertEqual(counts['raw_insert_count'], 2)
        self.assertEqual(counts['raw_delete_count'], 1)
        self.assertEqual(counts['insert_count'], 2)
        self.assertEqual(counts['delete_count'], 1)
        self.assertIsNone(counts['replace_count'])
        self.assertIsNone(counts['equal_count'])
        self.assertIsNone(counts['total_line_count'])

        diff_hash = self.filediff.diff_hash
        self.assertEqual(diff_hash.insert_count, 2)
        self.assertEqual(diff_hash.delete_count, 1)

    def test_set_line_counts(self):
        """Testing FileDiff.set_line_counts"""
        self.filediff.set_line_counts(
            raw_insert_count=1,
            raw_delete_count=2,
            insert_count=3,
            delete_count=4,
            replace_count=5,
            equal_count=6,
            total_line_count=7)

        counts = self.filediff.get_line_counts()
        self.assertEqual(counts['raw_insert_count'], 1)
        self.assertEqual(counts['raw_delete_count'], 2)
        self.assertEqual(counts['insert_count'], 3)
        self.assertEqual(counts['delete_count'], 4)
        self.assertEqual(counts['replace_count'], 5)
        self.assertEqual(counts['equal_count'], 6)
        self.assertEqual(counts['total_line_count'], 7)

        diff_hash = self.filediff.diff_hash
        self.assertEqual(diff_hash.insert_count, 1)
        self.assertEqual(diff_hash.delete_count, 2)

    def test_long_filenames(self):
        """Testing FileDiff with long filenames (1024 characters)"""
        long_filename = 'x' * 1024

        filediff = FileDiff.objects.create(source_file=long_filename,
                                           dest_file='foo',
                                           diffset=self.diffset)
        self.assertEqual(filediff.source_file, long_filename)

    def test_diff_hashes(self):
        """Testing FileDiff with multiple entries and same diff data
        deduplicates data
        """
        data = (
            b'diff -rcN orig_src/foo.c new_src/foo.c\n'
            b'*** orig_src/foo.c\t2007-01-24 02:11:31.000000000 -0800\n'
            b'--- new_src/foo.c\t2007-01-24 02:14:42.000000000 -0800\n'
            b'***************\n'
            b'*** 1,5 ****\n'
            b'  int\n'
            b'  main()\n'
            b'  {\n'
            b'! \tprintf("foo\n");\n'
            b'  }\n'
            b'--- 1,8 ----\n'
            b'+ #include <stdio.h>\n'
            b'+ \n'
            b'  int\n'
            b'  main()\n'
            b'  {\n'
            b'! \tprintf("foo bar\n");\n'
            b'! \treturn 0;\n'
            b'  }\n')

        filediff1 = FileDiff.objects.create(diff=data, diffset=self.diffset)
        filediff2 = FileDiff.objects.create(diff=data, diffset=self.diffset)

        self.assertEqual(filediff1.diff_hash, filediff2.diff_hash)

    def test_get_base_filediff(self):
        """Testing FileDiff.get_base_filediff"""
        commit1 = self.create_diffcommit(
            diffset=self.diffset,
            commit_id='r1',
            parent_id='r0',
            diff_contents=(
                b'diff --git a/ABC b/ABC\n'
                b'index 94bdd3e..197009f 100644\n'
                b'--- ABC\n'
                b'+++ ABC\n'
                b'@@ -1,1 +1,1 @@\n'
                b'-line!\n'
                b'+line..\n'
            ))
        commit2 = self.create_diffcommit(
            diffset=self.diffset,
            commit_id='r2',
            parent_id='r1',
            diff_contents=(
                b'diff --git a/README b/README\n'
                b'index 94bdd3e..197009f 100644\n'
                b'--- README\n'
                b'+++ README\n'
                b'@@ -1,1 +1,1 @@\n'
                b'-Hello, world!\n'
                b'+Hi, world!\n'
            ))
        commit3 = self.create_diffcommit(
            diffset=self.diffset,
            commit_id='r3',
            parent_id='r2',
            diff_contents=(
                b'diff --git a/FOO b/FOO\n'
                b'index 84bda3e..b975034 100644\n'
                b'--- FOO\n'
                b'+++ FOO\n'
                b'@@ -1,1 +0,0 @@\n'
                b'-Some line\n'
            ))
        commit4 = self.create_diffcommit(
            diffset=self.diffset,
            commit_id='r4',
            parent_id='r3',
            diff_contents=(
                b'diff --git a/README b/README\n'
                b'index 197009f..87abad9 100644\n'
                b'--- README\n'
                b'+++ README\n'
                b'@@ -1,1 +1,1 @@\n'
                b'-Hi, world!\n'
                b'+Yo, world.\n'
            ))

        self.diffset.finalize_commit_series(
            cumulative_diff=(
                b'diff --git a/ABC b/ABC\n'
                b'index 94bdd3e..197009f 100644\n'
                b'--- ABC\n'
                b'+++ ABC\n'
                b'@@ -1,1 +1,1 @@\n'
                b'-line!\n'
                b'+line..\n'
                b'diff --git a/FOO b/FOO\n'
                b'index 84bda3e..b975034 100644\n'
                b'--- FOO\n'
                b'+++ FOO\n'
                b'@@ -1,1 +0,0 @@\n'
                b'-Some line\n'
                b'diff --git a/README b/README\n'
                b'index 94bdd3e..87abad9 100644\n'
                b'--- README\n'
                b'+++ README\n'
                b'@@ -1,1 +1,1 @@\n'
                b'-Hello, world!\n'
                b'+Yo, world.\n'
            ),
            validation_info=None,
            validate=False,
            save=True)

        filediff1 = commit1.files.get()
        filediff2 = commit2.files.get()
        filediff3 = commit3.files.get()
        filediff4 = commit4.files.get()

        for commit in (commit1, commit2, commit3, commit4):
            self.assertIsNone(filediff1.get_base_filediff(base_commit=commit))
            self.assertIsNone(filediff2.get_base_filediff(base_commit=commit))
            self.assertIsNone(filediff3.get_base_filediff(base_commit=commit))

        self.assertIsNone(filediff4.get_base_filediff(base_commit=commit1))
        self.assertEqual(filediff4.get_base_filediff(base_commit=commit2),
                         filediff2)
        self.assertEqual(filediff4.get_base_filediff(base_commit=commit3),
                         filediff2)
        self.assertEqual(filediff4.get_base_filediff(base_commit=commit4),
                         filediff2)

    def test_get_base_filediff_without_commit(self):
        """Testing FileDiff.get_base_filediff without associated commit"""
        filediff = self.create_filediff(self.diffset)

        self.assertIsNone(filediff.get_base_filediff(base_commit=None))


class FileDiffAncestorTests(BaseFileDiffAncestorTests):
    """Unit tests for FileDiff.get_ancestors"""

    def setUp(self):
        super(FileDiffAncestorTests, self).setUp()

        self.set_up_filediffs()

    def test_get_ancestors_minimal(self):
        """Testing FileDiff.get_ancestors with minimal=True"""
        ancestors = {}

        with self.assertNumQueries(9):
            for filediff in self.filediffs:
                ancestors[filediff] = filediff.get_ancestors(
                    minimal=True,
                    filediffs=self.filediffs)

        self._check_ancestors(ancestors, minimal=True)

    def test_get_ancestors_full(self):
        """Testing FileDiff.get_ancestors with minimal=False"""
        ancestors = {}

        with self.assertNumQueries(len(self.filediffs)):
            for filediff in self.filediffs:
                ancestors[filediff] = filediff.get_ancestors(
                    minimal=False,
                    filediffs=self.filediffs)

        self._check_ancestors(ancestors, minimal=False)

    def test_get_ancestors_cached(self):
        """Testing FileDiff.get_ancestors with cached results"""
        ancestors = {}

        for filediff in self.filediffs:
            filediff.get_ancestors(minimal=True, filediffs=self.filediffs)

        for filediff in self.filediffs:
            with self.assertNumQueries(0):
                ancestors[filediff] = filediff.get_ancestors(
                    minimal=True,
                    filediffs=self.filediffs)

        self._check_ancestors(ancestors, minimal=True)

    def test_get_ancestors_no_update(self):
        """Testing FileDiff.get_ancestors without caching"""
        ancestors = {}

        for filediff in self.filediffs:
            with self.assertNumQueries(0):
                ancestors[filediff] = filediff.get_ancestors(
                    minimal=True,
                    filediffs=self.filediffs,
                    update=False)

        self._check_ancestors(ancestors, minimal=True)

    def test_get_ancestors_no_filediffs(self):
        """Testing FileDiff.get_ancestors when no FileDiffs are provided"""
        ancestors = {}

        with self.assertNumQueries(2 * len(self.filediffs)):
            for filediff in self.filediffs:
                ancestors[filediff] = filediff.get_ancestors(minimal=True)

        self._check_ancestors(ancestors, minimal=True)

    def test_get_ancestors_cached_no_filediffs(self):
        """Testing FileDiff.get_ancestors with cached results when no
        FileDiffs are provided
        """
        ancestors = {}

        for filediff in self.filediffs:
            filediff.get_ancestors(minimal=True,
                                   filediffs=self.filediffs)

        with self.assertNumQueries(5):
            for filediff in self.filediffs:
                ancestors[filediff] = filediff.get_ancestors(minimal=True)

        self._check_ancestors(ancestors, minimal=True)

    def _check_ancestors(self, all_ancestors, minimal):
        paths = {
            (1, 'foo', 'PRE-CREATION', 'foo', 'e69de29'): ([], []),
            (1, 'bar', '5716ca5', 'bar', '8e739cc'): ([], []),
            (2, 'foo', 'e69de29', 'foo', '257cc56'): (
                [],
                [
                    (1, 'foo', 'PRE-CREATION', 'foo', 'e69de29'),
                ],
            ),
            (2, 'bar', '8e739cc', 'bar', '0000000'): (
                [],
                [
                    (1, 'bar', '5716ca5', 'bar', '8e739cc'),
                ],
            ),
            (2, 'baz', '7601807', 'baz', '280beb2'): ([], []),
            (3, 'foo', '257cc56', 'qux', '03b37a0'): (
                [],
                [
                    (1, 'foo', 'PRE-CREATION', 'foo', 'e69de29'),
                    (2, 'foo', 'e69de29', 'foo', '257cc56'),
                ],
            ),
            (3, 'bar', 'PRE-CREATION', 'bar', '5716ca5'): (
                [
                    (1, 'bar', '5716ca5', 'bar', '8e739cc'),
                    (2, 'bar', '8e739cc', 'bar', '0000000'),
                ],
                [],
            ),
            (3, 'corge', 'e69de29', 'corge', 'f248ba3'): ([], []),
            (4, 'bar', '5716ca5', 'quux', 'e69de29'): (
                [
                    (1, 'bar', '5716ca5', 'bar', '8e739cc'),
                    (2, 'bar', '8e739cc', 'bar', '0000000'),
                ],
                [
                    (3, 'bar', 'PRE-CREATION', 'bar', '5716ca5'),
                ],
            ),
        }

        by_details = self.get_filediffs_by_details()

        for filediff, ancestors in six.iteritems(all_ancestors):
            rest_ids, minimal_ids = paths[(
                filediff.commit_id,
                filediff.source_file,
                filediff.source_revision,
                filediff.dest_file,
                filediff.dest_detail,
            )]

            if minimal:
                ids = minimal_ids
            else:
                ids = chain(rest_ids, minimal_ids)

            expected_ancestors = [
                by_details[details] for details in ids
            ]

            self.assertEqual(ancestors, expected_ancestors)
