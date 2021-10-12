"""Tests for reviewboard.diffviewer.managers.DiffCommitManager."""

import kgb
from dateutil.parser import parse as parse_date
from django.db import IntegrityError

from reviewboard.diffviewer.models import DiffCommit, DiffSet
from reviewboard.diffviewer.parser import DiffParser
from reviewboard.testing.testcase import TestCase


class DiffCommitManagerTests(kgb.SpyAgency, TestCase):
    """Unit tests for DiffCommitManager."""

    fixtures = ['test_scmtools']

    commit_test_diff = (
        b'diff --git a/README b/README\n'
        b'index d6613f5..5b50866 100644\n'
        b'--- README\n'
        b'+++ README\n'
        b'@ -1,1 +1,1 @@\n'
        b'-blah..\n'
        b'+blah blah\n'
    )

    def test_create_from_data(self):
        """Testing DiffCommitManager.create_from_data"""
        repository = self.create_repository(tool_name='Test')
        self.spy_on(repository.get_file_exists,
                    op=kgb.SpyOpReturn(True))

        diffset = DiffSet.objects.create_empty(
            repository=repository,
            basedir='',
            revision=1)

        raw_date = '2000-01-01 00:00:00-0600'
        parsed_date = parse_date(raw_date)
        commit = DiffCommit.objects.create_from_data(
            repository=repository,
            diff_file_name='diff',
            diff_file_contents=self.commit_test_diff,
            parent_diff_file_name=None,
            parent_diff_file_contents=b'',
            request=None,
            commit_id='r1',
            parent_id='r0',
            author_name='Author',
            author_email='author@example.com',
            author_date=parsed_date,
            committer_name='Committer',
            committer_email='committer@example.com',
            committer_date=parsed_date,
            commit_message='Description',
            diffset=diffset,
            validation_info={})

        self.assertEqual(commit.files.count(), 1)
        self.assertEqual(diffset.files.count(), commit.files.count())
        self.assertEqual(diffset.commit_count, 1)

        # We have to compare regular equality and equality after applying
        # ``strftime`` because two datetimes with different timezone info
        # may be equal
        self.assertEqual(commit.author_date, parsed_date)
        self.assertEqual(commit.committer_date, parsed_date)
        self.assertEqual(commit.committer_date_utc, parsed_date)
        self.assertEqual(commit.committer_date_offset, -21600.0)

        self.assertEqual(
            commit.author_date.strftime(DiffCommit.ISO_DATE_FORMAT),
            raw_date)

        self.assertEqual(
            commit.committer_date.strftime(DiffCommit.ISO_DATE_FORMAT),
            raw_date)

    def test_create_from_data_with_author_date_none(self):
        """Testing DiffCommitManager.create_from_data with author_date=None"""
        # author_date is a property that sets a couple of fields based on
        # the provided date. If this crashes (which was an issue initially with
        # the implementation when passing in None), construction will fail
        # with:
        #
        #     TypeError: 'author_date' is an invalid keyword argument for this
        #     function
        #
        # Instead, we set to None and allow Django to raise a standard
        # IntegrityError on model save.
        repository = self.create_repository(tool_name='Test')
        self.spy_on(repository.get_file_exists,
                    op=kgb.SpyOpReturn(True))

        diffset = DiffSet.objects.create_empty(
            repository=repository,
            basedir='',
            revision=1)

        with self.assertRaises(IntegrityError):
            commit = DiffCommit.objects.create_from_data(
                repository=repository,
                diff_file_name='diff',
                diff_file_contents=self.commit_test_diff,
                parent_diff_file_name=None,
                parent_diff_file_contents=b'',
                request=None,
                commit_id='r1',
                parent_id='r0',
                author_name='Author',
                author_email='author@example.com',
                author_date=None,
                committer_name='Committer',
                committer_email='committer@example.com',
                committer_date=parse_date('2000-01-01 00:00:00-0600'),
                commit_message='Description',
                diffset=diffset,
                validation_info={})

        self.assertEqual(diffset.commit_count, 0)

    def test_create_from_data_with_committer_date_none(self):
        """Testing DiffCommitManager.create_from_data with committer_date=None
        """
        # committer_date is a property that sets a couple of fields based on
        # the provided date. If this crashes (which was an issue initially with
        # the implementation when passing in None), construction will fail
        # with:
        #
        #     TypeError: 'committer_date' is an invalid keyword argument for
        #     this function
        repository = self.create_repository(tool_name='Test')
        self.spy_on(repository.get_file_exists,
                    op=kgb.SpyOpReturn(True))

        diffset = DiffSet.objects.create_empty(
            repository=repository,
            basedir='',
            revision=1)

        commit = DiffCommit.objects.create_from_data(
            repository=repository,
            diff_file_name='diff',
            diff_file_contents=self.commit_test_diff,
            parent_diff_file_name=None,
            parent_diff_file_contents=b'',
            request=None,
            commit_id='r1',
            parent_id='r0',
            author_name='Author',
            author_email='author@example.com',
            author_date=parse_date('2000-01-01 00:00:00-0600'),
            committer_name='Committer',
            committer_email='committer@example.com',
            committer_date=None,
            commit_message='Description',
            diffset=diffset,
            validation_info={})

        self.assertEqual(commit.files.count(), 1)
        self.assertEqual(diffset.files.count(), commit.files.count())
        self.assertEqual(diffset.commit_count, 1)

        self.assertIsNone(commit.committer_date)
        self.assertIsNone(commit.committer_date_utc)
        self.assertIsNone(commit.committer_date_offset)

    def test_create_from_data_custom_parser_extra_data(self):
        """Testing DiffCommitManager.create_from_data with a custom diff parser
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

        diffset = DiffSet.objects.create_empty(
            repository=repository,
            basedir='',
            revision=1)

        diffcommit = DiffCommit.objects.create_from_data(
            repository=repository,
            diff_file_name='diff',
            diff_file_contents=self.DEFAULT_FILEDIFF_DATA_DIFF,
            parent_diff_file_name=None,
            parent_diff_file_contents=b'',
            request=None,
            commit_id='r1',
            parent_id='r0',
            author_name='Author',
            author_email='author@example.com',
            author_date=parse_date('2000-01-01 00:00:00-0600'),
            committer_name='Committer',
            committer_email='committer@example.com',
            committer_date=None,
            commit_message='Description',
            diffset=diffset,
            validation_info={})

        # Test against what's in the database.
        diffset.refresh_from_db()
        diffcommit.refresh_from_db()

        self.assertEqual(diffset.extra_data, {
            'key1': 'value1',
        })

        self.assertEqual(diffcommit.extra_data, {
            'key2': 'value2',
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
