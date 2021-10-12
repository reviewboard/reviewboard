import kgb

from reviewboard.diffviewer.models import DiffSet, DiffSetHistory, FileDiff
from reviewboard.diffviewer.parser import DiffParser
from reviewboard.testing import TestCase


class DiffSetManagerTests(kgb.SpyAgency, TestCase):
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
            def parse(self):
                result = super(CustomParser, self).parse()

                self.parsed_diff.extra_data = {
                    'key1': 'value1',
                }

                self.parsed_diff_change.extra_data = {
                    'key2': 'value2',
                }

                return result

            def parse_diff_header(self, linenum, parsed_file):
                parsed_file.extra_data = {
                    'key3': 'value3',
                }

                return super(CustomParser, self).parse_diff_header(
                    linenum, parsed_file)

        self.spy_on(repository.get_file_exists,
                    op=kgb.SpyOpReturn(True))

        tool = repository.get_scmtool()

        self.spy_on(repository.get_scmtool,
                    op=kgb.SpyOpReturn(tool))
        self.spy_on(tool.get_parser,
                    call_fake=lambda repo, diff: CustomParser(diff))

        diffset = DiffSet.objects.create_from_data(
            repository=repository,
            diff_file_name='diff',
            diff_file_contents=self.DEFAULT_FILEDIFF_DATA_DIFF,
            basedir='/')

        # Test against what's in the database.
        diffset.refresh_from_db()

        self.assertEqual(diffset.extra_data, {
            'change_extra_data': {
                'key2': 'value2',
            },
            'key1': 'value1',
        })

        self.assertEqual(diffset.files.count(), 1)

        filediff = diffset.files.all()[0]
        self.assertEqual(filediff.extra_data, {
            'is_symlink': False,
            'key3': 'value3',
            'raw_delete_count': 1,
            'raw_insert_count': 1,
        })

        # Check the FileLookupContext passed to get_file_exists.
        self.assertSpyCallCount(repository.get_file_exists, 1)

        context = repository.get_file_exists.last_call.kwargs.get('context')
        self.assertIsNotNone(context)
        self.assertEqual(context.diff_extra_data, {
            'key1': 'value1',
        })
        self.assertEqual(context.commit_extra_data, {
            'key2': 'value2',
        })
        self.assertEqual(context.file_extra_data, {
            'key3': 'value3',
        })

    def test_create_from_data_custom_parser_extra_data_and_parent(self):
        """Testing DiffSetManager.create_from_data with a custom diff parser
        that sets extra_data and using parent diff
        """
        repository = self.create_repository(tool_name='Test')

        namespaces = ['main_', 'parent_']

        class CustomParser(DiffParser):
            def parse(self):
                self.namespace = namespaces.pop(0)

                result = super(CustomParser, self).parse()

                self.parsed_diff.extra_data = {
                    '%skey1' % self.namespace: 'value1',
                }

                self.parsed_diff_change.extra_data = {
                    '%skey2' % self.namespace: 'value2',
                }

                return result

            def parse_diff_header(self, linenum, parsed_file):
                parsed_file.extra_data = {
                    '%skey3' % self.namespace: 'value3',
                }

                return super(CustomParser, self).parse_diff_header(
                    linenum, parsed_file)

        self.spy_on(repository.get_file_exists,
                    op=kgb.SpyOpReturn(True))

        tool = repository.get_scmtool()

        self.spy_on(repository.get_scmtool,
                    op=kgb.SpyOpReturn(tool))
        self.spy_on(tool.get_parser,
                    call_fake=lambda repo, diff: CustomParser(diff))

        diffset = DiffSet.objects.create_from_data(
            repository=repository,
            diff_file_name='diff',
            diff_file_contents=self.DEFAULT_FILEDIFF_DATA_DIFF,
            parent_diff_file_name='parent-diff',
            parent_diff_file_contents=self.DEFAULT_FILEDIFF_DATA_DIFF,
            basedir='/')

        # Test against what's in the database.
        diffset.refresh_from_db()

        self.assertEqual(diffset.extra_data, {
            'change_extra_data': {
                'main_key2': 'value2',
            },
            'main_key1': 'value1',
            'parent_extra_data': {
                'change_extra_data': {
                    'parent_key2': 'value2',
                },
                'parent_key1': 'value1',
            },
        })

        self.assertEqual(diffset.files.count(), 1)

        filediff = diffset.files.all()[0]
        self.assertEqual(filediff.extra_data, {
            '__parent_diff_empty': False,
            'is_symlink': False,
            'main_key3': 'value3',
            'parent_extra_data': {
                'parent_key3': 'value3',
            },
            'parent_source_filename': '/README',
            'parent_source_revision': 'revision 123',
            'raw_delete_count': 1,
            'raw_insert_count': 1,
        })

        # Check the FileLookupContext passed to get_file_exists.
        self.assertSpyCallCount(repository.get_file_exists, 1)

        context = repository.get_file_exists.last_call.kwargs.get('context')
        self.assertIsNotNone(context)
        self.assertEqual(context.diff_extra_data, {
            'parent_key1': 'value1',
        })
        self.assertEqual(context.commit_extra_data, {
            'parent_key2': 'value2',
        })
        self.assertEqual(context.file_extra_data, {
            'parent_key3': 'value3',
        })
