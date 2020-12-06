from __future__ import unicode_literals

from djblets.testing.decorators import add_fixtures

from reviewboard.diffviewer.parser import DiffParser
from reviewboard.testing import TestCase


class DiffParserTest(TestCase):
    """Unit tests for DiffParser."""

    def test_form_feed(self):
        """Testing DiffParser with a form feed in the file"""
        data = (
            b'--- README  123\n'
            b'+++ README  (new)\n'
            b'@@ -1,4 +1,6 @@\n'
            b' Line 1\n'
            b' Line 2\n'
            b'+\x0c\n'
            b'+Inserted line\n'
            b' Line 3\n'
            b' Line 4\n')
        files = DiffParser(data).parse()

        self.assertEqual(len(files), 1)
        self.assertEqual(files[0].insert_count, 2)
        self.assertEqual(files[0].delete_count, 0)
        self.assertEqual(files[0].data, data)

    def test_line_counts(self):
        """Testing DiffParser with insert/delete line counts"""
        diff = (
            b'+ This is some line before the change\n'
            b'- And another line\n'
            b'Index: foo\n'
            b'- One last.\n'
            b'--- README  123\n'
            b'+++ README  (new)\n'
            b'@@ -1,1 +1,1 @@\n'
            b'-blah blah\n'
            b'-blah\n'
            b'+blah!\n'
            b'-blah...\n'
            b'+blah?\n'
            b'-blah!\n'
            b'+blah?!\n')
        files = DiffParser(diff).parse()

        self.assertEqual(len(files), 1)
        self.assertEqual(files[0].insert_count, 3)
        self.assertEqual(files[0].delete_count, 4)

    @add_fixtures(['test_scmtools'])
    def test_raw_diff_with_diffset(self):
        """Testing DiffParser.raw_diff with DiffSet"""
        repository = self.create_repository(tool_name='Test')
        diffset = self.create_diffset(repository=repository)

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

        parser = DiffParser(b'')
        self.assertEqual(parser.raw_diff(diffset), cumulative_diff)

    @add_fixtures(['test_scmtools'])
    def test_raw_diff_with_diffcommit(self):
        """Testing DiffParser.raw_diff with DiffCommit"""
        repository = self.create_repository(tool_name='Test')
        diffset = self.create_diffset(repository=repository)

        commit1_diff = (
            b'diff --git a/ABC b/ABC\n'
            b'index 94bdd3e..197009f 100644\n'
            b'--- ABC\n'
            b'+++ ABC\n'
            b'@@ -1,1 +1,1 @@\n'
            b'-line!\n'
            b'+line..\n'
            b'diff --git a/FOO b/FOO\n'
            b'index 84bda3e..b975034 100644\n'
            b'--- FOO\n'
            b'+++ FOO\n'
            b'@@ -1,1 +0,0 @@\n'
            b'-Some line\n'
        )

        commit1 = self.create_diffcommit(
            diffset=diffset,
            commit_id='r1',
            parent_id='r0',
            diff_contents=commit1_diff)
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

        diffset.finalize_commit_series(
            cumulative_diff=(
                b'diff --git a/ABC b/ABC\n'
                b'index 94bdd3e..197009f 100644\n'
                b'--- ABC\n'
                b'+++ ABC\n'
                b'@@ -1,1 +1,1 @@\n'
                b'-line!\n'
                b'+line..\n'
                b'diff --git a/FOO b/FOO\n'
                b'index 84bda3e..b975034 100644\n'
                b'--- FOO\n'
                b'+++ FOO\n'
                b'@@ -1,1 +0,0 @@\n'
                b'-Some line\n'
                b'diff --git a/README b/README\n'
                b'index 94bdd3e..87abad9 100644\n'
                b'--- README\n'
                b'+++ README\n'
                b'@@ -1,1 +1,1 @@\n'
                b'-Hello, world!\n'
                b'+Yo, world.\n'
            ),
            validation_info=None,
            validate=False,
            save=True)

        parser = DiffParser(b'')
        self.assertEqual(parser.raw_diff(commit1), commit1_diff)

    def test_extra_data(self):
        """Testing custom DiffParser populating extra_data"""
        class CustomParser(DiffParser):
            def parse_diff_header(self, linenum, info):
                info['extra_data'] = {'foo': True}

                return super(CustomParser, self).parse_diff_header(
                    linenum, info)

        diff = (
            b'+ This is some line before the change\n'
            b'- And another line\n'
            b'Index: foo\n'
            b'- One last.\n'
            b'--- README  123\n'
            b'+++ README  (new)\n'
            b'@@ -1,1 +1,1 @@\n'
            b'-blah blah\n'
            b'-blah\n'
            b'+blah!\n'
            b'-blah...\n'
            b'+blah?\n'
            b'-blah!\n'
            b'+blah?!\n')

        files = CustomParser(diff).parse()

        self.assertEqual(len(files), 1)
        self.assertEqual(files[0].extra_data, {'foo': True})
