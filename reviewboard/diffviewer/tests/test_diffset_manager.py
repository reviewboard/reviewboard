from __future__ import unicode_literals

from kgb import SpyAgency

from reviewboard.diffviewer.models import DiffSet, DiffSetHistory, FileDiff
from reviewboard.diffviewer.parser import DiffParser
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
            repository=repository,
            diff_file_name='diff',
            diff_file_contents=self.DEFAULT_GIT_FILEDIFF_DATA_DIFF,
            basedir='/')

        self.assertEqual(diffset.files.count(), 1)

    def test_create_from_data_with_basedir_no_slash(self):
        """Testing DiffSetManager.create_from_data with basedir without leading
        slash
        """
        repository = self.create_repository(tool_name='Test')

        self.spy_on(repository.get_file_exists,
                    call_fake=lambda *args, **kwargs: True)

        diffset = DiffSet.objects.create_from_data(
            repository=repository,
            diff_file_name='diff',
            diff_file_contents=self.DEFAULT_GIT_FILEDIFF_DATA_DIFF,
            basedir='trunk/')

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
            repository=repository,
            diff_file_name='diff',
            diff_file_contents=self.DEFAULT_GIT_FILEDIFF_DATA_DIFF,
            basedir='/trunk/')

        self.assertEqual(diffset.files.count(), 1)

        filediff = diffset.files.all()[0]
        self.assertEqual(filediff.source_file, 'trunk/README')
        self.assertEqual(filediff.dest_file, 'trunk/README')

    def test_create_from_data_with_validate_only_true(self):
        """Testing DiffSetManager.create_from_data with validate_only=True"""
        repository = self.create_repository(tool_name='Test')

        self.spy_on(repository.get_file_exists,
                    call_fake=lambda *args, **kwargs: True)

        with self.assertNumQueries(0):
            diffset = DiffSet.objects.create_from_data(
                repository=repository,
                diff_file_name='diff',
                diff_file_contents=self.DEFAULT_GIT_FILEDIFF_DATA_DIFF,
                basedir='/',
                validate_only=True)

        self.assertIsNone(diffset)
        self.assertEqual(DiffSet.objects.count(), 0)
        self.assertEqual(FileDiff.objects.count(), 0)

    def test_create_empty(self):
        """Testing DiffSetManager.create_empty"""
        repository = self.create_repository(tool_name='Test')
        history = DiffSetHistory.objects.create()

        diffset = DiffSet.objects.create_empty(
            repository=repository,
            diffset_history=history)

        self.assertEqual(diffset.files.count(), 0)
        self.assertEqual(diffset.revision, 1)

    def test_create_empty_with_revision(self):
        """Testing DiffSetManager.create_empty with revision"""
        repository = self.create_repository(tool_name='Test')
        history = DiffSetHistory.objects.create()

        diffset = DiffSet.objects.create_empty(
            repository=repository,
            diffset_history=history,
            revision=10)

        self.assertEqual(diffset.files.count(), 0)
        self.assertEqual(diffset.history, history)
        self.assertEqual(diffset.revision, 10)

    def test_create_empty_without_history(self):
        """Testing DiffSetManager.create_empty without diffset_history"""
        repository = self.create_repository(tool_name='Test')

        diffset = DiffSet.objects.create_empty(
            repository=repository)

        self.assertEqual(diffset.files.count(), 0)
        self.assertIsNone(diffset.history)
        self.assertEqual(diffset.revision, 0)

    def test_create_from_data_custom_parser_extra_data(self):
        """Testing DiffSetManager.create_from_data with a custom diff parser
        that sets extra_data
        """
        repository = self.create_repository(tool_name='Test')

        class CustomParser(DiffParser):
            def parse_diff_header(self, linenum, info):
                info['extra_data'] = {'foo': True}

                return super(CustomParser, self).parse_diff_header(
                    linenum, info)

        self.spy_on(repository.get_file_exists,
                    call_fake=lambda *args, **kwargs: True)

        tool = repository.get_scmtool()

        self.spy_on(repository.get_scmtool,
                    call_fake=lambda repo: tool)
        self.spy_on(tool.get_parser,
                    call_fake=lambda repo, diff: CustomParser(diff))

        diffset = DiffSet.objects.create_from_data(
            repository=repository,
            diff_file_name='diff',
            diff_file_contents=self.DEFAULT_FILEDIFF_DATA_DIFF,
            basedir='/')

        self.assertEqual(diffset.files.count(), 1)

        filediff = diffset.files.all()[0]
        self.assertEqual(filediff.extra_data, {
            'is_symlink': False,
            'raw_delete_count': 1,
            'raw_insert_count': 1,
            'foo': True,
        })
