"""Unit tests for reviewboard.reviews.views.ReviewsDiffViewerView."""

from __future__ import annotations

from reviewboard.site.urlresolvers import local_site_reverse
from reviewboard.testing.testcase import BaseFileDiffAncestorTests, TestCase


class ReviewsDiffViewerViewTests(TestCase):
    """Unit tests for reviewboard.reviews.views.ReviewsDiffViewerView."""

    fixtures = ['test_users', 'test_scmtools']

    # Bug 892
    def test_interdiff(self) -> None:
        """Testing ReviewsDiffViewerView with interdiffs"""
        review_request = self.create_review_request(create_repository=True,
                                                    publish=True)
        diffset = self.create_diffset(review_request, revision=1)
        self.create_filediff(
            diffset,
            source_file='/diffutils.py',
            dest_file='/diffutils.py',
            source_revision='6bba278',
            dest_detail='465d217',
            diff=(
                b'diff --git a/diffutils.py b/diffutils.py\n'
                b'index 6bba278..465d217 100644\n'
                b'--- a/diffutils.py\n'
                b'+++ b/diffutils.py\n'
                b'@@ -1,3 +1,4 @@\n'
                b'+# diffutils.py\n'
                b' import fnmatch\n'
                b' import os\n'
                b' import re\n'
            ))
        self.create_filediff(
            diffset,
            source_file='/readme',
            dest_file='/readme',
            source_revision='d6613f5',
            dest_detail='5b50866',
            diff=(
                b'diff --git a/readme b/readme\n'
                b'index d6613f5..5b50866 100644\n'
                b'--- a/readme\n'
                b'+++ b/readme\n'
                b'@@ -1 +1,3 @@\n'
                b' Hello there\n'
                b'+\n'
                b'+Oh hi!\n'
            ))
        self.create_filediff(
            diffset,
            source_file='/newfile',
            dest_file='/newfile',
            source_revision='PRE-CREATION',
            dest_detail='',
            diff=(
                b'diff --git a/new_file b/new_file\n'
                b'new file mode 100644\n'
                b'index 0000000..ac30bd3\n'
                b'--- /dev/null\n'
                b'+++ b/new_file\n'
                b'@@ -0,0 +1 @@\n'
                b'+This is a new file!\n'
            ))

        diffset = self.create_diffset(review_request, revision=2)
        self.create_filediff(
            diffset,
            source_file='/diffutils.py',
            dest_file='/diffutils.py',
            source_revision='6bba278',
            dest_detail='465d217',
            diff=(
                b'diff --git a/diffutils.py b/diffutils.py\n'
                b'index 6bba278..465d217 100644\n'
                b'--- a/diffutils.py\n'
                b'+++ b/diffutils.py\n'
                b'@@ -1,3 +1,4 @@\n'
                b'+# diffutils.py\n'
                b' import fnmatch\n'
                b' import os\n'
                b' import re\n'
            ))
        self.create_filediff(
            diffset,
            source_file='/readme',
            dest_file='/readme',
            source_revision='d6613f5',
            dest_detail='5b50867',
            diff=(
                b'diff --git a/readme b/readme\n'
                b'index d6613f5..5b50867 100644\n'
                b'--- a/readme\n'
                b'+++ b/readme\n'
                b'@@ -1 +1,3 @@\n'
                b' Hello there\n'
                b'+----------\n'
                b'+Oh hi!\n'
            ))
        self.create_filediff(
            diffset,
            source_file='/newfile',
            dest_file='/newfile',
            source_revision='PRE-CREATION',
            dest_detail='',
            diff=(
                b'diff --git a/new_file b/new_file\n'
                b'new file mode 100644\n'
                b'index 0000000..ac30bd4\n'
                b'--- /dev/null\n'
                b'+++ b/new_file\n'
                b'@@ -0,0 +1 @@\n'
                b'+This is a diffent version of this new file!\n'
            ))

        response = self.client.get('/r/1/diff/1-2/')

        # Useful for debugging any actual errors here.
        if response.status_code != 200:
            print('Error: %s' % response.context['error'])
            print(response.context['trace'])

        self.assertEqual(response.status_code, 200)

        self.assertEqual(response.context['diff_context']['num_diffs'], 2)

        files = response.context['files']
        self.assertTrue(files)
        self.assertEqual(len(files), 2)

        self.assertEqual(files[0]['orig_filename'], '/newfile')
        self.assertIn('interfilediff', files[0])

        self.assertEqual(files[1]['orig_filename'], '/readme')
        self.assertIn('interfilediff', files[1])

    # Bug 847
    def test_interdiff_new_file(self) -> None:
        """Testing ReviewsDiffViewrView with interdiffs containing new files"""
        review_request = self.create_review_request(create_repository=True,
                                                    publish=True)
        diffset = self.create_diffset(review_request, revision=1)
        self.create_filediff(
            diffset,
            source_file='/diffutils.py',
            dest_file='/diffutils.py',
            source_revision='6bba278',
            dest_detail='465d217',
            diff=(
                b'diff --git a/diffutils.py b/diffutils.py\n'
                b'index 6bba278..465d217 100644\n'
                b'--- a/diffutils.py\n'
                b'+++ b/diffutils.py\n'
                b'@@ -1,3 +1,4 @@\n'
                b'+# diffutils.py\n'
                b' import fnmatch\n'
                b' import os\n'
                b' import re\n'
            ))

        diffset = self.create_diffset(review_request, revision=2)
        self.create_filediff(
            diffset,
            source_file='/diffutils.py',
            dest_file='/diffutils.py',
            source_revision='6bba278',
            dest_detail='465d217',
            diff=(
                b'diff --git a/diffutils.py b/diffutils.py\n'
                b'index 6bba278..465d217 100644\n'
                b'--- a/diffutils.py\n'
                b'+++ b/diffutils.py\n'
                b'@@ -1,3 +1,4 @@\n'
                b'+# diffutils.py\n'
                b' import fnmatch\n'
                b' import os\n'
                b' import re\n'
            ))
        self.create_filediff(
            diffset,
            source_file='/newfile',
            dest_file='/newfile',
            source_revision='PRE-CREATION',
            dest_detail='',
            diff=(
                b'diff --git a/new_file b/new_file\n'
                b'new file mode 100644\n'
                b'index 0000000..ac30bd4\n'
                b'--- /dev/null\n'
                b'+++ b/new_file\n'
                b'@@ -0,0 +1 @@\n'
                b'+This is a diffent version of this new file!\n'
            ))

        response = self.client.get('/r/1/diff/1-2/')

        # Useful for debugging any actual errors here.
        if response.status_code != 200:
            print('Error: %s' % response.context['error'])
            print(response.context['trace'])

        self.assertEqual(response.status_code, 200)

        self.assertEqual(response.context['diff_context']['num_diffs'], 2)

        files = response.context['files']
        self.assertTrue(files)
        self.assertEqual(len(files), 1)

        self.assertEqual(files[0]['orig_filename'], '/newfile')
        self.assertIn('interfilediff', files[0])

    def test_with_filenames_option(self) -> None:
        """Testing ReviewsDiffViewerView with ?filenames=..."""
        review_request = self.create_review_request(create_repository=True,
                                                    publish=True)
        diffset = self.create_diffset(review_request)
        filediff1 = self.create_filediff(diffset,
                                         source_file='src/main/test.c',
                                         dest_file='src/main/test.cpp')
        filediff2 = self.create_filediff(diffset,
                                         source_file='docs/README.txt',
                                         dest_file='docs/README2.txt')
        filediff3 = self.create_filediff(diffset,
                                         source_file='test.txt',
                                         dest_file='test.rst')
        filediff4 = self.create_filediff(diffset,
                                         source_file='/lib/lib.h',
                                         dest_file='/lib/lib.h')
        self.create_filediff(diffset,
                             source_file='unmatched',
                             dest_file='unmatched')

        response = self.client.get(
            local_site_reverse(
                'view-diff-revision',
                kwargs={
                    'review_request_id': review_request.display_id,
                    'revision': diffset.revision,
                }),
            {
                'filenames': '*/test.cpp,*.txt,/lib/*',
            })
        self.assertEqual(response.status_code, 200)

        files = response.context['files']
        self.assertEqual({file_info['filediff'] for file_info in files},
                         {filediff1, filediff2, filediff3, filediff4})

    def test_with_filenames_option_normalized(self) -> None:
        """Testing ReviewsDiffViewerView with ?filenames=... values normalized
        """
        review_request = self.create_review_request(create_repository=True,
                                                    publish=True)
        diffset = self.create_diffset(review_request)
        filediff1 = self.create_filediff(diffset,
                                         source_file='src/main/test.c',
                                         dest_file='src/main/test.cpp')
        filediff2 = self.create_filediff(diffset,
                                         source_file='docs/README.txt',
                                         dest_file='docs/README2.txt')
        filediff3 = self.create_filediff(diffset,
                                         source_file='test.txt',
                                         dest_file='test.rst')
        filediff4 = self.create_filediff(diffset,
                                         source_file='/lib/lib.h',
                                         dest_file='/lib/lib.h')
        self.create_filediff(diffset,
                             source_file='unmatched',
                             dest_file='unmatched')

        response = self.client.get(
            local_site_reverse(
                'view-diff-revision',
                kwargs={
                    'review_request_id': review_request.display_id,
                    'revision': diffset.revision,
                }),
            {
                'filenames': ' ,  , */test.cpp,,,*.txt,/lib/*  ',
            })
        self.assertEqual(response.status_code, 200)

        files = response.context['files']
        self.assertEqual({file_info['filediff'] for file_info in files},
                         {filediff1, filediff2, filediff3, filediff4})


class CommitsTests(BaseFileDiffAncestorTests):
    """Tests for ReviewsDiffViewerView with commit history."""

    def setUp(self) -> None:
        """Set up the test case."""
        self.set_up_filediffs()

        review = self.create_review(review_request=self.review_request,
                                    publish=True)
        self.cumulative_comment = self.create_diff_comment(
            review=review,
            filediff=self.diffset.cumulative_files[0])

        commit1 = self.diff_commits[1]
        commit2 = self.diff_commits[2]

        # Comment from the base commit to a tip
        self.commit_comment1 = self.create_diff_comment(
            review=review,
            filediff=commit2.files.get(dest_file='bar'))

        # Comment from one commit to another
        self.commit_comment2 = self.create_diff_comment(
            review=review,
            filediff=commit2.files.get(dest_file='bar'))
        self.commit_comment2.base_filediff_id = \
            commit1.files.get(dest_file='bar').pk
        self.commit_comment2.save(update_fields=['extra_data'])

    def test_comment_data_with_cumulative_diff(self) -> None:
        """Testing ReviewsDiffViewerView comment data with cumulative diff"""
        response = self.client.get(
            local_site_reverse(
                'view-diff-revision',
                kwargs={
                    'review_request_id': self.review_request.display_id,
                    'revision': self.diffset.revision,
                }))
        self.assertEqual(response.status_code, 200)

        files = response.context['diff_context']['files']

        for f in files:
            comment_blocks = f['serialized_comment_blocks']

            if f['id'] == self.cumulative_comment.filediff_id:
                self.assertEqual(len(comment_blocks), 1)

                comments = list(comment_blocks.values())[0]
                self.assertEqual(comments[0]['comment_id'],
                                 self.cumulative_comment.pk)
            else:
                # All other files in the diff should show no comments on them.
                self.assertEqual(comment_blocks, {})

    def test_comment_data_with_commit_range1(self) -> None:
        """Testing ReviewsDiffViewerView comment data with a commit range from
        the base commit
        """
        response = self.client.get(
            local_site_reverse(
                'view-diff-revision',
                kwargs={
                    'review_request_id': self.review_request.display_id,
                    'revision': self.diffset.revision,
                }),
            {
                'tip-commit-id': self.diff_commits[2].pk,
            })
        self.assertEqual(response.status_code, 200)

        files = response.context['diff_context']['files']

        for f in files:
            comment_blocks = f['serialized_comment_blocks']

            if f['id'] == self.commit_comment1.filediff_id:
                self.assertEqual(len(comment_blocks), 1)

                comments = list(comment_blocks.values())[0]
                self.assertEqual(comments[0]['comment_id'],
                                 self.commit_comment1.pk)
            else:
                # All other files in the diff should show no comments on them.
                self.assertEqual(comment_blocks, {})

    def test_comment_data_with_commit_range2(self) -> None:
        """Testing ReviewsDiffViewerView comment data with a commit range in
        the middle
        """
        response = self.client.get(
            local_site_reverse(
                'view-diff-revision',
                kwargs={
                    'review_request_id': self.review_request.display_id,
                    'revision': self.diffset.revision,
                }),
            {
                'base-commit-id': self.diff_commits[1].pk,
                'tip-commit-id': self.diff_commits[2].pk,
            })
        self.assertEqual(response.status_code, 200)

        files = response.context['diff_context']['files']

        for f in files:
            comment_blocks = f['serialized_comment_blocks']

            if f['id'] == self.commit_comment2.filediff_id:
                self.assertEqual(len(comment_blocks), 1)

                comments = list(comment_blocks.values())[0]
                self.assertEqual(comments[0]['comment_id'],
                                 self.commit_comment2.pk)
            else:
                # All other files in the diff should show no comments on them.
                self.assertEqual(comment_blocks, {})

    def test_commits_in_diff_context(self) -> None:
        """Testing that commits are listed properly in diff context"""
        response = self.client.get(
            local_site_reverse(
                'view-diff-revision',
                kwargs={
                    'review_request_id': self.review_request.display_id,
                    'revision': self.diffset.revision,
                },
            ),
            {
                'base-commit-id': self.diff_commits[1].pk,
                'tip-commit-id': self.diff_commits[2].pk,
            })
        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            response.context['diff_context']['commits'],
            [
                {
                    'author_name': 'Author',
                    'commit_id': 'r1',
                    'commit_message': 'Commit message',
                    'id': 1,
                    'parent_id': 'r0',
                },
                {
                    'author_name': 'Author',
                    'commit_id': 'r2',
                    'commit_message': 'Commit message',
                    'id': 2,
                    'parent_id': 'r1',
                },
                {
                    'author_name': 'Author',
                    'commit_id': 'r3',
                    'commit_message': 'Commit message',
                    'id': 3,
                    'parent_id': 'r2',
                },
                {
                    'author_name': 'Author',
                    'commit_id': 'r4',
                    'commit_message': 'Commit message',
                    'id': 4,
                    'parent_id': 'r3',
                },
            ])

    def test_commits_in_diff_context_with_draft(self) -> None:
        """Testing that commits are listed properly in diff context with a
        draft diffset
        """
        self.client.login(username='doc', password='doc')

        draft_diffset = self.create_diffset(
            review_request=self.review_request,
            revision=2,
            draft=True)

        self.create_diffcommit(
            diffset=draft_diffset,
            commit_id='r5',
            parent_id='r4',
            diff_contents=self._COMMITS[0]['diff'])
        draft_diffset.finalize_commit_series(
            cumulative_diff=self._COMMITS[0]['diff'],
            validation_info=None,
            validate=False,
            save=True)

        response = self.client.get(
            local_site_reverse(
                'view-diff-revision',
                kwargs={
                    'review_request_id': self.review_request.display_id,
                    'revision': draft_diffset.revision,
                },
            ))
        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            response.context['diff_context']['commits'],
            [
                {
                    'author_name': 'Author',
                    'commit_id': 'r5',
                    'commit_message': 'Commit message',
                    'id': 5,
                    'parent_id': 'r4',
                },
            ])
