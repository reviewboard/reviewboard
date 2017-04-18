from __future__ import unicode_literals

from kgb import SpyAgency

from reviewboard.diffviewer.models import DiffSet, FileDiff
from reviewboard.testing import TestCase


class DiffSetManagerTests(SpyAgency, TestCase):
    """Unit tests for DiffSetManager."""

    fixtures = ['test_scmtools']

    def test_create_from_data(self):
        """Testing DiffSetManager.create_from_data"""
        repository = self.create_repository(tool_name='Test')

        self.spy_on(repository.get_file_exists,
                    call_fake=lambda *args, **kwargs: True)

        diffset = DiffSet.objects.create_from_data(
            repository, 'diff', self.DEFAULT_GIT_FILEDIFF_DATA, None, None,
            None, '/', None)

        self.assertEqual(diffset.files.count(), 1)

    def test_create_from_data_with_basedir_no_slash(self):
        """Testing DiffSetManager.create_from_data with basedir without leading
        slash
        """
        repository = self.create_repository(tool_name='Test')

        self.spy_on(repository.get_file_exists,
                    call_fake=lambda *args, **kwargs: True)

        diffset = DiffSet.objects.create_from_data(
            repository, 'diff', self.DEFAULT_GIT_FILEDIFF_DATA, None, None,
            None, 'trunk/', None)

        self.assertEqual(diffset.files.count(), 1)

        filediff = diffset.files.all()[0]
        self.assertEqual(filediff.source_file, 'trunk/README')
        self.assertEqual(filediff.dest_file, 'trunk/README')

    def test_create_from_data_with_basedir_slash(self):
        """Testing DiffSetManager.create_from_data with basedir with leading
        slash
        """
        repository = self.create_repository(tool_name='Test')

        self.spy_on(repository.get_file_exists,
                    call_fake=lambda *args, **kwargs: True)

        diffset = DiffSet.objects.create_from_data(
            repository, 'diff', self.DEFAULT_GIT_FILEDIFF_DATA, None, None,
            None, '/trunk/', None)

        self.assertEqual(diffset.files.count(), 1)

        filediff = diffset.files.all()[0]
        self.assertEqual(filediff.source_file, 'trunk/README')
        self.assertEqual(filediff.dest_file, 'trunk/README')

    def test_create_from_data_with_save_false(self):
        """Testing DiffSetManager.create_from_data with save=False"""
        repository = self.create_repository(tool_name='Test')

        self.spy_on(repository.get_file_exists,
                    call_fake=lambda *args, **kwargs: True)

        with self.assertNumQueries(0):
            DiffSet.objects.create_from_data(
                repository, 'diff', self.DEFAULT_GIT_FILEDIFF_DATA, None,
                None, None, '/', None,
                save=False)

        self.assertEqual(DiffSet.objects.count(), 0)
        self.assertEqual(FileDiff.objects.count(), 0)
