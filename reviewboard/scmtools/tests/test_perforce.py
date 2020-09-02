# coding=utf-8
from __future__ import unicode_literals

import os
import shutil
from hashlib import md5

try:
    import P4
except ImportError:
    P4 = None

import nose
from django.conf import settings
from django.utils import six
from django.utils.six.moves import zip_longest
from djblets.testing.decorators import add_fixtures
from djblets.util.filesystem import is_exe_in_path
from kgb import SpyAgency
from P4 import P4Exception

from reviewboard.scmtools.core import PRE_CREATION
from reviewboard.scmtools.errors import (AuthenticationError,
                                         RepositoryNotFoundError,
                                         SCMError,
                                         UnverifiedCertificateError)
from reviewboard.scmtools.models import Repository, Tool
from reviewboard.scmtools.perforce import PerforceTool, STunnelProxy
from reviewboard.scmtools.tests.testcases import SCMTestCase
from reviewboard.site.models import LocalSite
from reviewboard.testing import online_only
from reviewboard.testing.testcase import TestCase


if P4 is not None:
    class DummyP4(P4.P4):
        """A dummy wrapper around P4 that does not connect.

        This is used for certain tests that need to simulate connecting without
        actually talking to a server.
        """

        def connect(self):
            return self
else:
    DummyP4 = None


class BasePerforceTestCase(SpyAgency, SCMTestCase):
    """Base class for all Perforce tests.

    This will ensure that the test suite has proper Perforce support before
    it runs.
    """

    def setUp(self):
        super(BasePerforceTestCase, self).setUp()

        if P4 is None:
            raise nose.SkipTest('The p4python module is not installed')

        if not is_exe_in_path('p4'):
            raise nose.SkipTest('The p4 command line tool is not installed')


class PerforceTests(BasePerforceTestCase):
    """Unit tests for Perforce.

    This uses the open server at public.perforce.com to test various
    pieces. Because we have no control over things like pending
    changesets, not everything can be tested.
    """

    fixtures = ['test_scmtools']

    def setUp(self):
        super(PerforceTests, self).setUp()

        self.repository = Repository(name='Perforce.com',
                                     path='public.perforce.com:1666',
                                     username='guest',
                                     encoding='none',
                                     tool=Tool.objects.get(name='Perforce'))
        self.tool = self.repository.get_scmtool()

    def tearDown(self):
        super(PerforceTests, self).tearDown()

        shutil.rmtree(os.path.join(settings.SITE_DATA_DIR, 'p4'),
                      ignore_errors=True)

    def test_init_with_p4_client(self):
        """Testing PerforceTool.__init__ with p4_client"""
        self.repository.extra_data['p4_client'] = 'test-client'

        tool = PerforceTool(self.repository)
        self.assertIsInstance(tool.client.client_name, six.text_type)
        self.assertEqual(tool.client.client_name, 'test-client')

    def test_init_with_p4_client_none(self):
        """Testing PerforceTool.__init__ with p4_client=None"""
        self.repository.extra_data['p4_client'] = None

        tool = PerforceTool(self.repository)
        self.assertIsNone(tool.client.client_name)

    def test_init_without_p4_client(self):
        """Testing PerforceTool.__init__ without p4_client"""
        self.assertIsNone(self.tool.client.client_name)

    def test_init_with_p4_host(self):
        """Testing PerforceTool.__init__ with p4_host"""
        self.repository.extra_data['p4_host'] = 'test-host'

        tool = PerforceTool(self.repository)
        self.assertIsInstance(tool.client.p4host, six.text_type)
        self.assertEqual(tool.client.p4host, 'test-host')

    def test_init_with_p4_host_none(self):
        """Testing PerforceTool.__init__ with p4_host=None"""
        self.repository.extra_data['p4_host'] = None

        tool = PerforceTool(self.repository)
        self.assertIsNone(tool.client.p4host)

    def test_init_without_p4_host(self):
        """Testing PerforceTool.__init__ without p4_host"""
        self.assertIsNone(self.tool.client.p4host)

    def test_connect_sets_required_client_args(self):
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
            self.assertEqual(p4.port, 'public.perforce.com:1666')

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

    def test_connect_sets_optional_client_args(self):
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

    def test_run_worker_with_unverified_cert(self):
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
            "The authenticity of '1.2.3.4' can't be established,\\n"
            "this may be your first attempt to connect to this P4PORT.\\n"
            "The fingerprint for the key sent to your client is\\n"
            "%s\\n"
            "To allow connection use the 'p4 trust' command.\\n"
            % fingerprint
        )

        expected_msg = (
            'The SSL certificate for this repository (hostname '
            '"p4.example.com:1666", fingerprint "%s") was not verified and '
            'might not be safe. This certificate needs to be verified before '
            'the repository can be accessed.'
            % fingerprint
        )

        with self.assertRaisesMessage(UnverifiedCertificateError,
                                      expected_msg):
            with client.run_worker():
                raise P4Exception(err_msg)

    def test_run_worker_with_unverified_cert_new(self):
        """Testing PerforceTool.run_worker with new unverified certificate"""
        self.repository.path = 'p4.example.com:1666'

        tool = PerforceTool(self.repository)
        p4 = DummyP4()
        client = tool.client
        client.p4 = p4

        fingerprint = \
            'A0:B1:C2:D3:E4:F5:6A:7B:8C:9D:E0:F1:2A:3B:4C:5D:6E:7F:A1:B2'

        err_msg = (
            "The authenticity of '1.2.3.4:1666' can't be established,\\n"
            "this may be your first attempt to connect to this P4PORT.\\n"
            "The fingerprint for the key sent to your client is\\n"
            "%s\\n"
            "To allow connection use the 'p4 trust' command.\\n"
            % fingerprint
        )

        expected_msg = (
            'The SSL certificate for this repository (hostname '
            '"p4.example.com:1666", fingerprint "%s") was not verified and '
            'might not be safe. This certificate needs to be verified before '
            'the repository can be accessed.'
            % fingerprint
        )

        with self.assertRaisesMessage(UnverifiedCertificateError,
                                      expected_msg):
            with client.run_worker():
                raise P4Exception(err_msg)

    def test_run_worker_with_unverified_cert_changed_error(self):
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
            "******* WARNING P4PORT IDENTIFICATION HAS CHANGED! *******\\n"
            "It is possible that someone is intercepting your connection\\n"
            "to the Perforce P4PORT '1.2.3.4:1666'\\n"
            "If this is not a scheduled key change, then you should contact\\n"
            "your Perforce administrator.\\n"
            "The fingerprint for the mismatched key sent to your client is\\n"
            "%s\n"
            "To allow connection use the 'p4 trust' command.\n"
            % fingerprint
        )

        expected_msg = (
            'The SSL certificate for this repository (hostname '
            '"p4.example.com:1666", fingerprint "%s") was not verified and '
            'might not be safe. This certificate needs to be verified before '
            'the repository can be accessed.'
            % fingerprint
        )

        with self.assertRaisesMessage(UnverifiedCertificateError,
                                      expected_msg):
            with client.run_worker():
                raise P4Exception(err_msg)

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
                          username='guest',
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
                          password='bogus',
                          encoding='none')
        tool = repo.get_scmtool()

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
        tool = self.tool

        content = tool.get_file('//depot/foo', PRE_CREATION)
        self.assertIsInstance(content, bytes)
        self.assertEqual(content, b'')

        content = tool.get_file('//public/perforce/api/python/P4Client/p4.py',
                                1)
        self.assertIsInstance(content, bytes)
        self.assertEqual(md5(content).hexdigest(),
                         '227bdd87b052fcad9369e65c7bf23fd0')

    @online_only
    def test_file_exists(self):
        """Testing PerforceTool.file_exists"""
        self.assertTrue(self.tool.file_exists(
            '//public/perforce/api/python/P4Client/p4.py', '1'))

        self.assertFalse(self.tool.file_exists(
            '//public/perforce/xxx-non-existent', '1'))

    @online_only
    def test_file_exists_with_pre_creation(self):
        """Testing PerforceTool.file_exists"""
        self.assertFalse(self.tool.file_exists('//depot/xxx-new-file',
                                               PRE_CREATION))

    @online_only
    def test_custom_host(self):
        """Testing Perforce client initialization with a custom P4HOST"""
        repo = Repository(name='Perforce.com',
                          path='public.perforce.com:1666',
                          username='guest',
                          tool=Tool.objects.get(name='Perforce'),
                          encoding='utf8')
        repo.extra_data['p4_host'] = 'my-custom-host'

        tool = repo.get_scmtool()

        with tool.client.connect():
            self.assertEqual(tool.client.p4.host, 'my-custom-host')

    def test_ticket_login(self):
        """Testing Perforce with ticket-based logins"""
        repo = Repository(name='Perforce.com',
                          path='public.perforce.com:1666',
                          tool=Tool.objects.get(name='Perforce'),
                          username='samwise',
                          password='bogus')
        repo.extra_data = {
            'use_ticket_auth': True,
        }

        client = repo.get_scmtool().client
        self.assertTrue(client.use_ticket_auth)

        self.spy_on(client.get_ticket_status, call_fake=lambda *args: {
            'user': 'samwise',
            'expiration_secs': 100000,
        })

        self.spy_on(client.login, call_original=False)

        self.assertFalse(os.path.exists(os.path.join(
            settings.SITE_DATA_DIR, 'p4', 'p4tickets')))

        with client.connect():
            self.assertFalse(client.login.called)
            self.assertEqual(client.p4.ticket_file,
                             os.path.join(settings.SITE_DATA_DIR, 'p4',
                                          'p4tickets'))

    def test_ticket_login_with_expiring_ticket(self):
        """Testing Perforce with ticket-based logins with ticket close to
        expiring
        """
        repo = Repository(name='Perforce.com',
                          path='public.perforce.com:1666',
                          tool=Tool.objects.get(name='Perforce'),
                          username='samwise',
                          password='bogus')
        repo.extra_data = {
            'use_ticket_auth': True,
        }

        client = repo.get_scmtool().client
        self.assertTrue(client.use_ticket_auth)

        self.spy_on(client.get_ticket_status, call_fake=lambda *args: {
            'user': 'samwise',
            'expiration_secs': 99,
        })

        self.spy_on(client.login, call_original=False)

        with client.connect():
            self.assertIsNotNone(client.p4.ticket_file)
            self.assertTrue(client.login.called)
            self.assertEqual(client.p4.ticket_file,
                             os.path.join(settings.SITE_DATA_DIR, 'p4',
                                          'p4tickets'))

    def test_ticket_login_with_no_valid_ticket(self):
        """Testing Perforce with ticket-based logins without a valid ticket
        """
        repo = Repository(name='Perforce.com',
                          path='public.perforce.com:1666',
                          tool=Tool.objects.get(name='Perforce'),
                          username='samwise',
                          password='bogus')
        repo.extra_data = {
            'use_ticket_auth': True,
        }

        client = repo.get_scmtool().client
        self.assertTrue(client.use_ticket_auth)

        self.spy_on(client.get_ticket_status, call_fake=lambda *args: None)
        self.spy_on(client.login, call_original=False)

        with client.connect():
            self.assertTrue(client.login.called)
            self.assertEqual(client.p4.ticket_file,
                             os.path.join(settings.SITE_DATA_DIR, 'p4',
                                          'p4tickets'))

    def test_ticket_login_with_different_user(self):
        """Testing Perforce with ticket-based logins with ticket for a
        different user
        """
        repo = Repository(name='Perforce.com',
                          path='public.perforce.com:1666',
                          tool=Tool.objects.get(name='Perforce'),
                          username='samwise',
                          password='bogus')
        repo.extra_data = {
            'use_ticket_auth': True,
        }

        client = repo.get_scmtool().client
        self.assertTrue(client.use_ticket_auth)

        self.spy_on(client.get_ticket_status, call_fake=lambda *args: {
            'user': 'other-user',
            'expiration_secs': 100000,
        })

        self.spy_on(client.login, call_original=False)

        with client.connect():
            self.assertTrue(client.login.called)
            self.assertEqual(client.p4.ticket_file,
                             os.path.join(settings.SITE_DATA_DIR, 'p4',
                                          'p4tickets'))

    @add_fixtures(['test_site'])
    def test_ticket_login_with_local_site(self):
        """Testing Perforce with ticket-based logins with Local Sites"""
        repo = Repository(
            name='Perforce.com',
            path='public.perforce.com:1666',
            tool=Tool.objects.get(name='Perforce'),
            username='samwise',
            password='bogus',
            local_site=LocalSite.objects.get(name='local-site-1'))
        repo.extra_data = {
            'use_ticket_auth': True,
        }

        client = repo.get_scmtool().client
        self.assertTrue(client.use_ticket_auth)

        self.spy_on(client.get_ticket_status, call_fake=lambda *args: {
            'user': 'samwise',
            'expiration_secs': 100000,
        })

        self.spy_on(client.login, call_original=False)

        with client.connect():
            self.assertFalse(client.login.called)
            self.assertEqual(client.p4.ticket_file,
                             os.path.join(settings.SITE_DATA_DIR, 'p4',
                                          'local-site-1', 'p4tickets'))

    @online_only
    def test_parse_diff_revision_with_revision_eq_0(self):
        """Testing Perforce.parse_diff_revision with revision == 0"""
        self.assertEqual(
            self.tool.parse_diff_revision(
                filename=b'xxx-foo.py',
                revision=b'//public/perforce/xxx-foo.py#0'),
            (b'//public/perforce/xxx-foo.py', PRE_CREATION))

    @online_only
    def test_parse_diff_revision_with_revision_eq_1_and_existing(self):
        """Testing Perforce.parse_diff_revision with revision == 1 and existing
        file
        """
        self.assertEqual(
            self.tool.parse_diff_revision(
                filename=b'p4.p',
                revision=b'//public/perforce/api/python/P4Client/p4.py#1'),
            (b'//public/perforce/api/python/P4Client/p4.py', b'1'))

    @online_only
    def test_parse_diff_revision_with_revision_eq_1_and_new(self):
        """Testing Perforce.parse_diff_revision with revision == 1 and new file
        """
        self.assertEqual(
            self.tool.parse_diff_revision(
                filename=b'xxx-newfile',
                revision=b'//public/perforce/xxx-newfile#1'),
            (b'//public/perforce/xxx-newfile', PRE_CREATION))

    @online_only
    def test_parse_diff_revision_with_revision_gt_1(self):
        """Testing Perforce.parse_diff_revision with revision > 1"""
        self.assertEqual(
            self.tool.parse_diff_revision(
                filename=b'xxx-foo.py',
                revision=b'//public/perforce/xxx-foo.py#2'),
            (b'//public/perforce/xxx-foo.py', b'2'))

    def test_empty_diff(self):
        """Testing Perforce empty diff parsing"""
        diff = b'==== //depot/foo/proj/README#2 ==M== /src/proj/README ====\n'

        file = self.tool.get_parser(diff).parse()[0]
        self.assertEqual(file.orig_filename, b'//depot/foo/proj/README')
        self.assertEqual(file.orig_file_details, b'//depot/foo/proj/README#2')
        self.assertEqual(file.modified_filename, b'/src/proj/README')
        self.assertEqual(file.modified_file_details, b'')
        self.assertFalse(file.binary)
        self.assertFalse(file.deleted)
        self.assertFalse(file.moved)
        self.assertEqual(file.data, diff)
        self.assertEqual(file.insert_count, 0)
        self.assertEqual(file.delete_count, 0)

    def test_binary_diff(self):
        """Testing Perforce binary diff parsing"""
        diff = (b'==== //depot/foo/proj/test.png#1 ==A== /src/proj/test.png '
                b'====\nBinary files /tmp/foo and /src/proj/test.png differ\n')

        file = self.tool.get_parser(diff).parse()[0]
        self.assertEqual(file.orig_filename, b'//depot/foo/proj/test.png')
        self.assertEqual(file.orig_file_details,
                         b'//depot/foo/proj/test.png#1')
        self.assertEqual(file.modified_filename, b'/src/proj/test.png')
        self.assertEqual(file.modified_file_details, b'')
        self.assertEqual(file.data, diff)
        self.assertTrue(file.binary)
        self.assertFalse(file.deleted)
        self.assertFalse(file.moved)
        self.assertEqual(file.insert_count, 0)
        self.assertEqual(file.delete_count, 0)

    def test_deleted_diff(self):
        """Testing Perforce deleted diff parsing"""
        diff = (b'==== //depot/foo/proj/test.png#1 ==D== /src/proj/test.png '
                b'====\n')

        file = self.tool.get_parser(diff).parse()[0]
        self.assertEqual(file.orig_filename, b'//depot/foo/proj/test.png')
        self.assertEqual(file.orig_file_details,
                         b'//depot/foo/proj/test.png#1')
        self.assertEqual(file.modified_filename, b'/src/proj/test.png')
        self.assertEqual(file.modified_file_details, b'')
        self.assertEqual(file.data, diff)
        self.assertFalse(file.binary)
        self.assertTrue(file.deleted)
        self.assertFalse(file.moved)
        self.assertEqual(file.insert_count, 0)
        self.assertEqual(file.delete_count, 0)

    def test_moved_file_diff(self):
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

        file = self.tool.get_parser(diff).parse()[0]
        self.assertEqual(file.orig_filename, b'//depot/foo/proj/test.txt')
        self.assertEqual(file.orig_file_details,
                         b'//depot/foo/proj/test.txt#2')
        self.assertEqual(file.modified_filename, b'//depot/foo/proj/test2.txt')
        self.assertEqual(file.modified_file_details, b'01-02-03 04:05:06')
        self.assertEqual(file.data, diff)
        self.assertFalse(file.binary)
        self.assertFalse(file.deleted)
        self.assertTrue(file.moved)
        self.assertEqual(file.data, diff)
        self.assertEqual(file.insert_count, 2)
        self.assertEqual(file.delete_count, 1)

    def test_moved_file_diff_no_changes(self):
        """Testing Perforce moved file diff parsing without changes"""
        diff = (b'==== //depot/foo/proj/test.png#5 ==MV== '
                b'//depot/foo/proj/test2.png ====\n')

        file = self.tool.get_parser(diff).parse()[0]
        self.assertEqual(file.orig_filename, b'//depot/foo/proj/test.png')
        self.assertEqual(file.orig_file_details,
                         b'//depot/foo/proj/test.png#5')
        self.assertEqual(file.modified_filename, b'//depot/foo/proj/test2.png')
        self.assertEqual(file.modified_file_details, b'')
        self.assertEqual(file.data, diff)
        self.assertFalse(file.binary)
        self.assertFalse(file.deleted)
        self.assertTrue(file.moved)
        self.assertEqual(file.insert_count, 0)
        self.assertEqual(file.delete_count, 0)

    def test_empty_and_normal_diffs(self):
        """Testing Perforce empty and normal diff parsing"""
        diff1_text = (b'==== //depot/foo/proj/test.png#1 ==A== '
                      b'/src/proj/test.png ====\n')
        diff2_text = (b'--- test.c  //depot/foo/proj/test.c#2\n'
                      b'+++ test.c  01-02-03 04:05:06\n'
                      b'@@ -1 +1,2 @@\n'
                      b'-test content\n'
                      b'+updated test content\n'
                      b'+added info\n')
        diff = diff1_text + diff2_text

        files = self.tool.get_parser(diff).parse()
        self.assertEqual(len(files), 2)
        self.assertEqual(files[0].orig_filename, b'//depot/foo/proj/test.png')
        self.assertEqual(files[0].orig_file_details,
                         b'//depot/foo/proj/test.png#1')
        self.assertEqual(files[0].modified_filename, b'/src/proj/test.png')
        self.assertEqual(files[0].modified_file_details, b'')
        self.assertFalse(files[0].binary)
        self.assertFalse(files[0].deleted)
        self.assertFalse(files[0].moved)
        self.assertEqual(files[0].data, diff1_text)
        self.assertEqual(files[0].insert_count, 0)
        self.assertEqual(files[0].delete_count, 0)

        self.assertEqual(files[1].orig_filename, b'test.c')
        self.assertEqual(files[1].orig_file_details,
                         b'//depot/foo/proj/test.c#2')
        self.assertEqual(files[1].modified_filename, b'test.c')
        self.assertEqual(files[1].modified_file_details, b'01-02-03 04:05:06')
        self.assertFalse(files[1].binary)
        self.assertFalse(files[1].deleted)
        self.assertFalse(files[1].moved)
        self.assertEqual(files[1].data, diff2_text)
        self.assertEqual(files[1].insert_count, 2)
        self.assertEqual(files[1].delete_count, 1)

    def test_diff_file_normalization(self):
        """Testing perforce diff filename normalization"""
        parser = self.tool.get_parser(b'')
        self.assertEqual(parser.normalize_diff_filename('//depot/test'),
                         '//depot/test')

    def test_unicode_diff(self):
        """Testing Perforce diff parsing with unicode characters"""
        diff = ('--- tést.c  //depot/foo/proj/tést.c#2\n'
                '+++ tést.c  01-02-03 04:05:06\n'
                '@@ -1 +1,2 @@\n'
                '-tést content\n'
                '+updated test content\n'
                '+added info\n').encode('utf-8')

        files = self.tool.get_parser(diff).parse()
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0].orig_filename, 'tést.c'.encode('utf-8'))
        self.assertEqual(files[0].orig_file_details,
                         '//depot/foo/proj/tést.c#2'.encode('utf-8'))
        self.assertEqual(files[0].modified_filename, 'tést.c'.encode('utf-8'))
        self.assertEqual(files[0].modified_file_details, b'01-02-03 04:05:06')
        self.assertFalse(files[0].binary)
        self.assertFalse(files[0].deleted)
        self.assertFalse(files[0].moved)
        self.assertEqual(files[0].insert_count, 2)
        self.assertEqual(files[0].delete_count, 1)


class PerforceStunnelTests(BasePerforceTestCase):
    """Unit tests for Perforce running through stunnel.

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
                            '..', 'testdata', 'stunnel.pem')
        self.proxy = STunnelProxy('public.perforce.com:1666')
        self.proxy.start_server(cert)

        # Find an available port to listen on
        path = 'stunnel:localhost:%d' % self.proxy.port

        self.repository = Repository(name='Perforce.com - secure',
                                     path=path,
                                     username='guest',
                                     encoding='none',
                                     tool=Tool.objects.get(name='Perforce'))

        self.tool = self.repository.get_scmtool()
        self.tool.use_stunnel = True

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
        self.assertIsInstance(file, bytes)
        self.assertEqual(file, b'')

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


class PerforceAuthFormTests(TestCase):
    """Unit tests for PerforceTool's authentication form."""

    def test_fields(self):
        """Testing PerforceTool authentication form fields"""
        form = PerforceTool.create_auth_form()

        self.assertEqual(list(form.fields), ['username', 'password'])
        self.assertEqual(form['username'].help_text, '')
        self.assertEqual(form['username'].label, 'Username')
        self.assertEqual(form['password'].help_text, '')
        self.assertEqual(form['password'].label, 'Password')

    @add_fixtures(['test_scmtools'])
    def test_load(self):
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
    def test_save(self):
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

    def test_fields(self):
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
    def test_load(self):
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
    def test_save(self):
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
