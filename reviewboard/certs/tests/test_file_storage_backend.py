"""Unit tests for reviewboard.certs.storage.file_storage.

Version Added:
    6.0
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from typing import Optional, TYPE_CHECKING

import kgb

from reviewboard.certs.cert import (Certificate,
                                    CertificateBundle,
                                    CertificateFingerprints)
from reviewboard.certs.errors import (CertificateNotFoundError,
                                      CertificateStorageError)
from reviewboard.certs.storage.file_storage import (
    FileStoredCertificate,
    FileStoredCertificateBundle,
    FileStoredCertificateFingerprints,
    FileCertificateStorageBackend)
from reviewboard.certs.tests.testcases import (CertificateTestCase,
                                               TEST_CERT_BUNDLE_PEM,
                                               TEST_CERT_PEM,
                                               TEST_KEY_PEM,
                                               TEST_SHA1,
                                               TEST_SHA256)
from reviewboard.site.models import LocalSite

if TYPE_CHECKING:
    TestsMixinParentClass = CertificateTestCase
else:
    TestsMixinParentClass = object


TEST_FINGERPRINTS_JSON = json.dumps({
    'sha1': TEST_SHA1,
    'sha256': TEST_SHA256,
}).encode('utf-8')


class FileStoredDataTestCase(CertificateTestCase):
    """Base test case for file-based stored data tests.

    Version Added:
        6.0
    """

    #: An instance of the storage class to test with.
    #:
    #: Type:
    #:     reviewboard.certs.storage.file_storage.FileCertificateStorageBackend
    storage: FileCertificateStorageBackend

    @classmethod
    def setUpClass(cls) -> None:
        """Set up class-wide state for the test case.

        This will create a storage instance suitable for stored data object
        tests.
        """
        super().setUpClass()

        cls.storage = FileCertificateStorageBackend(storage_path='/xxx')

    @classmethod
    def tearDownClass(cls) -> None:
        """Tear down class-wide state for the test case."""
        # Note that we're ignoring the None because we're just in cleanup
        # phase, and don't want to have to mark storage as Optional[...].
        cls.storage = None  # type: ignore

        super().tearDownClass()


class FileStoredCertificateTests(FileStoredDataTestCase):
    """Unit tests for FileStoredCertificate.

    Version Added:
        6.0
    """

    def test_init_with_certificate(self) -> None:
        """Testing FileStoredCertificate.__init__ with certificate"""
        storage = self.storage
        stored_cert = FileStoredCertificate(
            storage=storage,
            cert_file_path='/path',
            certificate=Certificate(hostname='example.com',
                                    port=443,
                                    cert_data=b'...'))

        self.assertAttrsEqual(
            stored_cert,
            {
                '_hostname': 'example.com',
                '_port': 443,
                'local_site': None,
                'storage': storage,
                'storage_id': 'example.com:443',
            })

    def test_init_with_hostname_port(self) -> None:
        """Testing FileStoredCertificate.__init__ with hostname and port"""
        storage = self.storage
        stored_cert = FileStoredCertificate(
            storage=storage,
            cert_file_path='/path',
            hostname='example.com',
            port=443)

        self.assertAttrsEqual(
            stored_cert,
            {
                '_hostname': 'example.com',
                '_port': 443,
                'local_site': None,
                'storage': storage,
                'storage_id': 'example.com:443',
            })

    def test_init_with_local_site(self) -> None:
        """Testing FileStoredCertificate.__init__ with Local Site"""
        local_site = self.create_local_site(name='test-site')
        storage = self.storage
        stored_cert = FileStoredCertificate(
            storage=storage,
            cert_file_path='/path',
            hostname='example.com',
            port=443,
            local_site=local_site)

        self.assertAttrsEqual(
            stored_cert,
            {
                '_hostname': 'example.com',
                '_port': 443,
                'local_site': local_site,
                'storage': storage,
                'storage_id': 'test-site:example.com:443',
            })

    def test_parse_storage_id(self) -> None:
        """Testing FileStoredCertificate.parse_storage_id"""
        self.assertEqual(
            FileStoredCertificate.parse_storage_id('example.com:443'),
            {
                'hostname': 'example.com',
                'local_site': None,
                'port': 443,
            })

    def test_parse_storage_id_with_local_site(self) -> None:
        """Testing FileStoredCertificate.parse_storage_id with LocalSite"""
        local_site = self.create_local_site(name='test-site')

        self.assertEqual(
            FileStoredCertificate.parse_storage_id(
                'test-site:example.com:443'),
            {
                'hostname': 'example.com',
                'local_site': local_site,
                'port': 443,
            })

    def test_parse_storage_id_with_local_site_not_found(self) -> None:
        """Testing FileStoredCertificate.parse_storage_id with LocalSite not
        found in database
        """
        result = FileStoredCertificate.parse_storage_id(
            'bad-site:example.com:443')

        self.assertEqual(result['hostname'], 'example.com')
        self.assertEqual(result['port'], 443)

        local_site = result['local_site']
        self.assertIsNotNone(local_site)
        self.assertIsNone(local_site.pk)
        self.assertEqual(local_site.name, 'bad-site')

    def test_parse_storage_id_with_invalid(self) -> None:
        """Testing FileStoredCertificate.parse_storage_id with invalid ID"""
        message = (
            r'Internal error parsing a SSL/TLS certificate storage ID\. '
            r'Administrators can find details in the Review Board server logs '
            r'\(error ID [a-f0-9-]+\)\.'
        )

        with self.assertRaisesRegex(CertificateStorageError, message):
            FileStoredCertificate.parse_storage_id('')

        with self.assertRaisesRegex(CertificateStorageError, message):
            FileStoredCertificate.parse_storage_id('123')

        with self.assertRaisesRegex(CertificateStorageError, message):
            FileStoredCertificate.parse_storage_id('example.com_443')

        with self.assertRaisesRegex(CertificateStorageError, message):
            FileStoredCertificate.parse_storage_id('example.com:bad')

        with self.assertRaisesRegex(CertificateStorageError, message):
            FileStoredCertificate.parse_storage_id('test-site:example.com:bad')

        with self.assertRaisesRegex(CertificateStorageError, message):
            FileStoredCertificate.parse_storage_id(
                'test-site:example.com:443:bad')

    def test_get_cert_file_path(self) -> None:
        """Testing FileStoredCertificate.get_cert_file_path"""
        stored_cert = FileStoredCertificate(
            storage=self.storage,
            cert_file_path='/path/to/cert.crt',
            hostname='example.com',
            port=443)

        self.assertEqual(stored_cert.get_cert_file_path(),
                         '/path/to/cert.crt')

    def test_get_key_file_path(self) -> None:
        """Testing FileStoredCertificate.get_key_file_path"""
        stored_cert = FileStoredCertificate(
            storage=self.storage,
            cert_file_path='/path/to/cert.crt',
            key_file_path='/path/to/cert.key',
            hostname='example.com',
            port=443)

        self.assertEqual(stored_cert.get_key_file_path(),
                         '/path/to/cert.key')

    def test_get_key_file_path_not_set(self) -> None:
        """Testing FileStoredCertificate.get_key_file_path with None"""
        stored_cert = FileStoredCertificate(
            storage=self.storage,
            cert_file_path='/path/to/cert.crt',
            hostname='example.com',
            port=443)

        self.assertIsNone(stored_cert.get_key_file_path())

    def test_load_certificate(self) -> None:
        """Testing FileStoredCertificate.load_certificate"""
        cert_fd, cert_file_path = tempfile.mkstemp()
        os.write(cert_fd, TEST_CERT_PEM)
        os.close(cert_fd)

        try:
            stored_cert = FileStoredCertificate(
                storage=self.storage,
                cert_file_path=cert_file_path,
                hostname='example.com',
                port=443)

            certificate = stored_cert.load_certificate()
        finally:
            os.unlink(cert_file_path)

        self.assertAttrsEqual(
            certificate,
            {
                'cert_data': TEST_CERT_PEM,
                'hostname': 'example.com',
                'key_data': None,
                'port': 443,
            })

    def test_load_certificate_with_key(self) -> None:
        """Testing FileStoredCertificate.load_certificate with key"""
        cert_fd, cert_file_path = tempfile.mkstemp()
        os.write(cert_fd, TEST_CERT_PEM)
        os.close(cert_fd)

        key_fd, key_file_path = tempfile.mkstemp()
        os.write(key_fd, TEST_KEY_PEM)
        os.close(key_fd)

        try:
            stored_cert = FileStoredCertificate(
                storage=self.storage,
                cert_file_path=cert_file_path,
                key_file_path=key_file_path,
                hostname='example.com',
                port=443)

            certificate = stored_cert.load_certificate()
        finally:
            os.unlink(cert_file_path)
            os.unlink(key_file_path)

        self.assertAttrsEqual(
            certificate,
            {
                'cert_data': TEST_CERT_PEM,
                'hostname': 'example.com',
                'key_data': TEST_KEY_PEM,
                'port': 443,
            })

    def test_load_certificate_with_error(self) -> None:
        """Testing FileStoredCertificate.load_certificate with error"""
        cert_fd, cert_file_path = tempfile.mkstemp()
        os.write(cert_fd, b'XXX')
        os.close(cert_fd)

        message = (
            'Invalid certificate file found at "%s". This was not in a '
            'supported format.'
            % cert_file_path
        )

        try:
            stored_cert = FileStoredCertificate(
                storage=self.storage,
                cert_file_path=cert_file_path,
                hostname='example.com',
                port=443)

            with self.assertRaisesMessage(CertificateStorageError, message):
                stored_cert.load_certificate()
        finally:
            os.unlink(cert_file_path)


class FileStoredCertificateBundleTests(FileStoredDataTestCase):
    """Unit tests for FileStoredCertificateBundle.

    Version Added:
        6.0
    """

    def test_init_with_bundle(self) -> None:
        """Testing FileStoredCertificateBundle.__init__ with bundle"""
        storage = self.storage
        stored_bundle = FileStoredCertificateBundle(
            storage=storage,
            bundle_file_path='/path',
            bundle=CertificateBundle(name='my-cert-bundle',
                                     bundle_data=b'...'))

        self.assertAttrsEqual(
            stored_bundle,
            {
                '_name': 'my-cert-bundle',
                'local_site': None,
                'storage': storage,
                'storage_id': 'my-cert-bundle',
            })

    def test_init_with_name(self) -> None:
        """Testing FileStoredCertificateBundle.__init__ with name"""
        storage = self.storage
        stored_bundle = FileStoredCertificateBundle(
            storage=storage,
            bundle_file_path='/path',
            name='my-cert-bundle')

        self.assertAttrsEqual(
            stored_bundle,
            {
                '_name': 'my-cert-bundle',
                'local_site': None,
                'storage': storage,
                'storage_id': 'my-cert-bundle',
            })

    def test_init_with_local_site(self) -> None:
        """Testing FileStoredCertificateBundle.__init__ with Local Site"""
        local_site = self.create_local_site(name='test-site')
        storage = self.storage
        stored_bundle = FileStoredCertificateBundle(
            storage=storage,
            bundle_file_path='/path',
            name='my-cert-bundle',
            local_site=local_site)

        self.assertAttrsEqual(
            stored_bundle,
            {
                '_name': 'my-cert-bundle',
                'local_site': local_site,
                'storage': storage,
                'storage_id': 'test-site:my-cert-bundle',
            })

    def test_parse_storage_id(self) -> None:
        """Testing FileStoredCertificateBundle.parse_storage_id"""
        self.assertEqual(
            FileStoredCertificateBundle.parse_storage_id('my-cert-bundle'),
            {
                'local_site': None,
                'name': 'my-cert-bundle',
            })

    def test_parse_storage_id_with_local_site(self) -> None:
        """Testing FileStoredCertificateBundle.parse_storage_id with LocalSite
        """
        local_site = self.create_local_site(name='test-site')

        self.assertEqual(
            FileStoredCertificateBundle.parse_storage_id(
                'test-site:my-cert-bundle'),
            {
                'local_site': local_site,
                'name': 'my-cert-bundle',
            })

    def test_parse_storage_id_with_local_site_not_found(self) -> None:
        """Testing FileStoredCertificateBundle.parse_storage_id with LocalSite
        not found in database
        """
        result = FileStoredCertificateBundle.parse_storage_id(
            'bad-site:my-cert-bundle')

        self.assertEqual(result['name'], 'my-cert-bundle')

        local_site = result['local_site']
        self.assertIsNotNone(local_site)
        self.assertIsNone(local_site.pk)
        self.assertEqual(local_site.name, 'bad-site')

    def test_parse_storage_id_with_invalid(self) -> None:
        """Testing FileStoredCertificateBundle.parse_storage_id with
        invalid ID
        """
        message = (
            r'Internal error parsing a SSL/TLS certificate storage ID\. '
            r'Administrators can find details in the Review Board server logs '
            r'\(error ID [a-f0-9-]+\)\.'
        )

        with self.assertRaisesRegex(CertificateStorageError, message):
            FileStoredCertificate.parse_storage_id('')

        with self.assertRaisesRegex(CertificateStorageError, message):
            FileStoredCertificate.parse_storage_id('non-slug name')

        with self.assertRaisesRegex(CertificateStorageError, message):
            FileStoredCertificate.parse_storage_id('slug:bad')

    def test_load_bundle(self) -> None:
        """Testing FileStoredCertificateBundle.load_bundle"""
        cert_fd, bundle_file_path = tempfile.mkstemp()
        os.write(cert_fd, TEST_CERT_BUNDLE_PEM)
        os.close(cert_fd)

        try:
            stored_bundle = FileStoredCertificateBundle(
                storage=self.storage,
                bundle_file_path=bundle_file_path,
                name='my-cert-bundle')

            bundle = stored_bundle.load_bundle()
        finally:
            os.unlink(bundle_file_path)

        self.assertAttrsEqual(
            bundle,
            {
                'bundle_data': TEST_CERT_BUNDLE_PEM,
                'name': 'my-cert-bundle',
            })

    def test_load_bundle_with_error(self) -> None:
        """Testing FileStoredCertificateBundle.load_bundle with error"""
        cert_fd, bundle_file_path = tempfile.mkstemp()
        os.write(cert_fd, b'XXX')
        os.close(cert_fd)

        message = (
            'Invalid certificate file found at "%s". This was not in a '
            'supported format.'
            % bundle_file_path
        )

        try:
            stored_bundle = FileStoredCertificateBundle(
                storage=self.storage,
                bundle_file_path=bundle_file_path,
                name='my-cert-bundle')

            with self.assertRaisesMessage(CertificateStorageError, message):
                stored_bundle.load_bundle()
        finally:
            os.unlink(bundle_file_path)


class FileStoredCertificateFingerprintsTests(FileStoredDataTestCase):
    """Unit tests for FileStoredCertificateFingerprints.

    Version Added:
        6.0
    """

    def test_init(self) -> None:
        """Testing FileStoredCertificateFingerprints.__init__"""
        storage = self.storage
        stored_fingerprints = FileStoredCertificateFingerprints(
            storage=storage,
            hostname='example.com',
            port=443,
            fingerprints_file_path='/path')

        self.assertAttrsEqual(
            stored_fingerprints,
            {
                '_hostname': 'example.com',
                '_port': 443,
                'local_site': None,
                'storage': storage,
                'storage_id': 'example.com:443',
            })

    def test_init_with_local_site(self) -> None:
        """Testing FileStoredCertificateFingerprints.__init__ with Local Site
        """
        local_site = self.create_local_site(name='test-site')
        storage = self.storage
        stored_fingerprints = FileStoredCertificateFingerprints(
            storage=storage,
            hostname='example.com',
            port=443,
            fingerprints_file_path='/path',
            local_site=local_site)

        self.assertAttrsEqual(
            stored_fingerprints,
            {
                '_hostname': 'example.com',
                '_port': 443,
                'local_site': local_site,
                'storage': storage,
                'storage_id': 'test-site:example.com:443',
            })

    def test_parse_storage_id(self) -> None:
        """Testing FileStoredCertificateFingerprints.parse_storage_id"""
        self.assertEqual(
            FileStoredCertificateFingerprints.parse_storage_id(
                'example.com:443'),
            {
                'hostname': 'example.com',
                'local_site': None,
                'port': 443,
            })

    def test_parse_storage_id_with_local_site(self) -> None:
        """Testing FileStoredCertificateFingerprints.parse_storage_id with
        LocalSite
        """
        local_site = self.create_local_site(name='test-site')

        self.assertEqual(
            FileStoredCertificateFingerprints.parse_storage_id(
                'test-site:example.com:443'),
            {
                'hostname': 'example.com',
                'local_site': local_site,
                'port': 443,
            })

    def test_parse_storage_id_with_local_site_not_found(self) -> None:
        """Testing FileStoredCertificateFingerprints.parse_storage_id with
        LocalSite not found in database
        """
        result = FileStoredCertificateFingerprints.parse_storage_id(
            'bad-site:example.com:443')

        self.assertEqual(result['hostname'], 'example.com')
        self.assertEqual(result['port'], 443)

        local_site = result['local_site']
        self.assertIsNotNone(local_site)
        self.assertIsNone(local_site.pk)
        self.assertEqual(local_site.name, 'bad-site')

    def test_parse_storage_id_with_invalid(self) -> None:
        """Testing FileStoredCertificateFingerprints.parse_storage_id with
        invalid ID"""
        message = (
            r'Internal error parsing a SSL/TLS certificate storage ID\. '
            r'Administrators can find details in the Review Board server logs '
            r'\(error ID [a-f0-9-]+\)\.'
        )

        with self.assertRaisesRegex(CertificateStorageError, message):
            FileStoredCertificate.parse_storage_id('')

        with self.assertRaisesRegex(CertificateStorageError, message):
            FileStoredCertificate.parse_storage_id('123')

        with self.assertRaisesRegex(CertificateStorageError, message):
            FileStoredCertificate.parse_storage_id('bad')

        with self.assertRaisesRegex(CertificateStorageError, message):
            FileStoredCertificate.parse_storage_id('example.com:bad')

        with self.assertRaisesRegex(CertificateStorageError, message):
            FileStoredCertificate.parse_storage_id('test-site:example.com:bad')

        with self.assertRaisesRegex(CertificateStorageError, message):
            FileStoredCertificate.parse_storage_id(
                'test-site:example.com:443:bad')

    def test_load_fingerprints(self) -> None:
        """Testing FileStoredCertificateFingerprints.load_fingerprints"""
        cert_fd, fingerprints_file_path = tempfile.mkstemp()
        os.write(cert_fd, TEST_FINGERPRINTS_JSON)
        os.close(cert_fd)

        try:
            stored_fingerprints = FileStoredCertificateFingerprints(
                storage=self.storage,
                hostname='example.com',
                port=443,
                fingerprints_file_path=fingerprints_file_path)

            fingerprints = stored_fingerprints.load_fingerprints()
        finally:
            os.unlink(fingerprints_file_path)

        self.assertAttrsEqual(
            fingerprints,
            {
                'sha1': TEST_SHA1,
                'sha256': TEST_SHA256,
            })

    def test_load_fingerprints_with_error(self) -> None:
        """Testing FileStoredCertificateFingerprints.load_fingerprints with
        error
        """
        message = (
            r'Error loading SSL/TLS certificate fingerprints\. '
            r'Administrators can find details in the Review Board server '
            r'logs \(error ID [a-f0-9-]+\)\.'
        )

        cert_fd, fingerprints_file_path = tempfile.mkstemp()
        os.write(cert_fd, b'XXX')
        os.close(cert_fd)

        try:
            stored_fingerprints = FileStoredCertificateFingerprints(
                storage=self.storage,
                hostname='example.com',
                port=443,
                fingerprints_file_path=fingerprints_file_path)

            with self.assertRaisesRegex(CertificateStorageError, message):
                stored_fingerprints.load_fingerprints()
        finally:
            os.unlink(fingerprints_file_path)


class FileCertificateStorageBackendTests(kgb.SpyAgency, CertificateTestCase):
    """Unit tests for FileCertificateStorageBackend.

    Version Added:
        6.0
    """

    testdata_dir = os.path.join(CertificateTestCase.base_testdata_dir,
                                'file_storage')

    def test_get_stats(self) -> None:
        """Testing FileCertificateStorageBackend.get_stats"""
        backend = self._create_backend(storage_path=self.testdata_dir)
        stats1 = backend.get_stats()
        state_uuid1 = stats1['state_uuid']

        self.assertEqual(stats1['ca_bundle_count'], 2)
        self.assertEqual(stats1['cert_count'], 4)
        self.assertEqual(stats1['fingerprint_count'], 3)
        self.assertIsNotNone(state_uuid1)

        # Make sure this is cached.
        stats2 = backend.get_stats()
        self.assertEqual(stats2, stats1)

    def test_get_stats_with_local_site(self) -> None:
        """Testing FileCertificateStorageBackend.get_stats with LocalSite"""
        backend = self._create_backend(storage_path=self.testdata_dir)

        # This site has cabundles, certs, and fingerprints.
        stats = backend.get_stats(
            local_site=self.create_local_site(name='test-site-1'))
        state_uuid1 = stats['state_uuid']

        self.assertEqual(stats['ca_bundle_count'], 2)
        self.assertEqual(stats['cert_count'], 1)
        self.assertEqual(stats['fingerprint_count'], 1)
        self.assertIsNotNone(state_uuid1)

        # This site has cabundles, certs, and fingerprints.
        stats = backend.get_stats(
            local_site=self.create_local_site(name='test-site-2'))
        state_uuid2 = stats['state_uuid']

        self.assertEqual(stats['ca_bundle_count'], 1)
        self.assertEqual(stats['cert_count'], 3)
        self.assertEqual(stats['fingerprint_count'], 2)
        self.assertIsNotNone(state_uuid2)
        self.assertNotEqual(state_uuid2, state_uuid1)

        # This site has cert directories but no files.
        stats = backend.get_stats(
            local_site=self.create_local_site(name='test-site-3'))
        state_uuid3 = stats['state_uuid']

        self.assertEqual(stats['ca_bundle_count'], 0)
        self.assertEqual(stats['cert_count'], 0)
        self.assertEqual(stats['fingerprint_count'], 0)
        self.assertIsNotNone(state_uuid3)
        self.assertNotEqual(state_uuid3, state_uuid1)
        self.assertNotEqual(state_uuid3, state_uuid2)

        # This site has no cert directories at all.
        stats = backend.get_stats(
            local_site=self.create_local_site(name='test-site-4'))
        state_uuid4 = stats['state_uuid']

        self.assertEqual(stats['ca_bundle_count'], 0)
        self.assertEqual(stats['cert_count'], 0)
        self.assertEqual(stats['fingerprint_count'], 0)
        self.assertIsNotNone(state_uuid4)
        self.assertNotEqual(state_uuid4, state_uuid1)
        self.assertNotEqual(state_uuid4, state_uuid2)
        self.assertNotEqual(state_uuid4, state_uuid3)

    def test_get_stats_with_local_site_all(self) -> None:
        """Testing FileCertificateStorageBackend.get_stats with LocalSite.ALL
        """
        backend = self._create_backend(storage_path=self.testdata_dir)

        self.create_local_site(name='test-site-1')
        self.create_local_site(name='test-site-2')
        self.create_local_site(name='test-site-3')

        # This site has certs and fingerprints, but no cabundles.
        stats = backend.get_stats(local_site=LocalSite.ALL)

        self.assertEqual(stats['ca_bundle_count'], 5)
        self.assertEqual(stats['cert_count'], 8)
        self.assertEqual(stats['fingerprint_count'], 6)
        self.assertIsNotNone(stats['state_uuid'])

    def test_add_ca_bundle(self) -> None:
        """Testing FileCertificateStorageBackend.add_ca_bundle"""
        backend = self._create_backend()
        path = os.path.join(backend.storage_path, 'cabundles', 'my-certs.pem')

        self.spy_on(backend._invalidate_stats_cache)

        stored_bundle = backend.add_ca_bundle(
            CertificateBundle(bundle_data=TEST_CERT_BUNDLE_PEM,
                              name='my-certs'))

        self.assertIsNotNone(stored_bundle)
        self.assertAttrsEqual(
            stored_bundle,
            {
                '_bundle_file_path': path,
                '_name': 'my-certs',
                'local_site': None,
                'storage': backend,
                'storage_id': 'my-certs',
            })
        self.assertTrue(os.path.exists(path))

        with open(path, 'rb') as fp:
            self.assertEqual(fp.read(), TEST_CERT_BUNDLE_PEM)

        # Make sure this clears cache.
        self.assertSpyCalledWith(backend._invalidate_stats_cache,
                                 local_site=None)

    def test_add_ca_bundle_with_local_site(self) -> None:
        """Testing FileCertificateStorageBackend.add_ca_bundle with LocalSite
        """
        local_site = self.create_local_site(name='test-site')
        backend = self._create_backend()
        path = os.path.join(backend.storage_path, 'sites', 'test-site',
                            'cabundles', 'my-certs.pem')

        self.spy_on(backend._invalidate_stats_cache)

        stored_bundle = backend.add_ca_bundle(
            CertificateBundle(bundle_data=TEST_CERT_BUNDLE_PEM,
                              name='my-certs'),
            local_site=local_site)

        self.assertIsNotNone(stored_bundle)
        self.assertAttrsEqual(
            stored_bundle,
            {
                '_bundle_file_path': path,
                '_name': 'my-certs',
                'local_site': local_site,
                'storage': backend,
                'storage_id': 'test-site:my-certs',
            })
        self.assertTrue(os.path.exists(path))

        with open(path, 'rb') as fp:
            self.assertEqual(fp.read(), TEST_CERT_BUNDLE_PEM)

        # Make sure this clears cache.
        self.assertSpyCalledWith(backend._invalidate_stats_cache,
                                 local_site=local_site)

    def test_delete_ca_bundle(self) -> None:
        """Testing FileCertificateStorageBackend.delete_ca_bundle"""
        backend = self._create_backend()
        path = os.path.join(backend.storage_path, 'cabundles', 'my-certs.pem')

        self.spy_on(backend._invalidate_stats_cache)

        self._write_file(path, TEST_CERT_BUNDLE_PEM)

        backend.delete_ca_bundle(name='my-certs')

        self.assertFalse(os.path.exists(path))

        # Make sure this clears cache.
        self.assertSpyCalledWith(backend._invalidate_stats_cache,
                                 local_site=None)

    def test_delete_ca_bundle_with_local_site(self) -> None:
        """Testing FileCertificateStorageBackend.delete_ca_bundle with
        LocalSite
        """
        local_site = self.create_local_site(name='test-site')
        backend = self._create_backend()
        path = os.path.join(backend.storage_path, 'sites', 'test-site',
                            'cabundles', 'my-certs.pem')

        self.spy_on(backend._invalidate_stats_cache)

        self._write_file(path, TEST_CERT_BUNDLE_PEM)

        backend.delete_ca_bundle(name='my-certs',
                                      local_site=local_site)

        self.assertFalse(os.path.exists(path))

        # Make sure this clears cache.
        self.assertSpyCalledWith(backend._invalidate_stats_cache,
                                 local_site=local_site)

    def test_delete_ca_bundle_with_not_found(self) -> None:
        """Testing FileCertificateStorageBackend.delete_ca_bundle with
        not found
        """
        backend = self._create_backend()

        self.spy_on(backend._invalidate_stats_cache)

        with self.assertRaises(CertificateNotFoundError):
            backend.delete_ca_bundle(name='missing-cert')

        # Make sure this does not clear cache.
        self.assertSpyNotCalledWith(backend._invalidate_stats_cache,
                                    local_site=None)

    def test_delete_ca_bundle_with_ioerror(self) -> None:
        """Testing FileCertificateStorageBackend.delete_ca_bundle with
        IOError handling
        """
        backend = self._create_backend()

        self.spy_on(backend._invalidate_stats_cache)
        self.spy_on(backend._build_ca_bundle_file_path,
                    op=kgb.SpyOpReturn(os.path.join(backend.storage_path,
                                                    'xxx-bad-path')))

        message = (
            r'Error deleting SSL/TLS CA bundle\. Administrators can find '
            r'details in the Review Board server logs \(error ID '
            r'[a-z0-9-]+\)\.'
        )

        with self.assertRaisesRegex(CertificateStorageError, message):
            backend.delete_ca_bundle(name='bad-cert')

        # Make sure this does not clear cache.
        self.assertSpyNotCalledWith(backend._invalidate_stats_cache,
                                    local_site=None)

    def test_delete_ca_bundle_by_id(self) -> None:
        """Testing FileCertificateStorageBackend.delete_ca_bundle_by_id"""
        backend = self._create_backend()
        path = os.path.join(backend.storage_path, 'cabundles', 'my-certs.pem')

        self.spy_on(backend._invalidate_stats_cache)

        self._write_file(path, TEST_CERT_BUNDLE_PEM)

        backend.delete_ca_bundle_by_id('my-certs')

        self.assertFalse(os.path.exists(path))

        # Make sure this clears cache.
        self.assertSpyCalledWith(backend._invalidate_stats_cache,
                                 local_site=None)

    def test_delete_ca_bundle_by_id_with_local_site(self) -> None:
        """Testing FileCertificateStorageBackend.delete_ca_bundle_by_id
        with LocalSite
        """
        local_site = self.create_local_site(name='test-site')
        backend = self._create_backend()
        path = os.path.join(backend.storage_path, 'sites', 'test-site',
                            'cabundles', 'my-certs.pem')

        self.spy_on(backend._invalidate_stats_cache)

        self._write_file(path, TEST_CERT_BUNDLE_PEM)

        backend.delete_ca_bundle_by_id('test-site:my-certs')

        self.assertFalse(os.path.exists(path))

        # Make sure this clears cache.
        self.assertSpyCalledWith(backend._invalidate_stats_cache,
                                 local_site=local_site)

    def test_get_stored_ca_bundle(self) -> None:
        """Testing FileCertificateStorageBackend.get_stored_ca_bundle"""
        backend = self._create_backend()
        path = os.path.join(backend.storage_path, 'cabundles', 'my-certs.pem')

        self._write_file(path, TEST_CERT_BUNDLE_PEM)

        stored_bundle = backend.get_stored_ca_bundle(name='my-certs')

        assert stored_bundle is not None
        self.assertAttrsEqual(
            stored_bundle,
            {
                '_bundle_file_path': path,
                '_name': 'my-certs',
                'local_site': None,
                'storage': backend,
                'storage_id': 'my-certs',
            })

    def test_get_stored_ca_bundle_with_local_site(self) -> None:
        """Testing FileCertificateStorageBackend.get_stored_ca_bundle with
        LocalSite
        """
        local_site = self.create_local_site(name='test-site')
        backend = self._create_backend()
        path = os.path.join(backend.storage_path, 'sites', 'test-site',
                            'cabundles', 'my-certs.pem')

        self._write_file(path, TEST_CERT_BUNDLE_PEM)

        stored_bundle = backend.get_stored_ca_bundle(name='my-certs',
                                                     local_site=local_site)

        assert stored_bundle is not None
        self.assertAttrsEqual(
            stored_bundle,
            {
                '_bundle_file_path': path,
                '_name': 'my-certs',
                'local_site': local_site,
                'storage': backend,
                'storage_id': 'test-site:my-certs',
            })

    def test_get_stored_ca_bundle_with_local_site_mismatch(self) -> None:
        """Testing FileCertificateStorageBackend.get_stored_ca_bundle with
        LocalSite mismatch
        """
        local_site1 = self.create_local_site(name='test-site-1')
        local_site2 = self.create_local_site(name='test-site-2')

        backend = self._create_backend()
        path1 = os.path.join(backend.storage_path, 'cabundles',
                             'my-certs1.pem')
        path2 = os.path.join(backend.storage_path, 'sites', 'test-site-1',
                             'cabundles', 'my-certs2.pem')

        self._write_file(path1, TEST_CERT_BUNDLE_PEM)
        self._write_file(path2, TEST_CERT_BUNDLE_PEM)

        self.assertIsNone(backend.get_stored_ca_bundle(name='my-certs1',
                                                       local_site=local_site1))
        self.assertIsNone(backend.get_stored_ca_bundle(name='my-certs2'))
        self.assertIsNone(backend.get_stored_ca_bundle(name='my-certs2',
                                                       local_site=local_site2))

    def test_get_stored_ca_bundle_with_not_found(self) -> None:
        """Testing FileCertificateStorageBackend.get_stored_ca_bundle with
        not found
        """
        backend = self._create_backend()

        self.assertIsNone(backend.get_stored_ca_bundle(name='missing-certs'))

    def test_get_stored_ca_bundle_by_id(self) -> None:
        """Testing FileCertificateStorageBackend.get_stored_ca_bundle_by_id"""
        backend = self._create_backend()
        path = os.path.join(backend.storage_path, 'cabundles', 'my-certs.pem')

        self._write_file(path, TEST_CERT_BUNDLE_PEM)

        stored_bundle = backend.get_stored_ca_bundle_by_id('my-certs')

        assert stored_bundle is not None
        self.assertAttrsEqual(
            stored_bundle,
            {
                '_bundle_file_path': path,
                '_name': 'my-certs',
                'local_site': None,
                'storage': backend,
                'storage_id': 'my-certs',
            })

    def test_get_stored_ca_bundle_by_id_with_local_site(self) -> None:
        """Testing FileCertificateStorageBackend.get_stored_ca_bundle_by_id
        with LocalSite
        """
        local_site = self.create_local_site(name='test-site')
        backend = self._create_backend()

        path = os.path.join(backend.storage_path, 'sites', 'test-site',
                            'cabundles', 'my-certs.pem')
        self._write_file(path, TEST_CERT_BUNDLE_PEM)

        stored_bundle = \
            backend.get_stored_ca_bundle_by_id('test-site:my-certs')

        assert stored_bundle is not None
        self.assertAttrsEqual(
            stored_bundle,
            {
                '_bundle_file_path': path,
                '_name': 'my-certs',
                'local_site': local_site,
                'storage': backend,
                'storage_id': 'test-site:my-certs',
            })

    def test_iter_stored_ca_bundles(self) -> None:
        """Testing FileCertificateStorageBackend.iter_stored_ca_bundles"""
        backend = self._create_backend(storage_path=self.testdata_dir)
        cabundles_dir = os.path.join(backend.storage_path, 'cabundles')

        stored_bundles = list(backend.iter_stored_ca_bundles())
        self.assertEqual(len(stored_bundles), 2)

        self.assertAttrsEqual(
            stored_bundles[0],
            {
                '_bundle_file_path': os.path.join(cabundles_dir, 'comodo.pem'),
                '_name': 'comodo',
                'local_site': None,
                'storage': backend,
                'storage_id': 'comodo',
            })
        self.assertAttrsEqual(
            stored_bundles[1],
            {
                '_bundle_file_path': os.path.join(cabundles_dir,
                                                  'globalsign.pem'),
                '_name': 'globalsign',
                'local_site': None,
                'storage': backend,
                'storage_id': 'globalsign',
            })

    def test_iter_stored_ca_bundles_with_local_site(self) -> None:
        """Testing FileCertificateStorageBackend.iter_stored_ca_bundles with
        LocalSite
        """
        local_site = self.create_local_site(name='test-site-2')
        backend = self._create_backend(storage_path=self.testdata_dir)
        cabundles_dir = os.path.join(backend.storage_path, 'sites',
                                     'test-site-2', 'cabundles')

        stored_bundles = list(backend.iter_stored_ca_bundles(
            local_site=local_site))
        self.assertEqual(len(stored_bundles), 1)

        self.assertAttrsEqual(
            stored_bundles[0],
            {
                '_bundle_file_path': os.path.join(cabundles_dir,
                                                  'amazon.pem'),
                '_name': 'amazon',
                'local_site': local_site,
                'storage': backend,
                'storage_id': 'test-site-2:amazon',
            })

    def test_iter_stored_ca_bundles_with_local_site_all(self) -> None:
        """Testing FileCertificateStorageBackend.iter_stored_ca_bundles with
        LocalSite.ALL
        """
        local_site1 = self.create_local_site(name='test-site-1')
        local_site2 = self.create_local_site(name='test-site-2')
        self.create_local_site(name='test-site-3')

        backend = self._create_backend(storage_path=self.testdata_dir)
        global_cabundles_dir = os.path.join(backend.storage_path, 'cabundles')
        site1_cabundles_dir = os.path.join(backend.storage_path, 'sites',
                                           'test-site-1', 'cabundles')
        site2_cabundles_dir = os.path.join(backend.storage_path, 'sites',
                                           'test-site-2', 'cabundles')

        stored_bundles = list(backend.iter_stored_ca_bundles(
            local_site=LocalSite.ALL))
        self.assertEqual(len(stored_bundles), 5)

        self.assertAttrsEqual(
            stored_bundles[0],
            {
                '_bundle_file_path': os.path.join(global_cabundles_dir,
                                                  'comodo.pem'),
                '_name': 'comodo',
                'local_site': None,
                'storage': backend,
                'storage_id': 'comodo',
            })
        self.assertAttrsEqual(
            stored_bundles[1],
            {
                '_bundle_file_path': os.path.join(global_cabundles_dir,
                                                  'globalsign.pem'),
                '_name': 'globalsign',
                'local_site': None,
                'storage': backend,
                'storage_id': 'globalsign',
            })
        self.assertAttrsEqual(
            stored_bundles[2],
            {
                '_bundle_file_path': os.path.join(site1_cabundles_dir,
                                                  'amazon.pem'),
                '_name': 'amazon',
                'local_site': local_site1,
                'storage': backend,
                'storage_id': 'test-site-1:amazon',
            })
        self.assertAttrsEqual(
            stored_bundles[3],
            {
                '_bundle_file_path': os.path.join(site1_cabundles_dir,
                                                  'globalsign.pem'),
                '_name': 'globalsign',
                'local_site': local_site1,
                'storage': backend,
                'storage_id': 'test-site-1:globalsign',
            })
        self.assertAttrsEqual(
            stored_bundles[4],
            {
                '_bundle_file_path': os.path.join(site2_cabundles_dir,
                                                  'amazon.pem'),
                '_name': 'amazon',
                'local_site': local_site2,
                'storage': backend,
                'storage_id': 'test-site-2:amazon',
            })

    def test_iter_stored_ca_bundles_with_none(self) -> None:
        """Testing FileCertificateStorageBackend.iter_stored_ca_bundles with
        no bundles
        """
        local_site = self.create_local_site(name='test-site-4')
        backend = self._create_backend(storage_path=self.testdata_dir)

        stored_bundles = list(backend.iter_stored_ca_bundles(
            local_site=local_site))
        self.assertEqual(len(stored_bundles), 0)

    def test_add_certificate(self) -> None:
        """Testing FileCertificateStorageBackend.add_certificate"""
        backend = self._create_backend()

        self.spy_on(backend._invalidate_stats_cache)

        stored_cert = backend.add_certificate(
            Certificate(cert_data=TEST_CERT_PEM,
                        hostname='example.com',
                        port=443))
        cert_path = os.path.join(backend.storage_path, 'certs',
                                 'example.com__443.crt')

        self.assertIsNotNone(stored_cert)
        self.assertAttrsEqual(
            stored_cert,
            {
                '_hostname': 'example.com',
                '_port': 443,
                'local_site': None,
                'storage': backend,
                'storage_id': 'example.com:443',
            })
        self.assertEqual(stored_cert.get_cert_file_path(), cert_path)
        self.assertIsNone(stored_cert.get_key_file_path())
        self.assertTrue(os.path.exists(cert_path))
        self.assertAttrsEqual(
            stored_cert.certificate,
            {
                'cert_data': TEST_CERT_PEM,
                'hostname': 'example.com',
                'key_data': None,
                'port': 443,
            })

        with open(cert_path, 'rb') as fp:
            self.assertEqual(fp.read(), TEST_CERT_PEM)

        # Make sure this clears cache.
        self.assertSpyCalledWith(backend._invalidate_stats_cache,
                                 local_site=None)

    def test_add_certificate_with_key(self) -> None:
        """Testing FileCertificateStorageBackend.add_certificate with key"""
        backend = self._create_backend()

        self.spy_on(backend._invalidate_stats_cache)

        stored_cert = backend.add_certificate(
            Certificate(cert_data=TEST_CERT_PEM,
                        key_data=TEST_KEY_PEM,
                        hostname='example.com',
                        port=443))
        cert_path = os.path.join(backend.storage_path, 'certs',
                                 'example.com__443.crt')
        key_path = os.path.join(backend.storage_path, 'certs',
                                'example.com__443.key')

        self.assertIsNotNone(stored_cert)
        self.assertAttrsEqual(
            stored_cert,
            {
                '_hostname': 'example.com',
                '_port': 443,
                'local_site': None,
                'storage': backend,
                'storage_id': 'example.com:443',
            })
        self.assertTrue(os.path.exists(cert_path))
        self.assertTrue(os.path.exists(key_path))
        self.assertAttrsEqual(
            stored_cert.certificate,
            {
                'cert_data': TEST_CERT_PEM,
                'hostname': 'example.com',
                'key_data': TEST_KEY_PEM,
                'port': 443,
            })

        with open(cert_path, 'rb') as fp:
            self.assertEqual(fp.read(), TEST_CERT_PEM)

        with open(key_path, 'rb') as fp:
            self.assertEqual(fp.read(), TEST_KEY_PEM)

        # Make sure this clears cache.
        self.assertSpyCalledWith(backend._invalidate_stats_cache,
                                 local_site=None)

    def test_add_certificate_with_erase_key(self) -> None:
        """Testing FileCertificateStorageBackend.add_certificate with erasing
        key from previous upload
        """
        backend = self._create_backend()
        cert_path = os.path.join(backend.storage_path, 'certs',
                                 'example.com__443.crt')
        key_path = os.path.join(backend.storage_path, 'certs',
                                'example.com__443.key')

        self.spy_on(backend._invalidate_stats_cache)

        self._write_file(cert_path, TEST_CERT_PEM)
        self._write_file(key_path, TEST_KEY_PEM)

        stored_cert = backend.add_certificate(
            Certificate(cert_data=TEST_CERT_PEM,
                        hostname='example.com',
                        port=443))

        self.assertIsNotNone(stored_cert)
        self.assertAttrsEqual(
            stored_cert,
            {
                '_hostname': 'example.com',
                '_port': 443,
                'local_site': None,
                'storage': backend,
                'storage_id': 'example.com:443',
            })
        self.assertEqual(stored_cert.get_cert_file_path(), cert_path)
        self.assertIsNone(stored_cert.get_key_file_path())
        self.assertTrue(os.path.exists(cert_path))
        self.assertFalse(os.path.exists(key_path))
        self.assertAttrsEqual(
            stored_cert.certificate,
            {
                'cert_data': TEST_CERT_PEM,
                'hostname': 'example.com',
                'key_data': None,
                'port': 443,
            })

        with open(cert_path, 'rb') as fp:
            self.assertEqual(fp.read(), TEST_CERT_PEM)

        # Make sure this clears cache.
        self.assertSpyCalledWith(backend._invalidate_stats_cache,
                                 local_site=None)

    def test_add_certificate_with_local_site(self) -> None:
        """Testing FileCertificateStorageBackend.add_certificate with
        LocalSite
        """
        local_site = self.create_local_site(name='test-site')
        backend = self._create_backend()

        self.spy_on(backend._invalidate_stats_cache)

        stored_cert = backend.add_certificate(
            Certificate(cert_data=TEST_CERT_PEM,
                        key_data=TEST_KEY_PEM,
                        hostname='example.com',
                        port=443),
            local_site=local_site)
        cert_path = os.path.join(backend.storage_path, 'sites', 'test-site',
                                 'certs', 'example.com__443.crt')
        key_path = os.path.join(backend.storage_path, 'sites', 'test-site',
                                'certs', 'example.com__443.key')

        self.assertIsNotNone(stored_cert)
        self.assertAttrsEqual(
            stored_cert,
            {
                '_hostname': 'example.com',
                '_port': 443,
                'local_site': local_site,
                'storage': backend,
                'storage_id': 'test-site:example.com:443',
            })
        self.assertEqual(stored_cert.get_cert_file_path(), cert_path)
        self.assertEqual(stored_cert.get_key_file_path(), key_path)
        self.assertTrue(os.path.exists(cert_path))
        self.assertTrue(os.path.exists(key_path))
        self.assertAttrsEqual(
            stored_cert.certificate,
            {
                'cert_data': TEST_CERT_PEM,
                'hostname': 'example.com',
                'key_data': TEST_KEY_PEM,
                'port': 443,
            })

        with open(cert_path, 'rb') as fp:
            self.assertEqual(fp.read(), TEST_CERT_PEM)

        with open(key_path, 'rb') as fp:
            self.assertEqual(fp.read(), TEST_KEY_PEM)

        # Make sure this clears cache.
        self.assertSpyCalledWith(backend._invalidate_stats_cache,
                                 local_site=local_site)

    def test_add_certificate_with_ioerror_cert(self) -> None:
        """Testing FileCertificateStorageBackend.add_certificate with IOError
        writing cert
        """
        backend = self._create_backend()
        cert_path = os.path.join(backend.storage_path, 'bad-dir',
                                 'example.com__443.crt')

        self.spy_on(backend._invalidate_stats_cache)
        self.spy_on(backend._build_cert_file_path,
                    op=kgb.SpyOpReturn(cert_path))

        message = (
            r'Error writing SSL/TLS certificate file\. Administrators can '
            r'find details in the Review Board server logs \(error ID '
            r'[a-z0-9-]+\)\.'
        )

        with self.assertRaisesRegex(CertificateStorageError, message):
            backend.add_certificate(
                Certificate(cert_data=TEST_CERT_PEM,
                            hostname='example.com',
                            port=443))

        # Make sure this does not clear cache.
        self.assertSpyNotCalled(backend._invalidate_stats_cache)

    def test_add_certificate_with_ioerror_key(self) -> None:
        """Testing FileCertificateStorageBackend.add_certificate with IOError
        writing key
        """
        backend = self._create_backend()
        cert_path = os.path.join(backend.storage_path, 'example.com__443.crt')
        key_path = os.path.join(backend.storage_path, 'bad-dir',
                                'example.com__443.key')

        self.spy_on(backend._invalidate_stats_cache)
        self.spy_on(backend._build_cert_file_path,
                    op=kgb.SpyOpReturnInOrder([cert_path, key_path]))

        message = (
            r'Error writing SSL/TLS private key file\. Administrators can '
            r'find details in the Review Board server logs \(error ID '
            r'[a-z0-9-]+\)\.'
        )

        with self.assertRaisesRegex(CertificateStorageError, message):
            backend.add_certificate(
                Certificate(cert_data=TEST_CERT_PEM,
                            key_data=TEST_KEY_PEM,
                            hostname='example.com',
                            port=443))

        # Make sure this does not clear cache.
        self.assertSpyNotCalled(backend._invalidate_stats_cache)

    def test_delete_certificate(self) -> None:
        """Testing FileCertificateStorageBackend.delete_certificate"""
        backend = self._create_backend()

        self.spy_on(backend._invalidate_stats_cache)

        cert_path = os.path.join(backend.storage_path, 'certs',
                                 'example.com__443.crt')
        self._write_file(cert_path, TEST_CERT_PEM)

        backend.delete_certificate(hostname='example.com',
                                   port=443)

        self.assertFalse(os.path.exists(cert_path))

        # Make sure this clears cache.
        self.assertSpyCalledWith(backend._invalidate_stats_cache,
                                 local_site=None)

    def test_delete_certificate_with_key(self) -> None:
        """Testing FileCertificateStorageBackend.delete_certificate with key
        """
        backend = self._create_backend()

        self.spy_on(backend._invalidate_stats_cache)

        cert_path = os.path.join(backend.storage_path, 'certs',
                                 'example.com__443.crt')
        key_path = os.path.join(backend.storage_path, 'certs',
                                'example.com__443.key')
        self._write_file(cert_path, TEST_CERT_PEM)
        self._write_file(key_path, TEST_KEY_PEM)

        backend.delete_certificate(hostname='example.com',
                                   port=443)

        self.assertFalse(os.path.exists(cert_path))
        self.assertFalse(os.path.exists(key_path))

        # Make sure this clears cache.
        self.assertSpyCalledWith(backend._invalidate_stats_cache,
                                 local_site=None)

    def test_delete_certificate_with_local_site(self) -> None:
        """Testing FileCertificateStorageBackend.delete_certificate with
        LocalSite
        """
        local_site = self.create_local_site(name='test-site')
        backend = self._create_backend()

        self.spy_on(backend._invalidate_stats_cache)

        cert_path = os.path.join(backend.storage_path, 'sites', 'test-site',
                                 'certs', 'example.com__443.crt')
        key_path = os.path.join(backend.storage_path, 'sites', 'test-site',
                                'certs', 'example.com__443.key')
        self._write_file(cert_path, TEST_CERT_PEM)
        self._write_file(key_path, TEST_KEY_PEM)

        backend.delete_certificate(hostname='example.com',
                                   port=443,
                                   local_site=local_site)

        self.assertFalse(os.path.exists(cert_path))
        self.assertFalse(os.path.exists(key_path))

        # Make sure this clears cache.
        self.assertSpyCalledWith(backend._invalidate_stats_cache,
                                 local_site=local_site)

    def test_delete_certificate_with_not_found(self) -> None:
        """Testing FileCertificateStorageBackend.delete_certificate with
        not found
        """
        backend = self._create_backend()

        self.spy_on(backend._invalidate_stats_cache)

        with self.assertRaises(CertificateNotFoundError):
            backend.delete_certificate(hostname='example.com',
                                       port=443)

        # Make sure this does not clear cache.
        self.assertSpyNotCalled(backend._invalidate_stats_cache)

    def test_delete_certificate_with_ioerror_cert(self) -> None:
        """Testing FileCertificateStorageBackend.delete_certificate with
        IOError deleting cert
        """
        backend = self._create_backend()

        self.spy_on(backend._invalidate_stats_cache)
        self.spy_on(backend._build_cert_file_path,
                    op=kgb.SpyOpReturn(os.path.join(backend.storage_path,
                                                    'certs', 'missing.crt')))

        message = (
            r'Error deleting SSL/TLS certificate\. Administrators can find '
            r'details in the Review Board server logs \(error ID '
            r'[a-z0-9-]+\)\.'
        )

        with self.assertRaisesRegex(CertificateStorageError, message):
            backend.delete_certificate(hostname='example.com',
                                       port=443)

        # Make sure this does not clear cache.
        self.assertSpyNotCalled(backend._invalidate_stats_cache)

    def test_delete_certificate_with_ioerror_key(self) -> None:
        """Testing FileCertificateStorageBackend.delete_certificate with
        IOError deleting key
        """
        backend = self._create_backend()

        cert_path = os.path.join(backend.storage_path, 'certs',
                                 'example.com__443.crt')
        key_path = os.path.join(backend.storage_path, 'certs', 'missing.key')

        self._write_file(cert_path, TEST_CERT_PEM)

        self.spy_on(backend._invalidate_stats_cache)
        self.spy_on(
            backend._build_cert_file_path,
            op=kgb.SpyOpReturnInOrder([cert_path, key_path]))

        message = (
            r'Error deleting SSL/TLS private key\. Administrators can find '
            r'details in the Review Board server logs \(error ID '
            r'[a-z0-9-]+\)\.'
        )

        with self.assertRaisesRegex(CertificateStorageError, message):
            backend.delete_certificate(hostname='example.com',
                                       port=443)

        self.assertFalse(os.path.exists(cert_path))

        # Make sure this does not clear cache.
        self.assertSpyNotCalled(backend._invalidate_stats_cache)

    def test_delete_certificate_by_id(self) -> None:
        """Testing FileCertificateStorageBackend.delete_certificate_by_id"""
        backend = self._create_backend()

        self.spy_on(backend._invalidate_stats_cache)

        cert_path = os.path.join(backend.storage_path, 'certs',
                                 'example.com__443.crt')
        self._write_file(cert_path, TEST_CERT_PEM)

        backend.delete_certificate_by_id('example.com:443')

        self.assertFalse(os.path.exists(cert_path))

        # Make sure this clears cache.
        self.assertSpyCalledWith(backend._invalidate_stats_cache,
                                 local_site=None)

    def test_delete_certificate_by_id_with_local_site(self) -> None:
        """Testing FileCertificateStorageBackend.delete_certificate_by_id with
        LocalSite
        """
        local_site = self.create_local_site(name='test-site')
        backend = self._create_backend()

        self.spy_on(backend._invalidate_stats_cache)

        cert_path = os.path.join(backend.storage_path, 'sites', 'test-site',
                                 'certs', 'example.com__443.crt')
        key_path = os.path.join(backend.storage_path, 'sites', 'test-site',
                                'certs', 'example.com__443.key')
        self._write_file(cert_path, TEST_CERT_PEM)
        self._write_file(key_path, TEST_KEY_PEM)

        backend.delete_certificate_by_id('test-site:example.com:443')

        self.assertFalse(os.path.exists(cert_path))
        self.assertFalse(os.path.exists(key_path))

        # Make sure this clears cache.
        self.assertSpyCalledWith(backend._invalidate_stats_cache,
                                 local_site=local_site)

    def test_get_stored_certificate(self) -> None:
        """Testing FileCertificateStorageBackend.get_stored_certificate"""
        backend = self._create_backend()

        cert_path = os.path.join(backend.storage_path, 'certs',
                                 'example.com__443.crt')
        self._write_file(cert_path, TEST_CERT_PEM)

        stored_cert = backend.get_stored_certificate(hostname='example.com',
                                                     port=443)

        assert stored_cert is not None
        self.assertAttrsEqual(
            stored_cert,
            {
                '_hostname': 'example.com',
                '_port': 443,
                'local_site': None,
                'storage': backend,
                'storage_id': 'example.com:443',
            })
        self.assertEqual(stored_cert.get_cert_file_path(), cert_path)
        self.assertIsNone(stored_cert.get_key_file_path())
        self.assertAttrsEqual(
            stored_cert.certificate,
            {
                'cert_data': TEST_CERT_PEM,
                'hostname': 'example.com',
                'key_data': None,
                'port': 443,
            })

    def test_get_stored_certificate_with_key(self) -> None:
        """Testing FileCertificateStorageBackend.get_stored_certificate with
        key
        """
        backend = self._create_backend()

        cert_path = os.path.join(backend.storage_path, 'certs',
                                 'example.com__443.crt')
        key_path = os.path.join(backend.storage_path, 'certs',
                                'example.com__443.key')
        self._write_file(cert_path, TEST_CERT_PEM)
        self._write_file(key_path, TEST_KEY_PEM)

        stored_cert = backend.get_stored_certificate(hostname='example.com',
                                                     port=443)

        assert stored_cert is not None
        self.assertAttrsEqual(
            stored_cert,
            {
                '_hostname': 'example.com',
                '_port': 443,
                'local_site': None,
                'storage': backend,
                'storage_id': 'example.com:443',
            })
        self.assertEqual(stored_cert.get_cert_file_path(), cert_path)
        self.assertEqual(stored_cert.get_key_file_path(), key_path)
        self.assertAttrsEqual(
            stored_cert.certificate,
            {
                'cert_data': TEST_CERT_PEM,
                'hostname': 'example.com',
                'key_data': TEST_KEY_PEM,
                'port': 443,
            })

    def test_get_stored_certificate_with_local_site(self) -> None:
        """Testing FileCertificateStorageBackend.get_stored_certificate with
        LocalSite
        """
        local_site = self.create_local_site(name='test-site')
        backend = self._create_backend()

        cert_path = os.path.join(backend.storage_path, 'sites', 'test-site',
                                 'certs', 'example.com__443.crt')
        key_path = os.path.join(backend.storage_path, 'sites', 'test-site',
                                'certs', 'example.com__443.key')
        self._write_file(cert_path, TEST_CERT_PEM)
        self._write_file(key_path, TEST_KEY_PEM)

        stored_cert = backend.get_stored_certificate(hostname='example.com',
                                                     port=443,
                                                     local_site=local_site)

        assert stored_cert is not None
        self.assertAttrsEqual(
            stored_cert,
            {
                '_hostname': 'example.com',
                '_port': 443,
                'local_site': local_site,
                'storage': backend,
                'storage_id': 'test-site:example.com:443',
            })
        self.assertEqual(stored_cert.get_cert_file_path(), cert_path)
        self.assertEqual(stored_cert.get_key_file_path(), key_path)
        self.assertAttrsEqual(
            stored_cert.certificate,
            {
                'cert_data': TEST_CERT_PEM,
                'hostname': 'example.com',
                'key_data': TEST_KEY_PEM,
                'port': 443,
            })

    def test_get_stored_certificate_with_wildcard_cert(self) -> None:
        """Testing FileCertificateStorageBackend.get_stored_certificate with
        wildcard cert
        """
        backend = self._create_backend(storage_path=self.testdata_dir)
        certs_dir = os.path.join(backend.storage_path, 'certs')

        stored_cert = backend.get_stored_certificate(
            hostname='*.eng.example.com',
            port=443)

        assert stored_cert is not None
        self.assertAttrsEqual(
            stored_cert,
            {
                '_hostname': '*.eng.example.com',
                '_port': 443,
                'local_site': None,
                'storage': backend,
                'storage_id': '*.eng.example.com:443',
            })
        self.assertEqual(stored_cert.get_cert_file_path(),
                         os.path.join(certs_dir,
                                      '__.eng.example.com__443.crt'))
        self.assertEqual(stored_cert.get_key_file_path(),
                         os.path.join(certs_dir,
                                      '__.eng.example.com__443.key'))

        self.assertAttrsEqual(
            stored_cert.certificate,
            {
                'hostname': '*.eng.example.com',
                'port': 443,
            })

    def test_get_stored_certificate_with_wildcard_cert_fallback(self) -> None:
        """Testing FileCertificateStorageBackend.get_stored_certificate with
        wildcard cert as fallback
        """
        backend = self._create_backend(storage_path=self.testdata_dir)
        certs_dir = os.path.join(backend.storage_path, 'certs')

        stored_cert = backend.get_stored_certificate(
            hostname='test.eng.example.com',
            port=443)

        assert stored_cert is not None
        self.assertAttrsEqual(
            stored_cert,
            {
                '_hostname': 'test.eng.example.com',
                '_port': 443,
                'local_site': None,
                'storage': backend,
                'storage_id': '*.eng.example.com:443',
            })
        self.assertEqual(stored_cert.get_cert_file_path(),
                         os.path.join(certs_dir,
                                      '__.eng.example.com__443.crt'))
        self.assertEqual(stored_cert.get_key_file_path(),
                         os.path.join(certs_dir,
                                      '__.eng.example.com__443.key'))

        self.assertAttrsEqual(
            stored_cert.certificate,
            {
                'hostname': 'test.eng.example.com',
                'port': 443,
            })

    def test_get_stored_certificate_with_specific_and_wildcard_cert(
        self,
    ) -> None:
        """Testing FileCertificateStorageBackend.get_stored_certificate with
        specific cert taking precedence over wildcard cert
        """
        backend = self._create_backend(storage_path=self.testdata_dir)
        certs_dir = os.path.join(backend.storage_path, 'certs')

        stored_cert = backend.get_stored_certificate(
            hostname='reviewboard.eng.example.com',
            port=443)

        assert stored_cert is not None
        self.assertAttrsEqual(
            stored_cert,
            {
                '_hostname': 'reviewboard.eng.example.com',
                '_port': 443,
                'local_site': None,
                'storage': backend,
                'storage_id': 'reviewboard.eng.example.com:443',
            })
        self.assertEqual(stored_cert.get_cert_file_path(),
                         os.path.join(certs_dir,
                                      'reviewboard.eng.example.com__443.crt'))
        self.assertEqual(stored_cert.get_key_file_path(),
                         os.path.join(certs_dir,
                                      'reviewboard.eng.example.com__443.key'))

        self.assertAttrsEqual(
            stored_cert.certificate,
            {
                'hostname': 'reviewboard.eng.example.com',
                'port': 443,
            })

    def test_get_stored_certificate_with_not_found(self) -> None:
        """Testing FileCertificateStorageBackend.get_stored_certificate with
        not found
        """
        backend = self._create_backend()

        self.assertIsNone(backend.get_stored_certificate(
            hostname='example.com',
            port=443))

    def test_get_stored_certificate_by_id(self) -> None:
        """Testing FileCertificateStorageBackend.get_stored_certificate_by_id
        """
        backend = self._create_backend()

        cert_path = os.path.join(backend.storage_path, 'certs',
                                 'example.com__443.crt')
        key_path = os.path.join(backend.storage_path, 'certs',
                                'example.com__443.key')
        self._write_file(cert_path, TEST_CERT_PEM)
        self._write_file(key_path, TEST_KEY_PEM)

        stored_cert = backend.get_stored_certificate_by_id('example.com:443')

        assert stored_cert is not None
        self.assertAttrsEqual(
            stored_cert,
            {
                '_hostname': 'example.com',
                '_port': 443,
                'local_site': None,
                'storage': backend,
                'storage_id': 'example.com:443',
            })
        self.assertEqual(stored_cert.get_cert_file_path(), cert_path)
        self.assertEqual(stored_cert.get_key_file_path(), key_path)
        self.assertAttrsEqual(
            stored_cert.certificate,
            {
                'cert_data': TEST_CERT_PEM,
                'hostname': 'example.com',
                'key_data': TEST_KEY_PEM,
                'port': 443,
            })

    def test_get_stored_certificate_by_id_with_wildcard(self) -> None:
        """Testing FileCertificateStorageBackend.get_stored_certificate_by_id
        with wildcard certificate
        """
        backend = self._create_backend(storage_path=self.testdata_dir)
        certs_dir = os.path.join(backend.storage_path, 'certs')

        stored_cert = backend.get_stored_certificate_by_id(
            '*.eng.example.com:443')

        assert stored_cert is not None
        self.assertAttrsEqual(
            stored_cert,
            {
                '_hostname': '*.eng.example.com',
                '_port': 443,
                'local_site': None,
                'storage': backend,
                'storage_id': '*.eng.example.com:443',
            })
        self.assertEqual(stored_cert.get_cert_file_path(),
                         os.path.join(certs_dir,
                                      '__.eng.example.com__443.crt'))
        self.assertEqual(stored_cert.get_key_file_path(),
                         os.path.join(certs_dir,
                                      '__.eng.example.com__443.key'))

        self.assertAttrsEqual(
            stored_cert.certificate,
            {
                'hostname': '*.eng.example.com',
                'port': 443,
            })

    def test_get_stored_certificate_by_id_with_local_site(self) -> None:
        """Testing FileCertificateStorageBackend.get_stored_certificate_by_id
        with LocalSite
        """
        local_site = self.create_local_site(name='test-site')
        backend = self._create_backend()

        cert_path = os.path.join(backend.storage_path, 'sites', 'test-site',
                                 'certs', 'example.com__443.crt')
        key_path = os.path.join(backend.storage_path, 'sites', 'test-site',
                                'certs', 'example.com__443.key')
        self._write_file(cert_path, TEST_CERT_PEM)
        self._write_file(key_path, TEST_KEY_PEM)

        stored_cert = backend.get_stored_certificate_by_id(
            'test-site:example.com:443',
            local_site=local_site)

        assert stored_cert is not None
        self.assertAttrsEqual(
            stored_cert,
            {
                '_hostname': 'example.com',
                '_port': 443,
                'local_site': local_site,
                'storage': backend,
                'storage_id': 'test-site:example.com:443',
            })
        self.assertEqual(stored_cert.get_cert_file_path(), cert_path)
        self.assertEqual(stored_cert.get_key_file_path(), key_path)
        self.assertAttrsEqual(
            stored_cert.certificate,
            {
                'cert_data': TEST_CERT_PEM,
                'hostname': 'example.com',
                'key_data': TEST_KEY_PEM,
                'port': 443,
            })

    def test_iter_stored_certificates(self) -> None:
        """Testing FileCertificateStorageBackend.iter_stored_certificates"""
        backend = self._create_backend(storage_path=self.testdata_dir)
        certs_dir = os.path.join(backend.storage_path, 'certs')

        stored_certs = list(backend.iter_stored_certificates())
        self.assertEqual(len(stored_certs), 4)

        stored_cert = stored_certs[0]
        self.assertAttrsEqual(
            stored_cert,
            {
                '_hostname': '*.eng.example.com',
                '_port': 443,
                'local_site': None,
                'storage': backend,
                'storage_id': '*.eng.example.com:443',
            })
        self.assertEqual(stored_cert.get_cert_file_path(),
                         os.path.join(certs_dir,
                                      '__.eng.example.com__443.crt'))
        self.assertEqual(stored_cert.get_key_file_path(),
                         os.path.join(certs_dir,
                                      '__.eng.example.com__443.key'))

        stored_cert = stored_certs[1]
        self.assertAttrsEqual(
            stored_cert,
            {
                '_hostname': 'ldap.example.com',
                '_port': 636,
                'local_site': None,
                'storage': backend,
                'storage_id': 'ldap.example.com:636',
            })
        self.assertEqual(stored_cert.get_cert_file_path(),
                         os.path.join(certs_dir, 'ldap.example.com__636.crt'))
        self.assertEqual(stored_cert.get_key_file_path(),
                         os.path.join(certs_dir, 'ldap.example.com__636.key'))

        stored_cert = stored_certs[2]
        self.assertAttrsEqual(
            stored_cert,
            {
                '_hostname': 'reviewboard.eng.example.com',
                '_port': 443,
                'local_site': None,
                'storage': backend,
                'storage_id': 'reviewboard.eng.example.com:443',
            })
        self.assertEqual(stored_cert.get_cert_file_path(),
                         os.path.join(certs_dir,
                                      'reviewboard.eng.example.com__443.crt'))
        self.assertEqual(stored_cert.get_key_file_path(),
                         os.path.join(certs_dir,
                                      'reviewboard.eng.example.com__443.key'))

        stored_cert = stored_certs[3]
        self.assertAttrsEqual(
            stored_cert,
            {
                '_hostname': 'www.example.com',
                '_port': 443,
                'local_site': None,
                'storage': backend,
                'storage_id': 'www.example.com:443',
            })
        self.assertEqual(stored_cert.get_cert_file_path(),
                         os.path.join(certs_dir, 'www.example.com__443.crt'))
        self.assertIsNone(stored_cert.get_key_file_path())

    def test_iter_stored_certificates_with_local_site(self) -> None:
        """Testing FileCertificateStorageBackend.iter_stored_certificates
        with LocalSite
        """
        local_site = self.create_local_site(name='test-site-2')
        backend = self._create_backend(storage_path=self.testdata_dir)
        certs_dir = os.path.join(backend.storage_path, 'sites', 'test-site-2',
                                 'certs')

        stored_certs = list(backend.iter_stored_certificates(
            local_site=local_site))
        self.assertEqual(len(stored_certs), 3)

        stored_cert = stored_certs[0]
        self.assertAttrsEqual(
            stored_cert,
            {
                '_hostname': '*.eng.example.com',
                '_port': 443,
                'local_site': local_site,
                'storage': backend,
                'storage_id': 'test-site-2:*.eng.example.com:443',
            })
        self.assertEqual(stored_cert.get_cert_file_path(),
                         os.path.join(backend.storage_path, 'sites',
                                      'test-site-2', 'certs',
                                      '__.eng.example.com__443.crt'))
        self.assertEqual(stored_cert.get_key_file_path(),
                         os.path.join(backend.storage_path, 'sites',
                                      'test-site-2', 'certs',
                                      '__.eng.example.com__443.key'))

        stored_cert = stored_certs[1]
        self.assertAttrsEqual(
            stored_cert,
            {
                '_hostname': 'svn.example.com',
                '_port': 8443,
                'local_site': local_site,
                'storage': backend,
                'storage_id': 'test-site-2:svn.example.com:8443',
            })
        self.assertEqual(stored_cert.get_cert_file_path(),
                         os.path.join(backend.storage_path, 'sites',
                                      'test-site-2', 'certs',
                                      'svn.example.com__8443.crt'))
        self.assertEqual(stored_cert.get_key_file_path(),
                         os.path.join(backend.storage_path, 'sites',
                                      'test-site-2', 'certs',
                                      'svn.example.com__8443.key'))

        stored_cert = stored_certs[2]
        self.assertAttrsEqual(
            stored_cert,
            {
                '_hostname': 'tools.corp.example.com',
                '_port': 443,
                'local_site': local_site,
                'storage': backend,
                'storage_id': 'test-site-2:tools.corp.example.com:443',
            })
        self.assertEqual(stored_cert.get_cert_file_path(),
                         os.path.join(certs_dir,
                                      'tools.corp.example.com__443.crt'))
        self.assertEqual(stored_cert.get_key_file_path(),
                         os.path.join(certs_dir,
                                      'tools.corp.example.com__443.key'))

    def test_iter_stored_certificates_with_local_site_all(self) -> None:
        """Testing FileCertificateStorageBackend.iter_stored_certificates
        with LocalSite.ALL
        """
        local_site1 = self.create_local_site(name='test-site-1')
        local_site2 = self.create_local_site(name='test-site-2')
        self.create_local_site(name='test-site-3')
        self.create_local_site(name='test-site-4')

        backend = self._create_backend(storage_path=self.testdata_dir)
        global_certs_dir = os.path.join(backend.storage_path, 'certs')
        site1_certs_dir = os.path.join(backend.storage_path, 'sites',
                                       'test-site-1', 'certs')
        site2_certs_dir = os.path.join(backend.storage_path, 'sites',
                                       'test-site-2', 'certs')

        stored_certs = list(backend.iter_stored_certificates(
            local_site=LocalSite.ALL))
        self.assertEqual(len(stored_certs), 8)

        stored_cert = stored_certs[0]
        self.assertAttrsEqual(
            stored_cert,
            {
                '_hostname': '*.eng.example.com',
                '_port': 443,
                'local_site': None,
                'storage': backend,
                'storage_id': '*.eng.example.com:443',
            })
        self.assertEqual(stored_cert.get_cert_file_path(),
                         os.path.join(global_certs_dir,
                                      '__.eng.example.com__443.crt'))
        self.assertEqual(stored_cert.get_key_file_path(),
                         os.path.join(global_certs_dir,
                                      '__.eng.example.com__443.key'))

        stored_cert = stored_certs[1]
        self.assertAttrsEqual(
            stored_cert,
            {
                '_hostname': 'ldap.example.com',
                '_port': 636,
                'local_site': None,
                'storage': backend,
                'storage_id': 'ldap.example.com:636',
            })
        self.assertEqual(stored_cert.get_cert_file_path(),
                         os.path.join(global_certs_dir,
                                      'ldap.example.com__636.crt'))
        self.assertEqual(stored_cert.get_key_file_path(),
                         os.path.join(global_certs_dir,
                                      'ldap.example.com__636.key'))

        stored_cert = stored_certs[2]
        self.assertAttrsEqual(
            stored_cert,
            {
                '_hostname': 'reviewboard.eng.example.com',
                '_port': 443,
                'local_site': None,
                'storage': backend,
                'storage_id': 'reviewboard.eng.example.com:443',
            })
        self.assertEqual(stored_cert.get_cert_file_path(),
                         os.path.join(global_certs_dir,
                                      'reviewboard.eng.example.com__443.crt'))
        self.assertEqual(stored_cert.get_key_file_path(),
                         os.path.join(global_certs_dir,
                                      'reviewboard.eng.example.com__443.key'))

        stored_cert = stored_certs[3]
        self.assertAttrsEqual(
            stored_cert,
            {
                '_hostname': 'www.example.com',
                '_port': 443,
                'local_site': None,
                'storage': backend,
                'storage_id': 'www.example.com:443',
            })
        self.assertEqual(stored_cert.get_cert_file_path(),
                         os.path.join(global_certs_dir,
                                      'www.example.com__443.crt'))
        self.assertIsNone(stored_cert.get_key_file_path())

        stored_cert = stored_certs[4]
        self.assertAttrsEqual(
            stored_cert,
            {
                '_hostname': 'p4.example.com',
                '_port': 1667,
                'local_site': local_site1,
                'storage': backend,
                'storage_id': 'test-site-1:p4.example.com:1667',
            })
        self.assertEqual(stored_cert.get_cert_file_path(),
                         os.path.join(site1_certs_dir,
                                      'p4.example.com__1667.crt'))
        self.assertIsNone(stored_cert.get_key_file_path())

        stored_cert = stored_certs[5]
        self.assertAttrsEqual(
            stored_cert,
            {
                '_hostname': '*.eng.example.com',
                '_port': 443,
                'local_site': local_site2,
                'storage': backend,
                'storage_id': 'test-site-2:*.eng.example.com:443',
            })
        self.assertEqual(stored_cert.get_cert_file_path(),
                         os.path.join(site2_certs_dir,
                                      '__.eng.example.com__443.crt'))
        self.assertEqual(stored_cert.get_key_file_path(),
                         os.path.join(site2_certs_dir,
                                      '__.eng.example.com__443.key'))

        stored_cert = stored_certs[6]
        self.assertAttrsEqual(
            stored_cert,
            {
                '_hostname': 'svn.example.com',
                '_port': 8443,
                'local_site': local_site2,
                'storage': backend,
                'storage_id': 'test-site-2:svn.example.com:8443',
            })
        self.assertEqual(stored_cert.get_cert_file_path(),
                         os.path.join(site2_certs_dir,
                                      'svn.example.com__8443.crt'))
        self.assertEqual(stored_cert.get_key_file_path(),
                         os.path.join(site2_certs_dir,
                                      'svn.example.com__8443.key'))

        stored_cert = stored_certs[7]
        self.assertAttrsEqual(
            stored_cert,
            {
                '_hostname': 'tools.corp.example.com',
                '_port': 443,
                'local_site': local_site2,
                'storage': backend,
                'storage_id': 'test-site-2:tools.corp.example.com:443',
            })
        self.assertEqual(stored_cert.get_cert_file_path(),
                         os.path.join(site2_certs_dir,
                                      'tools.corp.example.com__443.crt'))
        self.assertEqual(stored_cert.get_key_file_path(),
                         os.path.join(site2_certs_dir,
                                      'tools.corp.example.com__443.key'))

    def test_iter_stored_certificates_with_none(self) -> None:
        """Testing FileCertificateStorageBackend.iter_stored_certificates
        with no certs
        """
        local_site = self.create_local_site(name='test-site-4')
        backend = self._create_backend(storage_path=self.testdata_dir)

        stored_certs = list(backend.iter_stored_certificates(
            local_site=local_site))
        self.assertEqual(len(stored_certs), 0)

    def test_add_fingerprints(self):
        """Testing FileCertificateStorageBackend.add_fingerprints
        """
        backend = self._create_backend()
        path = os.path.join(backend.storage_path, 'fingerprints',
                            'example.com__443.json')

        self.spy_on(backend._invalidate_stats_cache)

        stored_fingerprints = backend.add_fingerprints(
            CertificateFingerprints(sha1=TEST_SHA1,
                                    sha256=TEST_SHA256),
            hostname='example.com',
            port=443)

        self.assertIsNotNone(stored_fingerprints)
        self.assertAttrsEqual(
            stored_fingerprints,
            {
                '_fingerprints_file_path': path,
                '_hostname': 'example.com',
                '_port': 443,
                'local_site': None,
                'storage': backend,
                'storage_id': 'example.com:443',
            })
        self.assertTrue(os.path.exists(path))
        self.assertAttrsEqual(
            stored_fingerprints.fingerprints,
            {
                'sha1': TEST_SHA1,
                'sha256': TEST_SHA256,
            })

        # Make sure this clears cache.
        self.assertSpyCalledWith(backend._invalidate_stats_cache,
                                 local_site=None)

    def test_add_fingerprints_with_local_site(self):
        """Testing FileCertificateStorageBackend.add_fingerprints
        with LocalSite
        """
        local_site = self.create_local_site(name='test-site')
        backend = self._create_backend()
        path = os.path.join(backend.storage_path, 'sites', 'test-site',
                            'fingerprints', 'example.com__443.json')

        self.spy_on(backend._invalidate_stats_cache)

        stored_fingerprints = backend.add_fingerprints(
            CertificateFingerprints(sha1=TEST_SHA1,
                                    sha256=TEST_SHA256),
            hostname='example.com',
            port=443,
            local_site=local_site)

        self.assertIsNotNone(stored_fingerprints)
        self.assertAttrsEqual(
            stored_fingerprints,
            {
                '_fingerprints_file_path': path,
                '_hostname': 'example.com',
                '_port': 443,
                'local_site': local_site,
                'storage': backend,
                'storage_id': 'test-site:example.com:443',
            })
        self.assertTrue(os.path.exists(path))
        self.assertAttrsEqual(
            stored_fingerprints.fingerprints,
            {
                'sha1': TEST_SHA1,
                'sha256': TEST_SHA256,
            })

        # Make sure this clears cache.
        self.assertSpyCalledWith(backend._invalidate_stats_cache,
                                 local_site=local_site)

    def test_add_fingerprints_with_ioerror(self):
        """Testing FileCertificateStorageBackend.add_fingerprints
        with IOError
        """
        backend = self._create_backend()
        path = os.path.join(backend.storage_path, 'bad-dir',
                            'example.com__443.json')

        self.spy_on(backend._invalidate_stats_cache)
        self.spy_on(backend._build_fingerprints_file_path,
                    op=kgb.SpyOpReturn(path))

        message = (
            r'Error writing SSL/TLS certificate fingerprints\. '
            r'Administrators can find details in the Review Board server '
            r'logs \(error ID [a-z0-9-]+\)\.'
        )

        with self.assertRaisesRegex(CertificateStorageError, message):
            backend.add_fingerprints(
                CertificateFingerprints(sha1=TEST_SHA1,
                                        sha256=TEST_SHA256),
                hostname='example.com',
                port=443)

        # Make sure this does not clear cache.
        self.assertSpyNotCalled(backend._invalidate_stats_cache)

    def test_delete_fingerprints(self) -> None:
        """Testing FileCertificateStorageBackend.delete_fingerprints
        """
        backend = self._create_backend()
        path = os.path.join(backend.storage_path, 'fingerprints',
                            'example.com__443.json')

        self.spy_on(backend._invalidate_stats_cache)

        self._write_file(path, TEST_FINGERPRINTS_JSON)

        backend.delete_fingerprints(hostname='example.com',
                                    port=443)

        self.assertFalse(os.path.exists(path))

        # Make sure this clears cache.
        self.assertSpyCalledWith(backend._invalidate_stats_cache,
                                 local_site=None)

    def test_delete_fingerprints_with_local_site(self) -> None:
        """Testing FileCertificateStorageBackend.delete_fingerprints with
        LocalSite
        """
        local_site = self.create_local_site(name='test-site')
        backend = self._create_backend()
        path = os.path.join(backend.storage_path, 'sites', 'test-site',
                            'fingerprints', 'example.com__443.json')

        self.spy_on(backend._invalidate_stats_cache)

        self._write_file(path, TEST_FINGERPRINTS_JSON)

        backend.delete_fingerprints(hostname='example.com',
                                    port=443,
                                    local_site=local_site)

        self.assertFalse(os.path.exists(path))

        # Make sure this clears cache.
        self.assertSpyCalledWith(backend._invalidate_stats_cache,
                                 local_site=local_site)

    def test_delete_fingerprints_with_not_found(self) -> None:
        """Testing FileCertificateStorageBackend.delete_fingerprints with
        not found
        """
        backend = self._create_backend()

        self.spy_on(backend._invalidate_stats_cache)

        with self.assertRaises(CertificateNotFoundError):
            backend.delete_fingerprints(hostname='example.com',
                                        port=443)

        # Make sure this does not clear cache.
        self.assertSpyNotCalled(backend._invalidate_stats_cache)

    def test_delete_fingerprints_with_ioerror(self) -> None:
        """Testing FileCertificateStorageBackend.delete_fingerprints with
        IOError
        """
        backend = self._create_backend()

        self.spy_on(backend._invalidate_stats_cache)
        self.spy_on(backend._build_fingerprints_file_path,
                    op=kgb.SpyOpReturn(os.path.join(backend.storage_path,
                                                    'xxx-bad-path')))

        message = (
            r'Error deleting SSL/TLS certificate fingerprints\. '
            r'Administrators can find details in the Review Board server '
            r'logs \(error ID [a-z0-9-]+\)\.'
        )

        with self.assertRaisesRegex(CertificateStorageError, message):
            backend.delete_fingerprints(hostname='example.com',
                                        port=443)

        # Make sure this does not clear cache.
        self.assertSpyNotCalled(backend._invalidate_stats_cache)

    def test_delete_fingerprints_by_id(self) -> None:
        """Testing FileCertificateStorageBackend.delete_fingerprints_by_id
        """
        backend = self._create_backend()
        path = os.path.join(backend.storage_path, 'fingerprints',
                            'example.com__443.json')

        self.spy_on(backend._invalidate_stats_cache)

        self._write_file(path, TEST_FINGERPRINTS_JSON)

        backend.delete_fingerprints_by_id('example.com:443')

        self.assertFalse(os.path.exists(path))

        # Make sure this clears cache.
        self.assertSpyCalledWith(backend._invalidate_stats_cache,
                                 local_site=None)

    def test_delete_fingerprints_with_local_site_by_id(self) -> None:
        """Testing FileCertificateStorageBackend.delete_fingerprints_by_id
        with LocalSite
        """
        local_site = self.create_local_site(name='test-site')
        backend = self._create_backend()
        path = os.path.join(backend.storage_path, 'sites', 'test-site',
                            'fingerprints', 'example.com__443.json')

        self.spy_on(backend._invalidate_stats_cache)

        self._write_file(path, TEST_FINGERPRINTS_JSON)

        backend.delete_fingerprints_by_id('test-site:example.com:443')

        self.assertFalse(os.path.exists(path))

        # Make sure this clears cache.
        self.assertSpyCalledWith(backend._invalidate_stats_cache,
                                 local_site=local_site)

    def test_get_stored_fingerprints(self) -> None:
        """Testing FileCertificateStorageBackend.get_stored_fingerprints"""
        backend = self._create_backend()
        path = os.path.join(backend.storage_path, 'fingerprints',
                            'example.com__443.json')

        self._write_file(path, TEST_FINGERPRINTS_JSON)

        stored_fingerprints = backend.get_stored_fingerprints(
            hostname='example.com',
            port=443)

        assert stored_fingerprints is not None
        self.assertAttrsEqual(
            stored_fingerprints,
            {
                '_fingerprints_file_path': path,
                '_hostname': 'example.com',
                '_port': 443,
                'local_site': None,
                'storage': backend,
                'storage_id': 'example.com:443',
            })
        self.assertTrue(os.path.exists(path))
        self.assertAttrsEqual(
            stored_fingerprints.fingerprints,
            {
                'sha1': TEST_SHA1,
                'sha256': TEST_SHA256,
            })

    def test_get_stored_fingerprints_with_local_site(self) -> None:
        """Testing FileCertificateStorageBackend.get_stored_fingerprints with
        LocalSite
        """
        local_site = self.create_local_site(name='test-site')
        backend = self._create_backend()
        path = os.path.join(backend.storage_path, 'sites', 'test-site',
                            'fingerprints', 'example.com__443.json')

        self._write_file(path, TEST_FINGERPRINTS_JSON)

        stored_fingerprints = backend.get_stored_fingerprints(
            hostname='example.com',
            port=443,
            local_site=local_site)

        assert stored_fingerprints is not None
        self.assertAttrsEqual(
            stored_fingerprints,
            {
                '_fingerprints_file_path': path,
                '_hostname': 'example.com',
                '_port': 443,
                'local_site': local_site,
                'storage': backend,
                'storage_id': 'test-site:example.com:443',
            })
        self.assertTrue(os.path.exists(path))
        self.assertAttrsEqual(
            stored_fingerprints.fingerprints,
            {
                'sha1': TEST_SHA1,
                'sha256': TEST_SHA256,
            })

    def test_get_stored_fingerprints_with_not_found(self) -> None:
        """Testing FileCertificateStorageBackend.get_stored_fingerprints with
        not found
        """
        backend = self._create_backend()

        self.assertIsNone(backend.get_stored_fingerprints(
            hostname='example.com',
            port=443))

    def test_get_stored_fingerprints_by_id(self) -> None:
        """Testing FileCertificateStorageBackend.get_stored_fingerprints_by_id
        """
        backend = self._create_backend()
        path = os.path.join(backend.storage_path, 'fingerprints',
                            'example.com__443.json')

        self._write_file(path, TEST_FINGERPRINTS_JSON)

        stored_fingerprints = backend.get_stored_fingerprints_by_id(
            'example.com:443')

        assert stored_fingerprints is not None
        self.assertAttrsEqual(
            stored_fingerprints,
            {
                '_fingerprints_file_path': path,
                '_hostname': 'example.com',
                '_port': 443,
                'local_site': None,
                'storage': backend,
                'storage_id': 'example.com:443',
            })
        self.assertTrue(os.path.exists(path))
        self.assertAttrsEqual(
            stored_fingerprints.fingerprints,
            {
                'sha1': TEST_SHA1,
                'sha256': TEST_SHA256,
            })

    def test_get_stored_fingerprints_by_id_with_local_site(self) -> None:
        """Testing FileCertificateStorageBackend.get_stored_fingerprints_by_id
        with LocalSite
        """
        local_site = self.create_local_site(name='test-site')
        backend = self._create_backend()
        path = os.path.join(backend.storage_path, 'sites', 'test-site',
                            'fingerprints', 'example.com__443.json')

        self._write_file(path, TEST_FINGERPRINTS_JSON)

        stored_fingerprints = backend.get_stored_fingerprints_by_id(
            'test-site:example.com:443')

        assert stored_fingerprints is not None
        self.assertAttrsEqual(
            stored_fingerprints,
            {
                '_fingerprints_file_path': path,
                '_hostname': 'example.com',
                '_port': 443,
                'local_site': local_site,
                'storage': backend,
                'storage_id': 'test-site:example.com:443',
            })
        self.assertTrue(os.path.exists(path))
        self.assertAttrsEqual(
            stored_fingerprints.fingerprints,
            {
                'sha1': TEST_SHA1,
                'sha256': TEST_SHA256,
            })

    def test_iter_stored_fingerprints(self) -> None:
        """Testing FileCertificateStorageBackend.iter_stored_fingerprints"""
        backend = self._create_backend(storage_path=self.testdata_dir)
        fingerprints_dir = os.path.join(backend.storage_path, 'fingerprints')

        stored_fingerprints = list(backend.iter_stored_fingerprints())
        self.assertEqual(len(stored_fingerprints), 3)

        self.assertAttrsEqual(
            stored_fingerprints[0],
            {
                '_fingerprints_file_path': os.path.join(
                    fingerprints_dir, 'ldap.example.com__636.json'),
                '_hostname': 'ldap.example.com',
                '_port': 636,
                'local_site': None,
                'storage': backend,
                'storage_id': 'ldap.example.com:636',
            })
        self.assertAttrsEqual(
            stored_fingerprints[0].fingerprints,
            {
                'sha1': (
                    '77:E7:AC:DD:7D:73:70:9F:92:DC:27:91:18:71:3E:CC:E9:53:'
                    '67:37'
                ),
                'sha256': (
                    'FF:E0:23:97:69:F0:33:9A:2A:20:15:EC:FE:E6:79:56:82:95:'
                    '18:EE:70:62:BA:B0:68:DE:42:6D:74:C9:4A:F8'
                ),
            })

        self.assertAttrsEqual(
            stored_fingerprints[1],
            {
                '_fingerprints_file_path': os.path.join(
                    fingerprints_dir, 'www.example.com__443.json'),
                '_hostname': 'www.example.com',
                '_port': 443,
                'local_site': None,
                'storage': backend,
                'storage_id': 'www.example.com:443',
            })
        self.assertAttrsEqual(
            stored_fingerprints[1].fingerprints,
            {
                'sha1': (
                    '5D:1D:5A:B2:2D:73:1E:BC:6F:E1:76:64:BE:53:EC:21:96:A1:'
                    'AF:99'
                ),
                'sha256': (
                    '45:80:1F:65:CF:A8:CC:FE:99:C5:A8:3A:B5:13:A9:5F:65:25:'
                    '75:39:B8:9C:C9:9C:36:42:96:0F:D1:88:27:25'
                ),
            })

        self.assertAttrsEqual(
            stored_fingerprints[2],
            {
                '_fingerprints_file_path': os.path.join(
                    fingerprints_dir, 'www2.example.com__443.json'),
                '_hostname': 'www2.example.com',
                '_port': 443,
                'local_site': None,
                'storage': backend,
                'storage_id': 'www2.example.com:443',
            })
        self.assertAttrsEqual(
            stored_fingerprints[2].fingerprints,
            {
                'sha1': (
                    'F2:35:0F:BB:34:40:84:78:8B:20:1D:40:B1:4A:17:0C:DE:36:'
                    '2F:D5'
                ),
                'sha256': (
                    '79:19:70:AE:A6:1B:EB:BC:35:7C:B8:54:B1:6A:AD:79:FF:F7:'
                    '28:69:02:5E:C3:6F:B3:C2:B4:FD:84:66:DF:8F'
                ),
            })

    def test_iter_stored_fingerprints_with_local_site(self) -> None:
        """Testing FileCertificateStorageBackend.iter_stored_fingerprints
        with LocalSite
        """
        local_site = self.create_local_site(name='test-site-2')
        backend = self._create_backend(storage_path=self.testdata_dir)
        fingerprints_dir = os.path.join(backend.storage_path, 'sites',
                                        'test-site-2', 'fingerprints')

        stored_fingerprints = list(backend.iter_stored_fingerprints(
            local_site=local_site))
        self.assertEqual(len(stored_fingerprints), 2)

        self.assertAttrsEqual(
            stored_fingerprints[0],
            {
                '_fingerprints_file_path': os.path.join(
                    fingerprints_dir, 'svn.example.com__8443.json'),
                '_hostname': 'svn.example.com',
                '_port': 8443,
                'local_site': local_site,
                'storage': backend,
                'storage_id': 'test-site-2:svn.example.com:8443',
            })
        self.assertAttrsEqual(
            stored_fingerprints[0].fingerprints,
            {
                'sha1': (
                    'AE:62:1C:F1:C5:39:5A:07:6F:DE:7D:E6:5F:FB:7B:99:CA:80:'
                    '3F:A8'
                ),
                'sha256': (
                    '2C:7B:FE:DB:42:E5:DD:00:F6:F0:A0:D7:61:8F:22:9A:93:50:'
                    '4E:08:6E:1C:46:09:B0:28:4D:AA:96:7D:3D:B4'
                ),
            })

        self.assertAttrsEqual(
            stored_fingerprints[1],
            {
                '_fingerprints_file_path': os.path.join(
                    fingerprints_dir, 'tools.corp.example.com__443.json'),
                '_hostname': 'tools.corp.example.com',
                '_port': 443,
                'local_site': local_site,
                'storage': backend,
                'storage_id': 'test-site-2:tools.corp.example.com:443',
            })
        self.assertAttrsEqual(
            stored_fingerprints[1].fingerprints,
            {
                'sha1': (
                    '0E:12:5D:BC:CC:77:CE:2E:D6:41:12:F6:46:61:17:B2:AB:A6:'
                    '7F:3E'
                ),
                'sha256': (
                    'AD:DC:EE:5C:45:1F:AA:60:51:05:7F:F4:46:12:A0:E1:39:1B:'
                    'ED:48:32:F4:22:BD:6B:43:71:89:5F:2B:CA:D0'
                ),
            })

    def test_iter_stored_fingerprints_with_local_site_all(self) -> None:
        """Testing FileCertificateStorageBackend.iter_stored_fingerprints
        with LocalSite.ALL
        """
        local_site1 = self.create_local_site(name='test-site-1')
        local_site2 = self.create_local_site(name='test-site-2')
        self.create_local_site(name='test-site-3')

        backend = self._create_backend(storage_path=self.testdata_dir)
        global_fingerprints_dir = os.path.join(backend.storage_path,
                                               'fingerprints')
        site1_fingerprints_dir = os.path.join(backend.storage_path, 'sites',
                                              'test-site-1', 'fingerprints')
        site2_fingerprints_dir = os.path.join(backend.storage_path, 'sites',
                                              'test-site-2', 'fingerprints')

        stored_fingerprints = list(backend.iter_stored_fingerprints(
            local_site=LocalSite.ALL))
        self.assertEqual(len(stored_fingerprints), 6)

        self.assertAttrsEqual(
            stored_fingerprints[0],
            {
                '_fingerprints_file_path': os.path.join(
                    global_fingerprints_dir, 'ldap.example.com__636.json'),
                '_hostname': 'ldap.example.com',
                '_port': 636,
                'local_site': None,
                'storage': backend,
                'storage_id': 'ldap.example.com:636',
            })
        self.assertAttrsEqual(
            stored_fingerprints[0].fingerprints,
            {
                'sha1': (
                    '77:E7:AC:DD:7D:73:70:9F:92:DC:27:91:18:71:3E:CC:E9:53:'
                    '67:37'
                ),
                'sha256': (
                    'FF:E0:23:97:69:F0:33:9A:2A:20:15:EC:FE:E6:79:56:82:95:'
                    '18:EE:70:62:BA:B0:68:DE:42:6D:74:C9:4A:F8'
                ),
            })

        self.assertAttrsEqual(
            stored_fingerprints[1],
            {
                '_fingerprints_file_path': os.path.join(
                    global_fingerprints_dir, 'www.example.com__443.json'),
                '_hostname': 'www.example.com',
                '_port': 443,
                'local_site': None,
                'storage': backend,
                'storage_id': 'www.example.com:443',
            })
        self.assertAttrsEqual(
            stored_fingerprints[1].fingerprints,
            {
                'sha1': (
                    '5D:1D:5A:B2:2D:73:1E:BC:6F:E1:76:64:BE:53:EC:21:96:A1:'
                    'AF:99'
                ),
                'sha256': (
                    '45:80:1F:65:CF:A8:CC:FE:99:C5:A8:3A:B5:13:A9:5F:65:25:'
                    '75:39:B8:9C:C9:9C:36:42:96:0F:D1:88:27:25'
                ),
            })

        self.assertAttrsEqual(
            stored_fingerprints[2],
            {
                '_fingerprints_file_path': os.path.join(
                    global_fingerprints_dir, 'www2.example.com__443.json'),
                '_hostname': 'www2.example.com',
                '_port': 443,
                'local_site': None,
                'storage': backend,
                'storage_id': 'www2.example.com:443',
            })
        self.assertAttrsEqual(
            stored_fingerprints[2].fingerprints,
            {
                'sha1': (
                    'F2:35:0F:BB:34:40:84:78:8B:20:1D:40:B1:4A:17:0C:DE:36:'
                    '2F:D5'
                ),
                'sha256': (
                    '79:19:70:AE:A6:1B:EB:BC:35:7C:B8:54:B1:6A:AD:79:FF:F7:'
                    '28:69:02:5E:C3:6F:B3:C2:B4:FD:84:66:DF:8F'
                ),
            })

        self.assertAttrsEqual(
            stored_fingerprints[3],
            {
                '_fingerprints_file_path': os.path.join(
                    site1_fingerprints_dir, 'p4.example.com__1667.json'),
                '_hostname': 'p4.example.com',
                '_port': 1667,
                'local_site': local_site1,
                'storage': backend,
                'storage_id': 'test-site-1:p4.example.com:1667',
            })
        self.assertAttrsEqual(
            stored_fingerprints[3].fingerprints,
            {
                'sha1': (
                    '70:A1:B2:1D:A2:0A:9B:BC:B7:4C:0B:1B:4C:F5:63:08:27:07:'
                    'E3:A2'
                ),
                'sha256': (
                    '25:FF:E1:A1:D2:4F:38:11:55:CD:47:E7:FD:9A:CB:05:A2:2C:'
                    'C3:B9:6E:1D:D5:C5:58:9E:F4:CB:7A:78:8E:7C'
                ),
            })

        self.assertAttrsEqual(
            stored_fingerprints[4],
            {
                '_fingerprints_file_path': os.path.join(
                    site2_fingerprints_dir, 'svn.example.com__8443.json'),
                '_hostname': 'svn.example.com',
                '_port': 8443,
                'local_site': local_site2,
                'storage': backend,
                'storage_id': 'test-site-2:svn.example.com:8443',
            })
        self.assertAttrsEqual(
            stored_fingerprints[4].fingerprints,
            {
                'sha1': (
                    'AE:62:1C:F1:C5:39:5A:07:6F:DE:7D:E6:5F:FB:7B:99:CA:80:'
                    '3F:A8'
                ),
                'sha256': (
                    '2C:7B:FE:DB:42:E5:DD:00:F6:F0:A0:D7:61:8F:22:9A:93:50:'
                    '4E:08:6E:1C:46:09:B0:28:4D:AA:96:7D:3D:B4'
                ),
            })

        self.assertAttrsEqual(
            stored_fingerprints[5],
            {
                '_fingerprints_file_path': os.path.join(
                    site2_fingerprints_dir,
                    'tools.corp.example.com__443.json'),
                '_hostname': 'tools.corp.example.com',
                '_port': 443,
                'local_site': local_site2,
                'storage': backend,
                'storage_id': 'test-site-2:tools.corp.example.com:443',
            })
        self.assertAttrsEqual(
            stored_fingerprints[5].fingerprints,
            {
                'sha1': (
                    '0E:12:5D:BC:CC:77:CE:2E:D6:41:12:F6:46:61:17:B2:AB:A6:'
                    '7F:3E'
                ),
                'sha256': (
                    'AD:DC:EE:5C:45:1F:AA:60:51:05:7F:F4:46:12:A0:E1:39:1B:'
                    'ED:48:32:F4:22:BD:6B:43:71:89:5F:2B:CA:D0'
                ),
            })

    def _create_backend(
        self,
        storage_path: Optional[str] = None,
    ) -> FileCertificateStorageBackend:
        """Return a new storage backend.

        Args:
            storage_path (str, optional):
                The path to the storage directory.

                If not provided, a temporary directory will be created and
                then cleaned up when the test is done.

        Returns:
            reviewboard.certs.storage.file_storage.
            FileCertificateStorageBackend:
            The new storage backend.
        """
        if not storage_path:
            storage_path = tempfile.mkdtemp()
            self.addCleanup(shutil.rmtree, storage_path)

        return FileCertificateStorageBackend(storage_path=storage_path)

    def _write_file(
        self,
        path: str,
        data: bytes,
    ) -> None:
        """Write a cert-related file to a directory.

        Any missing directories will be created automatically.

        Args:
            path (str):
                The absolute path to write to.

            data (bytes):
                The data to write.
        """
        os.makedirs(os.path.dirname(path), 0o700,
                    exist_ok=True)

        with open(path, 'wb') as fp:
            fp.write(data)
