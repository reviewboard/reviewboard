from __future__ import unicode_literals

from kgb import SpyAgency

from reviewboard.diffviewer.chunk_generator import DiffChunkGenerator
from reviewboard.scmtools.core import PRE_CREATION
from reviewboard.testing import TestCase


class DiffChunkGeneratorTests(SpyAgency, TestCase):
    """Unit tests for DiffChunkGenerator."""

    fixtures = ['test_scmtools']

    COMMIT_1_DIFF = (
        b'diff --git a/README b/README\n'
        b'index 94bdd3e..197009f 100644\n'
        b'--- README\n'
        b'+++ README\n'
        b'@@ -1,1 +1,1 @@\n'
        b'-Hello, world!\n'
        b'+Hi, world!\n'
    )

    COMMIT_2_DIFF = (
        b'diff --git a/README b/README\n'
        b'index 197009f..87abad9 100644\n'
        b'--- README\n'
        b'+++ README\n'
        b'@@ -1,1 +1,1 @@\n'
        b'-Hi, world!\n'
        b'+Yo, world.\n'
    )

    COMMIT_3_DIFF = (
        b'diff --git a/README b/README\n'
        b'index 87abad9..fe1678a 100644\n'
        b'--- README\n'
        b'+++ README\n'
        b'@@ -1,1 +1,1 @@\n'
        b'-Yo, world.\n'
        b'+Yo, dog.\n'
    )

    COMMIT_1_2_SQUASHED_DIFF = (
        b'diff --git a/README b/README\n'
        b'index 94bdd3e..87abad9 100644\n'
        b'--- README\n'
        b'+++ README\n'
        b'@@ -1,1 +1,1 @@\n'
        b'-Hello, world!\n'
        b'+Yo, world.\n'
    )

    COMMIT_1_3_SQUASHED_DIFF = (
        b'diff --git a/README b/README\n'
        b'index 94bdd3e..fe1678a 100644\n'
        b'--- README\n'
        b'+++ README\n'
        b'@@ -1,1 +1,1 @@\n'
        b'-Hello, world!\n'
        b'+Yo, dog.\n'
    )

    def setUp(self):
        super(DiffChunkGeneratorTests, self).setUp()

        self.repository = self.create_repository(tool_name='Test')
        self.diffset = self.create_diffset(repository=self.repository)
        self.filediff = self.create_filediff(diffset=self.diffset)
        self.generator = DiffChunkGenerator(None, self.filediff)

    def test_get_chunks_with_empty_added_file(self):
        """Testing DiffChunkGenerator.get_chunks with empty added file"""
        self.filediff.source_revision = PRE_CREATION
        self.filediff.extra_data.update({
            'raw_insert_count': 0,
            'raw_delete_count': 0,
        })

        self.assertEqual(len(list(self.generator.get_chunks())), 0)

    def test_get_chunks_with_explicit_encoding(self):
        """Testing DiffChunkGenerator.get_chunks with explicit encoding on
        FileDiff
        """
        self.filediff.diff = (
            b'--- README\n'
            b'+++ README\n'
            b'@@ -1,1 +1,1 @@\n'
            b'-%s\n'
            b'+%s\n'
            % ('Hello, world!'.encode('utf-16'),
               'Hi, everybody!'.encode('utf-16'))
        )
        self.filediff.source_file = '/test-file;encoding=utf-16'
        self.filediff.extra_data['encoding'] = 'utf-16'

        self.spy_on(self.repository.get_file)

        chunks = list(self.generator.get_chunks())
        self.assertEqual(len(chunks), 1)
        self.assertEqual(
            chunks[0],
            {
                'change': 'replace',
                'collapsable': False,
                'index': 0,
                'lines': [
                    [
                        1, 1,
                        'Hello, world!',
                        None,
                        1,
                        'Hi, everybody!',
                        None,
                        False,
                    ]
                ],
                'meta': {
                    'left_headers': [],
                    'right_headers': [],
                    'whitespace_chunk': False,
                    'whitespace_lines': [],
                },
                'numlines': 1,
            })

        self.assertTrue(self.repository.get_file.last_returned(
            'Hello, world!\n'.encode('utf-16')))

    def test_get_chunks_with_replace_in_added_file_with_parent_diff(self):
        """Testing DiffChunkGenerator.get_chunks with replace chunks in
        added file with parent diff
        """
        self.filediff.diff = (
            b'--- README\n'
            b'+++ README\n'
            b'@@ -1,1 +1,1 @@\n'
            b'-line\n'
            b'+line.\n'
        )
        self.filediff.parent_diff = (
            b'--- README\n'
            b'+++ README\n'
            b'@@ -0,0 +1,1 @@\n'
            b'+line\n'
        )
        self.filediff.source_revision = PRE_CREATION
        self.filediff.extra_data.update({
            'raw_insert_count': 1,
            'raw_delete_count': 1,
            'insert_count': 0,
            'delete_count': 0,
        })

        self.assertEqual(len(list(self.generator.get_chunks())), 1)

    def test_get_chunks_with_commit_and_base_filediff(self):
        """Testing DiffChunkGenerator.get_chunks with commit using base_filediff
        """
        commit1 = self.create_diffcommit(
            commit_id='abc1234',
            parent_id='abc1233',
            diffset=self.diffset,
            diff_contents=self.COMMIT_1_DIFF)
        commit2 = self.create_diffcommit(
            commit_id='abc1235',
            parent_id='abc1234',
            diffset=self.diffset,
            diff_contents=self.COMMIT_2_DIFF)

        self.diffset.finalize_commit_series(
            cumulative_diff=self.COMMIT_1_2_SQUASHED_DIFF,
            validation_info=None,
            validate=False,
            save=True)

        base_filediff = commit1.files.get()
        tip_filediff = commit2.files.get()

        generator = DiffChunkGenerator(request=None,
                                       filediff=tip_filediff,
                                       base_filediff=base_filediff)

        chunks = list(generator.get_chunks())
        self.assertEqual(len(chunks), 1)

        chunk = chunks[0]
        self.assertEqual(chunk['index'], 0)
        self.assertEqual(chunk['change'], 'replace')
        self.assertEqual(
            chunk['lines'],
            [[
                1,
                1, 'Hi, world!', [(0, 2), (9, 10)],
                1, 'Yo, world.', [(0, 2), (9, 10)],
                False,
            ]])

    def test_get_chunks_with_commit_and_no_base_filediff(self):
        """Testing DiffChunkGenerator.get_chunks with commit and no
        base_filediff
        """
        self.create_diffcommit(
            commit_id='abc1234',
            parent_id='abc1233',
            diffset=self.diffset,
            diff_contents=self.COMMIT_1_DIFF)
        self.create_diffcommit(
            commit_id='abc1235',
            parent_id='abc1234',
            diffset=self.diffset,
            diff_contents=self.COMMIT_2_DIFF)
        commit3 = self.create_diffcommit(
            commit_id='abc1236',
            parent_id='abc1235',
            diffset=self.diffset,
            diff_contents=self.COMMIT_3_DIFF)

        self.diffset.finalize_commit_series(
            cumulative_diff=self.COMMIT_1_3_SQUASHED_DIFF,
            validation_info=None,
            validate=False,
            save=True)

        filediff = commit3.files.get()

        generator = DiffChunkGenerator(request=None,
                                       filediff=filediff)

        chunks = list(generator.get_chunks())
        self.assertEqual(len(chunks), 1)

        chunk = chunks[0]
        self.assertEqual(chunk['index'], 0)
        self.assertEqual(chunk['change'], 'replace')
        self.assertEqual(
            chunk['lines'],
            [[
                1,
                1, 'Hello, world!', None,
                1, 'Yo, dog.', None,
                False,
            ]])

    def test_get_chunks_with_commit_and_base_tip_same(self):
        """Testing DiffChunkGenerator.get_chunks with commit and base_filediff
        same as filediff
        """
        commit = self.create_diffcommit(
            commit_id='abc1234',
            parent_id='abc1233',
            diffset=self.diffset,
            diff_contents=self.COMMIT_1_DIFF)

        self.diffset.finalize_commit_series(
            cumulative_diff=self.COMMIT_1_DIFF,
            validation_info=None,
            validate=False,
            save=True)

        filediff = commit.files.get()

        generator = DiffChunkGenerator(request=None,
                                       filediff=filediff,
                                       base_filediff=filediff)

        chunks = list(generator.get_chunks())
        self.assertEqual(len(chunks), 1)

        chunk = chunks[0]
        self.assertEqual(chunk['index'], 0)
        self.assertEqual(chunk['change'], 'equal')
        self.assertEqual(
            chunk['lines'],
            [[
                1,
                1, 'Hi, world!', [],
                1, 'Hi, world!', [],
                False,
            ]])

    def test_get_chunks_with_commit_and_file_recreated(self):
        """Testing DiffChunkGenerator.get_chunks with commit and file recreated
        in prior commit
        """
        commit1, commit2 = self._make_delete_recreate_commits()
        filediff = commit2.files.get()

        generator = DiffChunkGenerator(request=None,
                                       filediff=filediff)

        chunks = list(generator.get_chunks())
        self.assertEqual(len(chunks), 1)

        chunk = chunks[0]
        self.assertEqual(chunk['index'], 0)
        self.assertEqual(chunk['change'], 'insert')
        self.assertEqual(
            chunk['lines'],
            [[
                1,
                '', '', [],
                1, 'This is a new file.', [],
                False,
            ]])

    def test_get_chunks_with_commit_and_file_recreated_and_base_deleted(self):
        """Testing DiffChunkGenerator.get_chunks with commit and file recreated
        in prior commit with base_filediff as deleted file
        """
        commit1, commit2 = self._make_delete_recreate_commits()
        base_filediff = commit1.files.get()
        filediff = commit2.files.get()

        generator = DiffChunkGenerator(request=None,
                                       filediff=filediff,
                                       base_filediff=base_filediff)

        chunks = list(generator.get_chunks())
        self.assertEqual(len(chunks), 1)

        chunk = chunks[0]
        self.assertEqual(chunk['index'], 0)
        self.assertEqual(chunk['change'], 'insert')
        self.assertEqual(
            chunk['lines'],
            [[
                1,
                '', '', [],
                1, 'This is a new file.', [],
                False,
            ]])

    def test_line_counts_unmodified_by_interdiff(self):
        """Testing that line counts are not modified by interdiffs where the
        changes are reverted
        """
        self.filediff.source_revision = PRE_CREATION
        self.filediff.diff = (
            b'--- README\n'
            b'+++ README\n'
            b'@@ -0,0 +1,1 @@\n'
            b'+line\n'
        )

        # We have to consume everything from the get_chunks generator in order
        # for the line counts to be set on the FileDiff.
        self.assertEqual(len(list(self.generator.get_chunks())), 1)

        line_counts = self.filediff.get_line_counts()

        # Simulate an interdiff where the changes are reverted.
        interdiff_generator = DiffChunkGenerator(request=None,
                                                 filediff=self.filediff,
                                                 interfilediff=None,
                                                 force_interdiff=True)

        # Again, just consuming the generator.
        self.assertEqual(len(list(interdiff_generator.get_chunks())), 1)

        self.assertEqual(line_counts, self.filediff.get_line_counts())

    def _make_delete_recreate_commits(self):
        """Finalize and return commits for a delete/re-create test.

        This creates two commits. In the first one, an upstream file is
        deleted. In the second, it's re-created.

        The commits are finalized before being returned.

        Returns:
            list of reviewboard.diffviewer.models.diffcommit.DiffCommit:
            The newly-created commits.
        """
        commits = [
            self.create_diffcommit(
                commit_id='abc1234',
                parent_id='abc1233',
                diffset=self.diffset,
                diff_contents=(
                    b'diff --git a/README b/README\n'
                    b'deleted file mode 100644\n'
                    b'index 94bdd3e..0000000\n'
                    b'--- README\n'
                    b'+++ /dev/null\n'
                    b'@@ -1,1 +0,0 @@\n'
                    b'-Hello, world!\n'
                )),
            self.create_diffcommit(
                commit_id='abc1235',
                parent_id='abc1234',
                diffset=self.diffset,
                diff_contents=(
                    b'diff --git a/README b/README\n'
                    b'new file mode 100644\n'
                    b'index 0000000..ba178ca\n'
                    b'--- /dev/null\n'
                    b'+++ README\n'
                    b'@@ -0,0 +1,1 @@\n'
                    b'+This is a new file.\n'
                )),
        ]

        self.diffset.finalize_commit_series(
            cumulative_diff=(
                b'diff --git a/README b/README\n'
                b'index 94bdd3e..0000000 10644\n'
                b'--- README\n'
                b'+++ README\n'
                b'@@ -1,1 +1,1 @@\n'
                b'-Hello, world!\n'
                b'+This is a new file.\n'
            ),
            validation_info=None,
            validate=False,
            save=True)

        return commits
