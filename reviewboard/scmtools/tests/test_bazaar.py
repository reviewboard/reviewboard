from __future__ import unicode_literals

import os

import nose
from django.utils import six

from reviewboard.scmtools.errors import SCMError
from reviewboard.scmtools.models import Repository, Tool
from reviewboard.scmtools.tests.testcases import SCMTestCase


class BZRTests(SCMTestCase):
    """Unit tests for bzr."""

    fixtures = ['test_scmtools']

    def setUp(self):
        super(BZRTests, self).setUp()

        self.bzr_repo_path = os.path.join(os.path.dirname(__file__),
                                          '..', 'testdata', 'bzr_repo')
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
