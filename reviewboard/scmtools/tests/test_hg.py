# coding=utf-8
from __future__ import unicode_literals

import json
import os

import nose
from djblets.testing.decorators import add_fixtures
from kgb import SpyAgency

from reviewboard.scmtools.core import HEAD, PRE_CREATION, Revision
from reviewboard.scmtools.errors import SCMError, FileNotFoundError
from reviewboard.scmtools.hg import (HgDiffParser,
                                     HgGitDiffParser,
                                     HgTool,
                                     HgWebClient)
from reviewboard.scmtools.models import Repository, Tool
from reviewboard.scmtools.tests.testcases import SCMTestCase
from reviewboard.testing import online_only
from reviewboard.testing.testcase import TestCase


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
            self.tool.parse_diff_revision(filename=b'/dev/null',
                                          revision=b'bf544ea505f8')[1],
            PRE_CREATION)

    def test_diff_parser_new_file(self):
        """Testing HgDiffParser with a diff that creates a new file"""
        diffContents = (b'diff -r bf544ea505f8 readme\n'
                        b'--- /dev/null\n'
                        b'+++ b/readme\n')

        file = self._first_file_in_diff(diffContents)
        self.assertEqual(file.orig_filename, b'readme')

    def test_diff_parser_with_added_empty_file(self):
        """Testing HgDiffParser with a diff with an added empty file"""
        diff = (b'diff -r 356a6127ef19 -r 4960455a8e88 empty\n'
                b'--- /dev/null\n'
                b'+++ b/empty\n')

        file = self._first_file_in_diff(diff)
        self.assertEqual(file.orig_file_details, PRE_CREATION)
        self.assertEqual(file.orig_filename, b'empty')
        self.assertEqual(file.modified_file_details, b'4960455a8e88')
        self.assertEqual(file.modified_filename, b'empty')
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
        self.assertEqual(file.orig_file_details, b'356a6127ef19')
        self.assertEqual(file.orig_filename, b'empty')
        self.assertEqual(file.modified_file_details, b'4960455a8e88')
        self.assertEqual(file.modified_filename, b'empty')
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
        self.assertEqual(file.orig_file_details, b'bf544ea505f8')
        self.assertEqual(file.orig_filename, b'readme')
        self.assertEqual(file.modified_file_details, b'Uncommitted')
        self.assertEqual(file.modified_filename, b'readme')

    def test_diff_parser_committed(self):
        """Testing HgDiffParser with a diff between committed revisions"""
        diffContents = (b'diff -r 356a6127ef19 -r 4960455a8e88 readme\n'
                        b'--- a/readme\n'
                        b'+++ b/readme\n')

        file = self._first_file_in_diff(diffContents)
        self.assertEqual(file.orig_file_details, b'356a6127ef19')
        self.assertEqual(file.orig_filename, b'readme')
        self.assertEqual(file.modified_file_details, b'4960455a8e88')
        self.assertEqual(file.modified_filename, b'readme')

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
        self.assertEqual(file.orig_file_details, b'356a6127ef19')
        self.assertEqual(file.orig_filename, b'readme')
        self.assertEqual(file.modified_file_details, b'4960455a8e88')
        self.assertEqual(file.modified_filename, b'readme')

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
        self.assertEqual(file.orig_file_details, b'bf544ea505f8')
        self.assertEqual(file.orig_filename, b'path/to file/readme.txt')
        self.assertEqual(file.modified_file_details, b'4960455a8e88')
        self.assertEqual(file.modified_filename, b'new/path to/readme.txt')

    def test_diff_parser_unicode(self):
        """Testing HgDiffParser with unicode characters"""

        diffContents = ('diff -r bf544ea505f8 réadme\n'
                        '--- a/réadme\n'
                        '+++ b/réadme\n').encode('utf-8')

        file = self._first_file_in_diff(diffContents)
        self.assertEqual(file.orig_file_details, b'bf544ea505f8')
        self.assertEqual(file.orig_filename, 'réadme'.encode('utf-8'))
        self.assertEqual(file.modified_file_details, b'Uncommitted')
        self.assertEqual(file.modified_filename, 'réadme'.encode('utf-8'))

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
        self.assertEqual(file.orig_file_details, b'bf544ea505f8')
        self.assertEqual(file.orig_filename,
                         'path/to file/réadme.txt'.encode('utf-8'))
        self.assertEqual(file.modified_file_details, b'4960455a8e88')
        self.assertEqual(file.modified_filename,
                         'new/path to/réadme.txt'.encode('utf-8'))

    def test_revision_parsing(self):
        """Testing HgDiffParser revision number parsing"""
        self.assertEqual(
            self.tool.parse_diff_revision(filename=b'doc/readme',
                                          revision=b'bf544ea505f8'),
            (b'doc/readme', b'bf544ea505f8'))

        self.assertEqual(
            self.tool.parse_diff_revision(filename=b'/dev/null',
                                          revision=b'bf544ea505f8'),
            (b'/dev/null', PRE_CREATION))

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
        self.assertNotIn(b'goodbye', value.diff)
        self.assertEqual(value.id, 'f814b6e226d2ba6d26d02ca8edbff91f57ab2786')
        value = self.tool.get_change('1')
        self.assertIn(b'goodbye', value.diff)
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

        self.assertEqual(value[1].id,
                         'f814b6e226d2ba6d26d02ca8edbff91f57ab2786')
        self.assertEqual(value[1].message, 'first')
        self.assertEqual(value[1].author_name,
                         'Michael Rowe <mike.rowe@nab.com.au>')
        self.assertEqual(value[1].date, '2007-08-07T17:11:57')
        self.assertEqual(value[1].parent,
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
        old_tz = os.environ[str('TZ')]
        os.environ[str('TZ')] = str('US/Pacific')

        try:
            value = self.tool.get_commits()
        finally:
            os.environ[str('TZ')] = old_tz

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

        self.assertEqual(value[1].id,
                         'f814b6e226d2ba6d26d02ca8edbff91f57ab2786')
        self.assertEqual(value[1].message, 'first')
        self.assertEqual(value[1].author_name,
                         'Michael Rowe <mike.rowe@nab.com.au>')
        self.assertEqual(value[1].date, '2007-08-07T17:11:57')
        self.assertEqual(value[1].parent,
                         '0000000000000000000000000000000000000000')

        self.assertRaisesRegexp(SCMError, 'Cannot load commits: ',
                                lambda: self.tool.get_commits(branch='x'))

        rev = 'f814b6e226d2ba6d26d02ca8edbff91f57ab2786'
        value = self.tool.get_commits(start=rev)
        self.assertTrue(isinstance(value, list))
        self.assertEqual(len(value), 1)

    def test_get_file(self):
        """Testing HgTool.get_file"""
        tool = self.tool

        value = tool.get_file('doc/readme', Revision('661e5dd3c493'))
        self.assertIsInstance(value, bytes)
        self.assertEqual(value, b'Hello\n\ngoodbye\n')

        with self.assertRaises(FileNotFoundError):
            tool.get_file('')

        with self.assertRaises(FileNotFoundError):
            tool.get_file('hello', PRE_CREATION)

    def test_file_exists(self):
        """Testing HgTool.file_exists"""
        rev = Revision('661e5dd3c493')

        self.assertTrue(self.tool.file_exists('doc/readme', rev))
        self.assertFalse(self.tool.file_exists('doc/readme2', rev))

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
                          path='https://www.mercurial-scm.org/repo/hg',
                          tool=Tool.objects.get(name='Mercurial'))
        tool = repo.get_scmtool()

        self.assertTrue(tool.file_exists('mercurial/hgweb/common.py',
                                         Revision('f0735f2ce542')))
        self.assertFalse(tool.file_exists('mercurial/hgweb/common.py',
                                          Revision('abcdef123456')))


class HgWebClientTests(SpyAgency, TestCase):
    """Unit tests for reviewboard.scmtools.hg.HgWebClient."""

    def setUp(self):
        super(HgWebClientTests, self).setUp()

        self.hgweb_client = HgWebClient(path='http://hg.example.com/',
                                        username='test-user',
                                        password='test-password')

    def test_cat_file_with_raw_file(self):
        """Testing HgWebClient.cat_file with URL using raw-file"""
        def _get_file_http(client, url, path, revision, *args, **kwargs):
            if url.startswith('http://hg.example.com/raw-file/'):
                return b'result payload'

            raise FileNotFoundError(path=path,
                                    revision=revision)

        spy = self.spy_on(self.hgweb_client.get_file_http,
                          call_fake=_get_file_http)

        rsp = self.hgweb_client.cat_file(path='foo/bar.txt',
                                         rev=HEAD)
        self.assertIsInstance(rsp, bytes)
        self.assertEqual(rsp, b'result payload')

        spy = self.hgweb_client.get_file_http.spy
        self.assertEqual(len(spy.calls), 1)
        self.assertTrue(spy.last_called_with(
            url='http://hg.example.com/raw-file/tip/foo/bar.txt',
            path='foo/bar.txt',
            revision='tip'))

    def test_cat_file_with_raw(self):
        """Testing HgWebClient.cat_file with URL using raw"""
        def _get_file_http(client, url, path, revision, *args, **kwargs):
            if url.startswith('http://hg.example.com/raw/'):
                return b'result payload'

            raise FileNotFoundError(path=path,
                                    revision=revision)

        spy = self.spy_on(self.hgweb_client.get_file_http,
                          call_fake=_get_file_http)

        rsp = self.hgweb_client.cat_file(path='foo/bar.txt',
                                         rev=HEAD)
        self.assertIsInstance(rsp, bytes)
        self.assertEqual(rsp, b'result payload')

        spy = self.hgweb_client.get_file_http.spy
        self.assertEqual(len(spy.calls), 2)
        self.assertTrue(spy.last_called_with(
            url='http://hg.example.com/raw/tip/foo/bar.txt',
            path='foo/bar.txt',
            revision='tip'))

    def test_cat_file_with_hg_history(self):
        """Testing HgWebClient.cat_file with URL using hg-history"""
        def _get_file_http(client, url, path, revision, *args, **kwargs):
            if url.startswith('http://hg.example.com/hg-history/'):
                return b'result payload'

            raise FileNotFoundError(path=path,
                                    revision=revision)

        self.spy_on(self.hgweb_client.get_file_http,
                    call_fake=_get_file_http)

        rsp = self.hgweb_client.cat_file(path='foo/bar.txt',
                                         rev=HEAD)
        self.assertIsInstance(rsp, bytes)
        self.assertEqual(rsp, b'result payload')

        spy = self.hgweb_client.get_file_http.spy
        self.assertEqual(len(spy.calls), 3)
        self.assertTrue(spy.last_called_with(
            url='http://hg.example.com/hg-history/tip/foo/bar.txt',
            path='foo/bar.txt',
            revision='tip'))

    def test_cat_file_with_base_commit_id(self):
        """Testing HgWebClient.cat_file with base_commit_id"""
        def _get_file_http(client, url, path, revision, *args, **kwargs):
            return b'result payload'

        spy = self.spy_on(self.hgweb_client.get_file_http,
                          call_fake=_get_file_http)

        rsp = self.hgweb_client.cat_file(
            path='foo/bar.txt',
            base_commit_id='1ca5879492b8fd606df1964ea3c1e2f4520f076f')
        self.assertIsInstance(rsp, bytes)
        self.assertEqual(rsp, b'result payload')

        self.assertEqual(len(spy.calls), 1)
        self.assertTrue(spy.last_called_with(
            url='http://hg.example.com/raw-file/'
                '1ca5879492b8fd606df1964ea3c1e2f4520f076f/foo/bar.txt',
            path='foo/bar.txt',
            revision='1ca5879492b8fd606df1964ea3c1e2f4520f076f'))

    def test_cat_file_with_not_found(self):
        """Testing HgWebClient.cat_file with file not found"""
        def _get_file_http(client, url, path, revision, *args, **kwargs):
            raise FileNotFoundError(path=path,
                                    revision=revision)

        spy = self.spy_on(self.hgweb_client.get_file_http,
                          call_fake=_get_file_http)

        with self.assertRaises(FileNotFoundError):
            self.hgweb_client.cat_file(path='foo/bar.txt')

        self.assertEqual(len(spy.calls), 3)

    def test_get_branches(self):
        """Testing HgWebClient.get_branches"""
        def _get_file_http(client, url, path, revision, mime_type, *args,
                           **kwargs):
            self.assertEqual(url, 'http://hg.example.com/json-branches')
            self.assertEqual(mime_type, 'application/json')
            self.assertEqual(path, '')
            self.assertEqual(revision, '')

            return self._dump_json({
                'branches': [
                    {
                        'branch': 'default',
                        'node': '1ca5879492b8fd606df1964ea3c1e2f4520f076f',
                        'status': 'open',
                    },
                    {
                        'branch': 'closed-branch',
                        'node': 'b9af6489f6f2004ad11b82c6057f7007e3c35372',
                        'status': 'closed',
                    },
                    {
                        'branch': 'release-branch',
                        'node': '8210c0d945ef893d40a903c9dc14cd072eee5bb7',
                        'status': 'open',
                    },
                ],
            })

        self.spy_on(self.hgweb_client.get_file_http,
                    call_fake=_get_file_http)

        branches = self.hgweb_client.get_branches()
        self.assertIsInstance(branches, list)
        self.assertEqual(len(branches), 2)

        branch = branches[0]
        self.assertEqual(branch.id, 'default')
        self.assertEqual(branch.commit,
                         '1ca5879492b8fd606df1964ea3c1e2f4520f076f')
        self.assertTrue(branch.default)

        branch = branches[1]
        self.assertEqual(branch.id, 'release-branch')
        self.assertEqual(branch.commit,
                         '8210c0d945ef893d40a903c9dc14cd072eee5bb7')
        self.assertFalse(branch.default)

    def test_get_branches_with_error(self):
        """Testing HgWebClient.get_branches with error fetching result"""
        def _get_file_http(client, url, path, revision, *args, **kwargs):
            raise FileNotFoundError(path, revision)

        self.spy_on(self.hgweb_client.get_file_http,
                    call_fake=_get_file_http)

        branches = self.hgweb_client.get_branches()
        self.assertEqual(branches, [])

    def test_get_change(self):
        """Testing HgWebClient.get_change"""
        def _get_file_http(client, url, path, revision, mime_type, *args,
                           **kwargs):
            if url.startswith('http://hg.example.com/raw-rev/'):
                self.assertEqual(
                    url,
                    'http://hg.example.com/raw-rev/'
                    '1ca5879492b8fd606df1964ea3c1e2f4520f076f')
                self.assertEqual(path, '')
                self.assertEqual(revision, '')
                self.assertIsNone(mime_type)

                return b'diff payload'
            elif url.startswith('http://hg.example.com/json-rev/'):
                self.assertEqual(
                    url,
                    'http://hg.example.com/json-rev/'
                    '1ca5879492b8fd606df1964ea3c1e2f4520f076f')
                self.assertEqual(mime_type, 'application/json')
                self.assertEqual(path, '')
                self.assertEqual(revision, '')

                return self._dump_json({
                    'node': '1ca5879492b8fd606df1964ea3c1e2f4520f076f',
                    'desc': 'This is the change description',
                    'user': 'Test User',
                    'date': [1583149219, 28800],
                    'parents': [
                        'b9af6489f6f2004ad11b82c6057f7007e3c35372'
                    ],
                })
            else:
                raise FileNotFoundError(path=path,
                                        revision=revision)

        self.spy_on(self.hgweb_client.get_file_http,
                    call_fake=_get_file_http)

        commit = self.hgweb_client.get_change(
            '1ca5879492b8fd606df1964ea3c1e2f4520f076f')
        self.assertEqual(commit.id, '1ca5879492b8fd606df1964ea3c1e2f4520f076f')
        self.assertEqual(commit.message, 'This is the change description')
        self.assertEqual(commit.author_name, 'Test User')
        self.assertEqual(commit.date, '2020-03-02T03:40:19')
        self.assertEqual(commit.parent,
                         'b9af6489f6f2004ad11b82c6057f7007e3c35372')

    def test_get_commits(self):
        """Testing HgWebClient.get_commits"""
        def _get_file_http(client, url, path, revision, mime_type, *args,
                           **kwargs):
            self.assertEqual(
                url,
                'http://hg.example.com/json-log/?rev=branch(.)')
            self.assertEqual(mime_type, 'application/json')
            self.assertEqual(path, '')
            self.assertEqual(revision, '')

            return self._dump_json({
                'entries': [
                    {
                        'node': '1ca5879492b8fd606df1964ea3c1e2f4520f076f',
                        'desc': 'This is the change description',
                        'user': 'Test User',
                        'date': [1583149219, 28800],
                        'parents': [
                            'b9af6489f6f2004ad11b82c6057f7007e3c35372'
                        ],
                    },
                    {
                        'node': 'b9af6489f6f2004ad11b82c6057f7007e3c35372',
                        'desc': 'This is another description',
                        'user': 'Another User',
                        'date': [1581897120, 28800],
                        'parents': [
                            '8210c0d945ef893d40a903c9dc14cd072eee5bb7',
                        ],
                    },
                ],
            })

        self.spy_on(self.hgweb_client.get_file_http,
                    call_fake=_get_file_http)

        commits = self.hgweb_client.get_commits()
        self.assertEqual(len(commits), 2)

        commit = commits[0]
        self.assertEqual(commit.id, '1ca5879492b8fd606df1964ea3c1e2f4520f076f')
        self.assertEqual(commit.message, 'This is the change description')
        self.assertEqual(commit.author_name, 'Test User')
        self.assertEqual(commit.date, '2020-03-02T03:40:19')
        self.assertEqual(commit.parent,
                         'b9af6489f6f2004ad11b82c6057f7007e3c35372')

        commit = commits[1]
        self.assertEqual(commit.id, 'b9af6489f6f2004ad11b82c6057f7007e3c35372')
        self.assertEqual(commit.message, 'This is another description')
        self.assertEqual(commit.author_name, 'Another User')
        self.assertEqual(commit.date, '2020-02-16T15:52:00')
        self.assertEqual(commit.parent,
                         '8210c0d945ef893d40a903c9dc14cd072eee5bb7')

    def test_get_commits_with_branch(self):
        """Testing HgWebClient.get_commits with branch"""
        def _get_file_http(client, url, path, revision, mime_type, *args,
                           **kwargs):
            self.assertEqual(
                url,
                'http://hg.example.com/json-log/?rev=branch(my-branch)')
            self.assertEqual(mime_type, 'application/json')
            self.assertEqual(path, '')
            self.assertEqual(revision, '')

            return self._dump_json({
                'entries': [
                    {
                        'node': '1ca5879492b8fd606df1964ea3c1e2f4520f076f',
                        'desc': 'This is the change description',
                        'user': 'Test User',
                        'date': [1583149219, 28800],
                        'parents': [
                            'b9af6489f6f2004ad11b82c6057f7007e3c35372'
                        ],
                    },
                    {
                        'node': 'b9af6489f6f2004ad11b82c6057f7007e3c35372',
                        'desc': 'This is another description',
                        'user': 'Another User',
                        'date': [1581897120, 28800],
                        'parents': [
                            '8210c0d945ef893d40a903c9dc14cd072eee5bb7',
                        ],
                    },
                ],
            })

        self.spy_on(self.hgweb_client.get_file_http,
                    call_fake=_get_file_http)

        commits = self.hgweb_client.get_commits(branch='my-branch')
        self.assertEqual(len(commits), 2)

        commit = commits[0]
        self.assertEqual(commit.id, '1ca5879492b8fd606df1964ea3c1e2f4520f076f')
        self.assertEqual(commit.message, 'This is the change description')
        self.assertEqual(commit.author_name, 'Test User')
        self.assertEqual(commit.date, '2020-03-02T03:40:19')
        self.assertEqual(commit.parent,
                         'b9af6489f6f2004ad11b82c6057f7007e3c35372')

        commit = commits[1]
        self.assertEqual(commit.id, 'b9af6489f6f2004ad11b82c6057f7007e3c35372')
        self.assertEqual(commit.message, 'This is another description')
        self.assertEqual(commit.author_name, 'Another User')
        self.assertEqual(commit.date, '2020-02-16T15:52:00')
        self.assertEqual(commit.parent,
                         '8210c0d945ef893d40a903c9dc14cd072eee5bb7')

    def test_get_commits_with_start(self):
        """Testing HgWebClient.get_commits with start"""
        def _get_file_http(client, url, path, revision, mime_type, *args,
                           **kwargs):
            self.assertEqual(
                url,
                'http://hg.example.com/json-log/'
                '?rev=ancestors(1ca5879492b8fd606df1964ea3c1e2f4520f076f)'
                '+and+branch(.)')
            self.assertEqual(mime_type, 'application/json')
            self.assertEqual(path, '')
            self.assertEqual(revision, '')

            return self._dump_json({
                'entries': [
                    {
                        'node': '1ca5879492b8fd606df1964ea3c1e2f4520f076f',
                        'desc': 'This is the change description',
                        'user': 'Test User',
                        'date': [1583149219, 28800],
                        'parents': [
                            'b9af6489f6f2004ad11b82c6057f7007e3c35372'
                        ],
                    },
                    {
                        'node': 'b9af6489f6f2004ad11b82c6057f7007e3c35372',
                        'desc': 'This is another description',
                        'user': 'Another User',
                        'date': [1581897120, 28800],
                        'parents': [
                            '8210c0d945ef893d40a903c9dc14cd072eee5bb7',
                        ],
                    },
                ],
            })

        self.spy_on(self.hgweb_client.get_file_http,
                    call_fake=_get_file_http)

        commits = self.hgweb_client.get_commits(
            start='1ca5879492b8fd606df1964ea3c1e2f4520f076f')
        self.assertEqual(len(commits), 2)

        commit = commits[0]
        self.assertEqual(commit.id, '1ca5879492b8fd606df1964ea3c1e2f4520f076f')
        self.assertEqual(commit.message, 'This is the change description')
        self.assertEqual(commit.author_name, 'Test User')
        self.assertEqual(commit.date, '2020-03-02T03:40:19')
        self.assertEqual(commit.parent,
                         'b9af6489f6f2004ad11b82c6057f7007e3c35372')

        commit = commits[1]
        self.assertEqual(commit.id, 'b9af6489f6f2004ad11b82c6057f7007e3c35372')
        self.assertEqual(commit.message, 'This is another description')
        self.assertEqual(commit.author_name, 'Another User')
        self.assertEqual(commit.date, '2020-02-16T15:52:00')
        self.assertEqual(commit.parent,
                         '8210c0d945ef893d40a903c9dc14cd072eee5bb7')

    def test_get_commits_with_not_implemented(self):
        """Testing HgWebClient.get_commits with server response of "not yet
        implemented"
        """
        def _get_file_http(client, url, path, revision, mime_type, *args,
                           **kwargs):
            self.assertEqual(url,
                             'http://hg.example.com/json-log/?rev=branch(.)')
            self.assertEqual(mime_type, 'application/json')
            self.assertEqual(path, '')
            self.assertEqual(revision, '')

            return b'not yet implemented'

        self.spy_on(self.hgweb_client.get_file_http,
                    call_fake=_get_file_http)

        commits = self.hgweb_client.get_commits()
        self.assertEqual(commits, [])

    def _dump_json(self, obj):
        """Dump an object to a JSON byte string.

        Args:
            obj (object):
                The object to dump.

        Returns:
            bytes;
            The JSON-serialized byte string.
        """
        return json.dumps(obj).encode('utf-8')


class HgAuthFormTests(TestCase):
    """Unit tests for HgTool's authentication form."""

    def test_fields(self):
        """Testing HgTool authentication form fields"""
        form = HgTool.create_auth_form()

        self.assertEqual(list(form.fields), ['username', 'password'])
        self.assertEqual(form['username'].help_text, '')
        self.assertEqual(form['username'].label, 'Username')
        self.assertEqual(form['password'].help_text, '')
        self.assertEqual(form['password'].label, 'Password')

    @add_fixtures(['test_scmtools'])
    def test_load(self):
        """Tetting HgTool authentication form load"""
        repository = self.create_repository(
            tool_name='Mercurial',
            username='test-user',
            password='test-pass')

        form = HgTool.create_auth_form(repository=repository)
        form.load()

        self.assertEqual(form['username'].value(), 'test-user')
        self.assertEqual(form['password'].value(), 'test-pass')

    @add_fixtures(['test_scmtools'])
    def test_save(self):
        """Tetting HgTool authentication form save"""
        repository = self.create_repository(tool_name='Mercurial')

        form = HgTool.create_auth_form(
            repository=repository,
            data={
                'username': 'test-user',
                'password': 'test-pass',
            })
        self.assertTrue(form.is_valid())
        form.save()

        self.assertEqual(repository.username, 'test-user')
        self.assertEqual(repository.password, 'test-pass')


class HgRepositoryFormTests(TestCase):
    """Unit tests for HgTool's repository form."""

    def test_fields(self):
        """Testing HgTool repository form fields"""
        form = HgTool.create_repository_form()

        self.assertEqual(list(form.fields), ['path', 'mirror_path'])
        self.assertEqual(form['path'].help_text,
                         'The path to the repository. This will generally be '
                         'the URL you would use to check out the repository.')
        self.assertEqual(form['path'].label, 'Path')
        self.assertEqual(form['mirror_path'].help_text, '')
        self.assertEqual(form['mirror_path'].label, 'Mirror Path')

    @add_fixtures(['test_scmtools'])
    def test_load(self):
        """Tetting HgTool repository form load"""
        repository = self.create_repository(
            tool_name='Mercurial',
            path='https://hg.example.com/repo',
            mirror_path='https://hg.mirror.example.com/repo')

        form = HgTool.create_repository_form(repository=repository)
        form.load()

        self.assertEqual(form['path'].value(), 'https://hg.example.com/repo')
        self.assertEqual(form['mirror_path'].value(),
                         'https://hg.mirror.example.com/repo')

    @add_fixtures(['test_scmtools'])
    def test_save(self):
        """Tetting HgTool repository form save"""
        repository = self.create_repository(tool_name='Mercurial')

        form = HgTool.create_repository_form(
            repository=repository,
            data={
                'path': 'https://hg.example.com/repo',
                'mirror_path': 'https://hg.mirror.example.com/repo',
            })
        self.assertTrue(form.is_valid())
        form.save()

        self.assertEqual(repository.path, 'https://hg.example.com/repo')
        self.assertEqual(repository.mirror_path,
                         'https://hg.mirror.example.com/repo')
