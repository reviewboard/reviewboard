from __future__ import unicode_literals

import os

import nose
from django.utils import six
from djblets.util.filesystem import is_exe_in_path

from reviewboard.scmtools.errors import (FileNotFoundError,
                                         InvalidRevisionFormatError,
                                         RepositoryNotFoundError, SCMError)
from reviewboard.scmtools.models import Repository, Tool
from reviewboard.scmtools.tests.testcases import SCMTestCase


class BZRTests(SCMTestCase):
    """Unit tests for bzr."""

    fixtures = ['test_scmtools']

    def setUp(self):
        super(BZRTests, self).setUp()

        if not is_exe_in_path('bzr'):
            raise nose.SkipTest()

        self.bzr_repo_path = os.path.join(os.path.dirname(__file__),
                                          '..', 'testdata', 'bzr_repo')
        self.bzr_ssh_path = ('bzr+ssh://localhost/%s'
                             % self.bzr_repo_path.replace('\\', '/'))
        self.bzr_sftp_path = ('sftp://localhost/%s'
                              % self.bzr_repo_path.replace('\\', '/'))
        self.repository = Repository(name='Bazaar',
                                     path='file://' + self.bzr_repo_path,
                                     tool=Tool.objects.get(name='Bazaar'))

        self.tool = self.repository.get_scmtool()

    def test_check_repository(self):
        """Testing BZRTool.check_repository"""
        self.tool.check_repository(self.repository.path)

    def test_check_repository_with_not_found(self):
        """Testing BZRTool.check_repository with repository not found"""
        with self.assertRaises(RepositoryNotFoundError):
            self.tool.check_repository('file:///dummy')

    def test_ssh(self):
        """Testing BZRTool with a SSH-backed repository"""
        self._test_ssh(self.bzr_ssh_path, 'README')

    def test_ssh_with_site(self):
        """Testing BZRTool with a SSH-backed repository with a LocalSite"""
        self._test_ssh_with_site(self.bzr_ssh_path, 'README')

    def test_sftp(self):
        """Testing BZRTool with a SFTP-backed repository"""
        try:
            self._test_ssh(self.bzr_sftp_path, 'README')
        except SCMError as e:
            err = six.text_type(e)

            if 'Installed bzr and paramiko modules are incompatible' in err:
                raise nose.SkipTest(err)

            raise

    def test_get_file(self):
        """Testing BZRTool.get_file"""
        content = self.tool.get_file('README', '2011-02-02 10:53:04 +0000')
        self.assertEqual(content, b'This is a test.\n')
        self.assertIsInstance(content, bytes)

    def test_get_file_with_timezone_offset(self):
        """Testing BZRTool.get_file with timezone offset"""
        content = self.tool.get_file('README', '2011-02-02 02:53:04 -0800')
        self.assertEqual(content, b'This is a test.\n')
        self.assertIsInstance(content, bytes)

    def test_get_file_with_non_utc_server_timezone(self):
        """Testing BZRTool.get_file with settings.TIME_ZONE != UTC"""
        old_timezone = os.environ[b'TZ']
        os.environ[b'TZ'] = b'US/Pacific'

        try:
            content = self.tool.get_file('README', '2011-02-02 02:53:04 -0800')
        finally:
            os.environ[b'TZ'] = old_timezone

        self.assertEqual(content, b'This is a test.\n')
        self.assertIsInstance(content, bytes)

    def test_get_file_with_revision_id(self):
        """Testing BZRTool.get_file with revision ID"""
        content = self.tool.get_file(
            'README',
            'revid:chipx86@chipx86.com-20110202105304-8lkgyb18aqr11b21')
        self.assertEqual(content, b'This is a test.\n')
        self.assertIsInstance(content, bytes)

    def test_get_file_with_unknown_file(self):
        """Testing BZRTool.get_file with unknown file"""
        with self.assertRaises(FileNotFoundError):
            self.tool.get_file('NOT_REAL', '2011-02-02 02:53:04 -0800')

    def test_get_file_with_unknown_revision(self):
        """Testing BZRTool.get_file with unknown revision"""
        with self.assertRaises(FileNotFoundError):
            self.tool.get_file('README', '9999-02-02 02:53:04 -0800')

    def test_get_file_with_invalid_revision(self):
        """Testing BZRTool.get_file with invalid revision"""
        with self.assertRaises(InvalidRevisionFormatError):
            self.tool.get_file('README', '\o/')

    def test_file_exists(self):
        """Testing BZRTool.files_exists"""
        self.assertTrue(self.tool.file_exists(
            'README',
            '2011-02-02 10:53:04 +0000'))

        self.assertFalse(self.tool.file_exists(
            'NOT_REAL',
            '2011-02-02 10:53:04 +0000'))
        self.assertFalse(self.tool.file_exists(
            'README',
            '9999-02-02 10:53:04 +0000'))

    def test_file_exists_with_timezone_offset(self):
        """Testing BZRTool.files_exists with timezone offset"""
        self.assertTrue(self.tool.file_exists(
            'README',
            '2011-02-02 02:53:04 -0800'))

    def test_file_exists_with_non_utc_server_timezone(self):
        """Testing BZRTool.files_exists with settings.TIME_ZONE != UTC"""
        old_timezone = os.environ[b'TZ']
        os.environ[b'TZ'] = b'US/Pacific'

        try:
            self.assertTrue(self.tool.file_exists(
                'README',
                '2011-02-02 02:53:04 -0800'))
        finally:
            os.environ[b'TZ'] = old_timezone

    def test_file_exists_with_revision_id(self):
        """Testing BZRTool.files_exists with revision ID"""
        self.assertTrue(self.tool.file_exists(
            'README',
            'revid:chipx86@chipx86.com-20110202105304-8lkgyb18aqr11b21'))

    def test_file_exists_with_invalid_revision(self):
        """Testing BZRTool.files_exists with invalid revision"""
        with self.assertRaises(InvalidRevisionFormatError):
            self.tool.file_exists('README', '\o/')
