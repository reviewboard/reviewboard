from __future__ import unicode_literals

import os

import nose
from django.utils import six
from djblets.testing.decorators import add_fixtures
from djblets.util.filesystem import is_exe_in_path

from reviewboard.scmtools.bzr import BZRTool
from reviewboard.scmtools.errors import (FileNotFoundError,
                                         InvalidRevisionFormatError,
                                         RepositoryNotFoundError, SCMError)
from reviewboard.scmtools.models import Repository, Tool
from reviewboard.scmtools.tests.testcases import SCMTestCase
from reviewboard.testing.testcase import TestCase


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
        old_timezone = os.environ[str('TZ')]
        os.environ[str('TZ')] = str('US/Pacific')

        try:
            content = self.tool.get_file('README', '2011-02-02 02:53:04 -0800')
        finally:
            os.environ[str('TZ')] = old_timezone

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
        old_timezone = os.environ[str('TZ')]
        os.environ[str('TZ')] = str('US/Pacific')

        try:
            self.assertTrue(self.tool.file_exists(
                'README',
                '2011-02-02 02:53:04 -0800'))
        finally:
            os.environ[str('TZ')] = old_timezone

    def test_file_exists_with_revision_id(self):
        """Testing BZRTool.files_exists with revision ID"""
        self.assertTrue(self.tool.file_exists(
            'README',
            'revid:chipx86@chipx86.com-20110202105304-8lkgyb18aqr11b21'))

    def test_file_exists_with_invalid_revision(self):
        """Testing BZRTool.files_exists with invalid revision"""
        with self.assertRaises(InvalidRevisionFormatError):
            self.tool.file_exists('README', '\o/')


class BZRAuthFormTests(TestCase):
    """Unit tests for BZRTool's authentication form."""

    def test_fields(self):
        """Testing BZRTool authentication form fields"""
        form = BZRTool.create_auth_form()

        self.assertEqual(list(form.fields), ['username', 'password'])
        self.assertEqual(form['username'].help_text, '')
        self.assertEqual(form['username'].label, 'Username')
        self.assertEqual(form['password'].help_text, '')
        self.assertEqual(form['password'].label, 'Password')

    @add_fixtures(['test_scmtools'])
    def test_load(self):
        """Tetting BZRTool authentication form load"""
        repository = self.create_repository(
            tool_name='Bazaar',
            username='test-user',
            password='test-pass')

        form = BZRTool.create_auth_form(repository=repository)
        form.load()

        self.assertEqual(form['username'].value(), 'test-user')
        self.assertEqual(form['password'].value(), 'test-pass')

    @add_fixtures(['test_scmtools'])
    def test_save(self):
        """Tetting BZRTool authentication form save"""
        repository = self.create_repository(tool_name='Bazaar')

        form = BZRTool.create_auth_form(
            repository=repository,
            data={
                'username': 'test-user',
                'password': 'test-pass',
            })
        self.assertTrue(form.is_valid())
        form.save()

        self.assertEqual(repository.username, 'test-user')
        self.assertEqual(repository.password, 'test-pass')


class BZRRepositoryFormTests(TestCase):
    """Unit tests for BZRTool's repository form."""

    def test_fields(self):
        """Testing BZRTool repository form fields"""
        form = BZRTool.create_repository_form()

        self.assertEqual(list(form.fields), ['path', 'mirror_path'])
        self.assertEqual(form['path'].help_text,
                         'The path to the repository. This will generally be '
                         'the URL you would use to check out the repository.')
        self.assertEqual(form['path'].label, 'Path')
        self.assertEqual(form['mirror_path'].help_text, '')
        self.assertEqual(form['mirror_path'].label, 'Mirror Path')

    @add_fixtures(['test_scmtools'])
    def test_load(self):
        """Tetting BZRTool repository form load"""
        repository = self.create_repository(
            tool_name='Bazaar',
            path='bzr+ssh://bzr.example.com/repo',
            mirror_path='sftp://bzr.example.com/repo')

        form = BZRTool.create_repository_form(repository=repository)
        form.load()

        self.assertEqual(form['path'].value(),
                         'bzr+ssh://bzr.example.com/repo')
        self.assertEqual(form['mirror_path'].value(),
                         'sftp://bzr.example.com/repo')

    @add_fixtures(['test_scmtools'])
    def test_save(self):
        """Tetting BZRTool repository form save"""
        repository = self.create_repository(tool_name='Bazaar')

        form = BZRTool.create_repository_form(
            repository=repository,
            data={
                'path': 'bzr+ssh://bzr.example.com/repo',
                'mirror_path': 'sftp://bzr.example.com/repo',
            })
        self.assertTrue(form.is_valid())
        form.save()

        self.assertEqual(repository.path, 'bzr+ssh://bzr.example.com/repo')
        self.assertEqual(repository.mirror_path, 'sftp://bzr.example.com/repo')
