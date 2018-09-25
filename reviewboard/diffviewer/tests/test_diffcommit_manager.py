"""Tests for reviewboard.diffviewer.managers.DiffCommitManager."""

from __future__ import unicode_literals

from dateutil.parser import parse as parse_date
from kgb import SpyAgency

from reviewboard.diffviewer.models import DiffCommit, DiffSet
from reviewboard.testing.testcase import TestCase


class DiffCommitManagerTests(SpyAgency, TestCase):
    """Unit tests for DiffCommitManager."""

    fixtures = ['test_scmtools']

    def test_create_from_data(self):
        """Testing DiffCommitManager.create_from_data"""
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

        diffset = DiffSet.objects.create_empty(
            repository=repository,
            basedir='',
            revision=1)

        raw_date = '2000-01-01 00:00:00-0600'
        parsed_date = parse_date(raw_date)
        commit = DiffCommit.objects.create_from_data(
            repository=repository,
            diff_file_name='diff',
            diff_file_contents=diff,
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
        self.assertEqual(parsed_date, commit.author_date)
        self.assertEqual(parsed_date, commit.committer_date)

        self.assertEqual(
            raw_date,
            commit.author_date.strftime(DiffCommit.ISO_DATE_FORMAT))

        self.assertEqual(
            raw_date,
            commit.committer_date.strftime(DiffCommit.ISO_DATE_FORMAT))
