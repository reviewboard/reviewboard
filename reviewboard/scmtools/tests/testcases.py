from __future__ import unicode_literals

import os
from errno import ECONNREFUSED
from socket import error as SocketError
from tempfile import mkdtemp

import nose

from reviewboard.scmtools.core import HEAD
from reviewboard.scmtools.errors import SCMError, AuthenticationError
from reviewboard.scmtools.models import Repository
from reviewboard.site.models import LocalSite
from reviewboard.ssh.client import SSHClient
from reviewboard.ssh.tests import SSHTestCase


class SCMTestCase(SSHTestCase):
    """Base class for test suites for SCMTools."""

    ssh_client = None
    _can_test_ssh = None

    def setUp(self):
        super(SCMTestCase, self).setUp()
        self.tool = None

    def _check_can_test_ssh(self):
        """Check whether SSH-based tests can be run.

        This will check if the user's SSH keys is authorized by the local
        machine, for authentication. If so, SSH-based tests can be attempted.

        If SSH-based tests cannot be run, the current test will be flagged
        as skipped.
        """
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
        """Helper for testing an SSH connection to a local repository.

        This will attempt to SSH into the local machine and connect to the
        given repository, checking it for validity and optionally fetching
        a file.

        If this is unable to connect to the local machine, the test will be
        flagged as skipped.

        Args:
            repo_path (unicode):
                The repository path to check.

            filename (unicode, optional):
                The optional file in the repository to fetch.
        """
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
                    'Cannot perform SSH access tests. No local SSH service is '
                    'running.')
            else:
                raise

        if filename:
            self.assertNotEqual(tool.get_file(filename, HEAD), None)

    def _test_ssh_with_site(self, repo_path, filename=None):
        """Helper for testing an SSH connection and using a Local Site.

        This will attempt to SSH into the local machine and connect to the
        given repository, using an SSH key and repository based on a Local
        Site. It will check the repository for validity and optionally fetch
        a file.

        If this is unable to connect to the local machine, the test will be
        flagged as skipped.

        Args:
            repo_path (unicode):
                The repository path to check.

            filename (unicode, optional):
                The optional file in the repository to fetch.
        """
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
