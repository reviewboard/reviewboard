from __future__ import unicode_literals

from reviewboard.diffviewer.models import DiffSet, FileDiff
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

        repository = self.create_repository(tool_name='Test')
        diffset = DiffSet.objects.create(name='test',
                                         revision=1,
                                         repository=repository)
        self.filediff = FileDiff(source_file='README',
                                 dest_file='README',
                                 diffset=diffset,
                                 diff64=diff,
                                 parent_diff64='')

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
        self.assertEqual(filediff.source_file, long_filename)

    def test_diff_hashes(self):
        """Testing that uploading two of the same diff will result in only
        one database entry
        """
        repository = self.create_repository()
        diffset = DiffSet.objects.create(name='test',
                                         revision=1,
                                         repository=repository)

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

        filediff1 = FileDiff.objects.create(diff=data, diffset=diffset)
        filediff2 = FileDiff.objects.create(diff=data, diffset=diffset)

        self.assertEqual(filediff1.diff_hash, filediff2.diff_hash)
