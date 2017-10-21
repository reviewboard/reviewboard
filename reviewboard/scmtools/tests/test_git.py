# coding=utf-8
from __future__ import unicode_literals

import os

import nose
from django.utils import six
from kgb import SpyAgency

from reviewboard.diffviewer.parser import DiffParserError
from reviewboard.scmtools.core import PRE_CREATION
from reviewboard.scmtools.errors import SCMError, FileNotFoundError
from reviewboard.scmtools.git import ShortSHA1Error, GitClient
from reviewboard.scmtools.models import Repository, Tool
from reviewboard.scmtools.tests.testcases import SCMTestCase


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
        with open(filename, 'r') as f:
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
        diff = self._read_fixture('git_filemode.diff')

        file = self._get_file_in_diff(diff)
        self.assertEqual(file.origFile, 'testing')
        self.assertEqual(file.newFile, 'testing')
        self.assertEqual(file.origInfo, 'e69de29')
        self.assertEqual(file.newInfo, 'bcae657')
        self.assertFalse(file.binary)
        self.assertFalse(file.deleted)
        self.assertFalse(file.is_symlink)
        self.assertEqual(file.data.splitlines()[0],
                         "diff --git a/testing b/testing")
        self.assertEqual(file.data.splitlines()[-1], "+ADD")
        self.assertEqual(file.insert_count, 1)
        self.assertEqual(file.delete_count, 0)

    def test_filemode_with_following_diff(self):
        """Testing parsing filemode changes with following Git diff"""
        diff = self._read_fixture('git_filemode2.diff')

        file = self._get_file_in_diff(diff)
        self.assertEqual(file.origFile, 'testing')
        self.assertEqual(file.newFile, 'testing')
        self.assertEqual(file.origInfo, 'e69de29')
        self.assertEqual(file.newInfo, 'bcae657')
        self.assertFalse(file.binary)
        self.assertFalse(file.deleted)
        self.assertFalse(file.is_symlink)
        self.assertEqual(file.data.splitlines()[0],
                         "diff --git a/testing b/testing")
        self.assertEqual(file.data.splitlines()[-1], "+ADD")
        self.assertEqual(file.insert_count, 1)
        self.assertEqual(file.delete_count, 0)

        file = self._get_file_in_diff(diff, 1)
        self.assertEqual(file.origFile, 'cfg/testcase.ini')
        self.assertEqual(file.newFile, 'cfg/testcase.ini')
        self.assertEqual(file.origInfo, 'cc18ec8')
        self.assertEqual(file.newInfo, '5e70b73')
        self.assertEqual(file.data.splitlines()[0],
                         "diff --git a/cfg/testcase.ini b/cfg/testcase.ini")
        self.assertEqual(file.data.splitlines()[-1], '+db = pyunit')
        self.assertEqual(file.insert_count, 2)
        self.assertEqual(file.delete_count, 1)

    def test_simple_diff(self):
        """Testing parsing simple Git diff"""
        diff = self._read_fixture('git_simple.diff')

        file = self._get_file_in_diff(diff)
        self.assertEqual(file.origFile, 'cfg/testcase.ini')
        self.assertEqual(file.newFile, 'cfg/testcase.ini')
        self.assertEqual(file.origInfo, 'cc18ec8')
        self.assertEqual(file.newInfo, '5e70b73')
        self.assertFalse(file.binary)
        self.assertFalse(file.deleted)
        self.assertFalse(file.is_symlink)
        self.assertEqual(len(file.data), 249)
        self.assertEqual(file.data.splitlines()[0],
                         "diff --git a/cfg/testcase.ini b/cfg/testcase.ini")
        self.assertEqual(file.data.splitlines()[-1], "+db = pyunit")
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
        self.assertEqual(file.origFile, 'cfg/téstcase.ini')
        self.assertEqual(file.newFile, 'cfg/téstcase.ini')
        self.assertEqual(file.origInfo, 'cc18ec8')
        self.assertEqual(file.newInfo, '5e70b73')
        self.assertFalse(file.binary)
        self.assertFalse(file.deleted)
        self.assertFalse(file.is_symlink)
        self.assertEqual(file.data.splitlines()[0].decode('utf-8'),
                         'diff --git a/cfg/téstcase.ini b/cfg/téstcase.ini')
        self.assertEqual(file.data.splitlines()[-1].decode('utf-8'),
                         '+db = pyunít')
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
            b'1.7.1\n')

        files = self.tool.get_parser(diff).parse()
        self.assertEqual(files[0].origFile, 'README')
        self.assertEqual(files[0].newFile, 'README')
        self.assertEqual(files[0].origInfo,
                         '712544e4343bf04967eb5ea80257f6c64d6f42c7')
        self.assertEqual(files[0].newInfo,
                         'f88b7f15c03d141d0bb38c8e49bb6c411ebfe1f1')
        self.assertEqual(files[0].data, diff)
        self.assertEqual(files[0].insert_count, 1)
        self.assertEqual(files[0].delete_count, 2)

    def test_new_file_diff(self):
        """Testing parsing Git diff with new file"""
        diff = self._read_fixture('git_newfile.diff')

        file = self._get_file_in_diff(diff)
        self.assertEqual(file.origFile, 'IAMNEW')
        self.assertEqual(file.newFile, 'IAMNEW')
        self.assertEqual(file.origInfo, PRE_CREATION)
        self.assertEqual(file.newInfo, 'e69de29')
        self.assertFalse(file.binary)
        self.assertFalse(file.deleted)
        self.assertFalse(file.is_symlink)
        self.assertEqual(len(file.data), 123)
        self.assertEqual(file.data.splitlines()[0],
                         'diff --git a/IAMNEW b/IAMNEW')
        self.assertEqual(file.data.splitlines()[-1], '+Hello')
        self.assertEqual(file.insert_count, 1)
        self.assertEqual(file.delete_count, 0)

    def test_new_file_no_content_diff(self):
        """Testing parsing Git diff new file, no content"""
        diff = self._read_fixture('git_newfile_nocontent.diff')
        files = self.tool.get_parser(diff).parse()
        self.assertEqual(len(files), 1)

        file = self._get_file_in_diff(diff)
        self.assertEqual(file.origFile, 'newfile')
        self.assertEqual(file.newFile, 'newfile')
        self.assertEqual(file.origInfo, PRE_CREATION)
        self.assertEqual(file.newInfo, 'e69de29')
        self.assertFalse(file.binary)
        self.assertFalse(file.deleted)
        self.assertFalse(file.is_symlink)
        lines = file.data.splitlines()
        self.assertEqual(len(lines), 3)
        self.assertEqual(lines[0], 'diff --git a/newfile b/newfile')
        self.assertEqual(file.insert_count, 0)
        self.assertEqual(file.delete_count, 0)

    def test_new_file_no_content_with_following_diff(self):
        """Testing parsing Git diff new file, no content, with following"""
        diff = self._read_fixture('git_newfile_nocontent2.diff')
        files = self.tool.get_parser(diff).parse()
        self.assertEqual(len(files), 2)

        self.assertEqual(files[0].origFile, 'newfile')
        self.assertEqual(files[0].newFile, 'newfile')
        self.assertEqual(files[0].origInfo, PRE_CREATION)
        self.assertEqual(files[0].newInfo, 'e69de29')
        self.assertFalse(files[0].binary)
        self.assertFalse(files[0].deleted)
        self.assertFalse(files[0].is_symlink)
        lines = files[0].data.splitlines()
        self.assertEqual(len(lines), 3)
        self.assertEqual(lines[0], 'diff --git a/newfile b/newfile')
        self.assertEqual(files[0].insert_count, 0)
        self.assertEqual(files[0].delete_count, 0)

        self.assertEqual(files[1].origFile, 'cfg/testcase.ini')
        self.assertEqual(files[1].newFile, 'cfg/testcase.ini')
        self.assertEqual(files[1].origInfo, 'cc18ec8')
        self.assertEqual(files[1].newInfo, '5e70b73')
        lines = files[1].data.splitlines()
        self.assertEqual(len(lines), 13)
        self.assertEqual(lines[0],
                         'diff --git a/cfg/testcase.ini b/cfg/testcase.ini')
        self.assertEqual(lines[-1], '+db = pyunit')
        self.assertEqual(files[1].insert_count, 2)
        self.assertEqual(files[1].delete_count, 1)

    def test_del_file_diff(self):
        """Testing parsing Git diff with deleted file"""
        diff = self._read_fixture('git_delfile.diff')

        file = self._get_file_in_diff(diff)
        self.assertEqual(file.origFile, 'OLDFILE')
        self.assertEqual(file.newFile, 'OLDFILE')
        self.assertEqual(file.origInfo, '8ebcb01')
        self.assertEqual(file.newInfo, '0000000')
        self.assertFalse(file.binary)
        self.assertTrue(file.deleted)
        self.assertFalse(file.is_symlink)
        self.assertEqual(len(file.data), 132)
        self.assertEqual(file.data.splitlines()[0],
                         'diff --git a/OLDFILE b/OLDFILE')
        self.assertEqual(file.data.splitlines()[-1], '-Goodbye')
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

        self.assertEqual(files[0].origFile, 'empty')
        self.assertEqual(files[0].newFile, 'empty')
        self.assertEqual(files[0].origInfo,
                         'e69de29bb2d1d6434b8b29ae775ad8c2e48c5391')
        self.assertEqual(files[0].newInfo,
                         '0000000000000000000000000000000000000000')
        self.assertFalse(files[0].binary)
        self.assertTrue(files[0].deleted)
        self.assertFalse(files[0].is_symlink)
        self.assertEqual(len(files[0].data), 141)
        self.assertEqual(files[0].data.splitlines()[0],
                         'diff --git a/empty b/empty')
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

        self.assertEqual(files[0].origFile, 'empty')
        self.assertEqual(files[0].newFile, 'empty')
        self.assertEqual(files[0].origInfo,
                         'e69de29bb2d1d6434b8b29ae775ad8c2e48c5391')
        self.assertEqual(files[0].newInfo,
                         '0000000000000000000000000000000000000000')
        self.assertFalse(files[0].binary)
        self.assertTrue(files[0].deleted)
        self.assertFalse(files[0].is_symlink)
        self.assertEqual(len(files[0].data), 141)
        self.assertEqual(files[0].data.splitlines()[0],
                         'diff --git a/empty b/empty')
        self.assertEqual(files[0].insert_count, 0)
        self.assertEqual(files[0].delete_count, 0)

        self.assertEqual(files[1].origFile, 'foo/bar')
        self.assertEqual(files[1].newFile, 'foo/bar')
        self.assertEqual(files[1].origInfo,
                         '484ba93ef5b0aed5b72af8f4e9dc4cfd10ef1a81')
        self.assertEqual(files[1].newInfo,
                         '0ae4095ddfe7387d405bd53bd59bbb5d861114c5')
        self.assertFalse(files[1].binary)
        self.assertFalse(files[1].deleted)
        self.assertFalse(files[1].is_symlink)
        lines = files[1].data.splitlines()
        self.assertEqual(len(lines), 7)
        self.assertEqual(lines[0], 'diff --git a/foo/bar b/foo/bar')
        self.assertEqual(lines[5], '+Hello!')
        self.assertEqual(files[1].insert_count, 1)
        self.assertEqual(files[1].delete_count, 0)

    def test_binary_diff(self):
        """Testing parsing Git diff with binary"""
        diff = self._read_fixture('git_binary.diff')

        file = self._get_file_in_diff(diff)
        self.assertEqual(file.origFile, 'pysvn-1.5.1.tar.gz')
        self.assertEqual(file.newFile, 'pysvn-1.5.1.tar.gz')
        self.assertEqual(file.origInfo, PRE_CREATION)
        self.assertEqual(file.newInfo, '86b520c')
        self.assertTrue(file.binary)
        self.assertFalse(file.deleted)
        self.assertFalse(file.is_symlink)
        lines = file.data.splitlines()
        self.assertEqual(len(lines), 4)
        self.assertEqual(
            lines[0], 'diff --git a/pysvn-1.5.1.tar.gz b/pysvn-1.5.1.tar.gz')
        self.assertEqual(
            lines[3], 'Binary files /dev/null and b/pysvn-1.5.1.tar.gz differ')
        self.assertEqual(file.insert_count, 0)
        self.assertEqual(file.delete_count, 0)

    def test_complex_diff(self):
        """Testing parsing Git diff with existing and new files"""
        diff = self._read_fixture('git_complex.diff')
        files = self.tool.get_parser(diff).parse()
        self.assertEqual(len(files), 7)
        self.assertEqual(files[0].origFile, 'cfg/testcase.ini')
        self.assertEqual(files[0].newFile, 'cfg/testcase.ini')
        self.assertEqual(files[0].origInfo, '5e35098')
        self.assertEqual(files[0].newInfo, 'e254ef4')
        self.assertFalse(files[0].binary)
        self.assertFalse(files[0].deleted)
        self.assertFalse(files[0].is_symlink)
        self.assertEqual(files[0].insert_count, 2)
        self.assertEqual(files[0].delete_count, 1)
        self.assertEqual(len(files[0].data), 549)
        self.assertEqual(files[0].data.splitlines()[0],
                         'diff --git a/cfg/testcase.ini b/cfg/testcase.ini')
        self.assertEqual(files[0].data.splitlines()[13],
                         '         if isinstance(value, basestring):')

        self.assertEqual(files[1].origFile, 'tests/models.py')
        self.assertEqual(files[1].newFile, 'tests/models.py')
        self.assertEqual(files[1].origInfo, PRE_CREATION)
        self.assertEqual(files[1].newInfo, 'e69de29')
        self.assertFalse(files[1].binary)
        self.assertFalse(files[1].deleted)
        self.assertFalse(files[1].is_symlink)
        self.assertEqual(files[1].insert_count, 0)
        self.assertEqual(files[1].delete_count, 0)
        lines = files[1].data.splitlines()
        self.assertEqual(len(lines), 3)
        self.assertEqual(lines[0],
                         'diff --git a/tests/models.py b/tests/models.py')

        self.assertEqual(files[2].origFile, 'tests/tests.py')
        self.assertEqual(files[2].newFile, 'tests/tests.py')
        self.assertEqual(files[2].origInfo, PRE_CREATION)
        self.assertEqual(files[2].newInfo, 'e279a06')
        self.assertFalse(files[2].binary)
        self.assertFalse(files[2].deleted)
        self.assertFalse(files[2].is_symlink)
        self.assertEqual(files[2].insert_count, 2)
        self.assertEqual(files[2].delete_count, 0)
        lines = files[2].data.splitlines()
        self.assertEqual(len(lines), 8)
        self.assertEqual(lines[0],
                         'diff --git a/tests/tests.py b/tests/tests.py')
        self.assertEqual(lines[7],
                         '+This is some new content')

        self.assertEqual(files[3].origFile, 'pysvn-1.5.1.tar.gz')
        self.assertEqual(files[3].newFile, 'pysvn-1.5.1.tar.gz')
        self.assertEqual(files[3].origInfo, PRE_CREATION)
        self.assertEqual(files[3].newInfo, '86b520c')
        self.assertTrue(files[3].binary)
        self.assertFalse(files[3].deleted)
        self.assertFalse(files[3].is_symlink)
        self.assertEqual(files[3].insert_count, 0)
        self.assertEqual(files[3].delete_count, 0)
        lines = files[3].data.splitlines()
        self.assertEqual(len(lines), 4)
        self.assertEqual(
            lines[0], 'diff --git a/pysvn-1.5.1.tar.gz b/pysvn-1.5.1.tar.gz')
        self.assertEqual(lines[3],
                         'Binary files /dev/null and b/pysvn-1.5.1.tar.gz '
                         'differ')

        self.assertEqual(files[4].origFile, 'readme')
        self.assertEqual(files[4].newFile, 'readme')
        self.assertEqual(files[4].origInfo, '5e35098')
        self.assertEqual(files[4].newInfo, 'e254ef4')
        self.assertFalse(files[4].binary)
        self.assertFalse(files[4].deleted)
        self.assertFalse(files[4].is_symlink)
        self.assertEqual(files[4].insert_count, 1)
        self.assertEqual(files[4].delete_count, 1)
        lines = files[4].data.splitlines()
        self.assertEqual(len(lines), 7)
        self.assertEqual(lines[0], 'diff --git a/readme b/readme')
        self.assertEqual(lines[6], '+Hello there')

        self.assertEqual(files[5].origFile, 'OLDFILE')
        self.assertEqual(files[5].newFile, 'OLDFILE')
        self.assertEqual(files[5].origInfo, '8ebcb01')
        self.assertEqual(files[5].newInfo, '0000000')
        self.assertFalse(files[5].binary)
        self.assertTrue(files[5].deleted)
        self.assertFalse(files[5].is_symlink)
        self.assertEqual(files[5].insert_count, 0)
        self.assertEqual(files[5].delete_count, 1)
        lines = files[5].data.splitlines()
        self.assertEqual(len(lines), 7)
        self.assertEqual(lines[0], 'diff --git a/OLDFILE b/OLDFILE')
        self.assertEqual(lines[6], '-Goodbye')

        self.assertEqual(files[6].origFile, 'readme2')
        self.assertEqual(files[6].newFile, 'readme2')
        self.assertEqual(files[6].origInfo, '5e43098')
        self.assertEqual(files[6].newInfo, 'e248ef4')
        self.assertFalse(files[6].binary)
        self.assertFalse(files[6].deleted)
        self.assertFalse(files[6].is_symlink)
        self.assertEqual(files[6].insert_count, 1)
        self.assertEqual(files[6].delete_count, 1)
        lines = files[6].data.splitlines()
        self.assertEqual(len(lines), 7)
        self.assertEqual(lines[0], 'diff --git a/readme2 b/readme2')
        self.assertEqual(lines[6], '+Hello there')

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
        self.assertEqual(files[0].origFile, 'foo/bar')
        self.assertEqual(files[0].newFile, 'foo/bar2')
        self.assertEqual(files[0].origInfo,
                         '612544e4343bf04967eb5ea80257f6c64d6f42c7')
        self.assertEqual(files[0].newInfo,
                         'e88b7f15c03d141d0bb38c8e49bb6c411ebfe1f1')
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
        self.assertEqual(files[0].origFile, 'foo.bin')
        self.assertEqual(files[0].newFile, 'foo.bin')
        self.assertEqual(files[0].binary, True)
        self.assertEqual(files[0].deleted, True)
        self.assertFalse(files[0].is_symlink)
        self.assertEqual(files[0].insert_count, 0)
        self.assertEqual(files[0].delete_count, 0)
        self.assertEqual(files[1].origFile, 'bar.bin')
        self.assertEqual(files[1].newFile, 'bar.bin')
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
        self.assertEqual(files[0].origFile, 'foo/bar')
        self.assertEqual(files[0].newFile, 'foo/bar2')
        self.assertEqual(files[0].origInfo,
                         '612544e4343bf04967eb5ea80257f6c64d6f42c7')
        self.assertEqual(files[0].newInfo,
                         'e88b7f15c03d141d0bb38c8e49bb6c411ebfe1f1')
        self.assertEqual(files[0].data, preamble + diff1)
        self.assertEqual(files[0].insert_count, 1)
        self.assertEqual(files[0].delete_count, 1)

        self.assertEqual(files[1].origFile, 'README')
        self.assertEqual(files[1].newFile, 'README')
        self.assertEqual(files[1].origInfo,
                         '712544e4343bf04967eb5ea80257f6c64d6f42c7')
        self.assertEqual(files[1].newInfo,
                         'f88b7f15c03d141d0bb38c8e49bb6c411ebfe1f1')
        self.assertEqual(files[1].data, diff2)
        self.assertEqual(files[1].insert_count, 1)
        self.assertEqual(files[1].delete_count, 2)

    def test_parse_diff_revision(self):
        """Testing Git revision number parsing"""
        self.assertEqual(
            self.tool.parse_diff_revision('doc/readme', 'bf544ea'),
            ('doc/readme', 'bf544ea'))
        self.assertEqual(
            self.tool.parse_diff_revision('/dev/null', 'bf544ea'),
            ('/dev/null', PRE_CREATION))
        self.assertEqual(
            self.tool.parse_diff_revision('/dev/null', '0000000'),
            ('/dev/null', PRE_CREATION))

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
        self.assertEqual(f.origFile, 'foo/bar')
        self.assertEqual(f.newFile, 'foo/bar2')
        self.assertEqual(f.origInfo, '')
        self.assertEqual(f.newInfo, '')
        self.assertEqual(f.insert_count, 0)
        self.assertEqual(f.delete_count, 0)
        self.assertFalse(f.moved)
        self.assertTrue(f.copied)
        self.assertFalse(f.is_symlink)

        f = files[1]
        self.assertEqual(f.origFile, 'foo/bar')
        self.assertEqual(f.newFile, 'foo/bar3')
        self.assertEqual(f.origInfo,
                         '612544e4343bf04967eb5ea80257f6c64d6f42c7')
        self.assertEqual(f.newInfo,
                         'e88b7f15c03d141d0bb38c8e49bb6c411ebfe1f1')
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
        self.assertEqual(f.origFile, 'foo/bar')
        self.assertEqual(f.newFile, 'foo/bar2')
        self.assertEqual(f.origInfo,
                         '612544e4343bf04967eb5ea80257f6c64d6f42c7')
        self.assertEqual(f.newInfo,
                         'e88b7f15c03d141d0bb38c8e49bb6c411ebfe1f1')
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
        self.assertEqual(f.origFile, 'foo')
        self.assertEqual(f.newFile, 'foo')
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
        self.assertEqual(f.origFile, 'foo')
        self.assertEqual(f.newFile, 'foo')
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
        self.assertEqual(f.origFile, 'foo bar1')
        self.assertEqual(f.newFile, 'foo bar1')
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
        self.assertEqual(f.origFile, 'foo bar1')
        self.assertEqual(f.newFile, 'foo bar1')

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
        self.assertEqual(f.origFile, 'foo bar1')
        self.assertEqual(f.newFile, 'foo bar2')
        self.assertTrue(f.deleted)
        self.assertFalse(f.is_symlink)

        f = files[1]
        self.assertEqual(f.origFile, 'foo bar1')
        self.assertEqual(f.newFile, 'foo')

        f = files[2]
        self.assertEqual(f.origFile, 'foo')
        self.assertEqual(f.newFile, 'foo bar1')

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
        self.assertEqual(f.origInfo, PRE_CREATION)
        self.assertEqual(f.newFile, 'link')
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
        self.assertEqual(f.newFile, 'link')
        self.assertEqual(f.origFile, 'link')
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
        self.assertEqual(f.origFile, 'link')
        self.assertTrue(f.deleted)
        self.assertTrue(f.is_symlink)

    def test_file_exists(self):
        """Testing GitTool.file_exists"""
        self.assertTrue(self.tool.file_exists('readme', 'e965047'))
        self.assertTrue(self.tool.file_exists('readme', 'd6613f5'))

        self.assertTrue(not self.tool.file_exists('readme', PRE_CREATION))
        self.assertTrue(not self.tool.file_exists('readme', 'fffffff'))
        self.assertTrue(not self.tool.file_exists('readme2', 'fffffff'))

        # these sha's are valid, but commit and tree objects, not blobs
        self.assertTrue(not self.tool.file_exists('readme', 'a62df6c'))
        self.assertTrue(not self.tool.file_exists('readme2', 'ccffbb4'))

    def test_get_file(self):
        """Testing GitTool.get_file"""
        self.assertEqual(self.tool.get_file('readme', PRE_CREATION), b'')
        self.assertTrue(
            isinstance(self.tool.get_file('readme', 'e965047'), bytes))
        self.assertEqual(self.tool.get_file('readme', 'e965047'), b'Hello\n')
        self.assertEqual(self.tool.get_file('readme', 'd6613f5'),
                         b'Hello there\n')

        self.assertEqual(self.tool.get_file('readme'), b'Hello there\n')

        self.assertRaises(SCMError, lambda: self.tool.get_file(''))

        self.assertRaises(FileNotFoundError,
                          lambda: self.tool.get_file('', '0000000'))
        self.assertRaises(FileNotFoundError,
                          lambda: self.tool.get_file('hello', '0000000'))
        self.assertRaises(FileNotFoundError,
                          lambda: self.tool.get_file('readme', '0000000'))

    def test_parse_diff_revision_with_remote_and_short_SHA1_error(self):
        """Testing GitTool.parse_diff_revision with remote files and short
        SHA1 error
        """
        self.assertRaises(
            ShortSHA1Error,
            lambda: self.remote_tool.parse_diff_revision('README', 'd7e96b3'))

    def test_get_file_with_remote_and_short_SHA1_error(self):
        """Testing GitTool.get_file with remote files and short SHA1 error"""
        self.assertRaises(
            ShortSHA1Error,
            lambda: self.remote_tool.get_file('README', 'd7e96b3'))

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
