"""Unit tests for reviewboard.certs.errors.CertificateVerificationFailureCode.

Version Added:
    8.0
"""

from __future__ import annotations

from reviewboard.certs.errors import CertificateVerificationFailureCode
from reviewboard.certs.tests.testcases import CertificateTestCase


class CertificateVerificationFailureCodeTests(CertificateTestCase):
    """Unit tests for CertificateVerificationFailureCode.

    Version Added:
        8.0
    """

    def test_for_ssl_verify_code(self) -> None:
        """Testing CertificateVerificationError.for_ssl_verify_code"""
        # There's a bit of a tautology here with the test, but we're just
        # making sure there are no surprises in the future if behavior
        # changes.
        checks = [
            (9, CertificateVerificationFailureCode.NOT_YET_VALID),
            (10, CertificateVerificationFailureCode.EXPIRED),
            (18, CertificateVerificationFailureCode.NOT_TRUSTED),
            (19, CertificateVerificationFailureCode.NOT_TRUSTED),
            (20, CertificateVerificationFailureCode.NOT_TRUSTED),
            (21, CertificateVerificationFailureCode.NOT_TRUSTED),
            (27, CertificateVerificationFailureCode.NOT_TRUSTED),
            (62, CertificateVerificationFailureCode.HOSTNAME_MISMATCH),
            (100, CertificateVerificationFailureCode.OTHER),
            (0, CertificateVerificationFailureCode.OTHER),
            (-1, CertificateVerificationFailureCode.OTHER),
            (12345, CertificateVerificationFailureCode.OTHER),
        ]

        for ssl_code, expected_failure_code in checks:
            failure_code = (
                CertificateVerificationFailureCode
                .for_ssl_verify_code(ssl_code)
            )

            self.assertEqual(failure_code,
                             expected_failure_code,
                             f'SSL verification code {ssl_code}')
