"""Unit tests for reviewboard.diffviewer.commit_utils."""

from __future__ import unicode_literals

from kgb import SpyAgency

from reviewboard.diffviewer.commit_utils import (exclude_ancestor_filediffs,
                                                 get_file_exists_in_history)
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
                (2, 'baz', 'PRE-CREATION', 'baz', '280beb2'),
                (3, 'foo', '257cc56', 'qux', '03b37a0'),
                (3, 'corge', 'PRE-CREATION', 'corge', 'f248ba3'),
                (4, 'bar', '5716ca5', 'quux', 'e69de29'),
            )
        }

        self.assertEqual(expected, set(result))
