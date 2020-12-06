from __future__ import print_function, unicode_literals

from django.contrib.auth.models import AnonymousUser
from django.test.client import RequestFactory
from django.utils import six
from django.utils.six.moves import zip_longest
from djblets.siteconfig.models import SiteConfiguration
from djblets.testing.decorators import add_fixtures
from kgb import SpyAgency

from reviewboard.deprecation import RemovedInReviewBoard50Warning
from reviewboard.diffviewer.diffutils import (
    convert_line_endings,
    convert_to_unicode,
    get_diff_data_chunks_info,
    get_diff_files,
    get_displayed_diff_line_ranges,
    get_file_chunks_in_range,
    get_filediffs_match,
    get_filediff_encodings,
    get_last_header_before_line,
    get_last_line_number_in_diff,
    get_line_changed_regions,
    get_matched_interdiff_files,
    get_original_file,
    get_original_file_from_repo,
    get_revision_str,
    get_sorted_filediffs,
    patch,
    split_line_endings,
    _PATCH_GARBAGE_INPUT,
    _get_last_header_in_chunks_before_line)
from reviewboard.diffviewer.errors import PatchError
from reviewboard.diffviewer.models import DiffCommit, FileDiff
from reviewboard.scmtools.core import PRE_CREATION
from reviewboard.scmtools.errors import FileNotFoundError
from reviewboard.scmtools.models import Repository
from reviewboard.testing import TestCase


class BaseFileDiffAncestorTests(SpyAgency, TestCase):
    """A base test case that creates a FileDiff history."""

    fixtures = ['test_scmtools']

    _COMMITS = [
        {
            'parent': (
                b'diff --git a/bar b/bar\n'
                b'index e69de29..5716ca5 100644\n'
                b'--- a/bar\n'
                b'+++ b/bar\n'
                b'@@ -0,0 +1 @@\n'
                b'+bar\n'
            ),
            'diff': (
                b'diff --git a/foo b/foo\n'
                b'new file mode 100644\n'
                b'index 0000000..e69de29\n'

                b'diff --git a/bar b/bar\n'
                b'index 5716ca5..8e739cc 100644\n'
                b'--- a/bar\n'
                b'+++ b/bar\n'
                b'@@ -1 +1 @@\n'
                b'-bar\n'
                b'+bar bar bar\n'
            ),
        },
        {
            'parent': (
                b'diff --git a/baz b/baz\n'
                b'new file mode 100644\n'
                b'index 0000000..7601807\n'
                b'--- /dev/null\n'
                b'+++ b/baz\n'
                b'@@ -0,0 +1 @@\n'
                b'+baz\n'
            ),
            'diff': (
                b'diff --git a/foo b/foo\n'
                b'index e69de29..257cc56 100644\n'
                b'--- a/foo\n'
                b'+++ b/foo\n'
                b'@@ -0,0 +1 @@\n'
                b'+foo\n'

                b'diff --git a/bar b/bar\n'
                b'deleted file mode 100644\n'
                b'index 8e739cc..0000000\n'
                b'--- a/bar\n'
                b'+++ /dev/null\n'
                b'@@ -1 +0,0 @@\n'
                b'-bar -bar -bar\n'

                b'diff --git a/baz b/baz\n'
                b'index 7601807..280beb2 100644\n'
                b'--- a/baz\n'
                b'+++ b/baz\n'
                b'@@ -1 +1 @@\n'
                b'-baz\n'
                b'+baz baz baz\n'
            ),
        },
        {
            'parent': (
                b'diff --git a/corge b/corge\n'
                b'new file mode 100644\n'
                b'index 0000000..e69de29\n'
            ),
            'diff': (
                b'diff --git a/foo b/qux\n'
                b'index 257cc56..03b37a0 100644\n'
                b'--- a/foo\n'
                b'+++ b/qux\n'
                b'@@ -1 +1 @@\n'
                b'-foo\n'
                b'+foo bar baz qux\n'

                b'diff --git a/bar b/bar\n'
                b'new file mode 100644\n'
                b'index 0000000..5716ca5\n'
                b'--- /dev/null\n'
                b'+++ b/bar\n'
                b'@@ -0,0 +1 @@\n'
                b'+bar\n'

                b'diff --git a/corge b/corge\n'
                b'index e69de29..f248ba3 100644\n'
                b'--- a/corge\n'
                b'+++ b/corge\n'
                b'@@ -0,0 +1 @@\n'
                b'+corge\n'
            ),
        },
        {
            'parent': None,
            'diff': (
                b'diff --git a/bar b/quux\n'
                b'index 5716ca5..e69de29 100644\n'
                b'--- a/bar\n'
                b'+++ b/quux\n'
                b'@@ -1 +0,0 @@\n'
                b'-bar\n'
            ),
        },
    ]

    _CUMULATIVE_DIFF = {
        'parent': b''.join(
            parent_diff
            for parent_diff in (
                entry['parent']
                for entry in _COMMITS
            )
            if parent_diff is not None
        ),
        'diff': (
            b'diff --git a/qux b/qux\n'
            b'new file mode 100644\n'
            b'index 000000..03b37a0\n'
            b'--- /dev/null\n'
            b'+++ /b/qux\n'
            b'@@ -0,0 +1 @@\n'
            b'foo bar baz qux\n'

            b'diff --git a/bar b/quux\n'
            b'index 5716ca5..e69de29 100644\n'
            b'--- a/bar\n'
            b'+++ b/quux\n'
            b'@@ -1 +0,0 @@\n'
            b'-bar\n'

            b'diff --git a/baz b/baz\n'
            b'index 7601807..280beb2 100644\n'
            b'--- a/baz\n'
            b'+++ b/baz\n'
            b'@@ -1 +1 @@\n'
            b'-baz\n'
            b'+baz baz baz\n'

            b'diff --git a/corge b/corge\n'
            b'index e69de29..f248ba3 100644\n'
            b'--- a/corge\n'
            b'+++ b/corge\n'
            b'@@ -0,0 +1 @@\n'
            b'+corge\n'
        ),
    }

    _FILES = {
        ('bar', 'e69de29'): b'',
    }

    # A mapping of filediff details to the details of its ancestors in
    # (compliment, minimal) form.
    _HISTORY = {
        (1, 'foo', 'PRE-CREATION', 'foo', 'e69de29'): ([], []),
        (1, 'bar', 'e69de29', 'bar', '8e739cc'): ([], []),
        (2, 'foo', 'e69de29', 'foo', '257cc56'): (
            [],
            [
                (1, 'foo', 'PRE-CREATION', 'foo', 'e69de29'),
            ],
        ),
        (2, 'bar', '8e739cc', 'bar', '0000000'): (
            [],
            [
                (1, 'bar', 'e69de29', 'bar', '8e739cc'),
            ],
        ),
        (2, 'baz', 'PRE-CREATION', 'baz', '280beb2'): ([], []),
        (3, 'foo', '257cc56', 'qux', '03b37a0'): (
            [],
            [
                (1, 'foo', 'PRE-CREATION', 'foo', 'e69de29'),
                (2, 'foo', 'e69de29', 'foo', '257cc56'),
            ],
        ),
        (3, 'bar', 'PRE-CREATION', 'bar', '5716ca5'): (
            [
                (1, 'bar', 'e69de29', 'bar', '8e739cc'),
                (2, 'bar', '8e739cc', 'bar', '0000000'),
            ],
            [],
        ),
        (3, 'corge', 'PRE-CREATION', 'corge', 'f248ba3'): ([], []),
        (4, 'bar', '5716ca5', 'quux', 'e69de29'): (
            [
                (1, 'bar', 'e69de29', 'bar', '8e739cc'),
                (2, 'bar', '8e739cc', 'bar', '0000000'),
            ],
            [
                (3, 'bar', 'PRE-CREATION', 'bar', '5716ca5'),
            ],
        ),
    }

    def set_up_filediffs(self):
        """Create a set of commits with history."""
        def get_file(repo, path, revision, base_commit_id=None, request=None):
            if repo == self.repository:
                try:
                    return self._FILES[(path, revision)]
                except KeyError:
                    raise FileNotFoundError(path, revision,
                                            base_commit_id=base_commit_id)

            raise FileNotFoundError(path, revision,
                                    base_commit_id=base_commit_id)

        self.repository = self.create_repository(tool_name='Git')

        self.spy_on(Repository.get_file,
                    owner=Repository,
                    call_fake=get_file)
        self.spy_on(Repository.get_file_exists,
                    owner=Repository,
                    call_fake=lambda *args, **kwargs: True)

        self.diffset = self.create_diffset(repository=self.repository)

        for i, diff in enumerate(self._COMMITS, 1):
            commit_id = 'r%d' % i
            parent_id = 'r%d' % (i - 1)

            self.create_diffcommit(
                diffset=self.diffset,
                repository=self.repository,
                commit_id=commit_id,
                parent_id=parent_id,
                diff_contents=diff['diff'],
                parent_diff_contents=diff['parent'])

        self.filediffs = list(FileDiff.objects.all())
        self.diffset.finalize_commit_series(
            cumulative_diff=self._CUMULATIVE_DIFF['diff'],
            parent_diff=self._CUMULATIVE_DIFF['parent'],
            validation_info=None,
            validate=False,
            save=True)

        # This was only necessary so that we could side step diff validation
        # during creation.
        Repository.get_file_exists.unspy()

    def get_filediffs_by_details(self):
        """Return a mapping of FileDiff details to the FileDiffs.

        Returns:
            dict:
            A mapping of FileDiff details to FileDiffs.
        """
        return {
            (
                filediff.commit_id,
                filediff.source_file,
                filediff.source_revision,
                filediff.dest_file,
                filediff.dest_detail,
            ): filediff
            for filediff in self.filediffs
        }


class GetDiffDataChunksInfoTests(TestCase):
    """Unit tests for get_diff_data_chunks_info."""

    def test_with_basic_diff(self):
        """Testing get_diff_data_chunks_info with a basic one-chunk diff"""
        self.assertEqual(
            get_diff_data_chunks_info(
                b'@@ -10,7 +12,10 @@\n'
                b' #\n'
                b' #\n'
                b' #\n'
                b'-# old line\n'
                b'+# new line\n'
                b'+# new line\n'
                b'+# new line\n'
                b'+# new line\n'
                b' #\n'
                b' #\n'
                b' #\n'),
            [
                {
                    'orig': {
                        'pre_lines_of_context': 3,
                        'post_lines_of_context': 3,
                        'chunk_start': 9,
                        'chunk_len': 7,
                        'changes_start': 12,
                        'changes_len': 1,
                    },
                    'modified': {
                        'pre_lines_of_context': 3,
                        'post_lines_of_context': 3,
                        'chunk_start': 11,
                        'chunk_len': 10,
                        'changes_start': 14,
                        'changes_len': 4,
                    },
                },
            ])

    def test_with_multiple_chunks(self):
        """Testing get_diff_data_chunks_info with multiple chunks in a diff"""
        self.assertEqual(
            get_diff_data_chunks_info(
                b'@@ -10,7 +12,10 @@\n'
                b' #\n'
                b' #\n'
                b' #\n'
                b'-# old line\n'
                b'+# new line\n'
                b'+# new line\n'
                b'+# new line\n'
                b'+# new line\n'
                b' #\n'
                b' #\n'
                b' #\n'
                b'@@ -23,7 +40,7 @@\n'
                b' #\n'
                b' #\n'
                b' #\n'
                b'-# old line\n'
                b'+# new line\n'
                b' #\n'
                b' #\n'
                b' #\n'),
            [
                {
                    'orig': {
                        'pre_lines_of_context': 3,
                        'post_lines_of_context': 3,
                        'chunk_start': 9,
                        'chunk_len': 7,
                        'changes_start': 12,
                        'changes_len': 1,
                    },
                    'modified': {
                        'pre_lines_of_context': 3,
                        'post_lines_of_context': 3,
                        'chunk_start': 11,
                        'chunk_len': 10,
                        'changes_start': 14,
                        'changes_len': 4,
                    },
                },
                {
                    'orig': {
                        'pre_lines_of_context': 3,
                        'post_lines_of_context': 3,
                        'chunk_start': 22,
                        'chunk_len': 7,
                        'changes_start': 25,
                        'changes_len': 1,
                    },
                    'modified': {
                        'pre_lines_of_context': 3,
                        'post_lines_of_context': 3,
                        'chunk_start': 39,
                        'chunk_len': 7,
                        'changes_start': 42,
                        'changes_len': 1,
                    },
                },
            ])

    def test_with_multiple_chunks_no_context(self):
        """Testing get_diff_data_chunks_info with multiple chunks and no
        context
        """
        self.assertEqual(
            get_diff_data_chunks_info(
                b'@@ -13,1 +15,4 @@\n'
                b'-# old line\n'
                b'+# new line\n'
                b'+# new line\n'
                b'+# new line\n'
                b'+# new line\n'
                b'@@ -26,1 +43,1 @@\n'
                b'-# old line\n'
                b'+# new line\n'),
            [
                {
                    'orig': {
                        'pre_lines_of_context': 0,
                        'post_lines_of_context': 0,
                        'chunk_start': 12,
                        'chunk_len': 1,
                        'changes_start': 12,
                        'changes_len': 1,
                    },
                    'modified': {
                        'pre_lines_of_context': 0,
                        'post_lines_of_context': 0,
                        'chunk_start': 14,
                        'chunk_len': 4,
                        'changes_start': 14,
                        'changes_len': 4,
                    },
                },
                {
                    'orig': {
                        'pre_lines_of_context': 0,
                        'post_lines_of_context': 0,
                        'chunk_start': 25,
                        'chunk_len': 1,
                        'changes_start': 25,
                        'changes_len': 1,
                    },
                    'modified': {
                        'pre_lines_of_context': 0,
                        'post_lines_of_context': 0,
                        'chunk_start': 42,
                        'chunk_len': 1,
                        'changes_start': 42,
                        'changes_len': 1,
                    },
                },
            ])

    def test_with_all_inserts(self):
        """Testing get_diff_data_chunks_info with all inserts"""
        self.assertEqual(
            get_diff_data_chunks_info(
                b'@@ -10,6 +12,10 @@\n'
                b' #\n'
                b' #\n'
                b' #\n'
                b'+# new line\n'
                b'+# new line\n'
                b'+# new line\n'
                b'+# new line\n'
                b' #\n'
                b' #\n'
                b' #\n'),
            [
                {
                    'orig': {
                        'pre_lines_of_context': 6,
                        'post_lines_of_context': 0,
                        'chunk_start': 9,
                        'chunk_len': 6,
                        'changes_start': 9,
                        'changes_len': 0,
                    },
                    'modified': {
                        'pre_lines_of_context': 3,
                        'post_lines_of_context': 3,
                        'chunk_start': 11,
                        'chunk_len': 10,
                        'changes_start': 14,
                        'changes_len': 4,
                    },
                },
            ])

    def test_with_all_deletes(self):
        """Testing get_diff_data_chunks_info with all deletes"""
        self.assertEqual(
            get_diff_data_chunks_info(
                b'@@ -10,10 +12,6 @@\n'
                b' #\n'
                b' #\n'
                b' #\n'
                b'-# old line\n'
                b'-# old line\n'
                b'-# old line\n'
                b'-# old line\n'
                b' #\n'
                b' #\n'
                b' #\n'),
            [
                {
                    'orig': {
                        'pre_lines_of_context': 3,
                        'post_lines_of_context': 3,
                        'chunk_start': 9,
                        'chunk_len': 10,
                        'changes_start': 12,
                        'changes_len': 4,
                    },
                    'modified': {
                        'pre_lines_of_context': 6,
                        'post_lines_of_context': 0,
                        'chunk_start': 11,
                        'chunk_len': 6,
                        'changes_start': 11,
                        'changes_len': 0,
                    },
                },
            ])

    def test_with_complex_chunk(self):
        """Testing get_diff_data_chunks_info with complex chunk containing
        inserts, deletes, and equals
        """
        self.assertEqual(
            get_diff_data_chunks_info(
                b'@@ -10,9 +12,12 @@\n'
                b' #\n'
                b' #\n'
                b' #\n'
                b'+# new line\n'
                b' #\n'
                b'-# old line\n'
                b'+# new line\n'
                b'+# new line\n'
                b' #\n'
                b'+# new line\n'
                b' #\n'
                b' #\n'
                b' #\n'),
            [
                {
                    'orig': {
                        'pre_lines_of_context': 4,
                        'post_lines_of_context': 4,
                        'chunk_start': 9,
                        'chunk_len': 9,
                        'changes_start': 13,
                        'changes_len': 1,
                    },
                    'modified': {
                        'pre_lines_of_context': 3,
                        'post_lines_of_context': 3,
                        'chunk_start': 11,
                        'chunk_len': 12,
                        'changes_start': 14,
                        'changes_len': 6,
                    },
                },
            ])

    def test_with_change_on_first_line(self):
        """Testing get_diff_data_chunks_info with change on first line"""
        self.assertEqual(
            get_diff_data_chunks_info(
                b'@@ -1,4 +1,5 @@\n'
                b'-# old line\n'
                b'+# new line\n'
                b'+# new line\n'
                b' #\n'
                b' #\n'
                b' #\n'),
            [
                {
                    'orig': {
                        'pre_lines_of_context': 0,
                        'post_lines_of_context': 3,
                        'chunk_start': 0,
                        'chunk_len': 4,
                        'changes_start': 0,
                        'changes_len': 1,
                    },
                    'modified': {
                        'pre_lines_of_context': 0,
                        'post_lines_of_context': 3,
                        'chunk_start': 0,
                        'chunk_len': 5,
                        'changes_start': 0,
                        'changes_len': 2,
                    },
                },
            ])

    def test_with_change_on_second_line(self):
        """Testing get_diff_data_chunks_info with change on second line"""
        self.assertEqual(
            get_diff_data_chunks_info(
                b'@@ -1,5 +1,6 @@\n'
                b' #\n'
                b'-# old line\n'
                b'+# new line\n'
                b'+# new line\n'
                b' #\n'
                b' #\n'
                b' #\n'),
            [
                {
                    'orig': {
                        'pre_lines_of_context': 1,
                        'post_lines_of_context': 3,
                        'chunk_start': 0,
                        'chunk_len': 5,
                        'changes_start': 1,
                        'changes_len': 1,
                    },
                    'modified': {
                        'pre_lines_of_context': 1,
                        'post_lines_of_context': 3,
                        'chunk_start': 0,
                        'chunk_len': 6,
                        'changes_start': 1,
                        'changes_len': 2,
                    },
                },
            ])

    def test_with_change_on_third_line(self):
        """Testing get_diff_data_chunks_info with change on third line"""
        self.assertEqual(
            get_diff_data_chunks_info(
                b'@@ -1,6 +1,7 @@\n'
                b' #\n'
                b' #\n'
                b'-# old line\n'
                b'+# new line\n'
                b'+# new line\n'
                b' #\n'
                b' #\n'
                b' #\n'),
            [
                {
                    'orig': {
                        'pre_lines_of_context': 2,
                        'post_lines_of_context': 3,
                        'chunk_start': 0,
                        'chunk_len': 6,
                        'changes_start': 2,
                        'changes_len': 1,
                    },
                    'modified': {
                        'pre_lines_of_context': 2,
                        'post_lines_of_context': 3,
                        'chunk_start': 0,
                        'chunk_len': 7,
                        'changes_start': 2,
                        'changes_len': 2,
                    },
                },
            ])

    def test_with_single_line_replace(self):
        """Testing get_diff_data_chunks_info with single-line diff with
        replaced line
        """
        self.assertEqual(
            get_diff_data_chunks_info(
                b'@@ -1,1 +1,1 @@\n'
                b'-# old line\n'
                b'+# new line\n'),
            [
                {
                    'orig': {
                        'pre_lines_of_context': 0,
                        'post_lines_of_context': 0,
                        'chunk_start': 0,
                        'chunk_len': 1,
                        'changes_start': 0,
                        'changes_len': 1,
                    },
                    'modified': {
                        'pre_lines_of_context': 0,
                        'post_lines_of_context': 0,
                        'chunk_start': 0,
                        'chunk_len': 1,
                        'changes_start': 0,
                        'changes_len': 1,
                    },
                },
            ])

    def test_with_insert_before_only_line(self):
        """Testing get_diff_data_chunks_info with insert before only line
        in diff
        """
        self.assertEqual(
            get_diff_data_chunks_info(
                b'@@ -1,1 +1,2 @@\n'
                b'+# new line\n'
                b' #\n'),
            [
                {
                    'orig': {
                        'pre_lines_of_context': 1,
                        'post_lines_of_context': 0,
                        'chunk_start': 0,
                        'chunk_len': 1,
                        'changes_start': 0,
                        'changes_len': 0,
                    },
                    'modified': {
                        'pre_lines_of_context': 0,
                        'post_lines_of_context': 1,
                        'chunk_start': 0,
                        'chunk_len': 2,
                        'changes_start': 0,
                        'changes_len': 1,
                    },
                },
            ])

    def test_with_no_lengths(self):
        """Testing get_diff_data_chunks_info with no lengths specified"""
        self.assertEqual(
            get_diff_data_chunks_info(
                b'@@ -1 +1 @@\n'
                b'-# old line\n'
                b'+# new line\n'),
            [
                {
                    'orig': {
                        'pre_lines_of_context': 0,
                        'post_lines_of_context': 0,
                        'chunk_start': 0,
                        'chunk_len': 1,
                        'changes_start': 0,
                        'changes_len': 1,
                    },
                    'modified': {
                        'pre_lines_of_context': 0,
                        'post_lines_of_context': 0,
                        'chunk_start': 0,
                        'chunk_len': 1,
                        'changes_start': 0,
                        'changes_len': 1,
                    },
                },
            ])

    def test_with_header_context(self):
        """Testing get_diff_data_chunks_info with class/functino context
        shown in the header
        """
        self.assertEqual(
            get_diff_data_chunks_info(
                b'@@ -10,7 +12,10 @@ def foo(self):\n'
                b' #\n'
                b' #\n'
                b' #\n'
                b'-# old line\n'
                b'+# new line\n'
                b'+# new line\n'
                b'+# new line\n'
                b'+# new line\n'
                b' #\n'
                b' #\n'
                b' #\n'),
            [
                {
                    'orig': {
                        'pre_lines_of_context': 3,
                        'post_lines_of_context': 3,
                        'chunk_start': 9,
                        'chunk_len': 7,
                        'changes_start': 12,
                        'changes_len': 1,
                    },
                    'modified': {
                        'pre_lines_of_context': 3,
                        'post_lines_of_context': 3,
                        'chunk_start': 11,
                        'chunk_len': 10,
                        'changes_start': 14,
                        'changes_len': 4,
                    },
                },
            ])


class GetDiffFilesTests(BaseFileDiffAncestorTests):
    """Unit tests for get_diff_files."""

    fixtures = [
        'test_users',
    ] + BaseFileDiffAncestorTests.fixtures

    def test_interdiff_when_renaming_twice(self):
        """Testing get_diff_files with interdiff when renaming twice"""
        repository = self.create_repository(tool_name='Git')
        review_request = self.create_review_request(repository=repository)

        one_to_two = (b'diff --git a/foo.txt b/foo.txt\n'
                      b'deleted file mode 100644\n'
                      b'index 092beec..0000000\n'
                      b'--- a/foo.txt\n'
                      b'+++ /dev/null\n'
                      b'@@ -1,2 +0,0 @@\n'
                      b'-This is foo!\n'
                      b'-=]\n'
                      b'diff --git a/foo2.txt b/foo2.txt\n'
                      b'new file mode 100644\n'
                      b'index 0000000..092beec\n'
                      b'--- /dev/null\n'
                      b'+++ b/foo2.txt\n'
                      b'@@ -0,0 +1,2 @@\n'
                      b'+This is foo!\n'
                      b'+=]\n')
        one_to_three = (b'diff --git a/foo.txt b/foo.txt\n'
                        b'deleted file mode 100644\n'
                        b'index 092beec..0000000\n'
                        b'--- a/foo.txt\n'
                        b'+++ /dev/null\n'
                        b'@@ -1,2 +0,0 @@\n'
                        b'-This is foo!\n'
                        b'-=]\n'
                        b'diff --git a/foo3.txt b/foo3.txt\n'
                        b'new file mode 100644\n'
                        b'index 0000000..092beec\n'
                        b'--- /dev/null\n'
                        b'+++ b/foo3.txt\n'
                        b'@@ -0,0 +1,2 @@\n'
                        b'+This is foo!\n'
                        b'+=]\n')

        diffset = self.create_diffset(review_request=review_request)
        self.create_filediff(diffset=diffset, source_file='foo.txt',
                             dest_file='foo2.txt', status=FileDiff.MODIFIED,
                             diff=one_to_two)

        interdiffset = self.create_diffset(review_request=review_request)
        self.create_filediff(diffset=interdiffset, source_file='foo.txt',
                             dest_file='foo3.txt', status=FileDiff.MODIFIED,
                             diff=one_to_three)

        diff_files = get_diff_files(diffset=diffset, interdiffset=interdiffset)
        two_to_three = diff_files[0]

        self.assertEqual(two_to_three['depot_filename'], 'foo2.txt')
        self.assertEqual(two_to_three['dest_filename'], 'foo3.txt')

    def test_get_diff_files_with_interdiff_and_files_same_source(self):
        """Testing get_diff_files with interdiff and multiple files using the
        same source_file
        """
        repository = self.create_repository(tool_name='Git')
        review_request = self.create_review_request(repository=repository)

        diffset = self.create_diffset(review_request=review_request,
                                      revision=1)

        # This one should be reverted, as it has no counterpart in the
        # interdiff.
        filediff1 = self.create_filediff(
            diffset=diffset,
            source_file='foo.txt',
            source_revision=123,
            dest_file='foo.txt',
            dest_detail='124',
            diff=b'diff1')

        # This one should match up with interfilediff1.
        filediff2 = self.create_filediff(
            diffset=diffset,
            source_file='foo.txt',
            source_revision=123,
            dest_file='foo2.txt',
            dest_detail='124',
            status=FileDiff.COPIED,
            diff=b'diff2')

        # This one should be reverted, as it has no counterpart in the
        # interdiff.
        filediff3 = self.create_filediff(
            diffset=diffset,
            source_file='foo.txt',
            source_revision=123,
            dest_file='foo3.txt',
            dest_detail='124',
            status=FileDiff.COPIED,
            diff=b'diff3')

        # This one should match up with interfilediff3 and interfilediff4.
        filediff4 = self.create_filediff(
            diffset=diffset,
            source_file='foo4.txt',
            source_revision=123,
            dest_file='foo4.txt',
            dest_detail='124',
            diff=b'diff4')

        interdiffset = self.create_diffset(review_request=review_request,
                                           revision=2)

        # This one should match up with filediff2.
        interfilediff1 = self.create_filediff(
            diffset=interdiffset,
            source_file='foo.txt',
            source_revision=123,
            dest_file='foo2.txt',
            dest_detail='124',
            status=FileDiff.COPIED,
            diff=b'interdiff1')

        # This one should show up as a new file.
        interfilediff2 = self.create_filediff(
            diffset=interdiffset,
            source_file='foo.txt',
            source_revision=PRE_CREATION,
            dest_file='foo.txt',
            dest_detail='125',
            diff=b'interdiff2')

        # This one should match up with filediff4.
        interfilediff3 = self.create_filediff(
            diffset=interdiffset,
            source_file='foo4.txt',
            source_revision=123,
            dest_file='foo5.txt',
            dest_detail='124',
            diff=b'interdiff2')

        # This one should match up with filediff4 as well.
        interfilediff4 = self.create_filediff(
            diffset=interdiffset,
            source_file='foo4.txt',
            source_revision=123,
            dest_file='foo6.txt',
            dest_detail='124',
            diff=b'interdiff3')

        diff_files = get_diff_files(diffset=diffset,
                                    interdiffset=interdiffset)
        self.assertEqual(len(diff_files), 6)

        diff_file = diff_files[0]
        self.assertEqual(diff_file['depot_filename'], 'foo.txt')
        self.assertEqual(diff_file['dest_filename'], 'foo.txt')
        self.assertEqual(diff_file['filediff'], filediff1)
        self.assertEqual(diff_file['interfilediff'], None)
        self.assertEqual(diff_file['revision'], 'Diff Revision 1')
        self.assertEqual(diff_file['dest_revision'],
                         'Diff Revision 2 - File Reverted')
        self.assertFalse(diff_file['is_new_file'])
        self.assertTrue(diff_file['force_interdiff'])

        diff_file = diff_files[1]
        self.assertEqual(diff_file['depot_filename'], 'foo.txt')
        self.assertEqual(diff_file['dest_filename'], 'foo.txt')
        self.assertEqual(diff_file['filediff'], interfilediff2)
        self.assertEqual(diff_file['interfilediff'], None)
        self.assertEqual(diff_file['revision'], 'Diff Revision 1')
        self.assertEqual(diff_file['dest_revision'], 'New File')
        self.assertTrue(diff_file['is_new_file'])
        self.assertFalse(diff_file['force_interdiff'])

        diff_file = diff_files[2]
        self.assertEqual(diff_file['depot_filename'], 'foo2.txt')
        self.assertEqual(diff_file['dest_filename'], 'foo2.txt')
        self.assertEqual(diff_file['filediff'], filediff2)
        self.assertEqual(diff_file['interfilediff'], interfilediff1)
        self.assertEqual(diff_file['revision'], 'Diff Revision 1')
        self.assertEqual(diff_file['dest_revision'], 'Diff Revision 2')
        self.assertFalse(diff_file['is_new_file'])
        self.assertTrue(diff_file['force_interdiff'])

        diff_file = diff_files[3]
        self.assertEqual(diff_file['depot_filename'], 'foo.txt')
        self.assertEqual(diff_file['dest_filename'], 'foo3.txt')
        self.assertEqual(diff_file['filediff'], filediff3)
        self.assertEqual(diff_file['interfilediff'], None)
        self.assertEqual(diff_file['revision'], 'Diff Revision 1')
        self.assertEqual(diff_file['dest_revision'],
                         'Diff Revision 2 - File Reverted')
        self.assertFalse(diff_file['is_new_file'])
        self.assertTrue(diff_file['force_interdiff'])

        diff_file = diff_files[4]
        self.assertEqual(diff_file['depot_filename'], 'foo4.txt')
        self.assertEqual(diff_file['dest_filename'], 'foo5.txt')
        self.assertEqual(diff_file['filediff'], filediff4)
        self.assertEqual(diff_file['interfilediff'], interfilediff3)
        self.assertEqual(diff_file['revision'], 'Diff Revision 1')
        self.assertEqual(diff_file['dest_revision'], 'Diff Revision 2')
        self.assertFalse(diff_file['is_new_file'])
        self.assertTrue(diff_file['force_interdiff'])

        diff_file = diff_files[5]
        self.assertEqual(diff_file['depot_filename'], 'foo4.txt')
        self.assertEqual(diff_file['dest_filename'], 'foo6.txt')
        self.assertEqual(diff_file['filediff'], filediff4)
        self.assertEqual(diff_file['interfilediff'], interfilediff4)
        self.assertEqual(diff_file['revision'], 'Diff Revision 1')
        self.assertEqual(diff_file['dest_revision'], 'Diff Revision 2')
        self.assertFalse(diff_file['is_new_file'])
        self.assertTrue(diff_file['force_interdiff'])

    def test_get_diff_files_with_interdiff_using_filediff_only(self):
        """Testing get_diff_files with interdiff using filediff but no
        interfilediff
        """
        repository = self.create_repository(tool_name='Git')
        review_request = self.create_review_request(repository=repository)

        diffset = self.create_diffset(review_request=review_request,
                                      revision=1)

        filediff = self.create_filediff(
            diffset=diffset,
            source_file='foo.txt',
            source_revision=123,
            dest_file='foo.txt',
            diff=b'diff1')

        self.create_filediff(
            diffset=diffset,
            source_file='foo.txt',
            source_revision=123,
            dest_file='foo2.txt',
            status=FileDiff.COPIED,
            diff=b'diff2')

        interdiffset = self.create_diffset(review_request=review_request,
                                           revision=2)

        self.create_filediff(
            diffset=interdiffset,
            source_file='foo.txt',
            source_revision=123,
            dest_file='foo.txt',
            status=FileDiff.COPIED,
            diff=b'interdiff1')

        self.create_filediff(
            diffset=interdiffset,
            source_file='foo.txt',
            source_revision=123,
            dest_file='foo2.txt',
            status=FileDiff.COPIED,
            diff=b'interdiff2')

        diff_files = get_diff_files(diffset=diffset,
                                    interdiffset=interdiffset,
                                    filediff=filediff)
        self.assertEqual(len(diff_files), 1)

        diff_file = diff_files[0]
        self.assertEqual(diff_file['depot_filename'], 'foo.txt')
        self.assertEqual(diff_file['dest_filename'], 'foo.txt')
        self.assertEqual(diff_file['filediff'], filediff)
        self.assertEqual(diff_file['interfilediff'], None)
        self.assertEqual(diff_file['revision'], 'Diff Revision 1')
        self.assertEqual(diff_file['dest_revision'],
                         'Diff Revision 2 - File Reverted')
        self.assertFalse(diff_file['is_new_file'])
        self.assertTrue(diff_file['force_interdiff'])

    def test_get_diff_files_with_interdiff_using_both_filediffs(self):
        """Testing get_diff_files with interdiff using filediff and
        interfilediff
        """
        repository = self.create_repository(tool_name='Git')
        review_request = self.create_review_request(repository=repository)

        diffset = self.create_diffset(review_request=review_request,
                                      revision=1)

        filediff = self.create_filediff(
            diffset=diffset,
            source_file='foo.txt',
            source_revision=123,
            dest_file='foo.txt',
            diff=b'diff1')

        self.create_filediff(
            diffset=diffset,
            source_file='foo.txt',
            source_revision=123,
            dest_file='foo2.txt',
            status=FileDiff.COPIED,
            diff=b'diff2')

        interdiffset = self.create_diffset(review_request=review_request,
                                           revision=2)

        interfilediff = self.create_filediff(
            diffset=interdiffset,
            source_file='foo.txt',
            source_revision=123,
            dest_file='foo.txt',
            status=FileDiff.COPIED,
            diff=b'interdiff1')

        self.create_filediff(
            diffset=interdiffset,
            source_file='foo.txt',
            source_revision=123,
            dest_file='foo2.txt',
            status=FileDiff.COPIED,
            diff=b'interdiff2')

        diff_files = get_diff_files(diffset=diffset,
                                    interdiffset=interdiffset,
                                    filediff=filediff,
                                    interfilediff=interfilediff)
        self.assertEqual(len(diff_files), 1)

        diff_file = diff_files[0]
        self.assertEqual(diff_file['depot_filename'], 'foo.txt')
        self.assertEqual(diff_file['dest_filename'], 'foo.txt')
        self.assertEqual(diff_file['filediff'], filediff)
        self.assertEqual(diff_file['interfilediff'], interfilediff)
        self.assertEqual(diff_file['revision'], 'Diff Revision 1')
        self.assertEqual(diff_file['dest_revision'], 'Diff Revision 2')
        self.assertFalse(diff_file['is_new_file'])
        self.assertTrue(diff_file['force_interdiff'])

    def test_get_diff_files_history(self):
        """Testing get_diff_files for a diffset with history"""
        self.set_up_filediffs()

        review_request = self.create_review_request(repository=self.repository,
                                                    create_with_history=True)
        review_request.diffset_history.diffsets = [self.diffset]

        result = get_diff_files(diffset=self.diffset)

        self.assertEqual(len(result), len(self.diffset.cumulative_files))

        self.assertEqual(
            [diff_file['filediff'].pk for diff_file in result],
            [
                filediff.pk
                for filediff in get_sorted_filediffs(
                    self.diffset.cumulative_files)
            ])

        for diff_file in result:
            filediff = diff_file['filediff']
            print('Current filediff is: ', filediff)

            self.assertIsNone(diff_file['base_filediff'])

    def test_with_diff_files_history_query_count(self):
        """Testing get_diff_files query count for a diffset with history"""
        self.set_up_filediffs()

        review_request = self.create_review_request(repository=self.repository,
                                                    create_with_history=True)
        review_request.diffset_history.diffsets = [self.diffset]

        # Expecting 1 query:
        #
        # 1. Select all FileDiffs for a DiffSet.
        with self.assertNumQueries(1):
            get_diff_files(diffset=self.diffset)

    def test_get_diff_files_history_query_count_ancestors_precomputed(self):
        """Testing get_diff_files query count for a whole diffset with history
        when ancestors have been computed
        """
        self.set_up_filediffs()

        review_request = self.create_review_request(repository=self.repository,
                                                    create_with_history=True)
        review_request.diffset_history.diffsets = [self.diffset]

        for filediff in self.filediffs:
            filediff.get_ancestors(minimal=False, filediffs=self.filediffs)

        # Expecting 1 query:
        #
        # 1. Select all FileDiffs for a DiffSet.
        with self.assertNumQueries(1):
            get_diff_files(diffset=self.diffset)

    def test_get_diff_files_query_count_filediff(self):
        """Testing get_diff_files for a single FileDiff with history"""
        self.set_up_filediffs()

        review_request = self.create_review_request(repository=self.repository,
                                                    create_with_history=True)
        review_request.diffset_history.diffsets = [self.diffset]

        by_details = self.get_filediffs_by_details()
        filediff = by_details[(
            3, 'foo', '257cc56', 'qux', '03b37a0',
        )]

        with self.assertNumQueries(4):
            files = get_diff_files(diffset=self.diffset,
                                   filediff=filediff)

        self.assertEqual(len(files), 1)
        f = files[0]

        self.assertEqual(f['filediff'], filediff)
        self.assertIsNone(f['base_filediff'])

    def test_get_diff_files_query_count_filediff_ancestors_precomupted(self):
        """Testing get_diff_files query count for a single FileDiff with
        history when ancestors are precomputed
        """
        self.set_up_filediffs()

        review_request = self.create_review_request(repository=self.repository,
                                                    create_with_history=True)
        review_request.diffset_history.diffsets = [self.diffset]

        by_details = self.get_filediffs_by_details()

        for f in self.filediffs:
            f.get_ancestors(minimal=False, filediffs=self.filediffs)

        filediff = by_details[(
            3, 'foo', '257cc56', 'qux', '03b37a0',
        )]

        with self.assertNumQueries(1):
            files = get_diff_files(diffset=self.diffset,
                                   filediff=filediff)

        self.assertEqual(len(files), 1)
        f = files[0]

        self.assertEqual(f['filediff'], filediff)
        self.assertIsNone(f['base_filediff'])

    def test_get_diff_files_with_history_base_commit(self):
        """Testing get_diff_files for a whole diffset with history with a
        specified base commit ID
        """
        self.set_up_filediffs()

        review_request = self.create_review_request(repository=self.repository,
                                                    create_with_history=True)
        review_request.diffset_history.diffsets = [self.diffset]

        diff_commit = DiffCommit.objects.get(pk=2)

        # Sanity-check how many FileDiffs we're working with, for the query
        # assertion.
        self.assertEqual(len(self.filediffs), 9)

        # Expecting 9 queries:
        #
        # 1. Select all FileDiffs for a DiffSet.
        # 2. Update extra_data on FileDiff id=1.
        # 3. Update extra_data on FileDiff id=3.
        # 4. Update extra_data on FileDiff id=6.
        # 5. Update extra_data on FileDiff id=7.
        # 6. Update extra_data on FileDiff id=2.
        # 7. Update extra_data on FileDiff id=5.
        # 8. Update extra_data on FileDiff id=8.
        # 9. Update extra_data on FileDiff id=9.
        with self.assertNumQueries(9):
            files = get_diff_files(diffset=self.diffset,
                                   base_commit=diff_commit)

        expected_results = self._get_filediff_base_mapping_from_details(
            self.get_filediffs_by_details(),
            [
                (
                    (4, 'bar', '5716ca5', 'quux', 'e69de29'),
                    (2, 'bar', '8e739cc', 'bar', '0000000'),
                ),
                (
                    (3, 'corge', 'e69de29', 'corge', 'f248ba3'),
                    None,
                ),
                (
                    (3, 'foo', '257cc56', 'qux', '03b37a0'),
                    (2, 'foo', 'e69de29', 'foo', '257cc56'),
                ),
            ])

        results = {
            f['filediff']: f['base_filediff']
            for f in files
        }

        self.assertEqual(results, expected_results)

    def test_get_diff_files_with_history_base_commit_as_latest(self):
        """Testing get_diff_files for a whole diffset with history with a
        specified base commit as the latest commit
        """
        self.set_up_filediffs()

        review_request = self.create_review_request(repository=self.repository,
                                                    create_with_history=True)
        review_request.diffset_history.diffsets = [self.diffset]

        files = get_diff_files(diffset=self.diffset,
                               base_commit=DiffCommit.objects.get(pk=4))

        self.assertEqual(files, [])

    def test_get_diff_files_with_history_tip_commit(self):
        """Testing get_diff_files for a whole diffset with history with a
        specified tip commit
        """
        self.set_up_filediffs()

        review_request = self.create_review_request(repository=self.repository,
                                                    create_with_history=True)
        review_request.diffset_history.diffsets = [self.diffset]

        tip_commit = DiffCommit.objects.get(pk=3)

        # Sanity-check how many FileDiffs we're working with, for the query
        # assertion.
        self.assertEqual(len(self.filediffs), 9)

        # Expecting 9 queries:
        #
        # 1. Select all FileDiffs for a DiffSet.
        # 2. Update extra_data on FileDiff id=1.
        # 3. Update extra_data on FileDiff id=3.
        # 4. Update extra_data on FileDiff id=6.
        # 5. Update extra_data on FileDiff id=7.
        # 6. Update extra_data on FileDiff id=2.
        # 7. Update extra_data on FileDiff id=5.
        # 8. Update extra_data on FileDiff id=8.
        # 9. Update extra_data on FileDiff id=9.
        with self.assertNumQueries(9):
            files = get_diff_files(diffset=self.diffset,
                                   tip_commit=tip_commit)

        expected_results = self._get_filediff_base_mapping_from_details(
            self.get_filediffs_by_details(),
            [
                (
                    (3, 'foo', '257cc56', 'qux', '03b37a0'),
                    None,
                ),
                (
                    (2, 'baz', '7601807', 'baz', '280beb2'),
                    None,
                ),
                (
                    (3, 'corge', 'e69de29', 'corge', 'f248ba3'),
                    None,
                ),
                (
                    (3, 'bar', 'PRE-CREATION', 'bar', '5716ca5'),
                    None,
                ),
            ])

        results = {
            f['filediff']: f['base_filediff']
            for f in files
        }

        self.assertEqual(results, expected_results)

    def test_get_diff_files_with_history_tip_commit_precomputed(self):
        """Testing get_diff_files for a whole diffset with history with a
        specified tip commit when ancestors have been precomputed
        """
        self.set_up_filediffs()

        review_request = self.create_review_request(repository=self.repository,
                                                    create_with_history=True)
        review_request.diffset_history.diffsets = [self.diffset]

        for f in self.filediffs:
            f.get_ancestors(minimal=False, filediffs=self.filediffs)

        tip_commit = DiffCommit.objects.get(pk=3)

        # Expecting 1 query:
        #
        # 1. Select all FileDiffs for a DiffSet.
        with self.assertNumQueries(1):
            files = get_diff_files(diffset=self.diffset,
                                   tip_commit=tip_commit)

        expected_results = self._get_filediff_base_mapping_from_details(
            self.get_filediffs_by_details(),
            [
                (
                    (3, 'foo', '257cc56', 'qux', '03b37a0'),
                    None,
                ),
                (
                    (2, 'baz', '7601807', 'baz', '280beb2'),
                    None,
                ),
                (
                    (3, 'corge', 'e69de29', 'corge', 'f248ba3'),
                    None,
                ),
                (
                    (3, 'bar', 'PRE-CREATION', 'bar', '5716ca5'),
                    None,
                ),
            ])

        results = {
            f['filediff']: f['base_filediff']
            for f in files
        }

        self.assertEqual(results, expected_results)

    def test_get_diff_files_with_history_base_tip(self):
        """Testing get_diff_files for a whole diffset with history with a
        specified base and tip commit
        """
        self.set_up_filediffs()

        review_request = self.create_review_request(repository=self.repository,
                                                    create_with_history=True)
        review_request.diffset_history.diffsets = [self.diffset]

        commits = DiffCommit.objects.in_bulk([2, 3])
        base_commit = commits[2]
        tip_commit = commits[3]

        # Sanity-check how many FileDiffs we're working with, for the query
        # assertion.
        self.assertEqual(len(self.filediffs), 9)

        # Expecting 8 queries:
        #
        # 1. Select all FileDiffs for a DiffSet.
        # 2. Update extra_data on FileDiff id=1.
        # 3. Update extra_data on FileDiff id=3.
        # 4. Update extra_data on FileDiff id=6.
        # 5. Update extra_data on FileDiff id=7.
        # 6. Update extra_data on FileDiff id=2.
        # 7. Update extra_data on FileDiff id=5.
        # 8. Update extra_data on FileDiff id=8.
        with self.assertNumQueries(8):
            files = get_diff_files(diffset=self.diffset,
                                   base_commit=base_commit,
                                   tip_commit=tip_commit)

        expected_results = self._get_filediff_base_mapping_from_details(
            self.get_filediffs_by_details(),
            [
                (
                    (3, 'foo', '257cc56', 'qux', '03b37a0'),
                    (2, 'foo', 'e69de29', 'foo', '257cc56'),
                ),
                (
                    (3, 'corge', 'e69de29', 'corge', 'f248ba3'),
                    None,
                ),
                (
                    (3, 'bar', 'PRE-CREATION', 'bar', '5716ca5'),
                    (2, 'bar', '8e739cc', 'bar', '0000000'),
                ),
            ])

        results = {
            f['filediff']: f['base_filediff']
            for f in files
        }

        self.assertEqual(results, expected_results)

    def test_get_diff_files_with_history_base_tip_ancestors_precomputed(self):
        """Testing get_diff_files for a whole diffset with history with a
        specified base and tip commit when ancestors are precomputed
        """
        self.set_up_filediffs()

        review_request = self.create_review_request(repository=self.repository,
                                                    create_with_history=True)
        review_request.diffset_history.diffsets = [self.diffset]

        for f in self.filediffs:
            f.get_ancestors(minimal=False, filediffs=self.filediffs)

        commits = DiffCommit.objects.in_bulk([2, 3])
        base_commit = commits[2]
        tip_commit = commits[3]

        # Expecting 1 query:
        #
        # 1. Select all FileDiffs for a DiffSet.
        with self.assertNumQueries(1):
            files = get_diff_files(diffset=self.diffset,
                                   base_commit=base_commit,
                                   tip_commit=tip_commit)

        expected_results = self._get_filediff_base_mapping_from_details(
            self.get_filediffs_by_details(),
            [

                (
                    (3, 'foo', '257cc56', 'qux', '03b37a0'),
                    (2, 'foo', 'e69de29', 'foo', '257cc56'),
                ),
                (
                    (3, 'corge', 'e69de29', 'corge', 'f248ba3'),
                    None,
                ),
                (
                    (3, 'bar', 'PRE-CREATION', 'bar', '5716ca5'),
                    (2, 'bar', '8e739cc', 'bar', '0000000'),
                ),
            ])

        results = {
            f['filediff']: f['base_filediff']
            for f in files
        }

        self.assertEqual(results, expected_results)

    def _get_filediff_base_mapping_from_details(self, by_details, details):
        """Return a mapping from FileDiffs to base FileDiffs from the details.

        Args:
            by_details (dict):
                A mapping of FileDiff details to FileDiffs, as returned from
                :py:meth:`BaseFileDiffAncestorTests.get_filediffs_by_details`.

            details (list):
                A list of the details in the form of:

                .. code-block:: python

                   [
                       (filediff_1_details, parent_1_details),
                       (filediff_2_details, parent_2_details),
                   ]

                where each set of details is either ``None`` or a 5-tuple of:

                - :py:attr`FileDiff.commit_id`
                - :py:attr`FileDiff.source_file`
                - :py:attr`FileDiff.source_revision`
                - :py:attr`FileDiff.dest_file`
                - :py:attr`FileDiff.dest_detail`

        Returns:
            dict:
            A mapping of the FileDiffs to their base FileDiffs (or ``None`` if
            there is no base FileDiff).
        """
        return {
            by_details[filediff_details]:
                by_details.get(base_filediff_details)
            for filediff_details, base_filediff_details in details
        }

    @add_fixtures(['test_users', 'test_scmtools'])
    def test_get_diff_files_filename_normalization_extra_data(self):
        """Testing that filename normalization from get_diff_files receives
        FileDiff extra_data
        """
        repository = self.create_repository(tool_name='Git')
        review_request = self.create_review_request(repository=repository)

        diffset = self.create_diffset(review_request=review_request,
                                      revision=1)

        filediff = self.create_filediff(
            diffset=diffset,
            source_file='foo.txt',
            source_revision=123,
            dest_file='foo.txt',
            diff=b'diff1')
        filediff.extra_data['test'] = True

        tool_class = repository.scmtool_class
        self.spy_on(tool_class.normalize_path_for_display,
                    owner=tool_class)

        get_diff_files(diffset=diffset, filediff=filediff)

        self.assertSpyCalledWith(tool_class.normalize_path_for_display,
                                 'foo.txt', extra_data={'test': True})


class GetFileDiffsMatchTests(TestCase):
    """Unit tests for get_filediffs_match."""

    fixtures = ['test_scmtools', 'test_users']

    def setUp(self):
        super(GetFileDiffsMatchTests, self).setUp()

        review_request = self.create_review_request(create_repository=True)
        self.diffset = self.create_diffset(review_request)

    def test_with_filediff_none(self):
        """Testing get_filediffs_match with either filediff as None"""
        filediff = self.create_filediff(self.diffset, save=False)

        self.assertFalse(get_filediffs_match(filediff, None))
        self.assertFalse(get_filediffs_match(None, filediff))

        message = 'filediff1 and filediff2 cannot both be None'

        with self.assertRaisesMessage(ValueError, message):
            self.assertFalse(get_filediffs_match(None, None))

    def test_with_diffs_equal(self):
        """Testing get_filediffs_match with diffs equal"""
        filediff1 = self.create_filediff(self.diffset,
                                         diff=b'abc',
                                         save=False)
        filediff2 = self.create_filediff(self.diffset,
                                         diff=b'abc',
                                         save=False)

        self.assertTrue(get_filediffs_match(filediff1, filediff2))

    def test_with_deleted_true(self):
        """Testing get_filediffs_match with deleted flags both set"""
        self.assertTrue(get_filediffs_match(
            self.create_filediff(self.diffset,
                                 diff=b'abc',
                                 status=FileDiff.DELETED,
                                 save=False),
            self.create_filediff(self.diffset,
                                 diff=b'def',
                                 status=FileDiff.DELETED,
                                 save=False)))

    def test_with_sha256_equal(self):
        """Testing get_filediffs_match with patched SHA256 hashes equal"""
        filediff1 = self.create_filediff(self.diffset,
                                         diff=b'abc',
                                         save=False)
        filediff2 = self.create_filediff(self.diffset,
                                         diff=b'def',
                                         save=False)

        filediff1.extra_data['patched_sha256'] = 'abc123'
        filediff2.extra_data['patched_sha256'] = 'abc123'

        self.assertTrue(get_filediffs_match(filediff1, filediff2))

    def test_with_sha1_equal(self):
        """Testing get_filediffs_match with patched SHA1 hashes equal"""
        filediff1 = self.create_filediff(self.diffset,
                                         diff=b'abc',
                                         save=False)
        filediff2 = self.create_filediff(self.diffset,
                                         diff=b'def',
                                         save=False)

        filediff1.extra_data['patched_sha1'] = 'abc123'
        filediff2.extra_data['patched_sha1'] = 'abc123'

        self.assertTrue(get_filediffs_match(filediff1, filediff2))

    def test_with_sha1_not_equal(self):
        """Testing get_filediffs_match with patched SHA1 hashes not equal"""
        filediff1 = self.create_filediff(self.diffset,
                                         diff=b'abc',
                                         save=False)
        filediff2 = self.create_filediff(self.diffset,
                                         diff=b'def',
                                         save=False)

        filediff1.extra_data['patched_sha1'] = 'abc123'
        filediff2.extra_data['patched_sha1'] = 'def456'

        self.assertFalse(get_filediffs_match(filediff1, filediff2))

    def test_with_sha256_not_equal_and_sha1_equal(self):
        """Testing get_filediffs_match with patched SHA256 hashes not equal
        and patched SHA1 hashes equal
        """
        filediff1 = self.create_filediff(self.diffset,
                                         diff=b'abc',
                                         save=False)
        filediff2 = self.create_filediff(self.diffset,
                                         diff=b'def',
                                         save=False)

        filediff1.extra_data.update({
            'patched_sha256': 'abc123',
            'patched_sha1': 'abcdef',
        })
        filediff2.extra_data.update({
            'patched_sha256': 'def456',
            'patched_sha1': 'abcdef',
        })

        self.assertFalse(get_filediffs_match(filediff1, filediff2))


class GetMatchedInterdiffFilesTests(TestCase):
    """Unit tests for get_matched_interdiff_files."""

    @add_fixtures(['test_users', 'test_scmtools'])
    def test_with_simple_matches(self):
        """Testing get_matched_interdiff_files with simple source file matches
        """
        repository = self.create_repository(tool_name='Git')
        review_request = self.create_review_request(repository=repository)

        diffset = self.create_diffset(review_request=review_request,
                                      revision=1)

        filediff1 = self.create_filediff(
            diffset=diffset,
            source_file='foo.txt',
            source_revision=123,
            dest_file='foo.txt',
            diff=b'diff1')

        filediff2 = self.create_filediff(
            diffset=diffset,
            source_file='foo2.txt',
            source_revision=123,
            dest_file='foo2.txt',
            diff=b'diff2')

        interdiffset = self.create_diffset(review_request=review_request,
                                           revision=2)

        interfilediff1 = self.create_filediff(
            diffset=interdiffset,
            source_file='foo.txt',
            source_revision=123,
            dest_file='foo.txt',
            diff=b'interdiff1')

        interfilediff2 = self.create_filediff(
            diffset=interdiffset,
            source_file='foo2.txt',
            source_revision=123,
            dest_file='foo2.txt',
            diff=b'interdiff2')

        matched_files = get_matched_interdiff_files(
            tool=repository.get_scmtool(),
            filediffs=[filediff1, filediff2],
            interfilediffs=[interfilediff1, interfilediff2])

        self.assertEqual(
            list(matched_files),
            [
                (filediff1, interfilediff1),
                (filediff2, interfilediff2),
            ])

    @add_fixtures(['test_users', 'test_scmtools'])
    def test_with_new_added_file_left(self):
        """Testing get_matched_interdiff_files with new added file on left
        side only
        """
        repository = self.create_repository(tool_name='Git')
        review_request = self.create_review_request(repository=repository)

        diffset = self.create_diffset(review_request=review_request,
                                      revision=1)

        filediff1 = self.create_filediff(
            diffset=diffset,
            source_file='foo.txt',
            source_revision=123,
            dest_file='foo.txt',
            diff=b'diff1')

        filediff2 = self.create_filediff(
            diffset=diffset,
            source_file='foo2.txt',
            source_revision=PRE_CREATION,
            dest_file='foo2.txt',
            diff=b'diff2')

        interdiffset = self.create_diffset(review_request=review_request,
                                           revision=2)

        interfilediff1 = self.create_filediff(
            diffset=interdiffset,
            source_file='foo.txt',
            source_revision=123,
            dest_file='foo.txt',
            diff=b'interdiff1')

        matched_files = get_matched_interdiff_files(
            tool=repository.get_scmtool(),
            filediffs=[filediff1, filediff2],
            interfilediffs=[interfilediff1])

        self.assertEqual(
            list(matched_files),
            [
                (filediff1, interfilediff1),
                (filediff2, None),
            ])

    @add_fixtures(['test_users', 'test_scmtools'])
    def test_with_new_added_file_right(self):
        """Testing get_matched_interdiff_files with new added file on right
        side only
        """
        repository = self.create_repository(tool_name='Git')
        review_request = self.create_review_request(repository=repository)

        diffset = self.create_diffset(review_request=review_request,
                                      revision=1)

        filediff1 = self.create_filediff(
            diffset=diffset,
            source_file='foo.txt',
            source_revision=123,
            dest_file='foo.txt',
            diff=b'diff1')

        interdiffset = self.create_diffset(review_request=review_request,
                                           revision=2)

        interfilediff1 = self.create_filediff(
            diffset=interdiffset,
            source_file='foo.txt',
            source_revision=123,
            dest_file='foo.txt',
            diff=b'interdiff1')

        interfilediff2 = self.create_filediff(
            diffset=interdiffset,
            source_file='foo2.txt',
            source_revision=PRE_CREATION,
            dest_file='foo2.txt',
            diff=b'interdiff2')

        matched_files = get_matched_interdiff_files(
            tool=repository.get_scmtool(),
            filediffs=[filediff1],
            interfilediffs=[interfilediff1, interfilediff2])

        self.assertEqual(
            list(matched_files),
            [
                (filediff1, interfilediff1),
                (None, interfilediff2),
            ])

    @add_fixtures(['test_users', 'test_scmtools'])
    def test_with_new_added_file_both(self):
        """Testing get_matched_interdiff_files with new added file on both
        sides
        """
        repository = self.create_repository(tool_name='Git')
        review_request = self.create_review_request(repository=repository)

        diffset = self.create_diffset(review_request=review_request,
                                      revision=1)

        filediff1 = self.create_filediff(
            diffset=diffset,
            source_file='foo.txt',
            source_revision=123,
            dest_file='foo.txt',
            diff=b'diff1')

        filediff2 = self.create_filediff(
            diffset=diffset,
            source_file='foo2.txt',
            source_revision=PRE_CREATION,
            dest_file='foo2.txt',
            diff=b'diff2')

        interdiffset = self.create_diffset(review_request=review_request,
                                           revision=2)

        interfilediff1 = self.create_filediff(
            diffset=interdiffset,
            source_file='foo.txt',
            source_revision=123,
            dest_file='foo.txt',
            diff=b'interdiff1')

        interfilediff2 = self.create_filediff(
            diffset=interdiffset,
            source_file='foo2.txt',
            source_revision=PRE_CREATION,
            dest_file='foo2.txt',
            diff=b'interdiff2')

        matched_files = get_matched_interdiff_files(
            tool=repository.get_scmtool(),
            filediffs=[filediff1, filediff2],
            interfilediffs=[interfilediff1, interfilediff2])

        self.assertEqual(
            list(matched_files),
            [
                (filediff1, interfilediff1),
                (filediff2, interfilediff2),
            ])

    @add_fixtures(['test_users', 'test_scmtools'])
    def test_with_new_deleted_file_left(self):
        """Testing get_matched_interdiff_files with new deleted file on left
        side only
        """
        repository = self.create_repository(tool_name='Git')
        review_request = self.create_review_request(repository=repository)

        diffset = self.create_diffset(review_request=review_request,
                                      revision=1)

        filediff1 = self.create_filediff(
            diffset=diffset,
            source_file='foo.txt',
            source_revision=123,
            dest_file='foo.txt',
            diff=b'diff1')

        filediff2 = self.create_filediff(
            diffset=diffset,
            source_file='foo2.txt',
            source_revision=123,
            dest_file='foo2.txt',
            status=FileDiff.DELETED,
            diff=b'diff2')

        interdiffset = self.create_diffset(review_request=review_request,
                                           revision=2)

        interfilediff1 = self.create_filediff(
            diffset=interdiffset,
            source_file='foo.txt',
            source_revision=123,
            dest_file='foo.txt',
            diff=b'interdiff1')

        matched_files = get_matched_interdiff_files(
            tool=repository.get_scmtool(),
            filediffs=[filediff1, filediff2],
            interfilediffs=[interfilediff1])

        self.assertEqual(
            list(matched_files),
            [
                (filediff1, interfilediff1),
                (filediff2, None),
            ])

    @add_fixtures(['test_users', 'test_scmtools'])
    def test_with_new_deleted_file_right(self):
        """Testing get_matched_interdiff_files with new deleted file on right
        side only
        """
        repository = self.create_repository(tool_name='Git')
        review_request = self.create_review_request(repository=repository)

        diffset = self.create_diffset(review_request=review_request,
                                      revision=1)

        filediff1 = self.create_filediff(
            diffset=diffset,
            source_file='foo.txt',
            source_revision=123,
            dest_file='foo.txt',
            diff=b'diff1')

        interdiffset = self.create_diffset(review_request=review_request,
                                           revision=2)

        interfilediff1 = self.create_filediff(
            diffset=interdiffset,
            source_file='foo.txt',
            source_revision=123,
            dest_file='foo.txt',
            diff=b'interdiff1')

        interfilediff2 = self.create_filediff(
            diffset=interdiffset,
            source_file='foo2.txt',
            source_revision=123,
            dest_file='foo2.txt',
            status=FileDiff.DELETED,
            diff=b'interdiff2')

        matched_files = get_matched_interdiff_files(
            tool=repository.get_scmtool(),
            filediffs=[filediff1],
            interfilediffs=[interfilediff1, interfilediff2])

        self.assertEqual(
            list(matched_files),
            [
                (filediff1, interfilediff1),
                (None, interfilediff2),
            ])

    @add_fixtures(['test_users', 'test_scmtools'])
    def test_with_new_deleted_file_both(self):
        """Testing get_matched_interdiff_files with new deleted file on both
        sides
        """
        repository = self.create_repository(tool_name='Git')
        review_request = self.create_review_request(repository=repository)

        diffset = self.create_diffset(review_request=review_request,
                                      revision=1)

        filediff1 = self.create_filediff(
            diffset=diffset,
            source_file='foo.txt',
            source_revision=123,
            dest_file='foo.txt',
            diff=b'diff1')

        filediff2 = self.create_filediff(
            diffset=diffset,
            source_file='foo2.txt',
            source_revision=123,
            dest_file='foo2.txt',
            status=FileDiff.DELETED,
            diff=b'diff2')

        interdiffset = self.create_diffset(review_request=review_request,
                                           revision=2)

        interfilediff1 = self.create_filediff(
            diffset=interdiffset,
            source_file='foo.txt',
            source_revision=123,
            dest_file='foo.txt',
            diff=b'interdiff1')

        interfilediff2 = self.create_filediff(
            diffset=interdiffset,
            source_file='foo2.txt',
            source_revision=123,
            dest_file='foo2.txt',
            status=FileDiff.DELETED,
            diff=b'interdiff2')

        matched_files = get_matched_interdiff_files(
            tool=repository.get_scmtool(),
            filediffs=[filediff1, filediff2],
            interfilediffs=[interfilediff1, interfilediff2])

        self.assertEqual(
            list(matched_files),
            [
                (filediff1, interfilediff1),
                (filediff2, interfilediff2),
            ])

    @add_fixtures(['test_users', 'test_scmtools'])
    def test_with_new_modified_file_right(self):
        """Testing get_matched_interdiff_files with new modified file on
        right side
        """
        repository = self.create_repository(tool_name='Git')
        review_request = self.create_review_request(repository=repository)

        diffset = self.create_diffset(review_request=review_request,
                                      revision=1)

        filediff1 = self.create_filediff(
            diffset=diffset,
            source_file='foo.txt',
            source_revision=123,
            dest_file='foo.txt',
            diff=b'diff1')

        interdiffset = self.create_diffset(review_request=review_request,
                                           revision=2)

        interfilediff1 = self.create_filediff(
            diffset=interdiffset,
            source_file='foo.txt',
            source_revision=123,
            dest_file='foo.txt',
            diff=b'interdiff1')

        interfilediff2 = self.create_filediff(
            diffset=interdiffset,
            source_file='foo2.txt',
            source_revision=123,
            dest_file='foo2.txt',
            diff=b'interdiff2')

        matched_files = get_matched_interdiff_files(
            tool=repository.get_scmtool(),
            filediffs=[filediff1],
            interfilediffs=[interfilediff1, interfilediff2])

        self.assertEqual(
            list(matched_files),
            [
                (filediff1, interfilediff1),
                (None, interfilediff2),
            ])

    @add_fixtures(['test_users', 'test_scmtools'])
    def test_with_reverted_file(self):
        """Testing get_matched_interdiff_files with reverted file"""
        repository = self.create_repository(tool_name='Git')
        review_request = self.create_review_request(repository=repository)

        diffset = self.create_diffset(review_request=review_request,
                                      revision=1)

        filediff1 = self.create_filediff(
            diffset=diffset,
            source_file='foo.txt',
            source_revision=123,
            dest_file='foo.txt',
            diff=b'diff1')

        filediff2 = self.create_filediff(
            diffset=diffset,
            source_file='foo2.txt',
            source_revision=123,
            dest_file='foo2.txt',
            diff=b'diff2')

        interdiffset = self.create_diffset(review_request=review_request,
                                           revision=2)

        interfilediff1 = self.create_filediff(
            diffset=interdiffset,
            source_file='foo.txt',
            source_revision=123,
            dest_file='foo.txt',
            diff=b'interdiff1')

        matched_files = get_matched_interdiff_files(
            tool=repository.get_scmtool(),
            filediffs=[filediff1, filediff2],
            interfilediffs=[interfilediff1])

        self.assertEqual(
            list(matched_files),
            [
                (filediff1, interfilediff1),
                (filediff2, None),
            ])

    @add_fixtures(['test_users', 'test_scmtools'])
    def test_with_both_renames(self):
        """Testing get_matched_interdiff_files with matching renames on both
        sides
        """
        repository = self.create_repository(tool_name='Git')
        review_request = self.create_review_request(repository=repository)

        diffset = self.create_diffset(review_request=review_request,
                                      revision=1)

        filediff1 = self.create_filediff(
            diffset=diffset,
            source_file='foo.txt',
            source_revision=123,
            dest_file='foo.txt',
            diff=b'diff1')

        filediff2 = self.create_filediff(
            diffset=diffset,
            source_file='foo.txt',
            source_revision=123,
            dest_file='foo2.txt',
            diff=b'diff2')

        interdiffset = self.create_diffset(review_request=review_request,
                                           revision=2)

        interfilediff1 = self.create_filediff(
            diffset=interdiffset,
            source_file='foo.txt',
            source_revision=123,
            dest_file='foo.txt',
            diff=b'interdiff1')

        interfilediff2 = self.create_filediff(
            diffset=interdiffset,
            source_file='foo.txt',
            source_revision=123,
            dest_file='foo2.txt',
            diff=b'interdiff2')

        matched_files = get_matched_interdiff_files(
            tool=repository.get_scmtool(),
            filediffs=[filediff1, filediff2],
            interfilediffs=[interfilediff1, interfilediff2])

        self.assertEqual(
            list(matched_files),
            [
                (filediff1, interfilediff1),
                (filediff2, interfilediff2),
            ])

    @add_fixtures(['test_users', 'test_scmtools'])
    def test_with_new_renames(self):
        """Testing get_matched_interdiff_files with modified on left side,
        modified + renamed on right
        """
        repository = self.create_repository(tool_name='Git')
        review_request = self.create_review_request(repository=repository)

        diffset = self.create_diffset(review_request=review_request,
                                      revision=1)

        filediff1 = self.create_filediff(
            diffset=diffset,
            source_file='foo.txt',
            source_revision=123,
            dest_file='foo.txt',
            diff=b'diff1')

        filediff2 = self.create_filediff(
            diffset=diffset,
            source_file='foo2.txt',
            source_revision=123,
            dest_file='foo2.txt',
            diff=b'diff2')

        interdiffset = self.create_diffset(review_request=review_request,
                                           revision=2)

        interfilediff1 = self.create_filediff(
            diffset=interdiffset,
            source_file='foo.txt',
            source_revision=123,
            dest_file='foo.txt',
            diff=b'interdiff1')

        interfilediff2 = self.create_filediff(
            diffset=interdiffset,
            source_file='foo2.txt',
            source_revision=123,
            dest_file='foo3.txt',
            diff=b'interdiff2')

        matched_files = get_matched_interdiff_files(
            tool=repository.get_scmtool(),
            filediffs=[filediff1, filediff2],
            interfilediffs=[interfilediff1, interfilediff2])

        self.assertEqual(
            list(matched_files),
            [
                (filediff1, interfilediff1),
                (filediff2, interfilediff2),
            ])

    @add_fixtures(['test_users', 'test_scmtools'])
    def test_with_multiple_copies(self):
        """Testing get_matched_interdiff_files with multiple copies of file
        from left on right
        """
        repository = self.create_repository(tool_name='Git')
        review_request = self.create_review_request(repository=repository)

        diffset = self.create_diffset(review_request=review_request,
                                      revision=1)

        filediff1 = self.create_filediff(
            diffset=diffset,
            source_file='foo.txt',
            source_revision=123,
            dest_file='foo.txt',
            diff=b'diff1')

        filediff2 = self.create_filediff(
            diffset=diffset,
            source_file='foo2.txt',
            source_revision=123,
            dest_file='foo2.txt',
            diff=b'diff2')

        interdiffset = self.create_diffset(review_request=review_request,
                                           revision=2)

        interfilediff1 = self.create_filediff(
            diffset=interdiffset,
            source_file='foo.txt',
            source_revision=123,
            dest_file='foo.txt',
            diff=b'interdiff1')

        interfilediff2 = self.create_filediff(
            diffset=interdiffset,
            source_file='foo2.txt',
            source_revision=123,
            dest_file='foo3.txt',
            diff=b'interdiff2')

        interfilediff3 = self.create_filediff(
            diffset=interdiffset,
            source_file='foo2.txt',
            source_revision=123,
            dest_file='foo4.txt',
            diff=b'interdiff3')

        matched_files = get_matched_interdiff_files(
            tool=repository.get_scmtool(),
            filediffs=[filediff1, filediff2],
            interfilediffs=[interfilediff1, interfilediff2, interfilediff3])

        self.assertEqual(
            list(matched_files),
            [
                (filediff1, interfilediff1),
                (filediff2, interfilediff2),
                (filediff2, interfilediff3),
            ])

    @add_fixtures(['test_users', 'test_scmtools'])
    def test_with_added_left_only(self):
        """Testing get_matched_interdiff_files with file added in left only"""
        repository = self.create_repository(tool_name='Git')
        review_request = self.create_review_request(repository=repository)

        diffset = self.create_diffset(review_request=review_request,
                                      revision=1)

        filediff1 = self.create_filediff(
            diffset=diffset,
            source_file='foo.txt',
            source_revision=PRE_CREATION,
            dest_file='foo.txt',
            dest_detail='124',
            diff=b'diff1')

        filediff2 = self.create_filediff(
            diffset=diffset,
            source_file='foo2.txt',
            source_revision=123,
            dest_file='foo2.txt',
            dest_detail='124',
            diff=b'diff2')

        interdiffset = self.create_diffset(review_request=review_request,
                                           revision=2)

        interfilediff1 = self.create_filediff(
            diffset=interdiffset,
            source_file='foo.txt',
            source_revision=123,
            dest_file='foo.txt',
            dest_detail='124',
            diff=b'interdiff1')

        interfilediff2 = self.create_filediff(
            diffset=interdiffset,
            source_file='foo2.txt',
            source_revision=PRE_CREATION,
            dest_file='foo3.txt',
            dest_detail='125',
            diff=b'interdiff2')

        matched_files = get_matched_interdiff_files(
            tool=repository.get_scmtool(),
            filediffs=[filediff1, filediff2],
            interfilediffs=[interfilediff1, interfilediff2])

        self.assertEqual(
            list(matched_files),
            [
                (filediff1, interfilediff1),
                (filediff2, None),
                (None, interfilediff2),
            ])

    @add_fixtures(['test_users', 'test_scmtools'])
    def test_with_deleted_right_only(self):
        """Testing get_matched_interdiff_files with file deleted in right only
        """
        repository = self.create_repository(tool_name='Git')
        review_request = self.create_review_request(repository=repository)

        diffset = self.create_diffset(review_request=review_request,
                                      revision=1)

        filediff1 = self.create_filediff(
            diffset=diffset,
            source_file='foo.txt',
            source_revision='123',
            dest_file='foo.txt',
            diff=b'diff1')

        filediff2 = self.create_filediff(
            diffset=diffset,
            source_file='foo2.txt',
            source_revision=123,
            dest_file='foo2.txt',
            status=FileDiff.DELETED,
            diff=b'diff2')

        interdiffset = self.create_diffset(review_request=review_request,
                                           revision=2)

        interfilediff1 = self.create_filediff(
            diffset=interdiffset,
            source_file='foo.txt',
            source_revision=123,
            dest_file='foo.txt',
            status=FileDiff.DELETED,
            diff=b'interdiff1')

        interfilediff2 = self.create_filediff(
            diffset=interdiffset,
            source_file='foo2.txt',
            source_revision=123,
            dest_file='foo3.txt',
            diff=b'interdiff2')

        matched_files = get_matched_interdiff_files(
            tool=repository.get_scmtool(),
            filediffs=[filediff1, filediff2],
            interfilediffs=[interfilediff1, interfilediff2])

        self.assertEqual(
            list(matched_files),
            [
                (filediff1, interfilediff1),
                (filediff2, None),
                (None, interfilediff2),
            ])

    @add_fixtures(['test_users', 'test_scmtools'])
    def test_with_same_names_multiple_ops(self):
        """Testing get_matched_interdiff_files with same names and multiple
        operation (pathological case)
        """
        repository = self.create_repository(tool_name='Git')
        review_request = self.create_review_request(repository=repository)

        diffset = self.create_diffset(review_request=review_request,
                                      revision=1)

        filediff1 = self.create_filediff(
            diffset=diffset,
            source_file='foo.txt',
            source_revision=PRE_CREATION,
            dest_file='foo.txt',
            diff=b'diff1')

        filediff2 = self.create_filediff(
            diffset=diffset,
            source_file='foo.txt',
            source_revision=123,
            dest_file='foo.txt',
            diff=b'diff2')

        filediff3 = self.create_filediff(
            diffset=diffset,
            source_file='foo.txt',
            source_revision=123,
            dest_file='foo2.txt',
            diff=b'diff3')

        filediff4 = self.create_filediff(
            diffset=diffset,
            source_file='foo.txt',
            source_revision=123,
            dest_file='foo.txt',
            status=FileDiff.DELETED,
            diff=b'diff1')

        interdiffset = self.create_diffset(review_request=review_request,
                                           revision=2)

        interfilediff1 = self.create_filediff(
            diffset=interdiffset,
            source_file='foo.txt',
            source_revision=123,
            dest_file='foo3.txt',
            diff=b'interdiff1')

        interfilediff2 = self.create_filediff(
            diffset=interdiffset,
            source_file='foo.txt',
            source_revision=123,
            dest_file='foo2.txt',
            diff=b'interdiff2')

        interfilediff3 = self.create_filediff(
            diffset=interdiffset,
            source_file='foo.txt',
            source_revision=123,
            dest_file='foo3.txt',
            diff=b'interdiff3')

        interfilediff4 = self.create_filediff(
            diffset=interdiffset,
            source_file='foo.txt',
            source_revision=123,
            dest_file='foo.txt',
            status=FileDiff.DELETED,
            diff=b'interdiff4')

        interfilediff5 = self.create_filediff(
            diffset=interdiffset,
            source_file='foo.txt',
            source_revision=PRE_CREATION,
            dest_file='foo.txt',
            diff=b'interdiff5')

        matched_files = get_matched_interdiff_files(
            tool=repository.get_scmtool(),
            filediffs=[filediff1, filediff2, filediff3, filediff4],
            interfilediffs=[interfilediff1, interfilediff2, interfilediff3,
                            interfilediff4, interfilediff5])

        self.assertEqual(
            list(matched_files),
            [
                (filediff1, interfilediff5),
                (filediff3, interfilediff2),
                (filediff4, interfilediff4),
                (filediff2, interfilediff1),
                (filediff2, interfilediff3),
            ])

    @add_fixtures(['test_users', 'test_scmtools'])
    def test_with_new_file_same_name(self):
        """Testing get_matched_interdiff_files with new file on right with
        same name from left
        """
        repository = self.create_repository(tool_name='Git')
        review_request = self.create_review_request(repository=repository)

        diffset = self.create_diffset(review_request=review_request,
                                      revision=1)
        interdiffset = self.create_diffset(review_request=review_request,
                                           revision=2)

        # Modified in revision 1 and in revision 2. Match.
        filediff1 = self.create_filediff(
            diffset=diffset,
            source_file='foo.txt',
            source_revision=123,
            dest_file='foo.txt',
            dest_detail='124',
            diff=b'diff1')

        interfilediff1 = self.create_filediff(
            diffset=interdiffset,
            source_file='foo.txt',
            source_revision=123,
            dest_file='foo.txt',
            dest_detail='124',
            diff=b'interdiff1')

        # Modified in revision 1. Re-created in revision 2 with the same
        # revision (implying an edge case where the file was deleted in a
        # parent diff and re-introduced in the main diff, turning into what
        # looks like a modification in the FileDiff).
        filediff2 = self.create_filediff(
            diffset=diffset,
            source_file='foo2.txt',
            source_revision=123,
            dest_file='foo2.txt',
            dest_detail='124',
            diff=b'diff2')

        interfilediff2 = self.create_filediff(
            diffset=interdiffset,
            source_file='foo2.txt',
            source_revision=PRE_CREATION,
            dest_file='foo2.txt',
            dest_detail='124',
            diff=b'interdiff2')

        # Modified in revision 1. Re-created in revision 2 with a new revision
        # (implying it was deleted upstream).
        filediff3 = self.create_filediff(
            diffset=diffset,
            source_file='foo3.txt',
            source_revision=123,
            dest_file='foo3.txt',
            dest_detail='124',
            diff=b'diff3')

        interfilediff3 = self.create_filediff(
            diffset=interdiffset,
            source_file='foo3.txt',
            source_revision=PRE_CREATION,
            dest_file='foo3.txt',
            dest_detail='125',
            diff=b'interdiff3')

        matched_files = get_matched_interdiff_files(
            tool=repository.get_scmtool(),
            filediffs=[filediff1, filediff2, filediff3],
            interfilediffs=[interfilediff1, interfilediff2, interfilediff3])

        self.assertEqual(
            list(matched_files),
            [
                (filediff1, interfilediff1),
                (filediff2, interfilediff2),
                (filediff3, None),
                (None, interfilediff3),
            ])


class GetLineChangedRegionsTests(TestCase):
    """Unit tests for get_line_changed_regions."""

    def test_get_line_changed_regions(self):
        """Testing get_line_changed_regions"""
        def deep_equal(A, B):
            typea, typeb = type(A), type(B)
            self.assertEqual(typea, typeb)

            if typea is tuple or typea is list:
                for a, b in zip_longest(A, B):
                    deep_equal(a, b)
            else:
                self.assertEqual(A, B)

        deep_equal(get_line_changed_regions(None, None),
                   (None, None))

        old = 'submitter = models.ForeignKey(Person, verbose_name="Submitter")'
        new = 'submitter = models.ForeignKey(User, verbose_name="Submitter")'
        regions = get_line_changed_regions(old, new)
        deep_equal(regions, ([(30, 36)], [(30, 34)]))

        old = '-from reviews.models import ReviewRequest, Person, Group'
        new = '+from .reviews.models import ReviewRequest, Group'
        regions = get_line_changed_regions(old, new)
        deep_equal(regions, ([(0, 1), (6, 6), (43, 51)],
                             [(0, 1), (6, 7), (44, 44)]))

        old = 'abcdefghijklm'
        new = 'nopqrstuvwxyz'
        regions = get_line_changed_regions(old, new)
        deep_equal(regions, (None, None))


class GetDisplayedDiffLineRangesTests(TestCase):
    """Unit tests for get_displayed_diff_line_ranges."""

    def test_with_delete_single_lines(self):
        """Testing get_displayed_diff_line_ranges with delete chunk and single
        virtual line
        """
        chunks = [
            {
                'change': 'delete',
                'lines': [
                    (10, 20, 'deleted line', [], '', '', [], False),
                    # ...
                    (50, 60, 'deleted line', [], '', '', [], False),
                ],
            },
        ]

        self.assertEqual(
            get_displayed_diff_line_ranges(chunks, 20, 20),
            ({
                'display_range': (30, 30),
                'virtual_range': (20, 20),
                'chunk_range': (chunks[0], chunks[0]),
            }, None))

    def test_with_delete_mutiple_lines(self):
        """Testing get_displayed_diff_line_ranges with delete chunk and multiple
        virtual lines
        """
        chunks = [
            {
                'change': 'delete',
                'lines': [
                    (10, 20, 'deleted line', [], '', '', [], False),
                    # ...
                    (50, 60, 'deleted line', [], '', '', [], False),
                ],
            },
        ]

        self.assertEqual(
            get_displayed_diff_line_ranges(chunks, 20, 21),
            ({
                'display_range': (30, 31),
                'virtual_range': (20, 21),
                'chunk_range': (chunks[0], chunks[0]),
            }, None))

    def test_with_replace_single_line(self):
        """Testing get_displayed_diff_line_ranges with replace chunk and single
        virtual line
        """
        chunks = [
            {
                'change': 'replace',
                'lines': [
                    (10, 20, 'foo', [], 30, 'replaced line', [], False),
                    # ...
                    (50, 60, 'foo', [], 70, 'replaced line', [], False),
                ],
            },
        ]

        self.assertEqual(
            get_displayed_diff_line_ranges(chunks, 20, 20),
            ({
                'display_range': (30, 30),
                'virtual_range': (20, 20),
                'chunk_range': (chunks[0], chunks[0]),
            }, {
                'display_range': (40, 40),
                'virtual_range': (20, 20),
                'chunk_range': (chunks[0], chunks[0]),
            }))

    def test_with_replace_multiple_lines(self):
        """Testing get_displayed_diff_line_ranges with replace chunk and
        multiple virtual lines
        """
        chunks = [
            {
                'change': 'replace',
                'lines': [
                    (10, 20, 'foo', [], 30, 'replaced line', [], False),
                    # ...
                    (50, 60, 'foo', [], 70, 'replaced line', [], False),
                ],
            },
        ]

        self.assertEqual(
            get_displayed_diff_line_ranges(chunks, 20, 21),
            ({
                'display_range': (30, 31),
                'virtual_range': (20, 21),
                'chunk_range': (chunks[0], chunks[0]),
            }, {
                'display_range': (40, 41),
                'virtual_range': (20, 21),
                'chunk_range': (chunks[0], chunks[0]),
            }))

    def test_with_insert_single_line(self):
        """Testing get_displayed_diff_line_ranges with insert chunk and single
        virtual line
        """
        chunks = [
            {
                'change': 'insert',
                'lines': [
                    (10, '', '', [], 20, 'inserted line', [], False),
                    # ...
                    (50, '', '', [], 60, 'inserted line', [], False),
                ],
            },
        ]

        self.assertEqual(
            get_displayed_diff_line_ranges(chunks, 20, 20),
            (None, {
                'display_range': (30, 30),
                'virtual_range': (20, 20),
                'chunk_range': (chunks[0], chunks[0]),
            }))

    def test_with_insert_multiple_lines(self):
        """Testing get_displayed_diff_line_ranges with insert chunk and multiple
        virtual lines
        """
        chunks = [
            {
                'change': 'insert',
                'lines': [
                    (10, '', '', [], 20, 'inserted line', [], False),
                    # ...
                    (50, '', '', [], 60, 'inserted line', [], False),
                ],
            },
        ]

        self.assertEqual(
            get_displayed_diff_line_ranges(chunks, 20, 21),
            (None, {
                'display_range': (30, 31),
                'virtual_range': (20, 21),
                'chunk_range': (chunks[0], chunks[0]),
            }))

    def test_with_fake_equal_orig(self):
        """Testing get_displayed_diff_line_ranges with fake equal from
        original side of interdiff
        """
        chunks = [
            {
                'change': 'equal',
                'lines': [
                    (10, '', '', [], 20, 'inserted line', [], False),
                    # ...
                    (50, '', '', [], 60, 'inserted line', [], False),
                ],
            },
        ]

        self.assertEqual(
            get_displayed_diff_line_ranges(chunks, 20, 21),
            (None, {
                'display_range': (30, 31),
                'virtual_range': (20, 21),
                'chunk_range': (chunks[0], chunks[0]),
            }))

    def test_with_fake_equal_patched(self):
        """Testing get_displayed_diff_line_ranges with fake equal from
        patched side of interdiff
        """
        chunks = [
            {
                'change': 'equal',
                'lines': [
                    (10, 20, 'deleted line', [], '', '', [], False),
                    # ...
                    (50, 60, 'deleted line', [], '', '', [], False),
                ],
            },
        ]

        self.assertEqual(
            get_displayed_diff_line_ranges(chunks, 20, 21),
            ({
                'display_range': (30, 31),
                'virtual_range': (20, 21),
                'chunk_range': (chunks[0], chunks[0]),
            }, None))

    def test_with_spanning_insert_delete(self):
        """Testing get_displayed_diff_line_ranges with spanning delete and
        insert
        """
        chunks = [
            {
                'change': 'delete',
                'lines': [
                    (10, 20, 'deleted line', [], '', '', [], False),
                    # ...
                    (50, 60, 'deleted line', [], '', '', [], False),
                ],
            },
            {
                'change': 'insert',
                'lines': [
                    (51, '', '', [], 61, 'inserted line', [], False),
                    # ...
                    (100, '', '', [], 110, 'inserted line', [], False),
                ],
            },
            {
                'change': 'equal',
                'lines': [
                    (101, 61, 'equal line', [], 111, 'equal line', [],
                     False),
                    # ...
                    (200, 160, 'equal line', [], 210, 'equal line', [],
                     False),
                ],
            },
        ]

        self.assertEqual(
            get_displayed_diff_line_ranges(chunks, 20, 69),
            ({
                'display_range': (30, 60),
                'virtual_range': (20, 50),
                'chunk_range': (chunks[0], chunks[0]),
            }, {
                'display_range': (61, 79),
                'virtual_range': (51, 69),
                'chunk_range': (chunks[1], chunks[1]),
            }))

    def test_with_spanning_delete_insert(self):
        """Testing get_displayed_diff_line_ranges with spanning insert and
        delete
        """
        chunks = [
            {
                'change': 'insert',
                'lines': [
                    (10, '', '', [], 20, 'inserted line', [], False),
                    # ...
                    (50, '', '', [], 60, 'inserted line', [], False),
                ],
            },
            {
                'change': 'delete',
                'lines': [
                    (51, 61, 'inserted line', [], '', '', [], False),
                    # ...
                    (100, 110, 'inserted line', [], '', '', [], False),
                ],
            },
            {
                'change': 'equal',
                'lines': [
                    (101, 111, 'equal line', [], 61, 'equal line', [],
                     False),
                    # ...
                    (200, 210, 'equal line', [], 160, 'equal line', [],
                     False),
                ],
            },
        ]

        self.assertEqual(
            get_displayed_diff_line_ranges(chunks, 20, 69),
            ({
                'display_range': (61, 79),
                'virtual_range': (51, 69),
                'chunk_range': (chunks[1], chunks[1]),
            }, {
                'display_range': (30, 60),
                'virtual_range': (20, 50),
                'chunk_range': (chunks[0], chunks[0]),
            }))

    def test_with_spanning_last_chunk(self):
        """Testing get_displayed_diff_line_ranges with spanning chunks through
        last chunk
        """
        chunks = [
            {
                'change': 'delete',
                'lines': [
                    (10, 20, 'deleted line', [], '', '', [], False),
                    # ...
                    (50, 60, 'deleted line', [], '', '', [], False),
                ],
            },
            {
                'change': 'insert',
                'lines': [
                    (51, '', '', [], 61, 'inserted line', [], False),
                    # ...
                    (100, '', '', [], 110, 'inserted line', [], False),
                ],
            },
        ]

        self.assertEqual(
            get_displayed_diff_line_ranges(chunks, 20, 69),
            ({
                'display_range': (30, 60),
                'virtual_range': (20, 50),
                'chunk_range': (chunks[0], chunks[0]),
            }, {
                'display_range': (61, 79),
                'virtual_range': (51, 69),
                'chunk_range': (chunks[1], chunks[1]),
            }))


class DiffExpansionHeaderTests(TestCase):
    """Testing generation of diff expansion headers."""

    def test_find_header_with_filtered_equal(self):
        """Testing finding a header in a file that has filtered equals
        chunks
        """
        # See diffviewer.diffutils.get_file_chunks_in_range for a description
        # of chunks and its elements. We fake the elements of lines here
        # because we only need elements 0, 1, and 4 (of what would be a list).
        chunks = [
            {
                'change': 'equal',
                'meta': {
                    'left_headers': [(1, 'foo')],
                    'right_headers': [],
                },
                'lines': [
                    {
                        0: 1,
                        1: 1,
                        4: '',
                    },
                    {
                        0: 2,
                        1: 2,
                        4: 1,
                    },
                ]
            },
            {
                'change': 'equal',
                'meta': {
                    'left_headers': [],
                    'right_headers': [(2, 'bar')],
                },
                'lines': [
                    {
                        0: 3,
                        1: '',
                        4: 2,
                    },
                    {
                        0: 4,
                        1: 3,
                        4: 3,
                    },
                ]
            }
        ]

        left_header = {
            'line': 1,
            'text': 'foo',
        }
        right_header = {
            'line': 3,
            'text': 'bar',
        }

        self.assertEqual(
            _get_last_header_in_chunks_before_line(chunks, 2),
            {
                'left': left_header,
                'right': None,
            })

        self.assertEqual(
            _get_last_header_in_chunks_before_line(chunks, 4),
            {
                'left': left_header,
                'right': right_header,
            })

    def test_find_header_with_header_oustside_chunk(self):
        """Testing finding a header in a file where the header in a chunk does
        not belong to the chunk it is in
        """
        chunks = [
            {
                'change': 'equal',
                'meta': {
                    'left_headers': [
                        (1, 'foo'),
                        (100, 'bar'),
                    ],
                },
                'lines': [
                    {
                        0: 1,
                        1: 1,
                        4: 1,
                    },
                    {
                        0: 2,
                        1: 2,
                        4: 1,
                    },
                ]
            }
        ]

        self.assertEqual(
            _get_last_header_in_chunks_before_line(chunks, 2),
            {
                'left': {
                    'line': 1,
                    'text': 'foo',
                },
                'right': None,
            })

    @add_fixtures(['test_users', 'test_scmtools'])
    def test_headers_use_correct_line_insert(self):
        """Testing header generation for chunks with insert chunks above"""
        line_number = 27  # This is a header line below the chunk of inserts

        diff = (b"diff --git a/tests.py b/tests.py\n"
                b"index a4fc53e..f2414cc 100644\n"
                b"--- a/tests.py\n"
                b"+++ b/tests.py\n"
                b"@@ -20,6 +20,9 @@ from reviewboard.site.urlresolvers import "
                b"local_site_reverse\n"
                b" from reviewboard.site.models import LocalSite\n"
                b" from reviewboard.webapi.errors import INVALID_REPOSITORY\n"
                b"\n"
                b"+class Foo(object):\n"
                b"+    def bar(self):\n"
                b"+        pass\n"
                b"\n"
                b" class BaseWebAPITestCase(TestCase, EmailTestHelper);\n"
                b"     fixtures = ['test_users', 'test_reviewrequests', 'test_"
                b"scmtools',\n")

        repository = self.create_repository(tool_name='Git')
        review_request = self.create_review_request(repository=repository)
        diffset = self.create_diffset(review_request=review_request)

        filediff = self.create_filediff(
            diffset=diffset, source_file='tests.py', dest_file='tests.py',
            source_revision='a4fc53e08863f5341effb5204b77504c120166ae',
            diff=diff)

        context = {'user': review_request.submitter}

        siteconfig_settings = {
            'diffviewer_syntax_highlighting': False,
        }

        with self.siteconfig_settings(siteconfig_settings,
                                      reload_settings=False):
            header = get_last_header_before_line(context=context,
                                                 filediff=filediff,
                                                 interfilediff=None,
                                                 target_line=line_number)
            chunks = get_file_chunks_in_range(
                context=context,
                filediff=filediff,
                interfilediff=None,
                first_line=1,
                num_lines=get_last_line_number_in_diff(
                    context=context,
                    filediff=filediff,
                    interfilediff=None))

        lines = []

        for chunk in chunks:
            lines.extend(chunk['lines'])

        # The header we find should be before our line number (which has a
        # header itself).
        self.assertTrue(header['right']['line'] < line_number)

        # The line numbers start at 1 and not 0.
        self.assertEqual(header['right']['text'],
                         lines[header['right']['line'] - 1][5])

    @add_fixtures(['test_users', 'test_scmtools'])
    def test_header_correct_line_delete(self):
        """Testing header generation for chunks with delete chunks above"""
        line_number = 53  # This is a header line below the chunk of deletes

        diff = (b"diff --git a/tests.py b/tests.py\n"
                b"index a4fc53e..ba7d34b 100644\n"
                b"--- a/tests.py\n"
                b"+++ b/tests.py\n"
                b"@@ -47,9 +47,6 @@ class BaseWebAPITestCase(TestCase, "
                b"EmailTestHelper);\n"
                b"\n"
                b"         yourself.base_url = 'http;//testserver'\n"
                b"\n"
                b"-    def tearDown(yourself);\n"
                b"-        yourself.client.logout()\n"
                b"-\n"
                b"     def api_func_wrapper(yourself, api_func, path, query, "
                b"expected_status,\n"
                b"                          follow_redirects, expected_"
                b"redirects);\n"
                b"         response = api_func(path, query, follow=follow_"
                b"redirects)\n")

        repository = self.create_repository(tool_name='Git')
        review_request = self.create_review_request(repository=repository)
        diffset = self.create_diffset(review_request=review_request)

        filediff = self.create_filediff(
            diffset=diffset, source_file='tests.py', dest_file='tests.py',
            source_revision='a4fc53e08863f5341effb5204b77504c120166ae',
            diff=diff)

        context = {'user': review_request.submitter}

        siteconfig_settings = {
            'diffviewer_syntax_highlighting': False,
        }

        with self.siteconfig_settings(siteconfig_settings,
                                      reload_settings=False):
            header = get_last_header_before_line(context=context,
                                                 filediff=filediff,
                                                 interfilediff=None,
                                                 target_line=line_number)
            chunks = get_file_chunks_in_range(
                context=context,
                filediff=filediff,
                interfilediff=None,
                first_line=1,
                num_lines=get_last_line_number_in_diff(
                    context=context,
                    filediff=filediff,
                    interfilediff=None))

        lines = []

        for chunk in chunks:
            lines.extend(chunk['lines'])

        # The header we find should be before our line number (which has a
        # header itself).
        self.assertTrue(header['left']['line'] < line_number)

        # The line numbers start at 1 and not 0.
        self.assertEqual(header['left']['text'],
                         lines[header['left']['line'] - 1][2])


class PatchTests(TestCase):
    """Unit tests for patch."""

    def test_patch(self):
        """Testing patch"""
        old = (b'int\n'
               b'main()\n'
               b'{\n'
               b'\tprintf("foo\\n");\n'
               b'}\n')

        new = (b'#include <stdio.h>\n'
               b'\n'
               b'int\n'
               b'main()\n'
               b'{\n'
               b'\tprintf("foo bar\\n");\n'
               b'\treturn 0;\n'
               b'}\n')

        diff = (b'--- foo.c\t2007-01-24 02:11:31.000000000 -0800\n'
                b'+++ foo.c\t2007-01-24 02:14:42.000000000 -0800\n'
                b'@@ -1,5 +1,8 @@\n'
                b'+#include <stdio.h>\n'
                b'+\n'
                b' int\n'
                b' main()\n'
                b' {\n'
                b'-\tprintf("foo\\n");\n'
                b'+\tprintf("foo bar\\n");\n'
                b'+\treturn 0;\n'
                b' }\n')

        patched = patch(diff=diff,
                        orig_file=old,
                        filename='foo.c')
        self.assertEqual(patched, new)

        diff = (b'--- README\t2007-01-24 02:10:28.000000000 -0800\n'
                b'+++ README\t2007-01-24 02:11:01.000000000 -0800\n'
                b'@@ -1,9 +1,10 @@\n'
                b' Test data for a README file.\n'
                b' \n'
                b' There\'s a line here.\n'
                b'-\n'
                b' A line there.\n'
                b' \n'
                b' And here.\n')

        with self.assertRaises(Exception):
            patch(diff=diff,
                  orig_file=old,
                  filename='foo.c')

    def test_empty_patch(self):
        """Testing patch with an empty diff"""
        old = 'This is a test'
        diff = ''
        patched = patch(diff=diff,
                        orig_file=old,
                        filename='test.c')
        self.assertEqual(patched, old)

    def test_patch_crlf_file_crlf_diff(self):
        """Testing patch with a CRLF file and a CRLF diff"""
        old = (b'Test data for a README file.\r\n'
               b'\r\n'
               b'There\'s a line here.\r\n'
               b'\r\n'
               b'A line there.\r\n'
               b'\r\n'
               b'And here.\r\n')

        new = (b'Test data for a README file.\n'
               b'\n'
               b'There\'s a line here.\n'
               b'A line there.\n'
               b'\n'
               b'And here.\n')

        diff = (b'--- README\t2007-07-02 23:33:27.000000000 -0700\n'
                b'+++ README\t2007-07-02 23:32:59.000000000 -0700\n'
                b'@@ -1,7 +1,6 @@\n'
                b' Test data for a README file.\r\n'
                b' \r\n'
                b' There\'s a line here.\r\n'
                b'-\r\n'
                b' A line there.\r\n'
                b' \r\n'
                b' And here.\r\n')

        patched = patch(diff=diff,
                        orig_file=old,
                        filename='README')
        self.assertEqual(patched, new)

    def test_patch_cr_file_crlf_diff(self):
        """Testing patch with a CR file and a CRLF diff"""
        old = (b'Test data for a README file.\n'
               b'\n'
               b'There\'s a line here.\n'
               b'\n'
               b'A line there.\n'
               b'\n'
               b'And here.\n')

        new = (b'Test data for a README file.\n'
               b'\n'
               b'There\'s a line here.\n'
               b'A line there.\n'
               b'\n'
               b'And here.\n')

        diff = (b'--- README\t2007-07-02 23:33:27.000000000 -0700\n'
                b'+++ README\t2007-07-02 23:32:59.000000000 -0700\n'
                b'@@ -1,7 +1,6 @@\n'
                b' Test data for a README file.\r\n'
                b' \r\n'
                b' There\'s a line here.\r\n'
                b'-\r\n'
                b' A line there.\r\n'
                b' \r\n'
                b' And here.\r\n')

        patched = patch(diff=diff,
                        orig_file=old,
                        filename='README')
        self.assertEqual(patched, new)

    def test_patch_crlf_file_cr_diff(self):
        """Testing patch with a CRLF file and a CR diff"""
        old = (b'Test data for a README file.\r\n'
               b'\r\n'
               b'There\'s a line here.\r\n'
               b'\r\n'
               b'A line there.\r\n'
               b'\r\n'
               b'And here.\r\n')

        new = (b'Test data for a README file.\n'
               b'\n'
               b'There\'s a line here.\n'
               b'A line there.\n'
               b'\n'
               b'And here.\n')

        diff = (b'--- README\t2007-07-02 23:33:27.000000000 -0700\n'
                b'+++ README\t2007-07-02 23:32:59.000000000 -0700\n'
                b'@@ -1,7 +1,6 @@\n'
                b' Test data for a README file.\n'
                b' \n'
                b' There\'s a line here.\n'
                b'-\n'
                b' A line there.\n'
                b' \n'
                b' And here.\n')

        patched = patch(diff=diff,
                        orig_file=old,
                        filename='README')
        self.assertEqual(patched, new)

    def test_patch_file_with_fake_no_newline(self):
        """Testing patch with a file indicating no newline
        with a trailing \\r
        """
        old = (
            b'Test data for a README file.\n'
            b'\n'
            b'There\'s a line here.\n'
            b'\n'
            b'A line there.\n'
            b'\n'
            b'And a new line here!\n'
            b'\n'
            b'We must have several lines to reproduce this problem.\n'
            b'\n'
            b'So that there\'s enough hidden context.\n'
            b'\n'
            b'And dividers so we can reproduce the bug.\n'
            b'\n'
            b'Which will a --- line at the end of one file due to the '
            b'lack of newline,\n'
            b'causing a parse error.\n'
            b'\n'
            b'And here.\n'
            b'Yes, this is a good README file. Like most README files, '
            b'this doesn\'t tell youanything you really didn\'t already '
            b'know.\r')

        new = (
            b'Test data for a README file.\n'
            b'\n'
            b'There\'s a line here.\n'
            b'Here\'s a change!\n'
            b'\n'
            b'A line there.\n'
            b'\n'
            b'And a new line here!\n'
            b'\n'
            b'We must have several lines to reproduce this problem.\n'
            b'\n'
            b'So that there\'s enough hidden context.\n'
            b'\n'
            b'And dividers so we can reproduce the bug.\n'
            b'\n'
            b'Which will a --- line at the end of one file due to the '
            b'lack of newline,\n'
            b'causing a parse error.\n'
            b'\n'
            b'And here.\n'
            b'Yes, this is a good README file. Like most README files, '
            b'this doesn\'t tell youanything you really didn\'t '
            b'already know.\n')

        diff = (
            b'--- README\t2008-02-25 03:40:42.000000000 -0800\n'
            b'+++ README\t2008-02-25 03:40:55.000000000 -0800\n'
            b'@@ -1,6 +1,7 @@\n'
            b' Test data for a README file.\n'
            b' \n'
            b' There\'s a line here.\n'
            b'+Here\'s a change!\n'
            b' \n'
            b' A line there.\n'
            b' \n'
            b'@@ -16,4 +17,4 @@\n'
            b' causing a parse error.\n'
            b' \n'
            b' And here.\n'
            b'-Yes, this is a good README file. Like most README files, this '
            b'doesn\'t tell youanything you really didn\'t already know.\n'
            b'\\ No newline at end of file\n'
            b'+Yes, this is a good README file. Like most README files, this '
            b'doesn\'t tell youanything you really didn\'t already know.\n')

        patched = patch(diff=diff,
                        orig_file=old,
                        filename='README')
        self.assertEqual(patched, new)


class GetFileDiffEncodingsTests(TestCase):
    """Unit tests for get_filediff_encodings."""

    fixtures = ['test_scmtools']

    def setUp(self):
        super(GetFileDiffEncodingsTests, self).setUp()

        self.repository = self.create_repository(encoding='ascii,iso-8859-15')
        self.diffset = self.create_diffset(repository=self.repository)

    def test_with_stored_encoding(self):
        """Testing get_filediff_encodings with recorded FileDiff.encoding"""
        filediff = self.create_filediff(self.diffset,
                                        encoding='utf-16')

        self.assertEqual(get_filediff_encodings(filediff),
                         ['utf-16', 'ascii', 'iso-8859-15'])

    def test_with_out_stored_encoding(self):
        """Testing get_filediff_encodings without recorded FileDiff.encoding"""
        filediff = self.create_filediff(self.diffset)

        self.assertEqual(get_filediff_encodings(filediff),
                         ['ascii', 'iso-8859-15'])

    def test_with_custom_encodings(self):
        """Testing get_filediff_encodings with custom encoding_list"""
        filediff = self.create_filediff(self.diffset)

        self.assertEqual(
            get_filediff_encodings(filediff,
                                   encoding_list=['rot13', 'palmos']),
            ['rot13', 'palmos'])


class GetOriginalFileTests(BaseFileDiffAncestorTests):
    """Unit tests for get_original_file."""

    def setUp(self):
        super(GetOriginalFileTests, self).setUp()

        self.spy_on(get_original_file_from_repo)

    def test_created_in_first_parent(self):
        """Test get_original_file with a file created in the parent diff of the
        first commit
        """
        self.set_up_filediffs()

        filediff = FileDiff.objects.get(dest_file='bar', dest_detail='8e739cc',
                                        commit_id=1)

        self.assertEqual(get_original_file(filediff=filediff), b'bar\n')
        self.assertTrue(get_original_file_from_repo.called_with(
            filediff=filediff,
            request=None,
            encoding_list=None))

    def test_created_in_subsequent_parent(self):
        """Test get_original_file with a file created in the parent diff of a
        subsequent commit
        """
        self.set_up_filediffs()

        filediff = FileDiff.objects.get(dest_file='baz', dest_detail='280beb2',
                                        commit_id=2)

        self.assertEqual(get_original_file(filediff=filediff), b'baz\n')
        self.assertTrue(get_original_file_from_repo.called)

    def test_created_previously_deleted(self):
        """Testing get_original_file with a file created and previously deleted
        """
        self.set_up_filediffs()

        filediff = FileDiff.objects.get(dest_file='bar', dest_detail='5716ca5',
                                        commit_id=3)

        self.assertEqual(get_original_file(filediff=filediff), b'')
        self.assertFalse(get_original_file_from_repo.called)

    def test_renamed(self):
        """Test get_original_file with a renamed file"""
        self.set_up_filediffs()

        filediff = FileDiff.objects.get(dest_file='qux', dest_detail='03b37a0',
                                        commit_id=3)

        self.assertEqual(get_original_file(filediff=filediff), b'foo\n')
        self.assertFalse(get_original_file_from_repo.called)

    def test_empty_parent_diff_old_patch(self):
        """Testing get_original_file with an empty parent diff with patch(1)
        that does not accept empty diffs
        """
        self.set_up_filediffs()

        filediff = (
            FileDiff.objects
            .select_related('parent_diff_hash',
                            'diffset',
                            'diffset__repository',
                            'diffset__repository__tool')
            .get(dest_file='corge',
                 dest_detail='f248ba3',
                 commit_id=3)
        )

        # FileDiff creation will set the _IS_PARENT_EMPTY flag.
        del filediff.extra_data[FileDiff._IS_PARENT_EMPTY_KEY]
        filediff.save(update_fields=('extra_data',))

        # Older versions of patch will choke on an empty patch with a "garbage
        # input" error, but newer versions will handle it just fine. We stub
        # out patch here to always fail so we can test for the case of an older
        # version of patch without requiring it to be installed.
        def _patch(diff, orig_file, filename, request=None):
            raise PatchError(
                filename=filename,
                error_output=_PATCH_GARBAGE_INPUT,
                orig_file=orig_file,
                new_file='tmp123-new',
                diff=b'',
                rejects=None)

        self.spy_on(patch, call_fake=_patch)

        # One query for each of the following:
        # - saving the RawFileDiffData in RawFileDiffData.recompute_line_counts
        # - saving the FileDiff in FileDiff.is_parent_diff_empty
        with self.assertNumQueries(2):
            orig = get_original_file(filediff=filediff)

        self.assertEqual(orig, b'')

        # Refresh the object from the database with the parent diff attached
        # and then verify that re-calculating the original file does not cause
        # additional queries.
        filediff = (
            FileDiff.objects
            .select_related('parent_diff_hash')
            .get(pk=filediff.pk)
        )

        with self.assertNumQueries(0):
            orig = get_original_file(filediff=filediff)

    def test_empty_parent_diff_new_patch(self):
        """Testing get_original_file with an empty parent diff with patch(1)
        that does accept empty diffs
        """
        self.set_up_filediffs()

        filediff = (
            FileDiff.objects
            .select_related('parent_diff_hash',
                            'diffset',
                            'diffset__repository',
                            'diffset__repository__tool')
            .get(dest_file='corge',
                 dest_detail='f248ba3',
                 commit_id=3)
        )

        # FileDiff creation will set the _IS_PARENT_EMPTY flag.
        del filediff.extra_data[FileDiff._IS_PARENT_EMPTY_KEY]
        filediff.save(update_fields=('extra_data',))

        # Newer versions of patch will allow empty patches. We stub out patch
        # here to always fail so we can test for the case of a newer version
        # of patch without requiring it to be installed.
        def _patch(diff, orig_file, filename, request=None):
            # This is the only call to patch() that should be made.
            self.assertEqual(diff,
                             b'diff --git a/corge b/corge\n'
                             b'new file mode 100644\n'
                             b'index 0000000..e69de29\n')
            return orig_file

        self.spy_on(patch, call_fake=_patch)

        with self.assertNumQueries(0):
            orig = get_original_file(filediff=filediff)

        self.assertEqual(orig, b'')

        # Refresh the object from the database with the parent diff attached
        # and then verify that re-calculating the original file does not cause
        # additional queries.
        filediff = (
            FileDiff.objects
            .select_related('parent_diff_hash')
            .get(pk=filediff.pk)
        )

        with self.assertNumQueries(0):
            orig = get_original_file(filediff=filediff)

    def test_empty_parent_diff_precomputed(self):
        """Testing get_original_file with an empty parent diff for which the
        result has been pre-computed
        """
        self.set_up_filediffs()

        filediff = (
            FileDiff.objects
            .select_related('parent_diff_hash',
                            'diffset',
                            'diffset__repository',
                            'diffset__repository__tool')
            .get(dest_file='corge',
                 dest_detail='f248ba3',
                 commit_id=3)
        )

        with self.assertNumQueries(0):
            orig = get_original_file(filediff=filediff)

        self.assertEqual(orig, b'')

    def test_with_encoding_list(self):
        """Testing get_original_file with encoding_list is deprecated"""
        self.set_up_filediffs()

        filediff = FileDiff.objects.get(dest_file='bar',
                                        dest_detail='8e739cc',
                                        commit_id=1)

        message = (
            'The encoding_list parameter passed to get_original_file() is '
            'deprecated and will be removed in Review Board 5.0.'
        )

        with self.assert_warns(RemovedInReviewBoard50Warning, message):
            get_original_file(filediff, encoding_list=['ascii'])

    def test_parent_diff_with_rename_and_modern_fields(self):
        """Testing get_original_file with a file renamed in parent diff
        with modern parent_source_* keys in extra_data
        """
        parent_diff = (
            b'diff --git a/old-name b/new-name\n'
            b'rename from old-name\n'
            b'rename to new-name\n'
            b'index b7a8c9f..e69de29 100644\n'
            b'--- a/old-name\n'
            b'+++ a/new-name\n'
            b'@@ -1,1 +1,1 @@\n'
            b'-orig file\n'
            b'+abc123\n'
        )

        diff = (
            b'diff --git a/new-name b/new-name\n'
            b'index e69de29..0e4b0c7 100644\n'
            b'--- a/new-name\n'
            b'+++ a/new-name\n'
            b'@@ -1,1 +1,1 @@\n'
            b'+abc123\n'
            b'+def456\n'
        )

        repository = self.create_repository(tool_name='Git')
        diffset = self.create_diffset(repository=repository)
        filediff = FileDiff.objects.create(
            diffset=diffset,
            source_file='new-name',
            source_revision='e69de29',
            dest_file='new-name',
            dest_detail='0e4b0c7',
            extra_data={
                'encoding': 'ascii',
                'parent_source_filename': 'old-file',
                'parent_source_revision': 'b7a8c9f',
            })
        filediff.parent_diff = parent_diff
        filediff.diff = diff
        filediff.save()

        request_factory = RequestFactory()

        def _get_file(_self, path, revision, *args, **kwargs):
            self.assertEqual(path, 'old-file')
            self.assertEqual(revision, 'b7a8c9f')

            return b'orig file\n'

        self.spy_on(repository.get_file, call_fake=_get_file)

        with self.assertNumQueries(0):
            orig = get_original_file(filediff=filediff,
                                     request=request_factory.get('/'),
                                     encoding_list=['ascii'])

        self.assertEqual(orig, b'abc123\n')

        # Refresh the object from the database with the parent diff attached
        # and then verify that re-calculating the original file does not cause
        # additional queries.
        filediff = (
            diffset.files
            .select_related('parent_diff_hash')
            .get(pk=filediff.pk)
        )

        with self.assertNumQueries(0):
            orig = get_original_file(filediff=filediff,
                                     request=request_factory.get('/'),
                                     encoding_list=['ascii'])

    def test_with_filediff_with_encoding_set(self):
        """Testing get_original_file with FileDiff.encoding set"""
        content = 'hello world'.encode('utf-16')

        repository = self.create_repository()
        self.spy_on(repository.get_file,
                    call_fake=lambda *args, **kwargs: content)
        self.spy_on(convert_to_unicode)
        self.spy_on(convert_line_endings)

        diffset = self.create_diffset(repository=repository)
        filediff = self.create_filediff(diffset,
                                        encoding='utf-16')

        self.assertEqual(get_original_file(filediff=filediff), content)
        self.assertTrue(convert_to_unicode.called_with(
            content, ['utf-16', 'iso-8859-15']))
        self.assertTrue(convert_line_endings.called_with('hello world'))

    def test_with_filediff_with_repository_encoding_set(self):
        """Testing get_original_file with Repository.encoding set"""
        content = 'hello world'.encode('utf-16')

        repository = self.create_repository(encoding='utf-16')
        self.spy_on(repository.get_file,
                    call_fake=lambda *args, **kwargs: content)
        self.spy_on(convert_to_unicode)
        self.spy_on(convert_line_endings)

        diffset = self.create_diffset(repository=repository)
        filediff = self.create_filediff(diffset)

        self.assertEqual(get_original_file(filediff=filediff), content)
        self.assertTrue(convert_to_unicode.called_with(content, ['utf-16']))
        self.assertTrue(convert_line_endings.called_with('hello world'))


class SplitLineEndingsTests(TestCase):
    """Unit tests for reviewboard.diffviewer.diffutils.split_line_endings."""

    def test_with_byte_string(self):
        """Testing split_line_endings with byte string"""
        lines = split_line_endings(
            b'This is line 1\n'
            b'This is line 2\r\n'
            b'This is line 3\r'
            b'This is line 4\r\r\n'
            b'This is line 5'
        )

        for line in lines:
            self.assertIsInstance(line, bytes)

        self.assertEqual(
            lines,
            [
                b'This is line 1',
                b'This is line 2',
                b'This is line 3',
                b'This is line 4',
                b'This is line 5',
            ])

    def test_with_unicode_string(self):
        """Testing split_line_endings with unicode string"""
        lines = split_line_endings(
            'This is line 1\n'
            'This is line 2\r\n'
            'This is line 3\r'
            'This is line 4\r\r\n'
            'This is line 5'
        )

        for line in lines:
            self.assertIsInstance(line, six.text_type)

        self.assertEqual(
            lines,
            [
                'This is line 1',
                'This is line 2',
                'This is line 3',
                'This is line 4',
                'This is line 5',
            ])
