import logging
import os
from tempfile import mkdtemp
from unittest import SkipTest

from paramiko.ssh_exception import NoValidConnectionsError

from reviewboard.scmtools.core import HEAD
from reviewboard.scmtools.errors import SCMError, AuthenticationError
from reviewboard.scmtools.models import Repository
from reviewboard.site.models import LocalSite
from reviewboard.ssh.client import SSHClient
from reviewboard.ssh.tests import SSHTestCase


logger = logging.getLogger(__name__)


class SCMTestCase(SSHTestCase):
    """Base class for test suites for SCMTools."""

    ssh_client = None

    #: Executables that must be available system-wide for SSH tests.
    #:
    #: SSH tests often require running a command over SSH. These commands
    #: may be available in the local virtualenv where development is taking
    #: place, but may not be available system-wide.
    #:
    #: If this is specified, and the command is not available in the system
    #: path when connecting, the test will be skipped.
    #:
    #: Version Added:
    #:     5.0
    #:
    #: Type:
    #:     list of unicode
    ssh_required_system_exes = None

    _can_test_ssh = None
    _ssh_system_exe_status = {}

    def setUp(self):
        super(SCMTestCase, self).setUp()
        self.tool = None

    def _check_can_test_ssh(self):
        """Check whether SSH-based tests can be run.

        This will check if the user's SSH keys are authorized by the local
        machine for authentication, and whether any system-wide tools are
        available.

        If SSH-based tests cannot be run, the current test will be flagged
        as skipped.
        """
        # These tests are global across all unit tests using this class.
        if SCMTestCase._can_test_ssh is None:
            SCMTestCase.ssh_client = SSHClient()
            key = self.ssh_client.get_user_key()
            SCMTestCase._can_test_ssh = (
                key is not None and
                self.ssh_client.is_key_authorized(key))

        if not SCMTestCase._can_test_ssh:
            raise SkipTest(
                "Cannot perform SSH access tests. The local user's SSH "
                "public key must be in the %s file and SSH must be enabled."
                % os.path.join(self.ssh_client.storage.get_ssh_dir(),
                               'authorized_keys'))

        # These tests are local to all unit tests using the same executable.
        system_exes = self.ssh_required_system_exes

        if system_exes:
            user_key = SCMTestCase.ssh_client.get_user_key()

            exes_to_check = (
                set(system_exes) -
                set(SCMTestCase._ssh_system_exe_status.keys()))

            for system_exe in exes_to_check:
                # For safety, we'll do one connection per check, to avoid
                # one check impacting another.
                client = SSHClient()
                client.connect('localhost',
                               pkey=user_key)

                try:
                    stdout, stderr = client.exec_command('which %s'
                                                         % system_exe)[1:]

                    # It's important to read all stdout/stderr data before
                    # waiting for status.
                    stdout.read()
                    stderr.read()
                    code = stdout.channel.recv_exit_status()

                    status = (code == 0)
                except Exception as e:
                    logger.error('Unexpected error running `which %s` on '
                                 'localhost for SSH test: %s',
                                 system_exe, e)
                    status = False
                finally:
                    client.close()

                SCMTestCase._ssh_system_exe_status[system_exe] = status

            missing_exes = ', '.join(
                '"%s"' % _system_exe
                for _system_exe in system_exes
                if not SCMTestCase._ssh_system_exe_status[_system_exe]
            )

            if missing_exes:
                raise SkipTest(
                    'Cannot perform SSH access tests. %s must be '
                    'available in the system path when executing '
                    'commands locally over SSH. You may need to install the '
                    'tool or make sure that the correct directory is in '
                    '~/.zshenv, ~/.profile, or another suitable file used '
                    'in non-interactive sessions.'
                    % missing_exes)

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

        repo = Repository(
            name='SSH Test',
            path=repo_path,
            tool=self.repository.tool,
            scmtool_id=self.repository.scmtool_id)
        tool = repo.get_scmtool()

        try:
            tool.check_repository(repo_path)
        except NoValidConnectionsError:
            # This box likely isn't set up for this test.
            SCMTestCase._can_test_ssh = False

            raise SkipTest(
                'Cannot perform SSH access tests. No local SSH service is '
                'running.')

        if filename:
            self.assertIsNotNone(tool.get_file(filename, HEAD))

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
        self.assertIsNotNone(user_key)

        # Switch to a new SSH directory.
        self.tempdir = mkdtemp(prefix='rb-tests-home-')
        sshdir = os.path.join(self.tempdir, '.ssh')
        self._set_home(self.tempdir)

        self.assertEqual(sshdir, self.ssh_client.storage.get_ssh_dir())
        self.assertFalse(os.path.exists(os.path.join(sshdir, 'id_rsa')))
        self.assertFalse(os.path.exists(os.path.join(sshdir, 'id_dsa')))
        self.assertIsNone(self.ssh_client.get_user_key())

        tool_class = self.repository.tool

        # Make sure we aren't using the old SSH key. We want auth errors.
        repo = self.create_repository(name='SSH Test',
                                      path=repo_path,
                                      tool_name=tool_class.name)
        tool = repo.get_scmtool()
        self.assertRaises(AuthenticationError,
                          lambda: tool.check_repository(repo_path))

        if filename:
            self.assertRaises(SCMError,
                              lambda: tool.get_file(filename, HEAD))

        for local_site_name in ('site-1',):
            local_site = LocalSite(name=local_site_name)
            local_site.save()

            repo = self.create_repository(
                name='SSH Test',
                path=repo_path,
                tool_name=tool_class.name,
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
                self.assertIsNotNone(tool.get_file(filename, HEAD))
