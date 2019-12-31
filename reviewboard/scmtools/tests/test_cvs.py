# coding=utf-8
from __future__ import unicode_literals

import os

import nose
from django.core.exceptions import ValidationError
from djblets.testing.decorators import add_fixtures

from reviewboard.diffviewer.parser import DiffParserError
from reviewboard.scmtools.core import PRE_CREATION, Revision
from reviewboard.scmtools.cvs import CVSTool
from reviewboard.scmtools.errors import SCMError, FileNotFoundError
from reviewboard.scmtools.models import Repository, Tool
from reviewboard.scmtools.tests.testcases import SCMTestCase
from reviewboard.testing.testcase import TestCase


class CVSTests(SCMTestCase):
    """Unit tests for CVS."""

    fixtures = ['test_scmtools']

    def setUp(self):
        super(CVSTests, self).setUp()

        self.cvs_repo_path = os.path.join(os.path.dirname(__file__),
                                          '..', 'testdata', 'cvs_repo')
        self.cvs_ssh_path = (':ext:localhost:%s'
                             % self.cvs_repo_path.replace('\\', '/'))
        self.repository = Repository(name='CVS',
                                     path=self.cvs_repo_path,
                                     tool=Tool.objects.get(name='CVS'))

        try:
            self.tool = self.repository.get_scmtool()
        except ImportError:
            raise nose.SkipTest('cvs binary not found')

    def test_build_cvsroot_with_port(self):
        """Testing CVSTool.build_cvsroot with a port"""
        self._test_build_cvsroot(
            repo_path='example.com:123/cvsroot/test',
            username='anonymous',
            expected_cvsroot=':pserver:anonymous@example.com:123/cvsroot/test',
            expected_path='/cvsroot/test')

    def test_path_without_port(self):
        """Testing CVSTool.build_cvsroot without a port"""
        self._test_build_cvsroot(
            repo_path='example.com:/cvsroot/test',
            username='anonymous',
            expected_cvsroot=':pserver:anonymous@example.com:/cvsroot/test',
            expected_path='/cvsroot/test')

    def test_path_with_pserver_and_no_user_or_password(self):
        """Testing CVSTool.build_cvsroot with :pserver: and no user or
        password
        """
        self._test_build_cvsroot(
            repo_path=':pserver:example.com:/cvsroot/test',
            expected_cvsroot=':pserver:example.com:/cvsroot/test',
            expected_path='/cvsroot/test')

    def test_path_with_pserver_and_inline_user(self):
        """Testing CVSTool.build_cvsroot with :pserver: and inline user"""
        self._test_build_cvsroot(
            repo_path=':pserver:anonymous@example.com:/cvsroot/test',
            expected_cvsroot=':pserver:anonymous@example.com:/cvsroot/test',
            expected_path='/cvsroot/test')

    def test_path_with_pserver_and_inline_user_and_password(self):
        """Testing CVSTool.build_cvsroot with :pserver: and inline user and
        password
        """
        self._test_build_cvsroot(
            repo_path=':pserver:anonymous:pass@example.com:/cvsroot/test',
            expected_cvsroot=':pserver:anonymous:pass@example.com:'
                             '/cvsroot/test',
            expected_path='/cvsroot/test')

    def test_path_with_pserver_and_form_user(self):
        """Testing CVSTool.build_cvsroot with :pserver: and form-provided
        user
        """
        self._test_build_cvsroot(
            repo_path=':pserver:example.com:/cvsroot/test',
            username='anonymous',
            expected_cvsroot=':pserver:anonymous@example.com:/cvsroot/test',
            expected_path='/cvsroot/test')

    def test_path_with_pserver_and_form_user_and_password(self):
        """Testing CVSTool.build_cvsroot with :pserver: and form-provided
        user and password
        """
        self._test_build_cvsroot(
            repo_path=':pserver:example.com:/cvsroot/test',
            username='anonymous',
            password='pass',
            expected_cvsroot=':pserver:anonymous:pass@example.com:'
                             '/cvsroot/test',
            expected_path='/cvsroot/test')

    def test_path_with_pserver_and_inline_takes_precedence(self):
        """Testing CVSTool.build_cvsroot with :pserver: and inline
        user/password taking precedence
        """
        self._test_build_cvsroot(
            repo_path=':pserver:anonymous:pass@example.com:/cvsroot/test',
            username='grumpy',
            password='grr',
            expected_cvsroot=':pserver:anonymous:pass@example.com:'
                             '/cvsroot/test',
            expected_path='/cvsroot/test')

    def test_path_with_gserver(self):
        """Testing CVSTool.build_cvsroot with :gserver:"""
        self._test_build_cvsroot(
            repo_path=':gserver:localhost:/cvsroot/test',
            expected_cvsroot=':gserver:localhost:/cvsroot/test',
            expected_path='/cvsroot/test')

    def test_path_with_gserver_with_username(self):
        """Testing CVSTool.build_cvsroot with :gserver: with username"""
        self._test_build_cvsroot(
            repo_path=':gserver:user@localhost:/cvsroot/test',
            expected_cvsroot=':gserver:user@localhost:/cvsroot/test',
            expected_path='/cvsroot/test')

        self._test_build_cvsroot(
            repo_path=':gserver:localhost:/cvsroot/test',
            username='user',
            expected_cvsroot=':gserver:user@localhost:/cvsroot/test',
            expected_path='/cvsroot/test')

    def test_path_with_gserver_with_port(self):
        """Testing CVSTool.build_cvsroot with :gserver: with port"""
        self._test_build_cvsroot(
            repo_path=':gserver:localhost:123/cvsroot/test',
            expected_cvsroot=':gserver:localhost:123/cvsroot/test',
            expected_path='/cvsroot/test')

    def test_path_with_gserver_validates_password(self):
        """Testing CVSTool.build_cvsroot with :gserver: validates password"""
        self._test_build_cvsroot(
            repo_path=':gserver:user:pass@localhost:/cvsroot/test',
            expected_error='"gserver" CVSROOTs do not support passwords.',
            expected_cvsroot=':gserver:user@localhost:/cvsroot/test',
            expected_path='/cvsroot/test')

    def test_path_with_kserver(self):
        """Testing CVSTool.build_cvsroot with :kserver:"""
        self._test_build_cvsroot(
            repo_path=':kserver:localhost:/cvsroot/test',
            expected_cvsroot=':kserver:localhost:/cvsroot/test',
            expected_path='/cvsroot/test')

    def test_path_with_kserver_with_username(self):
        """Testing CVSTool.build_cvsroot with :kserver: with username"""
        self._test_build_cvsroot(
            repo_path=':kserver:user@localhost:/cvsroot/test',
            expected_cvsroot=':kserver:user@localhost:/cvsroot/test',
            expected_path='/cvsroot/test')

        self._test_build_cvsroot(
            repo_path=':kserver:localhost:/cvsroot/test',
            username='user',
            expected_cvsroot=':kserver:user@localhost:/cvsroot/test',
            expected_path='/cvsroot/test')

    def test_path_with_kserver_with_port(self):
        """Testing CVSTool.build_cvsroot with :kserver: with port"""
        self._test_build_cvsroot(
            repo_path=':kserver:localhost:123/cvsroot/test',
            expected_cvsroot=':kserver:localhost:123/cvsroot/test',
            expected_path='/cvsroot/test')

    def test_path_with_kserver_validates_password(self):
        """Testing CVSTool.build_cvsroot with :kserver: validates password"""
        self._test_build_cvsroot(
            repo_path=':kserver:user:pass@localhost:/cvsroot/test',
            expected_error='"kserver" CVSROOTs do not support passwords.',
            expected_cvsroot=':kserver:user@localhost:/cvsroot/test',
            expected_path='/cvsroot/test')

    def test_path_with_ext(self):
        """Testing CVSTool.build_cvsroot with :ext:"""
        self._test_build_cvsroot(
            repo_path=':ext:localhost:/cvsroot/test',
            expected_cvsroot=':ext:localhost:/cvsroot/test',
            expected_path='/cvsroot/test')

    def test_path_with_ext_validates_password(self):
        """Testing CVSTool.build_cvsroot with :ext: validates password"""
        self._test_build_cvsroot(
            repo_path=':ext:user:pass@localhost:/cvsroot/test',
            expected_error='"ext" CVSROOTs do not support passwords.',
            expected_cvsroot=':ext:user@localhost:/cvsroot/test',
            expected_path='/cvsroot/test')

    def test_path_with_ext_validates_port(self):
        """Testing CVSTool.build_cvsroot with :ext: validates port"""
        self._test_build_cvsroot(
            repo_path=':ext:localhost:123/cvsroot/test',
            expected_error='"ext" CVSROOTs do not support specifying ports.',
            expected_cvsroot=':ext:localhost:/cvsroot/test',
            expected_path='/cvsroot/test')

    def test_path_with_server(self):
        """Testing CVSTool.build_cvsroot with :server:"""
        self._test_build_cvsroot(
            repo_path=':server:localhost:/cvsroot/test',
            expected_cvsroot=':server:localhost:/cvsroot/test',
            expected_path='/cvsroot/test')

    def test_path_with_server_validates_password(self):
        """Testing CVSTool.build_cvsroot with :server: validates password"""
        self._test_build_cvsroot(
            repo_path=':server:user:pass@localhost:/cvsroot/test',
            expected_error='"server" CVSROOTs do not support passwords.',
            expected_cvsroot=':server:user@localhost:/cvsroot/test',
            expected_path='/cvsroot/test')

    def test_path_with_server_validates_port(self):
        """Testing CVSTool.build_cvsroot with :server: validates port"""
        self._test_build_cvsroot(
            repo_path=':server:localhost:123/cvsroot/test',
            expected_error='"server" CVSROOTs do not support specifying '
                           'ports.',
            expected_cvsroot=':server:localhost:/cvsroot/test',
            expected_path='/cvsroot/test')

    def test_path_with_ssh(self):
        """Testing CVSTool.build_cvsroot with :ssh:"""
        self._test_build_cvsroot(
            repo_path=':ssh:localhost:/cvsroot/test',
            expected_cvsroot=':ssh:localhost:/cvsroot/test',
            expected_path='/cvsroot/test')

    def test_path_with_ssh_validates_password(self):
        """Testing CVSTool.build_cvsroot with :ssh: validates password"""
        self._test_build_cvsroot(
            repo_path=':ssh:user:pass@localhost:/cvsroot/test',
            expected_error='"ssh" CVSROOTs do not support passwords.',
            expected_cvsroot=':ssh:user@localhost:/cvsroot/test',
            expected_path='/cvsroot/test')

    def test_path_with_ssh_validates_port(self):
        """Testing CVSTool.build_cvsroot with :ssh: validates port"""
        self._test_build_cvsroot(
            repo_path=':ssh:localhost:123/cvsroot/test',
            expected_error='"ssh" CVSROOTs do not support specifying '
                           'ports.',
            expected_cvsroot=':ssh:localhost:/cvsroot/test',
            expected_path='/cvsroot/test')

    def test_path_with_extssh(self):
        """Testing CVSTool.build_cvsroot with :extssh:"""
        self._test_build_cvsroot(
            repo_path=':extssh:localhost:/cvsroot/test',
            expected_cvsroot=':extssh:localhost:/cvsroot/test',
            expected_path='/cvsroot/test')

    def test_path_with_extssh_validates_password(self):
        """Testing CVSTool.build_cvsroot with :extssh: validates password"""
        self._test_build_cvsroot(
            repo_path=':extssh:user:pass@localhost:/cvsroot/test',
            expected_error='"extssh" CVSROOTs do not support passwords.',
            expected_cvsroot=':extssh:user@localhost:/cvsroot/test',
            expected_path='/cvsroot/test')

    def test_path_with_extssh_validates_port(self):
        """Testing CVSTool.build_cvsroot with :extssh: validates port"""
        self._test_build_cvsroot(
            repo_path=':extssh:localhost:123/cvsroot/test',
            expected_error='"extssh" CVSROOTs do not support specifying '
                           'ports.',
            expected_cvsroot=':extssh:localhost:/cvsroot/test',
            expected_path='/cvsroot/test')

    def test_path_with_fork(self):
        """Testing CVSTool.build_cvsroot with :fork:"""
        self._test_build_cvsroot(
            repo_path=':fork:/home/myuser/cvsroot',
            expected_cvsroot=':fork:/home/myuser/cvsroot',
            expected_path='/home/myuser/cvsroot')

    def test_path_with_fork_validates_username(self):
        """Testing CVSTool.build_cvsroot with :fork: validates usernames"""
        self._test_build_cvsroot(
            repo_path=':fork:/home/myuser/cvsroot',
            username='myuser',
            expected_error='"fork" CVSROOTs do not support usernames.',
            expected_cvsroot=':fork:/home/myuser/cvsroot',
            expected_path='/home/myuser/cvsroot')

    def test_path_with_fork_validates_password(self):
        """Testing CVSTool.build_cvsroot with :fork: validates passwords"""
        self._test_build_cvsroot(
            repo_path=':fork:/home/myuser/cvsroot',
            password='myuser',
            expected_error='"fork" CVSROOTs do not support passwords.',
            expected_cvsroot=':fork:/home/myuser/cvsroot',
            expected_path='/home/myuser/cvsroot')

    def test_path_with_local(self):
        """Testing CVSTool.build_cvsroot with :local:"""
        self._test_build_cvsroot(
            repo_path=':local:/home/myuser/cvsroot',
            expected_cvsroot=':local:/home/myuser/cvsroot',
            expected_path='/home/myuser/cvsroot')

    def test_path_with_local_validates_username(self):
        """Testing CVSTool.build_cvsroot with :local: validates usernames"""
        self._test_build_cvsroot(
            repo_path=':local:/home/myuser/cvsroot',
            username='myuser',
            expected_error='"local" CVSROOTs do not support usernames.',
            expected_cvsroot=':local:/home/myuser/cvsroot',
            expected_path='/home/myuser/cvsroot')

    def test_path_with_local_validates_password(self):
        """Testing CVSTool.build_cvsroot with :local: validates passwords"""
        self._test_build_cvsroot(
            repo_path=':local:/home/myuser/cvsroot',
            password='myuser',
            expected_error='"local" CVSROOTs do not support passwords.',
            expected_cvsroot=':local:/home/myuser/cvsroot',
            expected_path='/home/myuser/cvsroot')

    def test_get_file(self):
        """Testing CVSTool.get_file"""
        tool = self.tool
        expected = b'test content\n'
        filename = 'test/testfile'
        rev = Revision('1.1')

        value = tool.get_file(filename, rev)
        self.assertIsInstance(value, bytes)
        self.assertEqual(value, expected)

        value = tool.get_file('%s,v' % filename, rev)
        self.assertIsInstance(value, bytes)
        self.assertEqual(value, expected)

        value = tool.get_file('%s/%s,v' % (tool.repopath, filename), rev)
        self.assertIsInstance(value, bytes)
        self.assertEqual(value, expected)

        with self.assertRaises(FileNotFoundError):
            tool.get_file('')

        with self.assertRaises(FileNotFoundError):
            tool.get_file('hello', PRE_CREATION)

    def test_get_file_with_keywords(self):
        """Testing CVSTool.get_file with file containing keywords"""
        self.assertEqual(self.tool.get_file('test/testfile', Revision('1.2')),
                         b'$Id$\n$Author$\n\ntest content\n')

    def test_file_exists(self):
        """Testing CVSTool.file_exists"""
        tool = self.tool

        self.assertTrue(tool.file_exists('test/testfile'))
        self.assertTrue(tool.file_exists('%s/test/testfile' % tool.repopath))
        self.assertTrue(tool.file_exists('test/testfile,v'))

        self.assertFalse(tool.file_exists('test/testfile2'))
        self.assertFalse(tool.file_exists('%s/test/testfile2' % tool.repopath))
        self.assertFalse(tool.file_exists('test/testfile2,v'))
        self.assertFalse(tool.file_exists('test/testfile', Revision('2.1')))

    def test_revision_parsing(self):
        """Testing CVSTool revision number parsing"""
        self.assertEqual(self.tool.parse_diff_revision(b'',
                                                       b'PRE-CREATION')[1],
                         PRE_CREATION)
        self.assertEqual(
            self.tool.parse_diff_revision(
                b'',
                b'7 Nov 2005 13:17:07 -0000\t1.2')[1],
            b'1.2')
        self.assertEqual(
            self.tool.parse_diff_revision(
                b'',
                b'7 Nov 2005 13:17:07 -0000\t1.2.3.4')[1],
            b'1.2.3.4')
        self.assertRaises(SCMError,
                          lambda: self.tool.parse_diff_revision(b'', b'hello'))

    def test_interface(self):
        """Testing basic CVSTool API"""
        self.assertTrue(self.tool.diffs_use_absolute_paths)

    def test_simple_diff(self):
        """Testing parsing CVS simple diff"""
        diff = (b'Index: testfile\n'
                b'==========================================================='
                b'========\n'
                b'RCS file: %s/test/testfile,v\n'
                b'retrieving revision 1.1.1.1\n'
                b'diff -u -r1.1.1.1 testfile\n'
                b'--- testfile    26 Jul 2007 08:50:30 -0000      1.1.1.1\n'
                b'+++ testfile    26 Jul 2007 10:20:20 -0000\n'
                b'@@ -1 +1,2 @@\n'
                b'-test content\n'
                b'+updated test content\n'
                b'+added info\n'
                % self.cvs_repo_path.encode('utf-8'))

        file = self.tool.get_parser(diff).parse()[0]
        self.assertEqual(file.orig_filename, b'test/testfile')
        self.assertEqual(file.orig_file_details,
                         b'26 Jul 2007 08:50:30 -0000      1.1.1.1')
        self.assertEqual(file.modified_filename, b'test/testfile')
        self.assertEqual(file.modified_file_details,
                         b'26 Jul 2007 10:20:20 -0000')
        self.assertEqual(file.data, diff)
        self.assertEqual(file.insert_count, 2)
        self.assertEqual(file.delete_count, 1)

    def test_new_diff_revision_format(self):
        """Testing parsing CVS diff with new revision format"""
        diff = (
            'Index: %(path)s/test/testfile\n'
            'diff -u %(path)s/test/testfile:1.5.2.1 '
            '%(path)s/test/testfile:1.5.2.2\n'
            '--- test/testfile:1.5.2.1\tThu Dec 15 16:27:47 2011\n'
            '+++ test/testfile\tTue Jan 10 10:36:26 2012\n'
            '@@ -1 +1,2 @@\n'
            '-test content\n'
            '+updated test content\n'
            '+added info\n'
            % {
                'path': self.cvs_repo_path,
            }
        ).encode('utf-8')

        file = self.tool.get_parser(diff).parse()[0]
        f2, revision = self.tool.parse_diff_revision(file.orig_filename,
                                                     file.orig_file_details,
                                                     file.moved)
        self.assertIsInstance(f2, bytes)
        self.assertIsInstance(revision, bytes)

        self.assertEqual(f2, b'test/testfile')
        self.assertEqual(revision, b'1.5.2.1')
        self.assertEqual(file.modified_filename, b'test/testfile')
        self.assertEqual(file.modified_file_details,
                         b'Tue Jan 10 10:36:26 2012')
        self.assertEqual(file.insert_count, 2)
        self.assertEqual(file.delete_count, 1)

    def test_bad_diff(self):
        """Testing parsing CVS diff with bad info"""
        diff = (b'Index: newfile\n'
                b'==========================================================='
                b'========\n'
                b'diff -N newfile\n'
                b'--- /dev/null\t1 Jan 1970 00:00:00 -0000\n'
                b'+++ newfile\t26 Jul 2007 10:11:45 -0000\n'
                b'@@ -0,0 +1 @@\n'
                b'+new file content')

        self.assertRaises(DiffParserError,
                          lambda: self.tool.get_parser(diff).parse())

    def test_bad_diff2(self):
        """Testing parsing CVS bad diff with new file"""
        diff = (b'Index: newfile\n'
                b'==========================================================='
                b'========\n'
                b'RCS file: newfile\n'
                b'diff -N newfile\n'
                b'--- /dev/null\n'
                b'+++ newfile\t26 Jul 2007 10:11:45 -0000\n'
                b'@@ -0,0 +1 @@\n'
                b'+new file content')

        self.assertRaises(DiffParserError,
                          lambda: self.tool.get_parser(diff).parse())

    def test_newfile_diff(self):
        """Testing parsing CVS diff with new file"""
        diff = (b'Index: newfile\n'
                b'==========================================================='
                b'========\n'
                b'RCS file: newfile\n'
                b'diff -N newfile\n'
                b'--- /dev/null\t1 Jan 1970 00:00:00 -0000\n'
                b'+++ newfile\t26 Jul 2007 10:11:45 -0000\n'
                b'@@ -0,0 +1 @@\n'
                b'+new file content\n')

        file = self.tool.get_parser(diff).parse()[0]
        self.assertEqual(file.orig_filename, b'newfile')
        self.assertEqual(file.orig_file_details, b'PRE-CREATION')
        self.assertEqual(file.modified_filename, b'newfile')
        self.assertEqual(file.modified_file_details,
                         b'26 Jul 2007 10:11:45 -0000')
        self.assertEqual(file.data, diff)
        self.assertEqual(file.insert_count, 1)
        self.assertEqual(file.delete_count, 0)

    def test_inter_revision_diff(self):
        """Testing parsing CVS inter-revision diff"""
        diff = (b'Index: testfile\n'
                b'==========================================================='
                b'========\n'
                b'RCS file: %s/test/testfile,v\n'
                b'retrieving revision 1.1\n'
                b'retrieving revision 1.2\n'
                b'diff -u -p -r1.1 -r1.2\n'
                b'--- testfile    26 Jul 2007 08:50:30 -0000      1.1\n'
                b'+++ testfile    27 Sep 2007 22:57:16 -0000      1.2\n'
                b'@@ -1 +1,2 @@\n'
                b'-test content\n'
                b'+updated test content\n'
                b'+added info\n'
                % self.cvs_repo_path.encode('utf-8'))

        file = self.tool.get_parser(diff).parse()[0]
        self.assertEqual(file.orig_filename, b'test/testfile')
        self.assertEqual(file.orig_file_details,
                         b'26 Jul 2007 08:50:30 -0000      1.1')
        self.assertEqual(file.modified_filename, b'test/testfile')
        self.assertEqual(file.modified_file_details,
                         b'27 Sep 2007 22:57:16 -0000      1.2')
        self.assertEqual(file.data, diff)
        self.assertEqual(file.insert_count, 2)
        self.assertEqual(file.delete_count, 1)

    def test_unicode_diff(self):
        """Testing parsing CVS diff with unicode filenames"""
        diff = ('Index: téstfile\n'
                '==========================================================='
                '========\n'
                'RCS file: %s/test/téstfile,v\n'
                'retrieving revision 1.1.1.1\n'
                'diff -u -r1.1.1.1 téstfile\n'
                '--- téstfile    26 Jul 2007 08:50:30 -0000      1.1.1.1\n'
                '+++ téstfile    26 Jul 2007 10:20:20 -0000\n'
                '@@ -1 +1,2 @@\n'
                '-tést content\n'
                '+updated test content\n'
                '+added info\n')
        diff = diff % self.cvs_repo_path
        diff = diff.encode('utf-8')

        file = self.tool.get_parser(diff).parse()[0]
        self.assertEqual(file.orig_filename, 'test/téstfile'.encode('utf-8'))
        self.assertEqual(file.orig_file_details,
                         b'26 Jul 2007 08:50:30 -0000      1.1.1.1')
        self.assertEqual(file.modified_filename,
                         'test/téstfile'.encode('utf-8'))
        self.assertEqual(file.modified_file_details,
                         b'26 Jul 2007 10:20:20 -0000')
        self.assertEqual(file.data, diff)
        self.assertEqual(file.insert_count, 2)
        self.assertEqual(file.delete_count, 1)

    def test_keyword_diff(self):
        """Testing parsing CVS diff with keywords"""
        diff = self.tool.normalize_patch(
            b'Index: Makefile\n'
            b'==========================================================='
            b'========\n'
            b'RCS file: /cvsroot/src/Makefile,v\n'
            b'retrieving revision 1.1\n'
            b'retrieving revision 1.2\n'
            b'diff -u -r1.1.1.1 Makefile\n'
            b'--- Makefile    26 Jul 2007 08:50:30 -0000      1.1\n'
            b'+++ Makefile    26 Jul 2007 10:20:20 -0000      1.2\n'
            b'@@ -1,6 +1,7 @@\n'
            b' # $Author: bob $\n'
            b' # $Date: 2014/12/18 13:09:42 $\n'
            b' # $Header: /src/Makefile,v 1.2 2014/12/18 '
            b'13:09:42 bob Exp $\n'
            b' # $Id: Makefile,v 1.2 2014/12/18 13:09:42 bob Exp $\n'
            b' # $Locker: bob $\n'
            b' # $Name: some_name $\n'
            b' # $RCSfile: Makefile,v $\n'
            b' # $Revision: 1.2 $\n'
            b' # $Source: /src/Makefile,v $\n'
            b' # $State: Exp $\n'
            b'+# foo\n'
            b' include ../tools/Makefile.base-vars\n'
            b' NAME = misc-docs\n'
            b' OUTNAME = cvs-misc-docs\n',
            'Makefile')

        self.assertEqual(
            diff,
            b'Index: Makefile\n'
            b'==========================================================='
            b'========\n'
            b'RCS file: /cvsroot/src/Makefile,v\n'
            b'retrieving revision 1.1\n'
            b'retrieving revision 1.2\n'
            b'diff -u -r1.1.1.1 Makefile\n'
            b'--- Makefile    26 Jul 2007 08:50:30 -0000      1.1\n'
            b'+++ Makefile    26 Jul 2007 10:20:20 -0000      1.2\n'
            b'@@ -1,6 +1,7 @@\n'
            b' # $Author$\n'
            b' # $Date$\n'
            b' # $Header$\n'
            b' # $Id$\n'
            b' # $Locker$\n'
            b' # $Name$\n'
            b' # $RCSfile$\n'
            b' # $Revision$\n'
            b' # $Source$\n'
            b' # $State$\n'
            b'+# foo\n'
            b' include ../tools/Makefile.base-vars\n'
            b' NAME = misc-docs\n'
            b' OUTNAME = cvs-misc-docs\n')

    def test_keyword_diff_unicode(self):
        """Testing parsing CVS diff with keywords and unicode characters"""
        # Test bug 3931: this should succeed without a UnicodeDecodeError
        self.tool.normalize_patch(
            b'Index: Makefile\n'
            b'==========================================================='
            b'========\n'
            b'RCS file: /cvsroot/src/Makefile,v\n'
            b'retrieving revision 1.1\n'
            b'retrieving revision 1.2\n'
            b'diff -u -r1.1.1.1 Makefile\n'
            b'--- Makefile    26 Jul 2007 08:50:30 -0000      1.1\n'
            b'+++ Makefile    26 Jul 2007 10:20:20 -0000      1.2\n'
            b'@@ -1,6 +1,7 @@\n'
            b' # $Author: bob $\n'
            b' # $Date: 2014/12/18 13:09:42 $\n'
            b' # $Header: /src/Makefile,v 1.2 2014/12/18 '
            b'13:09:42 bob Exp $\n'
            b' # $Id: Makefile,v 1.2 2014/12/18 13:09:42 bob Exp $\n'
            b' # $Locker: bob $\n'
            b' # $Name: some_name $\n'
            b' # $RCSfile: Makefile,v $\n'
            b' # $Revision: 1.2 $\n'
            b' # $Source: /src/Makefile,v $\n'
            b' # $State: Exp $\n'
            b'+# foo \xf0\x9f\x92\xa9\n'
            b' include ../tools/Makefile.base-vars\n'
            b' NAME = misc-docs\n'
            b' OUTNAME = cvs-misc-docs\n',
            'Makefile')

    def test_binary_diff(self):
        """Testing parsing CVS binary diff"""
        diff = (
            b'Index: testfile\n'
            b'==============================================================='
            b'====\n'
            b'RCS file: %s/test/testfile,v\n'
            b'retrieving revision 1.1.1.1\n'
            b'diff -u -r1.1.1.1 testfile\n'
            b'Binary files testfile and testfile differ\n'
            % self.cvs_repo_path.encode('utf-8'))

        file = self.tool.get_parser(diff).parse()[0]
        self.assertEqual(file.orig_filename, b'test/testfile')
        self.assertEqual(file.orig_file_details, b'')
        self.assertEqual(file.modified_filename, b'test/testfile')
        self.assertEqual(file.modified_file_details, b'')
        self.assertTrue(file.binary)
        self.assertEqual(file.data, diff)

    def test_binary_diff_new_file(self):
        """Testing parsing CVS binary diff with new file"""
        diff = (
            b'Index: test/testfile\n'
            b'==============================================================='
            b'====\n'
            b'RCS file: test/testfile,v\n'
            b'diff -N test/testfile\n'
            b'Binary files /dev/null and testfile differ\n')

        file = self.tool.get_parser(diff).parse()[0]
        self.assertEqual(file.orig_filename, b'test/testfile')
        self.assertEqual(file.orig_file_details, b'PRE-CREATION')
        self.assertEqual(file.modified_filename, b'test/testfile')
        self.assertEqual(file.modified_file_details, b'')
        self.assertTrue(file.binary)
        self.assertEqual(file.data, diff)

    def test_bad_root(self):
        """Testing CVSTool with a bad CVSROOT"""
        file = 'test/testfile'
        rev = Revision('1.1')
        badrepo = Repository(name='CVS',
                             path=self.cvs_repo_path + '2',
                             tool=Tool.objects.get(name='CVS'))
        badtool = badrepo.get_scmtool()

        self.assertRaises(SCMError, lambda: badtool.get_file(file, rev))

    def test_ssh(self):
        """Testing a SSH-backed CVS repository"""
        self._test_ssh(self.cvs_ssh_path, 'CVSROOT/modules')

    def test_ssh_with_site(self):
        """Testing a SSH-backed CVS repository with a LocalSite"""
        self._test_ssh_with_site(self.cvs_ssh_path, 'CVSROOT/modules')

    def _test_build_cvsroot(self, repo_path, expected_cvsroot, expected_path,
                            expected_error=None, username=None, password=None):
        if expected_error:
            with self.assertRaisesMessage(ValidationError, expected_error):
                self.tool.build_cvsroot(repo_path, username, password,
                                        validate=True)

        cvsroot, norm_path = self.tool.build_cvsroot(repo_path, username,
                                                     password, validate=False)

        self.assertEqual(cvsroot, expected_cvsroot)
        self.assertEqual(norm_path, expected_path)


class CVSAuthFormTests(TestCase):
    """Unit tests for CVSTool's authentication form."""

    def test_fields(self):
        """Testing CVSTool authentication form fields"""
        form = CVSTool.create_auth_form()

        self.assertEqual(list(form.fields), ['username', 'password'])
        self.assertEqual(form['username'].help_text, '')
        self.assertEqual(form['username'].label, 'Username')
        self.assertEqual(form['password'].help_text, '')
        self.assertEqual(form['password'].label, 'Password')

    @add_fixtures(['test_scmtools'])
    def test_load(self):
        """Tetting CVSTool authentication form load"""
        repository = self.create_repository(
            tool_name='CVS',
            username='test-user',
            password='test-pass')

        form = CVSTool.create_auth_form(repository=repository)
        form.load()

        self.assertEqual(form['username'].value(), 'test-user')
        self.assertEqual(form['password'].value(), 'test-pass')

    @add_fixtures(['test_scmtools'])
    def test_save(self):
        """Tetting CVSTool authentication form save"""
        repository = self.create_repository(tool_name='CVS')

        form = CVSTool.create_auth_form(
            repository=repository,
            data={
                'username': 'test-user',
                'password': 'test-pass',
            })
        self.assertTrue(form.is_valid())
        form.save()

        self.assertEqual(repository.username, 'test-user')
        self.assertEqual(repository.password, 'test-pass')


class CVSRepositoryFormTests(TestCase):
    """Unit tests for CVSTool's repository form."""

    def test_fields(self):
        """Testing CVSTool repository form fields"""
        form = CVSTool.create_repository_form()

        self.assertEqual(list(form.fields), ['path', 'mirror_path'])
        self.assertEqual(form['path'].help_text,
                         'The CVSROOT used to access the repository.')
        self.assertEqual(form['path'].label, 'Path')
        self.assertEqual(form['mirror_path'].help_text, '')
        self.assertEqual(form['mirror_path'].label, 'Mirror Path')

    @add_fixtures(['test_scmtools'])
    def test_load(self):
        """Tetting CVSTool repository form load"""
        repository = self.create_repository(
            tool_name='CVS',
            path='example.com:123/cvsroot/test',
            mirror_path=':pserver:example.com:/cvsroot/test')

        form = CVSTool.create_repository_form(repository=repository)
        form.load()

        self.assertEqual(form['path'].value(), 'example.com:123/cvsroot/test')
        self.assertEqual(form['mirror_path'].value(),
                         ':pserver:example.com:/cvsroot/test')

    @add_fixtures(['test_scmtools'])
    def test_save(self):
        """Tetting CVSTool repository form save"""
        repository = self.create_repository(tool_name='CVS')

        form = CVSTool.create_repository_form(
            repository=repository,
            data={
                'path': 'example.com:123/cvsroot/test',
                'mirror_path': ':pserver:example.com:/cvsroot/test',
            })
        self.assertTrue(form.is_valid())
        form.save()

        self.assertEqual(repository.path, 'example.com:123/cvsroot/test')
        self.assertEqual(repository.mirror_path,
                         ':pserver:example.com:/cvsroot/test')
