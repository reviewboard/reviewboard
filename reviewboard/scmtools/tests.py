# -*- coding: utf-8 -*-
import errno
import imp
import os
import socket
import tempfile
try:
    from hashlib import md5
except ImportError:
    from md5 import md5

from django import forms
from django.contrib.auth.models import AnonymousUser, User
from django.core.cache import cache
from django.test import TestCase as DjangoTestCase
from djblets.util.filesystem import is_exe_in_path
import nose
try:
    imp.find_module("P4")

    try:
        from P4 import P4Error
    except ImportError:
        from P4 import P4Exception as P4Error
except ImportError:
    pass

from reviewboard.diffviewer.diffutils import patch
from reviewboard.diffviewer.parser import DiffParserError
from reviewboard.hostingsvcs.forms import HostingServiceForm
from reviewboard.hostingsvcs.models import HostingServiceAccount
from reviewboard.hostingsvcs.service import HostingService, \
                                            register_hosting_service, \
                                            unregister_hosting_service
from reviewboard.reviews.models import Group
from reviewboard.scmtools.core import HEAD, PRE_CREATION, ChangeSet, Revision
from reviewboard.scmtools.errors import SCMError, FileNotFoundError, \
                                        RepositoryNotFoundError, \
                                        AuthenticationError
from reviewboard.scmtools.forms import RepositoryForm
from reviewboard.scmtools.git import ShortSHA1Error
from reviewboard.scmtools.models import Repository, Tool
from reviewboard.scmtools.perforce import STunnelProxy, STUNNEL_SERVER
from reviewboard.scmtools.signals import checked_file_exists, \
                                         checking_file_exists, \
                                         fetched_file, fetching_file
from reviewboard.site.models import LocalSite
from reviewboard.ssh.client import SSHClient
from reviewboard.ssh.tests import SSHTestCase


class SCMTestCase(SSHTestCase):
    ssh_client = None
    _can_test_ssh = None

    def setUp(self):
        super(SCMTestCase, self).setUp()
        self.tool = None

    def _check_can_test_ssh(self, local_site_name=None):
        if SCMTestCase._can_test_ssh is None:
            SCMTestCase.ssh_client = SSHClient()
            key = self.ssh_client.get_user_key()
            SCMTestCase._can_test_ssh = \
                key is not None and self.ssh_client.is_key_authorized(key)

        if not SCMTestCase._can_test_ssh:
            raise nose.SkipTest(
                "Cannot perform SSH access tests. The local user's SSH "
                "public key must be in the %s file and SSH must be enabled."
                % os.path.join(self.ssh_client.storage.get_ssh_dir(),
                               'authorized_keys'))

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
        user_key = self.ssh_client.get_user_key()
        self.assertNotEqual(user_key, None)

        # Switch to a new SSH directory.
        self.tempdir = tempfile.mkdtemp(prefix='rb-tests-home-')
        sshdir = os.path.join(self.tempdir, '.ssh')
        self._set_home(self.tempdir)

        self.assertEqual(sshdir, self.ssh_client.storage.get_ssh_dir())
        self.assertFalse(os.path.exists(os.path.join(sshdir, 'id_rsa')))
        self.assertFalse(os.path.exists(os.path.join(sshdir, 'id_dsa')))
        self.assertEqual(self.ssh_client.get_user_key(), None)

        tool_class = self.repository.tool

        # Make sure we aren't using the old SSH key. We want auth errors.
        repo = Repository(name='SSH Test', path=repo_path, tool=tool_class)
        tool = repo.get_scmtool()
        self.assertRaises(AuthenticationError,
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

            ssh_client = SSHClient(namespace=local_site_name)
            self.assertEqual(ssh_client.storage.get_ssh_dir(),
                             os.path.join(sshdir, local_site_name))
            ssh_client.import_user_key(user_key)
            self.assertEqual(ssh_client.get_user_key(), user_key)

            # Make sure we can verify the repository and access files.
            tool.check_repository(repo_path, local_site_name=local_site_name)

            if filename:
                self.assertNotEqual(tool.get_file(filename, HEAD), None)


class CoreTests(DjangoTestCase):
    """Tests for the scmtools.core module"""

    def test_interface(self):
        """Testing basic scmtools.core API"""

        # Empty changeset
        cs = ChangeSet()
        self.assertEqual(cs.changenum, None)
        self.assertEqual(cs.summary, '')
        self.assertEqual(cs.description, '')
        self.assertEqual(cs.branch, '')
        self.assert_(len(cs.bugs_closed) == 0)
        self.assert_(len(cs.files) == 0)


class RepositoryTests(DjangoTestCase):
    fixtures = ['test_scmtools']

    def setUp(self):
        self.local_repo_path = os.path.join(os.path.dirname(__file__),
                                            'testdata', 'git_repo')
        self.repository = Repository(name='Git test repo',
                                     path=self.local_repo_path,
                                     tool=Tool.objects.get(name='Git'))

        self.scmtool_cls = self.repository.get_scmtool().__class__
        self.old_get_file = self.scmtool_cls.get_file
        self.old_file_exists = self.scmtool_cls.file_exists

    def tearDown(self):
        cache.clear()

        self.scmtool_cls.get_file = self.old_get_file
        self.scmtool_cls.file_exists = self.old_file_exists

    def test_get_file_caching(self):
        """Testing Repository.get_file caches result"""
        def get_file(self, path, revision):
            num_calls['get_file'] += 1
            return 'file data'

        num_calls = {
            'get_file': 0,
        }

        path = 'readme'
        revision = 'e965047'
        request = {}

        self.scmtool_cls.get_file = get_file

        data1 = self.repository.get_file(path, revision, request=request)
        data2 = self.repository.get_file(path, revision, request=request)

        self.assertEqual(data1, 'file data')
        self.assertEqual(data1, data2)
        self.assertEqual(num_calls['get_file'], 1)

    def test_get_file_signals(self):
        """Testing Repository.get_file emits signals"""
        def on_fetching_file(sender, path, revision, request, **kwargs):
            found_signals.append(('fetching_file', path, revision, request))

        def on_fetched_file(sender, path, revision, request, **kwargs):
            found_signals.append(('fetched_file', path, revision, request))

        found_signals = []

        fetching_file.connect(on_fetching_file, sender=self.repository)
        fetched_file.connect(on_fetched_file, sender=self.repository)

        path = 'readme'
        revision = 'e965047'
        request = {}

        self.repository.get_file(path, revision, request=request)

        self.assertEqual(len(found_signals), 2)
        self.assertEqual(found_signals[0],
                         ('fetching_file', path, revision, request))
        self.assertEqual(found_signals[1],
                         ('fetched_file', path, revision, request))

    def test_get_file_exists_caching_when_exists(self):
        """Testing Repository.get_file_exists caches result when exists"""
        def file_exists(self, path, revision):
            num_calls['get_file_exists'] += 1
            return True

        num_calls = {
            'get_file_exists': 0,
        }

        path = 'readme'
        revision = 'e965047'
        request = {}

        self.scmtool_cls.file_exists = file_exists

        exists1 = self.repository.get_file_exists(path, revision,
                                                  request=request)
        exists2 = self.repository.get_file_exists(path, revision,
                                                  request=request)

        self.assertTrue(exists1)
        self.assertTrue(exists2)
        self.assertEqual(num_calls['get_file_exists'], 1)

    def test_get_file_exists_caching_when_not_exists(self):
        """Testing Repository.get_file_exists doesn't cache result when not exists"""
        def file_exists(self, path, revision):
            num_calls['get_file_exists'] += 1
            return False

        num_calls = {
            'get_file_exists': 0,
        }

        path = 'readme'
        revision = '12345'
        request = {}

        self.scmtool_cls.file_exists = file_exists

        exists1 = self.repository.get_file_exists(path, revision,
                                                  request=request)
        exists2 = self.repository.get_file_exists(path, revision,
                                                  request=request)

        self.assertFalse(exists1)
        self.assertFalse(exists2)
        self.assertEqual(num_calls['get_file_exists'], 2)

    def test_get_file_exists_caching_with_fetched_file(self):
        """Testing Repository.get_file_exists uses get_file's cached result"""
        def get_file(self, path, revision):
            num_calls['get_file'] += 1
            return 'file data'

        def file_exists(self, path, revision):
            num_calls['get_file_exists'] += 1
            return True

        num_calls = {
            'get_file_exists': 0,
            'get_file': 0,
        }

        path = 'readme'
        revision = 'e965047'
        request = {}

        self.scmtool_cls.get_file = get_file
        self.scmtool_cls.file_exists = file_exists

        self.repository.get_file(path, revision, request=request)
        exists1 = self.repository.get_file_exists(path, revision,
                                                  request=request)
        exists2 = self.repository.get_file_exists(path, revision,
                                                  request=request)

        self.assertTrue(exists1)
        self.assertTrue(exists2)
        self.assertEqual(num_calls['get_file'], 1)
        self.assertEqual(num_calls['get_file_exists'], 0)

    def test_get_file_exists_signals(self):
        """Testing Repository.get_file_exists emits signals"""
        def on_checking(sender, path, revision, request, **kwargs):
            found_signals.append(('checking_file_exists', path,
                                  revision, request))

        def on_checked(sender, path, revision, request, **kwargs):
            found_signals.append(('checked_file_exists', path,
                                  revision, request))

        found_signals = []

        checking_file_exists.connect(on_checking, sender=self.repository)
        checked_file_exists.connect(on_checked, sender=self.repository)

        path = 'readme'
        revision = 'e965047'
        request = {}

        self.repository.get_file_exists(path, revision, request=request)

        self.assertEqual(len(found_signals), 2)
        self.assertEqual(found_signals[0],
                         ('checking_file_exists', path, revision, request))
        self.assertEqual(found_signals[1],
                         ('checked_file_exists', path, revision, request))


class BZRTests(SCMTestCase):
    """Unit tests for bzr."""
    fixtures = ['test_scmtools']

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
    fixtures = ['test_scmtools']

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

    def test_path_with_port(self):
        """Testing parsing a CVSROOT with a port"""
        repo = Repository(name="CVS",
                          path="example.com:123/cvsroot/test",
                          username="anonymous",
                          tool=Tool.objects.get(name="CVS"))
        tool = repo.get_scmtool()

        self.assertEqual(tool.repopath, "/cvsroot/test")
        self.assertEqual(tool.client.cvsroot,
                         ":pserver:anonymous@example.com:123/cvsroot/test")

    def test_path_without_port(self):
        """Testing parsing a CVSROOT without a port"""
        repo = Repository(name="CVS",
                          path="example.com:/cvsroot/test",
                          username="anonymous",
                          tool=Tool.objects.get(name="CVS"))
        tool = repo.get_scmtool()

        self.assertEqual(tool.repopath, "/cvsroot/test")
        self.assertEqual(tool.client.cvsroot,
                         ":pserver:anonymous@example.com:/cvsroot/test")

    def test_get_file(self):
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

    def test_revision_parsing(self):
        """Testing revision number parsing"""
        self.assertEqual(self.tool.parse_diff_revision('', 'PRE-CREATION')[1],
                         PRE_CREATION)
        self.assertEqual(self.tool.parse_diff_revision('', '7 Nov 2005 13:17:07 -0000	1.2')[1],
                         '1.2')
        self.assertEqual(self.tool.parse_diff_revision('', '7 Nov 2005 13:17:07 -0000	1.2.3.4')[1],
                         '1.2.3.4')
        self.assertRaises(SCMError,
                          lambda: self.tool.parse_diff_revision('', 'hello'))

    def test_interface(self):
        """Testing basic CVSTool API"""
        self.assertEqual(self.tool.get_diffs_use_absolute_paths(), True)
        self.assertEqual(self.tool.get_fields(), ['diff_path'])

    def test_simple_diff(self):
        """Testing parsing CVS simple diff"""
        diff = ("Index: testfile\n"
                "===================================================================\n"
                "RCS file: %s/test/testfile,v\n"
                "retrieving revision 1.1.1.1\n"
                "diff -u -r1.1.1.1 testfile\n"
                "--- testfile    26 Jul 2007 08:50:30 -0000      1.1.1.1\n"
                "+++ testfile    26 Jul 2007 10:20:20 -0000\n"
                "@@ -1 +1,2 @@\n"
                "-test content\n"
                "+updated test content\n"
                "+added info\n")
        diff = diff % self.cvs_repo_path

        file = self.tool.get_parser(diff).parse()[0]
        self.assertEqual(file.origFile, 'test/testfile')
        self.assertEqual(file.origInfo, '26 Jul 2007 08:50:30 -0000      1.1.1.1')
        self.assertEqual(file.newFile, 'testfile')
        self.assertEqual(file.newInfo, '26 Jul 2007 10:20:20 -0000')
        self.assertEqual(file.data, diff)

    def test_new_diff_revision_format(self):
        """Testing parsing CVS diff with new revision format"""
        diff = ("Index: %s/test/testfile\n"
                "diff -u %s/test/testfile:1.5.2.1 %s/test/testfile:1.5.2.2\n"
                "--- test/testfile:1.5.2.1	Thu Dec 15 16:27:47 2011\n"
                "+++ test/testfile	Tue Jan 10 10:36:26 2012\n"
                "@@ -1 +1,2 @@\n"
                "-test content\n"
                "+updated test content\n"
                "+added info\n")
        diff = diff % (self.cvs_repo_path, self.cvs_repo_path, self.cvs_repo_path)

        file = self.tool.get_parser(diff).parse()[0]
        f2, revision = self.tool.parse_diff_revision(file.origFile, file.origInfo,
                                                    file.moved)
        self.assertEqual(f2, 'test/testfile')
        self.assertEqual(revision, '1.5.2.1')
        self.assertEqual(file.newFile, 'test/testfile')
        self.assertEqual(file.newInfo, 'Tue Jan 10 10:36:26 2012')

    def test_bad_diff(self):
        """Testing parsing CVS diff with bad info"""
        diff = ("Index: newfile\n"
                "===================================================================\n"
                "diff -N newfile\n"
                "--- /dev/null	1 Jan 1970 00:00:00 -0000\n"
                "+++ newfile	26 Jul 2007 10:11:45 -0000\n"
                "@@ -0,0 +1 @@\n"
                "+new file content")

        self.assertRaises(DiffParserError,
                          lambda: self.tool.get_parser(diff).parse())

    def test_bad_diff2(self):
        """Testing parsing CVS bad diff with new file"""
        diff = ("Index: newfile\n"
                "===================================================================\n"
                "RCS file: newfile\n"
                "diff -N newfile\n"
                "--- /dev/null\n"
                "+++ newfile	26 Jul 2007 10:11:45 -0000\n"
                "@@ -0,0 +1 @@\n"
                "+new file content")

        self.assertRaises(DiffParserError,
                          lambda: self.tool.get_parser(diff).parse())

    def test_newfile_diff(self):
        """Testing parsing CVS diff with new file"""
        diff = ("Index: newfile\n"
                "===================================================================\n"
                "RCS file: newfile\n"
                "diff -N newfile\n"
                "--- /dev/null	1 Jan 1970 00:00:00 -0000\n"
                "+++ newfile	26 Jul 2007 10:11:45 -0000\n"
                "@@ -0,0 +1 @@\n"
                "+new file content\n")

        file = self.tool.get_parser(diff).parse()[0]
        self.assertEqual(file.origFile, 'newfile')
        self.assertEqual(file.origInfo, 'PRE-CREATION')
        self.assertEqual(file.newFile, 'newfile')
        self.assertEqual(file.newInfo, '26 Jul 2007 10:11:45 -0000')
        self.assertEqual(file.data, diff)

    def test_inter_revision_diff(self):
        """Testing parsing CVS inter-revision diff"""
        diff = ("Index: testfile\n"
                "===================================================================\n"
                "RCS file: %s/test/testfile,v\n"
                "retrieving revision 1.1\n"
                "retrieving revision 1.2\n"
                "diff -u -p -r1.1 -r1.2\n"
                "--- testfile    26 Jul 2007 08:50:30 -0000      1.1\n"
                "+++ testfile    27 Sep 2007 22:57:16 -0000      1.2\n"
                "@@ -1 +1,2 @@\n"
                "-test content\n"
                "+updated test content\n"
                "+added info\n")
        diff = diff % self.cvs_repo_path

        file = self.tool.get_parser(diff).parse()[0]
        self.assertEqual(file.origFile, 'test/testfile')
        self.assertEqual(file.origInfo, '26 Jul 2007 08:50:30 -0000      1.1')
        self.assertEqual(file.newFile, 'testfile')
        self.assertEqual(file.newInfo, '27 Sep 2007 22:57:16 -0000      1.2')
        self.assertEqual(file.data, diff)

    def test_bad_root(self):
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
    fixtures = ['test_scmtools']

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

    def test_get_file(self):
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

    def test_revision_parsing(self):
        """Testing revision number parsing"""
        self.assertEqual(self.tool.parse_diff_revision('', '(working copy)')[1],
                         HEAD)
        self.assertEqual(self.tool.parse_diff_revision('', '   (revision 0)')[1],
                         PRE_CREATION)

        self.assertEqual(self.tool.parse_diff_revision('', '(revision 1)')[1],
                         '1')
        self.assertEqual(self.tool.parse_diff_revision('', '(revision 23)')[1],
                         '23')

        # Fix for bug 2176
        self.assertEqual(self.tool.parse_diff_revision('', '\t(revision 4)')[1],
                         '4')

        self.assertEqual(self.tool.parse_diff_revision('',
            '2007-06-06 15:32:23 UTC (rev 10958)')[1], '10958')

        self.assertRaises(SCMError,
                          lambda: self.tool.parse_diff_revision('', 'hello'))

        # Verify that 'svn diff' localized revision strings parse correctly.
        self.assertEqual(self.tool.parse_diff_revision('', '(revisión: 5)')[1],
                         '5')
        self.assertEqual(self.tool.parse_diff_revision('',
                         '(リビジョン 6)')[1], '6')
        self.assertEqual(self.tool.parse_diff_revision('', '(版本 7)')[1],
                         '7')

    def test_interface(self):
        """Testing basic SVNTool API"""
        self.assertEqual(self.tool.get_diffs_use_absolute_paths(), False)

        self.assertRaises(NotImplementedError,
                          lambda: self.tool.get_changeset(1))

        self.assertRaises(NotImplementedError,
                          lambda: self.tool.get_pending_changesets(1))

    def test_binary_diff(self):
        """Testing parsing SVN diff with binary file"""
        diff = "Index: binfile\n===========================================" + \
               "========================\nCannot display: file marked as a " + \
               "binary type.\nsvn:mime-type = application/octet-stream\n"

        file = self.tool.get_parser(diff).parse()[0]
        self.assertEqual(file.origFile, 'binfile')
        self.assertEqual(file.binary, True)

    def test_keyword_diff(self):
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

    def test_unterminated_keyword_diff(self):
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

    def test_svn16_property_diff(self):
        """Testing parsing SVN 1.6 diff with property changes"""
        prop_diff = (
            "Index:\n"
            "======================================================"
            "=============\n"
            "--- (revision 123)\n"
            "+++ (working copy)\n"
            "Property changes on: .\n"
            "______________________________________________________"
            "_____________\n"
            "Modified: reviewboard:url\n"
            "## -1 +1 ##\n"
            "-http://reviews.reviewboard.org\n"
            "+http://reviews.reviewboard.org\n")
        bin_diff = (
            "Index: binfile\n"
            "======================================================="
            "============\nCannot display: file marked as a "
            "binary type.\nsvn:mime-type = application/octet-stream\n")
        diff = prop_diff + bin_diff

        files = self.tool.get_parser(diff).parse()
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0].origFile, 'binfile')
        self.assertTrue(files[0].binary)

    def test_svn17_property_diff(self):
        """Testing parsing SVN 1.7+ diff with property changes"""
        prop_diff = (
            "Index .:\n"
            "======================================================"
            "=============\n"
            "--- .  (revision 123)\n"
            "+++ .  (working copy)\n"
            "\n"
            "Property changes on: .\n"
            "______________________________________________________"
            "_____________\n"
            "Modified: reviewboard:url\n"
            "## -0,0 +1,3 ##\n"
            "-http://reviews.reviewboard.org\n"
            "+http://reviews.reviewboard.org\n"
            "Added: myprop\n"
            "## -0,0 +1 ##\n"
            "+Property test.\n")
        bin_diff = (
            "Index: binfile\n"
            "======================================================="
            "============\nCannot display: file marked as a "
            "binary type.\nsvn:mime-type = application/octet-stream\n")
        diff = prop_diff + bin_diff

        files = self.tool.get_parser(diff).parse()
        print files
        print files[0].__dict__

        self.assertEqual(len(files), 1)
        self.assertEqual(files[0].origFile, 'binfile')
        self.assertTrue(files[0].binary)


class PerforceTests(SCMTestCase):
    """Unit tests for perforce.

       This uses the open server at public.perforce.com to test various
       pieces.  Because we have no control over things like pending
       changesets, not everything can be tested.
       """
    fixtures = ['test_scmtools']

    def setUp(self):
        super(PerforceTests, self).setUp()

        self.repository = Repository(name='Perforce.com',
                                     path='public.perforce.com:1666',
                                     tool=Tool.objects.get(name='Perforce'))

        try:
            self.tool = self.repository.get_scmtool()
        except ImportError:
            raise nose.SkipTest('perforce/p4python is not installed')

    def test_changeset(self):
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

    def test_encoding(self):
        """Testing PerforceTool.get_changeset with a specified encoding"""
        repo = Repository(name='Perforce.com',
                          path='public.perforce.com:1666',
                          tool=Tool.objects.get(name='Perforce'),
                          encoding='utf8')
        tool = repo.get_scmtool()
        try:
            tool.get_changeset(157)
            self.fail('Expected an error about unicode-enabled servers. Did '
                      'perforce.com turn on unicode for public.perforce.com?')
        except P4Error, e:
            if str(e).startswith('Connect to server failed'):
                raise nose.SkipTest(
                    'Connection to public.perforce.com failed.  No internet?')
            else:
                raise
        except SCMError, e:
            # public.perforce.com doesn't have unicode enabled. Getting this
            # error means we at least passed the charset through correctly
            # to the p4 client.
            self.assertTrue('clients require a unicode enabled server' in str(e))

    def test_changeset_broken(self):
        """Testing PerforceTool.get_changeset error conditions"""
        repo = Repository(name='Perforce.com',
                          path='public.perforce.com:1666',
                          tool=Tool.objects.get(name='Perforce'),
                          username='samwise',
                          password='bogus')

        try:
            tool = repo.get_scmtool()
        except ImportError:
            raise nose.SkipTest('perforce/p4python is not installed')

        self.assertRaises(AuthenticationError,
                          lambda: tool.get_changeset(157))

        repo = Repository(name='localhost:1',
                          path='localhost:1',
                          tool=Tool.objects.get(name='Perforce'))

        tool = repo.get_scmtool()
        self.assertRaises(RepositoryNotFoundError,
                          lambda: tool.get_changeset(1))

    def test_get_file(self):
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

    def test_empty_diff(self):
        """Testing Perforce empty diff parsing"""
        diff = "==== //depot/foo/proj/README#2 ==M== /src/proj/README ====\n"

        file = self.tool.get_parser(diff).parse()[0]
        self.assertEqual(file.origFile, '//depot/foo/proj/README')
        self.assertEqual(file.origInfo, '//depot/foo/proj/README#2')
        self.assertEqual(file.newFile, '/src/proj/README')
        self.assertEqual(file.newInfo, '')
        self.assertFalse(file.binary)
        self.assertFalse(file.deleted)
        self.assertFalse(file.moved)
        self.assertEqual(file.data, diff)

    def test_binary_diff(self):
        """Testing Perforce binary diff parsing"""
        diff = "==== //depot/foo/proj/test.png#1 ==A== /src/proj/test.png " + \
               "====\nBinary files /tmp/foo and /src/proj/test.png differ\n"

        file = self.tool.get_parser(diff).parse()[0]
        self.assertEqual(file.origFile, '//depot/foo/proj/test.png')
        self.assertEqual(file.origInfo, '//depot/foo/proj/test.png#1')
        self.assertEqual(file.newFile, '/src/proj/test.png')
        self.assertEqual(file.newInfo, '')
        self.assertEqual(file.data, diff)
        self.assertTrue(file.binary)
        self.assertFalse(file.deleted)
        self.assertFalse(file.moved)

    def test_deleted_diff(self):
        """Testing Perforce deleted diff parsing"""
        diff = "==== //depot/foo/proj/test.png#1 ==D== /src/proj/test.png " + \
               "====\n"

        file = self.tool.get_parser(diff).parse()[0]
        self.assertEqual(file.origFile, '//depot/foo/proj/test.png')
        self.assertEqual(file.origInfo, '//depot/foo/proj/test.png#1')
        self.assertEqual(file.newFile, '/src/proj/test.png')
        self.assertEqual(file.newInfo, '')
        self.assertEqual(file.data, diff)
        self.assertFalse(file.binary)
        self.assertTrue(file.deleted)
        self.assertFalse(file.moved)

    def test_moved_file_diff(self):
        """Testing Perforce moved file diff parsing"""
        diff = (
            "Moved from: //depot/foo/proj/test.txt\n"
            "Moved to: //depot/foo/proj/test2.txt\n"
            "--- //depot/foo/proj/test.txt  //depot/foo/proj/test.txt#2\n"
            "+++ //depot/foo/proj/test2.txt  01-02-03 04:05:06\n"
            "@@ -1 +1,2 @@\n"
            "-test content\n"
            "+updated test content\n"
            "+added info\n"
        )

        file = self.tool.get_parser(diff).parse()[0]
        self.assertEqual(file.origFile, '//depot/foo/proj/test.txt')
        self.assertEqual(file.origInfo, '//depot/foo/proj/test.txt#2')
        self.assertEqual(file.newFile, '//depot/foo/proj/test2.txt')
        self.assertEqual(file.newInfo, '01-02-03 04:05:06')
        self.assertEqual(file.data, diff)
        self.assertFalse(file.binary)
        self.assertFalse(file.deleted)
        self.assertTrue(file.moved)
        self.assertEqual(file.data, diff)

    def test_moved_file_diff_no_changes(self):
        """Testing Perforce moved file diff parsing without changes"""
        diff = "==== //depot/foo/proj/test.png#5 ==MV== " \
               "//depot/foo/proj/test2.png ====\n"

        file = self.tool.get_parser(diff).parse()[0]
        self.assertEqual(file.origFile, '//depot/foo/proj/test.png')
        self.assertEqual(file.origInfo, '//depot/foo/proj/test.png#5')
        self.assertEqual(file.newFile, '//depot/foo/proj/test2.png')
        self.assertEqual(file.newInfo, '')
        self.assertEqual(file.data, diff)
        self.assertFalse(file.binary)
        self.assertFalse(file.deleted)
        self.assertTrue(file.moved)

    def test_empty_and_normal_diffs(self):
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
        self.assertFalse(files[0].moved)
        self.assertEqual(files[0].data, diff1_text)

        self.assertEqual(files[1].origFile, 'test.c')
        self.assertEqual(files[1].origInfo, '//depot/foo/proj/test.c#2')
        self.assertEqual(files[1].newFile, 'test.c')
        self.assertEqual(files[1].newInfo, '01-02-03 04:05:06')
        self.assertFalse(files[1].binary)
        self.assertFalse(files[1].deleted)
        self.assertFalse(files[1].moved)
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
    fixtures = ['test_scmtools']

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

    def test_changeset(self):
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

    def test_get_file(self):
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
    fixtures = ['vmware.json', 'test_scmtools']

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
#    def test_parse(self):
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
#    def test_parse_single_line_desc(self):
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
#    def test_parse_multi_line_summary(self):
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
    fixtures = ['test_scmtools']

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

    def _first_file_in_diff(self, diff):
        return self.tool.get_parser(diff).parse()[0]

    def test_patch_creates_new_file(self):
        """Testing HgTool with a patch that creates a new file"""

        self.assertEqual(PRE_CREATION,
            self.tool.parse_diff_revision("/dev/null", "bf544ea505f8")[1])

    def test_diff_parser_new_file(self):
        """Testing HgDiffParser with a diff that creates a new file"""

        diffContents = 'diff -r bf544ea505f8 readme\n' + \
                       '--- /dev/null\n' + \
                       '+++ b/readme\n'

        file = self._first_file_in_diff(diffContents)
        self.assertEqual(file.origFile, "readme")

    def test_diff_parser_uncommitted(self):
        """Testing HgDiffParser with a diff with an uncommitted change"""

        diffContents = 'diff -r bf544ea505f8 readme\n' + \
                       '--- a/readme\n' + \
                       '+++ b/readme\n'

        file = self._first_file_in_diff(diffContents)
        self.assertEqual(file.origInfo, "bf544ea505f8")
        self.assertEqual(file.origFile, "readme")
        self.assertEqual(file.newInfo, "Uncommitted")
        self.assertEqual(file.newFile, "readme")

    def test_diff_parser_committed(self):
        """Testing HgDiffParser with a diff between committed revisions"""

        diffContents = 'diff -r 356a6127ef19 -r 4960455a8e88 readme\n' + \
                       '--- a/readme\n' + \
                       '+++ b/readme\n'

        file = self._first_file_in_diff(diffContents)
        self.assertEqual(file.origInfo, "356a6127ef19")
        self.assertEqual(file.origFile, "readme")
        self.assertEqual(file.newInfo, "4960455a8e88")
        self.assertEqual(file.newFile, "readme")

    def test_diff_parser_with_preamble_junk(self):
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

        file = self._first_file_in_diff(diffContents)
        self.assertEqual(file.origInfo, "356a6127ef19")
        self.assertEqual(file.origFile, "readme")
        self.assertEqual(file.newInfo, "4960455a8e88")
        self.assertEqual(file.newFile, "readme")

    def test_git_diff_parsing(self):
        """Testing HgDiffParser git diff support"""

        diffContents = '# Node ID 4960455a8e88\n' + \
                       '# Parent bf544ea505f8\n' + \
                       'diff --git a/path/to file/readme.txt ' + \
                       'b/new/path to/readme.txt\n' + \
                       '--- a/path/to file/readme.txt\n' + \
                       '+++ b/new/path to/readme.txt\n'

        file = self._first_file_in_diff(diffContents)
        self.assertEqual(file.origInfo, "bf544ea505f8")
        self.assertEqual(file.origFile, "path/to file/readme.txt")
        self.assertEqual(file.newInfo, "4960455a8e88")
        self.assertEqual(file.newFile, "new/path to/readme.txt")

    def test_revision_parsing(self):
        """Testing HgDiffParser revision number parsing"""

        self.assertEqual(self.tool.parse_diff_revision('doc/readme', 'bf544ea505f8'),
                         ('doc/readme', 'bf544ea505f8'))

        self.assertEqual(self.tool.parse_diff_revision('/dev/null', 'bf544ea505f8'),
                         ('/dev/null', PRE_CREATION))

        # TODO think of a meaningful thing to test here...
        # self.assertRaises(SCMException,
        #                  lambda: self.tool.parse_diff_revision('', 'hello'))

    def test_get_file(self):
        """Testing HgTool.get_file"""

        rev = Revision('661e5dd3c493')
        file = 'doc/readme'

        self.assertEqual(self.tool.get_file(file, rev), 'Hello\n\ngoodbye\n')

        self.assert_(self.tool.file_exists('doc/readme'))
        self.assert_(not self.tool.file_exists('doc/readme2'))

        self.assertRaises(FileNotFoundError, lambda: self.tool.get_file(''))

        self.assertRaises(FileNotFoundError,
                          lambda: self.tool.get_file('hello', PRE_CREATION))

    def test_interface(self):
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
    fixtures = ['test_scmtools']

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

    def _read_fixture(self, filename):
        return open( \
            os.path.join(os.path.dirname(__file__), 'testdata', filename), \
            'r').read()

    def _get_file_in_diff(self, diff, filenum=0):
        return self.tool.get_parser(diff).parse()[filenum]
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
        self.assertEqual(file.data.splitlines()[0],
                         "diff --git a/testing b/testing")
        self.assertEqual(file.data.splitlines()[-1], "+ADD")

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
        self.assertEqual(file.data.splitlines()[0],
                         "diff --git a/testing b/testing")
        self.assertEqual(file.data.splitlines()[-1], "+ADD")
        file = self._get_file_in_diff(diff, 1)
        self.assertEqual(file.origFile, 'cfg/testcase.ini')
        self.assertEqual(file.newFile, 'cfg/testcase.ini')
        self.assertEqual(file.origInfo, 'cc18ec8')
        self.assertEqual(file.newInfo, '5e70b73')
        self.assertEqual(file.data.splitlines()[0],
                        "diff --git a/cfg/testcase.ini b/cfg/testcase.ini")
        self.assertEqual(file.data.splitlines()[-1], '+db = pyunit')

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
        self.assertEqual(len(file.data), 249)
        self.assertEqual(file.data.splitlines()[0],
                         "diff --git a/cfg/testcase.ini b/cfg/testcase.ini")
        self.assertEqual(file.data.splitlines()[-1], "+db = pyunit")

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
        self.assertEqual(len(file.data), 124)
        self.assertEqual(file.data.splitlines()[0],
                         "diff --git a/IAMNEW b/IAMNEW")
        self.assertEqual(file.data.splitlines()[-1], "+Hello")

    def test_new_file_no_content_diff(self):
        """Testing parsing Git diff new file, no content"""
        diff = self._read_fixture('git_newfile_nocontent.diff')
        files = self.tool.get_parser(diff).parse()
        self.assertEqual(len(files), 0)

    def test_new_file_no_content_with_following_diff(self):
        """Testing parsing Git diff new file, no content, with following"""
        diff = self._read_fixture('git_newfile_nocontent2.diff')
        self.assertEqual(len(self.tool.get_parser(diff).parse()), 1)
        file = self._get_file_in_diff(diff)
        self.assertEqual(file.origFile, 'cfg/testcase.ini')
        self.assertEqual(file.newFile, 'cfg/testcase.ini')
        self.assertEqual(file.origInfo, 'cc18ec8')
        self.assertEqual(file.newInfo, '5e70b73')
        self.assertEqual(file.data.splitlines()[0],
                        "diff --git a/cfg/testcase.ini b/cfg/testcase.ini")
        self.assertEqual(file.data.splitlines()[-1], '+db = pyunit')

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
        self.assertEqual(len(file.data), 132)
        self.assertEqual(file.data.splitlines()[0],
                         "diff --git a/OLDFILE b/OLDFILE")
        self.assertEqual(file.data.splitlines()[-1], "-Goodbye")

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
        lines = file.data.splitlines()
        self.assertEqual(len(lines), 4)
        self.assertEqual(lines[0],
                         "diff --git a/pysvn-1.5.1.tar.gz b/pysvn-1.5.1.tar.gz")
        self.assertEqual(lines[3],
                         "Binary files /dev/null and b/pysvn-1.5.1.tar.gz "
                         "differ")

    def test_complex_diff(self):
        """Testing parsing Git diff with existing and new files"""
        diff = self._read_fixture('git_complex.diff')
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
        lines = files[1].data.splitlines()
        self.assertEqual(len(lines), 8)
        self.assertEqual(lines[0],
                         "diff --git a/tests/tests.py b/tests/tests.py")
        self.assertEqual(lines[7],
                         "+This is some new content")

        self.assertEqual(files[2].origFile, 'pysvn-1.5.1.tar.gz')
        self.assertEqual(files[2].newFile, 'pysvn-1.5.1.tar.gz')
        self.assertEqual(files[2].origInfo, PRE_CREATION)
        self.assertEqual(files[2].newInfo, '86b520c')
        self.assertTrue(files[2].binary)
        self.assertFalse(files[2].deleted)
        lines = files[2].data.splitlines()
        self.assertEqual(len(lines), 4)
        self.assertEqual(lines[0],
                         "diff --git a/pysvn-1.5.1.tar.gz b/pysvn-1.5.1.tar.gz")
        self.assertEqual(lines[3],
                         'Binary files /dev/null and b/pysvn-1.5.1.tar.gz '
                         'differ')

        self.assertEqual(files[3].origFile, 'readme')
        self.assertEqual(files[3].newFile, 'readme')
        self.assertEqual(files[3].origInfo, '5e35098')
        self.assertEqual(files[3].newInfo, 'e254ef4')
        self.assertFalse(files[3].binary)
        self.assertFalse(files[3].deleted)
        lines = files[3].data.splitlines()
        self.assertEqual(len(lines), 7)
        self.assertEqual(lines[0], "diff --git a/readme b/readme")
        self.assertEqual(lines[6], "+Hello there")

        self.assertEqual(files[4].origFile, 'OLDFILE')
        self.assertEqual(files[4].newFile, 'OLDFILE')
        self.assertEqual(files[4].origInfo, '8ebcb01')
        self.assertEqual(files[4].newInfo, '0000000')
        self.assertFalse(files[4].binary)
        self.assertTrue(files[4].deleted)
        lines = files[4].data.splitlines()
        self.assertEqual(len(lines), 7)
        self.assertEqual(lines[0], "diff --git a/OLDFILE b/OLDFILE")
        self.assertEqual(lines[6], "-Goodbye")

        self.assertEqual(files[5].origFile, 'readme2')
        self.assertEqual(files[5].newFile, 'readme2')
        self.assertEqual(files[5].origInfo, '5e43098')
        self.assertEqual(files[5].newInfo, 'e248ef4')
        self.assertFalse(files[5].binary)
        self.assertFalse(files[5].deleted)
        lines = files[5].data.splitlines()
        self.assertEqual(len(lines), 7)
        self.assertEqual(lines[0], "diff --git a/readme2 b/readme2")
        self.assertEqual(lines[6], "+Hello there")

    def test_parse_diff_with_index_range(self):
        """Testing Git diff parsing with an index range"""
        diff = "diff --git a/foo/bar b/foo/bar2\n" + \
               "similarity index 88%\n" + \
               "rename from foo/bar\n" + \
               "rename to foo/bar2\n" + \
               "index 612544e4343bf04967eb5ea80257f6c64d6f42c7.." + \
               "e88b7f15c03d141d0bb38c8e49bb6c411ebfe1f1 100644\n" + \
               "--- a/foo/bar\n" + \
               "+++ b/foo/bar2\n" + \
               "@ -1,1 +1,1 @@\n" + \
               "-blah blah\n" + \
               "+blah\n"
        files = self.tool.get_parser(diff).parse()
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0].origFile, 'foo/bar')
        self.assertEqual(files[0].newFile, 'foo/bar2')
        self.assertEqual(files[0].origInfo,
                         '612544e4343bf04967eb5ea80257f6c64d6f42c7')
        self.assertEqual(files[0].newInfo,
                         'e88b7f15c03d141d0bb38c8e49bb6c411ebfe1f1')

    def test_parse_diff_with_deleted_binary_files(self):
        """Testing Git diff parsing with deleted binary files"""
        diff = "diff --git a/foo.bin b/foo.bin\n" \
               "deleted file mode 100644\n" \
               "Binary file foo.bin has changed\n" \
               "diff --git a/bar.bin b/bar.bin\n" \
               "deleted file mode 100644\n" \
               "Binary file bar.bin has changed\n"
        files = self.tool.get_parser(diff).parse()
        self.assertEqual(len(files), 2)
        self.assertEqual(files[0].origFile, 'foo.bin')
        self.assertEqual(files[0].newFile, 'foo.bin')
        self.assertEqual(files[0].binary, True)
        self.assertEqual(files[0].deleted, True)
        self.assertEqual(files[1].origFile, 'bar.bin')
        self.assertEqual(files[1].newFile, 'bar.bin')
        self.assertEqual(files[1].binary, True)
        self.assertEqual(files[1].deleted, True)

    def test_parse_diff_with_all_headers(self):
        """Testing Git diff parsing and preserving all headers"""
        preamble = (
            "From 38d8fa94a9aa0c5b27943bec31d94e880165f1e0 Mon Sep "
            "17 00:00:00 2001\n"
            "From: Example Joe <joe@example.com>\n"
            "Date: Thu, 5 Apr 2012 00:41:12 -0700\n"
            "Subject: [PATCH 1/1] Sample patch.\n"
            "\n"
            "This is a test summary.\n"
            "\n"
            "With a description.\n"
            "---\n"
            " foo/bar |   2 -+n"
            " README  |   2 -+n"
            " 2 files changed, 2 insertions(+), 2 deletions(-)\n"
            "\n")
        diff1 = (
            "diff --git a/foo/bar b/foo/bar2\n"
            "index 612544e4343bf04967eb5ea80257f6c64d6f42c7.."
            "e88b7f15c03d141d0bb38c8e49bb6c411ebfe1f1 100644\n"
            "--- a/foo/bar\n"
            "+++ b/foo/bar2\n"
            "@ -1,1 +1,1 @@\n"
            "-blah blah\n"
            "+blah\n")
        diff2 = (
            "diff --git a/README b/README\n"
            "index 712544e4343bf04967eb5ea80257f6c64d6f42c7.."
            "f88b7f15c03d141d0bb38c8e49bb6c411ebfe1f1 100644\n"
            "--- a/README\n"
            "+++ b/README\n"
            "@ -1,1 +1,1 @@\n"
            "-blah blah\n"
            "+blah\n"
            "--n"
            "1.7.1\n")
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

        self.assertEqual(files[1].origFile, 'README')
        self.assertEqual(files[1].newFile, 'README')
        self.assertEqual(files[1].origInfo,
                         '712544e4343bf04967eb5ea80257f6c64d6f42c7')
        self.assertEqual(files[1].newInfo,
                         'f88b7f15c03d141d0bb38c8e49bb6c411ebfe1f1')
        self.assertEqual(files[1].data, diff2)

    def test_parse_diff_revision(self):
        """Testing Git revision number parsing"""

        self.assertEqual(self.tool.parse_diff_revision('doc/readme', 'bf544ea'),
                         ('doc/readme', 'bf544ea'))
        self.assertEqual(self.tool.parse_diff_revision('/dev/null', 'bf544ea'),
                         ('/dev/null', PRE_CREATION))
        self.assertEqual(self.tool.parse_diff_revision('/dev/null', '0000000'),
                         ('/dev/null', PRE_CREATION))

    def test_file_exists(self):
        """Testing GitTool.file_exists"""

        self.assert_(self.tool.file_exists("readme", "e965047"))
        self.assert_(self.tool.file_exists("readme", "d6613f5"))

        self.assert_(not self.tool.file_exists("readme", PRE_CREATION))
        self.assert_(not self.tool.file_exists("readme", "fffffff"))
        self.assert_(not self.tool.file_exists("readme2", "fffffff"))

        # these sha's are valid, but commit and tree objects, not blobs
        self.assert_(not self.tool.file_exists("readme", "a62df6c"))
        self.assert_(not self.tool.file_exists("readme2", "ccffbb4"))

    def test_get_file(self):
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

    def test_parse_diff_revision_with_remote_and_short_SHA1_error(self):
        """Testing GitTool.parse_diff_revision with remote files and short SHA1 error"""
        self.assertRaises(
            ShortSHA1Error,
            lambda: self.remote_tool.parse_diff_revision('README', 'd7e96b3'))

    def test_get_file_with_remote_and_short_SHA1_error(self):
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


class TestServiceForm(HostingServiceForm):
    test_repo_name = forms.CharField(
        label='Repository name',
        max_length=64,
        required=True)


class TestService(HostingService):
    name = 'Test Service'
    form = TestServiceForm
    needs_authorization = True
    supports_repositories = True
    supports_bug_trackers = True
    supported_scmtools = ['Git']
    bug_tracker_field = ('http://example.com/%(hosting_account_username)s/'
                         '%(test_repo_name)s/issue/%%s')
    repository_fields = {
        'Git': {
            'path': 'http://example.com/%(test_repo_name)s/',
        },
    }

    def authorize(self, username, password, hosting_url, local_site_name=None,
                  *args, **kwargs):
        self.authorize_args = {
            'username': username,
            'password': password,
            'hosting_url': hosting_url,
            'local_site_name': local_site_name,
        }

    def is_authorized(self):
        return True

    def check_repository(self, *args, **kwargs):
        pass


class SelfHostedTestService(TestService):
    name = 'Self-Hosted Test'
    self_hosted = True
    bug_tracker_field = '%(hosting_url)s/%(test_repo_name)s/issue/%%s'
    repository_fields = {
        'Git': {
            'path': '%(hosting_url)s/%(test_repo_name)s/',
        },
    }


class RepositoryFormTests(DjangoTestCase):
    fixtures = ['test_scmtools']

    def setUp(self):
        super(RepositoryFormTests, self).setUp()

        register_hosting_service('test', TestService)
        register_hosting_service('self_hosted_test', SelfHostedTestService)

        self.git_tool_id = Tool.objects.get(name='Git').pk

    def tearDown(self):
        super(RepositoryFormTests, self).tearDown()

        unregister_hosting_service('self_hosted_test')
        unregister_hosting_service('test')

    def test_with_hosting_service_new_account(self):
        """Testing RepositoryForm with a hosting service and new account"""
        form = RepositoryForm({
            'name': 'test',
            'hosting_type': 'test',
            'hosting_account_username': 'testuser',
            'hosting_account_password': 'testpass',
            'tool': self.git_tool_id,
            'test_repo_name': 'testrepo',
            'bug_tracker_type': 'none',
        })

        self.assertTrue(form.is_valid())

        repository = form.save()
        self.assertEqual(repository.name, 'test')
        self.assertEqual(repository.hosting_account.username, 'testuser')
        self.assertEqual(repository.hosting_account.service_name, 'test')
        self.assertEqual(repository.hosting_account.local_site, None)
        self.assertEqual(repository.extra_data['repository_plan'], '')

    def test_with_hosting_service_self_hosted_and_new_account(self):
        """Testing RepositoryForm with a self-hosted hosting service and new account"""
        form = RepositoryForm({
            'name': 'test',
            'hosting_type': 'self_hosted_test',
            'hosting_url': 'https://example.com',
            'hosting_account_username': 'testuser',
            'hosting_account_password': 'testpass',
            'test_repo_name': 'myrepo',
            'tool': self.git_tool_id,
            'bug_tracker_type': 'none',
        })
        form.validate_repository = False

        self.assertTrue(form.is_valid())

        repository = form.save()
        self.assertEqual(repository.name, 'test')
        self.assertEqual(repository.hosting_account.hosting_url,
                         'https://example.com')
        self.assertEqual(repository.hosting_account.username, 'testuser')
        self.assertEqual(repository.hosting_account.service_name,
                         'self_hosted_test')
        self.assertEqual(repository.hosting_account.local_site, None)
        self.assertEqual(repository.extra_data['test_repo_name'], 'myrepo')
        self.assertEqual(repository.extra_data['hosting_url'],
                         'https://example.com')

    def test_with_hosting_service_self_hosted_and_blank_url(self):
        """Testing RepositoryForm with a self-hosted hosting service and blank URL"""
        form = RepositoryForm({
            'name': 'test',
            'hosting_type': 'self_hosted_test',
            'hosting_url': '',
            'hosting_account_username': 'testuser',
            'hosting_account_password': 'testpass',
            'test_repo_name': 'myrepo',
            'tool': self.git_tool_id,
            'bug_tracker_type': 'none',
        })
        form.validate_repository = False

        self.assertFalse(form.is_valid())

    def test_with_hosting_service_new_account_localsite(self):
        """Testing RepositoryForm with a hosting service, new account and LocalSite"""
        local_site = LocalSite.objects.create(name='testsite')

        form = RepositoryForm({
            'name': 'test',
            'hosting_type': 'test',
            'hosting_account_username': 'testuser',
            'hosting_account_password': 'testpass',
            'tool': self.git_tool_id,
            'test_repo_name': 'testrepo',
            'bug_tracker_type': 'none',
            'local_site': local_site.pk,
        })

        self.assertTrue(form.is_valid())

        repository = form.save()
        self.assertEqual(repository.name, 'test')
        self.assertEqual(repository.local_site, local_site)
        self.assertEqual(repository.hosting_account.username, 'testuser')
        self.assertEqual(repository.hosting_account.service_name, 'test')
        self.assertEqual(repository.hosting_account.local_site, local_site)
        self.assertEqual(repository.extra_data['repository_plan'], '')

    def test_with_hosting_service_existing_account(self):
        """Testing RepositoryForm with a hosting service and existing account"""
        account = HostingServiceAccount.objects.create(username='testuser',
                                                       service_name='test')

        form = RepositoryForm({
            'name': 'test',
            'hosting_type': 'test',
            'hosting_account': account.pk,
            'tool': self.git_tool_id,
            'test_repo_name': 'testrepo',
            'bug_tracker_type': 'none',
        })

        self.assertTrue(form.is_valid())

        repository = form.save()
        self.assertEqual(repository.name, 'test')
        self.assertEqual(repository.hosting_account, account)
        self.assertEqual(repository.extra_data['repository_plan'], '')

    def test_with_hosting_service_self_hosted_and_existing_account(self):
        """Testing RepositoryForm with a self-hosted hosting service and existing account"""
        account = HostingServiceAccount.objects.create(
            username='testuser',
            service_name='self_hosted_test',
            hosting_url='https://example.com')

        form = RepositoryForm({
            'name': 'test',
            'hosting_type': 'self_hosted_test',
            'hosting_url': 'https://example.com',
            'hosting_account': account.pk,
            'tool': self.git_tool_id,
            'test_repo_name': 'myrepo',
            'bug_tracker_type': 'none',
        })
        form.validate_repository = False

        self.assertTrue(form.is_valid())

        repository = form.save()
        self.assertEqual(repository.name, 'test')
        self.assertEqual(repository.hosting_account, account)
        self.assertEqual(repository.extra_data['hosting_url'],
                         'https://example.com')

    def test_with_hosting_service_self_hosted_and_invalid_existing_account(self):
        """Testing RepositoryForm with a self-hosted hosting service and invalid existing account"""
        account = HostingServiceAccount.objects.create(
            username='testuser',
            service_name='self_hosted_test',
            hosting_url='https://example1.com')

        form = RepositoryForm({
            'name': 'test',
            'hosting_type': 'self_hosted_test',
            'hosting_url': 'https://example2.com',
            'hosting_account': account.pk,
            'tool': self.git_tool_id,
            'test_repo_name': 'myrepo',
            'bug_tracker_type': 'none',
        })
        form.validate_repository = False

        self.assertFalse(form.is_valid())

    def test_with_hosting_service_custom_bug_tracker(self):
        """Testing RepositoryForm with a custom bug tracker"""
        account = HostingServiceAccount.objects.create(username='testuser',
                                                       service_name='test')

        form = RepositoryForm({
            'name': 'test',
            'hosting_type': 'test',
            'hosting_account': account.pk,
            'tool': self.git_tool_id,
            'test_repo_name': 'testrepo',
            'bug_tracker_type': 'custom',
            'bug_tracker': 'http://example.com/issue/%s',
        })

        self.assertTrue(form.is_valid())

        repository = form.save()
        self.assertFalse(repository.extra_data['bug_tracker_use_hosting'])
        self.assertEqual(repository.bug_tracker, 'http://example.com/issue/%s')
        self.assertFalse('bug_tracker_type' in repository.extra_data)

    def test_with_hosting_service_bug_tracker_service(self):
        """Testing RepositoryForm with a bug tracker service"""
        account = HostingServiceAccount.objects.create(username='testuser',
                                                       service_name='test')

        form = RepositoryForm({
            'name': 'test',
            'hosting_type': 'test',
            'hosting_account': account.pk,
            'tool': self.git_tool_id,
            'test_repo_name': 'testrepo',
            'bug_tracker_type': 'test',
            'bug_tracker_hosting_account_username': 'testuser',
            'bug_tracker-test_repo_name': 'testrepo',
        })

        self.assertTrue(form.is_valid())

        repository = form.save()
        self.assertFalse(repository.extra_data['bug_tracker_use_hosting'])
        self.assertEqual(repository.bug_tracker,
                         'http://example.com/testuser/testrepo/issue/%s')
        self.assertEqual(repository.extra_data['bug_tracker_type'],
                         'test')
        self.assertEqual(
            repository.extra_data['bug_tracker-test_repo_name'],
            'testrepo')
        self.assertEqual(
            repository.extra_data['bug_tracker-hosting_account_username'],
            'testuser')

    def test_with_hosting_service_self_hosted_bug_tracker_service(self):
        """Testing RepositoryForm with a self-hosted bug tracker service"""
        account = HostingServiceAccount.objects.create(
            username='testuser',
            service_name='self_hosted_test',
            hosting_url='https://example.com')

        form = RepositoryForm({
            'name': 'test',
            'hosting_type': 'self_hosted_test',
            'hosting_url': 'https://example.com',
            'hosting_account': account.pk,
            'tool': self.git_tool_id,
            'test_repo_name': 'testrepo',
            'bug_tracker_type': 'self_hosted_test',
            'bug_tracker_hosting_url': 'https://example.com',
            'bug_tracker-test_repo_name': 'testrepo',
        })
        form.validate_repository = False

        self.assertTrue(form.is_valid())

        repository = form.save()
        self.assertFalse(repository.extra_data['bug_tracker_use_hosting'])
        self.assertEqual(repository.bug_tracker,
                         'https://example.com/testrepo/issue/%s')
        self.assertEqual(repository.extra_data['bug_tracker_type'],
                         'self_hosted_test')
        self.assertEqual(
            repository.extra_data['bug_tracker-test_repo_name'],
            'testrepo')
        self.assertEqual(
            repository.extra_data['bug_tracker_hosting_url'],
            'https://example.com')

    def test_with_hosting_service_with_hosting_bug_tracker(self):
        """Testing RepositoryForm with hosting service's bug tracker"""
        account = HostingServiceAccount.objects.create(username='testuser',
                                                       service_name='test')

        form = RepositoryForm({
            'name': 'test',
            'hosting_type': 'test',
            'hosting_account': account.pk,
            'tool': self.git_tool_id,
            'test_repo_name': 'testrepo',
            'bug_tracker_use_hosting': True,
            'bug_tracker_type': 'googlecode',
        })
        form.validate_repository = False

        self.assertTrue(form.is_valid())

        repository = form.save()
        self.assertTrue(repository.extra_data['bug_tracker_use_hosting'])
        self.assertEqual(repository.bug_tracker,
                         'http://example.com/testuser/testrepo/issue/%s')
        self.assertFalse('bug_tracker_type' in repository.extra_data)
        self.assertFalse('bug_tracker-test_repo_name'
                         in repository.extra_data)
        self.assertFalse('bug_tracker-hosting_account_username'
                         in repository.extra_data)

    def test_with_hosting_service_with_hosting_bug_tracker_and_self_hosted(self):
        """Testing RepositoryForm with self-hosted hosting service's bug tracker"""
        account = HostingServiceAccount.objects.create(
            username='testuser',
            service_name='self_hosted_test',
            hosting_url='https://example.com')

        account.data['authorization'] = {
            'token': '1234',
        }
        account.save()

        form = RepositoryForm({
            'name': 'test',
            'hosting_type': 'self_hosted_test',
            'hosting_url': 'https://example.com',
            'hosting_account': account.pk,
            'tool': self.git_tool_id,
            'test_repo_name': 'testrepo',
            'bug_tracker_use_hosting': True,
            'bug_tracker_type': 'googlecode',
        })
        form.validate_repository = False

        self.assertTrue(form.is_valid())

        repository = form.save()
        self.assertTrue(repository.extra_data['bug_tracker_use_hosting'])
        self.assertEqual(repository.bug_tracker,
                         'https://example.com/testrepo/issue/%s')
        self.assertFalse('bug_tracker_type' in repository.extra_data)
        self.assertFalse('bug_tracker-test_repo_name'
                         in repository.extra_data)
        self.assertFalse('bug_tracker_hosting_url'
                         in repository.extra_data)

    def test_with_hosting_service_no_bug_tracker(self):
        """Testing RepositoryForm with no bug tracker"""
        account = HostingServiceAccount.objects.create(username='testuser',
                                                       service_name='test')

        form = RepositoryForm({
            'name': 'test',
            'hosting_type': 'test',
            'hosting_account': account.pk,
            'tool': self.git_tool_id,
            'test_repo_name': 'testrepo',
            'bug_tracker_type': 'none',
        })

        self.assertTrue(form.is_valid())

        repository = form.save()
        self.assertFalse(repository.extra_data['bug_tracker_use_hosting'])
        self.assertEqual(repository.bug_tracker, '')
        self.assertFalse('bug_tracker_type' in repository.extra_data)

    def test_with_hosting_service_with_existing_custom_bug_tracker(self):
        """Testing RepositoryForm with existing custom bug tracker"""
        repository = Repository(name='test',
                                bug_tracker='http://example.com/issue/%s')

        form = RepositoryForm(instance=repository)
        self.assertFalse(form._get_field_data('bug_tracker_use_hosting'))
        self.assertEqual(form._get_field_data('bug_tracker_type'), 'custom')
        self.assertEqual(form.initial['bug_tracker'],
                         'http://example.com/issue/%s')

    def test_with_hosting_service_with_existing_bug_tracker_service(self):
        """Testing RepositoryForm with existing bug tracker service"""
        repository = Repository(name='test')
        repository.extra_data['bug_tracker_type'] = 'test'
        repository.extra_data['bug_tracker-test_repo_name'] = 'testrepo'
        repository.extra_data['bug_tracker-hosting_account_username'] = \
            'testuser'

        form = RepositoryForm(instance=repository)
        self.assertFalse(form._get_field_data('bug_tracker_use_hosting'))
        self.assertEqual(form._get_field_data('bug_tracker_type'), 'test')
        self.assertEqual(
            form._get_field_data('bug_tracker_hosting_account_username'),
            'testuser')

        self.assertTrue('test' in form.bug_tracker_forms)
        self.assertTrue('default' in form.bug_tracker_forms['test'])
        bitbucket_form = form.bug_tracker_forms['test']['default']
        self.assertEqual(
            bitbucket_form.fields['test_repo_name'].initial,
            'testrepo')

    def test_with_hosting_service_with_existing_bug_tracker_using_hosting(self):
        """Testing RepositoryForm with existing bug tracker using hosting service"""
        account = HostingServiceAccount.objects.create(username='testuser',
                                                       service_name='test')
        repository = Repository(name='test',
                                hosting_account=account)
        repository.extra_data['bug_tracker_use_hosting'] = True
        repository.extra_data['test_repo_name'] = 'testrepo'

        form = RepositoryForm(instance=repository)
        self.assertTrue(form._get_field_data('bug_tracker_use_hosting'))
