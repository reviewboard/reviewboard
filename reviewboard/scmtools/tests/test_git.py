# coding=utf-8

import os
import unittest

import kgb
from djblets.testing.decorators import add_fixtures

from reviewboard.diffviewer.parser import DiffParserError
from reviewboard.diffviewer.testing.mixins import DiffParserTestingMixin
from reviewboard.scmtools.core import PRE_CREATION
from reviewboard.scmtools.errors import SCMError, FileNotFoundError
from reviewboard.scmtools.git import ShortSHA1Error, GitClient, GitTool
from reviewboard.scmtools.tests.testcases import SCMTestCase
from reviewboard.testing.testcase import TestCase


class GitTests(DiffParserTestingMixin, kgb.SpyAgency, SCMTestCase):
    """Unit tests for Git."""

    fixtures = ['test_scmtools']

    ssh_required_system_exes = ['git']

    def setUp(self):
        super(GitTests, self).setUp()

        self.local_repo_path = os.path.join(os.path.dirname(__file__),
                                            '..', 'testdata', 'git_repo')
        self.git_ssh_path = ('localhost:%s'
                             % self.local_repo_path.replace('\\', '/'))
        remote_repo_path = 'git@github.com:reviewboard/reviewboard.git'
        remote_repo_raw_url = ('http://github.com/api/v2/yaml/blob/show/'
                               'reviewboard/reviewboard/<revision>')

        self.repository = self.create_repository(
            name='Git test repo',
            path=self.local_repo_path,
            tool_name='Git')
        self.remote_repository = self.create_repository(
            name='Remote Git test repo',
            path=remote_repo_path,
            raw_file_url=remote_repo_raw_url,
            tool_name='Git')

        try:
            self.tool = self.repository.get_scmtool()
            self.remote_tool = self.remote_repository.get_scmtool()
        except ImportError:
            raise unittest.SkipTest('git binary not found')

    def _read_diff_fixture(self, filename, expected_num_diffs):
        """Read a diff fixture from the test data.

        Args:
            filename (unicode):
                The name of the filename in the :file:`testdata` directory.

            expected_num_diffs (int):
                The expected number of files found in the fixture.

        Returns:
            tuple:
            A 2-tuple containing:

            1. The full diff from the file.
            2. Each diff in the file.

        Raises:
            AssertionError:
                The number of diffs found did not meet the expected number.
        """
        filename = os.path.join(os.path.dirname(__file__),
                                '..', 'testdata', filename)

        with open(filename, 'rb') as f:
            full_diff = f.read()

        diffs = []
        i1 = 0

        while True:
            i2 = full_diff.find(b'diff --git', i1 + 1)

            if i2 == -1:
                break

            diffs.append(full_diff[i1:i2])
            i1 = i2

        diffs.append(full_diff[i1:])

        self.assertEqual(len(diffs), expected_num_diffs)

        return full_diff, diffs

    def _get_file_in_diff(self, diff, filenum=0):
        files = self.tool.get_parser(diff).parse()
        self.assertTrue(filenum < len(files))
        return files[filenum]

    def test_ssh(self):
        """Testing a SSH-backed git repository"""
        self._test_ssh(self.git_ssh_path)

    def test_ssh_with_site(self):
        """Testing a SSH-backed git repository with a LocalSite"""
        self._test_ssh_with_site(self.git_ssh_path)

    def test_filemode_diff(self):
        """Testing parsing filemode changes Git diff"""
        diff1 = (
            b'diff --git a/testing b/testing\n'
            b'old mode 100755\n'
            b'new mode 100644\n'
            b'index e69de29..bcae657\n'
            b'--- a/testing\n'
            b'+++ b/testing\n'
            b'@@ -0,0 +1 @@\n'
            b'+ADD\n'
        )
        diff2 = (
            b'diff --git a/testing2 b/testing2\n'
            b'old mode 100644\n'
            b'new mode 100755\n'
        )
        diff = diff1 + diff2

        # NOTE: testing2 gets skipped, due to lack of changes we can
        #       represent.
        parsed_files = self.tool.get_parser(diff).parse()
        self.assertEqual(len(parsed_files), 1)

        self.assert_parsed_diff_file(
            parsed_files[0],
            orig_filename=b'testing',
            orig_file_details=b'e69de29',
            modified_filename=b'testing',
            modified_file_details=b'bcae657',
            old_unix_mode='100755',
            new_unix_mode='100644',
            insert_count=1,
            data=diff1)

    def test_filemode_with_following_diff(self):
        """Testing parsing filemode changes with following Git diff"""
        diff1 = (
            b'diff --git a/testing b/testing\n'
            b'old mode 100755\n'
            b'new mode 100644\n'
            b'index e69de29..bcae657\n'
            b'--- a/testing\n'
            b'+++ b/testing\n'
            b'@@ -0,0 +1 @@\n'
            b'+ADD\n'
        )
        diff2 = (
            b'diff --git a/testing2 b/testing2\n'
            b'old mode 100644\n'
            b'new mode 100755\n'
        )
        diff3 = (
            b'diff --git a/cfg/testcase.ini b/cfg/testcase.ini\n'
            b'index cc18ec8..5e70b73 100644\n'
            b'--- a/cfg/testcase.ini\n'
            b'+++ b/cfg/testcase.ini\n'
            b'@@ -1,6 +1,7 @@\n'
            b'+blah blah blah\n'
            b' [mysql]\n'
            b' host = localhost\n'
            b' port = 3306\n'
            b' user = user\n'
            b' pass = pass\n'
            b'-db = pyunit\n'
            b'+db = pyunit\n'
        )
        diff = diff1 + diff2 + diff3

        # NOTE: testing2 gets skipped, due to lack of changes we can
        #       represent.
        parsed_files = self.tool.get_parser(diff).parse()
        self.assertEqual(len(parsed_files), 2)

        self.assert_parsed_diff_file(
            parsed_files[0],
            orig_filename=b'testing',
            orig_file_details=b'e69de29',
            modified_filename=b'testing',
            modified_file_details=b'bcae657',
            old_unix_mode='100755',
            new_unix_mode='100644',
            insert_count=1,
            data=diff1)

        self.assert_parsed_diff_file(
            parsed_files[1],
            orig_filename=b'cfg/testcase.ini',
            orig_file_details=b'cc18ec8',
            modified_filename=b'cfg/testcase.ini',
            modified_file_details=b'5e70b73',
            old_unix_mode='100644',
            new_unix_mode='100644',
            insert_count=2,
            delete_count=1,
            data=diff3)

    def test_simple_diff(self):
        """Testing parsing simple Git diff"""
        diff = (
            b'diff --git a/cfg/testcase.ini b/cfg/testcase.ini\n'
            b'index cc18ec8..5e70b73 100644\n'
            b'--- a/cfg/testcase.ini\n'
            b'+++ b/cfg/testcase.ini\n'
            b'@@ -1,6 +1,7 @@\n'
            b'+blah blah blah\n'
            b' [mysql]\n'
            b' host = localhost\n'
            b' port = 3306\n'
            b' user = user\n'
            b' pass = pass\n'
            b'-db = pyunit\n'
            b'+db = pyunit\n'
        )

        parsed_files = self.tool.get_parser(diff).parse()
        self.assertEqual(len(parsed_files), 1)

        self.assert_parsed_diff_file(
            parsed_files[0],
            orig_filename=b'cfg/testcase.ini',
            orig_file_details=b'cc18ec8',
            modified_filename=b'cfg/testcase.ini',
            modified_file_details=b'5e70b73',
            old_unix_mode='100644',
            new_unix_mode='100644',
            insert_count=2,
            delete_count=1,
            data=diff)

    def test_diff_with_unicode(self):
        """Testing parsing Git diff with unicode characters"""
        diff = (
            'diff --git a/cfg/téstcase.ini b/cfg/téstcase.ini\n'
            'index cc18ec8..5e70b73 100644\n'
            '--- a/cfg/téstcase.ini\n'
            '+++ b/cfg/téstcase.ini\n'
            '@@ -1,6 +1,7 @@\n'
            '+blah blah blah\n'
            ' [mysql]\n'
            ' hóst = localhost\n'
            ' pórt = 3306\n'
            ' user = user\n'
            ' pass = pass\n'
            '-db = pyunít\n'
            '+db = pyunít\n'
        ).encode('utf-8')

        parsed_files = self.tool.get_parser(diff).parse()
        self.assertEqual(len(parsed_files), 1)

        self.assert_parsed_diff_file(
            parsed_files[0],
            orig_filename='cfg/téstcase.ini'.encode('utf-8'),
            orig_file_details=b'cc18ec8',
            modified_filename='cfg/téstcase.ini'.encode('utf-8'),
            modified_file_details=b'5e70b73',
            old_unix_mode='100644',
            new_unix_mode='100644',
            insert_count=2,
            delete_count=1,
            data=diff)

    def test_diff_with_tabs_after_filename(self):
        """Testing parsing Git diffs with tabs after the filename"""
        diff = (
            b'diff --git a/README b/README\n'
            b'index 712544e4343bf04967eb5ea80257f6c64d6f42c7..'
            b'f88b7f15c03d141d0bb38c8e49bb6c411ebfe1f1 100644\n'
            b'--- a/README\t\n'
            b'+++ b/README\t\n'
            b'@ -1,1 +1,1 @@\n'
            b'-blah blah\n'
            b'+blah\n'
            b'-\n'
            b'1.7.1\n'
        )

        parsed_files = self.tool.get_parser(diff).parse()
        self.assertEqual(len(parsed_files), 1)

        self.assert_parsed_diff_file(
            parsed_files[0],
            orig_filename=b'README',
            orig_file_details=b'712544e4343bf04967eb5ea80257f6c64d6f42c7',
            modified_filename=b'README',
            modified_file_details=b'f88b7f15c03d141d0bb38c8e49bb6c411ebfe1f1',
            old_unix_mode='100644',
            new_unix_mode='100644',
            insert_count=1,
            delete_count=2,
            data=diff)

    def test_new_file_diff(self):
        """Testing parsing Git diff with new file"""
        diff = (
            b'diff --git a/IAMNEW b/IAMNEW\n'
            b'new file mode 100644\n'
            b'index 0000000..e69de29\n'
            b'--- /dev/null\n'
            b'+++ b/IAMNEW\n'
            b'@@ -0,0 +1,1 @@\n'
            b'+Hello\n'
        )

        parsed_files = self.tool.get_parser(diff).parse()
        self.assertEqual(len(parsed_files), 1)

        self.assert_parsed_diff_file(
            parsed_files[0],
            orig_filename=b'IAMNEW',
            orig_file_details=PRE_CREATION,
            modified_filename=b'IAMNEW',
            modified_file_details=b'e69de29',
            new_unix_mode='100644',
            insert_count=1,
            data=diff)

    def test_new_file_no_content_diff(self):
        """Testing parsing Git diff new file, no content"""
        diff = (
            b'diff --git a/newfile b/newfile\n'
            b'new file mode 100644\n'
            b'index 0000000..e69de29\n'
        )

        parsed_files = self.tool.get_parser(diff).parse()
        self.assertEqual(len(parsed_files), 1)

        self.assert_parsed_diff_file(
            parsed_files[0],
            orig_filename=b'newfile',
            orig_file_details=PRE_CREATION,
            modified_filename=b'newfile',
            modified_file_details=b'e69de29',
            new_unix_mode='100644',
            data=diff)

    def test_new_file_no_content_with_following_diff(self):
        """Testing parsing Git diff new file, no content, with following"""
        diff1 = (
            b'diff --git a/newfile b/newfile\n'
            b'new file mode 100644\n'
            b'index 0000000..e69de29\n'
        )
        diff2 = (
            b'diff --git a/cfg/testcase.ini b/cfg/testcase.ini\n'
            b'index cc18ec8..5e70b73 100644\n'
            b'--- a/cfg/testcase.ini\n'
            b'+++ b/cfg/testcase.ini\n'
            b'@@ -1,6 +1,7 @@\n'
            b'+blah blah blah\n'
            b' [mysql]\n'
            b' host = localhost\n'
            b' port = 3306\n'
            b' user = user\n'
            b' pass = pass\n'
            b'-db = pyunit\n'
            b'+db = pyunit\n'
        )
        diff = diff1 + diff2

        parsed_files = self.tool.get_parser(diff).parse()
        self.assertEqual(len(parsed_files), 2)

        self.assert_parsed_diff_file(
            parsed_files[0],
            orig_filename=b'newfile',
            orig_file_details=PRE_CREATION,
            modified_filename=b'newfile',
            modified_file_details=b'e69de29',
            new_unix_mode='100644',
            data=diff1)

        self.assert_parsed_diff_file(
            parsed_files[1],
            orig_filename=b'cfg/testcase.ini',
            orig_file_details=b'cc18ec8',
            modified_filename=b'cfg/testcase.ini',
            modified_file_details=b'5e70b73',
            old_unix_mode='100644',
            new_unix_mode='100644',
            insert_count=2,
            delete_count=1,
            data=diff2)

    def test_del_file_diff(self):
        """Testing parsing Git diff with deleted file"""
        diff = (
            b'diff --git a/OLDFILE b/OLDFILE\n'
            b'deleted file mode 100644\n'
            b'index 8ebcb01..0000000\n'
            b'--- a/OLDFILE\n'
            b'+++ /dev/null\n'
            b'@@ -1,1 +0,0 @@\n'
            b'-Goodbye\n'
        )

        parsed_files = self.tool.get_parser(diff).parse()
        self.assertEqual(len(parsed_files), 1)

        self.assert_parsed_diff_file(
            parsed_files[0],
            orig_filename=b'OLDFILE',
            orig_file_details=b'8ebcb01',
            modified_filename=b'OLDFILE',
            modified_file_details=b'0000000',
            old_unix_mode='100644',
            deleted=True,
            delete_count=1,
            data=diff)

    def test_del_file_no_content_diff(self):
        """Testing parsing Git diff with deleted file, no content"""
        diff = (
            b'diff --git a/empty b/empty\n'
            b'deleted file mode 100644\n'
            b'index e69de29bb2d1d6434b8b29ae775ad8c2e48c5391..'
            b'0000000000000000000000000000000000000000\n'
        )

        parsed_files = self.tool.get_parser(diff).parse()
        self.assertEqual(len(parsed_files), 1)

        self.assert_parsed_diff_file(
            parsed_files[0],
            orig_filename=b'empty',
            orig_file_details=b'e69de29bb2d1d6434b8b29ae775ad8c2e48c5391',
            modified_filename=b'empty',
            modified_file_details=b'0000000000000000000000000000000000000000',
            old_unix_mode='100644',
            deleted=True,
            data=diff)

    def test_del_file_no_content_with_following_diff(self):
        """Testing parsing Git diff with deleted file, no content, with
        following
        """
        diff1 = (
            b'diff --git a/empty b/empty\n'
            b'deleted file mode 100644\n'
            b'index e69de29bb2d1d6434b8b29ae775ad8c2e48c5391..'
            b'0000000000000000000000000000000000000000\n'
        )
        diff2 = (
            b'diff --git a/foo/bar b/foo/bar\n'
            b'index 484ba93ef5b0aed5b72af8f4e9dc4cfd10ef1a81..'
            b'0ae4095ddfe7387d405bd53bd59bbb5d861114c5 100644\n'
            b'--- a/foo/bar\n'
            b'+++ b/foo/bar\n'
            b'@@ -1 +1,2 @@\n'
            b'+Hello!\n'
            b'blah\n'
        )
        diff = diff1 + diff2

        parsed_files = self.tool.get_parser(diff).parse()
        self.assertEqual(len(parsed_files), 2)

        self.assert_parsed_diff_file(
            parsed_files[0],
            orig_filename=b'empty',
            orig_file_details=b'e69de29bb2d1d6434b8b29ae775ad8c2e48c5391',
            modified_filename=b'empty',
            modified_file_details=b'0000000000000000000000000000000000000000',
            old_unix_mode='100644',
            deleted=True,
            data=diff1)

        self.assert_parsed_diff_file(
            parsed_files[1],
            orig_filename=b'foo/bar',
            orig_file_details=b'484ba93ef5b0aed5b72af8f4e9dc4cfd10ef1a81',
            modified_filename=b'foo/bar',
            modified_file_details=b'0ae4095ddfe7387d405bd53bd59bbb5d861114c5',
            old_unix_mode='100644',
            new_unix_mode='100644',
            insert_count=1,
            data=diff2)

    def test_binary_diff(self):
        """Testing parsing Git diff with binary"""
        diff = (
            b'diff --git a/pysvn-1.5.1.tar.gz b/pysvn-1.5.1.tar.gz\n'
            b'new file mode 100644\n'
            b'index 0000000..86b520c\n'
            b'Binary files /dev/null and b/pysvn-1.5.1.tar.gz differ\n'
        )

        parsed_files = self.tool.get_parser(diff).parse()
        self.assertEqual(len(parsed_files), 1)

        self.assert_parsed_diff_file(
            parsed_files[0],
            orig_filename=b'pysvn-1.5.1.tar.gz',
            orig_file_details=PRE_CREATION,
            modified_filename=b'pysvn-1.5.1.tar.gz',
            modified_file_details=b'86b520c',
            new_unix_mode='100644',
            binary=True,
            data=diff)

    def test_git_new_single_binary_diff(self):
        """Testing parsing Git diff with base64 binary and a new file"""
        full_diff, diffs = self._read_diff_fixture(
            'git_new_single_binary.diff',
            expected_num_diffs=2)

        parsed_files = self.tool.get_parser(full_diff).parse()
        self.assertEqual(len(parsed_files), 2)

        self.assert_parsed_diff_file(
            parsed_files[0],
            orig_filename=b'Checked.svg',
            orig_file_details=PRE_CREATION,
            modified_filename=b'Checked.svg',
            modified_file_details=b'',
            new_unix_mode='100644',
            insert_count=9,
            data=diffs[0])

        self.assert_parsed_diff_file(
            parsed_files[1],
            orig_filename=b'dialog.jpg',
            orig_file_details=b'e69de29bb2d1d6434b8b29ae775ad8c2e48c5391',
            modified_filename=b'dialog.jpg',
            modified_file_details=b'5503573346e25878d57775ed7caf88f2eb7a7d98',
            new_unix_mode='100644',
            binary=True,
            data=diffs[1])

    def test_git_new_binaries_diff(self):
        """Testing parsing Git diff with base64 binaries and new files"""
        full_diff, diffs = self._read_diff_fixture(
            'git_new_binaries.diff',
            expected_num_diffs=3)

        parsed_files = self.tool.get_parser(full_diff).parse()
        self.assertEqual(len(parsed_files), 3)

        self.assert_parsed_diff_file(
            parsed_files[0],
            orig_filename=b'other.png',
            orig_file_details=b'e69de29bb2d1d6434b8b29ae775ad8c2e48c5391',
            modified_filename=b'other.png',
            modified_file_details=b'fddeadc701ac6dd751b8fc70fe128bd29e54b9b0',
            new_unix_mode='100644',
            binary=True,
            data=diffs[0])

        self.assert_parsed_diff_file(
            parsed_files[1],
            orig_filename=b'initial.png',
            orig_file_details=b'fddeadc701ac6dd751b8fc70fe128bd29e54b9b0',
            modified_filename=b'initial.png',
            modified_file_details=b'532716ada15dc62ddf8c59618b926f34d4727d77',
            binary=True,
            data=diffs[1])

        self.assert_parsed_diff_file(
            parsed_files[2],
            orig_filename=b'xtxt.txt',
            orig_file_details=PRE_CREATION,
            modified_filename=b'xtxt.txt',
            modified_file_details=b'',
            new_unix_mode='100644',
            insert_count=1,
            data=diffs[2])

    def test_complex_diff(self):
        """Testing parsing Git diff with existing and new files"""
        full_diff, diffs = self._read_diff_fixture(
            'git_complex.diff',
            expected_num_diffs=7)

        parsed_files = self.tool.get_parser(full_diff).parse()
        self.assertEqual(len(parsed_files), 7)

        self.assert_parsed_diff_file(
            parsed_files[0],
            orig_filename=b'cfg/testcase.ini',
            orig_file_details=b'5e35098',
            modified_filename=b'cfg/testcase.ini',
            modified_file_details=b'e254ef4',
            old_unix_mode='100644',
            new_unix_mode='100644',
            insert_count=2,
            delete_count=1,
            data=diffs[0])

        self.assert_parsed_diff_file(
            parsed_files[1],
            orig_filename=b'tests/models.py',
            orig_file_details=PRE_CREATION,
            modified_filename=b'tests/models.py',
            modified_file_details=b'e69de29',
            new_unix_mode='100644',
            data=diffs[1])

        self.assert_parsed_diff_file(
            parsed_files[2],
            orig_filename=b'tests/tests.py',
            orig_file_details=PRE_CREATION,
            modified_filename=b'tests/tests.py',
            modified_file_details=b'e279a06',
            new_unix_mode='100644',
            insert_count=2,
            data=diffs[2])

        self.assert_parsed_diff_file(
            parsed_files[3],
            orig_filename=b'pysvn-1.5.1.tar.gz',
            orig_file_details=PRE_CREATION,
            modified_filename=b'pysvn-1.5.1.tar.gz',
            modified_file_details=b'86b520c',
            new_unix_mode='100644',
            binary=True,
            data=diffs[3])

        self.assert_parsed_diff_file(
            parsed_files[4],
            orig_filename=b'readme',
            orig_file_details=b'5e35098',
            modified_filename=b'readme',
            modified_file_details=b'e254ef4',
            old_unix_mode='100644',
            new_unix_mode='100644',
            insert_count=1,
            delete_count=1,
            data=diffs[4])

        self.assert_parsed_diff_file(
            parsed_files[5],
            orig_filename=b'OLDFILE',
            orig_file_details=b'8ebcb01',
            modified_filename=b'OLDFILE',
            modified_file_details=b'0000000',
            old_unix_mode='100644',
            deleted=True,
            delete_count=1,
            data=diffs[5])

        self.assert_parsed_diff_file(
            parsed_files[6],
            orig_filename=b'readme2',
            orig_file_details=b'5e43098',
            modified_filename=b'readme2',
            modified_file_details=b'e248ef4',
            old_unix_mode='100644',
            new_unix_mode='100644',
            insert_count=1,
            delete_count=1,
            data=diffs[6])

    def test_parse_diff_with_index_range(self):
        """Testing Git diff parsing with an index range"""
        diff = (
            b'diff --git a/foo/bar b/foo/bar2\n'
            b'similarity index 88%\n'
            b'rename from foo/bar\n'
            b'rename to foo/bar2\n'
            b'index 612544e4343bf04967eb5ea80257f6c64d6f42c7..'
            b'e88b7f15c03d141d0bb38c8e49bb6c411ebfe1f1 100644\n'
            b'--- a/foo/bar\n'
            b'+++ b/foo/bar2\n'
            b'@ -1,1 +1,1 @@\n'
            b'-blah blah\n'
            b'+blah\n'
        )

        parsed_files = self.tool.get_parser(diff).parse()
        self.assertEqual(len(parsed_files), 1)

        self.assert_parsed_diff_file(
            parsed_files[0],
            orig_filename=b'foo/bar',
            orig_file_details=b'612544e4343bf04967eb5ea80257f6c64d6f42c7',
            modified_filename=b'foo/bar2',
            modified_file_details=b'e88b7f15c03d141d0bb38c8e49bb6c411ebfe1f1',
            old_unix_mode='100644',
            new_unix_mode='100644',
            moved=True,
            insert_count=1,
            delete_count=1,
            data=diff)

    def test_parse_diff_with_deleted_binary_files(self):
        """Testing Git diff parsing with deleted binary files"""
        diff1 = (
            b'diff --git a/foo.bin b/foo.bin\n'
            b'deleted file mode 100644\n'
            b'Binary file foo.bin has changed\n'
        )
        diff2 = (
            b'diff --git a/bar.bin b/bar.bin\n'
            b'deleted file mode 100644\n'
            b'Binary file bar.bin has changed\n'
        )
        diff = diff1 + diff2

        parsed_files = self.tool.get_parser(diff).parse()
        self.assertEqual(len(parsed_files), 2)

        self.assert_parsed_diff_file(
            parsed_files[0],
            orig_filename=b'foo.bin',
            orig_file_details=b'',
            modified_filename=b'foo.bin',
            modified_file_details=b'',
            old_unix_mode='100644',
            deleted=True,
            binary=True,
            data=diff1)

        self.assert_parsed_diff_file(
            parsed_files[1],
            orig_filename=b'bar.bin',
            orig_file_details=b'',
            modified_filename=b'bar.bin',
            modified_file_details=b'',
            old_unix_mode='100644',
            deleted=True,
            binary=True,
            data=diff2)

    def test_parse_diff_with_all_headers(self):
        """Testing Git diff parsing and preserving all headers"""
        preamble = (
            b'From 38d8fa94a9aa0c5b27943bec31d94e880165f1e0 Mon Sep '
            b'17 00:00:00 2001\n'
            b'From: Example Joe <joe@example.com>\n'
            b'Date: Thu, 5 Apr 2012 00:41:12 -0700\n'
            b'Subject: [PATCH 1/1] Sample patch.\n'
            b'\n'
            b'This is a test summary.\n'
            b'\n'
            b'With a description.\n'
            b'---\n'
            b' foo/bar |   2 -+n'
            b' README  |   2 -+n'
            b' 2 files changed, 2 insertions(+), 2 deletions(-)\n'
            b'\n'
        )
        diff1 = (
            b'diff --git a/foo/bar b/foo/bar2\n'
            b'index 612544e4343bf04967eb5ea80257f6c64d6f42c7..'
            b'e88b7f15c03d141d0bb38c8e49bb6c411ebfe1f1 100644\n'
            b'--- a/foo/bar\n'
            b'+++ b/foo/bar2\n'
            b'@ -1,1 +1,1 @@\n'
            b'-blah blah\n'
            b'+blah\n'
        )
        diff2 = (
            b'diff --git a/README b/README\n'
            b'index 712544e4343bf04967eb5ea80257f6c64d6f42c7..'
            b'f88b7f15c03d141d0bb38c8e49bb6c411ebfe1f1 100644\n'
            b'--- a/README\n'
            b'+++ b/README\n'
            b'@ -1,1 +1,1 @@\n'
            b'-blah blah\n'
            b'+blah\n'
            b'-\n'
            b'1.7.1\n'
        )
        diff = preamble + diff1 + diff2

        parsed_files = self.tool.get_parser(diff).parse()
        self.assertEqual(len(parsed_files), 2)

        self.assert_parsed_diff_file(
            parsed_files[0],
            orig_filename=b'foo/bar',
            orig_file_details=b'612544e4343bf04967eb5ea80257f6c64d6f42c7',
            modified_filename=b'foo/bar2',
            modified_file_details=b'e88b7f15c03d141d0bb38c8e49bb6c411ebfe1f1',
            old_unix_mode='100644',
            new_unix_mode='100644',
            insert_count=1,
            delete_count=1,
            data=preamble + diff1)

        self.assert_parsed_diff_file(
            parsed_files[1],
            orig_filename=b'README',
            orig_file_details=b'712544e4343bf04967eb5ea80257f6c64d6f42c7',
            modified_filename=b'README',
            modified_file_details=b'f88b7f15c03d141d0bb38c8e49bb6c411ebfe1f1',
            old_unix_mode='100644',
            new_unix_mode='100644',
            insert_count=1,
            delete_count=2,
            data=diff2)

    def test_parse_diff_revision(self):
        """Testing Git revision number parsing"""
        self.assertEqual(
            self.tool.parse_diff_revision(filename=b'doc/readme',
                                          revision=b'bf544ea'),
            (b'doc/readme', b'bf544ea'))
        self.assertEqual(
            self.tool.parse_diff_revision(filename=b'/dev/null',
                                          revision=b'bf544ea'),
            (b'/dev/null', PRE_CREATION))
        self.assertEqual(
            self.tool.parse_diff_revision(filename=b'/dev/null',
                                          revision=b'0000000'),
            (b'/dev/null', PRE_CREATION))

    def test_parse_diff_with_copy_and_rename_same_file(self):
        """Testing Git diff parsing with copy and rename of same file"""
        diff1 = (
            b'diff --git a/foo/bar b/foo/bar2\n'
            b'similarity index 100%\n'
            b'copy from foo/bar\n'
            b'copy to foo/bar2\n'
        )
        diff2 = (
            b'diff --git a/foo/bar b/foo/bar3\n'
            b'similarity index 92%\n'
            b'rename from foo/bar\n'
            b'rename to foo/bar3\n'
            b'index 612544e4343bf04967eb5ea80257f6c64d6f42c7..'
            b'e88b7f15c03d141d0bb38c8e49bb6c411ebfe1f1 100644\n'
            b'--- a/foo/bar\n'
            b'+++ b/foo/bar3\n'
            b'@@ -1,1 +1,1 @@\n'
            b'-blah blah\n'
            b'+blah\n'
        )
        diff = diff1 + diff2

        parsed_files = self.tool.get_parser(diff).parse()
        self.assertEqual(len(parsed_files), 2)

        self.assert_parsed_diff_file(
            parsed_files[0],
            orig_filename=b'foo/bar',
            orig_file_details=b'',
            modified_filename=b'foo/bar2',
            modified_file_details=b'',
            copied=True,
            data=diff1)

        self.assert_parsed_diff_file(
            parsed_files[1],
            orig_filename=b'foo/bar',
            orig_file_details=b'612544e4343bf04967eb5ea80257f6c64d6f42c7',
            modified_filename=b'foo/bar3',
            modified_file_details=b'e88b7f15c03d141d0bb38c8e49bb6c411ebfe1f1',
            old_unix_mode='100644',
            new_unix_mode='100644',
            moved=True,
            insert_count=1,
            delete_count=1,
            data=diff2)

    def test_parse_diff_with_mode_change_and_rename(self):
        """Testing Git diff parsing with mode change and rename"""
        diff = (
            b'diff --git a/foo/bar b/foo/bar2\n'
            b'old mode 100755\n'
            b'new mode 100644\n'
            b'similarity index 99%\n'
            b'rename from foo/bar\n'
            b'rename to foo/bar2\n'
            b'index 612544e4343bf04967eb5ea80257f6c64d6f42c7..'
            b'e88b7f15c03d141d0bb38c8e49bb6c411ebfe1f1\n'
            b'--- a/foo/bar\n'
            b'+++ b/foo/bar2\n'
            b'@@ -1,1 +1,1 @@\n'
            b'-blah blah\n'
            b'+blah\n'
        )

        parsed_files = self.tool.get_parser(diff).parse()
        self.assertEqual(len(parsed_files), 1)

        self.assert_parsed_diff_file(
            parsed_files[0],
            orig_filename=b'foo/bar',
            orig_file_details=b'612544e4343bf04967eb5ea80257f6c64d6f42c7',
            modified_filename=b'foo/bar2',
            modified_file_details=b'e88b7f15c03d141d0bb38c8e49bb6c411ebfe1f1',
            old_unix_mode='100755',
            new_unix_mode='100644',
            moved=True,
            insert_count=1,
            delete_count=1,
            data=diff)

    def test_diff_git_line_without_a_b(self):
        """Testing parsing Git diff with deleted file without a/ and
        b/ filename prefixes
        """
        diff = (
            b'diff --git foo foo\n'
            b'deleted file mode 100644\n'
            b'index 612544e4343bf04967eb5ea80257f6c64d6f42c7..'
            b'0000000000000000000000000000000000000000\n'
        )

        parsed_files = self.tool.get_parser(diff).parse()
        self.assertEqual(len(parsed_files), 1)

        self.assert_parsed_diff_file(
            parsed_files[0],
            orig_filename=b'foo',
            orig_file_details=b'612544e4343bf04967eb5ea80257f6c64d6f42c7',
            modified_filename=b'foo',
            modified_file_details=b'0000000000000000000000000000000000000000',
            old_unix_mode='100644',
            deleted=True,
            data=diff)

    def test_diff_git_line_without_a_b_quotes(self):
        """Testing parsing Git diff with deleted file without a/ and
        b/ filename prefixes and with quotes
        """
        diff = (
            b'diff --git "foo" "foo"\n'
            b'deleted file mode 100644\n'
            b'index 612544e4343bf04967eb5ea80257f6c64d6f42c7..'
            b'0000000000000000000000000000000000000000\n'
        )

        parsed_files = self.tool.get_parser(diff).parse()
        self.assertEqual(len(parsed_files), 1)

        self.assert_parsed_diff_file(
            parsed_files[0],
            orig_filename=b'foo',
            orig_file_details=b'612544e4343bf04967eb5ea80257f6c64d6f42c7',
            modified_filename=b'foo',
            modified_file_details=b'0000000000000000000000000000000000000000',
            old_unix_mode='100644',
            deleted=True,
            data=diff)

    def test_diff_git_line_without_a_b_and_spaces(self):
        """Testing parsing Git diff with deleted file without a/ and
        b/ filename prefixes and with spaces
        """
        diff = (
            b'diff --git foo bar1 foo bar1\n'
            b'deleted file mode 100644\n'
            b'index 612544e4343bf04967eb5ea80257f6c64d6f42c7..'
            b'0000000000000000000000000000000000000000\n'
        )

        parsed_files = self.tool.get_parser(diff).parse()
        self.assertEqual(len(parsed_files), 1)

        self.assert_parsed_diff_file(
            parsed_files[0],
            orig_filename=b'foo bar1',
            orig_file_details=b'612544e4343bf04967eb5ea80257f6c64d6f42c7',
            modified_filename=b'foo bar1',
            modified_file_details=b'0000000000000000000000000000000000000000',
            old_unix_mode='100644',
            deleted=True,
            data=diff)

    def test_diff_git_line_without_a_b_and_spaces_quotes(self):
        """Testing parsing Git diff with deleted file without a/ and
        b/ filename prefixes and with space and quotes
        """
        diff = (
            b'diff --git "foo bar1" "foo bar1"\n'
            b'deleted file mode 100644\n'
            b'index 612544e4343bf04967eb5ea80257f6c64d6f42c7..'
            b'0000000000000000000000000000000000000000\n'
        )

        parsed_files = self.tool.get_parser(diff).parse()
        self.assertEqual(len(parsed_files), 1)

        self.assert_parsed_diff_file(
            parsed_files[0],
            orig_filename=b'foo bar1',
            orig_file_details=b'612544e4343bf04967eb5ea80257f6c64d6f42c7',
            modified_filename=b'foo bar1',
            modified_file_details=b'0000000000000000000000000000000000000000',
            old_unix_mode='100644',
            deleted=True,
            data=diff)

    def test_diff_git_line_without_a_b_and_spaces_changed(self):
        """Testing parsing Git diff with deleted file without a/ and
        b/ filename prefixes and with spaces, with filename changes
        """
        diff = (b'diff --git foo bar1 foo bar2\n'
                b'deleted file mode 100644\n'
                b'index 612544e4343bf04967eb5ea80257f6c64d6f42c7..'
                b'0000000000000000000000000000000000000000\n')

        with self.assertRaises(DiffParserError) as cm:
            self.tool.get_parser(diff).parse()

        self.assertTrue(str(cm.exception).startswith(
            'Unable to parse the "diff --git" line'))

    def test_diff_git_line_without_a_b_and_spaces_quotes_changed(self):
        """Testing parsing Git diff with deleted file without a/ and
        b/ filename prefixes and with spaces and quotes, with filename
        changes
        """
        diff1 = (
            b'diff --git "foo bar1" "foo bar2"\n'
            b'deleted file mode 100644\n'
            b'index 612544e4343bf04967eb5ea80257f6c64d6f42c7..'
            b'0000000000000000000000000000000000000000\n'
        )
        diff2 = (
            b'diff --git "foo bar1" foo\n'
            b'deleted file mode 100644\n'
            b'index 612544e4343bf04967eb5ea80257f6c64d6f42c7..'
            b'0000000000000000000000000000000000000000\n'
        )
        diff3 = (
            b'diff --git foo "foo bar1"\n'
            b'deleted file mode 100644\n'
            b'index 612544e4343bf04967eb5ea80257f6c64d6f42c7..'
            b'0000000000000000000000000000000000000000\n'
        )
        diff = diff1 + diff2 + diff3

        parsed_files = self.tool.get_parser(diff).parse()
        self.assertEqual(len(parsed_files), 3)

        self.assert_parsed_diff_file(
            parsed_files[0],
            orig_filename=b'foo bar1',
            orig_file_details=b'612544e4343bf04967eb5ea80257f6c64d6f42c7',
            modified_filename=b'foo bar2',
            modified_file_details=b'0000000000000000000000000000000000000000',
            old_unix_mode='100644',
            deleted=True,
            data=diff1)

        self.assert_parsed_diff_file(
            parsed_files[1],
            orig_filename=b'foo bar1',
            orig_file_details=b'612544e4343bf04967eb5ea80257f6c64d6f42c7',
            modified_filename=b'foo',
            modified_file_details=b'0000000000000000000000000000000000000000',
            old_unix_mode='100644',
            deleted=True,
            data=diff2)

        self.assert_parsed_diff_file(
            parsed_files[2],
            orig_filename=b'foo',
            orig_file_details=b'612544e4343bf04967eb5ea80257f6c64d6f42c7',
            modified_filename=b'foo bar1',
            modified_file_details=b'0000000000000000000000000000000000000000',
            old_unix_mode='100644',
            deleted=True,
            data=diff3)

    def test_diff_git_symlink_added(self):
        """Testing parsing Git diff with symlink added"""
        diff = (
            b'diff --git a/link b/link\n'
            b'new file mode 120000\n'
            b'index 0000000..100b938\n'
            b'--- /dev/null\n'
            b'+++ b/link\n'
            b'@@ -0,0 +1 @@\n'
            b'+README\n'
            b'\\ No newline at end of file\n'
        )

        parsed_files = self.tool.get_parser(diff).parse()
        self.assertEqual(len(parsed_files), 1)

        self.assert_parsed_diff_file(
            parsed_files[0],
            orig_filename=b'link',
            orig_file_details=PRE_CREATION,
            modified_filename=b'link',
            modified_file_details=b'100b938',
            new_unix_mode='120000',
            is_symlink=True,
            new_symlink_target=b'README',
            insert_count=1,
            data=diff)

    def test_diff_git_symlink_changed(self):
        """Testing parsing Git diff with symlink changed"""
        diff = (
            b'diff --git a/link b/link\n'
            b'index 100b937..100b938 120000\n'
            b'--- a/link\n'
            b'+++ b/link\n'
            b'@@ -1 +1 @@\n'
            b'-README\n'
            b'\\ No newline at end of file\n'
            b'+README.md\n'
            b'\\ No newline at end of file\n'
        )

        parsed_files = self.tool.get_parser(diff).parse()
        self.assertEqual(len(parsed_files), 1)

        self.assert_parsed_diff_file(
            parsed_files[0],
            orig_filename=b'link',
            orig_file_details=b'100b937',
            modified_filename=b'link',
            modified_file_details=b'100b938',
            old_unix_mode='120000',
            new_unix_mode='120000',
            is_symlink=True,
            old_symlink_target=b'README',
            new_symlink_target=b'README.md',
            insert_count=1,
            delete_count=1,
            data=diff)

    def test_diff_git_symlink_removed(self):
        """Testing parsing Git diff with symlink removed"""
        diff = (
            b'diff --git a/link b/link\n'
            b'deleted file mode 120000\n'
            b'index 100b938..0000000\n'
            b'--- a/link\n'
            b'+++ /dev/null\n'
            b'@@ -1 +0,0 @@\n'
            b'-README.txt\n'
            b'\\ No newline at end of file\n'
        )

        parsed_files = self.tool.get_parser(diff).parse()
        self.assertEqual(len(parsed_files), 1)

        self.assert_parsed_diff_file(
            parsed_files[0],
            orig_filename=b'link',
            orig_file_details=b'100b938',
            modified_filename=b'link',
            modified_file_details=b'0000000',
            old_unix_mode='120000',
            is_symlink=True,
            old_symlink_target=b'README.txt',
            deleted=True,
            delete_count=1,
            data=diff)

    def test_file_exists(self):
        """Testing GitTool.file_exists"""
        tool = self.tool

        self.assertTrue(tool.file_exists('readme', 'e965047'))
        self.assertTrue(tool.file_exists('readme', 'd6613f5'))

        self.assertFalse(tool.file_exists('readme', PRE_CREATION))
        self.assertFalse(tool.file_exists('readme', 'fffffff'))
        self.assertFalse(tool.file_exists('readme2', 'fffffff'))

        # These sha's are valid, but commit and tree objects, not blobs.
        self.assertFalse(tool.file_exists('readme', 'a62df6c'))
        self.assertFalse(tool.file_exists('readme2', 'ccffbb4'))

    def test_get_file(self):
        """Testing GitTool.get_file"""
        tool = self.tool

        content = tool.get_file('readme', PRE_CREATION)
        self.assertIsInstance(content, bytes)
        self.assertEqual(content, b'')

        content = tool.get_file('readme', 'e965047')
        self.assertIsInstance(content, bytes)
        self.assertEqual(content, b'Hello\n')

        content = tool.get_file('readme', 'd6613f5')
        self.assertIsInstance(content, bytes)
        self.assertEqual(content, b'Hello there\n')

        content = tool.get_file('readme')
        self.assertIsInstance(content, bytes)
        self.assertEqual(content, b'Hello there\n')

        with self.assertRaises(SCMError):
            tool.get_file('')

        with self.assertRaises(FileNotFoundError):
            tool.get_file('', '0000000')

        with self.assertRaises(FileNotFoundError):
            tool.get_file('hello', '0000000')

        with self.assertRaises(FileNotFoundError):
            tool.get_file('readme', '0000000')

    def test_parse_diff_revision_with_remote_and_short_SHA1_error(self):
        """Testing GitTool.parse_diff_revision with remote files and short
        SHA1 error
        """
        with self.assertRaises(ShortSHA1Error):
            self.remote_tool.parse_diff_revision(filename=b'README',
                                                 revision=b'd7e96b3')

    def test_get_file_with_remote_and_short_SHA1_error(self):
        """Testing GitTool.get_file with remote files and short SHA1 error"""
        with self.assertRaises(ShortSHA1Error):
            self.remote_tool.get_file('README', 'd7e96b3')

    def test_valid_repository_https_username(self):
        """Testing GitClient.is_valid_repository with an HTTPS URL and external
        credentials
        """
        client = GitClient('https://example.com/test.git',
                           username='username',
                           password='pass/word')

        self.spy_on(client._run_git)
        client.is_valid_repository()

        self.assertEqual(client._run_git.calls[0].args[0],
                         ['ls-remote',
                          'https://username:pass%2Fword@example.com/test.git',
                          'HEAD'])

    def test_raw_file_url_error(self):
        """Testing Repository.get_file re-fetches when raw file URL changes"""
        repository = self.remote_repository

        self.spy_on(repository._get_file_uncached,
                    op=kgb.SpyOpReturn(b'first'))

        self.assertEqual(repository.get_file('PATH', 'd7e96b3'),
                         b'first')

        # Ensure output of fake result matches.
        repository._get_file_uncached.unspy()
        self.spy_on(repository._get_file_uncached,
                    op=kgb.SpyOpReturn(b'second'))

        # Grab from cache when no changes and change fake result to confirm
        # it is not called.
        self.assertEqual(repository.get_file('PATH', 'd7e96b3'),
                         b'first')

        # When raw_file_url changed, do not grab from cache and ensure output
        # equals second fake value.
        repository.raw_file_url = \
            'http://github.com/api/v2/yaml/blob/show/reviewboard/<revision>'

        self.assertEqual(repository.get_file('PATH', 'd7e96b3'),
                         b'second')

    def test_get_file_exists_caching_with_raw_url(self):
        """Testing Repository.get_file_exists properly checks file existence in
        repository or cache when raw file URL changes
        """
        repository = self.remote_repository

        self.spy_on(repository._get_file_exists_uncached,
                    op=kgb.SpyOpReturn(True))

        # Use spy to put key into cache
        self.assertTrue(repository.get_file_exists('PATH', 'd7e96b3'))

        # Remove spy to ensure key is still in cache without needing spy
        repository._get_file_exists_uncached.unspy()
        self.assertTrue(repository.get_file_exists('PATH', 'd7e96b3'))

        # Does not exist when raw_file_url changed because it is not cached.
        repository.raw_file_url = \
            'http://github.com/api/v2/yaml/blob/show/reviewboard/<revision>'

        self.assertFalse(repository.get_file_exists('PATH', 'd7e96b3'))

    def test_normalize_patch_with_git_diff_new_symlink(self):
        """Testing GitTool.normalize_patch with new symlink"""
        self.assertEqual(
            self.tool.normalize_patch(
                patch=(
                    b'diff --git /dev/null b/test\n'
                    b'new file mode 120000\n'
                    b'--- /dev/null\n'
                    b'+++ b/test\n'
                    b'@@ -0,0 +1,1 @@\n'
                    b'+target_file\n'
                    b'\\ No newline at end of file'
                ),
                filename='test',
                revision=PRE_CREATION),
            (
                b'diff --git /dev/null b/test\n'
                b'new file mode 100000\n'
                b'--- /dev/null\n'
                b'+++ b/test\n'
                b'@@ -0,0 +1,1 @@\n'
                b'+target_file\n'
                b'\\ No newline at end of file'
            ))

    def test_normalize_patch_with_modified_symlink(self):
        """Testing GitTool.normalize_patch with modified symlink"""
        self.assertEqual(
            self.tool.normalize_patch(
                patch=(
                    b'diff --git a/test b/test\n'
                    b'index abc1234..def4567 120000\n'
                    b'--- a/test\n'
                    b'+++ b/test\n'
                    b'@@ -1,1 +1,1 @@\n'
                    b'-old_target\n'
                    b'\\ No newline at end of file'
                    b'+new_target\n'
                    b'\\ No newline at end of file'
                ),
                filename='test',
                revision='abc1234'),
            (
                b'diff --git a/test b/test\n'
                b'index abc1234..def4567 100000\n'
                b'--- a/test\n'
                b'+++ b/test\n'
                b'@@ -1,1 +1,1 @@\n'
                b'-old_target\n'
                b'\\ No newline at end of file'
                b'+new_target\n'
                b'\\ No newline at end of file'
            ))

    def test_normalize_patch_with_deleted_symlink(self):
        """Testing HgTool.normalize_patch with deleted symlink"""
        self.assertEqual(
            self.tool.normalize_patch(
                patch=(
                    b'diff --git a/test b/test\n'
                    b'deleted file mode 120000\n'
                    b'index abc1234..0000000\n'
                    b'--- a/test\n'
                    b'+++ /dev/null\n'
                    b'@@ -1,1 +0,0 @@\n'
                    b'-old_target\n'
                    b'\\ No newline at end of file'
                ),
                filename='test',
                revision='abc1234'),
            (
                b'diff --git a/test b/test\n'
                b'deleted file mode 100000\n'
                b'index abc1234..0000000\n'
                b'--- a/test\n'
                b'+++ /dev/null\n'
                b'@@ -1,1 +0,0 @@\n'
                b'-old_target\n'
                b'\\ No newline at end of file'
            ))


class GitAuthFormTests(TestCase):
    """Unit tests for GitTool's authentication form."""

    def test_fields(self):
        """Testing GitTool authentication form fields"""
        form = GitTool.create_auth_form()

        self.assertEqual(list(form.fields), ['username', 'password'])
        self.assertEqual(form['username'].help_text, '')
        self.assertEqual(form['username'].label, 'Username')
        self.assertEqual(form['password'].help_text, '')
        self.assertEqual(form['password'].label, 'Password')

    @add_fixtures(['test_scmtools'])
    def test_load(self):
        """Tetting GitTool authentication form load"""
        repository = self.create_repository(
            tool_name='Git',
            username='test-user',
            password='test-pass')

        form = GitTool.create_auth_form(repository=repository)
        form.load()

        self.assertEqual(form['username'].value(), 'test-user')
        self.assertEqual(form['password'].value(), 'test-pass')

    @add_fixtures(['test_scmtools'])
    def test_save(self):
        """Tetting GitTool authentication form save"""
        repository = self.create_repository(tool_name='Git')

        form = GitTool.create_auth_form(
            repository=repository,
            data={
                'username': 'test-user',
                'password': 'test-pass',
            })
        self.assertTrue(form.is_valid())
        form.save()

        self.assertEqual(repository.username, 'test-user')
        self.assertEqual(repository.password, 'test-pass')


class GitRepositoryFormTests(TestCase):
    """Unit tests for GitTool's repository form."""

    def test_fields(self):
        """Testing GitTool repository form fields"""
        form = GitTool.create_repository_form()

        self.assertEqual(list(form.fields),
                         ['path', 'mirror_path', 'raw_file_url'])
        self.assertEqual(form['path'].help_text,
                         'For local Git repositories, this should be the path '
                         'to a .git directory that Review Board can read '
                         'from. For remote Git repositories, it should be '
                         'the clone URL.')
        self.assertEqual(form['path'].label, 'Path')
        self.assertEqual(form['mirror_path'].help_text, '')
        self.assertEqual(form['mirror_path'].label, 'Mirror Path')
        self.assertEqual(form['raw_file_url'].label, 'Raw File URL Mask')
        self.assertEqual(form['raw_file_url'].help_text,
                         "A URL mask used to check out a particular revision "
                         "of a file using HTTP. This is needed for "
                         "repository types that can't access remote files "
                         "natively. Use <tt>&lt;revision&gt;</tt> and "
                         "<tt>&lt;filename&gt;</tt> in the URL in place of "
                         "the revision and filename parts of the path.")

    @add_fixtures(['test_scmtools'])
    def test_load(self):
        """Tetting GitTool repository form load"""
        repository = self.create_repository(
            tool_name='Git',
            path='https://github.com/reviewboard/reviewboard',
            mirror_path='git@github.com:reviewboard/reviewboard.git',
            raw_file_url='http://git.example.com/raw/<revision>')

        form = GitTool.create_repository_form(repository=repository)
        form.load()

        self.assertEqual(form['path'].value(),
                         'https://github.com/reviewboard/reviewboard')
        self.assertEqual(form['mirror_path'].value(),
                         'git@github.com:reviewboard/reviewboard.git')
        self.assertEqual(form['raw_file_url'].value(),
                         'http://git.example.com/raw/<revision>')

    @add_fixtures(['test_scmtools'])
    def test_save(self):
        """Tetting GitTool repository form save"""
        repository = self.create_repository(tool_name='Git')

        form = GitTool.create_repository_form(
            repository=repository,
            data={
                'path': 'https://github.com/reviewboard/reviewboard',
                'mirror_path': 'git@github.com:reviewboard/reviewboard.git',
                'raw_file_url': 'http://git.example.com/raw/<revision>',
            })
        self.assertTrue(form.is_valid())
        form.save()

        self.assertEqual(repository.path,
                         'https://github.com/reviewboard/reviewboard')
        self.assertEqual(repository.mirror_path,
                         'git@github.com:reviewboard/reviewboard.git')
        self.assertEqual(repository.raw_file_url,
                         'http://git.example.com/raw/<revision>')
