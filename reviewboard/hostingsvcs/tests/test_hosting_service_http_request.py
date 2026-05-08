"""Unit tests for reviewboard.hostingsvcs.base.http.HostingServiceHTTPRequest.

Version Added:
    8.0
"""

from __future__ import annotations

import logging
import os
import shutil
import ssl
from urllib.request import HTTPSHandler, OpenerDirector

import kgb

from reviewboard.admin.server import get_data_dir
from reviewboard.certs.manager import cert_manager
from reviewboard.certs.tests.testcases import (CaptureSSLContext,
                                               TEST_TRUST_CERT_PEM,
                                               TEST_TRUST_SAN_CERT_PEM)
from reviewboard.hostingsvcs.base.http import HostingServiceHTTPRequest
from reviewboard.hostingsvcs.models import HostingServiceAccount
from reviewboard.testing import TestCase


class _DummyResponse:
    headers = {}

    def getcode(self) -> int:
        return 200

    def geturl(self) -> str:
        return 'https://example.com/'

    def read(self) -> bytes:
        return b''


class BuildSSLContextFromSSLCertTests(kgb.SpyAgency, TestCase):
    """Unit tests for HostingServiceHTTPRequest.

    Version Added:
        8.0
    """

    def setUp(self) -> None:
        """Set up state for the test.

        This will clear out the certs directory before running a test.
        """
        super().setUp()

        shutil.rmtree(os.path.join(get_data_dir(), 'rb-certs'),
                      ignore_errors=True)

    def tearDown(self) -> None:
        """Tear down state for the test.

        This will clear out the certs directory after running a test.
        """
        shutil.rmtree(os.path.join(get_data_dir(), 'rb-certs'),
                      ignore_errors=True)

        super().tearDown()

    def test_open_with_https(self) -> None:
        """Testing HostingServiceHTTPRequest.open with HTTPS"""
        self.spy_on(OpenerDirector.open,
                    owner=OpenerDirector,
                    op=kgb.SpyOpReturn(_DummyResponse()))
        self.spy_on(ssl.create_default_context,
                    op=kgb.SpyOpReturn(CaptureSSLContext()))

        hosting_account = HostingServiceAccount.objects.create(
            service_name='gitlab',
            username='myuser',
            hosting_url='https://example.com',
        )

        http_request = HostingServiceHTTPRequest(
            url='https://example.com',
            hosting_service=hosting_account.service,
        )

        # Trigger the request.
        http_request.open()

        # Make sure hostname checks are enabled.
        handler = http_request._urlopen_handlers[-1]
        assert isinstance(handler, HTTPSHandler)
        self.assertAttrsEqual(
            handler._context,
            {
                'cadatas': [],
                'cafiles': [],
                'capaths': [
                    os.path.join(get_data_dir(), 'rb-certs', 'file',
                                 'cabundles'),
                ],
                'certfiles': [],
                'check_hostname': True,
                'keyfiles': [],
                'passwords': [],
            })

    def test_open_with_legacy_ssl_cert_data(self) -> None:
        """Testing HostingServiceHTTPRequest.open with legacy ssl_cert data"""
        self.spy_on(OpenerDirector.open,
                    owner=OpenerDirector,
                    op=kgb.SpyOpReturn(_DummyResponse()))
        self.spy_on(ssl.create_default_context,
                    op=kgb.SpyOpReturn(CaptureSSLContext()))

        self.assertIsNone(cert_manager.get_certificate(
            hostname='example.com',
            port=443,
        ))

        hosting_account = HostingServiceAccount.objects.create(
            service_name='gitlab',
            username='myuser',
            hosting_url='https://example.com',
            data={
                'ssl_cert': TEST_TRUST_CERT_PEM.decode('utf-8'),
            },
        )

        http_request = HostingServiceHTTPRequest(
            url='https://example.com',
            hosting_service=hosting_account.service,
        )

        # Trigger the ssl_cert migration.
        http_request.open()

        # Make sure hostname checks are enabled.
        handler = http_request._urlopen_handlers[-1]
        assert isinstance(handler, HTTPSHandler)
        self.assertAttrsEqual(
            handler._context,
            {
                'cadatas': [],
                'cafiles': [
                    os.path.join(get_data_dir(), 'rb-certs', 'file',
                                 'certs', 'trust', 'example.com__443.crt'),
                ],
                'capaths': [
                    os.path.join(get_data_dir(), 'rb-certs', 'file',
                                 'cabundles'),
                ],
                'certfiles': [],
                'check_hostname': True,
                'keyfiles': [],
                'passwords': [],
            })

        # Check the legacy data.
        hosting_account.refresh_from_db()
        self.assertNotIn('ssl_cert', hosting_account.data)

        # Check the migrated certificate.
        self.assertAttrsEqual(
            cert_manager.get_certificate(hostname='example.com',
                                         port=443),
            {
                'cert_data': TEST_TRUST_CERT_PEM,
                'hostname': 'example.com',
                'port': 443,
            })

    def test_open_with_legacy_ssl_cert_data_san(self) -> None:
        """Testing HostingServiceHTTPRequest.open with legacy ssl_cert data
        and hostname in SAN
        """
        self.spy_on(OpenerDirector.open,
                    owner=OpenerDirector,
                    op=kgb.SpyOpReturn(_DummyResponse()))
        self.spy_on(ssl.create_default_context,
                    op=kgb.SpyOpReturn(CaptureSSLContext()))

        self.assertIsNone(cert_manager.get_certificate(
            hostname='example.com',
            port=443,
        ))

        hosting_account = HostingServiceAccount.objects.create(
            service_name='gitlab',
            username='myuser',
            hosting_url='https://example.com',
            data={
                'ssl_cert': TEST_TRUST_SAN_CERT_PEM.decode('utf-8'),
            },
        )

        http_request = HostingServiceHTTPRequest(
            url='https://example.com',
            hosting_service=hosting_account.service,
        )

        # Trigger the ssl_cert migration.
        http_request.open()

        # Make sure hostname checks are enabled.
        handler = http_request._urlopen_handlers[-1]
        assert isinstance(handler, HTTPSHandler)
        self.assertAttrsEqual(
            handler._context,
            {
                'cadatas': [],
                'cafiles': [
                    os.path.join(get_data_dir(), 'rb-certs', 'file',
                                 'certs', 'trust', 'example.com__443.crt'),
                ],
                'capaths': [
                    os.path.join(get_data_dir(), 'rb-certs', 'file',
                                 'cabundles'),
                ],
                'certfiles': [],
                'check_hostname': True,
                'keyfiles': [],
                'passwords': [],
            })

        # Check the legacy data.
        hosting_account.refresh_from_db()
        self.assertNotIn('ssl_cert', hosting_account.data)

        # Check the migrated certificate.
        self.assertAttrsEqual(
            cert_manager.get_certificate(hostname='example.com',
                                         port=443),
            {
                'cert_data': TEST_TRUST_SAN_CERT_PEM,
                'hostname': 'example.com',
                'port': 443,
            })

    def test_open_with_legacy_ssl_cert_hostname_mismatch(self) -> None:
        """Testing HostingServiceHTTPRequest.open with legacy ssl_cert data
        and hostname mismatch
        """
        self.spy_on(OpenerDirector.open,
                    owner=OpenerDirector,
                    op=kgb.SpyOpReturn(_DummyResponse()))
        self.spy_on(ssl.create_default_context,
                    op=kgb.SpyOpReturn(CaptureSSLContext()))

        self.assertIsNone(cert_manager.get_certificate(
            hostname='test.example.com',
            port=443,
        ))

        cert_data = TEST_TRUST_CERT_PEM.decode('utf-8')
        hosting_account = HostingServiceAccount.objects.create(
            service_name='gitlab',
            username='myuser',
            hosting_url='https://test.example.com',
            data={
                'ssl_cert': cert_data,
            },
        )

        http_request = HostingServiceHTTPRequest(
            url='https://test.example.com',
            hosting_service=hosting_account.service,
        )

        # Trigger the (failing) ssl_cert migration.
        with self.assertLogs(level=logging.WARNING) as cm:
            http_request.open()

        self.assertEqual(
            cm.output,
            [
                "WARNING:reviewboard.hostingsvcs.base.http:The approved "
                "SSL/TLS certificate stored in hosting service account ID=1 "
                "does not match the hostname 'test.example.com' for the "
                "server. Falling back to a less-secure form of verification. "
                "Please ensure the server has a valid certificate matching "
                "its hostname and then upload a new certificate.",
            ])

        # Make sure hostname checks aren't enabled.
        handler = http_request._urlopen_handlers[-1]
        assert isinstance(handler, HTTPSHandler)
        self.assertAttrsEqual(
            handler._context,
            {
                'cadatas': [cert_data],
                'cafiles': [],
                'capaths': [],
                'certfiles': [],
                'check_hostname': False,
                'keyfiles': [],
                'passwords': [],
            })

        # Check the legacy data is present.
        hosting_account.refresh_from_db()
        self.assertIn('ssl_cert', hosting_account.data)
        self.assertEqual(hosting_account.data['ssl_cert'], cert_data)

        # Check that no certificate was stored.
        self.assertIsNone(cert_manager.get_certificate(
            hostname='test.example.com',
            port=443,
        ))
