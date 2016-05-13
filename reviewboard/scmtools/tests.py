# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
from errno import ECONNREFUSED
from hashlib import md5
from socket import error as SocketError
from tempfile import mkdtemp

from django.conf import settings
from django.contrib.auth.models import AnonymousUser, User
from django.core.cache import cache
from django.utils import six
from django.utils.six.moves import zip_longest
from djblets.util.filesystem import is_exe_in_path
from kgb import SpyAgency
import nose

from reviewboard.diffviewer.diffutils import patch
from reviewboard.diffviewer.parser import DiffParserError
from reviewboard.hostingsvcs.models import HostingServiceAccount
from reviewboard.hostingsvcs.service import (register_hosting_service,
                                             unregister_hosting_service)
from reviewboard.reviews.models import Group
from reviewboard.scmtools.core import (Branch, ChangeSet, Commit, Revision,
                                       HEAD, PRE_CREATION)
from reviewboard.scmtools.errors import (SCMError, FileNotFoundError,
                                         RepositoryNotFoundError,
                                         AuthenticationError)
from reviewboard.scmtools.forms import RepositoryForm
from reviewboard.scmtools.git import ShortSHA1Error, GitClient
from reviewboard.scmtools.hg import HgDiffParser, HgGitDiffParser
from reviewboard.scmtools.models import Repository, Tool
from reviewboard.scmtools.perforce import STunnelProxy, STUNNEL_SERVER
from reviewboard.scmtools.signals import (checked_file_exists,
                                          checking_file_exists,
                                          fetched_file, fetching_file)
from reviewboard.scmtools.svn import recompute_svn_backend
from reviewboard.site.models import LocalSite
from reviewboard.ssh.client import SSHClient
from reviewboard.ssh.tests import SSHTestCase
from reviewboard.testing import online_only
from reviewboard.testing.hosting_services import (SelfHostedTestService,
                                                  TestService)
from reviewboard.testing.testcase import TestCase


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
        except SocketError as e:
            if e.errno == ECONNREFUSED:
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
        self.tempdir = mkdtemp(prefix='rb-tests-home-')
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
                              lambda: tool.get_file(filename, HEAD))

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


class CoreTests(TestCase):
    """Tests for the scmtools.core module"""

    def test_interface(self):
        """Testing basic scmtools.core API"""

        # Empty changeset
        cs = ChangeSet()
        self.assertEqual(cs.changenum, None)
        self.assertEqual(cs.summary, '')
        self.assertEqual(cs.description, '')
        self.assertEqual(cs.branch, '')
        self.assertTrue(len(cs.bugs_closed) == 0)
        self.assertTrue(len(cs.files) == 0)


class RepositoryTests(TestCase):
    fixtures = ['test_scmtools']

    def setUp(self):
        super(RepositoryTests, self).setUp()

        self.local_repo_path = os.path.join(os.path.dirname(__file__),
                                            'testdata', 'git_repo')
        self.repository = Repository.objects.create(
            name='Git test repo',
            path=self.local_repo_path,
            tool=Tool.objects.get(name='Git'))

        self.scmtool_cls = self.repository.get_scmtool().__class__
        self.old_get_file = self.scmtool_cls.get_file
        self.old_file_exists = self.scmtool_cls.file_exists

    def tearDown(self):
        super(RepositoryTests, self).tearDown()

        cache.clear()

        self.scmtool_cls.get_file = self.old_get_file
        self.scmtool_cls.file_exists = self.old_file_exists

    def test_archive(self):
        """Testing Repository.archive"""
        self.repository.archive()
        self.assertTrue(self.repository.name.startswith('ar:Git test repo:'))
        self.assertTrue(self.repository.archived)
        self.assertFalse(self.repository.public)
        self.assertIsNotNone(self.repository.archived_timestamp)

        repository = Repository.objects.get(pk=self.repository.pk)
        self.assertEqual(repository.name, self.repository.name)
        self.assertEqual(repository.archived, self.repository.archived)
        self.assertEqual(repository.public, self.repository.public)
        self.assertEqual(repository.archived_timestamp,
                         self.repository.archived_timestamp)

    def test_archive_no_save(self):
        """Testing Repository.archive with save=False"""
        self.repository.archive(save=False)
        self.assertTrue(self.repository.name.startswith('ar:Git test repo:'))
        self.assertTrue(self.repository.archived)
        self.assertFalse(self.repository.public)
        self.assertIsNotNone(self.repository.archived_timestamp)

        repository = Repository.objects.get(pk=self.repository.pk)
        self.assertNotEqual(repository.name, self.repository.name)
        self.assertNotEqual(repository.archived, self.repository.archived)
        self.assertNotEqual(repository.public, self.repository.public)
        self.assertNotEqual(repository.archived_timestamp,
                            self.repository.archived_timestamp)

    def test_get_file_caching(self):
        """Testing Repository.get_file caches result"""
        def get_file(self, path, revision, **kwargs):
            num_calls['get_file'] += 1
            return b'file data'

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
        def file_exists(self, path, revision, **kwargs):
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
        """Testing Repository.get_file_exists doesn't cache result when the
        file does not exist
        """
        def file_exists(self, path, revision, **kwargs):
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
        def get_file(self, path, revision, **kwargs):
            num_calls['get_file'] += 1
            return 'file data'

        def file_exists(self, path, revision, **kwargs):
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

    def test_get_file_signature_warning(self):
        """Test old SCMTool.get_file signature triggers warning"""
        def get_file(self, path, revision):
            return 'file data'

        self.scmtool_cls.get_file = get_file

        path = 'readme'
        revision = 'e965047'
        request = {}

        warn_msg = ('SCMTool.get_file() must take keyword arguments, '
                    'signature for %s is deprecated.' %
                    self.repository.get_scmtool().name)

        with self.assert_warns(message=warn_msg):
            self.repository.get_file(path, revision, request=request)

    def test_file_exists_signature_warning(self):
        """Test old SCMTool.file_exists signature triggers warning"""
        def file_exists(self, path, revision=HEAD):
            return True

        self.scmtool_cls.file_exists = file_exists

        path = 'readme'
        revision = 'e965047'
        request = {}

        warn_msg = ('SCMTool.file_exists() must take keyword arguments, '
                    'signature for %s is deprecated.' %
                    self.repository.get_scmtool().name)

        with self.assert_warns(message=warn_msg):
            self.repository.get_file_exists(path, revision, request=request)


class BZRTests(SCMTestCase):
    """Unit tests for bzr."""
    fixtures = ['test_scmtools']

    def setUp(self):
        super(BZRTests, self).setUp()

        self.bzr_repo_path = os.path.join(os.path.dirname(__file__),
                                          'testdata', 'bzr_repo')
        self.bzr_ssh_path = ('bzr+ssh://localhost/%s'
                             % self.bzr_repo_path.replace('\\', '/'))
        self.bzr_sftp_path = ('sftp://localhost/%s'
                              % self.bzr_repo_path.replace('\\', '/'))
        self.repository = Repository(name='Bazaar',
                                     path='file://' + self.bzr_repo_path,
                                     tool=Tool.objects.get(name='Bazaar'))

        from reviewboard.scmtools.bzr import has_bzrlib
        if not has_bzrlib:
            self.tool = self.repository.get_scmtool()
            raise nose.SkipTest('bzrlib is not installed')

    def test_ssh(self):
        """Testing a SSH-backed bzr repository"""
        self._test_ssh(self.bzr_ssh_path, 'README')

    def test_ssh_with_site(self):
        """Testing a SSH-backed bzr repository with a LocalSite"""
        self._test_ssh_with_site(self.bzr_ssh_path, 'README')

    def test_sftp(self):
        """Testing a SFTP-backed bzr repository"""
        try:
            self._test_ssh(self.bzr_sftp_path, 'README')
        except SCMError as e:
            if six.text_type(e) == ('prefetch() takes exactly 2 arguments '
                                    '(1 given)'):
                raise nose.SkipTest(
                    'Installed bazaar and paramiko are incompatible. See '
                    'https://bugs.launchpad.net/bzr/+bug/1524066')
            else:
                raise e


class CVSTests(SCMTestCase):
    """Unit tests for CVS."""
    fixtures = ['test_scmtools']

    def setUp(self):
        super(CVSTests, self).setUp()

        self.cvs_repo_path = os.path.join(os.path.dirname(__file__),
                                          'testdata/cvs_repo')
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
        """Testing CVSTool.build_cvsroot with :pserver: and inline user/password
        taking precedence
        """
        self._test_build_cvsroot(
            repo_path=':pserver:anonymous:pass@example.com:/cvsroot/test',
            username='grumpy',
            password='grr',
            expected_cvsroot=':pserver:anonymous:pass@example.com:'
                             '/cvsroot/test',
            expected_path='/cvsroot/test')

    def test_get_file(self):
        """Testing CVSTool.get_file"""
        expected = b"test content\n"
        file = 'test/testfile'
        rev = Revision('1.1')
        badrev = Revision('2.1')

        value = self.tool.get_file(file, rev)
        self.assertTrue(isinstance(value, bytes))
        self.assertEqual(value, expected)
        self.assertEqual(self.tool.get_file(file + ",v", rev), expected)
        self.assertEqual(self.tool.get_file(self.tool.repopath + '/' +
                                            file + ",v", rev), expected)

        self.assertTrue(self.tool.file_exists('test/testfile'))
        self.assertTrue(self.tool.file_exists(
            self.tool.repopath + '/test/testfile'))
        self.assertTrue(self.tool.file_exists('test/testfile,v'))
        self.assertTrue(not self.tool.file_exists('test/testfile2'))
        self.assertTrue(not self.tool.file_exists(
            self.tool.repopath + '/test/testfile2'))
        self.assertTrue(not self.tool.file_exists('test/testfile2,v'))
        self.assertTrue(not self.tool.file_exists('test/testfile', badrev))

        self.assertRaises(FileNotFoundError,
                          lambda: self.tool.get_file(''))
        self.assertRaises(FileNotFoundError,
                          lambda: self.tool.get_file('hello', PRE_CREATION))

    def test_get_file_with_keywords(self):
        """Testing CVSTool.get_file with file containing keywords"""
        value = self.tool.get_file('test/testfile', Revision('1.2'))

        self.assertEqual(
            value,
            '$Id$\n'
            '$Author$\n'
            '\n'
            'test content\n')

    def test_revision_parsing(self):
        """Testing CVSTool revision number parsing"""
        self.assertEqual(self.tool.parse_diff_revision('', 'PRE-CREATION')[1],
                         PRE_CREATION)
        self.assertEqual(
            self.tool.parse_diff_revision(
                '', '7 Nov 2005 13:17:07 -0000\t1.2')[1],
            '1.2')
        self.assertEqual(
            self.tool.parse_diff_revision(
                '', '7 Nov 2005 13:17:07 -0000\t1.2.3.4')[1],
            '1.2.3.4')
        self.assertRaises(SCMError,
                          lambda: self.tool.parse_diff_revision('', 'hello'))

    def test_interface(self):
        """Testing basic CVSTool API"""
        self.assertEqual(self.tool.get_diffs_use_absolute_paths(), True)
        self.assertEqual(self.tool.get_fields(), ['diff_path'])

    def test_simple_diff(self):
        """Testing parsing CVS simple diff"""
        diff = (b"Index: testfile\n"
                b"==========================================================="
                b"========\n"
                b"RCS file: %s/test/testfile,v\n"
                b"retrieving revision 1.1.1.1\n"
                b"diff -u -r1.1.1.1 testfile\n"
                b"--- testfile    26 Jul 2007 08:50:30 -0000      1.1.1.1\n"
                b"+++ testfile    26 Jul 2007 10:20:20 -0000\n"
                b"@@ -1 +1,2 @@\n"
                b"-test content\n"
                b"+updated test content\n"
                b"+added info\n")
        diff = diff % self.cvs_repo_path

        file = self.tool.get_parser(diff).parse()[0]
        self.assertEqual(file.origFile, 'test/testfile')
        self.assertEqual(file.origInfo,
                         '26 Jul 2007 08:50:30 -0000      1.1.1.1')
        self.assertEqual(file.newFile, 'testfile')
        self.assertEqual(file.newInfo, '26 Jul 2007 10:20:20 -0000')
        self.assertEqual(file.data, diff)
        self.assertEqual(file.insert_count, 2)
        self.assertEqual(file.delete_count, 1)

    def test_new_diff_revision_format(self):
        """Testing parsing CVS diff with new revision format"""
        diff = (b"Index: %s/test/testfile\n"
                b"diff -u %s/test/testfile:1.5.2.1 %s/test/testfile:1.5.2.2\n"
                b"--- test/testfile:1.5.2.1\tThu Dec 15 16:27:47 2011\n"
                b"+++ test/testfile\tTue Jan 10 10:36:26 2012\n"
                b"@@ -1 +1,2 @@\n"
                b"-test content\n"
                b"+updated test content\n"
                b"+added info\n")
        diff = diff % (self.cvs_repo_path, self.cvs_repo_path,
                       self.cvs_repo_path)

        file = self.tool.get_parser(diff).parse()[0]
        f2, revision = self.tool.parse_diff_revision(file.origFile,
                                                     file.origInfo,
                                                     file.moved)
        self.assertEqual(f2, 'test/testfile')
        self.assertEqual(revision, '1.5.2.1')
        self.assertEqual(file.newFile, 'test/testfile')
        self.assertEqual(file.newInfo, 'Tue Jan 10 10:36:26 2012')
        self.assertEqual(file.insert_count, 2)
        self.assertEqual(file.delete_count, 1)

    def test_bad_diff(self):
        """Testing parsing CVS diff with bad info"""
        diff = (b"Index: newfile\n"
                b"==========================================================="
                b"========\n"
                b"diff -N newfile\n"
                b"--- /dev/null\t1 Jan 1970 00:00:00 -0000\n"
                b"+++ newfile\t26 Jul 2007 10:11:45 -0000\n"
                b"@@ -0,0 +1 @@\n"
                b"+new file content")

        self.assertRaises(DiffParserError,
                          lambda: self.tool.get_parser(diff).parse())

    def test_bad_diff2(self):
        """Testing parsing CVS bad diff with new file"""
        diff = (b"Index: newfile\n"
                b"==========================================================="
                b"========\n"
                b"RCS file: newfile\n"
                b"diff -N newfile\n"
                b"--- /dev/null\n"
                b"+++ newfile\t26 Jul 2007 10:11:45 -0000\n"
                b"@@ -0,0 +1 @@\n"
                b"+new file content")

        self.assertRaises(DiffParserError,
                          lambda: self.tool.get_parser(diff).parse())

    def test_newfile_diff(self):
        """Testing parsing CVS diff with new file"""
        diff = (b"Index: newfile\n"
                b"==========================================================="
                b"========\n"
                b"RCS file: newfile\n"
                b"diff -N newfile\n"
                b"--- /dev/null\t1 Jan 1970 00:00:00 -0000\n"
                b"+++ newfile\t26 Jul 2007 10:11:45 -0000\n"
                b"@@ -0,0 +1 @@\n"
                b"+new file content\n")

        file = self.tool.get_parser(diff).parse()[0]
        self.assertEqual(file.origFile, 'newfile')
        self.assertEqual(file.origInfo, 'PRE-CREATION')
        self.assertEqual(file.newFile, 'newfile')
        self.assertEqual(file.newInfo, '26 Jul 2007 10:11:45 -0000')
        self.assertEqual(file.data, diff)
        self.assertEqual(file.insert_count, 1)
        self.assertEqual(file.delete_count, 0)

    def test_inter_revision_diff(self):
        """Testing parsing CVS inter-revision diff"""
        diff = (b"Index: testfile\n"
                b"==========================================================="
                b"========\n"
                b"RCS file: %s/test/testfile,v\n"
                b"retrieving revision 1.1\n"
                b"retrieving revision 1.2\n"
                b"diff -u -p -r1.1 -r1.2\n"
                b"--- testfile    26 Jul 2007 08:50:30 -0000      1.1\n"
                b"+++ testfile    27 Sep 2007 22:57:16 -0000      1.2\n"
                b"@@ -1 +1,2 @@\n"
                b"-test content\n"
                b"+updated test content\n"
                b"+added info\n")
        diff = diff % self.cvs_repo_path

        file = self.tool.get_parser(diff).parse()[0]
        self.assertEqual(file.origFile, 'test/testfile')
        self.assertEqual(file.origInfo, '26 Jul 2007 08:50:30 -0000      1.1')
        self.assertEqual(file.newFile, 'testfile')
        self.assertEqual(file.newInfo, '27 Sep 2007 22:57:16 -0000      1.2')
        self.assertEqual(file.data, diff)
        self.assertEqual(file.insert_count, 2)
        self.assertEqual(file.delete_count, 1)

    def test_unicode_diff(self):
        """Testing parsing CVS diff with unicode filenames"""
        diff = ("Index: téstfile\n"
                "==========================================================="
                "========\n"
                "RCS file: %s/test/téstfile,v\n"
                "retrieving revision 1.1.1.1\n"
                "diff -u -r1.1.1.1 téstfile\n"
                "--- téstfile    26 Jul 2007 08:50:30 -0000      1.1.1.1\n"
                "+++ téstfile    26 Jul 2007 10:20:20 -0000\n"
                "@@ -1 +1,2 @@\n"
                "-tést content\n"
                "+updated test content\n"
                "+added info\n")
        diff = diff % self.cvs_repo_path
        diff = diff.encode('utf-8')

        file = self.tool.get_parser(diff).parse()[0]
        self.assertEqual(file.origFile, 'test/téstfile')
        self.assertEqual(file.origInfo,
                         '26 Jul 2007 08:50:30 -0000      1.1.1.1')
        self.assertEqual(file.newFile, 'téstfile')
        self.assertEqual(file.newInfo, '26 Jul 2007 10:20:20 -0000')
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
                            username=None, password=None):
        cvsroot, norm_path = self.tool.build_cvsroot(repo_path, username,
                                                     password)

        self.assertEqual(cvsroot, expected_cvsroot)
        self.assertEqual(norm_path, expected_path)


class CommonSVNTestsBase(SpyAgency, SCMTestCase):
    """Common unit tests for Subversion.

    This is meant to be subclassed for each backend that wants to run
    the common set of tests.
    """
    backend = None
    backend_name = None
    fixtures = ['test_scmtools']

    def setUp(self):
        super(CommonSVNTestsBase, self).setUp()

        self._old_backend_setting = settings.SVNTOOL_BACKENDS
        settings.SVNTOOL_BACKENDS = [self.backend]
        recompute_svn_backend()

        self.svn_repo_path = os.path.join(os.path.dirname(__file__),
                                          'testdata/svn_repo')
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
        super(CommonSVNTestsBase, self).tearDown()

        settings.SVNTOOL_BACKENDS = self._old_backend_setting
        recompute_svn_backend()

    def shortDescription(self):
        desc = super(CommonSVNTestsBase, self).shortDescription()
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
        diff = (b"Index: Makefile\n"
                b"==========================================================="
                b"========\n"
                b"--- Makefile    (revision 4)\n"
                b"+++ Makefile    (working copy)\n"
                b"@@ -1,6 +1,7 @@\n"
                b" # $Id$\n"
                b" # $Rev$\n"
                b" # $Revision::     $\n"
                b"+# foo\n"
                b" include ../tools/Makefile.base-vars\n"
                b" NAME = misc-docs\n"
                b" OUTNAME = svn-misc-docs\n")

        filename = 'trunk/doc/misc-docs/Makefile'
        rev = Revision('4')
        file = self.tool.get_file(filename, rev)
        patch(diff, file, filename)

    def test_unterminated_keyword_diff(self):
        """Testing SVN (<backend>) parsing diff with unterminated keywords"""
        diff = (b"Index: Makefile\n"
                b"==========================================================="
                b"========\n"
                b"--- Makefile    (revision 4)\n"
                b"+++ Makefile    (working copy)\n"
                b"@@ -1,6 +1,7 @@\n"
                b" # $Id$\n"
                b" # $Id:\n"
                b" # $Rev$\n"
                b" # $Revision::     $\n"
                b"+# foo\n"
                b" include ../tools/Makefile.base-vars\n"
                b" NAME = misc-docs\n"
                b" OUTNAME = svn-misc-docs\n")

        filename = 'trunk/doc/misc-docs/Makefile'
        rev = Revision('5')
        file = self.tool.get_file(filename, rev)
        patch(diff, file, filename)

    def test_svn16_property_diff(self):
        """Testing SVN (<backend>) parsing SVN 1.6 diff with
        property changes
        """
        prop_diff = (
            b"Index:\n"
            b"======================================================"
            b"=============\n"
            b"--- (revision 123)\n"
            b"+++ (working copy)\n"
            b"Property changes on: .\n"
            b"______________________________________________________"
            b"_____________\n"
            b"Modified: reviewboard:url\n"
            b"## -1 +1 ##\n"
            b"-http://reviews.reviewboard.org\n"
            b"+http://reviews.reviewboard.org\n")
        bin_diff = (
            b"Index: binfile\n"
            b"======================================================="
            b"============\nCannot display: file marked as a "
            b"binary type.\nsvn:mime-type = application/octet-stream\n")
        diff = prop_diff + bin_diff

        files = self.tool.get_parser(diff).parse()
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0].origFile, 'binfile')
        self.assertTrue(files[0].binary)
        self.assertEqual(files[0].insert_count, 0)
        self.assertEqual(files[0].delete_count, 0)

    def test_svn17_property_diff(self):
        """Testing SVN (<backend>) parsing SVN 1.7+ diff with
        property changes
        """
        prop_diff = (
            b"Index .:\n"
            b"======================================================"
            b"=============\n"
            b"--- .  (revision 123)\n"
            b"+++ .  (working copy)\n"
            b"\n"
            b"Property changes on: .\n"
            b"______________________________________________________"
            b"_____________\n"
            b"Modified: reviewboard:url\n"
            b"## -0,0 +1,3 ##\n"
            b"-http://reviews.reviewboard.org\n"
            b"+http://reviews.reviewboard.org\n"
            b"Added: myprop\n"
            b"## -0,0 +1 ##\n"
            b"+Property test.\n")
        bin_diff = (
            b"Index: binfile\n"
            b"======================================================="
            b"============\nCannot display: file marked as a "
            b"binary type.\nsvn:mime-type = application/octet-stream\n")
        diff = prop_diff + bin_diff

        files = self.tool.get_parser(diff).parse()

        self.assertEqual(len(files), 1)
        self.assertEqual(files[0].origFile, 'binfile')
        self.assertTrue(files[0].binary)
        self.assertEqual(files[0].insert_count, 0)
        self.assertEqual(files[0].delete_count, 0)

    def test_unicode_diff(self):
        """Testing SVN (<backend>) parsing diff with unicode characters"""
        diff = ("Index: Filé\n"
                "==========================================================="
                "========\n"
                "--- Filé    (revision 4)\n"
                "+++ Filé    (working copy)\n"
                "@@ -1,6 +1,7 @@\n"
                "+# foó\n"
                " include ../tools/Makefile.base-vars\n"
                " NAME = misc-docs\n"
                " OUTNAME = svn-misc-docs\n").encode('utf-8')

        files = self.tool.get_parser(diff).parse()
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0].origFile, 'Filé')
        self.assertFalse(files[0].binary)
        self.assertEqual(files[0].insert_count, 1)
        self.assertEqual(files[0].delete_count, 0)

    def test_diff_with_spaces_in_filenames(self):
        """Testing SVN (<backend>) parsing diff with spaces in filenames"""
        diff = (b"Index: File with spaces\n"
                b"==========================================================="
                b"========\n"
                b"--- File with spaces    (revision 4)\n"
                b"+++ File with spaces    (working copy)\n"
                b"@@ -1,6 +1,7 @@\n"
                b"+# foo\n"
                b" include ../tools/Makefile.base-vars\n"
                b" NAME = misc-docs\n"
                b" OUTNAME = svn-misc-docs\n")

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


class PySVNTests(CommonSVNTestsBase):
    backend = 'reviewboard.scmtools.svn.pysvn'
    backend_name = 'pysvn'


class SubvertpyTests(CommonSVNTestsBase):
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

    @online_only
    def test_changeset(self):
        """Testing PerforceTool.get_changeset"""
        desc = self.tool.get_changeset(157)
        self.assertEqual(desc.changenum, 157)
        self.assertEqual(type(desc.description), six.text_type)
        self.assertEqual(md5(desc.description.encode('utf-8')).hexdigest(),
                         'b7eff0ca252347cc9b09714d07397e64')

        expected_files = [
            '//public/perforce/api/python/P4Client/P4Clientmodule.cc',
            '//public/perforce/api/python/P4Client/p4.py',
            '//public/perforce/api/python/P4Client/review.py',
            '//public/perforce/python/P4Client/P4Clientmodule.cc',
            '//public/perforce/python/P4Client/p4.py',
            '//public/perforce/python/P4Client/review.py',
        ]
        for file, expected in zip_longest(desc.files, expected_files):
            self.assertEqual(file, expected)

        self.assertEqual(md5(desc.summary.encode('utf-8')).hexdigest(),
                         '99a335676b0e5821ffb2f7469d4d7019')

    @online_only
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
        except SCMError as e:
            # public.perforce.com doesn't have unicode enabled. Getting this
            # error means we at least passed the charset through correctly
            # to the p4 client.
            self.assertTrue('clients require a unicode enabled server' in
                            six.text_type(e))

    @online_only
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

    @online_only
    def test_get_file(self):
        """Testing PerforceTool.get_file"""
        file = self.tool.get_file('//depot/foo', PRE_CREATION)
        self.assertEqual(file, b'')

        file = self.tool.get_file(
            '//public/perforce/api/python/P4Client/p4.py', 1)
        self.assertEqual(md5(file).hexdigest(),
                         '227bdd87b052fcad9369e65c7bf23fd0')

    @online_only
    def test_custom_host(self):
        """Testing Perforce client initialization with a custom P4HOST"""
        repo = Repository(name='Perforce.com',
                          path='public.perforce.com:1666',
                          tool=Tool.objects.get(name='Perforce'),
                          encoding='utf8')
        repo.extra_data['p4_host'] = 'my-custom-host'

        tool = repo.get_scmtool()

        with tool.client._connect():
            self.assertEqual(tool.client.p4.host, 'my-custom-host')

    def test_empty_diff(self):
        """Testing Perforce empty diff parsing"""
        diff = b"==== //depot/foo/proj/README#2 ==M== /src/proj/README ====\n"

        file = self.tool.get_parser(diff).parse()[0]
        self.assertEqual(file.origFile, '//depot/foo/proj/README')
        self.assertEqual(file.origInfo, '//depot/foo/proj/README#2')
        self.assertEqual(file.newFile, '/src/proj/README')
        self.assertEqual(file.newInfo, '')
        self.assertFalse(file.binary)
        self.assertFalse(file.deleted)
        self.assertFalse(file.moved)
        self.assertEqual(file.data, diff)
        self.assertEqual(file.insert_count, 0)
        self.assertEqual(file.delete_count, 0)

    def test_binary_diff(self):
        """Testing Perforce binary diff parsing"""
        diff = (b"==== //depot/foo/proj/test.png#1 ==A== /src/proj/test.png "
                b"====\nBinary files /tmp/foo and /src/proj/test.png differ\n")

        file = self.tool.get_parser(diff).parse()[0]
        self.assertEqual(file.origFile, '//depot/foo/proj/test.png')
        self.assertEqual(file.origInfo, '//depot/foo/proj/test.png#1')
        self.assertEqual(file.newFile, '/src/proj/test.png')
        self.assertEqual(file.newInfo, '')
        self.assertEqual(file.data, diff)
        self.assertTrue(file.binary)
        self.assertFalse(file.deleted)
        self.assertFalse(file.moved)
        self.assertEqual(file.insert_count, 0)
        self.assertEqual(file.delete_count, 0)

    def test_deleted_diff(self):
        """Testing Perforce deleted diff parsing"""
        diff = (b"==== //depot/foo/proj/test.png#1 ==D== /src/proj/test.png "
                b"====\n")

        file = self.tool.get_parser(diff).parse()[0]
        self.assertEqual(file.origFile, '//depot/foo/proj/test.png')
        self.assertEqual(file.origInfo, '//depot/foo/proj/test.png#1')
        self.assertEqual(file.newFile, '/src/proj/test.png')
        self.assertEqual(file.newInfo, '')
        self.assertEqual(file.data, diff)
        self.assertFalse(file.binary)
        self.assertTrue(file.deleted)
        self.assertFalse(file.moved)
        self.assertEqual(file.insert_count, 0)
        self.assertEqual(file.delete_count, 0)

    def test_moved_file_diff(self):
        """Testing Perforce moved file diff parsing"""
        diff = (
            b"Moved from: //depot/foo/proj/test.txt\n"
            b"Moved to: //depot/foo/proj/test2.txt\n"
            b"--- //depot/foo/proj/test.txt  //depot/foo/proj/test.txt#2\n"
            b"+++ //depot/foo/proj/test2.txt  01-02-03 04:05:06\n"
            b"@@ -1 +1,2 @@\n"
            b"-test content\n"
            b"+updated test content\n"
            b"+added info\n"
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
        self.assertEqual(file.insert_count, 2)
        self.assertEqual(file.delete_count, 1)

    def test_moved_file_diff_no_changes(self):
        """Testing Perforce moved file diff parsing without changes"""
        diff = (b"==== //depot/foo/proj/test.png#5 ==MV== "
                b"//depot/foo/proj/test2.png ====\n")

        file = self.tool.get_parser(diff).parse()[0]
        self.assertEqual(file.origFile, '//depot/foo/proj/test.png')
        self.assertEqual(file.origInfo, '//depot/foo/proj/test.png#5')
        self.assertEqual(file.newFile, '//depot/foo/proj/test2.png')
        self.assertEqual(file.newInfo, '')
        self.assertEqual(file.data, diff)
        self.assertFalse(file.binary)
        self.assertFalse(file.deleted)
        self.assertTrue(file.moved)
        self.assertEqual(file.insert_count, 0)
        self.assertEqual(file.delete_count, 0)

    def test_empty_and_normal_diffs(self):
        """Testing Perforce empty and normal diff parsing"""
        diff1_text = (b"==== //depot/foo/proj/test.png#1 ==A== "
                      b"/src/proj/test.png ====\n")
        diff2_text = (b"--- test.c  //depot/foo/proj/test.c#2\n"
                      b"+++ test.c  01-02-03 04:05:06\n"
                      b"@@ -1 +1,2 @@\n"
                      b"-test content\n"
                      b"+updated test content\n"
                      b"+added info\n")
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
        self.assertEqual(files[0].insert_count, 0)
        self.assertEqual(files[0].delete_count, 0)

        self.assertEqual(files[1].origFile, 'test.c')
        self.assertEqual(files[1].origInfo, '//depot/foo/proj/test.c#2')
        self.assertEqual(files[1].newFile, 'test.c')
        self.assertEqual(files[1].newInfo, '01-02-03 04:05:06')
        self.assertFalse(files[1].binary)
        self.assertFalse(files[1].deleted)
        self.assertFalse(files[1].moved)
        self.assertEqual(files[1].data, diff2_text)
        self.assertEqual(files[1].insert_count, 2)
        self.assertEqual(files[1].delete_count, 1)

    def test_diff_file_normalization(self):
        """Testing perforce diff filename normalization"""
        parser = self.tool.get_parser('')
        self.assertEqual(parser.normalize_diff_filename('//depot/test'),
                         '//depot/test')

    def test_unicode_diff(self):
        """Testing Perforce diff parsing with unicode characters"""
        diff = ("--- tést.c  //depot/foo/proj/tést.c#2\n"
                "+++ tést.c  01-02-03 04:05:06\n"
                "@@ -1 +1,2 @@\n"
                "-tést content\n"
                "+updated test content\n"
                "+added info\n").encode('utf-8')

        files = self.tool.get_parser(diff).parse()
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0].origFile, 'tést.c')
        self.assertEqual(files[0].origInfo, '//depot/foo/proj/tést.c#2')
        self.assertEqual(files[0].newFile, 'tést.c')
        self.assertEqual(files[0].newInfo, '01-02-03 04:05:06')
        self.assertFalse(files[0].binary)
        self.assertFalse(files[0].deleted)
        self.assertFalse(files[0].moved)
        self.assertEqual(files[0].insert_count, 2)
        self.assertEqual(files[0].delete_count, 1)


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
        super(PerforceStunnelTests, self).tearDown()

        self.proxy.shutdown()

    def test_changeset(self):
        """Testing PerforceTool.get_changeset with stunnel"""
        desc = self.tool.get_changeset(157)

        self.assertEqual(desc.changenum, 157)
        self.assertEqual(md5(desc.description.encode('utf-8')).hexdigest(),
                         'b7eff0ca252347cc9b09714d07397e64')

        expected_files = [
            '//public/perforce/api/python/P4Client/P4Clientmodule.cc',
            '//public/perforce/api/python/P4Client/p4.py',
            '//public/perforce/api/python/P4Client/review.py',
            '//public/perforce/python/P4Client/P4Clientmodule.cc',
            '//public/perforce/python/P4Client/p4.py',
            '//public/perforce/python/P4Client/review.py',
        ]
        for file, expected in zip_longest(desc.files, expected_files):
            self.assertEqual(file, expected)

        self.assertEqual(md5(desc.summary.encode('utf-8')).hexdigest(),
                         '99a335676b0e5821ffb2f7469d4d7019')

    def test_get_file(self):
        """Testing PerforceTool.get_file with stunnel"""
        file = self.tool.get_file('//depot/foo', PRE_CREATION)
        self.assertEqual(file, '')

        try:
            file = self.tool.get_file(
                '//public/perforce/api/python/P4Client/p4.py', 1)
        except Exception as e:
            if six.text_type(e).startswith('Connect to server failed'):
                raise nose.SkipTest(
                    'Connection to public.perforce.com failed.  No internet?')
            else:
                raise
        self.assertEqual(md5(file).hexdigest(),
                         '227bdd87b052fcad9369e65c7bf23fd0')


class MercurialTests(SCMTestCase):
    """Unit tests for mercurial."""
    fixtures = ['test_scmtools']

    def setUp(self):
        super(MercurialTests, self).setUp()

        hg_repo_path = os.path.join(os.path.dirname(__file__),
                                    'testdata/hg_repo')
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
            self.tool.parse_diff_revision("/dev/null", "bf544ea505f8")[1])

    def test_diff_parser_new_file(self):
        """Testing HgDiffParser with a diff that creates a new file"""
        diffContents = (b'diff -r bf544ea505f8 readme\n'
                        b'--- /dev/null\n'
                        b'+++ b/readme\n')

        file = self._first_file_in_diff(diffContents)
        self.assertEqual(file.origFile, "readme")

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
        self.assertEqual(file.origInfo, "bf544ea505f8")
        self.assertEqual(file.origFile, "readme")
        self.assertEqual(file.newInfo, "Uncommitted")
        self.assertEqual(file.newFile, "readme")

    def test_diff_parser_committed(self):
        """Testing HgDiffParser with a diff between committed revisions"""
        diffContents = (b'diff -r 356a6127ef19 -r 4960455a8e88 readme\n'
                        b'--- a/readme\n'
                        b'+++ b/readme\n')

        file = self._first_file_in_diff(diffContents)
        self.assertEqual(file.origInfo, "356a6127ef19")
        self.assertEqual(file.origFile, "readme")
        self.assertEqual(file.newInfo, "4960455a8e88")
        self.assertEqual(file.newFile, "readme")

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
        self.assertEqual(file.origInfo, "356a6127ef19")
        self.assertEqual(file.origFile, "readme")
        self.assertEqual(file.newInfo, "4960455a8e88")
        self.assertEqual(file.newFile, "readme")

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
        self.assertEqual(file.origInfo, "bf544ea505f8")
        self.assertEqual(file.origFile, "path/to file/readme.txt")
        self.assertEqual(file.newInfo, "4960455a8e88")
        self.assertEqual(file.newFile, "new/path to/readme.txt")

    def test_diff_parser_unicode(self):
        """Testing HgDiffParser with unicode characters"""

        diffContents = ('diff -r bf544ea505f8 réadme\n'
                        '--- a/réadme\n'
                        '+++ b/réadme\n').encode('utf-8')

        file = self._first_file_in_diff(diffContents)
        self.assertEqual(file.origInfo, "bf544ea505f8")
        self.assertEqual(file.origFile, "réadme")
        self.assertEqual(file.newInfo, "Uncommitted")
        self.assertEqual(file.newFile, "réadme")

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
        self.assertEqual(file.origInfo, "bf544ea505f8")
        self.assertEqual(file.origFile, "path/to file/réadme.txt")
        self.assertEqual(file.newInfo, "4960455a8e88")
        self.assertEqual(file.newFile, "new/path to/réadme.txt")

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
        self.assertTrue(self.tool.get_diffs_use_absolute_paths())

        self.assertRaises(NotImplementedError,
                          lambda: self.tool.get_changeset(1))

        self.assertEqual(self.tool.get_fields(),
                         ['diff_path', 'parent_diff_path'])

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


class GitTests(SpyAgency, SCMTestCase):
    """Unit tests for Git."""
    fixtures = ['test_scmtools']

    def setUp(self):
        super(GitTests, self).setUp()

        tool = Tool.objects.get(name='Git')

        self.local_repo_path = os.path.join(os.path.dirname(__file__),
                                            'testdata', 'git_repo')
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
                                'testdata', filename)
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
            b"index 712544e4343bf04967eb5ea80257f6c64d6f42c7.."
            b"f88b7f15c03d141d0bb38c8e49bb6c411ebfe1f1 100644\n"
            b"--- a/README\t\n"
            b"+++ b/README\t\n"
            b"@ -1,1 +1,1 @@\n"
            b"-blah blah\n"
            b"+blah\n"
            b"-\n"
            b"1.7.1\n")

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
        self.assertEqual(len(file.data), 123)
        self.assertEqual(file.data.splitlines()[0],
                         "diff --git a/IAMNEW b/IAMNEW")
        self.assertEqual(file.data.splitlines()[-1], "+Hello")
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
        lines = file.data.splitlines()
        self.assertEqual(len(lines), 3)
        self.assertEqual(lines[0], "diff --git a/newfile b/newfile")
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
        lines = files[0].data.splitlines()
        self.assertEqual(len(lines), 3)
        self.assertEqual(lines[0], "diff --git a/newfile b/newfile")
        self.assertEqual(files[0].insert_count, 0)
        self.assertEqual(files[0].delete_count, 0)

        self.assertEqual(files[1].origFile, 'cfg/testcase.ini')
        self.assertEqual(files[1].newFile, 'cfg/testcase.ini')
        self.assertEqual(files[1].origInfo, 'cc18ec8')
        self.assertEqual(files[1].newInfo, '5e70b73')
        lines = files[1].data.splitlines()
        self.assertEqual(len(lines), 13)
        self.assertEqual(lines[0],
                         "diff --git a/cfg/testcase.ini b/cfg/testcase.ini")
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
        self.assertEqual(len(file.data), 132)
        self.assertEqual(file.data.splitlines()[0],
                         "diff --git a/OLDFILE b/OLDFILE")
        self.assertEqual(file.data.splitlines()[-1], "-Goodbye")
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
        self.assertEqual(len(files[0].data), 141)
        self.assertEqual(files[0].data.splitlines()[0],
                         "diff --git a/empty b/empty")
        self.assertEqual(files[0].insert_count, 0)
        self.assertEqual(files[0].delete_count, 0)

    def test_del_file_no_content_with_following_diff(self):
        """Testing parsing Git diff with deleted file, no content, with
        following"""
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
        self.assertEqual(len(files[0].data), 141)
        self.assertEqual(files[0].data.splitlines()[0],
                         "diff --git a/empty b/empty")
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
        lines = files[1].data.splitlines()
        self.assertEqual(len(lines), 7)
        self.assertEqual(lines[0], "diff --git a/foo/bar b/foo/bar")
        self.assertEqual(lines[5], "+Hello!")
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
        lines = file.data.splitlines()
        self.assertEqual(len(lines), 4)
        self.assertEqual(
            lines[0], "diff --git a/pysvn-1.5.1.tar.gz b/pysvn-1.5.1.tar.gz")
        self.assertEqual(
            lines[3], "Binary files /dev/null and b/pysvn-1.5.1.tar.gz differ")
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
        self.assertEqual(files[0].insert_count, 2)
        self.assertEqual(files[0].delete_count, 1)
        self.assertEqual(len(files[0].data), 549)
        self.assertEqual(files[0].data.splitlines()[0],
                         "diff --git a/cfg/testcase.ini b/cfg/testcase.ini")
        self.assertEqual(files[0].data.splitlines()[13],
                         "         if isinstance(value, basestring):")

        self.assertEqual(files[1].origFile, 'tests/models.py')
        self.assertEqual(files[1].newFile, 'tests/models.py')
        self.assertEqual(files[1].origInfo, PRE_CREATION)
        self.assertEqual(files[1].newInfo, 'e69de29')
        self.assertFalse(files[1].binary)
        self.assertFalse(files[1].deleted)
        self.assertEqual(files[1].insert_count, 0)
        self.assertEqual(files[1].delete_count, 0)
        lines = files[1].data.splitlines()
        self.assertEqual(len(lines), 3)
        self.assertEqual(lines[0],
                         "diff --git a/tests/models.py b/tests/models.py")

        self.assertEqual(files[2].origFile, 'tests/tests.py')
        self.assertEqual(files[2].newFile, 'tests/tests.py')
        self.assertEqual(files[2].origInfo, PRE_CREATION)
        self.assertEqual(files[2].newInfo, 'e279a06')
        self.assertFalse(files[2].binary)
        self.assertFalse(files[2].deleted)
        self.assertEqual(files[2].insert_count, 2)
        self.assertEqual(files[2].delete_count, 0)
        lines = files[2].data.splitlines()
        self.assertEqual(len(lines), 8)
        self.assertEqual(lines[0],
                         "diff --git a/tests/tests.py b/tests/tests.py")
        self.assertEqual(lines[7],
                         "+This is some new content")

        self.assertEqual(files[3].origFile, 'pysvn-1.5.1.tar.gz')
        self.assertEqual(files[3].newFile, 'pysvn-1.5.1.tar.gz')
        self.assertEqual(files[3].origInfo, PRE_CREATION)
        self.assertEqual(files[3].newInfo, '86b520c')
        self.assertTrue(files[3].binary)
        self.assertFalse(files[3].deleted)
        self.assertEqual(files[3].insert_count, 0)
        self.assertEqual(files[3].delete_count, 0)
        lines = files[3].data.splitlines()
        self.assertEqual(len(lines), 4)
        self.assertEqual(
            lines[0], "diff --git a/pysvn-1.5.1.tar.gz b/pysvn-1.5.1.tar.gz")
        self.assertEqual(lines[3],
                         'Binary files /dev/null and b/pysvn-1.5.1.tar.gz '
                         'differ')

        self.assertEqual(files[4].origFile, 'readme')
        self.assertEqual(files[4].newFile, 'readme')
        self.assertEqual(files[4].origInfo, '5e35098')
        self.assertEqual(files[4].newInfo, 'e254ef4')
        self.assertFalse(files[4].binary)
        self.assertFalse(files[4].deleted)
        self.assertEqual(files[4].insert_count, 1)
        self.assertEqual(files[4].delete_count, 1)
        lines = files[4].data.splitlines()
        self.assertEqual(len(lines), 7)
        self.assertEqual(lines[0], "diff --git a/readme b/readme")
        self.assertEqual(lines[6], "+Hello there")

        self.assertEqual(files[5].origFile, 'OLDFILE')
        self.assertEqual(files[5].newFile, 'OLDFILE')
        self.assertEqual(files[5].origInfo, '8ebcb01')
        self.assertEqual(files[5].newInfo, '0000000')
        self.assertFalse(files[5].binary)
        self.assertTrue(files[5].deleted)
        self.assertEqual(files[5].insert_count, 0)
        self.assertEqual(files[5].delete_count, 1)
        lines = files[5].data.splitlines()
        self.assertEqual(len(lines), 7)
        self.assertEqual(lines[0], "diff --git a/OLDFILE b/OLDFILE")
        self.assertEqual(lines[6], "-Goodbye")

        self.assertEqual(files[6].origFile, 'readme2')
        self.assertEqual(files[6].newFile, 'readme2')
        self.assertEqual(files[6].origInfo, '5e43098')
        self.assertEqual(files[6].newInfo, 'e248ef4')
        self.assertFalse(files[6].binary)
        self.assertFalse(files[6].deleted)
        self.assertEqual(files[6].insert_count, 1)
        self.assertEqual(files[6].delete_count, 1)
        lines = files[6].data.splitlines()
        self.assertEqual(len(lines), 7)
        self.assertEqual(lines[0], "diff --git a/readme2 b/readme2")
        self.assertEqual(lines[6], "+Hello there")

    def test_parse_diff_with_index_range(self):
        """Testing Git diff parsing with an index range"""
        diff = (b"diff --git a/foo/bar b/foo/bar2\n"
                b"similarity index 88%\n"
                b"rename from foo/bar\n"
                b"rename to foo/bar2\n"
                b"index 612544e4343bf04967eb5ea80257f6c64d6f42c7.."
                b"e88b7f15c03d141d0bb38c8e49bb6c411ebfe1f1 100644\n"
                b"--- a/foo/bar\n"
                b"+++ b/foo/bar2\n"
                b"@ -1,1 +1,1 @@\n"
                b"-blah blah\n"
                b"+blah\n")
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
        diff = (b"diff --git a/foo.bin b/foo.bin\n"
                b"deleted file mode 100644\n"
                b"Binary file foo.bin has changed\n"
                b"diff --git a/bar.bin b/bar.bin\n"
                b"deleted file mode 100644\n"
                b"Binary file bar.bin has changed\n")
        files = self.tool.get_parser(diff).parse()
        self.assertEqual(len(files), 2)
        self.assertEqual(files[0].origFile, 'foo.bin')
        self.assertEqual(files[0].newFile, 'foo.bin')
        self.assertEqual(files[0].binary, True)
        self.assertEqual(files[0].deleted, True)
        self.assertEqual(files[0].insert_count, 0)
        self.assertEqual(files[0].delete_count, 0)
        self.assertEqual(files[1].origFile, 'bar.bin')
        self.assertEqual(files[1].newFile, 'bar.bin')
        self.assertEqual(files[1].binary, True)
        self.assertEqual(files[1].deleted, True)
        self.assertEqual(files[1].insert_count, 0)
        self.assertEqual(files[1].delete_count, 0)

    def test_parse_diff_with_all_headers(self):
        """Testing Git diff parsing and preserving all headers"""
        preamble = (
            b"From 38d8fa94a9aa0c5b27943bec31d94e880165f1e0 Mon Sep "
            b"17 00:00:00 2001\n"
            b"From: Example Joe <joe@example.com>\n"
            b"Date: Thu, 5 Apr 2012 00:41:12 -0700\n"
            b"Subject: [PATCH 1/1] Sample patch.\n"
            b"\n"
            b"This is a test summary.\n"
            b"\n"
            b"With a description.\n"
            b"---\n"
            b" foo/bar |   2 -+n"
            b" README  |   2 -+n"
            b" 2 files changed, 2 insertions(+), 2 deletions(-)\n"
            b"\n")
        diff1 = (
            b"diff --git a/foo/bar b/foo/bar2\n"
            b"index 612544e4343bf04967eb5ea80257f6c64d6f42c7.."
            b"e88b7f15c03d141d0bb38c8e49bb6c411ebfe1f1 100644\n"
            b"--- a/foo/bar\n"
            b"+++ b/foo/bar2\n"
            b"@ -1,1 +1,1 @@\n"
            b"-blah blah\n"
            b"+blah\n")
        diff2 = (
            b"diff --git a/README b/README\n"
            b"index 712544e4343bf04967eb5ea80257f6c64d6f42c7.."
            b"f88b7f15c03d141d0bb38c8e49bb6c411ebfe1f1 100644\n"
            b"--- a/README\n"
            b"+++ b/README\n"
            b"@ -1,1 +1,1 @@\n"
            b"-blah blah\n"
            b"+blah\n"
            b"-\n"
            b"1.7.1\n")
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
                b'@ -1,1 +1,1 @@\n'
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
                b'@ -1,1 +1,1 @@\n'
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

        f = files[1]
        self.assertEqual(f.origFile, 'foo bar1')
        self.assertEqual(f.newFile, 'foo')

        f = files[2]
        self.assertEqual(f.origFile, 'foo')
        self.assertEqual(f.newFile, 'foo bar1')

    def test_file_exists(self):
        """Testing GitTool.file_exists"""

        self.assertTrue(self.tool.file_exists("readme", "e965047"))
        self.assertTrue(self.tool.file_exists("readme", "d6613f5"))

        self.assertTrue(not self.tool.file_exists("readme", PRE_CREATION))
        self.assertTrue(not self.tool.file_exists("readme", "fffffff"))
        self.assertTrue(not self.tool.file_exists("readme2", "fffffff"))

        # these sha's are valid, but commit and tree objects, not blobs
        self.assertTrue(not self.tool.file_exists("readme", "a62df6c"))
        self.assertTrue(not self.tool.file_exists("readme2", "ccffbb4"))

    def test_get_file(self):
        """Testing GitTool.get_file"""

        self.assertEqual(self.tool.get_file("readme", PRE_CREATION), b'')
        self.assertTrue(
            isinstance(self.tool.get_file("readme", "e965047"), bytes))
        self.assertEqual(self.tool.get_file("readme", "e965047"), b'Hello\n')
        self.assertEqual(self.tool.get_file("readme", "d6613f5"),
                         b'Hello there\n')

        self.assertEqual(self.tool.get_file("readme"), b'Hello there\n')

        self.assertRaises(SCMError, lambda: self.tool.get_file(""))

        self.assertRaises(FileNotFoundError,
                          lambda: self.tool.get_file("", "0000000"))
        self.assertRaises(FileNotFoundError,
                          lambda: self.tool.get_file("hello", "0000000"))
        self.assertRaises(FileNotFoundError,
                          lambda: self.tool.get_file("readme", "0000000"))

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
        repository or cache when raw file URL changes"""
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

class PolicyTests(TestCase):
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

        self.assertIn(self.repo, Repository.objects.accessible(self.user))
        self.assertTrue(
            self.repo in Repository.objects.accessible(self.anonymous))

    def test_repository_private_access_denied(self):
        """Testing no access to an inaccessible private repository"""
        self.repo.public = False
        self.repo.save()

        self.assertFalse(self.repo.is_accessible_by(self.user))
        self.assertFalse(self.repo.is_accessible_by(self.anonymous))

        self.assertNotIn(self.repo, Repository.objects.accessible(self.user))
        self.assertFalse(
            self.repo in Repository.objects.accessible(self.anonymous))

    def test_repository_private_access_allowed_by_user(self):
        """Testing access to a private repository accessible by user"""
        self.repo.users.add(self.user)
        self.repo.public = False
        self.repo.save()

        self.assertTrue(self.repo.is_accessible_by(self.user))
        self.assertFalse(self.repo.is_accessible_by(self.anonymous))

        self.assertIn(self.repo, Repository.objects.accessible(self.user))
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

        self.assertIn(self.repo, Repository.objects.accessible(self.user))
        self.assertFalse(
            self.repo in Repository.objects.accessible(self.anonymous))

    def test_repository_form_with_local_site_and_bad_group(self):
        """Testing adding a Group to a RepositoryForm with the wrong LocalSite
        """
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
        """Testing adding a User to a RepositoryForm with the wrong LocalSite
        """
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


class RepositoryFormTests(TestCase):
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

    def test_plain_repository(self):
        """Testing RepositoryForm with a plain repository"""
        form = RepositoryForm({
            'name': 'test',
            'hosting_type': 'custom',
            'tool': self.git_tool_id,
            'path': '/path/to/test.git',
            'bug_tracker_type': 'none',
        })

        self.assertTrue(form.is_valid())

        repository = form.save()
        self.assertEqual(repository.name, 'test')
        self.assertEqual(repository.hosting_account, None)
        self.assertEqual(repository.extra_data, {})

        # Make sure none of the other auth forms are unhappy. That would be
        # an indicator that we're doing form processing and validation wrong.
        for auth_form in six.itervalues(form.hosting_auth_forms):
            self.assertEqual(auth_form.errors, {})

    def test_plain_repository_with_missing_fields(self):
        """Testing RepositoryForm with a plain repository with missing fields
        """
        form = RepositoryForm({
            'name': 'test',
            'hosting_type': 'custom',
            'tool': self.git_tool_id,
            'bug_tracker_type': 'none',
        })

        self.assertFalse(form.is_valid())
        self.assertIn('path', form.errors)

        # Make sure none of the other auth forms are unhappy. That would be
        # an indicator that we're doing form processing and validation wrong.
        for auth_form in six.itervalues(form.hosting_auth_forms):
            self.assertEqual(auth_form.errors, {})

    def test_with_hosting_service_new_account(self):
        """Testing RepositoryForm with a hosting service and new account"""
        form = RepositoryForm({
            'name': 'test',
            'hosting_type': 'test',
            'test-hosting_account_username': 'testuser',
            'test-hosting_account_password': 'testpass',
            'tool': self.git_tool_id,
            'test_repo_name': 'testrepo',
            'bug_tracker_type': 'none',
        })

        self.assertTrue(form.is_valid())
        self.assertTrue(form.hosting_account_linked)

        repository = form.save()
        self.assertEqual(repository.name, 'test')
        self.assertEqual(repository.hosting_account.username, 'testuser')
        self.assertEqual(repository.hosting_account.service_name, 'test')
        self.assertEqual(repository.hosting_account.local_site, None)
        self.assertEqual(repository.extra_data['repository_plan'], '')
        self.assertEqual(repository.path, 'http://example.com/testrepo/')
        self.assertEqual(repository.mirror_path, '')

        # Make sure none of the other auth forms are unhappy. That would be
        # an indicator that we're doing form processing and validation wrong.
        for auth_form in six.itervalues(form.hosting_auth_forms):
            self.assertEqual(auth_form.errors, {})

    def test_with_hosting_service_new_account_auth_error(self):
        """Testing RepositoryForm with a hosting service and new account and
        authorization error
        """
        form = RepositoryForm({
            'name': 'test',
            'hosting_type': 'test',
            'test-hosting_account_username': 'baduser',
            'test-hosting_account_password': 'testpass',
            'tool': self.git_tool_id,
            'test_repo_name': 'testrepo',
            'bug_tracker_type': 'none',
        })

        self.assertFalse(form.is_valid())
        self.assertFalse(form.hosting_account_linked)
        self.assertIn('hosting_account', form.errors)
        self.assertEqual(form.errors['hosting_account'],
                         ['Unable to link the account: The username is '
                          'very very bad.'])

        # Make sure none of the other auth forms are unhappy. That would be
        # an indicator that we're doing form processing and validation wrong.
        for auth_form in six.itervalues(form.hosting_auth_forms):
            self.assertEqual(auth_form.errors, {})

    def test_with_hosting_service_new_account_2fa_code_required(self):
        """Testing RepositoryForm with a hosting service and new account and
        two-factor auth code required
        """
        form = RepositoryForm({
            'name': 'test',
            'hosting_type': 'test',
            'test-hosting_account_username': '2fa-user',
            'test-hosting_account_password': 'testpass',
            'tool': self.git_tool_id,
            'test_repo_name': 'testrepo',
            'bug_tracker_type': 'none',
        })

        self.assertFalse(form.is_valid())
        self.assertFalse(form.hosting_account_linked)
        self.assertIn('hosting_account', form.errors)
        self.assertEqual(form.errors['hosting_account'],
                         ['Enter your 2FA code.'])
        self.assertTrue(
            form.hosting_service_info['test']['needs_two_factor_auth_code'])

        # Make sure none of the other auth forms are unhappy. That would be
        # an indicator that we're doing form processing and validation wrong.
        for auth_form in six.itervalues(form.hosting_auth_forms):
            self.assertEqual(auth_form.errors, {})

    def test_with_hosting_service_new_account_2fa_code_provided(self):
        """Testing RepositoryForm with a hosting service and new account and
        two-factor auth code provided
        """
        form = RepositoryForm({
            'name': 'test',
            'hosting_type': 'test',
            'test-hosting_account_username': '2fa-user',
            'test-hosting_account_password': 'testpass',
            'test-hosting_account_two_factor_auth_code': '123456',
            'tool': self.git_tool_id,
            'test_repo_name': 'testrepo',
            'bug_tracker_type': 'none',
        })

        self.assertTrue(form.is_valid())
        self.assertTrue(form.hosting_account_linked)
        self.assertFalse(
            form.hosting_service_info['test']['needs_two_factor_auth_code'])

        # Make sure none of the other auth forms are unhappy. That would be
        # an indicator that we're doing form processing and validation wrong.
        for auth_form in six.itervalues(form.hosting_auth_forms):
            self.assertEqual(auth_form.errors, {})

    def test_with_hosting_service_new_account_missing_fields(self):
        """Testing RepositoryForm with a hosting service and new account and
        missing fields
        """
        form = RepositoryForm({
            'name': 'test',
            'hosting_type': 'test',
            'tool': self.git_tool_id,
            'test_repo_name': 'testrepo',
            'bug_tracker_type': 'none',
        })

        self.assertFalse(form.is_valid())
        self.assertFalse(form.hosting_account_linked)

        self.assertIn('hosting_account_username', form.errors)
        self.assertIn('hosting_account_password', form.errors)

        # Make sure the auth form also contains the errors.
        auth_form = form.hosting_auth_forms.pop('test')
        self.assertIn('hosting_account_username', auth_form.errors)
        self.assertIn('hosting_account_password', auth_form.errors)

        # Make sure none of the other auth forms are unhappy. That would be
        # an indicator that we're doing form processing and validation wrong.
        for auth_form in six.itervalues(form.hosting_auth_forms):
            self.assertEqual(auth_form.errors, {})

    def test_with_hosting_service_self_hosted_and_new_account(self):
        """Testing RepositoryForm with a self-hosted hosting service and new
        account
        """
        form = RepositoryForm({
            'name': 'test',
            'hosting_type': 'self_hosted_test',
            'self_hosted_test-hosting_url': 'https://myserver.com',
            'self_hosted_test-hosting_account_username': 'testuser',
            'self_hosted_test-hosting_account_password': 'testpass',
            'test_repo_name': 'myrepo',
            'tool': self.git_tool_id,
            'bug_tracker_type': 'none',
        })
        form.validate_repository = False

        self.assertTrue(form.is_valid())
        self.assertTrue(form.hosting_account_linked)

        repository = form.save()
        self.assertEqual(repository.name, 'test')
        self.assertEqual(repository.hosting_account.hosting_url,
                         'https://myserver.com')
        self.assertEqual(repository.hosting_account.username, 'testuser')
        self.assertEqual(repository.hosting_account.service_name,
                         'self_hosted_test')
        self.assertEqual(repository.hosting_account.local_site, None)
        self.assertEqual(repository.extra_data['test_repo_name'], 'myrepo')
        self.assertEqual(repository.extra_data['hosting_url'],
                         'https://myserver.com')
        self.assertEqual(repository.path, 'https://myserver.com/myrepo/')
        self.assertEqual(repository.mirror_path, 'git@myserver.com:myrepo/')

        # Make sure none of the other auth forms are unhappy. That would be
        # an indicator that we're doing form processing and validation wrong.
        for auth_form in six.itervalues(form.hosting_auth_forms):
            self.assertEqual(auth_form.errors, {})

    def test_with_hosting_service_self_hosted_and_blank_url(self):
        """Testing RepositoryForm with a self-hosted hosting service and blank
        URL
        """
        form = RepositoryForm({
            'name': 'test',
            'hosting_type': 'self_hosted_test',
            'self_hosted_test-hosting_url': '',
            'self_hosted_test-hosting_account_username': 'testuser',
            'self_hosted_test-hosting_account_password': 'testpass',
            'test_repo_name': 'myrepo',
            'tool': self.git_tool_id,
            'bug_tracker_type': 'none',
        })
        form.validate_repository = False

        self.assertFalse(form.is_valid())
        self.assertFalse(form.hosting_account_linked)

    def test_with_hosting_service_new_account_localsite(self):
        """Testing RepositoryForm with a hosting service, new account and
        LocalSite
        """
        local_site = LocalSite.objects.create(name='testsite')

        form = RepositoryForm(
            {
                'name': 'test',
                'hosting_type': 'test',
                'test-hosting_account_username': 'testuser',
                'test-hosting_account_password': 'testpass',
                'tool': self.git_tool_id,
                'test_repo_name': 'testrepo',
                'bug_tracker_type': 'none',
                'local_site': local_site.pk,
            },
            local_site_name=local_site.name)

        self.assertTrue(form.is_valid())
        self.assertTrue(form.hosting_account_linked)

        repository = form.save()
        self.assertEqual(repository.name, 'test')
        self.assertEqual(repository.local_site, local_site)
        self.assertEqual(repository.hosting_account.username, 'testuser')
        self.assertEqual(repository.hosting_account.service_name, 'test')
        self.assertEqual(repository.hosting_account.local_site, local_site)
        self.assertEqual(repository.extra_data['repository_plan'], '')

    def test_with_hosting_service_existing_account(self):
        """Testing RepositoryForm with a hosting service and existing
        account
        """
        account = HostingServiceAccount.objects.create(username='testuser',
                                                       service_name='test')
        account.data['password'] = 'testpass'
        account.save()

        form = RepositoryForm({
            'name': 'test',
            'hosting_type': 'test',
            'hosting_account': account.pk,
            'tool': self.git_tool_id,
            'test_repo_name': 'testrepo',
            'bug_tracker_type': 'none',
        })

        self.assertTrue(form.is_valid())
        self.assertFalse(form.hosting_account_linked)

        repository = form.save()
        self.assertEqual(repository.name, 'test')
        self.assertEqual(repository.hosting_account, account)
        self.assertEqual(repository.extra_data['repository_plan'], '')

    def test_with_hosting_service_existing_account_needs_reauth(self):
        """Testing RepositoryForm with a hosting service and existing
        account needing re-authorization
        """
        # We won't be setting the password, so that is_authorized() will
        # fail.
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

        self.assertFalse(form.is_valid())
        self.assertFalse(form.hosting_account_linked)
        self.assertEqual(set(form.errors.keys()),
                         set(['hosting_account_username',
                              'hosting_account_password']))

    def test_with_hosting_service_existing_account_reauthing(self):
        """Testing RepositoryForm with a hosting service and existing
        account with re-authorizating
        """
        # We won't be setting the password, so that is_authorized() will
        # fail.
        account = HostingServiceAccount.objects.create(username='testuser',
                                                       service_name='test')

        form = RepositoryForm({
            'name': 'test',
            'hosting_type': 'test',
            'hosting_account': account.pk,
            'test-hosting_account_username': 'testuser2',
            'test-hosting_account_password': 'testpass2',
            'tool': self.git_tool_id,
            'test_repo_name': 'testrepo',
            'bug_tracker_type': 'none',
        })

        self.assertTrue(form.is_valid())
        self.assertTrue(form.hosting_account_linked)

        account = HostingServiceAccount.objects.get(pk=account.pk)
        self.assertEqual(account.username, 'testuser2')
        self.assertEqual(account.data['password'], 'testpass2')

    def test_with_hosting_service_self_hosted_and_existing_account(self):
        """Testing RepositoryForm with a self-hosted hosting service and
        existing account
        """
        account = HostingServiceAccount.objects.create(
            username='testuser',
            service_name='self_hosted_test',
            hosting_url='https://example.com')
        account.data['password'] = 'testpass'
        account.save()

        form = RepositoryForm({
            'name': 'test',
            'hosting_type': 'self_hosted_test',
            'self_hosted_test-hosting_url': 'https://example.com',
            'hosting_account': account.pk,
            'tool': self.git_tool_id,
            'test_repo_name': 'myrepo',
            'bug_tracker_type': 'none',
        })
        form.validate_repository = False

        self.assertTrue(form.is_valid())
        self.assertFalse(form.hosting_account_linked)

        repository = form.save()
        self.assertEqual(repository.name, 'test')
        self.assertEqual(repository.hosting_account, account)
        self.assertEqual(repository.extra_data['hosting_url'],
                         'https://example.com')

    def test_with_self_hosted_and_invalid_account_service(self):
        """Testing RepositoryForm with a self-hosted hosting service and
        invalid existing account due to mismatched service type
        """
        account = HostingServiceAccount.objects.create(
            username='testuser',
            service_name='self_hosted_test',
            hosting_url='https://example1.com')
        account.data['password'] = 'testpass'
        account.save()

        form = RepositoryForm({
            'name': 'test',
            'hosting_type': 'test',
            'hosting_account': account.pk,
            'tool': self.git_tool_id,
            'test_repo_name': 'myrepo',
            'bug_tracker_type': 'none',
        })
        form.validate_repository = False

        self.assertFalse(form.is_valid())
        self.assertFalse(form.hosting_account_linked)

    def test_with_self_hosted_and_invalid_account_local_site(self):
        """Testing RepositoryForm with a self-hosted hosting service and
        invalid existing account due to mismatched Local Site
        """
        account = HostingServiceAccount.objects.create(
            username='testuser',
            service_name='self_hosted_test',
            hosting_url='https://example1.com',
            local_site=LocalSite.objects.create(name='test-site'))
        account.data['password'] = 'testpass'
        account.save()

        form = RepositoryForm({
            'name': 'test',
            'hosting_type': 'test',
            'hosting_account': account.pk,
            'tool': self.git_tool_id,
            'test_repo_name': 'myrepo',
            'bug_tracker_type': 'none',
        })
        form.validate_repository = False

        self.assertFalse(form.is_valid())
        self.assertFalse(form.hosting_account_linked)

    def test_with_hosting_service_custom_bug_tracker(self):
        """Testing RepositoryForm with a custom bug tracker"""
        account = HostingServiceAccount.objects.create(username='testuser',
                                                       service_name='test')
        account.data['password'] = 'testpass'
        account.save()

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
        self.assertNotIn('bug_tracker_type', repository.extra_data)

    def test_with_hosting_service_bug_tracker_service(self):
        """Testing RepositoryForm with a bug tracker service"""
        account = HostingServiceAccount.objects.create(username='testuser',
                                                       service_name='test')
        account.data['password'] = 'testpass'
        account.save()

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
        account.data['password'] = 'testpass'
        account.save()

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
        account.data['password'] = 'testpass'
        account.save()

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
        self.assertNotIn('bug_tracker_type', repository.extra_data)
        self.assertFalse('bug_tracker-test_repo_name'
                         in repository.extra_data)
        self.assertFalse('bug_tracker-hosting_account_username'
                         in repository.extra_data)

    def test_with_hosting_service_with_hosting_bug_tracker_and_self_hosted(
            self):
        """Testing RepositoryForm with self-hosted hosting service's bug
        tracker
        """
        account = HostingServiceAccount.objects.create(
            username='testuser',
            service_name='self_hosted_test',
            hosting_url='https://example.com')
        account.data['password'] = 'testpass'
        account.save()

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
        self.assertNotIn('bug_tracker_type', repository.extra_data)
        self.assertFalse('bug_tracker-test_repo_name'
                         in repository.extra_data)
        self.assertFalse('bug_tracker_hosting_url'
                         in repository.extra_data)

    def test_with_hosting_service_no_bug_tracker(self):
        """Testing RepositoryForm with no bug tracker"""
        account = HostingServiceAccount.objects.create(username='testuser',
                                                       service_name='test')
        account.data['password'] = 'testpass'
        account.save()

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
        self.assertNotIn('bug_tracker_type', repository.extra_data)

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

        self.assertIn('test', form.bug_tracker_forms)
        self.assertIn('default', form.bug_tracker_forms['test'])
        bitbucket_form = form.bug_tracker_forms['test']['default']
        self.assertEqual(
            bitbucket_form.fields['test_repo_name'].initial,
            'testrepo')

    def test_with_hosting_service_with_existing_bug_tracker_using_hosting(
            self):
        """Testing RepositoryForm with existing bug tracker using hosting
        service
        """
        account = HostingServiceAccount.objects.create(username='testuser',
                                                       service_name='test')
        repository = Repository(name='test',
                                hosting_account=account)
        repository.extra_data['bug_tracker_use_hosting'] = True
        repository.extra_data['test_repo_name'] = 'testrepo'

        form = RepositoryForm(instance=repository)
        self.assertTrue(form._get_field_data('bug_tracker_use_hosting'))
