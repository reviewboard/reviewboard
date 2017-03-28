from __future__ import unicode_literals

import nose
from django.core.files.uploadedfile import SimpleUploadedFile
from kgb import SpyAgency

from reviewboard.admin.import_utils import has_module
from reviewboard.diffviewer.diffutils import (get_original_file,
                                              get_patched_file,
                                              patch)
from reviewboard.diffviewer.forms import UploadDiffForm
from reviewboard.scmtools.models import Repository, Tool
from reviewboard.testing import TestCase


class UploadDiffFormTests(SpyAgency, TestCase):
    """Unit tests for UploadDiffForm."""

    fixtures = ['test_scmtools']

    def test_create(self):
        """Testing UploadDiffForm.create"""
        diff_file = SimpleUploadedFile('diff', self.DEFAULT_GIT_FILEDIFF_DATA,
                                       content_type='text/x-patch')

        repository = self.create_repository(tool_name='Test')

        self.spy_on(repository.get_file_exists,
                    call_fake=lambda *args, **kwargs: True)

        form = UploadDiffForm(
            repository=repository,
            data={
                'basedir': '/',
                'base_commit_id': '1234',
            },
            files={
                'path': diff_file,
            })
        self.assertTrue(form.is_valid())

        diffset = form.create(diff_file)
        self.assertEqual(diffset.files.count(), 1)
        self.assertEqual(diffset.basedir, '/')
        self.assertEqual(diffset.base_commit_id, '1234')

    def test_create_filters_parent_diffs(self):
        """Testing UploadDiffForm.create filters parent diff files"""
        saw_file_exists = {}

        def get_file_exists(repository, filename, revision, *args, **kwargs):
            saw_file_exists[(filename, revision)] = True
            return True

        parent_diff_1 = (
            b'diff --git a/README b/README\n'
            b'index d6613f4..5b50865 100644\n'
            b'--- README\n'
            b'+++ README\n'
            b'@@ -2 +2 @@\n'
            b'-blah..\n'
            b'+blah blah\n'
        )
        parent_diff_2 = (
            b'diff --git a/UNUSED b/UNUSED\n'
            b'index 1234567..5b50866 100644\n'
            b'--- UNUSED\n'
            b'+++ UNUSED\n'
            b'@@ -1,1 +1,1 @@\n'
            b'-foo\n'
            b'+bar\n'
        )
        parent_diff = parent_diff_1 + parent_diff_2

        diff_file = SimpleUploadedFile('diff', self.DEFAULT_GIT_FILEDIFF_DATA,
                                       content_type='text/x-patch')
        parent_diff_file = SimpleUploadedFile('parent_diff', parent_diff,
                                              content_type='text/x-patch')

        repository = self.create_repository(tool_name='Test')
        self.spy_on(repository.get_file_exists, call_fake=get_file_exists)

        form = UploadDiffForm(
            repository=repository,
            data={
                'basedir': '/',
            },
            files={
                'path': diff_file,
                'parent_diff_path': parent_diff_file,
            })
        self.assertTrue(form.is_valid())

        diffset = form.create(diff_file, parent_diff_file)
        self.assertEqual(diffset.files.count(), 1)

        filediff = diffset.files.get()
        self.assertEqual(filediff.diff, self.DEFAULT_GIT_FILEDIFF_DATA)
        self.assertEqual(filediff.parent_diff, parent_diff_1)

        self.assertIn(('/README', 'd6613f4'), saw_file_exists)
        self.assertNotIn(('/UNUSED', '1234567'), saw_file_exists)
        self.assertEqual(len(saw_file_exists), 1)

    def test_create_with_parser_get_orig_commit_id(self):
        """Testing UploadDiffForm.create uses correct base revision returned
        by DiffParser.get_orig_commit_id
        """
        diff = (
            b'# Node ID a6fc203fee9091ff9739c9c00cd4a6694e023f48\n'
            b'# Parent  7c4735ef51a7c665b5654f1a111ae430ce84ebbd\n'
            b'diff --git a/doc/readme b/doc/readme\n'
            b'--- a/doc/readme\n'
            b'+++ b/doc/readme\n'
            b'@@ -1,3 +1,3 @@\n'
            b' Hello\n'
            b'-\n'
            b'+...\n'
            b' goodbye\n'
        )

        parent_diff = (
            b'# Node ID 7c4735ef51a7c665b5654f1a111ae430ce84ebbd\n'
            b'# Parent  661e5dd3c4938ecbe8f77e2fdfa905d70485f94c\n'
            b'diff --git a/doc/newfile b/doc/newfile\n'
            b'new file mode 100644\n'
            b'--- /dev/null\n'
            b'+++ b/doc/newfile\n'
            b'@@ -0,0 +1,1 @@\n'
            b'+Lorem ipsum\n'
        )

        if not has_module('mercurial'):
            raise nose.SkipTest("Hg is not installed")

        diff_file = SimpleUploadedFile('diff', diff,
                                       content_type='text/x-patch')
        parent_diff_file = SimpleUploadedFile('parent_diff', parent_diff,
                                              content_type='text/x-patch')

        repository = Repository.objects.create(
            name='Test HG',
            path='scmtools/testdata/hg_repo',
            tool=Tool.objects.get(name='Mercurial'))

        form = UploadDiffForm(
            repository=repository,
            files={
                'path': diff_file,
                'parent_diff_path': parent_diff_file,
            })
        self.assertTrue(form.is_valid())

        diffset = form.create(diff_file, parent_diff_file)
        self.assertEqual(diffset.files.count(), 1)

        filediff = diffset.files.get()

        self.assertEqual(filediff.source_revision,
                         '661e5dd3c4938ecbe8f77e2fdfa905d70485f94c')

    def test_create_with_parent_filediff_with_move_and_no_change(self):
        """Testing UploadDiffForm.create with a parent diff consisting only
        of a move/rename without content change
        """
        revisions = [
            b'93e6b3e8944c48737cb11a1e52b046fa30aea7a9',
            b'4839fc480f47ca59cf05a9c39410ea744d1e17a2',
        ]

        parent_diff = SimpleUploadedFile(
            'parent_diff',
            (b'diff --git a/foo b/bar\n'
             b'similarity index 100%%\n'
             b'rename from foo\n'
             b'rename to bar\n'),
            content_type='text/x-patch')

        diff = SimpleUploadedFile(
            'diff',
            (b'diff --git a/bar b/bar\n'
             b'index %s..%s 100644\n'
             b'--- a/bar\n'
             b'+++ b/bar\n'
             b'@@ -1,2 +1,3 @@\n'
             b' Foo\n'
             b'+Bar\n') % (revisions[0], revisions[1]),
            content_type='text/x-patch')

        repository = self.create_repository(tool_name='Test')
        self.spy_on(repository.get_file_exists,
                    call_fake=lambda *args, **kwargs: True)

        # We will only be making one call to get_file and we can fake it out.
        self.spy_on(repository.get_file,
                    call_fake=lambda *args, **kwargs: b'Foo\n')
        self.spy_on(patch)

        form = UploadDiffForm(
            repository=repository,
            data={
                'basedir': '/',
            },
            files={
                'path': diff,
                'parent_diff_path': parent_diff,
            })
        self.assertTrue(form.is_valid())

        diffset = form.create(diff, parent_diff)
        self.assertEqual(diffset.files.count(), 1)

        f = diffset.files.get()
        self.assertEqual(f.source_revision, revisions[0])
        self.assertEqual(f.dest_detail, revisions[1])

        # We shouldn't call out to patch because the parent diff is just a
        # rename.
        original_file = get_original_file(f, None, ['ascii'])
        self.assertEqual(original_file, b'Foo\n')
        self.assertFalse(patch.spy.called)

        patched_file = get_patched_file(original_file, f, None)
        self.assertEqual(patched_file, b'Foo\nBar\n')
        self.assertTrue(patch.spy.called)

    def test_create_with_parent_filediff_with_move_and_change(self):
        """Testing UploadDiffForm.create with a parent diff consisting of a
        move/rename with content change
        """
        revisions = [
            b'93e6b3e8944c48737cb11a1e52b046fa30aea7a9',
            b'4839fc480f47ca59cf05a9c39410ea744d1e17a2',
            b'04861c126cfebd7e7cb93045ab0bff4a7acc4cf2',
        ]

        parent_diff = SimpleUploadedFile(
            'parent_diff',
            (b'diff --git a/foo b/bar\n'
             b'similarity index 55%%\n'
             b'rename from foo\n'
             b'rename to bar\n'
             b'index %s..%s 100644\n'
             b'--- a/foo\n'
             b'+++ b/bar\n'
             b'@@ -1,2 +1,3 @@\n'
             b' Foo\n'
             b'+Bar\n') % (revisions[0], revisions[1]),
            content_type='text/x-patch')

        diff = SimpleUploadedFile(
            'diff',
            (b'diff --git a/bar b/bar\n'
             b'index %s..%s 100644\n'
             b'--- a/bar\n'
             b'+++ b/bar\n'
             b'@@ -1,3 +1,4 @@\n'
             b' Foo\n'
             b' Bar\n'
             b'+Baz\n') % (revisions[1], revisions[2]),
            content_type='text/x-patch')

        repository = self.create_repository(tool_name='Test')
        self.spy_on(repository.get_file_exists,
                    call_fake=lambda *args, **kwargs: True)

        # We will only be making one call to get_file and we can fake it out.
        self.spy_on(repository.get_file,
                    call_fake=lambda *args, **kwargs: b'Foo\n')
        self.spy_on(patch)

        form = UploadDiffForm(
            repository=repository,
            data={
                'basedir': '/',
            },
            files={
                'path': diff,
                'parent_diff_path': parent_diff,
            })
        self.assertTrue(form.is_valid())

        diffset = form.create(diff, parent_diff)
        self.assertEqual(diffset.files.count(), 1)

        f = diffset.files.get()
        self.assertEqual(f.source_revision, revisions[0])
        self.assertEqual(f.dest_detail, revisions[2])

        original_file = get_original_file(f, None, ['ascii'])
        self.assertEqual(original_file, b'Foo\nBar\n')
        self.assertTrue(patch.spy.called)

        patched_file = get_patched_file(original_file, f, None)
        self.assertEqual(patched_file, b'Foo\nBar\nBaz\n')
        self.assertEqual(len(patch.spy.calls), 2)
