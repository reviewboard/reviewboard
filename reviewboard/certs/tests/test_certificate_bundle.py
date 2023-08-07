"""Unit tests for reviewboard.certs.cert.Certificate.

Version Added:
    6.0
"""

from __future__ import annotations

import os
import tempfile

import kgb

from reviewboard.certs.cert import CertDataFormat, CertificateBundle
from reviewboard.certs.errors import (CertificateNotFoundError,
                                      CertificateStorageError,
                                      InvalidCertificateFormatError)
from reviewboard.certs.tests.testcases import (CertificateTestCase,
                                               TEST_CERT_BUNDLE_PEM)


class CertificateBundleTests(kgb.SpyAgency, CertificateTestCase):
    """Unit tests for CertificateBundle.

    Version Added:
        6.0
    """
    def test_init_without_slug(self) -> None:
        """Testing CertificateBundle.__init__ with name not slug"""
        message = (
            'The certificate bundle name "test 123" must be in "slug" '
            'format (using characters "a-z", "0-9", "-").'
        )

        with self.assertRaisesMessage(ValueError, message):
            CertificateBundle(name='test 123',
                              bundle_data=b'...')

    def test_create_from_file(self) -> None:
        """Testing CertificateBundle.create_from_file"""
        fd, path = tempfile.mkstemp()
        os.write(fd, TEST_CERT_BUNDLE_PEM)
        os.close(fd)

        try:
            bundle = CertificateBundle.create_from_file(
                name='my-cert-bundle',
                path=path)
        finally:
            os.unlink(path)

        self.assertEqual(bundle.bundle_data, TEST_CERT_BUNDLE_PEM)
        self.assertEqual(bundle.name, 'my-cert-bundle')
        self.assertEqual(bundle.data_format, CertDataFormat.PEM)

    def test_create_from_file_with_not_found(self) -> None:
        """Testing CertificateBundle.create_from_file with not found"""
        message = 'The SSL/TLS CA bundle was not found.'

        with self.assertRaisesMessage(CertificateNotFoundError, message):
            CertificateBundle.create_from_file(
                name='my-cert-bundle',
                path='/rb-tests-xxx/bad/')

    def test_create_from_file_with_ioerror(self) -> None:
        """Testing CertificateBundle.create_from_file with IOError"""
        self.spy_on(os.path.exists, op=kgb.SpyOpReturn(True))

        message = (
            r'Error loading SSL/TLS CA bundle file\. Administrators can '
            r'find details in the Review Board server logs \(error ID '
            r'[a-z0-9-]+\)\.'
        )

        with self.assertRaisesRegex(CertificateStorageError, message):
            CertificateBundle.create_from_file(
                name='my-cert-bundle',
                path='/rb-tests-xxx/bad/')

    def test_create_from_file_with_invalid(self) -> None:
        """Testing CertificateBundle.create_from_file with invalid format"""
        fd, path = tempfile.mkstemp()
        os.write(fd, b'XXX')
        os.close(fd)

        try:
            with self.assertRaises(InvalidCertificateFormatError):
                CertificateBundle.create_from_file(
                    name='my-cert-bundle',
                    path=path)
        finally:
            os.unlink(path)

    def test_write_bundle_file(self) -> None:
        """Testing CertificateBundle.write_bundle_file"""
        bundle = CertificateBundle(name='my-cert-bundle',
                                   bundle_data=TEST_CERT_BUNDLE_PEM)

        fd, path = tempfile.mkstemp()
        os.close(fd)

        try:
            bundle.write_bundle_file(path)

            with open(path, 'rb') as fp:
                self.assertEqual(fp.read(), TEST_CERT_BUNDLE_PEM)
        finally:
            os.unlink(path)

    def test_write_bundle_file_with_ioerror(self) -> None:
        """Testing CertificateBundle.write_bundle_file with IOError"""
        bundle = CertificateBundle(name='my-cert-bundle',
                                   bundle_data=TEST_CERT_BUNDLE_PEM)

        message = (
            r'Error writing SSL/TLS CA bundle file\. Administrators can '
            r'find details in the Review Board server logs \(error ID '
            r'[a-z0-9-]+\)\.'
        )

        with self.assertRaisesRegex(CertificateStorageError, message):
            bundle.write_bundle_file('/rb-tests-xxx/bad/')
