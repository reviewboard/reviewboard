"""Tests for reviewboard.diffviewer.filediff_creator."""

from __future__ import unicode_literals

from django.utils.timezone import now

from reviewboard.diffviewer.filediff_creator import create_filediffs
from reviewboard.diffviewer.models import DiffCommit, DiffSet
from reviewboard.testing import TestCase


class FileDiffCreatorTests(TestCase):
    """Tests for reviewboard.diffviewer.filediff_creator."""

    fixtures = ['test_scmtools']

    def test_create_filediffs_file_count(self):
        """Testing create_filediffs() with a DiffSet"""
        repository = self.create_repository()
        diffset = self.create_diffset(repository=repository)

        self.assertEqual(diffset.files.count(), 0)

        create_filediffs(
            self.DEFAULT_GIT_FILEDIFF_DATA_DIFF,
            None,
            repository=repository,
            basedir='/',
            base_commit_id='0' * 40,
            diffset=diffset,
            check_existence=False)

        diffset = DiffSet.objects.get(pk=diffset.pk)

        self.assertEqual(diffset.files.count(), 1)

    def test_create_filediffs_commit_file_count(self):
        """Testing create_filediffs() with a DiffSet and a DiffCommit"""
        repository = self.create_repository()
        diffset = DiffSet.objects.create_empty(repository=repository)
        commits = [
            DiffCommit.objects.create(
                diffset=diffset,
                filename='diff',
                author_name='Author Name',
                author_email='author@example.com',
                commit_message='Message',
                author_date=now(),
                commit_id='a' * 40,
                parent_id='0' * 40),
            DiffCommit.objects.create(
                diffset=diffset,
                filename='diff',
                author_name='Author Name',
                author_email='author@example.com',
                commit_message='Message',
                author_date=now(),
                commit_id='b' * 40,
                parent_id='a' * 40),
        ]

        self.assertEqual(diffset.files.count(), 0)
        self.assertEqual(commits[0].files.count(), 0)

        create_filediffs(
            self.DEFAULT_GIT_FILEDIFF_DATA_DIFF,
            None,
            repository=repository,
            basedir='/',
            base_commit_id='0' * 40,
            diffset=diffset,
            diffcommit=commits[0],
            check_existence=False)

        diffset = DiffSet.objects.get(pk=diffset.pk)
        commits[0] = DiffCommit.objects.get(pk=commits[0].pk)

        self.assertEqual(diffset.files.count(), 1)
        self.assertEqual(commits[0].files.count(), 1)

        create_filediffs(
            self.DEFAULT_GIT_FILEDIFF_DATA_DIFF,
            None,
            repository=repository,
            basedir='/',
            base_commit_id='0' * 40,
            diffset=diffset,
            diffcommit=commits[1],
            check_existence=False)

        diffset = DiffSet.objects.get(pk=diffset.pk)
        commits[1] = DiffCommit.objects.get(pk=commits[1].pk)

        self.assertEqual(diffset.files.count(), 2)
        self.assertEqual(commits[1].files.count(), 1)
