"""Unit tests for reviewboard.reviews.views.ReviewsDiffViewerView."""

from __future__ import unicode_literals

from reviewboard.site.urlresolvers import local_site_reverse
from reviewboard.testing import TestCase


class ReviewsDiffViewerViewTests(TestCase):
    """Unit tests for reviewboard.reviews.views.ReviewsDiffViewerView."""

    fixtures = ['test_users', 'test_scmtools']

    # Bug 892
    def test_interdiff(self):
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

        self.assertEqual(files[0]['depot_filename'], '/newfile')
        self.assertIn('interfilediff', files[0])

        self.assertEqual(files[1]['depot_filename'], '/readme')
        self.assertIn('interfilediff', files[1])

    # Bug 847
    def test_interdiff_new_file(self):
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

        self.assertEqual(files[0]['depot_filename'], '/newfile')
        self.assertIn('interfilediff', files[0])

    def test_with_filenames_option(self):
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

    def test_with_filenames_option_normalized(self):
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
