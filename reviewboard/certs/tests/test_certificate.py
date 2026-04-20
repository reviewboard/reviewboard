"""Unit tests for reviewboard.certs.cert.Certificate.

Version Added:
    6.0
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timedelta, timezone

import kgb
from cryptography.x509.oid import NameOID
from djblets.util.serializers import DjbletsJSONEncoder

from reviewboard.certs.cert import (CertPurpose,
                                    Certificate,
                                    CertificateFingerprints)
from reviewboard.certs.errors import (CertificateNotFoundError,
                                      CertificateStorageError,
                                      InvalidCertificateFormatError)
from reviewboard.certs.tests.testcases import (CertificateTestCase,
                                               TEST_CLIENT_CERT_PEM,
                                               TEST_CLIENT_KEY_PEM,
                                               TEST_SHA1,
                                               TEST_SHA256,
                                               TEST_TRUST_CERT_PEM)
from reviewboard.testing import online_only


class CertificateTests(kgb.SpyAgency, CertificateTestCase):
    """Unit tests for Certificate.

    Version Added:
        6.0
    """

    def test_create_from_files_with_trust(self) -> None:
        """Testing Certificate.create_from_files with purpose=trust"""
        cert_fd, cert_path = tempfile.mkstemp()
        os.write(cert_fd, TEST_TRUST_CERT_PEM)
        os.close(cert_fd)

        try:
            cert = Certificate.create_from_files(
                hostname='example.com',
                port=443,
                cert_path=cert_path)
        finally:
            os.unlink(cert_path)

        self.assertEqual(cert.cert_data, TEST_TRUST_CERT_PEM)
        self.assertIsNone(cert.key_data)

    def test_create_from_files_with_trust_and_key(self) -> None:
        """Testing Certificate.create_from_files with purpose=trust and
        key_path=
        """
        cert_fd, cert_path = tempfile.mkstemp()
        os.write(cert_fd, TEST_TRUST_CERT_PEM)
        os.close(cert_fd)

        key_fd, key_path = tempfile.mkstemp()
        os.write(key_fd, TEST_CLIENT_KEY_PEM)
        os.close(key_fd)

        message = (
            'key_path cannot be provided when passing '
            'purpose=CertPurpose.TRUST.'
        )

        try:
            with self.assertRaisesMessage(ValueError, message):
                Certificate.create_from_files(
                    hostname='example.com',
                    port=443,
                    purpose=CertPurpose.TRUST,
                    cert_path=cert_path,
                    key_path=key_path,
                )
        finally:
            os.unlink(cert_path)
            os.unlink(key_path)

    def test_create_from_files_with_client_and_key(self) -> None:
        """Testing Certificate.create_from_files with purpose=client and
        key_path=
        """
        cert_fd, cert_path = tempfile.mkstemp()
        os.write(cert_fd, TEST_CLIENT_CERT_PEM)
        os.close(cert_fd)

        key_fd, key_path = tempfile.mkstemp()
        os.write(key_fd, TEST_CLIENT_KEY_PEM)
        os.close(key_fd)

        try:
            cert = Certificate.create_from_files(
                hostname='example.com',
                port=443,
                purpose=CertPurpose.CLIENT,
                cert_path=cert_path,
                key_path=key_path)
        finally:
            os.unlink(cert_path)
            os.unlink(key_path)

        self.assertEqual(cert.cert_data, TEST_CLIENT_CERT_PEM)
        self.assertEqual(cert.key_data, TEST_CLIENT_KEY_PEM)

    def test_create_from_files_with_cert_not_found(self) -> None:
        """Testing Certificate.create_from_files with cert not found"""
        message = 'The SSL/TLS certificate was not found.'

        with self.assertRaisesMessage(CertificateNotFoundError, message):
            Certificate.create_from_files(
                hostname='example.com',
                port=443,
                cert_path='/rb-tests-xxx/bad/')

    def test_create_from_files_with_ioerror_cert(self) -> None:
        """Testing Certificate.create_from_files with IOError reading cert"""
        self.spy_on(os.path.exists, op=kgb.SpyOpReturn(True))

        message = (
            r'Error reading SSL/TLS certificate file\. Administrators can '
            r'find details in the Review Board server logs \(error ID '
            r'[a-z0-9-]+\)\.'
        )

        with self.assertRaisesRegex(CertificateStorageError, message):
            Certificate.create_from_files(
                hostname='example.com',
                port=443,
                cert_path='/rb-tests/bad-path/')

    def test_create_from_files_with_invalid_cert(self) -> None:
        """Testing Certificate.create_from_files with invalid cert format"""
        cert_fd, cert_path = tempfile.mkstemp()
        os.write(cert_fd, b'XXX')
        os.close(cert_fd)

        try:
            with self.assertRaises(InvalidCertificateFormatError) as ctx:
                Certificate.create_from_files(
                    hostname='example.com',
                    port=443,
                    cert_path=cert_path)
        finally:
            os.unlink(cert_path)

        self.assertEqual(ctx.exception.data, b'XXX')
        self.assertEqual(ctx.exception.path, cert_path)

    def test_create_from_files_with_client_and_key_not_found(self) -> None:
        """Testing Certificate.create_from_files with purpose=client and
        key not found
        """
        cert_fd, cert_path = tempfile.mkstemp()
        os.write(cert_fd, TEST_CLIENT_CERT_PEM)
        os.close(cert_fd)

        message = 'The SSL/TLS private key was not found.'

        try:
            with self.assertRaisesMessage(CertificateNotFoundError, message):
                Certificate.create_from_files(
                    hostname='example.com',
                    port=443,
                    purpose=CertPurpose.CLIENT,
                    cert_path=cert_path,
                    key_path='/rb-tests-xxx/bad/')
        finally:
            os.unlink(cert_path)

    def test_create_from_files_with_client_and_ioerror_key(self) -> None:
        """Testing Certificate.create_from_files with purpose=client and
        IOError reading key
        """
        cert_fd, cert_path = tempfile.mkstemp()
        os.write(cert_fd, TEST_CLIENT_CERT_PEM)
        os.close(cert_fd)

        self.spy_on(os.path.exists, op=kgb.SpyOpReturn(True))

        message = (
            r'Error reading SSL/TLS private key file\. Administrators can '
            r'find details in the Review Board server logs \(error ID '
            r'[a-z0-9-]+\)\.'
        )

        try:
            with self.assertRaisesRegex(CertificateStorageError, message):
                Certificate.create_from_files(
                    hostname='example.com',
                    port=443,
                    purpose=CertPurpose.CLIENT,
                    cert_path=cert_path,
                    key_path='/rb-tests/bad-path/')
        finally:
            os.unlink(cert_path)

    def test_create_from_files_with_client_and_invalid_key(self) -> None:
        """Testing Certificate.create_from_files with purpose=client and
        invalid key format
        """
        cert_fd, cert_path = tempfile.mkstemp()
        os.write(cert_fd, TEST_CLIENT_CERT_PEM)
        os.close(cert_fd)

        key_fd, key_path = tempfile.mkstemp()
        os.write(key_fd, b'XXX')
        os.close(key_fd)

        try:
            with self.assertRaises(InvalidCertificateFormatError) as ctx:
                Certificate.create_from_files(
                    hostname='example.com',
                    port=443,
                    purpose=CertPurpose.CLIENT,
                    cert_path=cert_path,
                    key_path=key_path)
        finally:
            os.unlink(cert_path)
            os.unlink(key_path)

        self.assertEqual(ctx.exception.data, b'XXX')
        self.assertEqual(ctx.exception.path, key_path)

    @online_only
    def test_create_from_server(self) -> None:
        """Testing Certificate.create_from_server"""
        cert = Certificate.create_from_server(hostname='reviewboard.org',
                                              port=443)

        assert cert is not None
        self.assertAttrsEqual(
            cert,
            {
                'hostname': 'reviewboard.org',
                'port': 443,
            })
        self.assertIsNotNone(cert.cert_data)

    @online_only
    def test_create_from_server_with_bad_cert(self) -> None:
        """Testing Certificate.create_from_server with bad certificate state
        """
        cert = Certificate.create_from_server(hostname='expired.badssl.com',
                                              port=443)

        assert cert is not None
        self.assertAttrsEqual(
            cert,
            {
                'hostname': 'expired.badssl.com',
                'port': 443,
            })
        self.assertIsNotNone(cert.cert_data)

    @online_only
    def test_create_from_server_with_failure(self) -> None:
        """Testing Certificate.create_from_server with failure looking up
        cert
        """
        with self.assertLogs() as cm:
            cert = Certificate.create_from_server(
                hostname='xxx.badhosttld',
                port=443,
            )

        self.assertEqual(len(cm.output), 1)
        self.assertTrue(cm.output[0].startswith(
            'WARNING:reviewboard.certs.cert:Failed to fetch server '
            'certificate from xxx.badhosttld:443:'
        ))

        self.assertIsNone(cert)

    def test_init_with_valid_from_naive(self) -> None:
        """Testing Certificate.__init__ with valid_from as naive datetime"""
        message = 'valid_from must contain a timezone.'

        with self.assertRaisesMessage(ValueError, message):
            Certificate(hostname='example.com',
                        port=443,
                        valid_from=datetime(2023, 7, 14, 7, 50, 30))

    def test_init_with_valid_through_naive(self) -> None:
        """Testing Certificate.__init__ with valid_through as naive datetime"""
        message = 'valid_through must contain a timezone.'

        with self.assertRaisesMessage(ValueError, message):
            Certificate(hostname='example.com',
                        port=443,
                        valid_through=datetime(2023, 7, 14, 7, 50, 30))

    def test_x509_cert(self) -> None:
        """Testing Certificate.x509_cert"""
        cert = Certificate(hostname='example.com',
                           port=443,
                           cert_data=TEST_TRUST_CERT_PEM)

        x509_cert = cert.x509_cert
        assert x509_cert is not None

        name = (
            x509_cert.subject
            .get_attributes_for_oid(NameOID.COMMON_NAME)[0]
            .value
        )

        self.assertEqual(name, 'example.com')

        # This should be cached.
        self.assertIs(cert.x509_cert, x509_cert)

    def test_x509_cert_without_cert_data(self) -> None:
        """Testing Certificate.x509_cert without cert_data"""
        cert = Certificate(hostname='example.com',
                           port=443)

        self.assertIsNone(cert.x509_cert)

    def test_attrs_default(self) -> None:
        """Testing Certificate certificate attribute defaults"""
        cert = Certificate(hostname='example.com',
                           port=443)

        self.assertIsNone(cert.fingerprints)
        self.assertIsNone(cert.issuer)
        self.assertIsNone(cert.subject)
        self.assertEqual(cert.subject_alternative_names, [])
        self.assertIsNone(cert.valid_from)
        self.assertIsNone(cert.valid_through)

    def test_attrs_with_provided(self) -> None:
        """Testing Certificate certificate attributes provided during
        construction
        """
        cert = Certificate(
            hostname='example.com',
            port=443,
            subject='Subject',
            issuer='Issuer',
            fingerprints=CertificateFingerprints(sha1=TEST_SHA1,
                                                 sha256=TEST_SHA256),
            valid_from=datetime(2023, 7, 14, 7, 50, 30, tzinfo=timezone.utc),
            valid_through=datetime(2024, 7, 13, 7, 50, 30,
                                   tzinfo=timezone.utc))

        self.assertEqual(cert.subject, 'Subject')
        self.assertEqual(cert.issuer, 'Issuer')
        self.assertEqual(cert.subject_alternative_names, [])
        self.assertEqual(cert.valid_from,
                         datetime(2023, 7, 14, 7, 50, 30, tzinfo=timezone.utc))
        self.assertEqual(cert.valid_through,
                         datetime(2024, 7, 13, 7, 50, 30, tzinfo=timezone.utc))

        fingerprints = cert.fingerprints
        assert fingerprints is not None

        self.assertEqual(fingerprints.sha1, TEST_SHA1)
        self.assertEqual(fingerprints.sha256, TEST_SHA256)

    def test_attrs_with_x509(self) -> None:
        """Testing Certificate certificate attributes with cert data"""
        cert = Certificate(hostname='example.com',
                           port=443,
                           cert_data=TEST_TRUST_CERT_PEM)

        self.assertEqual(cert.subject, 'example.com')
        self.assertEqual(cert.issuer, 'example.com')
        self.assertEqual(cert.subject_alternative_names, [])
        self.assertEqual(cert.valid_from,
                         datetime(2023, 7, 14, 7, 50, 30, tzinfo=timezone.utc))
        self.assertEqual(cert.valid_through,
                         datetime(2024, 7, 13, 7, 50, 30, tzinfo=timezone.utc))

        fingerprints = cert.fingerprints
        assert fingerprints is not None

        self.assertEqual(fingerprints.sha1, TEST_SHA1)
        self.assertEqual(fingerprints.sha256, TEST_SHA256)

        # This should be cached.
        self.assertIs(cert.fingerprints, fingerprints)

    def test_attr_x509_subject_alt_names(self) -> None:
        """Testing Certificate.subject_alternative_names"""
        cert = Certificate(
            hostname='example.com',
            port=443,
            cert_data=b"""-----BEGIN CERTIFICATE-----
MIIEWzCCAkOgAwIBAgIUH/aJUMZgutxwbM0xXq8DRrfVR+gwDQYJKoZIhvcNAQEL
BQAwFzEVMBMGA1UEAwwMVGVzdCBMREFQIENBMB4XDTI2MDMxNjIzNDM0NVoXDTM2
MDMxMzIzNDM0NVowFDESMBAGA1UEAwwJbG9jYWxob3N0MIIBIjANBgkqhkiG9w0B
AQEFAAOCAQ8AMIIBCgKCAQEAvR432MX+pKoZcpXG7hP2DL6C3YlBggoDJ6YoKz1V
k8dNyX4jWkcYYXbDAMMWd72LQl/LBJeKguaeQpVqv3ViWCgK6aompJDkqyTNqs3l
sbL7ZXzBT+6E/iwP6ChxXEVY8EsBC8kAzBoq1gG1QvtT0qj1P0FpgPKl2T7SxwUG
B+k9gHNwHRRoMiFDVozbB3l6KHUaTro3RmVbAngzgK+2fYv5rXRKhdaKlIU555To
sExOXW9OCyiT7gUX8F/UGp05MhdGoJeB6rj6/Y6ekIubQbzW3JiPWXHuCelO/Iel
VNHUVRacUjXMndXVFx6J+AEmhIdhLK193WZoXV5eAMmd0QIDAQABo4GhMIGeMAkG
A1UdEwQCMAAwDgYDVR0PAQH/BAQDAgWgMBMGA1UdJQQMMAoGCCsGAQUFBwMBMCwG
A1UdEQQlMCOCCWxvY2FsaG9zdIcEfwAAAYcQAAAAAAAAAAAAAAAAAAAAATAdBgNV
HQ4EFgQURPbKJRFrb6AbUB4GuvEWMIKwCFcwHwYDVR0jBBgwFoAUFZ8R0MgmCmxb
G0buLdWs5L+1kT0wDQYJKoZIhvcNAQELBQADggIBACRE4MjIm1hlC5+xiBlyrQ1i
B1TWcRkX9+0UQfI4BMdaIPrEZLz1B8mdRcRAn5NKyfjQKhUsbW7aBXUD/3wsxuy+
Lfgek8xvDoeY4y/L4wkdFl+QfYKgwLsXrzMexHwcCZ3SEvaqFrm55hW0hVcX5FeW
4FARqlGIWp+MSPfGtDHbncGUnk+fRO4EGiZcsakQNdzL7Gn+aS/1swk0A0w6V5bx
+/LkMhkTEZt+fClRAMNW2X169ki+/vDe7pQQinrQ6j+8fDwMvrAD+qpSM91CJLNA
ddMXmrDbvYgDQdQ+YbineuSahoIjgPzE8hJ8rSVl5R+uGSjTgbS5JsrqlA+bP0se
/VzkkIglRm5XmGUHYT4CQIAbbg1u5wQsOrgaymBbFWN08eNhNAak0j0KhmF1PDy6
LML/n+xSjIDwI4llZkog1hv1jmSCW0PJ9ty6UHb6yfZ063spR/SIpMtekGkLllAR
RwPgp5YWsu1t/GiEk0qWlXT6qRxtjYh2zL5SorEAmJtwOYZj5ywuKG4NUzZQ9vqD
0PsulCD8L5we9EAuxYY9D9wQL7qlQLoPnL01FRscsVFHEw6Dv3noqCa0BzjMcU3H
RS9daj4M6YOwBbgGt+YgjLCGsQ7fRGXYo1UebeZDFE6RwLJ0FQvzUQQfuEk7qSq3
pa6+8p+V5VkIunYFLWOw
-----END CERTIFICATE-----""")

        self.assertEqual(cert.subject_alternative_names, [
            'localhost',
            '127.0.0.1',
            '::1',
        ])

    def test_is_valid_with_not_expired(self) -> None:
        """Testing Certificate.is_valid with not expired"""
        cert_data = self.build_x509_cert_pem()

        cert = Certificate(hostname='example.com',
                           port=443,
                           cert_data=cert_data)

        self.assertTrue(cert.is_valid)

    def test_is_valid_with_expired(self) -> None:
        """Testing Certificate.is_valid with expired"""
        cert_data = self.build_x509_cert_pem(
            not_valid_before_delta=-timedelta(days=10),
            not_valid_after_delta=-timedelta(days=5))

        cert = Certificate(hostname='example.com',
                           port=443,
                           cert_data=cert_data)

        self.assertFalse(cert.is_valid)

    def test_is_valid_with_not_yet_valid(self) -> None:
        """Testing Certificate.is_valid with not yet valid"""
        cert_data = self.build_x509_cert_pem(
            not_valid_before_delta=timedelta(days=5),
            not_valid_after_delta=timedelta(days=10))

        cert = Certificate(hostname='example.com',
                           port=443,
                           cert_data=cert_data)

        self.assertFalse(cert.is_valid)

    def test_is_wildcard_with_true(self) -> None:
        """Testing Certificate.is_wildcard with wildcard domain"""
        cert = Certificate(hostname='w*.example.com',
                           port=443)

        self.assertTrue(cert.is_wildcard)

    def test_is_wildcard_with_false(self) -> None:
        """Testing Certificate.is_wildcard with non-wildcard domain"""
        cert = Certificate(hostname='www.example.com',
                           port=443)

        self.assertFalse(cert.is_wildcard)

    def test_write_cert_file(self) -> None:
        """Testing Certificate.write_cert_file"""
        cert = Certificate(hostname='example.com',
                           port=443,
                           cert_data=TEST_TRUST_CERT_PEM)

        fd, path = tempfile.mkstemp()
        os.close(fd)

        try:
            cert.write_cert_file(path)

            with open(path, 'rb') as fp:
                self.assertEqual(fp.read(), TEST_TRUST_CERT_PEM)
        finally:
            os.unlink(path)

    def test_write_cert_file_with_ioerror(self) -> None:
        """Testing Certificate.write_cert_file with IOError"""
        cert = Certificate(hostname='example.com',
                           port=443,
                           cert_data=TEST_TRUST_CERT_PEM)

        message = (
            r'Error writing SSL/TLS certificate file\. Administrators can '
            r'find details in the Review Board server logs \(error ID '
            r'[a-z0-9-]+\)\.'
        )

        with self.assertRaisesRegex(CertificateStorageError, message):
            cert.write_cert_file('/rb-tests-xxx/bad/')

    def test_write_key_file(self) -> None:
        """Testing Certificate.write_key_file"""
        cert = Certificate(hostname='example.com',
                           port=443,
                           purpose=CertPurpose.CLIENT,
                           cert_data=TEST_CLIENT_CERT_PEM,
                           key_data=TEST_CLIENT_KEY_PEM)

        fd, path = tempfile.mkstemp()
        os.close(fd)

        try:
            cert.write_key_file(path)

            with open(path, 'rb') as fp:
                self.assertEqual(fp.read(), TEST_CLIENT_KEY_PEM)
        finally:
            os.unlink(path)

    def test_write_key_file_with_ioerror(self) -> None:
        """Testing Certificate.write_key_file with IOError"""
        cert = Certificate(hostname='example.com',
                           port=443,
                           purpose=CertPurpose.CLIENT,
                           cert_data=TEST_CLIENT_CERT_PEM,
                           key_data=TEST_CLIENT_KEY_PEM)

        message = (
            r'Error writing SSL/TLS private key file\. Administrators can '
            r'find details in the Review Board server logs \(error ID '
            r'[a-z0-9-]+\)\.'
        )

        with self.assertRaisesRegex(CertificateStorageError, message):
            cert.write_key_file('/rb-tests-xxx/bad/')

    def test_repr(self) -> None:
        """Testing Certificate.__repr__"""
        cert = Certificate(hostname='example.com',
                           port=443)

        self.assertEqual(
            repr(cert),
            "<Certificate(hostname='example.com', port=443, "
            "purpose=CertPurpose.TRUST, fingerprints=None)>")

    def test_repr_with_fingerprints(self) -> None:
        """Testing Certificate.__repr__ with fingerprints"""
        cert = Certificate(
            hostname='example.com',
            port=443,
            fingerprints=CertificateFingerprints(sha1=TEST_SHA1))

        self.assertEqual(
            repr(cert),
            "<Certificate(hostname='example.com', port=443, "
            "purpose=CertPurpose.TRUST, "
            "fingerprints=<CertificateFingerprints("
            "sha1='F2:35:0F:BB:34:40:84:78:8B:20:1D:40:B1:4A:17:0C:DE:36:2F:"
            "D5', sha256=None)>)>")

    def test_to_json(self) -> None:
        """Testing Certificate.to_json"""
        fingerprints = CertificateFingerprints(sha1=TEST_SHA1,
                                               sha256=TEST_SHA256)

        cert = Certificate(
            hostname='example.com',
            port=443,
            subject='Subject',
            issuer='Issuer',
            fingerprints=CertificateFingerprints(sha1=TEST_SHA1,
                                                 sha256=TEST_SHA256),
            valid_from=datetime(2023, 7, 14, 7, 50, 30, tzinfo=timezone.utc),
            valid_through=datetime(2024, 7, 13, 7, 50, 30,
                                   tzinfo=timezone.utc))

        json_data = cert.to_json()

        self.assertEqual(
            json_data,
            {
                'fingerprints': fingerprints,
                'hostname': 'example.com',
                'issuer': 'Issuer',
                'port': 443,
                'purpose': 'trust',
                'subject': 'Subject',
                'valid_from': datetime(2023, 7, 14, 7, 50, 30,
                                       tzinfo=timezone.utc),
                'valid_through': datetime(2024, 7, 13, 7, 50, 30,
                                          tzinfo=timezone.utc),
            })

        # Verify we used encodeable data.
        self.assertJSONEqual(
            json.dumps(json_data, cls=DjbletsJSONEncoder),
            {
                'fingerprints': {
                    'sha1': (
                        'F2:35:0F:BB:34:40:84:78:8B:20:1D:40:B1:4A:17:0C:DE:'
                        '36:2F:D5'
                    ),
                    'sha256': (
                        '79:19:70:AE:A6:1B:EB:BC:35:7C:B8:54:B1:6A:AD:79:FF:'
                        'F7:28:69:02:5E:C3:6F:B3:C2:B4:FD:84:66:DF:8F'
                    ),
                },
                'hostname': 'example.com',
                'issuer': 'Issuer',
                'port': 443,
                'purpose': 'trust',
                'subject': 'Subject',
                'valid_from': '2023-07-14T07:50:30Z',
                'valid_through': '2024-07-13T07:50:30Z',
            })
