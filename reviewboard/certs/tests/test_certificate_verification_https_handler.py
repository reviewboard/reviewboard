"""Unit tests for reviewboard.certs.http.CertificateVerificationHTTPSHandler.

Version Added:
    8.1
"""

from __future__ import annotations

import os
import ssl
from urllib.request import Request

import kgb

from reviewboard.certs.cert import CertPurpose, Certificate, CertificateBundle
from reviewboard.certs.errors import CertificateVerificationError
from reviewboard.certs.http import CertificateVerificationHTTPSHandler
from reviewboard.certs.manager import CertificateManager
from reviewboard.certs.tests.testcases import (CaptureSSLContext,
                                               TEST_CERT_BUNDLE_PEM,
                                               TEST_CLIENT_CERT_PEM,
                                               TEST_CLIENT_KEY_PEM,
                                               TEST_TRUST_CERT_PEM)
from reviewboard.testing.testcase import TestCase


class CertificateVerificationHTTPSHandlerTests(kgb.SpyAgency, TestCase):
    """Unit tests for CertificateVerificationHTTPSHandler.

    Version Added:
        8.1
    """

    def setUp(self) -> None:
        """Set up state for the test."""
        super().setUp()

        self.spy_on(
            Certificate.create_from_server,
            owner=Certificate,
            op=kgb.SpyOpReturn(Certificate(
                hostname='example.com',
                port=443,
                cert_data=TEST_TRUST_CERT_PEM,
            )),
        )

    def test_https_open_with_cert_found(self) -> None:
        """Testing CertificateVerificationHTTPSHandler.https_open
        with certificate found for hostname
        """
        cert_manager = CertificateManager()
        cert_manager.add_ca_bundle(CertificateBundle(
            bundle_data=TEST_CERT_BUNDLE_PEM,
            name='my-certs',
        ))
        cert_manager.add_certificate(self.create_certificate(
            cert_data=TEST_TRUST_CERT_PEM,
        ))
        cert_manager.add_certificate(self.create_certificate(
            purpose=CertPurpose.CLIENT,
            cert_data=TEST_CLIENT_CERT_PEM,
            key_data=TEST_CLIENT_KEY_PEM,
        ))

        storage_backend = cert_manager.storage_backend

        opener = CertificateVerificationHTTPSHandler(
            cert_manager=cert_manager,
            local_site=None,
        )

        self.spy_on(ssl.create_default_context,
                    op=kgb.SpyOpReturn(CaptureSSLContext()))
        self.spy_on(opener.do_open, call_original=False)

        opener.https_open(Request(url='https://example.com'))
        context = opener._context

        assert isinstance(context, CaptureSSLContext)
        self.assertAttrsEqual(
            context,
            {
                'cadatas': [],
                'cafiles': [
                    os.path.join(storage_backend.storage_path, 'certs',
                                 'trust', 'example.com__443.crt'),
                ],
                'capaths': [
                    os.path.join(storage_backend.storage_path, 'cabundles'),
                ],
                'certfiles': [
                    os.path.join(storage_backend.storage_path, 'certs',
                                 'client', 'example.com__443.crt'),
                ],
                'keyfiles': [
                    os.path.join(storage_backend.storage_path, 'certs',
                                 'client', 'example.com__443.key'),
                ],
                'passwords': [
                    None,
                ],
            })

    def test_https_open_with_cert_not_found(self) -> None:
        """Testing CertificateVerificationHTTPSHandler.https_open
        with certificate not found for hostname
        """
        cert_manager = CertificateManager()
        cert_manager.add_ca_bundle(CertificateBundle(
            bundle_data=TEST_CERT_BUNDLE_PEM,
            name='my-certs',
        ))
        cert_manager.add_certificate(self.create_certificate(
            cert_data=TEST_TRUST_CERT_PEM,
        ))
        cert_manager.add_certificate(self.create_certificate(
            purpose=CertPurpose.CLIENT,
            cert_data=TEST_CLIENT_CERT_PEM,
            key_data=TEST_CLIENT_KEY_PEM,
        ))

        storage_backend = cert_manager.storage_backend

        opener = CertificateVerificationHTTPSHandler(
            cert_manager=cert_manager,
            local_site=None,
        )

        self.spy_on(ssl.create_default_context,
                    op=kgb.SpyOpReturn(CaptureSSLContext()))
        self.spy_on(opener.do_open, call_original=False)

        opener.https_open(Request(url='https://other.example.com'))
        context = opener._context

        assert isinstance(context, CaptureSSLContext)
        self.assertAttrsEqual(
            context,
            {
                'cadatas': [],
                'cafiles': [],
                'capaths': [
                    os.path.join(storage_backend.storage_path, 'cabundles'),
                ],
                'certfiles': [],
                'keyfiles': [],
                'passwords': [],
            })

    def test_process_ssl_error_with_not_yet_valid(self) -> None:
        """Testing CertificateVerificationHTTPSHandler._process_ssl_error
        with X509_V_ERR_CERT_NOT_YET_VALID
        """
        self._run_process_cert_verification_error_test(
            verify_code=9,
            verify_code_name='X509_V_ERR_CERT_NOT_YET_VALID',
            expected_message=(
                'The SSL certificate provided by example.com is not yet '
                'valid and cannot be used.'
            ),
        )

    def test_process_ssl_error_with_expired(self) -> None:
        """Testing CertificateVerificationHTTPSHandler._process_ssl_error
        with X509_V_ERR_CERT_HAS_EXPIRED
        """
        self._run_process_cert_verification_error_test(
            verify_code=10,
            verify_code_name='X509_V_ERR_CERT_HAS_EXPIRED',
            expected_message=(
                'The SSL certificate provided by example.com has expired and '
                'can no longer be used.'
            ),
        )

    def test_process_ssl_error_with_depth_zero_self_signed_cert(self) -> None:
        """Testing CertificateVerificationHTTPSHandler._process_ssl_error
        with X509_V_ERR_DEPTH_ZERO_SELF_SIGNED_CERT
        """
        self._run_process_cert_verification_error_test(
            verify_code=18,
            verify_code_name='X509_V_ERR_DEPTH_ZERO_SELF_SIGNED_CERT',
            expected_message=(
                'The SSL certificate provided by example.com has not been '
                'signed by a trusted Certificate Authority and may not be '
                'safe. The certificate needs to be verified in Review Board '
                'before the server can be accessed.'
            ),
        )

    def test_process_ssl_error_with_self_signed_cert_in_chain(self) -> None:
        """Testing CertificateVerificationHTTPSHandler._process_ssl_error
        with X509_V_ERR_SELF_SIGNED_CERT_IN_CHAIN
        """
        self._run_process_cert_verification_error_test(
            verify_code=19,
            verify_code_name='X509_V_ERR_SELF_SIGNED_CERT_IN_CHAIN',
            expected_message=(
                'The SSL certificate provided by example.com has not been '
                'signed by a trusted Certificate Authority and may not be '
                'safe. The certificate needs to be verified in Review Board '
                'before the server can be accessed.'
            ),
        )

    def test_process_ssl_error_with_unable_to_get_issuer_cert_locally(
        self,
    ) -> None:
        """Testing CertificateVerificationHTTPSHandler._process_ssl_error
        with X509_V_ERR_UNABLE_TO_GET_ISSUER_CERT_LOCALLY
        """
        self._run_process_cert_verification_error_test(
            verify_code=20,
            verify_code_name='X509_V_ERR_UNABLE_TO_GET_ISSUER_CERT_LOCALLY',
            expected_message=(
                'The SSL certificate provided by example.com has not been '
                'signed by a trusted Certificate Authority and may not be '
                'safe. The certificate needs to be verified in Review Board '
                'before the server can be accessed.'
            ),
        )

    def test_process_ssl_error_with_unable_to_verify_leaf_signature(
        self,
    ) -> None:
        """Testing CertificateVerificationHTTPSHandler._process_ssl_error
        with X509_V_ERR_UNABLE_TO_VERIFY_LEAF_SIGNATURE
        """
        self._run_process_cert_verification_error_test(
            verify_code=21,
            verify_code_name='X509_V_ERR_UNABLE_TO_VERIFY_LEAF_SIGNATURE',
            expected_message=(
                'The SSL certificate provided by example.com has not been '
                'signed by a trusted Certificate Authority and may not be '
                'safe. The certificate needs to be verified in Review Board '
                'before the server can be accessed.'
            ),
        )

    def test_process_ssl_error_with_cert_untrusted(self) -> None:
        """Testing CertificateVerificationHTTPSHandler._process_ssl_error
        with X509_V_ERR_CERT_UNTRUSTED
        """
        self._run_process_cert_verification_error_test(
            verify_code=27,
            verify_code_name='X509_V_ERR_CERT_UNTRUSTED',
            expected_message=(
                'The SSL certificate provided by example.com has not been '
                'signed by a trusted Certificate Authority and may not be '
                'safe. The certificate needs to be verified in Review Board '
                'before the server can be accessed.'
            ),
        )

    def test_process_ssl_error_with_hostname_mismatch(self) -> None:
        """Testing CertificateVerificationHTTPSHandler._process_ssl_error
        with X509_V_ERR_HOSTNAME_MISMATCH
        """
        self._run_process_cert_verification_error_test(
            verify_code=62,
            verify_code_name='X509_V_ERR_HOSTNAME_MISMATCH',
            expected_message=(
                'The SSL certificate provided by example.com does not '
                'match its hostname and may not be safe.'
            ),
        )

    def test_process_ssl_error_with_other_cert_code(self) -> None:
        """Testing CertificateVerificationHTTPSHandler._process_ssl_error
        with other cert code
        """
        self._run_process_cert_verification_error_test(
            verify_code=1234567,
            verify_code_name='Some Other Bad Thing Happened',
            expected_message=(
                'The SSL certificate provided by example.com could not be '
                'verified and may not be safe. The certificate must be valid '
                'and verified in Review Board before the server can be '
                'accessed.'
            ),
        )

    def test_process_ssl_error_with_sslerror(self) -> None:
        """Testing CertificateVerificationHTTPSHandler._process_ssl_error
        with SSLError
        """
        opener = CertificateVerificationHTTPSHandler(local_site=None)

        error = ssl.SSLError('Bob turned traitor')
        message = (
            'The SSL certificate provided by example.com could not be '
            'verified and may not be safe. The certificate must be valid '
            'and verified in Review Board before the server can be accessed. '
            'Certificate details: hostname="example.com", port=443, '
            'issuer="example.com", fingerprints=SHA1=F2:35:0F:BB:34:40:84:'
            '78:8B:20:1D:40:B1:4A:17:0C:DE:36:2F:D5; SHA256=79:19:70:AE:A6:'
            '1B:EB:BC:35:7C:B8:54:B1:6A:AD:79:FF:F7:28:69:02:5E:C3:6F:B3:C2:'
            'B4:FD:84:66:DF:8F'
        )

        with self.assertRaisesMessage(CertificateVerificationError, message):
            opener._process_ssl_error(error=error,
                                      hostname='example.com',
                                      port=443)

    def _run_process_cert_verification_error_test(
        self,
        *,
        verify_code: int,
        verify_code_name: str,
        expected_message: str,
    ) -> None:
        """Run an SSL cert verification error test.

        Args:
            verify_code (int):
                The SSL verification error code.

            verify_code_name (str):
                The SSL verification error name string.

            expected_message (str):
                The expected SSL error message.
        """
        opener = CertificateVerificationHTTPSHandler(local_site=None)

        error = ssl.SSLCertVerificationError()
        error.verify_code = verify_code
        error.verify_message = verify_code_name

        message = (
            f'{expected_message} '
            f'Certificate details: hostname="example.com", port=443, '
            f'issuer="example.com", fingerprints=SHA1=F2:35:0F:BB:34:40:84:'
            f'78:8B:20:1D:40:B1:4A:17:0C:DE:36:2F:D5; SHA256=79:19:70:AE:A6:'
            f'1B:EB:BC:35:7C:B8:54:B1:6A:AD:79:FF:F7:28:69:02:5E:C3:6F:B3:C2:'
            f'B4:FD:84:66:DF:8F'
        )

        with self.assertRaisesMessage(CertificateVerificationError, message):
            opener._process_ssl_error(error=error,
                                      hostname='example.com',
                                      port=443)
