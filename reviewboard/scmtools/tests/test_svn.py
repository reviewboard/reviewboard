# coding=utf-8
from __future__ import unicode_literals

import os
from hashlib import md5

import nose
from django.conf import settings
from django.utils import six
from django.utils.six.moves import range
from djblets.testing.decorators import add_fixtures
from kgb import SpyAgency

from reviewboard.diffviewer.diffutils import patch
from reviewboard.scmtools.core import (Branch, Commit, Revision, HEAD,
                                       PRE_CREATION)
from reviewboard.scmtools.errors import SCMError, FileNotFoundError
from reviewboard.scmtools.models import Repository, Tool
from reviewboard.scmtools.svn import SVNTool, recompute_svn_backend
from reviewboard.scmtools.svn.utils import (collapse_svn_keywords,
                                            has_expanded_svn_keywords)
from reviewboard.scmtools.tests.testcases import SCMTestCase
from reviewboard.testing.testcase import TestCase


class _CommonSVNTestCase(SpyAgency, SCMTestCase):
    """Common unit tests for Subversion.

    This is meant to be subclassed for each backend that wants to run
    the common set of tests.
    """

    backend = None
    backend_name = None
    fixtures = ['test_scmtools']

    def setUp(self):
        super(_CommonSVNTestCase, self).setUp()

        self._old_backend_setting = settings.SVNTOOL_BACKENDS
        settings.SVNTOOL_BACKENDS = [self.backend]
        recompute_svn_backend()

        self.svn_repo_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__),
                         '..', 'testdata', 'svn_repo'))
        self.svn_ssh_path = ('svn+ssh://localhost%s'
                             % self.svn_repo_path.replace('\\', '/'))
        self.repository = Repository.objects.create(
            name='Subversion SVN',
            path='file://%s' % self.svn_repo_path,
            tool=Tool.objects.get(name='Subversion'))

        try:
            self.tool = self.repository.get_scmtool()
        except ImportError:
            raise nose.SkipTest('The %s backend could not be used. A '
                                'dependency may be missing.'
                                % self.backend)

        assert self.tool.client.__class__.__module__ == self.backend

    def tearDown(self):
        super(_CommonSVNTestCase, self).tearDown()

        settings.SVNTOOL_BACKENDS = self._old_backend_setting
        recompute_svn_backend()

    def shortDescription(self):
        desc = super(_CommonSVNTestCase, self).shortDescription()
        desc = desc.replace('<backend>', self.backend_name)

        return desc

    def test_get_repository_info(self):
        """Testing SVN (<backend>) get_repository_info"""
        info = self.tool.get_repository_info()

        self.assertIn('uuid', info)
        self.assertIsInstance(info['uuid'], six.text_type)
        self.assertEqual(info['uuid'], '41215d38-f5a5-421f-ba17-e0be11e6c705')

        self.assertIn('root_url', info)
        self.assertIsInstance(info['root_url'], six.text_type)
        self.assertEqual(info['root_url'], self.repository.path)

        self.assertIn('url', info)
        self.assertIsInstance(info['url'], six.text_type)
        self.assertEqual(info['url'], self.repository.path)

    def test_ssh(self):
        """Testing SVN (<backend>) with a SSH-backed Subversion repository"""
        self._test_ssh(self.svn_ssh_path, 'trunk/doc/misc-docs/Makefile')

    def test_ssh_with_site(self):
        """Testing SVN (<backend>) with a SSH-backed Subversion repository
        with a LocalSite
        """
        self._test_ssh_with_site(self.svn_ssh_path,
                                 'trunk/doc/misc-docs/Makefile')

    def test_get_file(self):
        """Testing SVN (<backend>) get_file"""
        tool = self.tool

        expected = (b'include ../tools/Makefile.base-vars\n'
                    b'NAME = misc-docs\n'
                    b'OUTNAME = svn-misc-docs\n'
                    b'INSTALL_DIR = $(DESTDIR)/usr/share/doc/subversion\n'
                    b'include ../tools/Makefile.base-rules\n')

        # There are 3 versions of this test in order to get 100% coverage of
        # the svn module.
        rev = Revision('2')
        filename = 'trunk/doc/misc-docs/Makefile'

        value = tool.get_file(filename, rev)
        self.assertIsInstance(value, bytes)
        self.assertEqual(value, expected)

        value = tool.get_file('/%s' % filename, rev)
        self.assertIsInstance(value, bytes)
        self.assertEqual(value, expected)

        value = tool.get_file('%s/%s' % (self.repository.path, filename), rev)
        self.assertIsInstance(value, bytes)
        self.assertEqual(value, expected)

        with self.assertRaises(FileNotFoundError):
            tool.get_file('')

    def test_file_exists(self):
        """Testing SVN (<backend>) file_exists"""
        tool = self.tool

        self.assertTrue(tool.file_exists('trunk/doc/misc-docs/Makefile'))
        self.assertFalse(tool.file_exists('trunk/doc/misc-docs/Makefile2'))

        with self.assertRaises(FileNotFoundError):
            tool.get_file('hello', PRE_CREATION)

    def test_get_file_with_special_url_chars(self):
        """Testing SVN (<backend>) get_file with filename containing
        characters that are special in URLs and repository path as a URI
        """
        value = self.tool.get_file('trunk/crazy& ?#.txt', Revision('12'))
        self.assertTrue(isinstance(value, bytes))
        self.assertEqual(value, b'Lots of characters in this one.\n')

    def test_file_exists_with_special_url_chars(self):
        """Testing SVN (<backend>) file_exists with filename containing
        characters that are special in URLs
        """
        self.assertTrue(self.tool.file_exists('trunk/crazy& ?#.txt',
                                              Revision('12')))

        # These should not crash. We'll be testing both file:// URLs
        # (which fail for anything lower than ASCII code 32) and for actual
        # URLs (which support all characters).
        self.assertFalse(self.tool.file_exists('trunk/%s.txt' % ''.join(
            chr(c)
            for c in range(32, 128)
        )))

        self.tool.client.repopath = 'svn+ssh://localhost:0/svn'

        try:
            self.assertFalse(self.tool.file_exists('trunk/%s.txt' % ''.join(
                chr(c)
                for c in range(128)
            )))
        except SCMError:
            # Couldn't connect. Valid result.
            pass

    def test_normalize_path_with_special_chars_and_remote_url(self):
        """Testing SVN (<backend>) normalize_path with special characters
        and remote URL
        """
        client = self.tool.client

        client.repopath = 'svn+ssh://example.com/svn'
        path = client.normalize_path(''.join(
            chr(c)
            for c in range(128)
        ))

        # This URL was generated based on modified code that directly used
        # Subversion's lookup take explicitly, ensuring we're getting the
        # results we want from urllib.quote() and our list of safe characters.
        self.assertEqual(
            path,
            "svn+ssh://example.com/svn/%00%01%02%03%04%05%06%07%08%09%0A"
            "%0B%0C%0D%0E%0F%10%11%12%13%14%15%16%17%18%19%1A%1B%1C%1D%1E"
            "%1F%20!%22%23$%25&'()*+,-./0123456789:%3B%3C=%3E%3F@ABCDEFGH"
            "IJKLMNOPQRSTUVWXYZ%5B%5C%5D%5E_%60abcdefghijklmnopqrstuvwxyz"
            "%7B%7C%7D~%7F")

    def test_normalize_path_with_special_chars_and_file_url(self):
        """Testing SVN (<backend>) normalize_path with special characters
        and local file:// URL
        """
        client = self.tool.client

        client.repopath = 'file:///tmp/svn'
        path = client.normalize_path(''.join(
            chr(c)
            for c in range(32, 128)
        ))

        # This URL was generated based on modified code that directly used
        # Subversion's lookup take explicitly, ensuring we're getting the
        # results we want from urllib.quote() and our list of safe characters.
        self.assertEqual(
            path,
            "file:///tmp/svn/%20!%22%23$%25&'()*+,-./0123456789:%3B%3C=%3E"
            "%3F@ABCDEFGHIJKLMNOPQRSTUVWXYZ%5B%5C%5D%5E_%60abcdefghijklmno"
            "pqrstuvwxyz%7B%7C%7D~%7F")

        # This should provide a reasonable error for each code in 0..32.
        for i in range(32):
            c = chr(i)

            message = (
                'Invalid character code %s found in path %r.'
                % (i, c)
            )

            with self.assertRaisesMessage(SCMError, message):
                client.normalize_path(c)

    def test_normalize_path_with_absolute_repo_path(self):
        """Testing SVN (<backend>) normalize_path with absolute path"""
        client = self.tool.client

        client.repopath = '/var/lib/svn'
        path = '/var/lib/svn/foo/bar'
        self.assertEqual(client.normalize_path(path), path)

        client.repopath = 'svn+ssh://example.com/svn/'
        path = 'svn+ssh://example.com/svn/foo/bar'
        self.assertEqual(client.normalize_path(path), path)

    def test_normalize_path_with_rel_path(self):
        """Testing SVN (<backend>) normalize_path with relative path"""
        client = self.tool.client
        client.repopath = 'svn+ssh://example.com/svn'

        self.assertEqual(client.normalize_path('foo/bar'),
                         'svn+ssh://example.com/svn/foo/bar')
        self.assertEqual(client.normalize_path('/foo/bar'),
                         'svn+ssh://example.com/svn/foo/bar')
        self.assertEqual(client.normalize_path('//foo/bar'),
                         'svn+ssh://example.com/svn/foo/bar')
        self.assertEqual(client.normalize_path('foo&/b ar?/#file#.txt'),
                         'svn+ssh://example.com/svn/foo&/b%20ar%3F/'
                         '%23file%23.txt')

    def test_revision_parsing(self):
        """Testing SVN (<backend>) revision number parsing"""
        self.assertEqual(
            self.tool.parse_diff_revision(filename=b'',
                                          revision=b'(working copy)'),
            (b'', HEAD))
        self.assertEqual(
            self.tool.parse_diff_revision(filename=b'',
                                          revision=b'   (revision 0)'),
            (b'', PRE_CREATION))

        self.assertEqual(
            self.tool.parse_diff_revision(filename=b'',
                                          revision=b'(revision 1)'),
            (b'', b'1'))
        self.assertEqual(
            self.tool.parse_diff_revision(filename=b'',
                                          revision=b'(revision 23)'),
            (b'', b'23'))

        # Fix for bug 2176
        self.assertEqual(
            self.tool.parse_diff_revision(filename=b'',
                                          revision=b'\t(revision 4)'),
            (b'', b'4'))

        self.assertEqual(
            self.tool.parse_diff_revision(
                filename=b'',
                revision=b'2007-06-06 15:32:23 UTC (rev 10958)'),
            (b'', b'10958'))

        # Fix for bug 2632
        self.assertEqual(
            self.tool.parse_diff_revision(filename=b'',
                                          revision=b'(revision )'),
            (b'', PRE_CREATION))

        with self.assertRaises(SCMError):
            self.tool.parse_diff_revision(filename=b'',
                                          revision=b'hello')

        # Verify that 'svn diff' localized revision strings parse correctly.
        self.assertEqual(
            self.tool.parse_diff_revision(
                filename=b'',
                revision='(revisión: 5)'.encode('utf-8')),
            (b'', b'5'))
        self.assertEqual(
            self.tool.parse_diff_revision(
                filename=b'',
                revision='(リビジョン 6)'.encode('utf-8')),
            (b'', b'6'))
        self.assertEqual(
            self.tool.parse_diff_revision(
                filename=b'',
                revision='(版本 7)'.encode('utf-8')),
            (b'', b'7'))

    def test_revision_parsing_with_nonexistent(self):
        """Testing SVN (<backend>) revision parsing with "(nonexistent)"
        revision indicator
        """
        # English
        self.assertEqual(
            self.tool.parse_diff_revision(filename=b'',
                                          revision=b'(nonexistent)'),
            (b'', PRE_CREATION))

        # German
        self.assertEqual(
            self.tool.parse_diff_revision(filename=b'',
                                          revision=b'(nicht existent)'),
            (b'', PRE_CREATION))

        # Simplified Chinese
        self.assertEqual(
            self.tool.parse_diff_revision(
                filename=b'',
                revision='(不存在的)'.encode('utf-8')),
            (b'', PRE_CREATION))

    def test_revision_parsing_with_nonexistent_and_branches(self):
        """Testing SVN (<backend>) revision parsing with relocation
        information and nonexisitent revision specifier.
        """
        self.assertEqual(
            self.tool.parse_diff_revision(
                filename=b'',
                revision=b'(.../trunk) (nonexistent)'),
            (b'trunk/', PRE_CREATION))

        self.assertEqual(
            self.tool.parse_diff_revision(
                filename=b'',
                revision=b'(.../branches/branch-1.0)     (nicht existent)'),
            (b'branches/branch-1.0/', PRE_CREATION))

        self.assertEqual(
            self.tool.parse_diff_revision(
                filename=b'',
                revision='        (.../trunk)     (不存在的)'.encode('utf-8')),
            (b'trunk/', PRE_CREATION))

    def test_interface(self):
        """Testing SVN (<backend>) with basic SVNTool API"""
        self.assertFalse(self.tool.diffs_use_absolute_paths)

        self.assertRaises(NotImplementedError,
                          lambda: self.tool.get_changeset(1))

    def test_binary_diff(self):
        """Testing SVN (<backend>) parsing SVN diff with binary file"""
        diff = (b'Index: binfile\n'
                b'============================================================'
                b'=======\n'
                b'Cannot display: file marked as a binary type.\n'
                b'svn:mime-type = application/octet-stream\n')

        file = self.tool.get_parser(diff).parse()[0]
        self.assertEqual(file.orig_filename, b'binfile')
        self.assertEqual(file.binary, True)

    def test_binary_diff_with_property_change(self):
        """Testing SVN (<backend>) parsing SVN diff with binary file with
        property change
        """
        diff = (
            b'Index: binfile\n'
            b'============================================================'
            b'=======\n'
            b'Cannot display: file marked as a binary type.\n'
            b'svn:mime-type = application/octet-stream\n'
            b'\n'
            b'Property changes on: binfile\n'
            b'____________________________________________________________'
            b'_______\n'
            b'Added: svn:mime-type\n'
            b'## -0,0 +1 ##\n'
            b'+application/octet-stream\n'
            b'\\ No newline at end of property\n'
        )

        file = self.tool.get_parser(diff).parse()[0]
        self.assertEqual(file.orig_filename, b'binfile')
        self.assertTrue(file.binary)

    def test_keyword_diff(self):
        """Testing SVN (<backend>) parsing diff with keywords"""
        # 'svn cat' will expand special variables in svn:keywords,
        # but 'svn diff' doesn't expand anything.  This causes the
        # patch to fail if those variables appear in the patch context.
        diff = (b'Index: Makefile\n'
                b'==========================================================='
                b'========\n'
                b'--- Makefile    (revision 4)\n'
                b'+++ Makefile    (working copy)\n'
                b'@@ -1,6 +1,7 @@\n'
                b' # $Id$\n'
                b' # $Rev$\n'
                b' # $Revision::     $\n'
                b'+# foo\n'
                b' include ../tools/Makefile.base-vars\n'
                b' NAME = misc-docs\n'
                b' OUTNAME = svn-misc-docs\n')

        filename = 'trunk/doc/misc-docs/Makefile'
        rev = Revision('4')
        file = self.tool.get_file(filename, rev)
        patch(diff, file, filename)

    def test_unterminated_keyword_diff(self):
        """Testing SVN (<backend>) parsing diff with unterminated keywords"""
        diff = (b'Index: Makefile\n'
                b'==========================================================='
                b'========\n'
                b'--- Makefile    (revision 4)\n'
                b'+++ Makefile    (working copy)\n'
                b'@@ -1,6 +1,7 @@\n'
                b' # $Id$\n'
                b' # $Id:\n'
                b' # $Rev$\n'
                b' # $Revision::     $\n'
                b'+# foo\n'
                b' include ../tools/Makefile.base-vars\n'
                b' NAME = misc-docs\n'
                b' OUTNAME = svn-misc-docs\n')

        filename = 'trunk/doc/misc-docs/Makefile'
        rev = Revision('5')
        file = self.tool.get_file(filename, rev)
        patch(diff, file, filename)

    def test_svn16_property_diff(self):
        """Testing SVN (<backend>) parsing SVN 1.6 diff with property changes
        """
        prop_diff = (
            b'Index:\n'
            b'======================================================'
            b'=============\n'
            b'--- (revision 123)\n'
            b'+++ (working copy)\n'
            b'Property changes on: .\n'
            b'______________________________________________________'
            b'_____________\n'
            b'Modified: reviewboard:url\n'
            b'## -1 +1 ##\n'
            b'-http://reviews.reviewboard.org\n'
            b'+http://reviews.reviewboard.org\n')
        bin_diff = (
            b'Index: binfile\n'
            b'======================================================='
            b'============\nCannot display: file marked as a '
            b'binary type.\nsvn:mime-type = application/octet-stream\n')
        diff = prop_diff + bin_diff

        files = self.tool.get_parser(diff).parse()
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0].orig_filename, b'binfile')
        self.assertTrue(files[0].binary)
        self.assertEqual(files[0].insert_count, 0)
        self.assertEqual(files[0].delete_count, 0)

    def test_svn17_property_diff(self):
        """Testing SVN (<backend>) parsing SVN 1.7+ diff with property changes
        """
        prop_diff = (
            b'Index .:\n'
            b'======================================================'
            b'=============\n'
            b'--- .  (revision 123)\n'
            b'+++ .  (working copy)\n'
            b'\n'
            b'Property changes on: .\n'
            b'______________________________________________________'
            b'_____________\n'
            b'Modified: reviewboard:url\n'
            b'## -0,0 +1,3 ##\n'
            b'-http://reviews.reviewboard.org\n'
            b'+http://reviews.reviewboard.org\n'
            b'Added: myprop\n'
            b'## -0,0 +1 ##\n'
            b'+Property test.\n')
        bin_diff = (
            b'Index: binfile\n'
            b'======================================================='
            b'============\nCannot display: file marked as a '
            b'binary type.\nsvn:mime-type = application/octet-stream\n')
        diff = prop_diff + bin_diff

        files = self.tool.get_parser(diff).parse()

        self.assertEqual(len(files), 1)
        self.assertEqual(files[0].orig_filename, b'binfile')
        self.assertTrue(files[0].binary)
        self.assertEqual(files[0].insert_count, 0)
        self.assertEqual(files[0].delete_count, 0)

    def test_unicode_diff(self):
        """Testing SVN (<backend>) parsing diff with unicode characters"""
        diff = ('Index: Filé\n'
                '==========================================================='
                '========\n'
                '--- Filé    (revision 4)\n'
                '+++ Filé    (working copy)\n'
                '@@ -1,6 +1,7 @@\n'
                '+# foó\n'
                ' include ../tools/Makefile.base-vars\n'
                ' NAME = misc-docs\n'
                ' OUTNAME = svn-misc-docs\n').encode('utf-8')

        files = self.tool.get_parser(diff).parse()
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0].orig_filename, 'Filé'.encode('utf-8'))
        self.assertFalse(files[0].binary)
        self.assertEqual(files[0].insert_count, 1)
        self.assertEqual(files[0].delete_count, 0)

    def test_diff_with_spaces_in_filenames(self):
        """Testing SVN (<backend>) parsing diff with spaces in filenames"""
        diff = (b'Index: File with spaces\n'
                b'==========================================================='
                b'========\n'
                b'--- File with spaces    (revision 4)\n'
                b'+++ File with spaces    (working copy)\n'
                b'@@ -1,6 +1,7 @@\n'
                b'+# foo\n'
                b' include ../tools/Makefile.base-vars\n'
                b' NAME = misc-docs\n'
                b' OUTNAME = svn-misc-docs\n')

        files = self.tool.get_parser(diff).parse()
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0].orig_filename, b'File with spaces')
        self.assertFalse(files[0].binary)
        self.assertEqual(files[0].insert_count, 1)
        self.assertEqual(files[0].delete_count, 0)

    def test_diff_with_added_empty_file(self):
        """Testing parsing SVN diff with added empty file"""
        diff = (b'Index: empty-file\t(added)\n'
                b'==========================================================='
                b'========\n'
                b'--- empty-file\t(revision 0)\n'
                b'+++ empty-file\t(revision 0)\n')

        files = self.tool.get_parser(diff).parse()
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0].orig_filename, b'empty-file')
        self.assertEqual(files[0].modified_filename, b'empty-file')
        self.assertEqual(files[0].orig_file_details, b'(revision 0)')
        self.assertEqual(files[0].modified_file_details, b'(revision 0)')
        self.assertFalse(files[0].binary)
        self.assertFalse(files[0].deleted)
        self.assertEqual(files[0].insert_count, 0)
        self.assertEqual(files[0].delete_count, 0)

    def test_diff_with_deleted_empty_file(self):
        """Testing parsing SVN diff with deleted empty file"""
        diff = (b'Index: empty-file\t(deleted)\n'
                b'==========================================================='
                b'========\n'
                b'--- empty-file\t(revision 4)\n'
                b'+++ empty-file\t(working copy)\n')

        files = self.tool.get_parser(diff).parse()
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0].orig_filename, b'empty-file')
        self.assertEqual(files[0].modified_filename, b'empty-file')
        self.assertEqual(files[0].orig_file_details, b'(revision 4)')
        self.assertEqual(files[0].modified_file_details, b'(working copy)')
        self.assertFalse(files[0].binary)
        self.assertTrue(files[0].deleted)
        self.assertEqual(files[0].insert_count, 0)
        self.assertEqual(files[0].delete_count, 0)

    def test_idea_diff(self):
        """Testing parsing SVN diff with multi-file diff generated by IDEA
        IDEs
        """
        diff1 = (
            b'Index: path/to/README\n'
            b'IDEA additional info:\n'
            b'Subsystem: org.reviewboard.org.test\n'
            b'<+>ISO-8859-1\n'
            b'=============================================================='
            b'=====\n'
            b'--- path/to/README\t(revision 4)\n'
            b'+++ path/to/README\t(revision )\n'
            b'@@ -1,6 +1,7 @@\n'
            b' #\n'
            b' #\n'
            b' #\n'
            b'+# test\n'
            b' #\n'
            b' #\n'
            b' #\n'
        )
        diff2 = (
            b'Index: path/to/README2\n'
            b'IDEA additional info:\n'
            b'Subsystem: org.reviewboard.org.test\n'
            b'<+>ISO-8859-1\n'
            b'=============================================================='
            b'=====\n'
            b'--- path/to/README2\t(revision 4)\n'
            b'+++ path/to/README2\t(revision )\n'
            b'@@ -1,6 +1,7 @@\n'
            b' #\n'
            b' #\n'
            b' #\n'
            b'+# test\n'
            b' #\n'
            b' #\n'
            b' #\n'
        )

        diff_files = self.tool.get_parser(diff1 + diff2).parse()
        self.assertEqual(len(diff_files), 2)

        diff_file = diff_files[1]
        self.assertEqual(diff_file.orig_filename, b'path/to/README2')
        self.assertEqual(diff_file.modified_filename, b'path/to/README2')
        self.assertEqual(diff_file.orig_file_details, b'(revision 4)')
        self.assertEqual(diff_file.modified_file_details, b'(revision )')
        self.assertFalse(diff_file.binary)
        self.assertFalse(diff_file.deleted)
        self.assertEqual(diff_file.insert_count, 1)
        self.assertEqual(diff_file.delete_count, 0)
        self.assertEqual(diff_file.data, diff2)

    def test_get_branches(self):
        """Testing SVN (<backend>) get_branches"""
        branches = self.tool.get_branches()

        self.assertEqual(len(branches), 3)
        self.assertEqual(branches[0], Branch(id='trunk', name='trunk',
                                             commit='12', default=True))
        self.assertEqual(branches[1], Branch(id='branches/branch1',
                                             name='branch1',
                                             commit='7', default=False))
        self.assertEqual(branches[2], Branch(id='top-level-branch',
                                             name='top-level-branch',
                                             commit='10', default=False))

    def test_get_commits(self):
        """Testing SVN (<backend>) get_commits"""
        commits = self.tool.get_commits(start='5')

        self.assertEqual(len(commits), 5)
        self.assertEqual(
            commits[0],
            Commit('chipx86',
                   '5',
                   '2010-05-21T09:33:40.893946',
                   'Add an unterminated keyword for testing bug #1523\n',
                   '4'))

        commits = self.tool.get_commits(start='7')
        self.assertEqual(len(commits), 7)
        self.assertEqual(
            commits[1],
            Commit('david',
                   '6',
                   '2013-06-13T07:43:04.725088',
                   'Add a branches directory',
                   '5'))

    def test_get_commits_with_branch(self):
        """Testing SVN (<backend>) get_commits with branch"""
        commits = self.tool.get_commits(branch='/branches/branch1', start='5')

        self.assertEqual(len(commits), 5)
        self.assertEqual(
            commits[0],
            Commit('chipx86',
                   '5',
                   '2010-05-21T09:33:40.893946',
                   'Add an unterminated keyword for testing bug #1523\n',
                   '4'))

        commits = self.tool.get_commits(branch='/branches/branch1', start='7')
        self.assertEqual(len(commits), 6)
        self.assertEqual(
            commits[0],
            Commit('david',
                   '7',
                   '2013-06-13T07:43:27.259554',
                   'Add a branch',
                   '5'))
        self.assertEqual(
            commits[1],
            Commit('chipx86',
                   '5',
                   '2010-05-21T09:33:40.893946',
                   'Add an unterminated keyword for testing bug #1523\n',
                   '4'))

    def test_get_commits_with_no_date(self):
        """Testing SVN (<backend>) get_commits with no date in commit"""
        def _get_log(*args, **kwargs):
            return [
                {
                    'author': 'chipx86',
                    'revision': '5',
                    'message': 'Commit 1',
                },
            ]

        self.spy_on(self.tool.client.get_log, _get_log)

        commits = self.tool.get_commits(start='5')

        self.assertEqual(len(commits), 1)
        self.assertEqual(
            commits[0],
            Commit('chipx86',
                   '5',
                   '',
                   'Commit 1'))

    def test_get_commits_with_exception(self):
        """Testing SVN (<backend>) get_commits with exception"""
        def _get_log(*args, **kwargs):
            raise Exception('Bad things happened')

        self.spy_on(self.tool.client.get_log, _get_log)

        with self.assertRaisesMessage(SCMError, 'Bad things happened'):
            self.tool.get_commits(start='5')

    def test_get_change(self):
        """Testing SVN (<backend>) get_change"""
        commit = self.tool.get_change('5')

        self.assertEqual(md5(commit.message.encode('utf-8')).hexdigest(),
                         '928336c082dd756e3f7af4cde4724ebf')
        self.assertEqual(md5(commit.diff).hexdigest(),
                         '56e50374056931c03a333f234fa63375')

    def test_utf8_keywords(self):
        """Testing SVN (<backend>) with UTF-8 files with keywords"""
        self.repository.get_file('trunk/utf8-file.txt', '9')

    def test_normalize_patch_with_svn_and_expanded_keywords(self):
        """Testing SVN (<backend>) normalize_patch with expanded keywords"""
        diff = (
            b'Index: Makefile\n'
            b'==========================================================='
            b'========\n'
            b'--- Makefile    (revision 4)\n'
            b'+++ Makefile    (working copy)\n'
            b'@@ -1,6 +1,7 @@\n'
            b' # $Id$\n'
            b' # $Rev: 123$\n'
            b' # $Revision:: 123   $\n'
            b'+# foo\n'
            b' include ../tools/Makefile.base-vars\n'
            b' NAME = misc-docs\n'
            b' OUTNAME = svn-misc-docs\n'
        )

        normalized = self.tool.normalize_patch(
            patch=diff,
            filename='trunk/doc/misc-docs/Makefile',
            revision='4')

        self.assertEqual(
            normalized,
            b'Index: Makefile\n'
            b'==========================================================='
            b'========\n'
            b'--- Makefile    (revision 4)\n'
            b'+++ Makefile    (working copy)\n'
            b'@@ -1,6 +1,7 @@\n'
            b' # $Id$\n'
            b' # $Rev$\n'
            b' # $Revision::       $\n'
            b'+# foo\n'
            b' include ../tools/Makefile.base-vars\n'
            b' NAME = misc-docs\n'
            b' OUTNAME = svn-misc-docs\n')

    def test_normalize_patch_with_svn_and_no_expanded_keywords(self):
        """Testing SVN (<backend>) normalize_patch with no expanded keywords"""
        diff = (
            b'Index: Makefile\n'
            b'==========================================================='
            b'========\n'
            b'--- Makefile    (revision 4)\n'
            b'+++ Makefile    (working copy)\n'
            b'@@ -1,6 +1,7 @@\n'
            b' # $Id$\n'
            b' # $Rev$\n'
            b' # $Revision::    $\n'
            b'+# foo\n'
            b' include ../tools/Makefile.base-vars\n'
            b' NAME = misc-docs\n'
            b' OUTNAME = svn-misc-docs\n'
        )

        normalized = self.tool.normalize_patch(
            patch=diff,
            filename='trunk/doc/misc-docs/Makefile',
            revision='4')

        self.assertEqual(
            normalized,
            b'Index: Makefile\n'
            b'==========================================================='
            b'========\n'
            b'--- Makefile    (revision 4)\n'
            b'+++ Makefile    (working copy)\n'
            b'@@ -1,6 +1,7 @@\n'
            b' # $Id$\n'
            b' # $Rev$\n'
            b' # $Revision::    $\n'
            b'+# foo\n'
            b' include ../tools/Makefile.base-vars\n'
            b' NAME = misc-docs\n'
            b' OUTNAME = svn-misc-docs\n')


class PySVNTests(_CommonSVNTestCase):
    backend = 'reviewboard.scmtools.svn.pysvn'
    backend_name = 'pysvn'


class SubvertpyTests(_CommonSVNTestCase):
    backend = 'reviewboard.scmtools.svn.subvertpy'
    backend_name = 'subvertpy'


class UtilsTests(SCMTestCase):
    """Unit tests for reviewboard.scmtools.svn.utils."""

    def test_collapse_svn_keywords(self):
        """Testing collapse_svn_keywords"""
        keyword_test_data = [
            (b'Id',
             b'/* $Id: test2.c 3 2014-08-04 22:55:09Z david $ */',
             b'/* $Id$ */'),
            (b'id',
             b'/* $Id: test2.c 3 2014-08-04 22:55:09Z david $ */',
             b'/* $Id$ */'),
            (b'id',
             b'/* $id: test2.c 3 2014-08-04 22:55:09Z david $ */',
             b'/* $id$ */'),
            (b'Id',
             b'/* $id: test2.c 3 2014-08-04 22:55:09Z david $ */',
             b'/* $id$ */')
        ]

        for keyword, data, result in keyword_test_data:
            self.assertEqual(collapse_svn_keywords(data, keyword),
                             result)

    def test_has_expanded_svn_keywords(self):
        """Testing has_expanded_svn_keywords"""
        self.assertTrue(has_expanded_svn_keywords(b'.. $ID: 123$ ..'))
        self.assertTrue(has_expanded_svn_keywords(b'.. $id::  123$ ..'))

        self.assertFalse(has_expanded_svn_keywords(b'.. $Id::   $ ..'))
        self.assertFalse(has_expanded_svn_keywords(b'.. $Id$ ..'))
        self.assertFalse(has_expanded_svn_keywords(b'.. $Id ..'))
        self.assertFalse(has_expanded_svn_keywords(b'.. $Id Here$ ..'))


class SVNAuthFormTests(TestCase):
    """Unit tests for SVNTool's authentication form."""

    def test_fields(self):
        """Testing SVNTool authentication form fields"""
        form = SVNTool.create_auth_form()

        self.assertEqual(list(form.fields), ['username', 'password'])
        self.assertEqual(form['username'].help_text, '')
        self.assertEqual(form['username'].label, 'Username')
        self.assertEqual(form['password'].help_text, '')
        self.assertEqual(form['password'].label, 'Password')

    @add_fixtures(['test_scmtools'])
    def test_load(self):
        """Tetting SVNTool authentication form load"""
        repository = self.create_repository(
            tool_name='Subversion',
            username='test-user',
            password='test-pass')

        form = SVNTool.create_auth_form(repository=repository)
        form.load()

        self.assertEqual(form['username'].value(), 'test-user')
        self.assertEqual(form['password'].value(), 'test-pass')

    @add_fixtures(['test_scmtools'])
    def test_save(self):
        """Tetting SVNTool authentication form save"""
        repository = self.create_repository(tool_name='Subversion')

        form = SVNTool.create_auth_form(
            repository=repository,
            data={
                'username': 'test-user',
                'password': 'test-pass',
            })
        self.assertTrue(form.is_valid())
        form.save()

        self.assertEqual(repository.username, 'test-user')
        self.assertEqual(repository.password, 'test-pass')


class SVNRepositoryFormTests(TestCase):
    """Unit tests for SVNTool's repository form."""

    def test_fields(self):
        """Testing SVNTool repository form fields"""
        form = SVNTool.create_repository_form()

        self.assertEqual(list(form.fields), ['path', 'mirror_path'])
        self.assertEqual(form['path'].help_text,
                         'The path to the repository. This will generally be '
                         'the URL you would use to check out the repository.')
        self.assertEqual(form['path'].label, 'Path')
        self.assertEqual(form['mirror_path'].help_text, '')
        self.assertEqual(form['mirror_path'].label, 'Mirror Path')

    @add_fixtures(['test_scmtools'])
    def test_load(self):
        """Tetting SVNTool repository form load"""
        repository = self.create_repository(
            tool_name='Subversion',
            path='https://svn.example.com/',
            mirror_path='https://svn.mirror.example.com')

        form = SVNTool.create_repository_form(repository=repository)
        form.load()

        self.assertEqual(form['path'].value(), 'https://svn.example.com/')
        self.assertEqual(form['mirror_path'].value(),
                         'https://svn.mirror.example.com')

    @add_fixtures(['test_scmtools'])
    def test_save(self):
        """Tetting SVNTool repository form save"""
        repository = self.create_repository(tool_name='Subversion')

        form = SVNTool.create_repository_form(
            repository=repository,
            data={
                'path': 'https://svn.example.com/',
                'mirror_path': 'https://svn.mirror.example.com',
            })
        self.assertTrue(form.is_valid())
        form.save()

        self.assertEqual(repository.path, 'https://svn.example.com/')
        self.assertEqual(repository.mirror_path,
                         'https://svn.mirror.example.com')
