"""Tests for reviewboard.diffviewer.models.diffcommit."""

from __future__ import unicode_literals

from django.utils.timezone import now

from reviewboard.diffviewer.models import DiffCommit, DiffSet
from reviewboard.testing import TestCase


class DiffCommitTests(TestCase):
    """Tests for reviewboard.diffviewer.models.diffcommit.DiffCommit."""

    fixtures = ['test_scmtools']

    def setUp(self):
        super(DiffCommitTests, self).setUp()

        repository = self.create_repository()
        self.diffset = DiffSet.objects.create_empty(repository=repository)

        self.commits = [
            DiffCommit.objects.create(
                diffset=self.diffset,
                filename='diff',
                author_name='Author Name',
                author_email='author@example.com',
                commit_message='Message',
                author_date=now(),
                commit_id='a' * 40,
                parent_id='0' * 40),
            DiffCommit.objects.create(
                diffset=self.diffset,
                filename='diff',
                author_name='Author Name',
                author_email='author@example.com',
                commit_message='Message',
                author_date=now(),
                commit_id='b' * 40,
                parent_id='a' * 40),
        ]

        self.create_filediff(self.diffset, commit=self.commits[0],
                             diff=self.DEFAULT_GIT_FILEDIFF_DATA_DIFF)
        self.create_filediff(self.diffset, commit=self.commits[1],
                             diff=self.DEFAULT_GIT_FILEDIFF_DATA_DIFF)

    def test_get_line_counts_raw(self):
        """Testing DiffCommit.get_line_counts() returns correct raw counts"""
        self.assertEqual(self.diffset.get_total_line_counts(), {
            'raw_insert_count': 2,
            'raw_delete_count': 2,
            'insert_count': 2,
            'delete_count': 2,
            'replace_count': None,
            'equal_count': None,
            'total_line_count': None,
        })

        self.assertEqual(self.commits[0].get_total_line_counts(), {
            'raw_insert_count': 1,
            'raw_delete_count': 1,
            'insert_count': 1,
            'delete_count': 1,
            'replace_count': None,
            'equal_count': None,
            'total_line_count': None,
        })
        self.assertEqual(self.commits[1].get_total_line_counts(), {
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
        for filediff in self.diffset.files.all():
            filediff.extra_data.update({
                'insert_count': 0,
                'delete_count': 0,
                'equal_count': 0,
                'replace_count': 1,
                'total_line_count': 2,
            })
            filediff.save(update_fields=('extra_data',))

        self.assertEqual(self.diffset.get_total_line_counts(), {
            'raw_insert_count': 2,
            'raw_delete_count': 2,
            'insert_count': 0,
            'delete_count': 0,
            'replace_count': 2,
            'equal_count': 0,
            'total_line_count': 4,
        })

        self.assertEqual(self.commits[0].get_total_line_counts(), {
            'raw_insert_count': 1,
            'raw_delete_count': 1,
            'insert_count': 0,
            'delete_count': 0,
            'replace_count': 1,
            'equal_count': 0,
            'total_line_count': 2,
        })

        self.assertEqual(self.commits[1].get_total_line_counts(), {
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
        commits = list(DiffCommit.objects.all())
        self.assertEqual(commits, self.commits)
