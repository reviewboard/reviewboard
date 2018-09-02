"""Unit tests for reviewboard.diffviewer.commit_utils."""

from __future__ import unicode_literals

from kgb import SpyAgency

from reviewboard.diffviewer.commit_utils import get_file_exists_in_history
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
        """Tesing get_file_exists_in_history for a file removed in a parent
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
