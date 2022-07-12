"""Unit tests for reviewboard.diffviewer.parser."""

from djblets.testing.decorators import add_fixtures

from reviewboard.deprecation import RemovedInReviewBoard60Warning
from reviewboard.diffviewer.testing.mixins import DiffParserTestingMixin
from reviewboard.diffviewer.parser import (BaseDiffParser,
                                           DiffParser,
                                           ParsedDiff,
                                           ParsedDiffChange,
                                           ParsedDiffFile)
from reviewboard.testing import TestCase


class ParsedDiffTests(TestCase):
    """Unit tests for reviewboard.diffviewer.parser.ParsedDiff."""

    def test_init(self):
        """Testing ParsedDiff.__init__"""
        parser = BaseDiffParser(b'')
        parsed_diff = ParsedDiff(parser=parser)

        self.assertIs(parsed_diff.parser, parser)


class ParsedDiffChangeTests(TestCase):
    """Unit tests for reviewboard.diffviewer.parser.ParsedDiffChange."""

    def test_init(self):
        """Testing ParsedDiffChange.__init__"""
        parser = BaseDiffParser(b'')
        parsed_diff = ParsedDiff(parser=parser)
        parsed_diff_change = ParsedDiffChange(parsed_diff=parsed_diff)

        self.assertEqual(parsed_diff.changes, [parsed_diff_change])
        self.assertIs(parsed_diff_change.parent_parsed_diff, parsed_diff)


class ParsedDiffFileTests(TestCase):
    """Unit tests for reviewboard.diffviewer.parser.ParsedDiffFile."""

    def test_init_with_parsed_diff_change(self):
        """Testing ParsedDiffFile.__init__ with parsed_diff_change="""
        parser = BaseDiffParser(b'')
        parsed_diff = ParsedDiff(parser=parser)
        parsed_diff_change = ParsedDiffChange(parsed_diff=parsed_diff)
        parsed_diff_file = ParsedDiffFile(
            parsed_diff_change=parsed_diff_change)

        self.assertIs(parsed_diff_file.parser, parser)
        self.assertEqual(parsed_diff_change.files, [parsed_diff_file])
        self.assertEqual(parsed_diff_file.parent_parsed_diff_change,
                         parsed_diff_change)

    def test_init_with_parser(self):
        """Testing ParsedDiffFile.__init__ with parser="""
        parser = BaseDiffParser(b'')

        message = (
            'Diff parsers must pass a ParsedDiffChange as the '
            'parsed_diff_change= parameter when creating a ParsedDiffFile. '
            'They should no longer pass a parser= parameter. This will be '
            'mandatory in Review Board 6.0.'
        )

        with self.assertWarns(cls=RemovedInReviewBoard60Warning,
                              message=message):
            parsed_diff_file = ParsedDiffFile(parser=parser)

        self.assertIs(parsed_diff_file.parser, parser)
        self.assertIsNone(parsed_diff_file.parent_parsed_diff_change)

    def test_init_with_no_parser_or_parsed_diff_change(self):
        """Testing ParsedDiffFile.__init__ without parsed_diff_change= or
        parser=
        """
        message = (
            'Diff parsers must pass a ParsedDiffChange as the '
            'parsed_diff_change= parameter when creating a ParsedDiffFile. '
            'They should no longer pass a parser= parameter. This will be '
            'mandatory in Review Board 6.0.'
        )

        with self.assertWarns(cls=RemovedInReviewBoard60Warning,
                              message=message):
            parsed_diff_file = ParsedDiffFile()

        self.assertIsNone(parsed_diff_file.parser)
        self.assertIsNone(parsed_diff_file.parent_parsed_diff_change)


class DiffParserTest(DiffParserTestingMixin, TestCase):
    """Unit tests for reviewboard.diffviewer.parser.DiffParser."""

    def test_form_feed(self):
        """Testing DiffParser with a form feed in the file"""
        diff = (
            b'--- README  123\n'
            b'+++ README  (new)\n'
            b'@@ -1,4 +1,6 @@\n'
            b' Line 1\n'
            b' Line 2\n'
            b'+\x0c\n'
            b'+Inserted line\n'
            b' Line 3\n'
            b' Line 4\n'
        )

        parsed_files = DiffParser(diff).parse()
        self.assertEqual(len(parsed_files), 1)

        self.assert_parsed_diff_file(
            parsed_files[0],
            orig_filename=b'README',
            orig_file_details=b'123',
            modified_filename=b'README',
            modified_file_details=b'(new)',
            insert_count=2,
            data=diff)

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
            b'+blah?!\n'
        )

        parsed_files = DiffParser(diff).parse()
        self.assertEqual(len(parsed_files), 1)

        self.assert_parsed_diff_file(
            parsed_files[0],
            orig_filename=b'README',
            orig_file_details=b'123',
            modified_filename=b'README',
            modified_file_details=b'(new)',
            insert_count=3,
            delete_count=4,
            data=diff)

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

    def test_parsed_diff_extra_data(self):
        """Testing custom DiffParser populating a ParsedDiff's extra_data"""
        class CustomParser(DiffParser):
            def parse(self):
                result = super(CustomParser, self).parse()

                self.parsed_diff.extra_data = {
                    'foo': True,
                }

                return result

        diff = self.DEFAULT_FILEDIFF_DATA_DIFF
        parsed_diff_file = CustomParser(diff).parse_diff()

        self.assertEqual(parsed_diff_file.extra_data, {'foo': True})

    def test_parsed_diff_change_extra_data(self):
        """Testing custom DiffParser populating a ParsedDiffChange's
        extra_data
        """
        class CustomParser(DiffParser):
            def parse(self):
                result = super(CustomParser, self).parse()

                self.parsed_diff_change.extra_data = {
                    'foo': True,
                }

                return result

        diff = self.DEFAULT_FILEDIFF_DATA_DIFF
        parsed_diff_file = CustomParser(diff).parse_diff()

        changes = parsed_diff_file.changes
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0].extra_data, {'foo': True})

    def test_parsed_diff_file_extra_data(self):
        """Testing custom DiffParser populating a ParsedDiffFile's extra_data
        """
        class CustomParser(DiffParser):
            def parse_diff_header(self, linenum, parsed_file):
                parsed_file.extra_data = {'foo': True}

                return super(CustomParser, self).parse_diff_header(
                    linenum, parsed_file)

        diff = self.DEFAULT_FILEDIFF_DATA_DIFF
        parsed_diff_file = CustomParser(diff).parse_diff()

        changes = parsed_diff_file.changes
        self.assertEqual(len(changes), 1)

        files = changes[0].files
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0].extra_data, {'foo': True})

    def test_parse_diff_with_get_orig_commit_id(self):
        """Testing DiffParser.parse_diff with get_orig_commit_id() returning
        a value
        """
        class CustomParser(DiffParser):
            def get_orig_commit_id(self):
                return b'abc123'

        parser = CustomParser(self.DEFAULT_FILEDIFF_DATA_DIFF)

        message = (
            'CustomParser.get_orig_commit_id() will no longer be supported '
            'in Review Board 6.0. Please set the commit ID in '
            'self.parsed_diff_change.parent_commit_id, and set '
            'parsed_diff_change.uses_commit_ids_as_revisions = True.'
        )

        with self.assertWarns(RemovedInReviewBoard60Warning, message):
            parsed_diff_file = parser.parse_diff()

        changes = parsed_diff_file.changes
        self.assertEqual(len(changes), 1)

        self.assertTrue(parsed_diff_file.uses_commit_ids_as_revisions)
        self.assertEqual(changes[0].parent_commit_id, b'abc123')
