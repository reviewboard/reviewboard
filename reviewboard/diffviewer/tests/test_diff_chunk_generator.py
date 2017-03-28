from __future__ import unicode_literals

from reviewboard.diffviewer.chunk_generator import DiffChunkGenerator
from reviewboard.scmtools.core import PRE_CREATION
from reviewboard.testing import TestCase


class DiffChunkGeneratorTests(TestCase):
    """Unit tests for DiffChunkGenerator."""

    fixtures = ['test_scmtools']

    def setUp(self):
        self.repository = self.create_repository()
        self.diffset = self.create_diffset(repository=self.repository)
        self.filediff = self.create_filediff(diffset=self.diffset)
        self.generator = DiffChunkGenerator(None, self.filediff)

    def test_get_chunks_with_empty_added_file(self):
        """Testing DiffChunkGenerator.get_chunks with empty added file"""
        self.filediff.source_revision = PRE_CREATION
        self.filediff.extra_data.update({
            'raw_insert_count': 0,
            'raw_delete_count': 0,
        })

        self.assertEqual(len(list(self.generator.get_chunks())), 0)

    def test_get_chunks_with_replace_in_added_file_with_parent_diff(self):
        """Testing DiffChunkGenerator.get_chunks with replace chunks in
        added file with parent diff
        """
        self.filediff.diff = (
            b'--- README\n'
            b'+++ README\n'
            b'@@ -1,1 +1,1 @@\n'
            b'-line\n'
            b'+line.\n'
        )
        self.filediff.parent_diff = (
            b'--- README\n'
            b'+++ README\n'
            b'@@ -0,0 +1,1 @@\n'
            b'+line\n'
        )
        self.filediff.source_revision = PRE_CREATION
        self.filediff.extra_data.update({
            'raw_insert_count': 1,
            'raw_delete_count': 1,
            'insert_count': 0,
            'delete_count': 0,
        })

        self.assertEqual(len(list(self.generator.get_chunks())), 1)

    def test_line_counts_unmodified_by_interdiff(self):
        """Testing that line counts are not modified by interdiffs where the
        changes are reverted
        """
        self.filediff.source_revision = PRE_CREATION
        self.filediff.diff = (
            b'--- README\n'
            b'+++ README\n'
            b'@@ -0,0 +1,1 @@\n'
            b'+line\n'
        )

        # We have to consume everything from the get_chunks generator in order
        # for the line counts to be set on the FileDiff.
        self.assertEqual(len(list(self.generator.get_chunks())), 1)

        line_counts = self.filediff.get_line_counts()

        # Simulate an interdiff where the changes are reverted.
        interdiff_generator = DiffChunkGenerator(request=None,
                                                 filediff=self.filediff,
                                                 interfilediff=None,
                                                 force_interdiff=True)

        # Again, just consuming the generator.
        self.assertEqual(len(list(interdiff_generator.get_chunks())), 1)

        self.assertEqual(line_counts, self.filediff.get_line_counts())
