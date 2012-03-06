import errno
import imp
import os
import nose
import paramiko
import shutil
import socket
import tempfile
try:
    from hashlib import md5
except ImportError:
    from md5 import md5

from django.contrib.auth.models import AnonymousUser, User
from django.test import TestCase as DjangoTestCase
from djblets.util.filesystem import is_exe_in_path
try:
    imp.find_module("P4")
    from P4 import P4Error
except ImportError:
    pass

from reviewboard.diffviewer.diffutils import patch
from reviewboard.diffviewer.parser import DiffParserError
from reviewboard.reviews.models import Group
from reviewboard.scmtools import sshutils
from reviewboard.scmtools.core import HEAD, PRE_CREATION, ChangeSet, Revision
from reviewboard.scmtools.errors import SCMError, FileNotFoundError, \
                                        RepositoryNotFoundError, \
                                        AuthenticationError
from reviewboard.scmtools.forms import RepositoryForm
from reviewboard.scmtools.git import ShortSHA1Error
from reviewboard.scmtools.models import Repository, Tool
from reviewboard.scmtools.perforce import STunnelProxy, STUNNEL_SERVER
from reviewboard.site.models import LocalSite


class SCMTestCase(DjangoTestCase):
    _can_test_ssh = None

    def setUp(self):
        self.old_home = os.getenv('HOME')
        self.tempdir = None
        self.tool = None
        os.environ['RBSSH_ALLOW_AGENT'] = '0'

    def tearDown(self):
        self._set_home(self.old_home)

        if self.tempdir:
            shutil.rmtree(self.tempdir)

    def _set_home(self, homedir):
        os.environ['HOME'] = homedir

    def _check_can_test_ssh(self):
        if SCMTestCase._can_test_ssh is None:
            key = sshutils.get_user_key()

            SCMTestCase._can_test_ssh = (key is not None and
                                         sshutils.is_key_authorized(key))

        if not SCMTestCase._can_test_ssh:
            raise nose.SkipTest(
                "Cannot perform SSH access tests. The local user's SSH "
                "public key must be in the %s file and SSH must be enabled."
                % os.path.join(sshutils.get_ssh_dir(), 'authorized_keys'))

    def _test_ssh(self, repo_path, filename=None):
        self._check_can_test_ssh()

        repo = Repository(name='SSH Test', path=repo_path,
                          tool=self.repository.tool)
        tool = repo.get_scmtool()

        try:
            tool.check_repository(repo_path)
        except socket.error, e:
            if e.errno == errno.ECONNREFUSED:
                # This box likely isn't set up for this test.
                SCMTestCase._can_test_ssh = False
                raise nose.SkipTest(
                    "Cannot perform SSH access tests. No local SSH service is "
                    "running.")
            else:
                raise

        if filename:
            self.assertNotEqual(tool.get_file(filename, HEAD), None)

    def _test_ssh_with_site(self, repo_path, filename=None):
        """Utility function to test SSH access with a LocalSite."""
        self._check_can_test_ssh()

        # Get the user's .ssh key, for use in the tests
        user_key = sshutils.get_user_key()
        self.assertNotEqual(user_key, None)

        # Switch to a new SSH directory.
        self.tempdir = tempfile.mkdtemp(prefix='rb-tests-home-')
        sshdir = os.path.join(self.tempdir, '.ssh')
        self._set_home(self.tempdir)

        self.assertEqual(sshdir, sshutils.get_ssh_dir())
        self.assertFalse(os.path.exists(os.path.join(sshdir, 'id_rsa')))
        self.assertFalse(os.path.exists(os.path.join(sshdir, 'id_dsa')))
        self.assertEqual(sshutils.get_user_key(), None)

        tool_class = self.repository.tool

        # Make sure we aren't using the old SSH key. We want auth errors.
        repo = Repository(name='SSH Test', path=repo_path, tool=tool_class)
        tool = repo.get_scmtool()
        self.assertRaises(sshutils.AuthenticationError,
                          lambda: tool.check_repository(repo_path))

        if filename:
            self.assertRaises(SCMError,
                              lambda: tool.get_file(filename, HEAD));

        for local_site_name in ('site-1',):
            local_site = LocalSite(name=local_site_name)
            local_site.save()

            repo = Repository(name='SSH Test', path=repo_path, tool=tool_class,
                              local_site=local_site)
            tool = repo.get_scmtool()

            self.assertEqual(sshutils.get_ssh_dir(local_site_name),
                             os.path.join(sshdir, local_site_name))
            sshutils.import_user_key(user_key, local_site_name)
            self.assertEqual(sshutils.get_user_key(local_site_name), user_key)

            # Make sure we can verify the repository and access files.
            tool.check_repository(repo_path, local_site_name=local_site_name)

            if filename:
                self.assertNotEqual(tool.get_file(filename, HEAD), None)


class CoreTests(DjangoTestCase):
    """Tests for the scmtools.core module"""

    def testInterface(self):
        """Testing basic scmtools.core API"""

        # Empty changeset
        cs = ChangeSet()
        self.assertEqual(cs.changenum, None)
        self.assertEqual(cs.summary, '')
        self.assertEqual(cs.description, '')
        self.assertEqual(cs.branch, '')
        self.assert_(len(cs.bugs_closed) == 0)
        self.assert_(len(cs.files) == 0)


class SSHUtilsTests(SCMTestCase):
    """Unit tests for sshutils."""
    def setUp(self):
        super(SSHUtilsTests, self).setUp()

        self.tempdir = tempfile.mkdtemp(prefix='rb-tests-home-')

    def test_get_ssh_dir_with_dot_ssh(self):
        """Testing sshutils.get_ssh_dir with ~/.ssh"""
        self._set_home(self.tempdir)
        sshdir = os.path.join(self.tempdir, '.ssh')
        self.assertEqual(sshutils.get_ssh_dir(), sshdir)

    def test_get_ssh_dir_with_ssh(self):
        """Testing sshutils.get_ssh_dir with ~/ssh"""
        self._set_home(self.tempdir)
        sshdir = os.path.join(self.tempdir, 'ssh')
        os.mkdir(sshdir, 0700)
        self.assertEqual(sshutils.get_ssh_dir(), sshdir)

    def test_get_ssh_dir_with_dot_ssh_and_localsite(self):
        """Testing sshutils.get_ssh_dir with ~/.ssh and localsite"""
        self._set_home(self.tempdir)
        sshdir = os.path.join(self.tempdir, '.ssh', 'site-1')
        self.assertEqual(sshutils.get_ssh_dir(local_site_name='site-1'), sshdir)

    def test_get_ssh_dir_with_ssh_and_localsite(self):
        """Testing sshutils.get_ssh_dir with ~/ssh and localsite"""
        self._set_home(self.tempdir)
        sshdir = os.path.join(self.tempdir, 'ssh')
        os.mkdir(sshdir, 0700)
        sshdir = os.path.join(sshdir, 'site-1')
        self.assertEqual(sshutils.get_ssh_dir(local_site_name='site-1'), sshdir)

    def test_generate_user_key(self, local_site_name=None):
        """Testing sshutils.generate_user_key"""
        self._set_home(self.tempdir)
        key = sshutils.generate_user_key(local_site_name)
        key_file = os.path.join(sshutils.get_ssh_dir(local_site_name), 'id_rsa')
        self.assertTrue(os.path.exists(key_file))
        self.assertEqual(sshutils.get_user_key(local_site_name), key)

    def test_generate_user_key_with_localsite(self):
        """Testing sshutils.generate_user_key with localsite"""
        self.test_generate_user_key('site-1')

    def test_add_host_key(self, local_site_name=None):
        """Testing sshutils.add_host_key"""
        self._set_home(self.tempdir)
        key = paramiko.RSAKey.generate(2048)
        sshutils.add_host_key('example.com', key, local_site_name)

        known_hosts_file = sshutils.get_host_keys_filename(local_site_name)
        self.assertTrue(os.path.exists(known_hosts_file))

        f = open(known_hosts_file, 'r')
        lines = f.readlines()
        f.close()

        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0].split(),
                         ['example.com', key.get_name(), key.get_base64()])

    def test_add_host_key_with_localsite(self):
        """Testing sshutils.add_host_key with localsite"""
        self.test_add_host_key('site-1')

    def test_replace_host_key(self, local_site_name=None):
        """Testing sshutils.replace_host_key"""
        self._set_home(self.tempdir)
        key = paramiko.RSAKey.generate(2048)
        sshutils.add_host_key('example.com', key, local_site_name)

        new_key = paramiko.RSAKey.generate(2048)
        sshutils.replace_host_key('example.com', key, new_key, local_site_name)

        known_hosts_file = sshutils.get_host_keys_filename(local_site_name)
        self.assertTrue(os.path.exists(known_hosts_file))

        f = open(known_hosts_file, 'r')
        lines = f.readlines()
        f.close()

        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0].split(),
                         ['example.com', new_key.get_name(),
                          new_key.get_base64()])

    def test_replace_host_key_with_localsite(self):
        """Testing sshutils.replace_host_key with localsite"""
        self.test_replace_host_key('site-1')


class BZRTests(SCMTestCase):
    """Unit tests for bzr."""
    fixtures = ['test_scmtools.json']

    def setUp(self):
        super(BZRTests, self).setUp()

        self.bzr_repo_path = os.path.join(os.path.dirname(__file__),
                                          'testdata', 'bzr_repo')
        self.bzr_ssh_path = 'bzr+ssh://localhost/%s' % \
                            self.bzr_repo_path.replace('\\', '/')
        self.bzr_sftp_path = 'sftp://localhost/%s' % \
                             self.bzr_repo_path.replace('\\', '/')
        self.repository = Repository(name='Bazaar',
                                     path='file://' + self.bzr_repo_path,
                                     tool=Tool.objects.get(name='Bazaar'))

        try:
            self.tool = self.repository.get_scmtool()
        except ImportError:
            raise nose.SkipTest('bzrlib is not installed')

    def test_ssh(self):
        """Testing a SSH-backed bzr repository"""
        self._test_ssh(self.bzr_ssh_path, 'README')

    def test_ssh_with_site(self):
        """Testing a SSH-backed bzr repository with a LocalSite"""
        self._test_ssh_with_site(self.bzr_ssh_path, 'README')

    def test_sftp(self):
        """Testing a SFTP-backed bzr repository"""
        self._test_ssh(self.bzr_sftp_path, 'README')


class CVSTests(SCMTestCase):
    """Unit tests for CVS."""
    fixtures = ['test_scmtools.json']

    def setUp(self):
        super(CVSTests, self).setUp()

        self.cvs_repo_path = os.path.join(os.path.dirname(__file__),
                                          'testdata/cvs_repo')
        self.cvs_ssh_path = ':ext:localhost:%s' % \
                            self.cvs_repo_path.replace('\\', '/')
        self.repository = Repository(name='CVS',
                                     path=self.cvs_repo_path,
                                     tool=Tool.objects.get(name='CVS'))

        try:
            self.tool = self.repository.get_scmtool()
        except ImportError:
            raise nose.SkipTest('cvs binary not found')

    def testPathWithPort(self):
        """Testing parsing a CVSROOT with a port"""
        repo = Repository(name="CVS",
                          path="example.com:123/cvsroot/test",
                          username="anonymous",
                          tool=Tool.objects.get(name="CVS"))
        tool = repo.get_scmtool()

        self.assertEqual(tool.repopath, "/cvsroot/test")
        self.assertEqual(tool.client.cvsroot,
                         ":pserver:anonymous@example.com:123/cvsroot/test")

    def testPathWithoutPort(self):
        """Testing parsing a CVSROOT without a port"""
        repo = Repository(name="CVS",
                          path="example.com:/cvsroot/test",
                          username="anonymous",
                          tool=Tool.objects.get(name="CVS"))
        tool = repo.get_scmtool()

        self.assertEqual(tool.repopath, "/cvsroot/test")
        self.assertEqual(tool.client.cvsroot,
                         ":pserver:anonymous@example.com:/cvsroot/test")

    def testGetFile(self):
        """Testing CVSTool.get_file"""
        expected = "test content\n"
        file = 'test/testfile'
        rev = Revision('1.1')
        badrev = Revision('2.1')

        self.assertEqual(self.tool.get_file(file, rev), expected)
        self.assertEqual(self.tool.get_file(file + ",v", rev), expected)
        self.assertEqual(self.tool.get_file(self.tool.repopath + '/' +
                                            file + ",v", rev), expected)

        self.assert_(self.tool.file_exists('test/testfile'))
        self.assert_(self.tool.file_exists(self.tool.repopath +
                                           '/test/testfile'))
        self.assert_(self.tool.file_exists('test/testfile,v'))
        self.assert_(not self.tool.file_exists('test/testfile2'))
        self.assert_(not self.tool.file_exists(self.tool.repopath +
                                               '/test/testfile2'))
        self.assert_(not self.tool.file_exists('test/testfile2,v'))
        self.assert_(not self.tool.file_exists('test/testfile', badrev))

        self.assertRaises(FileNotFoundError,
                          lambda: self.tool.get_file(''))
        self.assertRaises(FileNotFoundError,
                          lambda: self.tool.get_file('hello', PRE_CREATION))

    def testRevisionParsing(self):
        """Testing revision number parsing"""
        self.assertEqual(self.tool.parse_diff_revision('', 'PRE-CREATION')[1],
                         PRE_CREATION)
        self.assertEqual(self.tool.parse_diff_revision('', '7 Nov 2005 13:17:07 -0000	1.2')[1],
                         '1.2')
        self.assertEqual(self.tool.parse_diff_revision('', '7 Nov 2005 13:17:07 -0000	1.2.3.4')[1],
                         '1.2.3.4')
        self.assertRaises(SCMError,
                          lambda: self.tool.parse_diff_revision('', 'hello'))

    def testInterface(self):
        """Testing basic CVSTool API"""
        self.assertEqual(self.tool.get_diffs_use_absolute_paths(), True)
        self.assertEqual(self.tool.get_fields(), ['diff_path'])

    def testSimpleDiff(self):
        """Testing parsing CVS simple diff"""
        diff = "Index: testfile\n==========================================" + \
               "=========================\nRCS file: %s/test/testfile,v\nre" + \
               "trieving revision 1.1.1.1\ndiff -u -r1.1.1.1 testfile\n--- " + \
               "testfile    26 Jul 2007 08:50:30 -0000      1.1.1.1\n+++ te" + \
               "stfile    26 Jul 2007 10:20:20 -0000\n@@ -1 +1,2 @@\n-test " + \
               "content\n+updated test content\n+added info\n"
        diff = diff % self.cvs_repo_path

        file = self.tool.get_parser(diff).parse()[0]
        self.assertEqual(file.origFile, 'test/testfile')
        self.assertEqual(file.origInfo, '26 Jul 2007 08:50:30 -0000      1.1.1.1')
        self.assertEqual(file.newFile, 'testfile')
        self.assertEqual(file.newInfo, '26 Jul 2007 10:20:20 -0000')
        self.assertEqual(file.data, diff)

    def testBadDiff(self):
        """Testing parsing CVS diff with bad info"""
        diff = "Index: newfile\n===========================================" + \
               "========================\ndiff -N newfile\n--- /dev/null	1" + \
               "Jan 1970 00:00:00 -0000\n+++ newfile	26 Jul 2007 10:11:45 " + \
               "-0000\n@@ -0,0 +1 @@\n+new file content"

        self.assertRaises(DiffParserError,
                          lambda: self.tool.get_parser(diff).parse())

    def testBadDiff2(self):
        """Testing parsing CVS bad diff with new file"""
        diff = "Index: newfile\n===========================================" + \
               "========================\nRCS file: newfile\ndiff -N newfil" + \
               "e\n--- /dev/null\n+++ newfile	2" + \
               "6 Jul 2007 10:11:45 -0000\n@@ -0,0 +1 @@\n+new file content"

        self.assertRaises(DiffParserError,
                          lambda: self.tool.get_parser(diff).parse())

    def testNewfileDiff(self):
        """Testing parsing CVS diff with new file"""
        diff = "Index: newfile\n===========================================" + \
               "========================\nRCS file: newfile\ndiff -N newfil" + \
               "e\n--- /dev/null	1 Jan 1970 00:00:00 -0000\n+++ newfile	2" + \
               "6 Jul 2007 10:11:45 -0000\n@@ -0,0 +1 @@\n+new file content\n"

        file = self.tool.get_parser(diff).parse()[0]
        self.assertEqual(file.origFile, 'newfile')
        self.assertEqual(file.origInfo, 'PRE-CREATION')
        self.assertEqual(file.newFile, 'newfile')
        self.assertEqual(file.newInfo, '26 Jul 2007 10:11:45 -0000')
        self.assertEqual(file.data, diff)

    def testInterRevisionDiff(self):
        """Testing parsing CVS inter-revision diff"""
        diff = "Index: testfile\n==========================================" + \
               "=========================\nRCS file: %s/test/testfile,v\nre" + \
               "trieving revision 1.1\nretrieving revision 1.2\ndiff -u -p " + \
               "-r1.1 -r1.2\n--- testfile    26 Jul 2007 08:50:30 -0000    " + \
               "  1.1\n+++ testfile    27 Sep 2007 22:57:16 -0000      1.2"  + \
               "\n@@ -1 +1,2 @@\n-test content\n+updated test content\n+add" + \
               "ed info\n"
        diff = diff % self.cvs_repo_path

        file = self.tool.get_parser(diff).parse()[0]
        self.assertEqual(file.origFile, 'test/testfile')
        self.assertEqual(file.origInfo, '26 Jul 2007 08:50:30 -0000      1.1')
        self.assertEqual(file.newFile, 'testfile')
        self.assertEqual(file.newInfo, '27 Sep 2007 22:57:16 -0000      1.2')
        self.assertEqual(file.data, diff)

    def testBadRoot(self):
        """Testing a bad CVSROOT"""
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


class SubversionTests(SCMTestCase):
    """Unit tests for subversion."""
    fixtures = ['test_scmtools.json']

    def setUp(self):
        super(SubversionTests, self).setUp()

        self.svn_repo_path = os.path.join(os.path.dirname(__file__),
                                          'testdata/svn_repo')
        self.svn_ssh_path = 'svn+ssh://localhost/%s' % \
                            self.svn_repo_path.replace('\\', '/')
        self.repository = Repository(name='Subversion SVN',
                                     path='file://' + self.svn_repo_path,
                                     tool=Tool.objects.get(name='Subversion'))

        try:
            self.tool = self.repository.get_scmtool()
        except ImportError:
            raise nose.SkipTest('pysvn is not installed')

    def test_ssh(self):
        """Testing a SSH-backed Subversion repository"""
        self._test_ssh(self.svn_ssh_path, 'trunk/doc/misc-docs/Makefile')

    def test_ssh_with_site(self):
        """Testing a SSH-backed Subversion repository with a LocalSite"""
        self._test_ssh_with_site(self.svn_ssh_path,
                                 'trunk/doc/misc-docs/Makefile')

    def testGetFile(self):
        """Testing SVNTool.get_file"""
        expected = 'include ../tools/Makefile.base-vars\nNAME = misc-docs\n' + \
                   'OUTNAME = svn-misc-docs\nINSTALL_DIR = $(DESTDIR)/usr/s' + \
                   'hare/doc/subversion\ninclude ../tools/Makefile.base-rul' + \
                   'es\n'

        # There are 3 versions of this test in order to get 100% coverage of
        # the svn module.
        rev = Revision('2')
        file = 'trunk/doc/misc-docs/Makefile'

        self.assertEqual(self.tool.get_file(file, rev), expected)

        self.assertEqual(self.tool.get_file('/' + file, rev), expected)

        self.assertEqual(self.tool.get_file(self.repository.path + '/' + file, rev),
                         expected)


        self.assert_(self.tool.file_exists('trunk/doc/misc-docs/Makefile'))
        self.assert_(not self.tool.file_exists('trunk/doc/misc-docs/Makefile2'))

        self.assertRaises(FileNotFoundError,
                          lambda: self.tool.get_file(''))

        self.assertRaises(FileNotFoundError,
                          lambda: self.tool.get_file('hello',
                                                     PRE_CREATION))

    def testRevisionParsing(self):
        """Testing revision number parsing"""
        self.assertEqual(self.tool.parse_diff_revision('', '(working copy)')[1],
                         HEAD)
        self.assertEqual(self.tool.parse_diff_revision('', '   (revision 0)')[1],
                         PRE_CREATION)

        self.assertEqual(self.tool.parse_diff_revision('', '(revision 1)')[1],
                         '1')
        self.assertEqual(self.tool.parse_diff_revision('', '(revision 23)')[1],
                         '23')

        self.assertEqual(self.tool.parse_diff_revision('',
            '2007-06-06 15:32:23 UTC (rev 10958)')[1], '10958')

        self.assertRaises(SCMError,
                          lambda: self.tool.parse_diff_revision('', 'hello'))

    def testInterface(self):
        """Testing basic SVNTool API"""
        self.assertEqual(self.tool.get_diffs_use_absolute_paths(), False)

        self.assertRaises(NotImplementedError,
                          lambda: self.tool.get_changeset(1))

        self.assertRaises(NotImplementedError,
                          lambda: self.tool.get_pending_changesets(1))

    def testBinaryDiff(self):
        """Testing parsing SVN diff with binary file"""
        diff = "Index: binfile\n===========================================" + \
               "========================\nCannot display: file marked as a " + \
               "binary type.\nsvn:mime-type = application/octet-stream\n"

        file = self.tool.get_parser(diff).parse()[0]
        self.assertEqual(file.origFile, 'binfile')
        self.assertEqual(file.binary, True)

    def testKeywordDiff(self):
        """Testing parsing SVN diff with keywords"""
        # 'svn cat' will expand special variables in svn:keywords,
        # but 'svn diff' doesn't expand anything.  This causes the
        # patch to fail if those variables appear in the patch context.
        diff = "Index: Makefile\n" \
               "===========================================================" \
               "========\n" \
               "--- Makefile    (revision 4)\n" \
               "+++ Makefile    (working copy)\n" \
               "@@ -1,6 +1,7 @@\n" \
               " # $Id$\n" \
               " # $Rev$\n" \
               " # $Revision::     $\n" \
               "+# foo\n" \
               " include ../tools/Makefile.base-vars\n" \
               " NAME = misc-docs\n" \
               " OUTNAME = svn-misc-docs\n"

        filename = 'trunk/doc/misc-docs/Makefile'
        rev = Revision('4')
        file = self.tool.get_file(filename, rev)
        patch(diff, file, filename)

    def testUnterminatedKeywordDiff(self):
        """Testing parsing SVN diff with unterminated keywords"""
        diff = "Index: Makefile\n" \
               "===========================================================" \
               "========\n" \
               "--- Makefile    (revision 4)\n" \
               "+++ Makefile    (working copy)\n" \
               "@@ -1,6 +1,7 @@\n" \
               " # $Id$\n" \
               " # $Id:\n" \
               " # $Rev$\n" \
               " # $Revision::     $\n" \
               "+# foo\n" \
               " include ../tools/Makefile.base-vars\n" \
               " NAME = misc-docs\n" \
               " OUTNAME = svn-misc-docs\n"

        filename = 'trunk/doc/misc-docs/Makefile'
        rev = Revision('5')
        file = self.tool.get_file(filename, rev)
        patch(diff, file, filename)


class PerforceTests(SCMTestCase):
    """Unit tests for perforce.

       This uses the open server at public.perforce.com to test various
       pieces.  Because we have no control over things like pending
       changesets, not everything can be tested.
       """
    fixtures = ['test_scmtools.json']

    def setUp(self):
        super(PerforceTests, self).setUp()

        self.repository = Repository(name='Perforce.com',
                                     path='public.perforce.com:1666',
                                     tool=Tool.objects.get(name='Perforce'))

        try:
            self.tool = self.repository.get_scmtool()
        except ImportError:
            raise nose.SkipTest('perforce/p4python is not installed')

    def testChangeset(self):
        """Testing PerforceTool.get_changeset"""

        try:
            desc = self.tool.get_changeset(157)
        except P4Error, e:
            if str(e).startswith('Connect to server failed'):
                raise nose.SkipTest(
                    'Connection to public.perforce.com failed.  No internet?')
            else:
                raise
        self.assertEqual(desc.changenum, 157)
        self.assertEqual(md5(desc.description).hexdigest(),
                         'b7eff0ca252347cc9b09714d07397e64')

        expected_files = [
            '//public/perforce/api/python/P4Client/P4Clientmodule.cc',
            '//public/perforce/api/python/P4Client/p4.py',
            '//public/perforce/api/python/P4Client/review.py',
            '//public/perforce/python/P4Client/P4Clientmodule.cc',
            '//public/perforce/python/P4Client/p4.py',
            '//public/perforce/python/P4Client/review.py',
        ]
        for file, expected in map(None, desc.files, expected_files):
            self.assertEqual(file, expected)

        self.assertEqual(md5(desc.summary).hexdigest(),
                         '99a335676b0e5821ffb2f7469d4d7019')

    def testChangesetBroken(self):
        """Testing PerforceTool.get_changeset error conditions"""
        repo = Repository(name='Perforce.com',
                          path='public.perforce.com:1666',
                          tool=Tool.objects.get(name='Perforce'),
                          username='samwise',
                          password='bogus')
        tool = repo.get_scmtool()
        self.assertRaises(AuthenticationError,
                          lambda: tool.get_changeset(157))

        repo = Repository(name='localhost:1',
                          path='localhost:1',
                          tool=Tool.objects.get(name='Perforce'))

        tool = repo.get_scmtool()
        self.assertRaises(RepositoryNotFoundError,
                          lambda: tool.get_changeset(1))

    def testGetFile(self):
        """Testing PerforceTool.get_file"""

        file = self.tool.get_file('//depot/foo', PRE_CREATION)
        self.assertEqual(file, '')

        try:
            file = self.tool.get_file('//public/perforce/api/python/P4Client/p4.py', 1)
        except Exception, e:
            if str(e).startswith('Connect to server failed'):
                raise nose.SkipTest(
                    'Connection to public.perforce.com failed.  No internet?')
            else:
                raise
        self.assertEqual(md5(file).hexdigest(),
                         '227bdd87b052fcad9369e65c7bf23fd0')

    def testEmptyDiff(self):
        """Testing Perforce empty diff parsing"""
        diff = "==== //depot/foo/proj/README#2 ==M== /src/proj/README ====\n"

        file = self.tool.get_parser(diff).parse()[0]
        self.assertEqual(file.origFile, '//depot/foo/proj/README')
        self.assertEqual(file.origInfo, '//depot/foo/proj/README#2')
        self.assertEqual(file.newFile, '/src/proj/README')
        self.assertEqual(file.newInfo, '')
        self.assertFalse(file.binary)
        self.assertFalse(file.deleted)
        self.assertEqual(file.data, '')

    def testBinaryDiff(self):
        """Testing Perforce binary diff parsing"""
        diff = "==== //depot/foo/proj/test.png#1 ==A== /src/proj/test.png " + \
               "====\nBinary files /tmp/foo and /src/proj/test.png differ\n"

        file = self.tool.get_parser(diff).parse()[0]
        self.assertEqual(file.origFile, '//depot/foo/proj/test.png')
        self.assertEqual(file.origInfo, '//depot/foo/proj/test.png#1')
        self.assertEqual(file.newFile, '/src/proj/test.png')
        self.assertEqual(file.newInfo, '')
        self.assertEqual(file.data, '')
        self.assertTrue(file.binary)
        self.assertFalse(file.deleted)

    def testDeletedDiff(self):
        """Testing Perforce deleted diff parsing"""
        diff = "==== //depot/foo/proj/test.png#1 ==D== /src/proj/test.png " + \
               "====\n"

        file = self.tool.get_parser(diff).parse()[0]
        self.assertEqual(file.origFile, '//depot/foo/proj/test.png')
        self.assertEqual(file.origInfo, '//depot/foo/proj/test.png#1')
        self.assertEqual(file.newFile, '/src/proj/test.png')
        self.assertEqual(file.newInfo, '')
        self.assertEqual(file.data, '')
        self.assertFalse(file.binary)
        self.assertTrue(file.deleted)

    def testEmptyAndNormalDiffs(self):
        """Testing Perforce empty and normal diff parsing"""
        diff1_text = "==== //depot/foo/proj/test.png#1 ==A== " + \
                     "/src/proj/test.png ====\n"
        diff2_text = "--- test.c  //depot/foo/proj/test.c#2\n" + \
                     "+++ test.c  01-02-03 04:05:06\n" + \
                     "@@ -1 +1,2 @@\n" + \
                     "-test content\n" + \
                     "+updated test content\n" + \
                     "+added info\n"
        diff = diff1_text + diff2_text

        files = self.tool.get_parser(diff).parse()
        self.assertEqual(len(files), 2)
        self.assertEqual(files[0].origFile, '//depot/foo/proj/test.png')
        self.assertEqual(files[0].origInfo, '//depot/foo/proj/test.png#1')
        self.assertEqual(files[0].newFile, '/src/proj/test.png')
        self.assertEqual(files[0].newInfo, '')
        self.assertFalse(files[0].binary)
        self.assertFalse(files[0].deleted)
        self.assertEqual(files[0].data, '')

        self.assertEqual(files[1].origFile, 'test.c')
        self.assertEqual(files[1].origInfo, '//depot/foo/proj/test.c#2')
        self.assertEqual(files[1].newFile, 'test.c')
        self.assertEqual(files[1].newInfo, '01-02-03 04:05:06')
        self.assertFalse(files[1].binary)
        self.assertFalse(files[1].deleted)
        self.assertEqual(files[1].data, diff2_text)


class PerforceStunnelTests(SCMTestCase):
    """
    Unit tests for perforce running through stunnel.

    Out of the box, Perforce doesn't support any kind of encryption on its
    connections. The recommended setup in this case is to run an stunnel server
    on the perforce server which bounces SSL connections to the normal p4 port.
    One can then start an stunnel on their client machine and connect via a
    localhost: P4PORT.

    For these tests, we set up an stunnel server which will accept secure
    connections and proxy (insecurely) to the public perforce server. We can
    then tell the Perforce SCMTool to connect securely to localhost.
    """
    fixtures = ['test_scmtools.json']

    def setUp(self):
        super(PerforceStunnelTests, self).setUp()

        if not is_exe_in_path('stunnel'):
            raise nose.SkipTest('stunnel is not installed')

        cert = os.path.join(os.path.dirname(__file__),
                            'testdata', 'stunnel.pem')
        self.proxy = STunnelProxy(STUNNEL_SERVER, 'public.perforce.com:1666')
        self.proxy.start_server(cert)

        # Find an available port to listen on
        path = 'stunnel:localhost:%d' % self.proxy.port

        self.repository = Repository(name='Perforce.com - secure',
                                     path=path,
                                     tool=Tool.objects.get(name='Perforce'))
        try:
            self.tool = self.repository.get_scmtool()
            self.tool.use_stunnel = True
        except ImportError:
            raise nose.SkipTest('perforce/p4python is not installed')


    def tearDown(self):
        self.proxy.shutdown()

    def testChangeset(self):
        """Testing PerforceTool.get_changeset with stunnel"""
        desc = self.tool.get_changeset(157)

        self.assertEqual(desc.changenum, 157)
        self.assertEqual(md5(desc.description).hexdigest(),
                         'b7eff0ca252347cc9b09714d07397e64')

        expected_files = [
            '//public/perforce/api/python/P4Client/P4Clientmodule.cc',
            '//public/perforce/api/python/P4Client/p4.py',
            '//public/perforce/api/python/P4Client/review.py',
            '//public/perforce/python/P4Client/P4Clientmodule.cc',
            '//public/perforce/python/P4Client/p4.py',
            '//public/perforce/python/P4Client/review.py',
        ]
        for file, expected in map(None, desc.files, expected_files):
            self.assertEqual(file, expected)

        self.assertEqual(md5(desc.summary).hexdigest(),
                         '99a335676b0e5821ffb2f7469d4d7019')

    def testGetFile(self):
        """Testing PerforceTool.get_file with stunnel"""
        file = self.tool.get_file('//depot/foo', PRE_CREATION)
        self.assertEqual(file, '')

        try:
            file = self.tool.get_file('//public/perforce/api/python/P4Client/p4.py', 1)
        except Exception, e:
            if str(e).startswith('Connect to server failed'):
                raise nose.SkipTest(
                    'Connection to public.perforce.com failed.  No internet?')
            else:
                raise
        self.assertEqual(md5(file).hexdigest(),
                         '227bdd87b052fcad9369e65c7bf23fd0')


class VMWareTests(SCMTestCase):
    """Tests for VMware specific code"""
    fixtures = ['vmware.json', 'test_scmtools.json']

    def setUp(self):
        super(VMWareTests, self).setUp()

        self.repository = Repository(name='VMware Test',
                                     path='perforce.eng.vmware.com:1666',
                                     tool=Tool.objects.get(name='VMware Perforce'))

        try:
            self.tool = self.repository.get_scmtool()
        except ImportError:
            raise nose.SkipTest('perforce/p4python is not installed')

#    TODO: Re-enable when we find a way to feed strings into the new p4python.
#    def testParse(self):
#        """Testing VMware changeset parsing"""
#
#        file = open(os.path.join(os.path.dirname(__file__), 'testdata',
#                                 'vmware.changeset'), 'r')
#        data = file.read()
#        file.close()
#
#        changeset = self.tool.parse_change_desc(data, 123456)
#        self.assertEqual(changeset.summary, "Emma")
#        self.assertEqual(hash(changeset.description), 315618127)
#        self.assertEqual(changeset.changenum, 123456)
#        self.assertEqual(hash(changeset.testing_done), 1030854806)
#
#        self.assertEqual(len(changeset.bugs_closed), 1)
#        self.assertEqual(changeset.bugs_closed[0], '128700')
#
#        expected_files = [
#            '//depot/bora/hosted07-rel/foo.cc',
#            '//depot/bora/hosted07-rel/foo.hh',
#            '//depot/bora/hosted07-rel/bar.cc',
#            '//depot/bora/hosted07-rel/bar.hh',
#        ]
#        for file, expected in map(None, changeset.files, expected_files):
#            self.assertEqual(file, expected)
#
#        self.assertEqual(changeset.branch,
#                         'hosted07-rel &rarr; hosted07 &rarr; bfg-main (manual)')
#
#
#    def testParseSingleLineDesc(self):
#        """Testing VMware changeset parsing with a single line description."""
#        file = open(os.path.join(os.path.dirname(__file__), 'testdata',
#                                 'vmware-single-line-desc.changeset'), 'r')
#        data = file.read()
#        file.close()
#
#        changeset = self.tool.parse_change_desc(data, 1234567)
#        self.assertEqual(changeset.summary,
#                         "There is only a single line in this changeset description.")
#        self.assertEqual(changeset.description,
#                         "There is only a single line in this changeset description.")
#        self.assertEqual(changeset.changenum, 1234567)
#        self.assertEqual(changeset.testing_done, "")
#
#        self.assertEqual(len(changeset.bugs_closed), 0)
#
#        expected_files = [
#            '//depot/qa/foo/bar',
#        ]
#        for file, expected in map(None, changeset.files, expected_files):
#            self.assertEqual(file, expected)
#
#    def testParseMultiLineSummary(self):
#        """Testing VMware changeset parsing with a summary spanning multiple lines."""
#        file = open(os.path.join(os.path.dirname(__file__), 'testdata',
#                                 'vmware-phil-is-crazy.changeset'), 'r')
#        data = file.read()
#        file.close()
#
#        changeset = self.tool.parse_change_desc(data, 123456)
#        self.assertEqual(changeset.summary, "Changes: Emma")
#
#        self.assertEqual(changeset.branch, 'bfg-main')


class MercurialTests(SCMTestCase):
    """Unit tests for mercurial."""
    fixtures = ['test_scmtools.json']

    def setUp(self):
        super(MercurialTests, self).setUp()

        hg_repo_path = os.path.join(os.path.dirname(__file__),
                                    'testdata/hg_repo.bundle')
        self.repository = Repository(name='Test HG',
                                     path=hg_repo_path,
                                     tool=Tool.objects.get(name='Mercurial'))

        try:
            self.tool = self.repository.get_scmtool()
        except ImportError:
            raise nose.SkipTest('Hg is not installed')

    def _firstFileInDiff(self, diff):
        return self.tool.get_parser(diff).parse()[0]

    def testPatchCreatesNewFile(self):
        """Testing HgTool with a patch that creates a new file"""

        self.assertEqual(PRE_CREATION,
            self.tool.parse_diff_revision("/dev/null", "bf544ea505f8")[1])

    def testDiffParserNewFile(self):
        """Testing HgDiffParser with a diff that creates a new file"""

        diffContents = 'diff -r bf544ea505f8 readme\n' + \
                       '--- /dev/null\n' + \
                       '+++ b/readme\n'

        file = self._firstFileInDiff(diffContents)
        self.assertEqual(file.origFile, "readme")

    def testDiffParserUncommitted(self):
        """Testing HgDiffParser with a diff with an uncommitted change"""

        diffContents = 'diff -r bf544ea505f8 readme\n' + \
                       '--- a/readme\n' + \
                       '+++ b/readme\n'

        file = self._firstFileInDiff(diffContents)
        self.assertEqual(file.origInfo, "bf544ea505f8")
        self.assertEqual(file.origFile, "readme")
        self.assertEqual(file.newInfo, "Uncommitted")
        self.assertEqual(file.newFile, "readme")

    def testDiffParserCommitted(self):
        """Testing HgDiffParser with a diff between committed revisions"""

        diffContents = 'diff -r 356a6127ef19 -r 4960455a8e88 readme\n' + \
                       '--- a/readme\n' + \
                       '+++ b/readme\n'

        file = self._firstFileInDiff(diffContents)
        self.assertEqual(file.origInfo, "356a6127ef19")
        self.assertEqual(file.origFile, "readme")
        self.assertEqual(file.newInfo, "4960455a8e88")
        self.assertEqual(file.newFile, "readme")

    def testDiffParserWithPreambleJunk(self):
        """Testing HgDiffParser with a diff that contains non-diff junk test as a preamble"""

        diffContents = 'changeset:   60:3613c58ad1d5\n' + \
                       'user:        Michael Rowe <mrowe@mojain.com>\n' + \
                       'date:        Fri Jul 27 11:44:37 2007 +1000\n' + \
                       'files:       readme\n' + \
                       'description:\n' + \
                       'Update the readme file\n' + \
                       '\n' + \
                       '\n' + \
                       'diff -r 356a6127ef19 -r 4960455a8e88 readme\n' + \
                       '--- a/readme\n' + \
                       '+++ b/readme\n'

        file = self._firstFileInDiff(diffContents)
        self.assertEqual(file.origInfo, "356a6127ef19")
        self.assertEqual(file.origFile, "readme")
        self.assertEqual(file.newInfo, "4960455a8e88")
        self.assertEqual(file.newFile, "readme")

    def testRevisionParsing(self):
        """Testing HgDiffParser revision number parsing"""

        self.assertEqual(self.tool.parse_diff_revision('doc/readme', 'bf544ea505f8'),
                         ('doc/readme', 'bf544ea505f8'))

        self.assertEqual(self.tool.parse_diff_revision('/dev/null', 'bf544ea505f8'),
                         ('/dev/null', PRE_CREATION))

        # TODO think of a meaningful thing to test here...
        # self.assertRaises(SCMException,
        #                  lambda: self.tool.parse_diff_revision('', 'hello'))

    def testGetFile(self):
        """Testing HgTool.get_file"""

        rev = Revision('661e5dd3c493')
        file = 'doc/readme'

        self.assertEqual(self.tool.get_file(file, rev), 'Hello\n\ngoodbye\n')

        self.assert_(self.tool.file_exists('doc/readme'))
        self.assert_(not self.tool.file_exists('doc/readme2'))

        self.assertRaises(FileNotFoundError, lambda: self.tool.get_file(''))

        self.assertRaises(FileNotFoundError,
                          lambda: self.tool.get_file('hello', PRE_CREATION))

    def testInterface(self):
        """Testing basic HgTool API"""
        self.assert_(self.tool.get_diffs_use_absolute_paths())

        self.assertRaises(NotImplementedError,
                          lambda: self.tool.get_changeset(1))

        self.assertRaises(NotImplementedError,
                          lambda: self.tool.get_pending_changesets(1))

        self.assertEqual(self.tool.get_fields(),
                         ['diff_path', 'parent_diff_path'])

    def test_https_repo(self):
        """Testing HgTool.get_file with an HTTPS-based repository"""
        repo = Repository(name='Test HG2',
                          path='https://bitbucket.org/pypy/pypy',
                          tool=Tool.objects.get(name='Mercurial'))
        tool = repo.get_scmtool()

        rev = Revision('877cf1960916')

        self.assert_(tool.file_exists('TODO.rst', rev))
        self.assert_(not tool.file_exists('TODO.rstNotFound', rev))


class GitTests(SCMTestCase):
    """Unit tests for Git."""
    fixtures = ['test_scmtools.json']

    def setUp(self):
        super(GitTests, self).setUp()

        tool = Tool.objects.get(name='Git')

        self.local_repo_path = os.path.join(os.path.dirname(__file__),
                                           'testdata', 'git_repo')
        self.git_ssh_path = 'localhost:%s' % \
                            self.local_repo_path.replace('\\', '/')
        remote_repo_path = 'git@github.com:reviewboard/reviewboard.git'
        remote_repo_raw_url = 'http://github.com/api/v2/yaml/blob/show/' \
                              'reviewboard/reviewboard/<revision>'


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

    def _readFixture(self, filename):
        return open( \
            os.path.join(os.path.dirname(__file__), 'testdata', filename), \
            'r').read()

    def _getFileInDiff(self, diff, filenum=0):
        return self.tool.get_parser(diff).parse()[filenum]

    def test_ssh(self):
        """Testing a SSH-backed git repository"""
        self._test_ssh(self.git_ssh_path)

    def test_ssh_with_site(self):
        """Testing a SSH-backed git repository with a LocalSite"""
        self._test_ssh_with_site(self.git_ssh_path)

    def testFilemodeDiff(self):
        """Testing parsing filemode changes Git diff"""
        diff = self._readFixture('git_filemode.diff')
        file = self._getFileInDiff(diff)
        self.assertEqual(file.origFile, 'testing')
        self.assertEqual(file.newFile, 'testing')
        self.assertEqual(file.origInfo, 'e69de29')
        self.assertEqual(file.newInfo, 'bcae657')
        self.assertFalse(file.binary)
        self.assertFalse(file.deleted)
        self.assertEqual(file.data.splitlines()[0],
                         "diff --git a/testing b/testing")
        self.assertEqual(file.data.splitlines()[-1], "+ADD")

    def testFilemodeWithFollowingDiff(self):
        """Testing parsing filemode changes with following Git diff"""
        diff = self._readFixture('git_filemode2.diff')
        file = self._getFileInDiff(diff)
        self.assertEqual(file.origFile, 'testing')
        self.assertEqual(file.newFile, 'testing')
        self.assertEqual(file.origInfo, 'e69de29')
        self.assertEqual(file.newInfo, 'bcae657')
        self.assertFalse(file.binary)
        self.assertFalse(file.deleted)
        self.assertEqual(file.data.splitlines()[0],
                         "diff --git a/testing b/testing")
        self.assertEqual(file.data.splitlines()[-1], "+ADD")
        file = self._getFileInDiff(diff, 1)
        self.assertEqual(file.origFile, 'cfg/testcase.ini')
        self.assertEqual(file.newFile, 'cfg/testcase.ini')
        self.assertEqual(file.origInfo, 'cc18ec8')
        self.assertEqual(file.newInfo, '5e70b73')
        self.assertEqual(file.data.splitlines()[0],
                        "diff --git a/cfg/testcase.ini b/cfg/testcase.ini")
        self.assertEqual(file.data.splitlines()[-1], '+db = pyunit')

    def testSimpleDiff(self):
        """Testing parsing simple Git diff"""
        diff = self._readFixture('git_simple.diff')
        file = self._getFileInDiff(diff)
        self.assertEqual(file.origFile, 'cfg/testcase.ini')
        self.assertEqual(file.newFile, 'cfg/testcase.ini')
        self.assertEqual(file.origInfo, 'cc18ec8')
        self.assertEqual(file.newInfo, '5e70b73')
        self.assertFalse(file.binary)
        self.assertFalse(file.deleted)
        self.assertEqual(len(file.data), 249)
        self.assertEqual(file.data.splitlines()[0],
                         "diff --git a/cfg/testcase.ini b/cfg/testcase.ini")
        self.assertEqual(file.data.splitlines()[-1], "+db = pyunit")

    def testNewfileDiff(self):
        """Testing parsing Git diff with new file"""
        diff = self._readFixture('git_newfile.diff')
        file = self._getFileInDiff(diff)
        self.assertEqual(file.origFile, 'IAMNEW')
        self.assertEqual(file.newFile, 'IAMNEW')
        self.assertEqual(file.origInfo, PRE_CREATION)
        self.assertEqual(file.newInfo, 'e69de29')
        self.assertFalse(file.binary)
        self.assertFalse(file.deleted)
        self.assertEqual(len(file.data), 124)
        self.assertEqual(file.data.splitlines()[0],
                         "diff --git a/IAMNEW b/IAMNEW")
        self.assertEqual(file.data.splitlines()[-1], "+Hello")

    def testNewfileNoContentDiff(self):
        """Testing parsing Git diff new file, no content"""
        diff = self._readFixture('git_newfile_nocontent.diff')
        files = self.tool.get_parser(diff).parse()
        self.assertEqual(len(files), 0)

    def testNewfileNoContentWithFollowingDiff(self):
        """Testing parsing Git diff new file, no content, with following"""
        diff = self._readFixture('git_newfile_nocontent2.diff')
        self.assertEqual(len(self.tool.get_parser(diff).parse()), 1)
        file = self._getFileInDiff(diff)
        self.assertEqual(file.origFile, 'cfg/testcase.ini')
        self.assertEqual(file.newFile, 'cfg/testcase.ini')
        self.assertEqual(file.origInfo, 'cc18ec8')
        self.assertEqual(file.newInfo, '5e70b73')
        self.assertEqual(file.data.splitlines()[0],
                        "diff --git a/cfg/testcase.ini b/cfg/testcase.ini")
        self.assertEqual(file.data.splitlines()[-1], '+db = pyunit')

    def testDelFileDiff(self):
        """Testing parsing Git diff with deleted file"""
        diff = self._readFixture('git_delfile.diff')
        file = self._getFileInDiff(diff)
        self.assertEqual(file.origFile, 'OLDFILE')
        self.assertEqual(file.newFile, 'OLDFILE')
        self.assertEqual(file.origInfo, '8ebcb01')
        self.assertEqual(file.newInfo, '0000000')
        self.assertFalse(file.binary)
        self.assertTrue(file.deleted)
        self.assertEqual(len(file.data), 132)
        self.assertEqual(file.data.splitlines()[0],
                         "diff --git a/OLDFILE b/OLDFILE")
        self.assertEqual(file.data.splitlines()[-1], "-Goodbye")

    def testBinaryDiff(self):
        """Testing parsing Git diff with binary"""
        diff = self._readFixture('git_binary.diff')
        file = self._getFileInDiff(diff)
        self.assertEqual(file.origFile, 'pysvn-1.5.1.tar.gz')
        self.assertEqual(file.newFile, 'pysvn-1.5.1.tar.gz')
        self.assertEqual(file.origInfo, PRE_CREATION)
        self.assertEqual(file.newInfo, '86b520c')
        self.assertTrue(file.binary)
        self.assertFalse(file.deleted)
        self.assertEqual(len(file.data), 97)
        self.assertEqual(file.data.splitlines()[0],
                         "diff --git a/pysvn-1.5.1.tar.gz b/pysvn-1.5.1.tar.gz")

    def testComplexDiff(self):
        """Testing parsing Git diff with existing and new files"""
        diff = self._readFixture('git_complex.diff')
        files = self.tool.get_parser(diff).parse()
        self.assertEqual(len(files), 6)
        self.assertEqual(files[0].origFile, 'cfg/testcase.ini')
        self.assertEqual(files[0].newFile, 'cfg/testcase.ini')
        self.assertEqual(files[0].origInfo, '5e35098')
        self.assertEqual(files[0].newInfo, 'e254ef4')
        self.assertFalse(files[0].binary)
        self.assertFalse(files[0].deleted)
        self.assertEqual(len(files[0].data), 549)
        self.assertEqual(files[0].data.splitlines()[0],
                         "diff --git a/cfg/testcase.ini b/cfg/testcase.ini")
        self.assertEqual(files[0].data.splitlines()[13],
                         "         if isinstance(value, basestring):")

        self.assertEqual(files[1].origFile, 'tests/tests.py')
        self.assertEqual(files[1].newFile, 'tests/tests.py')
        self.assertEqual(files[1].origInfo, PRE_CREATION)
        self.assertEqual(files[1].newInfo, 'e279a06')
        self.assertFalse(files[1].binary)
        self.assertFalse(files[1].deleted)
        self.assertEqual(len(files[1].data), 182)
        self.assertEqual(files[1].data.splitlines()[0],
                         "diff --git a/tests/tests.py b/tests/tests.py")
        self.assertEqual(files[1].data.splitlines()[-1],
                         "+This is some new content")

        self.assertEqual(files[2].origFile, 'pysvn-1.5.1.tar.gz')
        self.assertEqual(files[2].newFile, 'pysvn-1.5.1.tar.gz')
        self.assertEqual(files[2].origInfo, PRE_CREATION)
        self.assertEqual(files[2].newInfo, '86b520c')
        self.assertTrue(files[2].binary)
        self.assertFalse(files[2].deleted)
        self.assertEqual(len(files[2].data), 97)
        self.assertEqual(files[2].data.splitlines()[0],
                         "diff --git a/pysvn-1.5.1.tar.gz b/pysvn-1.5.1.tar.gz")

        self.assertEqual(files[3].origFile, 'readme')
        self.assertEqual(files[3].newFile, 'readme')
        self.assertEqual(files[3].origInfo, '5e35098')
        self.assertEqual(files[3].newInfo, 'e254ef4')
        self.assertFalse(files[3].binary)
        self.assertFalse(files[3].deleted)
        self.assertEqual(len(files[3].data), 127)
        self.assertEqual(files[3].data.splitlines()[0],
                         "diff --git a/readme b/readme")
        self.assertEqual(files[3].data.splitlines()[-1],
                         "+Hello there")

        self.assertEqual(files[4].origFile, 'OLDFILE')
        self.assertEqual(files[4].newFile, 'OLDFILE')
        self.assertEqual(files[4].origInfo, '8ebcb01')
        self.assertEqual(files[4].newInfo, '0000000')
        self.assertFalse(files[4].binary)
        self.assertTrue(files[4].deleted)
        self.assertEqual(len(files[4].data), 132)
        self.assertEqual(files[4].data.splitlines()[0],
                         "diff --git a/OLDFILE b/OLDFILE")
        self.assertEqual(files[4].data.splitlines()[-1],
                         "-Goodbye")

        self.assertEqual(files[5].origFile, 'readme2')
        self.assertEqual(files[5].newFile, 'readme2')
        self.assertEqual(files[5].origInfo, '5e43098')
        self.assertEqual(files[5].newInfo, 'e248ef4')
        self.assertFalse(files[5].binary)
        self.assertFalse(files[5].deleted)
        self.assertEqual(len(files[5].data), 131)
        self.assertEqual(files[5].data.splitlines()[0],
                         "diff --git a/readme2 b/readme2")
        self.assertEqual(files[5].data.splitlines()[-1],
                         "+Hello there")

    def testParseDiffRevision(self):
        """Testing Git revision number parsing"""

        self.assertEqual(self.tool.parse_diff_revision('doc/readme', 'bf544ea'),
                         ('doc/readme', 'bf544ea'))
        self.assertEqual(self.tool.parse_diff_revision('/dev/null', 'bf544ea'),
                         ('/dev/null', PRE_CREATION))
        self.assertEqual(self.tool.parse_diff_revision('/dev/null', '0000000'),
                         ('/dev/null', PRE_CREATION))

    def testFileExists(self):
        """Testing GitTool.file_exists"""

        self.assert_(self.tool.file_exists("readme", "e965047"))
        self.assert_(self.tool.file_exists("readme", "d6613f5"))

        self.assert_(not self.tool.file_exists("readme", PRE_CREATION))
        self.assert_(not self.tool.file_exists("readme", "fffffff"))
        self.assert_(not self.tool.file_exists("readme2", "fffffff"))

        # these sha's are valid, but commit and tree objects, not blobs
        self.assert_(not self.tool.file_exists("readme", "a62df6c"))
        self.assert_(not self.tool.file_exists("readme2", "ccffbb4"))

    def testGetFile(self):
        """Testing GitTool.get_file"""

        self.assertEqual(self.tool.get_file("readme", PRE_CREATION), '')
        self.assertEqual(self.tool.get_file("readme", "e965047"), 'Hello\n')
        self.assertEqual(self.tool.get_file("readme", "d6613f5"), 'Hello there\n')

        self.assertEqual(self.tool.get_file("readme"), 'Hello there\n')

        self.assertRaises(SCMError, lambda: self.tool.get_file(""))

        self.assertRaises(FileNotFoundError,
                          lambda: self.tool.get_file("", "0000000"))
        self.assertRaises(FileNotFoundError,
                          lambda: self.tool.get_file("hello", "0000000"))
        self.assertRaises(FileNotFoundError,
                          lambda: self.tool.get_file("readme", "0000000"))

    def testParseDiffRevisionWithRemoteAndShortSHA1Error(self):
        """Testing GitTool.parse_diff_revision with remote files and short SHA1 error"""
        self.assertRaises(
            ShortSHA1Error,
            lambda: self.remote_tool.parse_diff_revision('README', 'd7e96b3'))

    def testGetFileWithRemoteAndShortSHA1Error(self):
        """Testing GitTool.get_file with remote files and short SHA1 error"""
        self.assertRaises(
            ShortSHA1Error,
            lambda: self.remote_tool.get_file('README', 'd7e96b3'))


class PolicyTests(DjangoTestCase):
    fixtures = ['test_scmtools']

    def setUp(self):
        self.user = User.objects.create(username='testuser', password='')
        self.anonymous = AnonymousUser()
        self.repo = Repository.objects.create(
            name="test",
            path="example.com:/cvsroot/test",
            username="anonymous",
            tool=Tool.objects.get(name="CVS"))

    def test_repository_public(self):
        """Testing access to a public repository"""
        self.assertTrue(self.repo.is_accessible_by(self.user))
        self.assertTrue(self.repo.is_accessible_by(self.anonymous))

        self.assertTrue(self.repo in Repository.objects.accessible(self.user))
        self.assertTrue(
            self.repo in Repository.objects.accessible(self.anonymous))

    def test_repository_private_access_denied(self):
        """Testing no access to an inaccessible private repository"""
        self.repo.public = False
        self.repo.save()

        self.assertFalse(self.repo.is_accessible_by(self.user))
        self.assertFalse(self.repo.is_accessible_by(self.anonymous))

        self.assertFalse(self.repo in Repository.objects.accessible(self.user))
        self.assertFalse(
            self.repo in Repository.objects.accessible(self.anonymous))

    def test_repository_private_access_allowed_by_user(self):
        """Testing access to a private repository accessible by user"""
        self.repo.users.add(self.user)
        self.repo.public = False
        self.repo.save()

        self.assertTrue(self.repo.is_accessible_by(self.user))
        self.assertFalse(self.repo.is_accessible_by(self.anonymous))

        self.assertTrue(self.repo in Repository.objects.accessible(self.user))
        self.assertFalse(
            self.repo in Repository.objects.accessible(self.anonymous))

    def test_repository_private_access_allowed_by_review_group(self):
        """Testing access to a private repository accessible by review group"""
        group = Group.objects.create(name='test-group')
        group.users.add(self.user)

        self.repo.public = False
        self.repo.review_groups.add(group)
        self.repo.save()

        self.assertTrue(self.repo.is_accessible_by(self.user))
        self.assertFalse(self.repo.is_accessible_by(self.anonymous))

        self.assertTrue(self.repo in Repository.objects.accessible(self.user))
        self.assertFalse(
            self.repo in Repository.objects.accessible(self.anonymous))

    def test_repository_form_with_local_site_and_bad_group(self):
        """Testing adding a Group to a RepositoryForm with the wrong LocalSite."""
        test_site = LocalSite.objects.create(name='test')
        tool = Tool.objects.get(name='Subversion')
        group = Group.objects.create(name='test-group')

        svn_repo_path = 'file://' + os.path.join(os.path.dirname(__file__),
                                                 'testdata/svn_repo')

        form = RepositoryForm({
            'name': 'test',
            'path': svn_repo_path,
            'hosting_type': 'custom',
            'bug_tracker_type': 'custom',
            'review_groups': [group.pk],
            'local_site': test_site.pk,
            'tool': tool.pk,
        })
        self.assertFalse(form.is_valid())

        group.local_site = test_site
        group.save()

        form = RepositoryForm({
            'name': 'test',
            'path': svn_repo_path,
            'hosting_type': 'custom',
            'bug_tracker_type': 'custom',
            'review_groups': [group.pk],
            'tool': tool.pk,
        })
        self.assertFalse(form.is_valid())

    def test_repository_form_with_local_site_and_bad_user(self):
        """Testing adding a User to a RepositoryForm with the wrong LocalSite."""
        test_site = LocalSite.objects.create(name='test')
        tool = Tool.objects.get(name='Subversion')

        svn_repo_path = 'file://' + os.path.join(os.path.dirname(__file__),
                                                 'testdata/svn_repo')

        form = RepositoryForm({
            'name': 'test',
            'path': svn_repo_path,
            'hosting_type': 'custom',
            'bug_tracker_type': 'custom',
            'users': [self.user.pk],
            'local_site': test_site.pk,
            'tool': tool.pk,
        })
        self.assertFalse(form.is_valid())
