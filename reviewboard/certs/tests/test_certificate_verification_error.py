"""Unit tests for reviewboard.certs.errors.CertificateVerificationError.

Version Added:
    6.0
"""

from __future__ import annotations

from datetime import datetime

from django.utils import timezone

from reviewboard.certs.cert import Certificate, CertificateFingerprints
from reviewboard.certs.errors import (CertificateVerificationError,
                                      CertificateVerificationFailureCode)
from reviewboard.certs.tests.testcases import (CertificateTestCase,
                                               TEST_SHA1,
                                               TEST_SHA256)


_TEST_CERT = Certificate(
    hostname='example.com',
    port=443,
    subject='Subject',
    issuer='Issuer',
    fingerprints=CertificateFingerprints(sha1=TEST_SHA1,
                                         sha256=TEST_SHA256),
    valid_from=datetime(2023, 7, 14, 7, 50, 30, tzinfo=timezone.utc),
    valid_through=datetime(2024, 7, 13, 7, 50, 30,
                           tzinfo=timezone.utc))

_TEST_CERT_DETAILS = (
    'hostname="example.com", port=443, issuer="Issuer", fingerprints='
    'SHA1=F2:35:0F:BB:34:40:84:78:8B:20:1D:40:B1:4A:17:0C:DE:36:2F:D5; '
    'SHA256=79:19:70:AE:A6:1B:EB:BC:35:7C:B8:54:B1:6A:AD:79:FF:F7:28:'
    '69:02:5E:C3:6F:B3:C2:B4:FD:84:66:DF:8F'
)


class CertificateVerificationErrorTests(CertificateTestCase):
    """Unit tests for CertificateVerificationError.

    Version Added:
        6.0
    """

    def test_init_with_expired(self) -> None:
        """Testing CertificateVerificationError with code=EXPIRED"""
        error = CertificateVerificationError(
            code=CertificateVerificationFailureCode.EXPIRED)

        self.assertEqual(
            str(error),
            'The SSL certificate provided by the server has expired and can '
            'no longer be used.')
        self.assertEqual(error.generic_msg, str(error))
        self.assertIsNone(error.certificate)
        self.assertEqual(error.code,
                         CertificateVerificationFailureCode.EXPIRED)

    def test_init_with_expired_and_cert(self) -> None:
        """Testing CertificateVerificationError with code=EXPIRED and
        certificate
        """
        error = CertificateVerificationError(
            code=CertificateVerificationFailureCode.EXPIRED,
            certificate=_TEST_CERT)

        self.assertEqual(
            str(error),
            f'The SSL certificate provided by example.com has expired and '
            f'can no longer be used. Certificate details: '
            f'{_TEST_CERT_DETAILS}')
        self.assertEqual(
            error.generic_msg,
            'The SSL certificate provided by example.com has expired and '
            'can no longer be used.')
        self.assertEqual(error.certificate, _TEST_CERT)
        self.assertEqual(error.code,
                         CertificateVerificationFailureCode.EXPIRED)

    def test_init_with_not_yet_valid(self) -> None:
        """Testing CertificateVerificationError with code=NOT_YET_VALID"""
        error = CertificateVerificationError(
            code=CertificateVerificationFailureCode.NOT_YET_VALID)

        self.assertEqual(
            str(error),
            'The SSL certificate provided by the server is not yet valid '
            'and cannot be used.')
        self.assertEqual(error.generic_msg, str(error))
        self.assertIsNone(error.certificate)
        self.assertEqual(error.code,
                         CertificateVerificationFailureCode.NOT_YET_VALID)

    def test_init_with_not_yet_valid_and_cert(self) -> None:
        """Testing CertificateVerificationError with code=NOT_YET_VALID and
        certificate
        """
        error = CertificateVerificationError(
            code=CertificateVerificationFailureCode.NOT_YET_VALID,
            certificate=_TEST_CERT)

        self.assertEqual(
            str(error),
            f'The SSL certificate provided by example.com is not yet valid '
            f'and cannot be used. Certificate details: {_TEST_CERT_DETAILS}')
        self.assertEqual(
            error.generic_msg,
            'The SSL certificate provided by example.com is not yet valid '
            'and cannot be used.')
        self.assertEqual(error.certificate, _TEST_CERT)
        self.assertEqual(error.code,
                         CertificateVerificationFailureCode.NOT_YET_VALID)

    def test_init_with_hostname_mismatch(self) -> None:
        """Testing CertificateVerificationError with code=HOSTNAME_MISMATCH"""
        error = CertificateVerificationError(
            code=CertificateVerificationFailureCode.HOSTNAME_MISMATCH)

        self.assertEqual(
            str(error),
            'The SSL certificate provided by the server does not match its '
            'hostname and may not be safe.')
        self.assertEqual(error.generic_msg, str(error))
        self.assertIsNone(error.certificate)
        self.assertEqual(error.code,
                         CertificateVerificationFailureCode.HOSTNAME_MISMATCH)

    def test_init_with_hostname_mismatch_and_cert(self) -> None:
        """Testing CertificateVerificationError with code=HOSTNAME_MISMATCH
        and certificate
        """
        error = CertificateVerificationError(
            code=CertificateVerificationFailureCode.HOSTNAME_MISMATCH,
            certificate=_TEST_CERT)

        self.assertEqual(
            str(error),
            f'The SSL certificate provided by example.com does not match its '
            f'hostname and may not be safe. Certificate details: '
            f'{_TEST_CERT_DETAILS}')
        self.assertEqual(
            error.generic_msg,
            'The SSL certificate provided by example.com does not match its '
            'hostname and may not be safe.')
        self.assertEqual(error.certificate, _TEST_CERT)
        self.assertEqual(error.code,
                         CertificateVerificationFailureCode.HOSTNAME_MISMATCH)

    def test_init_with_not_trusted(self) -> None:
        """Testing CertificateVerificationError with code=NOT_TRUSTED"""
        error = CertificateVerificationError(
            code=CertificateVerificationFailureCode.NOT_TRUSTED)

        self.assertEqual(
            str(error),
            'The SSL certificate provided by the server has not been signed '
            'by a trusted Certificate Authority and may not be safe. The '
            'certificate needs to be verified in Review Board before the '
            'server can be accessed.')
        self.assertEqual(error.generic_msg, str(error))
        self.assertIsNone(error.certificate)
        self.assertEqual(error.code,
                         CertificateVerificationFailureCode.NOT_TRUSTED)

    def test_init_with_not_trusted_and_cert(self) -> None:
        """Testing CertificateVerificationError with code=NOT_TRUSTED and
        certificate
        """
        error = CertificateVerificationError(
            code=CertificateVerificationFailureCode.NOT_TRUSTED,
            certificate=_TEST_CERT)

        self.assertEqual(
            str(error),
            f'The SSL certificate provided by example.com has not been signed '
            f'by a trusted Certificate Authority and may not be safe. The '
            f'certificate needs to be verified in Review Board before the '
            f'server can be accessed. Certificate details: '
            f'{_TEST_CERT_DETAILS}')
        self.assertEqual(
            error.generic_msg,
            'The SSL certificate provided by example.com has not been signed '
            'by a trusted Certificate Authority and may not be safe. The '
            'certificate needs to be verified in Review Board before the '
            'server can be accessed.')
        self.assertEqual(error.certificate, _TEST_CERT)
        self.assertEqual(error.code,
                         CertificateVerificationFailureCode.NOT_TRUSTED)

    def test_init_with_other(self) -> None:
        """Testing CertificateVerificationError with code=OTHER"""
        error = CertificateVerificationError(
            code=CertificateVerificationFailureCode.OTHER)

        self.assertEqual(
            str(error),
            'The SSL certificate provided by the server could not be '
            'verified and may not be safe. The certificate must be valid '
            'and verified in Review Board before the server can be '
            'accessed.')
        self.assertEqual(error.generic_msg, str(error))
        self.assertIsNone(error.certificate)
        self.assertEqual(error.code,
                         CertificateVerificationFailureCode.OTHER)

    def test_init_with_other_and_cert(self) -> None:
        """Testing CertificateVerificationError with code=OTHER and
        certificate
        """
        error = CertificateVerificationError(
            code=CertificateVerificationFailureCode.OTHER,
            certificate=_TEST_CERT)

        self.assertEqual(
            str(error),
            f'The SSL certificate provided by example.com could not be '
            f'verified and may not be safe. The certificate must be valid '
            f'and verified in Review Board before the server can be '
            f'accessed. Certificate details: {_TEST_CERT_DETAILS}')
        self.assertEqual(
            error.generic_msg,
            'The SSL certificate provided by example.com could not be '
            'verified and may not be safe. The certificate must be valid '
            'and verified in Review Board before the server can be '
            'accessed.')
        self.assertEqual(error.certificate, _TEST_CERT)
        self.assertEqual(error.code,
                         CertificateVerificationFailureCode.OTHER)

    def test_init_with_custom_message(self) -> None:
        """Testing CertificateVerificationError with custom message"""
        error = CertificateVerificationError(
            'Something is horribly wrong with the certificate (error '
            '%(code)s)!',
            code=CertificateVerificationFailureCode.NOT_TRUSTED)

        self.assertEqual(
            str(error),
            'Something is horribly wrong with the certificate (error '
            'NOT_TRUSTED)!')
        self.assertEqual(error.generic_msg, str(error))
        self.assertIsNone(error.certificate)
        self.assertEqual(error.code,
                         CertificateVerificationFailureCode.NOT_TRUSTED)

    def test_init_with_custom_message_and_cert(self) -> None:
        """Testing CertificateVerificationError with code=NOT_TRUSTED and
        certificate
        """
        error = CertificateVerificationError(
            'Something is horribly wrong with the %(hostname)s certificate '
            '(error %(code)s)!',
            code=CertificateVerificationFailureCode.NOT_TRUSTED,
            certificate=_TEST_CERT)

        self.assertEqual(
            str(error),
            f'Something is horribly wrong with the example.com certificate '
            f'(error NOT_TRUSTED)! Certificate details: {_TEST_CERT_DETAILS}')
        self.assertEqual(
            error.generic_msg,
            'Something is horribly wrong with the example.com certificate '
            '(error NOT_TRUSTED)!')
        self.assertEqual(error.certificate, _TEST_CERT)
        self.assertEqual(error.code,
                         CertificateVerificationFailureCode.NOT_TRUSTED)
