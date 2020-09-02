"""Unit tests for reviewboard.diffviewer.commit_utils."""

from __future__ import unicode_literals

from django.utils import six
from kgb import SpyAgency

from reviewboard.diffviewer.commit_utils import (CommitHistoryDiffEntry,
                                                 diff_histories,
                                                 exclude_ancestor_filediffs,
                                                 get_base_and_tip_commits,
                                                 get_file_exists_in_history)
from reviewboard.diffviewer.models import DiffCommit
from reviewboard.diffviewer.tests.test_diffutils import \
    BaseFileDiffAncestorTests
from reviewboard.scmtools.core import UNKNOWN
from reviewboard.testing.testcase import TestCase


class GetFileExistsInHistoryTests(SpyAgency, TestCase):
    """Unit tests for get_file_exists_in_history."""

    fixtures = ['test_scmtools']

    def test_added_in_parent_with_revision(self):
        """Testing get_file_exists_in_history for a file added in the parent
        commit for an SCM that uses file revisions
        """
        repository = self.create_repository()
        validation_info = {
            'r1': {
                'parent_id': 'r0',
                'tree': {
                    'added': [{
                        'filename': 'foo',
                        'revision': 'a' * 40,
                    }],
                    'modified': [],
                    'removed': [],
                },
            },
        }

        self.assertTrue(get_file_exists_in_history(
            validation_info=validation_info,
            repository=repository,
            parent_id='r1',
            path='foo',
            revision='a' * 40))

    def test_added_in_parent_without_revision(self):
        """Testing get_file_exists_in_history for a file added in the parent
        commit for an SCM that doesn't use file revisions
        """
        repository = self.create_repository(tool_name='Mercurial')
        validation_info = {
            'r1': {
                'parent_id': 'r0',
                'tree': {
                    'added': [{
                        'filename': 'foo',
                        'revision': UNKNOWN,
                    }],
                    'modified': [],
                    'removed': [],
                },
            },
        }

        self.assertTrue(get_file_exists_in_history(
            validation_info=validation_info,
            repository=repository,
            parent_id='r1',
            path='foo',
            revision=UNKNOWN))

    def test_added_in_grandparent_with_revision(self):
        """Testing get_file_exists_in_history for a file added in a
        grandparent commit for an SCM that uses file revisions
        """
        repository = self.create_repository()
        validation_info = {
            'r2': {
                'parent_id': 'r1',
                'tree': {
                    'added': [],
                    'modified': [],
                    'removed': [],
                },
            },
            'r1': {
                'parent_id': 'r0',
                'tree': {
                    'added': [{
                        'filename': 'foo',
                        'revision': 'a' * 40,
                    }],
                    'modified': [],
                    'removed': [],
                },
            },
        }

        self.assertTrue(get_file_exists_in_history(
            validation_info=validation_info,
            repository=repository,
            parent_id='r2',
            path='foo',
            revision='a' * 40))

    def test_added_in_grandparent_without_revision(self):
        """Testing get_file_exists_in_history for a file added in a
        grandparent commit for an SCM that doesn't use file revisions
        """
        repository = self.create_repository(tool_name='Mercurial')
        validation_info = {
            'r2': {
                'parent_id': 'r1',
                'tree': {
                    'added': [],
                    'modified': [],
                    'removed': [],
                },
            },
            'r1': {
                'parent_id': 'r0',
                'tree': {
                    'added': [{
                        'filename': 'foo',
                        'revision': UNKNOWN,
                    }],
                    'modified': [],
                    'removed': [],
                },
            },
        }

        self.assertTrue(get_file_exists_in_history(
            validation_info=validation_info,
            repository=repository,
            parent_id='r2',
            path='foo',
            revision=UNKNOWN))

    def test_removed_in_parent_without_revision(self):
        """Testing get_file_exists_in_history for a file removed in a parent
        revision for an SCM that uses file revisions
        """
        repository = self.create_repository()
        target_path = 'foo'
        target_revision = 'a' * 40

        self.spy_on(
            repository.get_file_exists,
            call_fake=self._make_get_file_exists_in_history(target_path,
                                                            target_revision))

        validation_info = {
            'r1': {
                'parent_id': 'r0',
                'tree': {
                    'added': [],
                    'modified': [],
                    'removed': [{
                        'filename': target_path,
                        'revision': target_revision,
                    }],
                },
            },
        }

        self.assertTrue(get_file_exists_in_history(
            validation_info=validation_info,
            repository=repository,
            parent_id='r1',
            path=target_path,
            revision=target_revision))

        self.assertTrue(repository.get_file_exists.spy.called_with(
            target_path, target_revision))

    def test_removed_in_parent_unknown_revision(self):
        """Testing get_file_exists_in_history for a file removed in a parent
        commit for an SCM that does not use file revisions
        """
        repository = self.create_repository(tool_name='Mercurial')

        validation_info = {
            'r1': {
                'parent_id': 'r0',
                'tree': {
                    'added': [],
                    'modified': [],
                    'removed': [{
                        'filename': 'foo',
                        'revision': UNKNOWN,
                    }],
                },
            },
        }

        self.assertFalse(get_file_exists_in_history(
            validation_info=validation_info,
            repository=repository,
            parent_id='r1',
            path='foo',
            revision=UNKNOWN))

    def test_removed_readded_in_parent_unknown_revision(self):
        """Testing get_file_exists_in_history for a file removed and re-added
        in parent commits for an SCM that does not use file revisions
        """
        repository = self.create_repository(tool_name='Mercurial')

        validation_info = {
            'r2': {
                'parent_id': 'r1',
                'tree': {
                    'added': [{
                        'filename': 'foo',
                        'revision': UNKNOWN,
                    }],
                    'modified': [],
                    'removed': [],
                },
            },
            'r1': {
                'parent_id': 'r0',
                'tree': {
                    'added': [],
                    'modified': [],
                    'removed': [{
                        'filename': 'foo',
                        'revision': UNKNOWN,
                    }],
                },
            },
        }

        self.assertFalse(get_file_exists_in_history(
            validation_info=validation_info,
            repository=repository,
            parent_id='r1',
            path='foo',
            revision=UNKNOWN))

        self.assertTrue(get_file_exists_in_history(
            validation_info=validation_info,
            repository=repository,
            parent_id='r2',
            path='foo',
            revision=UNKNOWN))

    def test_modified_in_parent_with_revision(self):
        """Testing get_file_exists_in_history for a file modified in a
        parent revision for an SCM that uses file revisions
        """
        repository = self.create_repository()
        self.spy_on(
            repository.get_file_exists,
            call_fake=self._make_get_file_exists_in_history('foo', 'a' * 40))

        validation_info = {
            'r2': {
                'parent_id': 'r1',
                'tree': {
                    'added': [],
                    'modified': [{
                        'filename': 'foo',
                        'revision': 'c' * 40,
                    }],
                    'removed': [],
                },
            },
            'r1': {
                'parent_id': 'r0',
                'tree': {
                    'added': [],
                    'modified': [{
                        'filename': 'foo',
                        'revision': 'b' * 40,
                    }],
                    'removed': [],
                },
            },
        }

        self.assertTrue(get_file_exists_in_history(
            validation_info=validation_info,
            repository=repository,
            parent_id='r2',
            path='foo',
            revision='c' * 40))
        self.assertFalse(repository.get_file_exists.spy.called)

        self.assertTrue(get_file_exists_in_history(
            validation_info=validation_info,
            repository=repository,
            parent_id='r1',
            path='foo',
            revision='b' * 40))
        self.assertFalse(repository.get_file_exists.spy.called)

        self.assertTrue(get_file_exists_in_history(
            validation_info=validation_info,
            repository=repository,
            parent_id='r0',
            path='foo',
            revision='a' * 40))
        self.assertTrue(repository.get_file_exists.spy.called_with(
            'foo', 'a' * 40,
        ))

    def test_modified_in_parent_unknown_revision(self):
        """Testing get_file_exists_in_history for a file modified in a
        parent revision for an SCM that does not use file revision
        """
        repository = self.create_repository(tool_name='Mercurial')
        self.spy_on(
            repository.get_file_exists,
            call_fake=self._make_get_file_exists_in_history('foo', UNKNOWN))

        validation_info = {
            'r2': {
                'parent_id': 'r1',
                'tree': {
                    'added': [],
                    'modified': [{
                        'filename': 'foo',
                        'revision': UNKNOWN,
                    }],
                    'removed': [],
                },
            },
            'r1': {
                'parent_id': 'r0',
                'tree': {
                    'added': [],
                    'modified': [{
                        'filename': 'foo',
                        'revision': UNKNOWN,
                    }],
                    'removed': [],
                },
            },
        }

        self.assertTrue(get_file_exists_in_history(
            validation_info=validation_info,
            repository=repository,
            parent_id='r2',
            path='foo',
            revision=UNKNOWN))
        self.assertFalse(repository.get_file_exists.spy.called)

        self.assertTrue(get_file_exists_in_history(
            validation_info=validation_info,
            repository=repository,
            parent_id='r1',
            path='foo',
            revision=UNKNOWN))
        self.assertFalse(repository.get_file_exists.spy.called)

        self.assertTrue(get_file_exists_in_history(
            validation_info=validation_info,
            repository=repository,
            parent_id='r0',
            path='foo',
            revision=UNKNOWN))
        self.assertTrue(repository.get_file_exists.spy.called_with(
            'foo', UNKNOWN))

    def _make_get_file_exists_in_history(self, target_path, target_revision):
        """Return a fake get_file_exists_in_history method for a repository.

        Args:
            target_path (unicode):
                The path that should report as existing in the repository.

            target_revision (unicode):
                The revision of the file.

        Returns:
            callable:
            A function that only returns True when called with the given
            ``target_path`` and ``target_revision``.
        """
        def get_file_exists_in_history(repository, path, revision, *args,
                                       **kwargs):
            return path == target_path and revision == target_revision

        return get_file_exists_in_history


class ExcludeAncestorFileDiffsTests(BaseFileDiffAncestorTests):
    """Unit tests for commit_utils.exclude_ancestor_filediffs."""

    def setUp(self):
        super(ExcludeAncestorFileDiffsTests, self).setUp()

        self.set_up_filediffs()

    def test_exclude(self):
        """Testing exclude_ancestor_filediffs"""
        self._test_excluded(exclude_ancestor_filediffs(self.filediffs))

    def test_exclude_query_count(self):
        """Testing exclude_ancestor_filediffs query count"""
        num_queries = len(self.filediffs)

        with self.assertNumQueries(num_queries):
            result = exclude_ancestor_filediffs(self.filediffs)

        self._test_excluded(result)

    def test_exclude_query_count_precomputed(self):
        """Testing exclude_ancestor_filediffs query count when the ancestors
        are pre-computed
        """
        for filediff in self.filediffs:
            filediff.get_ancestors(minimal=False, filediffs=self.filediffs)

        with self.assertNumQueries(0):
            result = exclude_ancestor_filediffs(self.filediffs)

        self._test_excluded(result)

    def _test_excluded(self, result):
        """Test that the given set of FileDiffs matches the expected results.

        Args:
            result (list of reviewboard.diffviewer.models.filediff.FileDiff):
                The FileDiffs that were returned from :py:func:`~reviewboard.
                diffviewer.commit_utils.exclude_ancestor_filediffs`.

        Raises:
            AssertionError:
                The FileDiffs do not match the expected results.
        """
        by_details = {
            (
                filediff.commit_id,
                filediff.source_file,
                filediff.source_revision,
                filediff.dest_file,
                filediff.dest_detail,
            ): filediff
            for filediff in self.filediffs
        }

        expected = {
            by_details[details]
            for details in (
                (2, 'baz', '7601807', 'baz', '280beb2'),
                (3, 'foo', '257cc56', 'qux', '03b37a0'),
                (3, 'corge', 'e69de29', 'corge', 'f248ba3'),
                (4, 'bar', '5716ca5', 'quux', 'e69de29'),
            )
        }

        self.assertEqual(expected, set(result))


class DiffHistoriesTests(TestCase):
    """Unit tests for reviewboard.diffviewer.commit_utils.diff_histories."""

    def test_diff_histories_identical(self):
        """Testing diff_histories with identical histories"""
        new_history = old_history = [
            DiffCommit(commit_id='r0'),
            DiffCommit(commit_id='r1'),
            DiffCommit(commit_id='r2'),
        ]

        expected_result = [
            CommitHistoryDiffEntry(
                entry_type=CommitHistoryDiffEntry.COMMIT_UNMODIFIED,
                old_commit=old_history[0],
                new_commit=new_history[0]),
            CommitHistoryDiffEntry(
                entry_type=CommitHistoryDiffEntry.COMMIT_UNMODIFIED,
                old_commit=old_history[1],
                new_commit=new_history[1]),
            CommitHistoryDiffEntry(
                entry_type=CommitHistoryDiffEntry.COMMIT_UNMODIFIED,
                old_commit=old_history[2],
                new_commit=new_history[2]),
        ]

        self.assertEqual(list(diff_histories(old_history, new_history)),
                         expected_result)

    def test_diff_histories_added(self):
        """Testing diff_histories with a new history that adds commits at the
        end of the history
        """
        old_history = [
            DiffCommit(commit_id='r0'),
            DiffCommit(commit_id='r1'),
        ]

        new_history = [
            DiffCommit(commit_id='r0'),
            DiffCommit(commit_id='r1'),
            DiffCommit(commit_id='r2'),
        ]

        expected_result = [
            CommitHistoryDiffEntry(
                entry_type=CommitHistoryDiffEntry.COMMIT_UNMODIFIED,
                old_commit=old_history[0],
                new_commit=new_history[0]),
            CommitHistoryDiffEntry(
                entry_type=CommitHistoryDiffEntry.COMMIT_UNMODIFIED,
                old_commit=old_history[1],
                new_commit=new_history[1]),
            CommitHistoryDiffEntry(
                entry_type=CommitHistoryDiffEntry.COMMIT_ADDED,
                new_commit=new_history[2]),
        ]

        self.assertEqual(list(diff_histories(old_history, new_history)),
                         expected_result)

    def test_diff_histories_removed(self):
        """Testing diff_histories with a new history that removes commits"""
        old_history = [
            DiffCommit(commit_id='r0'),
            DiffCommit(commit_id='r1'),
            DiffCommit(commit_id='r2'),
        ]

        new_history = [
            DiffCommit(commit_id='r0'),
            DiffCommit(commit_id='r1'),
        ]

        expected_result = [
            CommitHistoryDiffEntry(
                entry_type=CommitHistoryDiffEntry.COMMIT_UNMODIFIED,
                old_commit=old_history[0],
                new_commit=new_history[0]),
            CommitHistoryDiffEntry(
                entry_type=CommitHistoryDiffEntry.COMMIT_UNMODIFIED,
                old_commit=old_history[1],
                new_commit=new_history[1]),
            CommitHistoryDiffEntry(
                entry_type=CommitHistoryDiffEntry.COMMIT_REMOVED,
                old_commit=old_history[2]),
        ]

        self.assertEqual(list(diff_histories(old_history, new_history)),
                         expected_result)

    def test_diff_histories_added_start(self):
        """Testing diff_histories with a new history that adds commits at the
        start of the history
        """
        old_history = [
            DiffCommit(commit_id='r1'),
            DiffCommit(commit_id='r2'),
        ]

        new_history = [
            DiffCommit(commit_id='r0'),
            DiffCommit(commit_id='r1'),
            DiffCommit(commit_id='r2'),
        ]

        expected_result = [
            CommitHistoryDiffEntry(
                entry_type=CommitHistoryDiffEntry.COMMIT_REMOVED,
                old_commit=old_history[0]),
            CommitHistoryDiffEntry(
                entry_type=CommitHistoryDiffEntry.COMMIT_REMOVED,
                old_commit=old_history[1]),
            CommitHistoryDiffEntry(
                entry_type=CommitHistoryDiffEntry.COMMIT_ADDED,
                new_commit=new_history[0]),
            CommitHistoryDiffEntry(
                entry_type=CommitHistoryDiffEntry.COMMIT_ADDED,
                new_commit=new_history[1]),
            CommitHistoryDiffEntry(
                entry_type=CommitHistoryDiffEntry.COMMIT_ADDED,
                new_commit=new_history[2]),
        ]

        self.assertEqual(list(diff_histories(old_history, new_history)),
                         expected_result)

    def test_diff_histories_removed_start(self):
        """Testing diff_histories with a new history that removes commits at
        the start of the history
        """
        old_history = [
            DiffCommit(commit_id='r0'),
            DiffCommit(commit_id='r1'),
            DiffCommit(commit_id='r2'),
        ]

        new_history = [
            DiffCommit(commit_id='r1'),
            DiffCommit(commit_id='r2'),
        ]

        expected_result = [
            CommitHistoryDiffEntry(
                entry_type=CommitHistoryDiffEntry.COMMIT_REMOVED,
                old_commit=old_history[0]),
            CommitHistoryDiffEntry(
                entry_type=CommitHistoryDiffEntry.COMMIT_REMOVED,
                old_commit=old_history[1]),
            CommitHistoryDiffEntry(
                entry_type=CommitHistoryDiffEntry.COMMIT_REMOVED,
                old_commit=old_history[2]),
            CommitHistoryDiffEntry(
                entry_type=CommitHistoryDiffEntry.COMMIT_ADDED,
                new_commit=new_history[0]),
            CommitHistoryDiffEntry(
                entry_type=CommitHistoryDiffEntry.COMMIT_ADDED,
                new_commit=new_history[1]),
        ]

        self.assertEqual(list(diff_histories(old_history, new_history)),
                         expected_result)

    def test_diff_histories_addedd_middle(self):
        """Testing diff_histories with a new history that adds commits in the
        middle of the history
        """
        old_history = [
            DiffCommit(commit_id='r0'),
            DiffCommit(commit_id='r2'),
        ]

        new_history = [
            DiffCommit(commit_id='r0'),
            DiffCommit(commit_id='r1'),
            DiffCommit(commit_id='r2'),
        ]

        expected_result = [
            CommitHistoryDiffEntry(
                entry_type=CommitHistoryDiffEntry.COMMIT_UNMODIFIED,
                old_commit=old_history[0],
                new_commit=new_history[0]),
            CommitHistoryDiffEntry(
                entry_type=CommitHistoryDiffEntry.COMMIT_REMOVED,
                old_commit=old_history[1]),
            CommitHistoryDiffEntry(
                entry_type=CommitHistoryDiffEntry.COMMIT_ADDED,
                new_commit=new_history[1]),
            CommitHistoryDiffEntry(
                entry_type=CommitHistoryDiffEntry.COMMIT_ADDED,
                new_commit=new_history[2]),
        ]

        self.assertEqual(list(diff_histories(old_history, new_history)),
                         expected_result)

    def test_diff_histories_removed_middle(self):
        """Testing diff_histories with a new history that removes commits in
        the middle of the history
        """
        old_history = [
            DiffCommit(commit_id='r0'),
            DiffCommit(commit_id='r1'),
            DiffCommit(commit_id='r2'),
        ]

        new_history = [
            DiffCommit(commit_id='r0'),
            DiffCommit(commit_id='r2'),
        ]

        expected_result = [
            CommitHistoryDiffEntry(
                entry_type=CommitHistoryDiffEntry.COMMIT_UNMODIFIED,
                old_commit=old_history[0],
                new_commit=new_history[0]),
            CommitHistoryDiffEntry(
                entry_type=CommitHistoryDiffEntry.COMMIT_REMOVED,
                old_commit=old_history[1]),
            CommitHistoryDiffEntry(
                entry_type=CommitHistoryDiffEntry.COMMIT_REMOVED,
                old_commit=old_history[2]),
            CommitHistoryDiffEntry(
                entry_type=CommitHistoryDiffEntry.COMMIT_ADDED,
                new_commit=new_history[1]),
        ]

        self.assertEqual(list(diff_histories(old_history, new_history)),
                         expected_result)


class GetBaseAndTipCommitsTests(TestCase):
    """Unit tests for commit_utils.get_base_and_tip_commits."""

    fixtures = ['test_scmtools']

    def setUp(self):
        super(GetBaseAndTipCommitsTests, self).setUp()

        self.repository = self.create_repository(tool_name='Git')
        self.diffset = self.create_diffset(repository=self.repository)
        self.commits = {
            commit.pk: commit
            for commit in (
                self.create_diffcommit(diffset=self.diffset, **kwargs)
                for kwargs in (
                    {'commit_id': 'r1', 'parent_id': 'r0'},
                    {'commit_id': 'r2', 'parent_id': 'r1'},
                    {'commit_id': 'r3', 'parent_id': 'r2'},
                    {'commit_id': 'r4', 'parent_id': 'r3'},
                    {'commit_id': 'r5', 'parent_id': 'r4'},
                    {'commit_id': 'r6', 'parent_id': 'r5'},
                )
            )
        }

    def test_get_base_and_tip_commits_no_commits_no_diffset(self):
        """Testing get_base_and_tip_commits with no commits and no diffset
        raises ValueError
        """
        with self.assertRaises(ValueError):
            get_base_and_tip_commits(base_commit_id=1,
                                     tip_commit_id=5)

    def test_get_base_and_tip_commits_commits_no_diffset(self):
        """Testing get_base_and_tip_commits with commits and no diffset"""
        with self.assertNumQueries(0):
            base, tip = get_base_and_tip_commits(
                base_commit_id=1,
                tip_commit_id=5,
                commits=[
                    commit
                    for commit in six.itervalues(self.commits)
                ])

        self.assertEqual(self.commits[1], base)
        self.assertEqual(self.commits[5], tip)

    def test_get_base_and_tip_commits_no_commits_diffset(self):
        """Testing get_base_and_tip_commits with a diffset and no commits"""
        with self.assertNumQueries(1):
            base, tip = get_base_and_tip_commits(
                base_commit_id=1,
                tip_commit_id=5,
                diffset=self.diffset)

        self.assertEqual(self.commits[1], base)
        self.assertEqual(self.commits[5], tip)

    def test_get_base_and_tip_commits_with_commits_invalid_commit_id(self):
        """Testing get_base_and_tip_commits with commits and an invalid commit
        ID
        """
        base, tip = get_base_and_tip_commits(
            base_commit_id=7,
            tip_commit_id=5000,
            commits=[
                commit
                for commit in six.itervalues(self.commits)
            ])

        self.assertIsNone(base)
        self.assertIsNone(tip)

    def test_get_base_and_tip_commits_with_diffset_invalid_commit_id(self):
        """Testing get_base_and_tip_commits with commits and an invalid commit
        ID
        """
        other_diffset = self.create_diffset(repository=self.repository)
        other_commits = [
            self.create_diffcommit(diffset=other_diffset, **kwargs)
            for kwargs in (
                {'commit_id': 'r1', 'parent_id': 'r0'},
                {'commit_id': 'r2', 'parent_id': 'r1'},
            )
        ]

        base, tip = get_base_and_tip_commits(
            base_commit_id=other_commits[0].pk,
            tip_commit_id=other_commits[1].pk,
            diffset=self.diffset)

        self.assertIsNone(base)
        self.assertIsNone(tip)

    def test_get_base_and_tip_commits_only_base(self):
        """Testing get_base_and_tip_commits with only base_commit_id"""
        base, tip = get_base_and_tip_commits(
            base_commit_id=3,
            tip_commit_id=None,
            diffset=self.diffset)

        self.assertEqual(self.commits[3], base)
        self.assertIsNone(tip)

    def test_get_base_and_tip_commits_only_tip(self):
        """Testing get_base_and_tip_commits with only tip_commit_id"""
        base, tip = get_base_and_tip_commits(
            base_commit_id=None,
            tip_commit_id=3,
            diffset=self.diffset)

        self.assertIsNone(base)
        self.assertEqual(self.commits[3], tip)
