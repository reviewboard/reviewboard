# coding=utf-8
from __future__ import unicode_literals

import os
from hashlib import md5

import nose
from django.conf import settings
from kgb import SpyAgency

from reviewboard.diffviewer.diffutils import patch
from reviewboard.scmtools.core import (Branch, Commit, Revision, HEAD,
                                       PRE_CREATION)
from reviewboard.scmtools.errors import SCMError, FileNotFoundError
from reviewboard.scmtools.models import Repository, Tool
from reviewboard.scmtools.svn import recompute_svn_backend
from reviewboard.scmtools.tests.testcases import SCMTestCase


class CommonSVNTestCase(SpyAgency, SCMTestCase):
    """Common unit tests for Subversion.

    This is meant to be subclassed for each backend that wants to run
    the common set of tests.
    """

    backend = None
    backend_name = None
    fixtures = ['test_scmtools']

    def setUp(self):
        super(CommonSVNTestCase, self).setUp()

        self._old_backend_setting = settings.SVNTOOL_BACKENDS
        settings.SVNTOOL_BACKENDS = [self.backend]
        recompute_svn_backend()

        self.svn_repo_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__),
                         '..', 'testdata', 'svn_repo'))
        self.svn_ssh_path = ('svn+ssh://localhost%s'
                             % self.svn_repo_path.replace('\\', '/'))
        self.repository = Repository(name='Subversion SVN',
                                     path='file://' + self.svn_repo_path,
                                     tool=Tool.objects.get(name='Subversion'))

        try:
            self.tool = self.repository.get_scmtool()
        except ImportError:
            raise nose.SkipTest('The %s backend could not be used. A '
                                'dependency may be missing.'
                                % self.backend)

        assert self.tool.client.__class__.__module__ == self.backend

    def tearDown(self):
        super(CommonSVNTestCase, self).tearDown()

        settings.SVNTOOL_BACKENDS = self._old_backend_setting
        recompute_svn_backend()

    def shortDescription(self):
        desc = super(CommonSVNTestCase, self).shortDescription()
        desc = desc.replace('<backend>', self.backend_name)

        return desc

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
        expected = (b'include ../tools/Makefile.base-vars\n'
                    b'NAME = misc-docs\n'
                    b'OUTNAME = svn-misc-docs\n'
                    b'INSTALL_DIR = $(DESTDIR)/usr/share/doc/subversion\n'
                    b'include ../tools/Makefile.base-rules\n')

        # There are 3 versions of this test in order to get 100% coverage of
        # the svn module.
        rev = Revision('2')
        file = 'trunk/doc/misc-docs/Makefile'

        value = self.tool.get_file(file, rev)
        self.assertTrue(isinstance(value, bytes))
        self.assertEqual(value, expected)

        self.assertEqual(self.tool.get_file('/' + file, rev), expected)

        self.assertEqual(
            self.tool.get_file(self.repository.path + '/' + file, rev),
            expected)

        self.assertTrue(self.tool.file_exists('trunk/doc/misc-docs/Makefile'))
        self.assertTrue(
            not self.tool.file_exists('trunk/doc/misc-docs/Makefile2'))

        self.assertRaises(FileNotFoundError, lambda: self.tool.get_file(''))

        self.assertRaises(FileNotFoundError,
                          lambda: self.tool.get_file('hello', PRE_CREATION))

    def test_revision_parsing(self):
        """Testing SVN (<backend>) revision number parsing"""
        self.assertEqual(
            self.tool.parse_diff_revision('', '(working copy)')[1],
            HEAD)
        self.assertEqual(
            self.tool.parse_diff_revision('', '   (revision 0)')[1],
            PRE_CREATION)

        self.assertEqual(self.tool.parse_diff_revision('', '(revision 1)')[1],
                         '1')
        self.assertEqual(self.tool.parse_diff_revision('', '(revision 23)')[1],
                         '23')

        # Fix for bug 2176
        self.assertEqual(
            self.tool.parse_diff_revision('', '\t(revision 4)')[1], '4')

        self.assertEqual(
            self.tool.parse_diff_revision(
                '', '2007-06-06 15:32:23 UTC (rev 10958)')[1],
            '10958')

        # Fix for bug 2632
        self.assertEqual(self.tool.parse_diff_revision('', '(revision )')[1],
                         PRE_CREATION)

        self.assertRaises(SCMError,
                          lambda: self.tool.parse_diff_revision('', 'hello'))

        # Verify that 'svn diff' localized revision strings parse correctly.
        self.assertEqual(self.tool.parse_diff_revision('', '(revisión: 5)')[1],
                         '5')
        self.assertEqual(self.tool.parse_diff_revision('',
                         '(リビジョン 6)')[1], '6')
        self.assertEqual(self.tool.parse_diff_revision('', '(版本 7)')[1],
                         '7')

    def test_revision_parsing_with_nonexistent(self):
        """Testing SVN (<backend>) revision parsing with "(nonexistent)"
        revision indicator
        """
        # English
        self.assertEqual(
            self.tool.parse_diff_revision('', '(nonexistent)')[1],
            PRE_CREATION)

        # German
        self.assertEqual(
            self.tool.parse_diff_revision('', '(nicht existent)')[1],
            PRE_CREATION)

        # Simplified Chinese
        self.assertEqual(
            self.tool.parse_diff_revision('', '(不存在的)')[1],
            PRE_CREATION)

    def test_revision_parsing_with_nonexistent_and_branches(self):
        """Testing SVN (<backend>) revision parsing with relocation
        information and nonexisitent revision specifier.
        """
        self.assertEqual(
            self.tool.parse_diff_revision(
                '', '(.../trunk) (nonexistent)')[1],
            PRE_CREATION)

        self.assertEqual(
            self.tool.parse_diff_revision(
                '', '(.../branches/branch-1.0)     (nicht existent)')[1],
            PRE_CREATION)

        self.assertEqual(
            self.tool.parse_diff_revision(
                '', '        (.../trunk)     (不存在的)')[1],
            PRE_CREATION)

    def test_interface(self):
        """Testing SVN (<backend>) with basic SVNTool API"""
        self.assertEqual(self.tool.get_diffs_use_absolute_paths(), False)

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
        self.assertEqual(file.origFile, 'binfile')
        self.assertEqual(file.binary, True)

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
        self.assertEqual(files[0].origFile, 'binfile')
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
        self.assertEqual(files[0].origFile, 'binfile')
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
        self.assertEqual(files[0].origFile, 'Filé')
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
        self.assertEqual(files[0].origFile, 'File with spaces')
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
        self.assertEqual(files[0].origFile, 'empty-file')
        self.assertEqual(files[0].newFile, 'empty-file')
        self.assertEqual(files[0].origInfo, '(revision 0)')
        self.assertEqual(files[0].newInfo, '(revision 0)')
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
        self.assertEqual(files[0].origFile, 'empty-file')
        self.assertEqual(files[0].newFile, 'empty-file')
        self.assertEqual(files[0].origInfo, '(revision 4)')
        self.assertEqual(files[0].newInfo, '(working copy)')
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
        self.assertEqual(diff_file.origFile, 'path/to/README2')
        self.assertEqual(diff_file.newFile, 'path/to/README2')
        self.assertEqual(diff_file.origInfo, '(revision 4)')
        self.assertEqual(diff_file.newInfo, '(revision )')
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
                                             commit='9', default=True))
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

    def test_get_change(self):
        """Testing SVN (<backend>) get_change"""
        commit = self.tool.get_change('5')

        self.assertEqual(md5(commit.message.encode('utf-8')).hexdigest(),
                         '928336c082dd756e3f7af4cde4724ebf')
        self.assertEqual(md5(commit.diff.encode('utf-8')).hexdigest(),
                         '56e50374056931c03a333f234fa63375')

    def test_utf8_keywords(self):
        """Testing SVN (<backend>) with UTF-8 files with keywords"""
        self.repository.get_file('trunk/utf8-file.txt', '9')


class PySVNTests(CommonSVNTestCase):
    backend = 'reviewboard.scmtools.svn.pysvn'
    backend_name = 'pysvn'


class SubvertpyTests(CommonSVNTestCase):
    backend = 'reviewboard.scmtools.svn.subvertpy'
    backend_name = 'subvertpy'

    def test_collapse_keywords(self):
        """Testing SVN keyword collapsing"""
        keyword_test_data = [
            ('Id',
             '/* $Id: test2.c 3 2014-08-04 22:55:09Z david $ */',
             '/* $Id$ */'),
            ('id',
             '/* $Id: test2.c 3 2014-08-04 22:55:09Z david $ */',
             '/* $Id$ */'),
            ('id',
             '/* $id: test2.c 3 2014-08-04 22:55:09Z david $ */',
             '/* $id$ */'),
            ('Id',
             '/* $id: test2.c 3 2014-08-04 22:55:09Z david $ */',
             '/* $id$ */')
        ]

        for keyword, data, result in keyword_test_data:
            self.assertEqual(self.tool.client.collapse_keywords(data, keyword),
                             result)
