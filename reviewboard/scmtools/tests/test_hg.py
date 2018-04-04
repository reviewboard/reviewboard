# coding=utf-8
from __future__ import unicode_literals

import os

import nose

from reviewboard.scmtools.core import PRE_CREATION, Revision
from reviewboard.scmtools.errors import SCMError, FileNotFoundError
from reviewboard.scmtools.hg import HgDiffParser, HgGitDiffParser
from reviewboard.scmtools.models import Repository, Tool
from reviewboard.scmtools.tests.testcases import SCMTestCase
from reviewboard.testing import online_only


class MercurialTests(SCMTestCase):
    """Unit tests for mercurial."""

    fixtures = ['test_scmtools']

    def setUp(self):
        super(MercurialTests, self).setUp()

        hg_repo_path = os.path.join(os.path.dirname(__file__),
                                    '..', 'testdata', 'hg_repo')
        self.repository = Repository(name='Test HG',
                                     path=hg_repo_path,
                                     tool=Tool.objects.get(name='Mercurial'))

        try:
            self.tool = self.repository.get_scmtool()
        except ImportError:
            raise nose.SkipTest('Hg is not installed')

    def _first_file_in_diff(self, diff):
        return self.tool.get_parser(diff).parse()[0]

    def test_ssh_disallowed(self):
        """Testing HgTool does not allow SSH URLs"""
        with self.assertRaises(SCMError):
            self.tool.check_repository('ssh://foo')

    def test_git_parser_selection_with_header(self):
        """Testing HgTool returns the git parser when a header is present"""
        diffContents = (b'# HG changeset patch\n'
                        b'# Node ID 6187592a72d7\n'
                        b'# Parent  9d3f4147f294\n'
                        b'diff --git a/emptyfile b/emptyfile\n'
                        b'new file mode 100644\n')

        parser = self.tool.get_parser(diffContents)
        self.assertEqual(type(parser), HgGitDiffParser)

    def test_hg_parser_selection_with_header(self):
        """Testing HgTool returns the hg parser when a header is present"""
        diffContents = (b'# HG changeset patch'
                        b'# Node ID 6187592a72d7\n'
                        b'# Parent  9d3f4147f294\n'
                        b'diff -r 9d3f4147f294 -r 6187592a72d7 new.py\n'
                        b'--- /dev/null   Thu Jan 01 00:00:00 1970 +0000\n'
                        b'+++ b/new.py  Tue Apr 21 12:20:05 2015 -0400\n')

        parser = self.tool.get_parser(diffContents)
        self.assertEqual(type(parser), HgDiffParser)

    def test_git_parser_sets_commit_ids(self):
        """Testing HgGitDiffParser sets the parser commit ids"""
        diffContents = (b'# HG changeset patch\n'
                        b'# Node ID 6187592a72d7\n'
                        b'# Parent  9d3f4147f294\n'
                        b'diff --git a/emptyfile b/emptyfile\n'
                        b'new file mode 100644\n')

        parser = self.tool.get_parser(diffContents)
        parser.parse()
        self.assertEqual(parser.new_commit_id, b'6187592a72d7')
        self.assertEqual(parser.base_commit_id, b'9d3f4147f294')

    def test_patch_creates_new_file(self):
        """Testing HgTool with a patch that creates a new file"""
        self.assertEqual(
            PRE_CREATION,
            self.tool.parse_diff_revision('/dev/null', 'bf544ea505f8')[1])

    def test_diff_parser_new_file(self):
        """Testing HgDiffParser with a diff that creates a new file"""
        diffContents = (b'diff -r bf544ea505f8 readme\n'
                        b'--- /dev/null\n'
                        b'+++ b/readme\n')

        file = self._first_file_in_diff(diffContents)
        self.assertEqual(file.origFile, 'readme')

    def test_diff_parser_with_added_empty_file(self):
        """Testing HgDiffParser with a diff with an added empty file"""
        diff = (b'diff -r 356a6127ef19 -r 4960455a8e88 empty\n'
                b'--- /dev/null\n'
                b'+++ b/empty\n')

        file = self._first_file_in_diff(diff)
        self.assertEqual(file.origInfo, PRE_CREATION)
        self.assertEqual(file.origFile, 'empty')
        self.assertEqual(file.newInfo, '4960455a8e88')
        self.assertEqual(file.newFile, 'empty')
        self.assertFalse(file.binary)
        self.assertFalse(file.deleted)
        self.assertEqual(file.insert_count, 0)
        self.assertEqual(file.delete_count, 0)

    def test_diff_parser_with_deleted_empty_file(self):
        """Testing HgDiffParser with a diff with a deleted empty file"""
        diff = (b'diff -r 356a6127ef19 -r 4960455a8e88 empty\n'
                b'--- a/empty\n'
                b'+++ /dev/null\n')

        file = self._first_file_in_diff(diff)
        self.assertEqual(file.origInfo, '356a6127ef19')
        self.assertEqual(file.origFile, 'empty')
        self.assertEqual(file.newInfo, '4960455a8e88')
        self.assertEqual(file.newFile, 'empty')
        self.assertFalse(file.binary)
        self.assertTrue(file.deleted)
        self.assertEqual(file.insert_count, 0)
        self.assertEqual(file.delete_count, 0)

    def test_diff_parser_uncommitted(self):
        """Testing HgDiffParser with a diff with an uncommitted change"""
        diffContents = (b'diff -r bf544ea505f8 readme\n'
                        b'--- a/readme\n'
                        b'+++ b/readme\n')

        file = self._first_file_in_diff(diffContents)
        self.assertEqual(file.origInfo, 'bf544ea505f8')
        self.assertEqual(file.origFile, 'readme')
        self.assertEqual(file.newInfo, 'Uncommitted')
        self.assertEqual(file.newFile, 'readme')

    def test_diff_parser_committed(self):
        """Testing HgDiffParser with a diff between committed revisions"""
        diffContents = (b'diff -r 356a6127ef19 -r 4960455a8e88 readme\n'
                        b'--- a/readme\n'
                        b'+++ b/readme\n')

        file = self._first_file_in_diff(diffContents)
        self.assertEqual(file.origInfo, '356a6127ef19')
        self.assertEqual(file.origFile, 'readme')
        self.assertEqual(file.newInfo, '4960455a8e88')
        self.assertEqual(file.newFile, 'readme')

    def test_diff_parser_with_preamble_junk(self):
        """Testing HgDiffParser with a diff that contains non-diff junk test
        as a preamble
        """
        diffContents = (b'changeset:   60:3613c58ad1d5\n'
                        b'user:        Michael Rowe <mrowe@mojain.com>\n'
                        b'date:        Fri Jul 27 11:44:37 2007 +1000\n'
                        b'files:       readme\n'
                        b'description:\n'
                        b'Update the readme file\n'
                        b'\n'
                        b'\n'
                        b'diff -r 356a6127ef19 -r 4960455a8e88 readme\n'
                        b'--- a/readme\n'
                        b'+++ b/readme\n')

        file = self._first_file_in_diff(diffContents)
        self.assertEqual(file.origInfo, '356a6127ef19')
        self.assertEqual(file.origFile, 'readme')
        self.assertEqual(file.newInfo, '4960455a8e88')
        self.assertEqual(file.newFile, 'readme')

    def test_git_diff_parsing(self):
        """Testing HgDiffParser git diff support"""
        diffContents = (b'# Node ID 4960455a8e88\n'
                        b'# Parent bf544ea505f8\n'
                        b'diff --git a/path/to file/readme.txt '
                        b'b/new/path to/readme.txt\n'
                        b'rename from path/to file/readme.txt\n'
                        b'rename to new/path to/readme.txt\n'
                        b'--- a/path/to file/readme.txt\n'
                        b'+++ b/new/path to/readme.txt\n')

        file = self._first_file_in_diff(diffContents)
        self.assertEqual(file.origInfo, 'bf544ea505f8')
        self.assertEqual(file.origFile, 'path/to file/readme.txt')
        self.assertEqual(file.newInfo, '4960455a8e88')
        self.assertEqual(file.newFile, 'new/path to/readme.txt')

    def test_diff_parser_unicode(self):
        """Testing HgDiffParser with unicode characters"""

        diffContents = ('diff -r bf544ea505f8 réadme\n'
                        '--- a/réadme\n'
                        '+++ b/réadme\n').encode('utf-8')

        file = self._first_file_in_diff(diffContents)
        self.assertEqual(file.origInfo, 'bf544ea505f8')
        self.assertEqual(file.origFile, 'réadme')
        self.assertEqual(file.newInfo, 'Uncommitted')
        self.assertEqual(file.newFile, 'réadme')

    def test_git_diff_parsing_unicode(self):
        """Testing HgDiffParser git diff with unicode characters"""
        diffContents = ('# Node ID 4960455a8e88\n'
                        '# Parent bf544ea505f8\n'
                        'diff --git a/path/to file/réadme.txt '
                        'b/new/path to/réadme.txt\n'
                        'rename from path/to file/réadme.txt\n'
                        'rename to new/path to/réadme.txt\n'
                        '--- a/path/to file/réadme.txt\n'
                        '+++ b/new/path to/réadme.txt\n').encode('utf-8')

        file = self._first_file_in_diff(diffContents)
        self.assertEqual(file.origInfo, 'bf544ea505f8')
        self.assertEqual(file.origFile, 'path/to file/réadme.txt')
        self.assertEqual(file.newInfo, '4960455a8e88')
        self.assertEqual(file.newFile, 'new/path to/réadme.txt')

    def test_revision_parsing(self):
        """Testing HgDiffParser revision number parsing"""
        self.assertEqual(
            self.tool.parse_diff_revision('doc/readme', 'bf544ea505f8'),
            ('doc/readme', 'bf544ea505f8'))

        self.assertEqual(
            self.tool.parse_diff_revision('/dev/null', 'bf544ea505f8'),
            ('/dev/null', PRE_CREATION))

        # TODO think of a meaningful thing to test here...
        # self.assertRaises(SCMException,
        #                  lambda: self.tool.parse_diff_revision('', 'hello'))

    def test_get_branches(self):
        """Testing list of branches in HgClient.get_change"""
        value = self.tool.get_branches()
        self.assertTrue(isinstance(value, list))
        self.assertEqual(len(value), 1)

        self.assertEqual(value[0].id, 'default')
        self.assertEqual(value[0].commit,
                         '661e5dd3c4938ecbe8f77e2fdfa905d70485f94c')
        self.assertEqual(value[0].default, True)

    def test_get_change(self):
        """Testing raw diff of HgClient.get_change"""
        self.assertRaises(SCMError, lambda: self.tool.get_change('dummy'))

        value = self.tool.get_change('0')
        self.assertNotIn('goodbye', value.diff)
        self.assertEqual(value.id, 'f814b6e226d2ba6d26d02ca8edbff91f57ab2786')
        value = self.tool.get_change('1')
        self.assertIn('goodbye', value.diff)
        self.assertEqual(value.id, '661e5dd3c4938ecbe8f77e2fdfa905d70485f94c')

    def test_get_commits(self):
        """Testing commit objects in HgClient.get_commits"""
        value = self.tool.get_commits()
        self.assertTrue(isinstance(value, list))
        self.assertEqual(len(value), 2)

        self.assertEqual(value[0].id,
                         '661e5dd3c4938ecbe8f77e2fdfa905d70485f94c')
        self.assertEqual(value[0].message, 'second')
        self.assertEqual(value[0].author_name,
                         'Michael Rowe <mike.rowe@nab.com.au>')
        self.assertEqual(value[0].date, '2007-08-07T17:12:23')
        self.assertEqual(value[0].parent,
                         'f814b6e226d2ba6d26d02ca8edbff91f57ab2786')
        self.assertEqual(value[0].base_commit_id,
                         'f814b6e226d2ba6d26d02ca8edbff91f57ab2786')

        self.assertEqual(value[1].id,
                         'f814b6e226d2ba6d26d02ca8edbff91f57ab2786')
        self.assertEqual(value[1].message, 'first')
        self.assertEqual(value[1].author_name,
                         'Michael Rowe <mike.rowe@nab.com.au>')
        self.assertEqual(value[1].date, '2007-08-07T17:11:57')
        self.assertEqual(value[1].parent,
                         '0000000000000000000000000000000000000000')
        self.assertEqual(value[1].base_commit_id,
                         '0000000000000000000000000000000000000000')

        self.assertRaisesRegexp(SCMError, 'Cannot load commits: ',
                                lambda: self.tool.get_commits(branch='x'))

        rev = 'f814b6e226d2ba6d26d02ca8edbff91f57ab2786'
        value = self.tool.get_commits(start=rev)
        self.assertTrue(isinstance(value, list))
        self.assertEqual(len(value), 1)

    def test_get_commits_with_non_utc_server_timezone(self):
        """Testing commit objects in HgClient.get_commits with
        settings.TIME_ZONE != UTC
        """
        old_tz = os.environ[b'TZ']
        os.environ[b'TZ'] = b'US/Pacific'

        try:
            value = self.tool.get_commits()
        finally:
            os.environ[b'TZ'] = old_tz

        self.assertTrue(isinstance(value, list))
        self.assertEqual(len(value), 2)

        self.assertEqual(value[0].id,
                         '661e5dd3c4938ecbe8f77e2fdfa905d70485f94c')
        self.assertEqual(value[0].message, 'second')
        self.assertEqual(value[0].author_name,
                         'Michael Rowe <mike.rowe@nab.com.au>')
        self.assertEqual(value[0].date, '2007-08-07T17:12:23')
        self.assertEqual(value[0].parent,
                         'f814b6e226d2ba6d26d02ca8edbff91f57ab2786')
        self.assertEqual(value[0].base_commit_id,
                         'f814b6e226d2ba6d26d02ca8edbff91f57ab2786')

        self.assertEqual(value[1].id,
                         'f814b6e226d2ba6d26d02ca8edbff91f57ab2786')
        self.assertEqual(value[1].message, 'first')
        self.assertEqual(value[1].author_name,
                         'Michael Rowe <mike.rowe@nab.com.au>')
        self.assertEqual(value[1].date, '2007-08-07T17:11:57')
        self.assertEqual(value[1].parent,
                         '0000000000000000000000000000000000000000')
        self.assertEqual(value[1].base_commit_id,
                         '0000000000000000000000000000000000000000')

        self.assertRaisesRegexp(SCMError, 'Cannot load commits: ',
                                lambda: self.tool.get_commits(branch='x'))

        rev = 'f814b6e226d2ba6d26d02ca8edbff91f57ab2786'
        value = self.tool.get_commits(start=rev)
        self.assertTrue(isinstance(value, list))
        self.assertEqual(len(value), 1)

    def test_get_file(self):
        """Testing HgTool.get_file"""
        rev = Revision('661e5dd3c493')
        file = 'doc/readme'

        value = self.tool.get_file(file, rev)
        self.assertTrue(isinstance(value, bytes))
        self.assertEqual(value, b'Hello\n\ngoodbye\n')

        self.assertTrue(self.tool.file_exists('doc/readme', rev))
        self.assertTrue(not self.tool.file_exists('doc/readme2', rev))

        self.assertRaises(FileNotFoundError, lambda: self.tool.get_file(''))

        self.assertRaises(FileNotFoundError,
                          lambda: self.tool.get_file('hello', PRE_CREATION))

    def test_get_file_base_commit_id_override(self):
        """Testing base_commit_id overrides revision in HgTool.get_file"""
        base_commit_id = Revision('661e5dd3c493')
        bogus_rev = Revision('bogusrevision')
        file = 'doc/readme'

        value = self.tool.get_file(file, bogus_rev,
                                   base_commit_id=base_commit_id)
        self.assertTrue(isinstance(value, bytes))
        self.assertEqual(value, b'Hello\n\ngoodbye\n')

        self.assertTrue(self.tool.file_exists(
            'doc/readme',
            bogus_rev,
            base_commit_id=base_commit_id))
        self.assertTrue(not self.tool.file_exists(
            'doc/readme2',
            bogus_rev,
            base_commit_id=base_commit_id))

    def test_interface(self):
        """Testing basic HgTool API"""
        self.assertTrue(self.tool.diffs_use_absolute_paths)

        self.assertRaises(NotImplementedError,
                          lambda: self.tool.get_changeset(1))

    @online_only
    def test_https_repo(self):
        """Testing HgTool.file_exists with an HTTPS-based repository"""
        repo = Repository(name='Test HG2',
                          path='https://bitbucket.org/pypy/pypy',
                          tool=Tool.objects.get(name='Mercurial'))
        tool = repo.get_scmtool()

        rev = Revision('877cf1960916')

        self.assertTrue(tool.file_exists('TODO.rst', rev))
        self.assertTrue(not tool.file_exists('TODO.rstNotFound', rev))
