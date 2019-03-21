"""Unit tests for reviewboard.reviews.views.DownloadRawDiffView."""

from __future__ import unicode_literals

from reviewboard.testing import TestCase


class DownloadRawDiffViewTests(TestCase):
    """Unit tests for reviewboard.reviews.views.DownloadRawDiffView."""

    fixtures = ['test_users', 'test_scmtools']

    # Bug #3384
    def test_sends_correct_content_disposition(self):
        """Testing DownloadRawDiffView sends correct Content-Disposition"""
        review_request = self.create_review_request(create_repository=True,
                                                    publish=True)

        self.create_diffset(review_request=review_request)

        response = self.client.get('/r/%d/diff/raw/' % review_request.pk)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Disposition'],
                         'attachment; filename=diffset')

    # Bug #3704
    def test_normalize_commas_in_filename(self):
        """Testing DownloadRawDiffView removes commas in filename"""
        review_request = self.create_review_request(create_repository=True,
                                                    publish=True)

        # Create a diffset with a comma in its name.
        self.create_diffset(review_request=review_request, name='test, comma')

        response = self.client.get('/r/%d/diff/raw/' % review_request.pk)
        content_disposition = response['Content-Disposition']
        filename = content_disposition[len('attachment; filename='):]
        self.assertFalse(',' in filename)

    def test_with_commit_history(self):
        """Testing DiffParser.raw_diff with commit history contains only
        cumulative diff
        """
        review_request = self.create_review_request(create_repository=True,
                                                    publish=True)
        diffset = self.create_diffset(review_request=review_request)

        self.create_diffcommit(
            diffset=diffset,
            commit_id='r1',
            parent_id='r0',
            diff_contents=(
                b'diff --git a/ABC b/ABC\n'
                b'index 94bdd3e..197009f 100644\n'
                b'--- ABC\n'
                b'+++ ABC\n'
                b'@@ -1,1 +1,1 @@\n'
                b'-line!\n'
                b'+line..\n'
            ))
        self.create_diffcommit(
            diffset=diffset,
            commit_id='r2',
            parent_id='r1',
            diff_contents=(
                b'diff --git a/README b/README\n'
                b'index 94bdd3e..197009f 100644\n'
                b'--- README\n'
                b'+++ README\n'
                b'@@ -1,1 +1,1 @@\n'
                b'-Hello, world!\n'
                b'+Hi, world!\n'
            ))
        self.create_diffcommit(
            diffset=diffset,
            commit_id='r4',
            parent_id='r3',
            diff_contents=(
                b'diff --git a/README b/README\n'
                b'index 197009f..87abad9 100644\n'
                b'--- README\n'
                b'+++ README\n'
                b'@@ -1,1 +1,1 @@\n'
                b'-Hi, world!\n'
                b'+Yo, world.\n'
            ))

        cumulative_diff = (
            b'diff --git a/ABC b/ABC\n'
            b'index 94bdd3e..197009f 100644\n'
            b'--- ABC\n'
            b'+++ ABC\n'
            b'@@ -1,1 +1,1 @@\n'
            b'-line!\n'
            b'+line..\n'
            b'diff --git a/README b/README\n'
            b'index 94bdd3e..87abad9 100644\n'
            b'--- README\n'
            b'+++ README\n'
            b'@@ -1,1 +1,1 @@\n'
            b'-Hello, world!\n'
            b'+Yo, world.\n'
        )

        diffset.finalize_commit_series(
            cumulative_diff=cumulative_diff,
            validation_info=None,
            validate=False,
            save=True)

        response = self.client.get('/r/%d/diff/raw/' % review_request.pk)
        self.assertEqual(response.content, cumulative_diff)
