# coding=utf-8

from __future__ import annotations

import os
import shutil
import subprocess
import time
import unittest
from hashlib import md5
from tempfile import mkdtemp
from typing import TYPE_CHECKING, cast

try:
    import P4
    from P4 import P4Exception
except ImportError:
    P4 = None
    P4Exception = None

from django.conf import settings
from djblets.testing.decorators import add_fixtures
from djblets.util.filesystem import is_exe_in_path
from kgb import SpyAgency

from reviewboard.diffviewer.testing.mixins import DiffParserTestingMixin
from reviewboard.scmtools.core import PRE_CREATION
from reviewboard.scmtools.errors import (AuthenticationError,
                                         RepositoryNotFoundError,
                                         SCMError,
                                         UnverifiedCertificateError)
from reviewboard.scmtools.models import Repository, Tool
from reviewboard.scmtools.perforce import PerforceTool, STunnelProxy
from reviewboard.scmtools.tests.testcases import SCMTestCase
from reviewboard.site.models import LocalSite
from reviewboard.testing.testcase import TestCase

if TYPE_CHECKING:
    from typing import ClassVar

    from typing_extensions import Self


has_p4 = is_exe_in_path('p4')
has_p4d = is_exe_in_path('p4d')


if P4 is not None:
    class DummyP4(P4.P4):
        """A dummy wrapper around P4 that does not connect.

        This is used for certain tests that need to simulate connecting without
        actually talking to a server.
        """

        def connect(self) -> Self:
            """Connect to the server."""
            return self
else:
    DummyP4 = None  # type: ignore


@unittest.skipIf(P4 is None, 'The p4python module is not installed')
@unittest.skipIf(not has_p4, 'The p4 command line tool is not installed')
class BasePerforceTestCase(SpyAgency, SCMTestCase):
    """Base class for all Perforce tests.

    This will set up a local p4d server for use by tests which need to connect
    to a real server.
    """

    #: The local p4d process.
    p4d_process: ClassVar[subprocess.Popen[str]]

    @classmethod
    def setUpClass(cls) -> None:
        """Set up the test case class.

        Raises:
            RuntimeError:
                The local p4d failed to start.
        """
        super().setUpClass()

        p4_repo = os.path.join(os.path.dirname(__file__),
                               '..', 'testdata', 'p4_repo')

        local_repo_path = mkdtemp(prefix='rb-tests-perforce-')
        os.rmdir(local_repo_path)
        shutil.copytree(p4_repo, local_repo_path)
        cls.local_repo_path = local_repo_path

        if has_p4d:
            cls.p4d_process = subprocess.Popen(
                ['p4d', '-p', '61666', '-r', local_repo_path],
                text=True,
            )

            # Poll until `p4 info` succeeds.
            timeout = 5.0  # seconds
            poll_interval = 0.1  # seconds
            elapsed = 0.0

            while elapsed < timeout:
                try:
                    result = subprocess.run(
                        ['p4', '-p', 'localhost:61666', 'info'],
                        capture_output=True,
                        timeout=1.0,
                        check=True,
                    )
                    if result.returncode == 0:
                        break
                except (subprocess.TimeoutExpired,
                        subprocess.CalledProcessError):
                    pass

                time.sleep(poll_interval)
                elapsed += poll_interval
            else:
                # If we get here, we timed out.
                cls.p4d_process.terminate()
                raise RuntimeError('p4d failed to start within timeout period')

    @classmethod
    def tearDownClass(cls) -> None:
        """Tear down the test case class."""
        super().tearDownClass()

        if has_p4d:
            try:
                cls.p4d_process.terminate()
                cls.p4d_process.wait()
            finally:
                shutil.rmtree(cls.local_repo_path)


class PerforceTests(DiffParserTestingMixin, BasePerforceTestCase):
    """Unit tests for Perforce."""

    fixtures = ['test_scmtools']
    tool: PerforceTool

    def setUp(self) -> None:
        """Set up the test case."""
        super().setUp()

        self.repository = self.create_repository(
            name='localhost',
            path='localhost:61666',
            username='guest',
            encoding='none',
            tool_name='Perforce')
        self.tool = cast(PerforceTool, self.repository.get_scmtool())

    def tearDown(self) -> None:
        """Tear down the test case."""
        super().tearDown()

        shutil.rmtree(os.path.join(settings.SITE_DATA_DIR, 'p4'),
                      ignore_errors=True)

    def test_init_with_p4_client(self) -> None:
        """Testing PerforceTool.__init__ with p4_client"""
        self.repository.extra_data['p4_client'] = 'test-client'

        tool = PerforceTool(self.repository)
        self.assertIsInstance(tool.client.client_name, str)
        self.assertEqual(tool.client.client_name, 'test-client')

    def test_init_with_p4_client_none(self) -> None:
        """Testing PerforceTool.__init__ with p4_client=None"""
        self.repository.extra_data['p4_client'] = None

        tool = PerforceTool(self.repository)
        self.assertIsNone(tool.client.client_name)

    def test_init_without_p4_client(self) -> None:
        """Testing PerforceTool.__init__ without p4_client"""
        self.assertIsNone(self.tool.client.client_name)

    def test_init_with_p4_host(self) -> None:
        """Testing PerforceTool.__init__ with p4_host"""
        self.repository.extra_data['p4_host'] = 'test-host'

        tool = PerforceTool(self.repository)
        self.assertIsInstance(tool.client.p4host, str)
        self.assertEqual(tool.client.p4host, 'test-host')

    def test_init_with_p4_host_none(self) -> None:
        """Testing PerforceTool.__init__ with p4_host=None"""
        self.repository.extra_data['p4_host'] = None

        tool = PerforceTool(self.repository)
        self.assertIsNone(tool.client.p4host)

    def test_init_without_p4_host(self) -> None:
        """Testing PerforceTool.__init__ without p4_host"""
        self.assertIsNone(self.tool.client.p4host)

    def test_connect_sets_required_client_args(self) -> None:
        """Testing PerforceTool.connect sets required client args"""
        self.repository.username = 'test-user'
        self.repository.password = 'test-pass'
        self.repository.encoding = 'utf8'
        self.repository.extra_data['use_ticket_auth'] = False

        tool = PerforceTool(self.repository)
        p4 = DummyP4()
        client = tool.client
        client.p4 = p4

        # Note that P4 will use the native string type on each major version
        # of Python. We want to sanity-check that here.
        with client.connect():
            self.assertEqual(p4.exception_level, 1)

            self.assertIsInstance(p4.user, str)
            self.assertEqual(p4.user, 'test-user')

            self.assertIsInstance(p4.password, str)
            self.assertEqual(p4.password, 'test-pass')

            self.assertIsInstance(p4.charset, str)
            self.assertEqual(p4.charset, 'utf8')

            self.assertIsInstance(p4.port, str)
            self.assertEqual(p4.port, 'localhost:61666')

            # Perforce will set a default for the host and client. They'll
            # be the same. We don't care what they are, just that they're
            # equal and of the right string type, and not "none".
            self.assertIsInstance(p4.host, str)
            self.assertIsInstance(p4.client, str)
            self.assertEqual(p4.host.split('.')[0], p4.client)
            self.assertNotEqual(p4.client.lower(), 'none')

            # Perforce will set the ticket file to be in the user's home
            # directory. We don't care about the exact contents, and will
            # just look at the filename.
            self.assertIsInstance(p4.ticket_file, str)
            self.assertTrue(p4.ticket_file.endswith('.p4tickets'))

    def test_connect_sets_optional_client_args(self) -> None:
        """Testing PerforceTool.connect sets optional client args"""
        self.repository.extra_data.update({
            'use_ticket_auth': True,
            'p4_client': 'test-client',
            'p4_host': 'test-host',
        })

        tool = PerforceTool(self.repository)
        p4 = DummyP4()
        client = tool.client
        client.p4 = p4

        self.spy_on(client.check_refresh_ticket, call_original=False)

        # Note that P4 will use the native string type on each major version
        # of Python. We want to sanity-check that here.
        with client.connect():
            self.assertIsInstance(p4.client, str)
            self.assertEqual(p4.client, 'test-client')

            self.assertIsInstance(p4.host, str)
            self.assertEqual(p4.host, 'test-host')

            self.assertIsInstance(p4.ticket_file, str)
            self.assertTrue(p4.ticket_file.endswith(
                os.path.join('data', 'p4', 'p4tickets')))

    def test_run_worker_with_unverified_cert(self) -> None:
        """Testing PerforceTool.run_worker with unverified certificate"""
        self.repository.path = 'p4.example.com:1666'
        self.repository.username = 'test-user'
        self.repository.password = 'test-pass'
        self.repository.encoding = 'utf8'
        self.repository.extra_data['use_ticket_auth'] = False

        tool = PerforceTool(self.repository)
        p4 = DummyP4()
        client = tool.client
        client.p4 = p4

        fingerprint = \
            'A0:B1:C2:D3:E4:F5:6A:7B:8C:9D:E0:F1:2A:3B:4C:5D:6E:7F:A1:B2'

        err_msg = (
            f"The authenticity of '1.2.3.4' can't be established,\\n"
            f"this may be your first attempt to connect to this P4PORT.\\n"
            f"The fingerprint for the key sent to your client is\\n"
            f"{fingerprint}\\n"
            f"To allow connection use the 'p4 trust' command.\\n"
        )

        expected_msg = (
            f'The SSL certificate for this repository (hostname '
            f'"p4.example.com:1666", fingerprint "{fingerprint}") was not '
            f'verified and might not be safe. This certificate needs to be '
            f'verified before the repository can be accessed.'
        )

        with self.assertRaisesMessage(UnverifiedCertificateError,
                                      expected_msg):
            with client.run_worker():
                raise P4Exception(err_msg)

    def test_run_worker_with_unverified_cert_new(self) -> None:
        """Testing PerforceTool.run_worker with new unverified certificate"""
        self.repository.path = 'p4.example.com:1666'

        tool = PerforceTool(self.repository)
        p4 = DummyP4()
        client = tool.client
        client.p4 = p4

        fingerprint = \
            'A0:B1:C2:D3:E4:F5:6A:7B:8C:9D:E0:F1:2A:3B:4C:5D:6E:7F:A1:B2'

        err_msg = (
            f"The authenticity of '1.2.3.4:1666' can't be established,\\n"
            f"this may be your first attempt to connect to this P4PORT.\\n"
            f"The fingerprint for the key sent to your client is\\n"
            f"{fingerprint}\\n"
            f"To allow connection use the 'p4 trust' command.\\n"
        )

        expected_msg = (
            f'The SSL certificate for this repository (hostname '
            f'"p4.example.com:1666", fingerprint "{fingerprint}") was not '
            f'verified and might not be safe. This certificate needs to be '
            f'verified before the repository can be accessed.'
        )

        with self.assertRaisesMessage(UnverifiedCertificateError,
                                      expected_msg):
            with client.run_worker():
                raise P4Exception(err_msg)

    def test_run_worker_with_unverified_cert_changed_error(self) -> None:
        """Testing PerforceTool.run_worker with unverified certificate and
        cert changed error
        """
        self.repository.path = 'p4.example.com:1666'

        tool = PerforceTool(self.repository)
        p4 = DummyP4()
        client = tool.client
        client.p4 = p4

        fingerprint = \
            'A0:B1:C2:D3:E4:F5:6A:7B:8C:9D:E0:F1:2A:3B:4C:5D:6E:7F:A1:B2'

        err_msg = (
            f"******* WARNING P4PORT IDENTIFICATION HAS CHANGED! *******\\n"
            f"It is possible that someone is intercepting your connection\\n"
            f"to the Perforce P4PORT '1.2.3.4:1666'\\n"
            f"If this is not a scheduled key change, then you should "
            f"contact\\n"
            f"your Perforce administrator.\\n"
            f"The fingerprint for the mismatched key sent to your client is\\n"
            f"{fingerprint}\n"
            f"To allow connection use the 'p4 trust' command.\n"
        )

        expected_msg = (
            f'The SSL certificate for this repository (hostname '
            f'"p4.example.com:1666", fingerprint "{fingerprint}") was not '
            f'verified and might not be safe. This certificate needs to be '
            f'verified before the repository can be accessed.'
        )

        with self.assertRaisesMessage(UnverifiedCertificateError,
                                      expected_msg):
            with client.run_worker():
                raise P4Exception(err_msg)

    @unittest.skipIf(not has_p4d,
                     'The p4d command line tool is not installed')
    def test_changeset(self) -> None:
        """Testing PerforceTool.get_changeset"""
        desc = self.tool.get_changeset(4)

        assert desc is not None

        self.assertEqual(desc.changenum, 4)
        self.assertEqual(desc.files, ['//depot/model.py', '//depot/readme'])
        self.assertEqual(desc.summary, 'Make some changes.')

    @unittest.skipIf(not has_p4d,
                     'The p4d command line tool is not installed')
    def test_encoding(self) -> None:
        """Testing PerforceTool.get_changeset with a specified encoding"""
        repo = self.create_repository(
            path='localhost:61666',
            username='guest',
            tool_name='Perforce',
            encoding='utf8')
        tool = repo.get_scmtool()

        try:
            tool.get_changeset('4')

            self.fail('Expected an error about unicode-enabled servers.')
        except SCMError as e:
            # Our local p4d doesn't have unicode enabled. Getting this
            # error means we at least passed the charset through correctly
            # to the p4 client.
            self.assertTrue('clients require a unicode enabled server' in
                            str(e))

    @unittest.skipIf(not has_p4d,
                     'The p4d command line tool is not installed')
    def test_changeset_authentication_error(self) -> None:
        """Testing PerforceTool.get_changeset with an authentication error"""
        repo = self.create_repository(
            path='localhost:61666',
            tool_name='Perforce',
            username='samwise',
            password='bogus',
            encoding='none')
        tool = repo.get_scmtool()

        self.assertRaises(AuthenticationError,
                          lambda: tool.get_changeset('4'))

    @unittest.skipIf(not has_p4d,
                     'The p4d command line tool is not installed')
    def test_changeset_bad_p4port(self) -> None:
        """Testing PerforceTool.get_changeset with a bad P4PORT"""
        repo = self.create_repository(
            name='localhost:1',
            path='localhost:1',
            tool_name='Perforce')

        tool = repo.get_scmtool()
        self.assertRaises(RepositoryNotFoundError,
                          lambda: tool.get_changeset('1'))

    @unittest.skipIf(not has_p4d,
                     'The p4d command line tool is not installed')
    def test_get_file(self) -> None:
        """Testing PerforceTool.get_file"""
        tool = self.tool

        content = tool.get_file('//depot/foo', PRE_CREATION)
        self.assertIsInstance(content, bytes)
        self.assertEqual(content, b'')

        content = tool.get_file('//depot/model.py', '4')
        self.assertIsInstance(content, bytes)
        self.assertEqual(md5(content).hexdigest(),
                         'd41d8cd98f00b204e9800998ecf8427e')

    @unittest.skipIf(not has_p4d,
                     'The p4d command line tool is not installed')
    def test_file_exists(self) -> None:
        """Testing PerforceTool.file_exists"""
        self.assertTrue(self.tool.file_exists(
            '//depot/model.py', '2'))

        self.assertFalse(self.tool.file_exists(
            '//depot/xxx-non-existent', '1'))

    def test_file_exists_with_pre_creation(self) -> None:
        """Testing PerforceTool.file_exists"""
        self.assertFalse(self.tool.file_exists('//depot/xxx-new-file',
                                               PRE_CREATION))

    @unittest.skipIf(not has_p4d,
                     'The p4d command line tool is not installed')
    def test_custom_host(self) -> None:
        """Testing Perforce client initialization with a custom P4HOST"""
        repo = self.create_repository(
            path='localhost:61666',
            username='guest',
            tool_name='Perforce',
            encoding='utf8')
        repo.extra_data['p4_host'] = 'my-custom-host'

        tool = repo.get_scmtool()
        assert isinstance(tool, PerforceTool)

        with tool.client.connect():
            self.assertEqual(tool.client.p4.host, 'my-custom-host')

    @unittest.skipIf(not has_p4d,
                     'The p4d command line tool is not installed')
    def test_ticket_login(self) -> None:
        """Testing Perforce with ticket-based logins"""
        repo = self.create_repository(
            path='localhost:61666',
            tool_name='Perforce',
            username='samwise',
            password='bogus')
        repo.extra_data = {
            'use_ticket_auth': True,
        }

        tool = repo.get_scmtool()
        assert isinstance(tool, PerforceTool)

        client = tool.client
        self.assertTrue(client.use_ticket_auth)

        self.spy_on(client.get_ticket_status, call_fake=lambda *args: {
            'user': 'samwise',
            'expiration_secs': 100000,
        })

        self.spy_on(client.login, call_original=False)

        self.assertFalse(os.path.exists(os.path.join(
            settings.SITE_DATA_DIR, 'p4', 'p4tickets')))

        with client.connect():
            self.assertSpyNotCalled(client.login)
            self.assertEqual(client.p4.ticket_file,
                             os.path.join(settings.SITE_DATA_DIR, 'p4',
                                          'p4tickets'))

    @unittest.skipIf(not has_p4d,
                     'The p4d command line tool is not installed')
    def test_ticket_login_with_expiring_ticket(self) -> None:
        """Testing Perforce with ticket-based logins with ticket close to
        expiring
        """
        repo = self.create_repository(
            path='localhost:61666',
            tool_name='Perforce',
            username='samwise',
            password='bogus')
        repo.extra_data = {
            'use_ticket_auth': True,
        }

        tool = repo.get_scmtool()
        assert isinstance(tool, PerforceTool)

        client = tool.client
        self.assertTrue(client.use_ticket_auth)

        self.spy_on(client.get_ticket_status, call_fake=lambda *args: {
            'user': 'samwise',
            'expiration_secs': 99,
        })

        self.spy_on(client.login, call_original=False)

        with client.connect():
            self.assertIsNotNone(client.p4.ticket_file)
            self.assertSpyCalled(client.login)
            self.assertEqual(client.p4.ticket_file,
                             os.path.join(settings.SITE_DATA_DIR, 'p4',
                                          'p4tickets'))

    @unittest.skipIf(not has_p4d,
                     'The p4d command line tool is not installed')
    def test_ticket_login_with_no_valid_ticket(self) -> None:
        """Testing Perforce with ticket-based logins without a valid ticket
        """
        repo = self.create_repository(
            path='localhost:61666',
            tool_name='Perforce',
            username='samwise',
            password='bogus')
        repo.extra_data = {
            'use_ticket_auth': True,
        }

        tool = repo.get_scmtool()
        assert isinstance(tool, PerforceTool)

        client = tool.client
        self.assertTrue(client.use_ticket_auth)

        self.spy_on(client.get_ticket_status, call_fake=lambda *args: None)
        self.spy_on(client.login, call_original=False)

        with client.connect():
            self.assertSpyCalled(client.login)
            self.assertEqual(client.p4.ticket_file,
                             os.path.join(settings.SITE_DATA_DIR, 'p4',
                                          'p4tickets'))

    @unittest.skipIf(not has_p4d,
                     'The p4d command line tool is not installed')
    def test_ticket_login_with_different_user(self) -> None:
        """Testing Perforce with ticket-based logins with ticket for a
        different user
        """
        repo = self.create_repository(
            path='localhost:61666',
            tool_name='Perforce',
            username='samwise',
            password='bogus')
        repo.extra_data = {
            'use_ticket_auth': True,
        }

        tool = repo.get_scmtool()
        assert isinstance(tool, PerforceTool)

        client = tool.client
        self.assertTrue(client.use_ticket_auth)

        self.spy_on(client.get_ticket_status, call_fake=lambda *args: {
            'user': 'other-user',
            'expiration_secs': 100000,
        })

        self.spy_on(client.login, call_original=False)

        with client.connect():
            self.assertSpyCalled(client.login)
            self.assertEqual(client.p4.ticket_file,
                             os.path.join(settings.SITE_DATA_DIR, 'p4',
                                          'p4tickets'))

    @unittest.skipIf(not has_p4d,
                     'The p4d command line tool is not installed')
    @add_fixtures(['test_site', 'test_users'])
    def test_ticket_login_with_local_site(self) -> None:
        """Testing Perforce with ticket-based logins with Local Sites"""
        repo = self.create_repository(
            path='localhost:61666',
            tool_name='Perforce',
            username='samwise',
            password='bogus',
            local_site=LocalSite.objects.get(name='local-site-1'))
        repo.extra_data = {
            'use_ticket_auth': True,
        }

        tool = repo.get_scmtool()
        assert isinstance(tool, PerforceTool)

        client = tool.client
        self.assertTrue(client.use_ticket_auth)

        self.spy_on(client.get_ticket_status, call_fake=lambda *args: {
            'user': 'samwise',
            'expiration_secs': 100000,
        })

        self.spy_on(client.login, call_original=False)

        with client.connect():
            self.assertSpyNotCalled(client.login)
            self.assertEqual(client.p4.ticket_file,
                             os.path.join(settings.SITE_DATA_DIR, 'p4',
                                          'local-site-1', 'p4tickets'))

    def test_empty_diff(self) -> None:
        """Testing Perforce empty diff parsing"""
        diff = b'==== //depot/foo/proj/README#2 ==M== /src/proj/README ====\n'

        parsed_files = self.tool.get_parser(diff).parse()
        self.assertEqual(len(parsed_files), 1)

        self.assert_parsed_diff_file(
            parsed_files[0],
            orig_filename=b'//depot/foo/proj/README',
            orig_file_details=b'//depot/foo/proj/README#2',
            modified_filename=b'/src/proj/README',
            modified_file_details=b'',
            data=diff)

    def test_binary_diff(self) -> None:
        """Testing Perforce binary diff parsing"""
        diff = (
            b'==== //depot/foo/proj/test.png#1 ==A== /src/proj/test.png '
            b'====\nBinary files /tmp/foo and /src/proj/test.png differ\n'
        )

        parsed_files = self.tool.get_parser(diff).parse()
        self.assertEqual(len(parsed_files), 1)

        self.assert_parsed_diff_file(
            parsed_files[0],
            orig_filename=b'//depot/foo/proj/test.png',
            orig_file_details=b'//depot/foo/proj/test.png#1',
            modified_filename=b'/src/proj/test.png',
            modified_file_details=b'',
            binary=True,
            data=diff)

    def test_deleted_diff(self) -> None:
        """Testing Perforce deleted diff parsing"""
        diff = (
            b'==== //depot/foo/proj/test.png#1 ==D== /src/proj/test.png '
            b'====\n'
        )

        parsed_files = self.tool.get_parser(diff).parse()
        self.assertEqual(len(parsed_files), 1)

        self.assert_parsed_diff_file(
            parsed_files[0],
            orig_filename=b'//depot/foo/proj/test.png',
            orig_file_details=b'//depot/foo/proj/test.png#1',
            modified_filename=b'/src/proj/test.png',
            modified_file_details=b'',
            deleted=True,
            data=diff)

    def test_moved_file_diff(self) -> None:
        """Testing Perforce moved file diff parsing"""
        diff = (
            b'Moved from: //depot/foo/proj/test.txt\n'
            b'Moved to: //depot/foo/proj/test2.txt\n'
            b'--- //depot/foo/proj/test.txt  //depot/foo/proj/test.txt#2\n'
            b'+++ //depot/foo/proj/test2.txt  01-02-03 04:05:06\n'
            b'@@ -1 +1,2 @@\n'
            b'-test content\n'
            b'+updated test content\n'
            b'+added info\n'
        )

        parsed_files = self.tool.get_parser(diff).parse()
        self.assertEqual(len(parsed_files), 1)

        self.assert_parsed_diff_file(
            parsed_files[0],
            orig_filename=b'//depot/foo/proj/test.txt',
            orig_file_details=b'//depot/foo/proj/test.txt#2',
            modified_filename=b'//depot/foo/proj/test2.txt',
            modified_file_details=b'01-02-03 04:05:06',
            moved=True,
            insert_count=2,
            delete_count=1,
            data=diff)

    def test_moved_file_diff_no_changes(self) -> None:
        """Testing Perforce moved file diff parsing without changes"""
        diff = (
            b'==== //depot/foo/proj/test.png#5 ==MV== '
            b'//depot/foo/proj/test2.png ====\n'
        )

        parsed_files = self.tool.get_parser(diff).parse()
        self.assertEqual(len(parsed_files), 1)

        self.assert_parsed_diff_file(
            parsed_files[0],
            orig_filename=b'//depot/foo/proj/test.png',
            orig_file_details=b'//depot/foo/proj/test.png#5',
            modified_filename=b'//depot/foo/proj/test2.png',
            modified_file_details=b'',
            moved=True,
            data=diff)

    def test_empty_and_normal_diffs(self) -> None:
        """Testing Perforce empty and normal diff parsing"""
        diff1_text = (
            b'==== //depot/foo/proj/test.png#1 ==A== '
            b'/src/proj/test.png ====\n'
        )
        diff2_text = (
            b'--- test.c  //depot/foo/proj/test.c#2\n'
            b'+++ test.c  01-02-03 04:05:06\n'
            b'@@ -1 +1,2 @@\n'
            b'-test content\n'
            b'+updated test content\n'
            b'+added info\n'
        )
        diff = diff1_text + diff2_text

        parsed_files = self.tool.get_parser(diff).parse()
        self.assertEqual(len(parsed_files), 2)

        self.assert_parsed_diff_file(
            parsed_files[0],
            orig_filename=b'//depot/foo/proj/test.png',
            orig_file_details=b'//depot/foo/proj/test.png#1',
            modified_filename=b'/src/proj/test.png',
            modified_file_details=b'',
            data=diff1_text)

        self.assert_parsed_diff_file(
            parsed_files[1],
            orig_filename=b'test.c',
            orig_file_details=b'//depot/foo/proj/test.c#2',
            modified_filename=b'test.c',
            modified_file_details=b'01-02-03 04:05:06',
            insert_count=2,
            delete_count=1,
            data=diff2_text)

    def test_diff_file_normalization(self) -> None:
        """Testing perforce diff filename normalization"""
        parser = self.tool.get_parser(b'')
        self.assertEqual(parser.normalize_diff_filename('//depot/test'),
                         '//depot/test')

    def test_unicode_diff(self) -> None:
        """Testing Perforce diff parsing with unicode characters"""
        diff = (
            '--- tést.c  //depot/foo/proj/tést.c#2\n'
            '+++ tést.c  01-02-03 04:05:06\n'
            '@@ -1 +1,2 @@\n'
            '-tést content\n'
            '+updated test content\n'
            '+added info\n'
        ).encode('utf-8')

        parsed_files = self.tool.get_parser(diff).parse()
        self.assertEqual(len(parsed_files), 1)

        self.assert_parsed_diff_file(
            parsed_files[0],
            orig_filename='tést.c'.encode('utf-8'),
            orig_file_details='//depot/foo/proj/tést.c#2'.encode('utf-8'),
            modified_filename='tést.c'.encode('utf-8'),
            modified_file_details=b'01-02-03 04:05:06',
            insert_count=2,
            delete_count=1,
            data=diff)


class PerforceStunnelTests(BasePerforceTestCase):
    """Unit tests for Perforce running through stunnel.

    Out of the box, Perforce doesn't support any kind of encryption on its
    connections. The recommended setup in this case is to run an stunnel server
    on the perforce server which bounces SSL connections to the normal p4 port.
    One can then start an stunnel on their client machine and connect via a
    localhost: P4PORT.

    For these tests, we set up an stunnel server which will accept secure
    connections and proxy (insecurely) to the local perforce server. We can
    then tell the Perforce SCMTool to connect securely to stunnel.
    """

    fixtures = ['test_scmtools']

    def setUp(self) -> None:
        """Set up the test case."""
        super().setUp()

        if not is_exe_in_path('stunnel'):
            raise unittest.SkipTest('stunnel is not installed')

        cert = os.path.join(os.path.dirname(__file__),
                            '..', 'testdata', 'stunnel.pem')
        self.proxy = STunnelProxy('localhost:61666')
        self.proxy.start_server(cert)

        # Find an available port to listen on
        path = f'stunnel:localhost:{self.proxy.port}'

        self.repository = self.create_repository(
            name='localhost - secure',
            path=path,
            username='guest',
            encoding='none',
            tool_name='Perforce')

        self.tool = self.repository.get_scmtool()
        assert isinstance(self.tool, PerforceTool)

        self.tool.use_stunnel = True

    def tearDown(self) -> None:
        """Tear down the test case."""
        super().tearDown()

        self.proxy.shutdown()

    @unittest.skipIf(not has_p4d,
                     'The p4d command line tool is not installed')
    def test_changeset(self) -> None:
        """Testing PerforceTool.get_changeset with stunnel"""
        desc = self.tool.get_changeset('4')

        self.assertEqual(desc.changenum, 4)
        self.assertEqual(desc.files, ['//depot/model.py', '//depot/readme'])
        self.assertEqual(desc.summary, 'Make some changes.')

    @unittest.skipIf(not has_p4d,
                     'The p4d command line tool is not installed')
    def test_get_file(self) -> None:
        """Testing PerforceTool.get_file with stunnel"""
        file = self.tool.get_file('//depot/foo', PRE_CREATION)

        self.assertIsInstance(file, bytes)
        self.assertEqual(file, b'')

        file = self.tool.get_file('//depot/model.py', '4')

        self.assertEqual(md5(file).hexdigest(),
                         'd41d8cd98f00b204e9800998ecf8427e')


class PerforceAuthFormTests(TestCase):
    """Unit tests for PerforceTool's authentication form."""

    def test_fields(self) -> None:
        """Testing PerforceTool authentication form fields"""
        form = PerforceTool.create_auth_form()

        self.assertEqual(list(form.fields), ['username', 'password'])
        self.assertEqual(form['username'].help_text, '')
        self.assertEqual(form['username'].label, 'Username')
        self.assertEqual(form['password'].help_text, '')
        self.assertEqual(form['password'].label, 'Password')

    @add_fixtures(['test_scmtools'])
    def test_load(self) -> None:
        """Tetting PerforceTool authentication form load"""
        repository = self.create_repository(
            tool_name='Perforce',
            username='test-user',
            password='test-pass')

        form = PerforceTool.create_auth_form(repository=repository)
        form.load()

        self.assertEqual(form['username'].value(), 'test-user')
        self.assertEqual(form['password'].value(), 'test-pass')

    @add_fixtures(['test_scmtools'])
    def test_save(self) -> None:
        """Tetting PerforceTool authentication form save"""
        repository = self.create_repository(tool_name='Perforce')

        form = PerforceTool.create_auth_form(
            repository=repository,
            data={
                'username': 'test-user',
                'password': 'test-pass',
            })
        self.assertTrue(form.is_valid())
        form.save()

        self.assertEqual(repository.username, 'test-user')
        self.assertEqual(repository.password, 'test-pass')


class PerforceRepositoryFormTests(TestCase):
    """Unit tests for PerforceTool's repository form."""

    def test_fields(self) -> None:
        """Testing PerforceTool repository form fields"""
        form = PerforceTool.create_repository_form()

        self.assertEqual(list(form.fields),
                         ['path', 'mirror_path', 'use_ticket_auth'])
        self.assertEqual(form['path'].help_text,
                         'The Perforce port identifier (P4PORT) for the '
                         'repository. If your server is set up to use SSL '
                         '(2012.1+), prefix the port with "ssl:". If your '
                         'server connection is secured with stunnel (2011.x '
                         'or older), prefix the port with "stunnel:".')
        self.assertEqual(form['path'].label, 'Path')
        self.assertEqual(form['mirror_path'].help_text,
                         'If provided, this path will be used instead for '
                         'all communication with Perforce.')
        self.assertEqual(form['mirror_path'].label, 'Mirror Path')
        self.assertEqual(form['use_ticket_auth'].help_text, '')
        self.assertEqual(form['use_ticket_auth'].label,
                         'Use ticket-based authentication')

    @add_fixtures(['test_scmtools'])
    def test_load(self) -> None:
        """Tetting PerforceTool repository form load"""
        repository = self.create_repository(
            tool_name='Perforce',
            path='example.com:123/cvsroot/test',
            mirror_path=':pserver:example.com:/cvsroot/test',
            extra_data={
                'use_ticket_auth': True,
            })

        form = PerforceTool.create_repository_form(repository=repository)
        form.load()

        self.assertEqual(form['path'].value(), 'example.com:123/cvsroot/test')
        self.assertEqual(form['mirror_path'].value(),
                         ':pserver:example.com:/cvsroot/test')
        self.assertTrue(form['use_ticket_auth'].value())

    @add_fixtures(['test_scmtools'])
    def test_save(self) -> None:
        """Tetting PerforceTool repository form save"""
        repository = self.create_repository(tool_name='Perforce')
        self.assertIsNone(repository.extra_data.get('use_ticket_auth'))

        form = PerforceTool.create_repository_form(
            repository=repository,
            data={
                'path': 'ssl:perforce.example.com:1666',
                'mirror_path': 'mirror.example.com:1666',
                'use_ticket_auth': True,
            })
        self.assertTrue(form.is_valid())
        form.save()

        self.assertEqual(repository.path, 'ssl:perforce.example.com:1666')
        self.assertEqual(repository.mirror_path, 'mirror.example.com:1666')
        self.assertTrue(repository.extra_data.get('use_ticket_auth'))
