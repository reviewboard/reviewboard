from __future__ import unicode_literals

import os

import nose

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
        self._test_ssh(self.bzr_sftp_path, 'README')
