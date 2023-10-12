"""Tests for reviewboard.diffviewer.models.diffcommit."""

from __future__ import annotations

from typing import Sequence, Tuple

from django.utils import timezone

from reviewboard.diffviewer.models import DiffCommit, DiffSet
from reviewboard.testing import TestCase


class DiffCommitTests(TestCase):
    """Tests for reviewboard.diffviewer.models.diffcommit.DiffCommit."""

    fixtures = ['test_scmtools']

    def test_get_line_counts_raw(self):
        """Testing DiffCommit.get_line_counts() returns correct raw counts"""
        diffset, commits = self._populate_commits()

        self.assertEqual(diffset.get_total_line_counts(), {
            'raw_insert_count': 2,
            'raw_delete_count': 2,
            'insert_count': 2,
            'delete_count': 2,
            'replace_count': None,
            'equal_count': None,
            'total_line_count': None,
        })

        self.assertEqual(commits[0].get_total_line_counts(), {
            'raw_insert_count': 1,
            'raw_delete_count': 1,
            'insert_count': 1,
            'delete_count': 1,
            'replace_count': None,
            'equal_count': None,
            'total_line_count': None,
        })
        self.assertEqual(commits[1].get_total_line_counts(), {
            'raw_insert_count': 1,
            'raw_delete_count': 1,
            'insert_count': 1,
            'delete_count': 1,
            'replace_count': None,
            'equal_count': None,
            'total_line_count': None,
        })

    def test_get_line_counts_computed(self):
        """Testing DiffCommit.get_total_line_counts() returns correct computed
        line counts
        """
        diffset, commits = self._populate_commits()

        for filediff in diffset.files.all():
            filediff.extra_data.update({
                'insert_count': 0,
                'delete_count': 0,
                'equal_count': 0,
                'replace_count': 1,
                'total_line_count': 2,
            })
            filediff.save(update_fields=('extra_data',))

        self.assertEqual(diffset.get_total_line_counts(), {
            'raw_insert_count': 2,
            'raw_delete_count': 2,
            'insert_count': 0,
            'delete_count': 0,
            'replace_count': 2,
            'equal_count': 0,
            'total_line_count': 4,
        })

        self.assertEqual(commits[0].get_total_line_counts(), {
            'raw_insert_count': 1,
            'raw_delete_count': 1,
            'insert_count': 0,
            'delete_count': 0,
            'replace_count': 1,
            'equal_count': 0,
            'total_line_count': 2,
        })

        self.assertEqual(commits[1].get_total_line_counts(), {
            'raw_insert_count': 1,
            'raw_delete_count': 1,
            'insert_count': 0,
            'delete_count': 0,
            'replace_count': 1,
            'equal_count': 0,
            'total_line_count': 2,
        })

    def test_ordering(self):
        """Testing DiffCommits are returned in the correct order"""
        commits = self._populate_commits()[1]

        self.assertEqual(list(DiffCommit.objects.all()),
                         commits)

    def test_commit_message_body(self) -> None:
        """Testing DiffCommit.commit_message_body"""
        diffcommit = DiffCommit(commit_message=(
            'This is a summary line.\n'
            '\n'
            'This is a multi-line\n'
            'description.\n'
        ))

        self.assertEqual(
            diffcommit.commit_message_body,
            (
                'This is a multi-line\n'
                'description.'
            ))

    def test_commit_message_body_with_excess_newlines(self) -> None:
        """Testing DiffCommit.commit_message_body with newlines before and
        after body
        """
        diffcommit = DiffCommit(commit_message=(
            'This is a summary line.\n'
            '\n'
            '\n'
            'This is a multi-line\n'
            'description.\n'
            '\n'
        ))

        self.assertEqual(
            diffcommit.commit_message_body,
            (
                'This is a multi-line\n'
                'description.'
            ))

    def test_commit_message_body_with_only_summary(self) -> None:
        """Testing DiffCommit.commit_message_body with only summary"""
        diffcommit = DiffCommit(commit_message=(
            'This is a summary line.\n'
        ))

        self.assertIsNone(diffcommit.commit_message_body)

    def _populate_commits(self) -> Tuple[DiffSet, Sequence[DiffCommit]]:
        """Populate and return commits used for testing.

        Returns:
            tuple:
            A 2-tuple of:

            Tuple:
                0 (reviewboard.diffviewer.models.diffset.DiffSet):
                    The parent diffset for the commits.

                1 (list):
                    The list of commits.
        """
        repository = self.create_repository()
        diffset = DiffSet.objects.create_empty(repository=repository)

        now = timezone.now()

        commits = [
            DiffCommit.objects.create(
                diffset=diffset,
                filename='diff',
                author_name='Author Name',
                author_email='author@example.com',
                commit_message='Message',
                author_date=now,
                commit_id='a' * 40,
                parent_id='0' * 40),
            DiffCommit.objects.create(
                diffset=diffset,
                filename='diff',
                author_name='Author Name',
                author_email='author@example.com',
                commit_message='Message',
                author_date=now,
                commit_id='b' * 40,
                parent_id='a' * 40),
        ]

        diff_data = self.DEFAULT_GIT_FILEDIFF_DATA_DIFF

        self.create_filediff(diffset,
                             commit=commits[0],
                             diff=diff_data)
        self.create_filediff(diffset,
                             commit=commits[1],
                             diff=diff_data)

        return diffset, commits
