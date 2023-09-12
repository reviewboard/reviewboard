"""Unit tests for reviewboard.certs.cert.CertificateFingerprints.

Version Added:
    6.0
"""

from __future__ import annotations

from cryptography import x509

from reviewboard.certs.cert import CertificateFingerprints
from reviewboard.certs.tests.testcases import (CertificateTestCase,
                                               TEST_CERT_PEM,
                                               TEST_SHA1,
                                               TEST_SHA1_2,
                                               TEST_SHA256,
                                               TEST_SHA256_2)


class CertificateFingerprintTests(CertificateTestCase):
    """Unit tests for CertificateFingerprints.

    Version Added:
        6.0
    """

    def test_from_json(self) -> None:
        """Testing CertificateFingerprints.from_json"""
        fingerprints = CertificateFingerprints.from_json({
            'sha1': TEST_SHA1,
            'sha256': TEST_SHA256,
        })

        self.assertEqual(fingerprints.sha1, TEST_SHA1)
        self.assertEqual(fingerprints.sha256, TEST_SHA256)

    def test_from_json_with_empty(self) -> None:
        """Testing CertificateFingerprints.from_json with empty data"""
        fingerprints = CertificateFingerprints.from_json({})

        self.assertIsNone(fingerprints.sha1)
        self.assertIsNone(fingerprints.sha256)

    def test_from_json_with_bad_data(self) -> None:
        """Testing CertificateFingerprints.from_json with bad data"""
        fingerprints = CertificateFingerprints.from_json({
            'sha1': 1,
            'sha256': 2,
        })

        self.assertIsNone(fingerprints.sha1)
        self.assertIsNone(fingerprints.sha256)

    def test_from_x509_cert(self) -> None:
        """Testing CertificateFingerprints.from_x509_cert"""
        fingerprints = CertificateFingerprints.from_x509_cert(
            x509.load_pem_x509_certificate(TEST_CERT_PEM))

        self.assertEqual(fingerprints.sha1, TEST_SHA1)
        self.assertEqual(fingerprints.sha256, TEST_SHA256)

    def test_to_json(self) -> None:
        """Testing CertificateFingerprints.to_json"""
        fingerprints = CertificateFingerprints.from_json({
            'sha1': TEST_SHA1,
            'sha256': TEST_SHA256,
        })

        self.assertEqual(fingerprints.to_json(), {
            'sha1': TEST_SHA1,
            'sha256': TEST_SHA256,
        })

    def test_to_json_with_empty(self) -> None:
        """Testing CertificateFingerprints.to_json with empty fingerprints"""
        fingerprints = CertificateFingerprints()

        self.assertEqual(fingerprints.to_json(), {})

    def test_is_empty_with_empty(self) -> None:
        """Testing CertificateFingerprints.is_empty with empty fingerprints"""
        fingerprints = CertificateFingerprints()

        self.assertTrue(fingerprints.is_empty())

    def test_is_empty_with_not_empty(self) -> None:
        """Testing CertificateFingerprints.is_empty with fingerprints"""
        fingerprints = CertificateFingerprints(sha1=TEST_SHA1)
        self.assertFalse(fingerprints.is_empty())

        fingerprints = CertificateFingerprints(sha256=TEST_SHA256)
        self.assertFalse(fingerprints.is_empty())

    def test_matches_with_empty(self) -> None:
        """Testing CertificateFingerprints.matches with empty"""
        fingerprints1 = CertificateFingerprints()
        fingerprints2 = CertificateFingerprints()

        self.assertFalse(fingerprints1.matches(fingerprints2))
        self.assertFalse(fingerprints2.matches(fingerprints1))

    def test_matches_with_sha1_only_match(self) -> None:
        """Testing CertificateFingerprints.matches with SHA1 only and match"""
        fingerprints1 = CertificateFingerprints(sha1=TEST_SHA1)
        fingerprints2 = CertificateFingerprints(sha1=TEST_SHA1)

        self.assertTrue(fingerprints1.matches(fingerprints2))
        self.assertTrue(fingerprints2.matches(fingerprints1))

    def test_matches_with_sha1_only_no_match(self) -> None:
        """Testing CertificateFingerprints.matches with SHA1 only and no match
        """
        fingerprints1 = CertificateFingerprints(sha1=TEST_SHA1)
        fingerprints2 = CertificateFingerprints(sha1=TEST_SHA1_2)

        self.assertFalse(fingerprints1.matches(fingerprints2))
        self.assertFalse(fingerprints2.matches(fingerprints1))

    def test_matches_with_sha256_only_match(self) -> None:
        """Testing CertificateFingerprints.matches with SHA256 only and match
        """
        fingerprints1 = CertificateFingerprints(sha256=TEST_SHA256)
        fingerprints2 = CertificateFingerprints(sha256=TEST_SHA256)

        self.assertTrue(fingerprints1.matches(fingerprints2))
        self.assertTrue(fingerprints2.matches(fingerprints1))

    def test_matches_with_sha256_only_no_match(self) -> None:
        """Testing CertificateFingerprints.matches with SHA256 only and no
        match
        """
        fingerprints1 = CertificateFingerprints(sha256=TEST_SHA256)
        fingerprints2 = CertificateFingerprints(sha256=TEST_SHA256_2)

        self.assertFalse(fingerprints1.matches(fingerprints2))
        self.assertFalse(fingerprints2.matches(fingerprints1))

    def test_matches_with_sha_type_mismatch(self) -> None:
        """Testing CertificateFingerprints.matches with mismatch in available
        fingerprint types
        """
        fingerprints1 = CertificateFingerprints(sha1=TEST_SHA1)
        fingerprints2 = CertificateFingerprints(sha256=TEST_SHA256)

        self.assertFalse(fingerprints1.matches(fingerprints2))
        self.assertFalse(fingerprints2.matches(fingerprints1))

    def test_matches_with_match(self) -> None:
        """Testing CertificateFingerprints.matches with match"""
        fingerprints1 = CertificateFingerprints(sha1=TEST_SHA1,
                                                sha256=TEST_SHA256)
        fingerprints2 = CertificateFingerprints(sha1=TEST_SHA1,
                                                sha256=TEST_SHA256)

        self.assertTrue(fingerprints1.matches(fingerprints2))
        self.assertTrue(fingerprints2.matches(fingerprints1))

    def test_matches_with_no_match(self) -> None:
        """Testing CertificateFingerprints.matches with no match"""
        fingerprints1 = CertificateFingerprints(sha1=TEST_SHA1,
                                                sha256=TEST_SHA256)
        fingerprints2 = CertificateFingerprints(sha1=TEST_SHA1,
                                                sha256=TEST_SHA256_2)

        self.assertFalse(fingerprints1.matches(fingerprints2))
        self.assertFalse(fingerprints2.matches(fingerprints1))

    def test_eq_with_equal(self) -> None:
        """"Testing CertificateFingerprints.__eq__ with objects equal"""
        fingerprints1 = CertificateFingerprints(sha1=TEST_SHA1,
                                                sha256=TEST_SHA256)
        fingerprints2 = CertificateFingerprints(sha1=TEST_SHA1,
                                                sha256=TEST_SHA256)

        self.assertEqual(fingerprints1, fingerprints2)

    def test_eq_with_not_equal(self) -> None:
        """"Testing CertificateFingerprints.__eq__ with objects not equal"""
        fingerprints1 = CertificateFingerprints(sha1=TEST_SHA1,
                                                sha256=TEST_SHA256)
        fingerprints2 = CertificateFingerprints(sha1=TEST_SHA1)

        self.assertNotEqual(fingerprints1, fingerprints2)

    def test_eq_with_wrong_object(self) -> None:
        """"Testing CertificateFingerprints.__eq__ with wrong object type"""
        fingerprints1 = CertificateFingerprints(sha1=TEST_SHA1,
                                                sha256=TEST_SHA256)

        self.assertNotEqual(fingerprints1, 123)
        self.assertNotEqual(fingerprints1, None)
