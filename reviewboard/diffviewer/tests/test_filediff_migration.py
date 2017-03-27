from __future__ import unicode_literals

from reviewboard.diffviewer.models import DiffSet, FileDiff
from reviewboard.testing import TestCase


class FileDiffMigrationTests(TestCase):
    """Unit tests for FileDiff migration."""

    fixtures = ['test_scmtools']

    def setUp(self):
        super(FileDiffMigrationTests, self).setUp()

        self.parent_diff = (
            b'diff --git a/README b/README\n'
            b'index 94bdd3e..3d2b777 100644\n'
            b'--- README\n'
            b'+++ README\n'
            b'@@ -2 +2 @@\n'
            b'-blah..\n'
            b'+blah blah\n'
        )

        repository = self.create_repository(tool_name='Test')
        diffset = DiffSet.objects.create(name='test',
                                         revision=1,
                                         repository=repository)
        self.filediff = FileDiff(source_file='README',
                                 dest_file='README',
                                 diffset=diffset,
                                 diff64='',
                                 parent_diff64=b'')

    def test_migration_by_diff(self):
        """Testing FileDiffData migration accessing FileDiff.diff"""
        self.filediff.diff64 = self.DEFAULT_GIT_FILEDIFF_DATA

        self.assertIsNone(self.filediff.diff_hash)
        self.assertIsNone(self.filediff.parent_diff_hash)

        # This should prompt the migration.
        diff = self.filediff.diff

        self.assertIsNone(self.filediff.parent_diff_hash)
        self.assertIsNotNone(self.filediff.diff_hash)

        self.assertEqual(diff, self.DEFAULT_GIT_FILEDIFF_DATA)
        self.assertEqual(self.filediff.diff64, b'')
        self.assertEqual(self.filediff.diff_hash.binary,
                         self.DEFAULT_GIT_FILEDIFF_DATA)
        self.assertEqual(self.filediff.diff, diff)
        self.assertIsNone(self.filediff.parent_diff)
        self.assertIsNone(self.filediff.parent_diff_hash)

    def test_migration_by_parent_diff(self):
        """Testing FileDiffData migration accessing FileDiff.parent_diff"""
        self.filediff.diff64 = self.DEFAULT_GIT_FILEDIFF_DATA
        self.filediff.parent_diff64 = self.parent_diff

        self.assertIsNone(self.filediff.parent_diff_hash)

        # This should prompt the migration.
        parent_diff = self.filediff.parent_diff

        self.assertIsNotNone(self.filediff.parent_diff_hash)

        self.assertEqual(parent_diff, self.parent_diff)
        self.assertEqual(self.filediff.parent_diff64, b'')
        self.assertEqual(self.filediff.parent_diff_hash.binary,
                         self.parent_diff)
        self.assertEqual(self.filediff.parent_diff, self.parent_diff)

    def test_migration_by_delete_count(self):
        """Testing FileDiffData migration accessing FileDiff.delete_count"""
        self.filediff.diff64 = self.DEFAULT_GIT_FILEDIFF_DATA

        self.assertIsNone(self.filediff.diff_hash)

        # This should prompt the migration.
        counts = self.filediff.get_line_counts()

        self.assertIsNotNone(self.filediff.diff_hash)
        self.assertEqual(counts['raw_delete_count'], 1)
        self.assertEqual(self.filediff.diff_hash.delete_count, 1)

    def test_migration_by_insert_count(self):
        """Testing FileDiffData migration accessing FileDiff.insert_count"""
        self.filediff.diff64 = self.DEFAULT_GIT_FILEDIFF_DATA

        self.assertIsNone(self.filediff.diff_hash)

        # This should prompt the migration.
        counts = self.filediff.get_line_counts()

        self.assertIsNotNone(self.filediff.diff_hash)
        self.assertEqual(counts['raw_insert_count'], 1)
        self.assertEqual(self.filediff.diff_hash.insert_count, 1)

    def test_migration_by_set_line_counts(self):
        """Testing FileDiffData migration calling FileDiff.set_line_counts"""
        self.filediff.diff64 = self.DEFAULT_GIT_FILEDIFF_DATA

        self.assertIsNone(self.filediff.diff_hash)

        # This should prompt the migration, but with our line counts.
        self.filediff.set_line_counts(raw_insert_count=10,
                                      raw_delete_count=20)

        self.assertIsNotNone(self.filediff.diff_hash)

        counts = self.filediff.get_line_counts()
        self.assertEqual(counts['raw_insert_count'], 10)
        self.assertEqual(counts['raw_delete_count'], 20)
        self.assertEqual(self.filediff.diff_hash.insert_count, 10)
        self.assertEqual(self.filediff.diff_hash.delete_count, 20)
