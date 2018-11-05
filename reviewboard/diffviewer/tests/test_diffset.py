from __future__ import unicode_literals

from reviewboard.diffviewer.models import DiffSet, DiffSetHistory
from reviewboard.testing import TestCase


class DiffSetTests(TestCase):
    """Unit tests for reviewboard.diffviewer.models.diffset.DiffSet."""

    fixtures = ['test_scmtools']

    def test_update_revision_from_history_with_diffsets(self):
        """Testing DiffSet.update_revision_from_history with existing diffsets
        """
        repository = self.create_repository(tool_name='Test')
        diffset_history = DiffSetHistory.objects.create()
        diffset_history.diffsets.add(
            self.create_diffset(repository=repository))

        diffset = DiffSet()
        diffset.update_revision_from_history(diffset_history)

        self.assertEqual(diffset.revision, 2)

    def test_update_revision_from_history_without_diffsets(self):
        """Testing DiffSet.update_revision_from_history without existing
        diffsets
        """
        diffset_history = DiffSetHistory.objects.create()

        diffset = DiffSet()
        diffset.update_revision_from_history(diffset_history)

        self.assertEqual(diffset.revision, 1)

    def test_update_revision_from_history_with_revision_already_set(self):
        """Testing DiffSet.update_revision_from_history with revision
        already set
        """
        diffset_history = DiffSetHistory.objects.create()
        diffset = DiffSet(revision=1)

        with self.assertRaises(ValueError):
            diffset.update_revision_from_history(diffset_history)

    def test_per_commit_files_unpopulated(self):
        """Testing DiffSet.per_commit_files without pre-fetching files"""
        repository = self.create_repository()
        diffset = self.create_diffset(repository=repository)
        commit = self.create_diffcommit(diffset=diffset)

        expected = list(commit.files.all())

        self.create_filediff(diffset=diffset)

        diffset = DiffSet.objects.get(pk=diffset.pk)

        with self.assertNumQueries(1):
            result = diffset.per_commit_files

        self.assertEqual(result, expected)

        with self.assertNumQueries(0):
            result = diffset.per_commit_files

        self.assertEqual(result, expected)

    def test_per_commit_files_prefetch_files(self):
        """Testing DiffSet.per_commit_files with pre-fetching files"""
        repository = self.create_repository()
        diffset = self.create_diffset(repository=repository)
        commit = self.create_diffcommit(diffset=diffset)

        expected = list(commit.files.all())

        self.create_filediff(diffset=diffset)

        diffset = DiffSet.objects.prefetch_related('files').get(pk=diffset.pk)

        with self.assertNumQueries(0):
            result = diffset.per_commit_files

        self.assertEqual(result, expected)

    def test_cumulative_files_unpopulated(self):
        """Testing DiffSet.cumulative_files without pre-fetching files"""
        repository = self.create_repository()
        diffset = self.create_diffset(repository=repository)
        self.create_diffcommit(diffset=diffset)

        expected = [self.create_filediff(diffset=diffset)]

        diffset = DiffSet.objects.get(pk=diffset.pk)

        with self.assertNumQueries(1):
            result = diffset.cumulative_files

        self.assertEqual(result, expected)

        with self.assertNumQueries(0):
            result = diffset.cumulative_files

        self.assertEqual(result, expected)

    def test_cumulative_files_prefetch_files(self):
        """Testing DiffSet.cumulative_files with pre-fetching files"""
        repository = self.create_repository()
        diffset = self.create_diffset(repository=repository)
        self.create_diffcommit(diffset=diffset)

        expected = [self.create_filediff(diffset=diffset)]

        diffset = DiffSet.objects.prefetch_related('files').get(pk=diffset.pk)

        with self.assertNumQueries(0):
            result = diffset.cumulative_files

        self.assertEqual(result, expected)
