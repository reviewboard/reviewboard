# coding=utf-8
from __future__ import unicode_literals

import os

import nose
from django.utils import six
from djblets.testing.decorators import add_fixtures
from kgb import SpyAgency

from reviewboard.diffviewer.parser import DiffParserError
from reviewboard.scmtools.core import PRE_CREATION
from reviewboard.scmtools.errors import SCMError, FileNotFoundError
from reviewboard.scmtools.git import ShortSHA1Error, GitClient, GitTool
from reviewboard.scmtools.models import Repository, Tool
from reviewboard.scmtools.tests.testcases import SCMTestCase
from reviewboard.testing.testcase import TestCase


class GitTests(SpyAgency, SCMTestCase):
    """Unit tests for Git."""

    fixtures = ['test_scmtools']

    def setUp(self):
        super(GitTests, self).setUp()

        tool = Tool.objects.get(name='Git')

        self.local_repo_path = os.path.join(os.path.dirname(__file__),
                                            '..', 'testdata', 'git_repo')
        self.git_ssh_path = ('localhost:%s'
                             % self.local_repo_path.replace('\\', '/'))
        remote_repo_path = 'git@github.com:reviewboard/reviewboard.git'
        remote_repo_raw_url = ('http://github.com/api/v2/yaml/blob/show/'
                               'reviewboard/reviewboard/<revision>')

        self.repository = Repository(name='Git test repo',
                                     path=self.local_repo_path,
                                     tool=tool)
        self.remote_repository = Repository(name='Remote Git test repo',
                                            path=remote_repo_path,
                                            raw_file_url=remote_repo_raw_url,
                                            tool=tool)

        try:
            self.tool = self.repository.get_scmtool()
            self.remote_tool = self.remote_repository.get_scmtool()
        except ImportError:
            raise nose.SkipTest('git binary not found')

    def _read_fixture(self, filename):
        filename = os.path.join(os.path.dirname(__file__),
                                '..', 'testdata', filename)

        with open(filename, 'rb') as f:
            return f.read()

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
        diff = (
            b'diff --git a/testing b/testing\n'
            b'old mode 100755\n'
            b'new mode 100644\n'
            b'index e69de29..bcae657\n'
            b'--- a/testing\n'
            b'+++ b/testing\n'
            b'@@ -0,0 +1 @@\n'
            b'+ADD\n'
            b'diff --git a/testing2 b/testing2\n'
            b'old mode 100644\n'
            b'new mode 100755\n'
        )

        file = self._get_file_in_diff(diff)
        self.assertEqual(file.orig_filename, b'testing')
        self.assertEqual(file.modified_filename, b'testing')
        self.assertEqual(file.orig_file_details, b'e69de29')
        self.assertEqual(file.modified_file_details, b'bcae657')
        self.assertFalse(file.binary)
        self.assertFalse(file.deleted)
        self.assertFalse(file.is_symlink)
        self.assertEqual(file.data.splitlines()[0],
                         b'diff --git a/testing b/testing')
        self.assertEqual(file.data.splitlines()[-1], b'+ADD')
        self.assertEqual(file.insert_count, 1)
        self.assertEqual(file.delete_count, 0)

    def test_filemode_with_following_diff(self):
        """Testing parsing filemode changes with following Git diff"""
        diff = (
            b'diff --git a/testing b/testing\n'
            b'old mode 100755\n'
            b'new mode 100644\n'
            b'index e69de29..bcae657\n'
            b'--- a/testing\n'
            b'+++ b/testing\n'
            b'@@ -0,0 +1 @@\n'
            b'+ADD\n'
            b'diff --git a/testing2 b/testing2\n'
            b'old mode 100644\n'
            b'new mode 100755\n'
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

        file = self._get_file_in_diff(diff)
        self.assertEqual(file.orig_filename, b'testing')
        self.assertEqual(file.modified_filename, b'testing')
        self.assertEqual(file.orig_file_details, b'e69de29')
        self.assertEqual(file.modified_file_details, b'bcae657')
        self.assertFalse(file.binary)
        self.assertFalse(file.deleted)
        self.assertFalse(file.is_symlink)
        self.assertEqual(file.data.splitlines()[0],
                         b'diff --git a/testing b/testing')
        self.assertEqual(file.data.splitlines()[-1], b'+ADD')
        self.assertEqual(file.insert_count, 1)
        self.assertEqual(file.delete_count, 0)

        file = self._get_file_in_diff(diff, 1)
        self.assertEqual(file.orig_filename, b'cfg/testcase.ini')
        self.assertEqual(file.modified_filename, b'cfg/testcase.ini')
        self.assertEqual(file.orig_file_details, b'cc18ec8')
        self.assertEqual(file.modified_file_details, b'5e70b73')
        self.assertEqual(file.data.splitlines()[0],
                         b'diff --git a/cfg/testcase.ini b/cfg/testcase.ini')
        self.assertEqual(file.data.splitlines()[-1], b'+db = pyunit')
        self.assertEqual(file.insert_count, 2)
        self.assertEqual(file.delete_count, 1)

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

        file = self._get_file_in_diff(diff)
        self.assertEqual(file.orig_filename, b'cfg/testcase.ini')
        self.assertEqual(file.modified_filename, b'cfg/testcase.ini')
        self.assertEqual(file.orig_file_details, b'cc18ec8')
        self.assertEqual(file.modified_file_details, b'5e70b73')
        self.assertFalse(file.binary)
        self.assertFalse(file.deleted)
        self.assertFalse(file.is_symlink)
        self.assertEqual(len(file.data), 249)
        self.assertEqual(file.data.splitlines()[0],
                         b'diff --git a/cfg/testcase.ini b/cfg/testcase.ini')
        self.assertEqual(file.data.splitlines()[-1], b'+db = pyunit')
        self.assertEqual(file.insert_count, 2)
        self.assertEqual(file.delete_count, 1)

    def test_diff_with_unicode(self):
        """Testing parsing Git diff with unicode characters"""
        diff = ('diff --git a/cfg/téstcase.ini b/cfg/téstcase.ini\n'
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
                '+db = pyunít\n').encode('utf-8')

        file = self._get_file_in_diff(diff)
        self.assertEqual(file.orig_filename,
                         'cfg/téstcase.ini'.encode('utf-8'))
        self.assertEqual(file.modified_filename,
                         'cfg/téstcase.ini'.encode('utf-8'))
        self.assertEqual(file.orig_file_details, b'cc18ec8')
        self.assertEqual(file.modified_file_details, b'5e70b73')
        self.assertFalse(file.binary)
        self.assertFalse(file.deleted)
        self.assertFalse(file.is_symlink)
        self.assertEqual(file.data.splitlines()[0].decode('utf-8'),
                         'diff --git a/cfg/téstcase.ini b/cfg/téstcase.ini')
        self.assertEqual(file.data.splitlines()[-1],
                         '+db = pyunít'.encode('utf-8'))
        self.assertEqual(file.insert_count, 2)
        self.assertEqual(file.delete_count, 1)

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

        files = self.tool.get_parser(diff).parse()
        self.assertEqual(files[0].orig_filename, b'README')
        self.assertEqual(files[0].modified_filename, b'README')
        self.assertEqual(files[0].orig_file_details,
                         b'712544e4343bf04967eb5ea80257f6c64d6f42c7')
        self.assertEqual(files[0].modified_file_details,
                         b'f88b7f15c03d141d0bb38c8e49bb6c411ebfe1f1')
        self.assertEqual(files[0].data, diff)
        self.assertEqual(files[0].insert_count, 1)
        self.assertEqual(files[0].delete_count, 2)

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

        file = self._get_file_in_diff(diff)
        self.assertEqual(file.orig_filename, b'IAMNEW')
        self.assertEqual(file.modified_filename, b'IAMNEW')
        self.assertEqual(file.orig_file_details, PRE_CREATION)
        self.assertEqual(file.modified_file_details, b'e69de29')
        self.assertFalse(file.binary)
        self.assertFalse(file.deleted)
        self.assertFalse(file.is_symlink)
        self.assertEqual(len(file.data), 123)
        self.assertEqual(file.data.splitlines()[0],
                         b'diff --git a/IAMNEW b/IAMNEW')
        self.assertEqual(file.data.splitlines()[-1], b'+Hello')
        self.assertEqual(file.insert_count, 1)
        self.assertEqual(file.delete_count, 0)

    def test_new_file_no_content_diff(self):
        """Testing parsing Git diff new file, no content"""
        diff = (
            b'diff --git a/newfile b/newfile\n'
            b'new file mode 100644\n'
            b'index 0000000..e69de29\n'
        )

        files = self.tool.get_parser(diff).parse()
        self.assertEqual(len(files), 1)

        file = self._get_file_in_diff(diff)
        self.assertEqual(file.orig_filename, b'newfile')
        self.assertEqual(file.modified_filename, b'newfile')
        self.assertEqual(file.orig_file_details, PRE_CREATION)
        self.assertEqual(file.modified_file_details, b'e69de29')
        self.assertFalse(file.binary)
        self.assertFalse(file.deleted)
        self.assertFalse(file.is_symlink)
        lines = file.data.splitlines()
        self.assertEqual(len(lines), 3)
        self.assertEqual(lines[0], b'diff --git a/newfile b/newfile')
        self.assertEqual(file.insert_count, 0)
        self.assertEqual(file.delete_count, 0)

    def test_new_file_no_content_with_following_diff(self):
        """Testing parsing Git diff new file, no content, with following"""
        diff = (
            b'diff --git a/newfile b/newfile\n'
            b'new file mode 100644\n'
            b'index 0000000..e69de29\n'
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

        files = self.tool.get_parser(diff).parse()
        self.assertEqual(len(files), 2)

        self.assertEqual(files[0].orig_filename, b'newfile')
        self.assertEqual(files[0].modified_filename, b'newfile')
        self.assertEqual(files[0].orig_file_details, PRE_CREATION)
        self.assertEqual(files[0].modified_file_details, b'e69de29')
        self.assertFalse(files[0].binary)
        self.assertFalse(files[0].deleted)
        self.assertFalse(files[0].is_symlink)
        lines = files[0].data.splitlines()
        self.assertEqual(len(lines), 3)
        self.assertEqual(lines[0], b'diff --git a/newfile b/newfile')
        self.assertEqual(files[0].insert_count, 0)
        self.assertEqual(files[0].delete_count, 0)

        self.assertEqual(files[1].orig_filename, b'cfg/testcase.ini')
        self.assertEqual(files[1].modified_filename, b'cfg/testcase.ini')
        self.assertEqual(files[1].orig_file_details, b'cc18ec8')
        self.assertEqual(files[1].modified_file_details, b'5e70b73')
        lines = files[1].data.splitlines()
        self.assertEqual(len(lines), 13)
        self.assertEqual(lines[0],
                         b'diff --git a/cfg/testcase.ini b/cfg/testcase.ini')
        self.assertEqual(lines[-1], b'+db = pyunit')
        self.assertEqual(files[1].insert_count, 2)
        self.assertEqual(files[1].delete_count, 1)

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

        file = self._get_file_in_diff(diff)
        self.assertEqual(file.orig_filename, b'OLDFILE')
        self.assertEqual(file.modified_filename, b'OLDFILE')
        self.assertEqual(file.orig_file_details, b'8ebcb01')
        self.assertEqual(file.modified_file_details, b'0000000')
        self.assertFalse(file.binary)
        self.assertTrue(file.deleted)
        self.assertFalse(file.is_symlink)
        self.assertEqual(len(file.data), 132)
        self.assertEqual(file.data.splitlines()[0],
                         b'diff --git a/OLDFILE b/OLDFILE')
        self.assertEqual(file.data.splitlines()[-1], b'-Goodbye')
        self.assertEqual(file.insert_count, 0)
        self.assertEqual(file.delete_count, 1)

    def test_del_file_no_content_diff(self):
        """Testing parsing Git diff with deleted file, no content"""
        diff = (b'diff --git a/empty b/empty\n'
                b'deleted file mode 100644\n'
                b'index e69de29bb2d1d6434b8b29ae775ad8c2e48c5391..'
                b'0000000000000000000000000000000000000000\n')

        files = self.tool.get_parser(diff).parse()
        self.assertEqual(len(files), 1)

        self.assertEqual(files[0].orig_filename, b'empty')
        self.assertEqual(files[0].modified_filename, b'empty')
        self.assertEqual(files[0].orig_file_details,
                         b'e69de29bb2d1d6434b8b29ae775ad8c2e48c5391')
        self.assertEqual(files[0].modified_file_details,
                         b'0000000000000000000000000000000000000000')
        self.assertFalse(files[0].binary)
        self.assertTrue(files[0].deleted)
        self.assertFalse(files[0].is_symlink)
        self.assertEqual(len(files[0].data), 141)
        self.assertEqual(files[0].data.splitlines()[0],
                         b'diff --git a/empty b/empty')
        self.assertEqual(files[0].insert_count, 0)
        self.assertEqual(files[0].delete_count, 0)

    def test_del_file_no_content_with_following_diff(self):
        """Testing parsing Git diff with deleted file, no content, with
        following
        """
        diff = (b'diff --git a/empty b/empty\n'
                b'deleted file mode 100644\n'
                b'index e69de29bb2d1d6434b8b29ae775ad8c2e48c5391..'
                b'0000000000000000000000000000000000000000\n'
                b'diff --git a/foo/bar b/foo/bar\n'
                b'index 484ba93ef5b0aed5b72af8f4e9dc4cfd10ef1a81..'
                b'0ae4095ddfe7387d405bd53bd59bbb5d861114c5 100644\n'
                b'--- a/foo/bar\n'
                b'+++ b/foo/bar\n'
                b'@@ -1 +1,2 @@\n'
                b'+Hello!\n'
                b'blah\n')

        files = self.tool.get_parser(diff).parse()
        self.assertEqual(len(files), 2)

        self.assertEqual(files[0].orig_filename, b'empty')
        self.assertEqual(files[0].modified_filename, b'empty')
        self.assertEqual(files[0].orig_file_details,
                         b'e69de29bb2d1d6434b8b29ae775ad8c2e48c5391')
        self.assertEqual(files[0].modified_file_details,
                         b'0000000000000000000000000000000000000000')
        self.assertFalse(files[0].binary)
        self.assertTrue(files[0].deleted)
        self.assertFalse(files[0].is_symlink)
        self.assertEqual(len(files[0].data), 141)
        self.assertEqual(files[0].data.splitlines()[0],
                         b'diff --git a/empty b/empty')
        self.assertEqual(files[0].insert_count, 0)
        self.assertEqual(files[0].delete_count, 0)

        self.assertEqual(files[1].orig_filename, b'foo/bar')
        self.assertEqual(files[1].modified_filename, b'foo/bar')
        self.assertEqual(files[1].orig_file_details,
                         b'484ba93ef5b0aed5b72af8f4e9dc4cfd10ef1a81')
        self.assertEqual(files[1].modified_file_details,
                         b'0ae4095ddfe7387d405bd53bd59bbb5d861114c5')
        self.assertFalse(files[1].binary)
        self.assertFalse(files[1].deleted)
        self.assertFalse(files[1].is_symlink)
        lines = files[1].data.splitlines()
        self.assertEqual(len(lines), 7)
        self.assertEqual(lines[0], b'diff --git a/foo/bar b/foo/bar')
        self.assertEqual(lines[5], b'+Hello!')
        self.assertEqual(files[1].insert_count, 1)
        self.assertEqual(files[1].delete_count, 0)

    def test_binary_diff(self):
        """Testing parsing Git diff with binary"""
        diff = (
            b'diff --git a/pysvn-1.5.1.tar.gz b/pysvn-1.5.1.tar.gz\n'
            b'new file mode 100644\n'
            b'index 0000000..86b520c\n'
            b'Binary files /dev/null and b/pysvn-1.5.1.tar.gz differ\n'
        )

        file = self._get_file_in_diff(diff)
        self.assertEqual(file.orig_filename, b'pysvn-1.5.1.tar.gz')
        self.assertEqual(file.modified_filename, b'pysvn-1.5.1.tar.gz')
        self.assertEqual(file.orig_file_details, PRE_CREATION)
        self.assertEqual(file.modified_file_details, b'86b520c')
        self.assertTrue(file.binary)
        self.assertFalse(file.deleted)
        self.assertFalse(file.is_symlink)
        lines = file.data.splitlines()
        self.assertEqual(len(lines), 4)
        self.assertEqual(
            lines[0],
            b'diff --git a/pysvn-1.5.1.tar.gz b/pysvn-1.5.1.tar.gz')
        self.assertEqual(
            lines[3],
            b'Binary files /dev/null and b/pysvn-1.5.1.tar.gz differ')
        self.assertEqual(file.insert_count, 0)
        self.assertEqual(file.delete_count, 0)

    def test_git_new_single_binary_diff(self):
        """Testing parsing Git diff with base64 binary and a new file"""
        diff = self._read_fixture('git_new_single_binary.diff')

        files = self.tool.get_parser(diff).parse()
        self.assertEqual(len(files), 2)

        self.assertEqual(files[0].orig_filename, b'Checked.svg')
        self.assertEqual(files[0].modified_filename, b'Checked.svg')
        self.assertFalse(files[0].binary)
        self.assertFalse(files[0].deleted)
        self.assertFalse(files[0].is_symlink)
        self.assertEqual(files[0].insert_count, 9)
        self.assertEqual(files[0].delete_count, 0)
        self.assertEqual(len(files[0].data), 969)
        split = files[0].data.splitlines()
        self.assertEqual(split[0], b'diff --git a/Checked.svg b/Checked.svg')
        self.assertEqual(split[-1], b'+</svg>')

        self.assertEqual(files[1].orig_filename, b'dialog.jpg')
        self.assertEqual(files[1].modified_filename, b'dialog.jpg')
        self.assertEqual(files[1].orig_file_details,
                         b'e69de29bb2d1d6434b8b29ae775ad8c2e48c5391')
        self.assertEqual(files[1].modified_file_details,
                         b'5503573346e25878d57775ed7caf88f2eb7a7d98')
        self.assertTrue(files[1].binary)
        self.assertFalse(files[1].deleted)
        self.assertFalse(files[1].is_symlink)
        self.assertEqual(files[1].insert_count, 0)
        self.assertEqual(files[1].delete_count, 0)
        self.assertEqual(len(files[1].data), 42513)
        split = files[1].data.splitlines()
        self.assertEqual(split[0], b'diff --git a/dialog.jpg b/dialog.jpg')
        self.assertEqual(split[3], b'GIT binary patch')
        self.assertEqual(split[4], b'literal 34445')
        self.assertEqual(split[-2], (b'q75*tM8SetfV1Lcj#Q^wI3)5>pmuS8'
                                     b'x#<EIC&-<U<r2qLm&;Nht|C_x4'))

    def test_git_new_binaries_diff(self):
        """Testing parsing Git diff with base64 binaries and new files"""
        diff = self._read_fixture('git_new_binaries.diff')

        files = self.tool.get_parser(diff).parse()
        self.assertEqual(len(files), 3)

        self.assertEqual(files[0].orig_filename, b'other.png')
        self.assertEqual(files[0].modified_filename, b'other.png')
        self.assertEqual(files[0].orig_file_details,
                         b'e69de29bb2d1d6434b8b29ae775ad8c2e48c5391')
        self.assertEqual(files[0].modified_file_details,
                         b'fddeadc701ac6dd751b8fc70fe128bd29e54b9b0')
        self.assertTrue(files[0].binary)
        self.assertFalse(files[0].deleted)
        self.assertFalse(files[0].is_symlink)
        self.assertEqual(files[0].insert_count, 0)
        self.assertEqual(files[0].delete_count, 0)
        self.assertEqual(len(files[0].data), 2007)
        split = files[0].data.splitlines()
        self.assertEqual(split[0], b'diff --git a/other.png b/other.png')
        self.assertEqual(split[3], b'GIT binary patch')
        self.assertEqual(split[4], b'literal 1459')
        self.assertEqual(split[-2], b'PuWv&b7#dLSFWLP!d=7XA')

        self.assertEqual(files[1].orig_filename, b'initial.png')
        self.assertEqual(files[1].modified_filename, b'initial.png')
        self.assertEqual(files[1].orig_file_details,
                         b'fddeadc701ac6dd751b8fc70fe128bd29e54b9b0')
        self.assertEqual(files[1].modified_file_details,
                         b'532716ada15dc62ddf8c59618b926f34d4727d77')
        self.assertTrue(files[1].binary)
        self.assertFalse(files[1].deleted)
        self.assertFalse(files[1].is_symlink)
        self.assertEqual(files[1].insert_count, 0)
        self.assertEqual(files[1].delete_count, 0)
        self.assertEqual(len(files[1].data), 10065)
        split = files[1].data.splitlines()
        self.assertEqual(split[0], b'diff --git a/initial.png b/initial.png')
        self.assertEqual(split[2], b'GIT binary patch')
        self.assertEqual(split[3], b'literal 7723')
        self.assertEqual(split[-2], (b'qU@utQTCoRZj8p;!(2CJ;Kce7Up0C'
                                     b'cmx5xf(jw;BgNY_Z3hW;Oyu4s(_'))

        self.assertEqual(files[2].orig_filename, b'xtxt.txt')
        self.assertEqual(files[2].modified_filename, b'xtxt.txt')
        self.assertFalse(files[2].binary)
        self.assertFalse(files[2].deleted)
        self.assertFalse(files[2].is_symlink)
        self.assertEqual(files[2].insert_count, 1)
        self.assertEqual(files[2].delete_count, 0)
        self.assertEqual(len(files[2].data), 107)
        split = files[2].data.splitlines()
        self.assertEqual(split[0], b'diff --git a/xtxt.txt b/xtxt.txt')
        self.assertEqual(split[-2], b'+Hello')

    def test_complex_diff(self):
        """Testing parsing Git diff with existing and new files"""
        diff = self._read_fixture('git_complex.diff')

        files = self.tool.get_parser(diff).parse()
        self.assertEqual(len(files), 7)
        self.assertEqual(files[0].orig_filename, b'cfg/testcase.ini')
        self.assertEqual(files[0].modified_filename, b'cfg/testcase.ini')
        self.assertEqual(files[0].orig_file_details, b'5e35098')
        self.assertEqual(files[0].modified_file_details, b'e254ef4')
        self.assertFalse(files[0].binary)
        self.assertFalse(files[0].deleted)
        self.assertFalse(files[0].is_symlink)
        self.assertEqual(files[0].insert_count, 2)
        self.assertEqual(files[0].delete_count, 1)
        self.assertEqual(len(files[0].data), 549)
        self.assertEqual(files[0].data.splitlines()[0],
                         b'diff --git a/cfg/testcase.ini b/cfg/testcase.ini')
        self.assertEqual(files[0].data.splitlines()[13],
                         b'         if isinstance(value, basestring):')

        self.assertEqual(files[1].orig_filename, b'tests/models.py')
        self.assertEqual(files[1].modified_filename, b'tests/models.py')
        self.assertEqual(files[1].orig_file_details, PRE_CREATION)
        self.assertEqual(files[1].modified_file_details, b'e69de29')
        self.assertFalse(files[1].binary)
        self.assertFalse(files[1].deleted)
        self.assertFalse(files[1].is_symlink)
        self.assertEqual(files[1].insert_count, 0)
        self.assertEqual(files[1].delete_count, 0)
        lines = files[1].data.splitlines()
        self.assertEqual(len(lines), 3)
        self.assertEqual(lines[0],
                         b'diff --git a/tests/models.py b/tests/models.py')

        self.assertEqual(files[2].orig_filename, b'tests/tests.py')
        self.assertEqual(files[2].modified_filename, b'tests/tests.py')
        self.assertEqual(files[2].orig_file_details, PRE_CREATION)
        self.assertEqual(files[2].modified_file_details, b'e279a06')
        self.assertFalse(files[2].binary)
        self.assertFalse(files[2].deleted)
        self.assertFalse(files[2].is_symlink)
        self.assertEqual(files[2].insert_count, 2)
        self.assertEqual(files[2].delete_count, 0)
        lines = files[2].data.splitlines()
        self.assertEqual(len(lines), 8)
        self.assertEqual(lines[0],
                         b'diff --git a/tests/tests.py b/tests/tests.py')
        self.assertEqual(lines[7],
                         b'+This is some new content')

        self.assertEqual(files[3].orig_filename, b'pysvn-1.5.1.tar.gz')
        self.assertEqual(files[3].modified_filename, b'pysvn-1.5.1.tar.gz')
        self.assertEqual(files[3].orig_file_details, PRE_CREATION)
        self.assertEqual(files[3].modified_file_details, b'86b520c')
        self.assertTrue(files[3].binary)
        self.assertFalse(files[3].deleted)
        self.assertFalse(files[3].is_symlink)
        self.assertEqual(files[3].insert_count, 0)
        self.assertEqual(files[3].delete_count, 0)
        lines = files[3].data.splitlines()
        self.assertEqual(len(lines), 4)
        self.assertEqual(
            lines[0], b'diff --git a/pysvn-1.5.1.tar.gz b/pysvn-1.5.1.tar.gz')
        self.assertEqual(lines[3],
                         b'Binary files /dev/null and b/pysvn-1.5.1.tar.gz '
                         b'differ')

        self.assertEqual(files[4].orig_filename, b'readme')
        self.assertEqual(files[4].modified_filename, b'readme')
        self.assertEqual(files[4].orig_file_details, b'5e35098')
        self.assertEqual(files[4].modified_file_details, b'e254ef4')
        self.assertFalse(files[4].binary)
        self.assertFalse(files[4].deleted)
        self.assertFalse(files[4].is_symlink)
        self.assertEqual(files[4].insert_count, 1)
        self.assertEqual(files[4].delete_count, 1)
        lines = files[4].data.splitlines()
        self.assertEqual(len(lines), 7)
        self.assertEqual(lines[0], b'diff --git a/readme b/readme')
        self.assertEqual(lines[6], b'+Hello there')

        self.assertEqual(files[5].orig_filename, b'OLDFILE')
        self.assertEqual(files[5].modified_filename, b'OLDFILE')
        self.assertEqual(files[5].orig_file_details, b'8ebcb01')
        self.assertEqual(files[5].modified_file_details, b'0000000')
        self.assertFalse(files[5].binary)
        self.assertTrue(files[5].deleted)
        self.assertFalse(files[5].is_symlink)
        self.assertEqual(files[5].insert_count, 0)
        self.assertEqual(files[5].delete_count, 1)
        lines = files[5].data.splitlines()
        self.assertEqual(len(lines), 7)
        self.assertEqual(lines[0], b'diff --git a/OLDFILE b/OLDFILE')
        self.assertEqual(lines[6], b'-Goodbye')

        self.assertEqual(files[6].orig_filename, b'readme2')
        self.assertEqual(files[6].modified_filename, b'readme2')
        self.assertEqual(files[6].orig_file_details, b'5e43098')
        self.assertEqual(files[6].modified_file_details, b'e248ef4')
        self.assertFalse(files[6].binary)
        self.assertFalse(files[6].deleted)
        self.assertFalse(files[6].is_symlink)
        self.assertEqual(files[6].insert_count, 1)
        self.assertEqual(files[6].delete_count, 1)
        lines = files[6].data.splitlines()
        self.assertEqual(len(lines), 7)
        self.assertEqual(lines[0], b'diff --git a/readme2 b/readme2')
        self.assertEqual(lines[6], b'+Hello there')

    def test_parse_diff_with_index_range(self):
        """Testing Git diff parsing with an index range"""
        diff = (b'diff --git a/foo/bar b/foo/bar2\n'
                b'similarity index 88%\n'
                b'rename from foo/bar\n'
                b'rename to foo/bar2\n'
                b'index 612544e4343bf04967eb5ea80257f6c64d6f42c7..'
                b'e88b7f15c03d141d0bb38c8e49bb6c411ebfe1f1 100644\n'
                b'--- a/foo/bar\n'
                b'+++ b/foo/bar2\n'
                b'@ -1,1 +1,1 @@\n'
                b'-blah blah\n'
                b'+blah\n')

        files = self.tool.get_parser(diff).parse()
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0].orig_filename, b'foo/bar')
        self.assertEqual(files[0].modified_filename, b'foo/bar2')
        self.assertEqual(files[0].orig_file_details,
                         b'612544e4343bf04967eb5ea80257f6c64d6f42c7')
        self.assertEqual(files[0].modified_file_details,
                         b'e88b7f15c03d141d0bb38c8e49bb6c411ebfe1f1')
        self.assertEqual(files[0].insert_count, 1)
        self.assertEqual(files[0].delete_count, 1)

    def test_parse_diff_with_deleted_binary_files(self):
        """Testing Git diff parsing with deleted binary files"""
        diff = (b'diff --git a/foo.bin b/foo.bin\n'
                b'deleted file mode 100644\n'
                b'Binary file foo.bin has changed\n'
                b'diff --git a/bar.bin b/bar.bin\n'
                b'deleted file mode 100644\n'
                b'Binary file bar.bin has changed\n')

        files = self.tool.get_parser(diff).parse()
        self.assertEqual(len(files), 2)
        self.assertEqual(files[0].orig_filename, b'foo.bin')
        self.assertEqual(files[0].modified_filename, b'foo.bin')
        self.assertEqual(files[0].binary, True)
        self.assertEqual(files[0].deleted, True)
        self.assertFalse(files[0].is_symlink)
        self.assertEqual(files[0].insert_count, 0)
        self.assertEqual(files[0].delete_count, 0)
        self.assertEqual(files[1].orig_filename, b'bar.bin')
        self.assertEqual(files[1].modified_filename, b'bar.bin')
        self.assertEqual(files[1].binary, True)
        self.assertEqual(files[1].deleted, True)
        self.assertFalse(files[1].is_symlink)
        self.assertEqual(files[1].insert_count, 0)
        self.assertEqual(files[1].delete_count, 0)

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
            b'\n')
        diff1 = (
            b'diff --git a/foo/bar b/foo/bar2\n'
            b'index 612544e4343bf04967eb5ea80257f6c64d6f42c7..'
            b'e88b7f15c03d141d0bb38c8e49bb6c411ebfe1f1 100644\n'
            b'--- a/foo/bar\n'
            b'+++ b/foo/bar2\n'
            b'@ -1,1 +1,1 @@\n'
            b'-blah blah\n'
            b'+blah\n')
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
            b'1.7.1\n')
        diff = preamble + diff1 + diff2

        files = self.tool.get_parser(diff).parse()
        self.assertEqual(len(files), 2)
        self.assertEqual(files[0].orig_filename, b'foo/bar')
        self.assertEqual(files[0].modified_filename, b'foo/bar2')
        self.assertEqual(files[0].orig_file_details,
                         b'612544e4343bf04967eb5ea80257f6c64d6f42c7')
        self.assertEqual(files[0].modified_file_details,
                         b'e88b7f15c03d141d0bb38c8e49bb6c411ebfe1f1')
        self.assertEqual(files[0].data, preamble + diff1)
        self.assertEqual(files[0].insert_count, 1)
        self.assertEqual(files[0].delete_count, 1)

        self.assertEqual(files[1].orig_filename, b'README')
        self.assertEqual(files[1].modified_filename, b'README')
        self.assertEqual(files[1].orig_file_details,
                         b'712544e4343bf04967eb5ea80257f6c64d6f42c7')
        self.assertEqual(files[1].modified_file_details,
                         b'f88b7f15c03d141d0bb38c8e49bb6c411ebfe1f1')
        self.assertEqual(files[1].data, diff2)
        self.assertEqual(files[1].insert_count, 1)
        self.assertEqual(files[1].delete_count, 2)

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
        diff = (b'diff --git a/foo/bar b/foo/bar2\n'
                b'similarity index 100%\n'
                b'copy from foo/bar\n'
                b'copy to foo/bar2\n'
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
                b'+blah\n')

        files = self.tool.get_parser(diff).parse()
        self.assertEqual(len(files), 2)

        f = files[0]
        self.assertEqual(f.orig_filename, b'foo/bar')
        self.assertEqual(f.modified_filename, b'foo/bar2')
        self.assertEqual(f.orig_file_details, b'')
        self.assertEqual(f.modified_file_details, b'')
        self.assertEqual(f.insert_count, 0)
        self.assertEqual(f.delete_count, 0)
        self.assertFalse(f.moved)
        self.assertTrue(f.copied)
        self.assertFalse(f.is_symlink)

        f = files[1]
        self.assertEqual(f.orig_filename, b'foo/bar')
        self.assertEqual(f.modified_filename, b'foo/bar3')
        self.assertEqual(f.orig_file_details,
                         b'612544e4343bf04967eb5ea80257f6c64d6f42c7')
        self.assertEqual(f.modified_file_details,
                         b'e88b7f15c03d141d0bb38c8e49bb6c411ebfe1f1')
        self.assertEqual(f.insert_count, 1)
        self.assertEqual(f.delete_count, 1)
        self.assertTrue(f.moved)
        self.assertFalse(f.copied)
        self.assertFalse(f.is_symlink)

    def test_parse_diff_with_mode_change_and_rename(self):
        """Testing Git diff parsing with mode change and rename"""
        diff = (b'diff --git a/foo/bar b/foo/bar2\n'
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
                b'+blah\n')

        files = self.tool.get_parser(diff).parse()
        self.assertEqual(len(files), 1)

        f = files[0]
        self.assertEqual(f.orig_filename, b'foo/bar')
        self.assertEqual(f.modified_filename, b'foo/bar2')
        self.assertEqual(f.orig_file_details,
                         b'612544e4343bf04967eb5ea80257f6c64d6f42c7')
        self.assertEqual(f.modified_file_details,
                         b'e88b7f15c03d141d0bb38c8e49bb6c411ebfe1f1')
        self.assertEqual(f.insert_count, 1)
        self.assertEqual(f.delete_count, 1)
        self.assertTrue(f.moved)
        self.assertFalse(f.copied)
        self.assertFalse(f.is_symlink)

    def test_diff_git_line_without_a_b(self):
        """Testing parsing Git diff with deleted file without a/ and
        b/ filename prefixes
        """
        diff = (b'diff --git foo foo\n'
                b'deleted file mode 100644\n'
                b'index 612544e4343bf04967eb5ea80257f6c64d6f42c7..'
                b'0000000000000000000000000000000000000000\n')

        files = self.tool.get_parser(diff).parse()
        self.assertEqual(len(files), 1)

        f = files[0]
        self.assertEqual(f.orig_filename, b'foo')
        self.assertEqual(f.modified_filename, b'foo')
        self.assertTrue(f.deleted)
        self.assertFalse(f.is_symlink)

    def test_diff_git_line_without_a_b_quotes(self):
        """Testing parsing Git diff with deleted file without a/ and
        b/ filename prefixes and with quotes
        """
        diff = (b'diff --git "foo" "foo"\n'
                b'deleted file mode 100644\n'
                b'index 612544e4343bf04967eb5ea80257f6c64d6f42c7..'
                b'0000000000000000000000000000000000000000\n')

        files = self.tool.get_parser(diff).parse()
        self.assertEqual(len(files), 1)

        f = files[0]
        self.assertEqual(f.orig_filename, b'foo')
        self.assertEqual(f.modified_filename, b'foo')
        self.assertTrue(f.deleted)
        self.assertFalse(f.is_symlink)

    def test_diff_git_line_without_a_b_and_spaces(self):
        """Testing parsing Git diff with deleted file without a/ and
        b/ filename prefixes and with spaces
        """
        diff = (b'diff --git foo bar1 foo bar1\n'
                b'deleted file mode 100644\n'
                b'index 612544e4343bf04967eb5ea80257f6c64d6f42c7..'
                b'0000000000000000000000000000000000000000\n')

        files = self.tool.get_parser(diff).parse()
        self.assertEqual(len(files), 1)

        f = files[0]
        self.assertEqual(f.orig_filename, b'foo bar1')
        self.assertEqual(f.modified_filename, b'foo bar1')
        self.assertTrue(f.deleted)
        self.assertFalse(f.is_symlink)

    def test_diff_git_line_without_a_b_and_spaces_quotes(self):
        """Testing parsing Git diff with deleted file without a/ and
        b/ filename prefixes and with space and quotes
        """
        diff = (b'diff --git "foo bar1" "foo bar1"\n'
                b'deleted file mode 100644\n'
                b'index 612544e4343bf04967eb5ea80257f6c64d6f42c7..'
                b'0000000000000000000000000000000000000000\n')

        files = self.tool.get_parser(diff).parse()
        self.assertEqual(len(files), 1)

        f = files[0]
        self.assertEqual(f.orig_filename, b'foo bar1')
        self.assertEqual(f.modified_filename, b'foo bar1')

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

        self.assertTrue(six.text_type(cm.exception).startswith(
            'Unable to parse the "diff --git" line'))

    def test_diff_git_line_without_a_b_and_spaces_quotes_changed(self):
        """Testing parsing Git diff with deleted file without a/ and
        b/ filename prefixes and with spaces and quotes, with filename
        changes
        """
        diff = (b'diff --git "foo bar1" "foo bar2"\n'
                b'deleted file mode 100644\n'
                b'index 612544e4343bf04967eb5ea80257f6c64d6f42c7..'
                b'0000000000000000000000000000000000000000\n'
                b'diff --git "foo bar1" foo\n'
                b'deleted file mode 100644\n'
                b'index 612544e4343bf04967eb5ea80257f6c64d6f42c7..'
                b'0000000000000000000000000000000000000000\n'
                b'diff --git foo "foo bar1"\n'
                b'deleted file mode 100644\n'
                b'index 612544e4343bf04967eb5ea80257f6c64d6f42c7..'
                b'0000000000000000000000000000000000000000\n')

        files = self.tool.get_parser(diff).parse()
        self.assertEqual(len(files), 3)

        f = files[0]
        self.assertEqual(f.orig_filename, b'foo bar1')
        self.assertEqual(f.modified_filename, b'foo bar2')
        self.assertTrue(f.deleted)
        self.assertFalse(f.is_symlink)

        f = files[1]
        self.assertEqual(f.orig_filename, b'foo bar1')
        self.assertEqual(f.modified_filename, b'foo')

        f = files[2]
        self.assertEqual(f.orig_filename, b'foo')
        self.assertEqual(f.modified_filename, b'foo bar1')

    def test_diff_git_symlink_added(self):
        """Testing parsing Git diff with symlink added"""
        diff = (b'diff --git a/link b/link\n'
                b'new file mode 120000\n'
                b'index 0000000..100b938\n'
                b'--- /dev/null\n'
                b'+++ b/link\n'
                b'@@ -0,0 +1 @@\n'
                b'+README\n'
                b'\\ No newline at end of file\n')
        files = self.tool.get_parser(diff).parse()
        self.assertEqual(len(files), 1)

        f = files[0]
        self.assertEqual(f.orig_file_details, PRE_CREATION)
        self.assertEqual(f.modified_filename, b'link')
        self.assertTrue(f.is_symlink)

    def test_diff_git_symlink_changed(self):
        """Testing parsing Git diff with symlink changed"""
        diff = (b'diff --git a/link b/link\n'
                b'index 100b937..100b938 120000\n'
                b'--- a/link\n'
                b'+++ b/link\n'
                b'@@ -1 +1 @@\n'
                b'-README\n'
                b'\\ No newline at end of file\n'
                b'+README.md\n'
                b'\\ No newline at end of file\n')

        files = self.tool.get_parser(diff).parse()
        self.assertEqual(len(files), 1)

        f = files[0]
        self.assertEqual(f.modified_filename, b'link')
        self.assertEqual(f.orig_filename, b'link')
        self.assertTrue(f.is_symlink)

    def test_diff_git_symlink_removed(self):
        """Testing parsing Git diff with symlink removed"""
        diff = (b'diff --git a/link b/link\n'
                b'deleted file mode 120000\n'
                b'index 100b938..0000000\n'
                b'--- a/link\n'
                b'+++ /dev/null\n'
                b'@@ -1 +0,0 @@\n'
                b'-README.txt\n'
                b'\\ No newline at end of file\n')

        files = self.tool.get_parser(diff).parse()
        self.assertEqual(len(files), 1)

        f = files[0]
        self.assertEqual(f.orig_filename, b'link')
        self.assertTrue(f.deleted)
        self.assertTrue(f.is_symlink)

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
        self.spy_on(self.remote_repository._get_file_uncached,
                    call_fake=lambda a, b, x, y, z: 'first')
        self.assertEqual(self.remote_repository.get_file('PATH', 'd7e96b3'),
                         'first')
        # Ensure output of fake result matches.
        self.remote_repository._get_file_uncached.unspy()
        self.spy_on(self.remote_repository._get_file_uncached,
                    call_fake=lambda a, b, x, y, z: 'second')
        # Grab from cache when no changes and change fake result to confirm
        # it is not called.
        self.assertEqual(self.remote_repository.get_file('PATH', 'd7e96b3'),
                         'first')
        self.remote_repository.raw_file_url = (
            'http://github.com/api/v2/yaml/blob/show/reviewboard/<revision>')
        # When raw_file_url changed, do not grab from cache and ensure output
        # equals second fake value.
        self.assertEqual(self.remote_repository.get_file('PATH', 'd7e96b3'),
                         'second')

    def test_get_file_exists_caching_with_raw_url(self):
        """Testing Repository.get_file_exists properly checks file existence in
        repository or cache when raw file URL changes
        """
        self.spy_on(self.remote_repository._get_file_exists_uncached,
                    call_fake=lambda a, b, x, y, z: True)
        # Use spy to put key into cache
        self.assertTrue(self.remote_repository.get_file_exists('PATH',
                                                               'd7e96b3'))
        # Remove spy to ensure key is still in cache without needing spy
        self.remote_repository._get_file_exists_uncached.unspy()
        self.assertTrue(self.remote_repository.get_file_exists('PATH',
                                                               'd7e96b3'))
        self.remote_repository.raw_file_url = (
            'http://github.com/api/v2/yaml/blob/show/reviewboard/<revision>')
        # Does not exist when raw_file_url changed because it is not cached.
        self.assertFalse(self.remote_repository.get_file_exists('PATH',
                                                                'd7e96b3'))


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
