"""Tests for reviewboard.diffviewer.filediff_creator."""

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
            diff_file_contents=self.DEFAULT_GIT_FILEDIFF_DATA_DIFF,
            parent_diff_file_contents=None,
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
            diff_file_contents=self.DEFAULT_GIT_FILEDIFF_DATA_DIFF,
            parent_diff_file_contents=None,
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
            diff_file_contents=self.DEFAULT_GIT_FILEDIFF_DATA_DIFF,
            parent_diff_file_contents=None,
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

    def test_create_filediffs_with_symlinks(self):
        """Testing create_filediffs() with symlinks"""
        repository = self.create_repository(tool_name='TestToolDiffX')
        diffset = self.create_diffset(repository=repository)

        self.assertEqual(diffset.files.count(), 0)

        create_filediffs(
            diff_file_contents=(
                b'#diffx: encoding=utf-8, version=1.0\n'
                b'#.change:\n'
                b'#..file:\n'
                b'#...meta: format=json, length=140\n'
                b'{\n'
                b'    "op": "modify",\n'
                b'    "path": "name",\n'
                b'    "revision": {\n'
                b'        "old": "abc123",\n'
                b'        "new": "def456"\n'
                b'    },\n'
                b'    "type": "symlink"\n'
                b'}\n'
            ),
            parent_diff_file_contents=None,
            repository=repository,
            basedir='/',
            base_commit_id='0' * 40,
            diffset=diffset,
            check_existence=False)

        diffset = DiffSet.objects.get(pk=diffset.pk)

        self.assertEqual(diffset.files.count(), 1)
        filediff = diffset.files.get()

        self.assertTrue(filediff.is_symlink)
        self.assertIsNone(filediff.old_symlink_target)
        self.assertIsNone(filediff.new_symlink_target)

    def test_create_filediffs_with_symlinks_and_targets(self):
        """Testing create_filediffs() with symlinks and symlink targets"""
        repository = self.create_repository(tool_name='TestToolDiffX')
        diffset = self.create_diffset(repository=repository)

        self.assertEqual(diffset.files.count(), 0)

        create_filediffs(
            diff_file_contents=(
                b'#diffx: encoding=utf-8, version=1.0\n'
                b'#.change:\n'
                b'#..file:\n'
                b'#...meta: format=json, length=230\n'
                b'{\n'
                b'    "op": "modify",\n'
                b'    "path": "name",\n'
                b'    "revision": {\n'
                b'        "old": "abc123",\n'
                b'        "new": "def456"\n'
                b'    },\n'
                b'    "symlink target": {\n'
                b'        "old": "old/target/",\n'
                b'        "new": "new/target/"\n'
                b'    },\n'
                b'    "type": "symlink"\n'
                b'}\n'
            ),
            parent_diff_file_contents=None,
            repository=repository,
            basedir='/',
            base_commit_id='0' * 40,
            diffset=diffset,
            check_existence=False)

        diffset = DiffSet.objects.get(pk=diffset.pk)

        self.assertEqual(diffset.files.count(), 1)
        filediff = diffset.files.get()

        self.assertTrue(filediff.is_symlink)
        self.assertEqual(filediff.old_symlink_target, 'old/target/')
        self.assertEqual(filediff.new_symlink_target, 'new/target/')

    def test_create_filediffs_with_unix_mode(self):
        """Testing create_filediffs() with UNIX file modes"""
        repository = self.create_repository(tool_name='TestToolDiffX')
        diffset = self.create_diffset(repository=repository)

        self.assertEqual(diffset.files.count(), 0)

        create_filediffs(
            diff_file_contents=(
                b'#diffx: encoding=utf-8, version=1.0\n'
                b'#.change:\n'
                b'#..file:\n'
                b'#...meta: format=json, length=199\n'
                b'{\n'
                b'    "op": "modify",\n'
                b'    "path": "name",\n'
                b'    "revision": {\n'
                b'        "old": "abc123",\n'
                b'        "new": "def456"\n'
                b'    },\n'
                b'    "unix file mode": {\n'
                b'        "old": "0100644",\n'
                b'        "new": "0100755"\n'
                b'    }\n'
                b'}\n'
            ),
            parent_diff_file_contents=None,
            repository=repository,
            basedir='/',
            base_commit_id='0' * 40,
            diffset=diffset,
            check_existence=False)

        diffset = DiffSet.objects.get(pk=diffset.pk)

        self.assertEqual(diffset.files.count(), 1)
        filediff = diffset.files.get()

        self.assertEqual(filediff.old_unix_mode, '0100644')
        self.assertEqual(filediff.new_unix_mode, '0100755')
