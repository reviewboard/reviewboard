"""Unit tests for reviewboard.certs.manager.CertificateManager.

Version Added:
    6.0
"""

from __future__ import annotations

import json
import os
import shutil
import ssl

import kgb
from django.conf import settings
from django.core.cache import cache
from djblets.cache.backend import make_cache_key
from djblets.siteconfig.models import SiteConfiguration

from reviewboard.certs.cert import (CertPurpose, CertificateBundle,
                                    CertificateFingerprints)
from reviewboard.certs.errors import CertificateNotFoundError
from reviewboard.certs.manager import CertificateManager, logger
from reviewboard.certs.storage import cert_storage_backend_registry
from reviewboard.certs.storage.file_storage import \
    FileCertificateStorageBackend
from reviewboard.certs.tests.testcases import (CertificateTestCase,
                                               TEST_CERT_BUNDLE_PEM,
                                               TEST_CLIENT_CERT_PEM,
                                               TEST_CLIENT_KEY_PEM,
                                               TEST_SHA1,
                                               TEST_SHA256,
                                               TEST_SHA256_2,
                                               TEST_TRUST_CERT_PEM)


class MyCertificateStorageBackend(FileCertificateStorageBackend):
    backend_id = 'test'


class MySSLContext:
    cadatas: list[bytes | str | None]
    cafiles: list[str | None]
    capaths: list[str | None]
    certfiles: list[str | None]
    keyfiles: list[str | None]
    passwords: list[str | None]

    def __init__(self) -> None:
        self.cadatas = []
        self.cafiles = []
        self.capaths = []
        self.certfiles = []
        self.keyfiles = []
        self.passwords = []

    def load_verify_locations(
        self,
        cafile: (str | None) = None,
        capath: (str | None) = None,
        cadata: (bytes | str | None) = None
    ) -> None:
        if cafile:
            self.cafiles.append(cafile)

        if capath:
            self.capaths.append(capath)

        if cadata:
            self.cadatas.append(cadata)

    def load_cert_chain(
        self,
        certfile: str,
        keyfile: (str | None) = None,
        password: (str | None) = None,
    ) -> None:
        self.certfiles.append(certfile)
        self.keyfiles.append(keyfile)
        self.passwords.append(password)


class CertificateManagerTests(kgb.SpyAgency, CertificateTestCase):
    """Unit tests for CertificateManager.

    Version Added:
        6.0
    """

    ######################
    # Instance variables #
    ######################

    #: The CertificateManager certs storage path for the test run.
    #:
    #: Type:
    #:     str
    certs_path: str

    def setUp(self) -> None:
        """Set up the test case.

        This will patch in a storage location for the certificate manager
        for this test run.
        """
        super().setUp()

        self.certs_path = os.path.join(settings.SITE_DATA_DIR, 'rb-certs')

    def tearDown(self) -> None:
        if os.path.exists(self.certs_path):
            shutil.rmtree(self.certs_path)

        super().tearDown()

    def test_storage_backend_default(self) -> None:
        """Testing CertificateManager.storage_backend with default"""
        cert_manager = CertificateManager()
        storage_backend = cert_manager.storage_backend

        self.assertIsInstance(storage_backend, FileCertificateStorageBackend)
        self.assertEqual(storage_backend.storage_path,
                         os.path.join(self.certs_path, 'file'))

    def test_storage_backend_with_custom(self) -> None:
        """Testing CertificateManager.storage_backend with custom setting"""
        cert_storage_backend_registry.register(MyCertificateStorageBackend)

        self.addCleanup(
            lambda: cert_storage_backend_registry.unregister(
                MyCertificateStorageBackend))

        siteconfig = SiteConfiguration.objects.get_current()
        siteconfig.set('certs_storage_backend', 'test')

        cert_manager = CertificateManager()
        storage_backend = cert_manager.storage_backend

        self.assertIsInstance(storage_backend, MyCertificateStorageBackend)
        self.assertEqual(storage_backend.storage_path,
                         os.path.join(self.certs_path, 'test'))

    def test_storage_backend_after_setting_change(self) -> None:
        """Testing CertificateManager.storage_backend after setting is
        changed
        """
        cert_storage_backend_registry.register(MyCertificateStorageBackend)

        self.addCleanup(
            lambda: cert_storage_backend_registry.unregister(
                MyCertificateStorageBackend))

        cert_manager = CertificateManager()
        storage_backend = cert_manager.storage_backend

        self.assertIsInstance(storage_backend, FileCertificateStorageBackend)
        self.assertEqual(storage_backend.storage_path,
                         os.path.join(self.certs_path, 'file'))

        # Change the setting.
        siteconfig = SiteConfiguration.objects.get_current()
        siteconfig.set('certs_storage_backend', 'test')

        storage_backend = cert_manager.storage_backend

        self.assertIsInstance(storage_backend, MyCertificateStorageBackend)
        self.assertEqual(storage_backend.storage_path,
                         os.path.join(self.certs_path, 'test'))

    def test_storage_backend_with_missing_backend(self) -> None:
        """Testing CertificateManager.storage_backend with missing backend"""
        siteconfig = SiteConfiguration.objects.get_current()
        siteconfig.set('certs_storage_backend', 'test')

        cert_manager = CertificateManager()

        with self.assertLogs(logger) as cm:
            storage_backend = cert_manager.storage_backend

        self.assertEqual(
            cm.records[0].getMessage(),
            'Unable to load SSL/TLS certificate storage backend "test". '
            'Falling back to file-based storage.')

        self.assertIsInstance(storage_backend, FileCertificateStorageBackend)
        self.assertEqual(storage_backend.storage_path,
                         os.path.join(self.certs_path, 'file'))

    def test_add_ca_bundle(self) -> None:
        """Testing CertificateManager.add_ca_bundle"""
        cert_manager = CertificateManager()
        storage_backend = cert_manager.storage_backend
        path = os.path.join(storage_backend.storage_path, 'cabundles',
                            'my-certs.pem')

        stored_ca_bundle = cert_manager.add_ca_bundle(
            CertificateBundle(bundle_data=TEST_CERT_BUNDLE_PEM,
                              name='my-certs'))

        self.assertIsNotNone(stored_ca_bundle)
        self.assertAttrsEqual(
            stored_ca_bundle,
            {
                'local_site': None,
                'storage': storage_backend,
            })
        self.assertTrue(os.path.exists(path))
        self.assertEqual(stored_ca_bundle.get_bundle_file_path(), path)

        with open(path, 'rb') as fp:
            self.assertEqual(fp.read(), TEST_CERT_BUNDLE_PEM)

        self.assertAttrsEqual(
            stored_ca_bundle.bundle,
            {
                'bundle_data': TEST_CERT_BUNDLE_PEM,
                'name': 'my-certs',
            })

    def test_add_ca_bundle_with_local_site(self) -> None:
        """Testing CertificateManager.add_ca_bundle with LocalSite"""
        local_site = self.create_local_site('test-site')

        cert_manager = CertificateManager()
        storage_backend = cert_manager.storage_backend
        path = os.path.join(storage_backend.storage_path, 'sites',
                            'test-site', 'cabundles', 'my-certs.pem')

        stored_ca_bundle = cert_manager.add_ca_bundle(
            CertificateBundle(bundle_data=TEST_CERT_BUNDLE_PEM,
                              name='my-certs'),
            local_site=local_site)

        self.assertIsNotNone(stored_ca_bundle)
        self.assertAttrsEqual(
            stored_ca_bundle,
            {
                'local_site': local_site,
                'storage': storage_backend,
            })
        self.assertTrue(os.path.exists(path))
        self.assertEqual(stored_ca_bundle.get_bundle_file_path(), path)

        with open(path, 'rb') as fp:
            self.assertEqual(fp.read(), TEST_CERT_BUNDLE_PEM)

        self.assertAttrsEqual(
            stored_ca_bundle.bundle,
            {
                'bundle_data': TEST_CERT_BUNDLE_PEM,
                'name': 'my-certs',
            })

    def test_delete_ca_bundle(self) -> None:
        """Testing CertificateManager.delete_ca_bundle"""
        cert_manager = CertificateManager()
        storage_backend = cert_manager.storage_backend
        path = os.path.join(storage_backend.storage_path, 'cabundles',
                            'my-certs.pem')

        cert_manager.add_ca_bundle(
            CertificateBundle(bundle_data=TEST_CERT_BUNDLE_PEM,
                              name='my-certs'))
        self.assertTrue(os.path.exists(path))

        storage_backend.delete_ca_bundle(name='my-certs')
        self.assertFalse(os.path.exists(path))

    def test_delete_ca_bundle_with_local_site(self) -> None:
        """Testing CertificateManager.delete_ca_bundle with LocalSite"""
        local_site = self.create_local_site('test-site')

        cert_manager = CertificateManager()
        storage_backend = cert_manager.storage_backend
        path = os.path.join(storage_backend.storage_path, 'sites',
                            'test-site', 'cabundles', 'my-certs.pem')

        cert_manager.add_ca_bundle(
            CertificateBundle(bundle_data=TEST_CERT_BUNDLE_PEM,
                              name='my-certs'),
            local_site=local_site)
        self.assertTrue(os.path.exists(path))

        storage_backend.delete_ca_bundle(name='my-certs',
                                         local_site=local_site)
        self.assertFalse(os.path.exists(path))

    def test_delete_ca_bundle_with_local_site_mismatch(self) -> None:
        """Testing CertificateManager.delete_ca_bundle with LocalSite
        mismatch
        """
        local_site1 = self.create_local_site('test-site-1')
        local_site2 = self.create_local_site('test-site-2')

        cert_manager = CertificateManager()
        storage_backend = cert_manager.storage_backend
        path = os.path.join(storage_backend.storage_path, 'sites',
                            'test-site-1', 'cabundles', 'my-certs.pem')

        cert_manager.add_ca_bundle(
            CertificateBundle(bundle_data=TEST_CERT_BUNDLE_PEM,
                              name='my-certs'),
            local_site=local_site1)
        self.assertTrue(os.path.exists(path))

        message = 'The SSL/TLS certificate was not found.'

        with self.assertRaisesMessage(CertificateNotFoundError, message):
            storage_backend.delete_ca_bundle(name='my-certs')

        with self.assertRaisesMessage(CertificateNotFoundError, message):
            storage_backend.delete_ca_bundle(name='my-certs',
                                             local_site=local_site2)

        self.assertTrue(os.path.exists(path))

    def test_get_ca_bundle(self) -> None:
        """Testing CertificateManager.get_ca_bundle"""
        local_site = self.create_local_site('test-site-1')

        cert_manager = CertificateManager()

        cert_manager.add_ca_bundle(
            CertificateBundle(bundle_data=TEST_CERT_BUNDLE_PEM,
                              name='my-certs'))
        ca_bundle = cert_manager.get_ca_bundle(name='my-certs')
        assert ca_bundle is not None

        self.assertAttrsEqual(
            ca_bundle,
            {
                'bundle_data': TEST_CERT_BUNDLE_PEM,
                'name': 'my-certs',
            })

        # Make sure it's only accessible on the global site.
        self.assertIsNone(cert_manager.get_ca_bundle(name='my-certs',
                                                     local_site=local_site))

    def test_get_ca_bundle_with_local_site(self) -> None:
        """Testing CertificateManager.get_ca_bundle with LocalSite"""
        local_site1 = self.create_local_site('test-site-1')
        local_site2 = self.create_local_site('test-site-2')

        cert_manager = CertificateManager()
        cert_manager.add_ca_bundle(
            CertificateBundle(bundle_data=TEST_CERT_BUNDLE_PEM,
                              name='my-certs'),
            local_site=local_site1)
        ca_bundle = cert_manager.get_ca_bundle(name='my-certs',
                                               local_site=local_site1)
        assert ca_bundle is not None

        self.assertAttrsEqual(
            ca_bundle,
            {
                'bundle_data': TEST_CERT_BUNDLE_PEM,
                'name': 'my-certs',
            })

        # Make sure it's only accessible on local_site1.
        self.assertIsNone(cert_manager.get_ca_bundle(name='my-certs'))
        self.assertIsNone(cert_manager.get_ca_bundle(name='my-certs',
                                                     local_site=local_site2))

    def test_get_ca_bundle_with_not_found(self) -> None:
        """Testing CertificateManager.get_ca_bundle with not found"""
        cert_manager = CertificateManager()

        self.assertIsNone(cert_manager.get_ca_bundle(name='missing-certs'))

    def test_get_ca_bundles_dir(self) -> None:
        """Testing CertificateManager.get_ca_bundles_dir"""
        cert_manager = CertificateManager()

        self.assertEqual(cert_manager.get_ca_bundles_dir(),
                         os.path.join(self.certs_path, 'file', 'cabundles'))

    def test_get_ca_bundles_dir_with_local_site(self) -> None:
        """Testing CertificateManager.get_ca_bundles_dir"""
        local_site = self.create_local_site('test-site-1')

        cert_manager = CertificateManager()

        self.assertEqual(
            cert_manager.get_ca_bundles_dir(local_site=local_site),
            os.path.join(self.certs_path, 'file', 'sites', 'test-site-1',
                         'cabundles'))

    def test_add_certificate_with_trust(self) -> None:
        """Testing CertificateManager.add_certificate with purpose=trust"""
        cert_manager = CertificateManager()
        storage_backend = cert_manager.storage_backend

        cert_path = os.path.join(storage_backend.storage_path, 'certs',
                                 'trust', 'example.com__443.crt')
        key_path = os.path.join(storage_backend.storage_path, 'certs',
                                'trust', 'example.com__443.key')
        fingerprints_path = os.path.join(storage_backend.storage_path,
                                         'fingerprints',
                                         'example.com__443.json')

        stored_cert = cert_manager.add_certificate(
            self.create_certificate(cert_data=TEST_TRUST_CERT_PEM))

        self.assertIsNotNone(stored_cert)
        self.assertAttrsEqual(
            stored_cert,
            {
                'local_site': None,
                'purpose': CertPurpose.TRUST,
                'storage': storage_backend,
            })
        self.assertTrue(os.path.exists(cert_path))
        self.assertFalse(os.path.exists(key_path))
        self.assertTrue(os.path.exists(fingerprints_path))
        self.assertEqual(stored_cert.get_cert_file_path(), cert_path)
        self.assertIsNone(stored_cert.get_key_file_path())

        with open(cert_path, 'rb') as fp:
            self.assertEqual(fp.read(), TEST_TRUST_CERT_PEM)

        with open(fingerprints_path, 'rb') as fp:
            self.assertEqual(json.load(fp), {
                'sha1': TEST_SHA1,
                'sha256': TEST_SHA256,
            })

        self.assertAttrsEqual(
            stored_cert.certificate,
            {
                'cert_data': TEST_TRUST_CERT_PEM,
                'hostname': 'example.com',
                'key_data': None,
                'port': 443,
                'purpose': CertPurpose.TRUST,
            })

    def test_add_certificate_with_client(self) -> None:
        """Testing CertificateManager.add_certificate with purpose=client"""
        cert_manager = CertificateManager()
        storage_backend = cert_manager.storage_backend

        cert_path = os.path.join(storage_backend.storage_path, 'certs',
                                 'client', 'example.com__443.crt')
        key_path = os.path.join(storage_backend.storage_path, 'certs',
                                'client', 'example.com__443.key')

        stored_cert = cert_manager.add_certificate(
            self.create_certificate(purpose=CertPurpose.CLIENT,
                                    cert_data=TEST_CLIENT_CERT_PEM,
                                    key_data=TEST_CLIENT_KEY_PEM))

        self.assertIsNotNone(stored_cert)
        self.assertAttrsEqual(
            stored_cert,
            {
                'local_site': None,
                'purpose': CertPurpose.CLIENT,
                'storage': storage_backend,
            })
        self.assertTrue(os.path.exists(cert_path))
        self.assertTrue(os.path.exists(key_path))
        self.assertEqual(stored_cert.get_cert_file_path(), cert_path)
        self.assertEqual(stored_cert.get_key_file_path(), key_path)

        # Fingerprints should not exist for these certificates.
        self.assertFalse(os.path.exists(os.path.join(
            storage_backend.storage_path, 'fingerprints',
            'example.com__443.json')))

        with open(cert_path, 'rb') as fp:
            self.assertEqual(fp.read(), TEST_CLIENT_CERT_PEM)

        with open(key_path, 'rb') as fp:
            self.assertEqual(fp.read(), TEST_CLIENT_KEY_PEM)

        self.assertAttrsEqual(
            stored_cert.certificate,
            {
                'cert_data': TEST_CLIENT_CERT_PEM,
                'hostname': 'example.com',
                'key_data': TEST_CLIENT_KEY_PEM,
                'port': 443,
                'purpose': CertPurpose.CLIENT,
            })

    def test_add_certificate_with_trust_and_local_site(self) -> None:
        """Testing CertificateManager.add_certificate with purpose=trust and
        LocalSite
        """
        local_site = self.create_local_site('test-site-1')

        cert_manager = CertificateManager()
        storage_backend = cert_manager.storage_backend

        site_storage_path = os.path.join(storage_backend.storage_path, 'sites',
                                         'test-site-1')
        cert_path = os.path.join(site_storage_path, 'certs', 'trust',
                                 'example.com__443.crt')
        key_path = os.path.join(site_storage_path, 'certs', 'trust',
                                'example.com__443.key')
        fingerprints_path = os.path.join(site_storage_path, 'fingerprints',
                                         'example.com__443.json')

        stored_cert = cert_manager.add_certificate(
            self.create_certificate(cert_data=TEST_TRUST_CERT_PEM),
            local_site=local_site)

        self.assertIsNotNone(stored_cert)
        self.assertAttrsEqual(
            stored_cert,
            {
                'local_site': local_site,
                'purpose': CertPurpose.TRUST,
                'storage': storage_backend,
            })
        self.assertTrue(os.path.exists(cert_path))
        self.assertFalse(os.path.exists(key_path))
        self.assertTrue(os.path.exists(fingerprints_path))
        self.assertEqual(stored_cert.get_cert_file_path(), cert_path)
        self.assertIsNone(stored_cert.get_key_file_path())

        with open(cert_path, 'rb') as fp:
            self.assertEqual(fp.read(), TEST_TRUST_CERT_PEM)

        with open(fingerprints_path, 'rb') as fp:
            self.assertEqual(json.load(fp), {
                'sha1': TEST_SHA1,
                'sha256': TEST_SHA256,
            })

        self.assertAttrsEqual(
            stored_cert.certificate,
            {
                'cert_data': TEST_TRUST_CERT_PEM,
                'hostname': 'example.com',
                'key_data': None,
                'port': 443,
                'purpose': CertPurpose.TRUST,
            })

    def test_add_certificate_with_client_and_local_site(self) -> None:
        """Testing CertificateManager.add_certificate with purpose=client and
        LocalSite
        """
        local_site = self.create_local_site('test-site-1')

        cert_manager = CertificateManager()
        storage_backend = cert_manager.storage_backend

        site_storage_path = os.path.join(storage_backend.storage_path, 'sites',
                                         'test-site-1')
        cert_path = os.path.join(site_storage_path, 'certs', 'client',
                                 'example.com__443.crt')
        key_path = os.path.join(site_storage_path, 'certs', 'client',
                                'example.com__443.key')

        stored_cert = cert_manager.add_certificate(
            self.create_certificate(purpose=CertPurpose.CLIENT,
                                    cert_data=TEST_CLIENT_CERT_PEM,
                                    key_data=TEST_CLIENT_KEY_PEM),
            local_site=local_site)

        self.assertIsNotNone(stored_cert)
        self.assertAttrsEqual(
            stored_cert,
            {
                'local_site': local_site,
                'purpose': CertPurpose.CLIENT,
                'storage': storage_backend,
            })
        self.assertTrue(os.path.exists(cert_path))
        self.assertTrue(os.path.exists(key_path))
        self.assertEqual(stored_cert.get_cert_file_path(), cert_path)
        self.assertEqual(stored_cert.get_key_file_path(), key_path)

        # Fingerprints should not exist for these certificates.
        self.assertFalse(os.path.exists(os.path.join(
            storage_backend.storage_path, 'fingerprints',
            'example.com__443.json')))

        with open(cert_path, 'rb') as fp:
            self.assertEqual(fp.read(), TEST_CLIENT_CERT_PEM)

        with open(key_path, 'rb') as fp:
            self.assertEqual(fp.read(), TEST_CLIENT_KEY_PEM)

        self.assertAttrsEqual(
            stored_cert.certificate,
            {
                'cert_data': TEST_CLIENT_CERT_PEM,
                'hostname': 'example.com',
                'key_data': TEST_CLIENT_KEY_PEM,
                'port': 443,
                'purpose': CertPurpose.CLIENT,
            })

    def test_delete_certificate_with_trust(self) -> None:
        """Testing CertificateManager.delete_certificate with purpose=trust"""
        cert_manager = CertificateManager()
        storage_backend = cert_manager.storage_backend

        cert_path = os.path.join(storage_backend.storage_path, 'certs',
                                 'trust', 'example.com__443.crt')
        key_path = os.path.join(storage_backend.storage_path, 'certs',
                                'trust', 'example.com__443.key')
        fingerprints_path = os.path.join(storage_backend.storage_path,
                                         'fingerprints',
                                         'example.com__443.json')

        cert_manager.add_certificate(
            self.create_certificate(cert_data=TEST_TRUST_CERT_PEM))

        self.assertTrue(os.path.exists(cert_path))
        self.assertFalse(os.path.exists(key_path))
        self.assertTrue(os.path.exists(fingerprints_path))

        cert_manager.delete_certificate(hostname='example.com',
                                        port=443)

        self.assertFalse(os.path.exists(cert_path))
        self.assertFalse(os.path.exists(key_path))
        self.assertFalse(os.path.exists(fingerprints_path))

    def test_delete_certificate_with_client(self) -> None:
        """Testing CertificateManager.delete_certificate with purpose=client"""
        cert_manager = CertificateManager()
        storage_backend = cert_manager.storage_backend

        cert_path = os.path.join(storage_backend.storage_path, 'certs',
                                 'client', 'example.com__443.crt')
        key_path = os.path.join(storage_backend.storage_path, 'certs',
                                'client', 'example.com__443.key')
        fingerprints_path = os.path.join(storage_backend.storage_path,
                                         'fingerprints',
                                         'example.com__443.json')

        cert_manager.add_certificate(
            self.create_certificate(purpose=CertPurpose.CLIENT,
                                    cert_data=TEST_CLIENT_CERT_PEM,
                                    key_data=TEST_CLIENT_KEY_PEM))

        self.assertTrue(os.path.exists(cert_path))
        self.assertTrue(os.path.exists(key_path))
        self.assertFalse(os.path.exists(fingerprints_path))

        cert_manager.delete_certificate(hostname='example.com',
                                        port=443,
                                        purpose=CertPurpose.CLIENT)

        self.assertFalse(os.path.exists(cert_path))
        self.assertFalse(os.path.exists(key_path))
        self.assertFalse(os.path.exists(fingerprints_path))

    def test_delete_certificate_with_trust_and_local_site(self) -> None:
        """Testing CertificateManager.delete_certificate with purpose=trust
        and LocalSite
        """
        local_site = self.create_local_site('test-site-1')

        cert_manager = CertificateManager()
        storage_backend = cert_manager.storage_backend

        site_storage_path = os.path.join(storage_backend.storage_path, 'sites',
                                         'test-site-1')
        cert_path = os.path.join(site_storage_path, 'certs', 'trust',
                                 'example.com__443.crt')
        key_path = os.path.join(site_storage_path, 'certs', 'trust',
                                'example.com__443.key')
        fingerprints_path = os.path.join(site_storage_path, 'fingerprints',
                                         'example.com__443.json')

        cert_manager.add_certificate(
            self.create_certificate(cert_data=TEST_TRUST_CERT_PEM),
            local_site=local_site)

        self.assertTrue(os.path.exists(cert_path))
        self.assertFalse(os.path.exists(key_path))
        self.assertTrue(os.path.exists(fingerprints_path))

        cert_manager.delete_certificate(hostname='example.com',
                                        port=443,
                                        local_site=local_site)

        self.assertFalse(os.path.exists(cert_path))
        self.assertFalse(os.path.exists(key_path))
        self.assertFalse(os.path.exists(fingerprints_path))

    def test_delete_certificate_with_client_and_local_site(self) -> None:
        """Testing CertificateManager.delete_certificate with purpose=client
        and LocalSite
        """
        local_site = self.create_local_site('test-site-1')

        cert_manager = CertificateManager()
        storage_backend = cert_manager.storage_backend

        site_storage_path = os.path.join(storage_backend.storage_path, 'sites',
                                         'test-site-1')
        cert_path = os.path.join(site_storage_path, 'certs', 'client',
                                 'example.com__443.crt')
        key_path = os.path.join(site_storage_path, 'certs', 'client',
                                'example.com__443.key')
        fingerprints_path = os.path.join(site_storage_path, 'fingerprints',
                                         'example.com__443.json')

        cert_manager.add_certificate(
            self.create_certificate(purpose=CertPurpose.CLIENT,
                                    cert_data=TEST_CLIENT_CERT_PEM,
                                    key_data=TEST_CLIENT_KEY_PEM),
            local_site=local_site)

        self.assertTrue(os.path.exists(cert_path))
        self.assertTrue(os.path.exists(key_path))
        self.assertFalse(os.path.exists(fingerprints_path))

        cert_manager.delete_certificate(hostname='example.com',
                                        port=443,
                                        purpose=CertPurpose.CLIENT,
                                        local_site=local_site)

        self.assertFalse(os.path.exists(cert_path))
        self.assertFalse(os.path.exists(key_path))
        self.assertFalse(os.path.exists(fingerprints_path))

    def test_delete_certificate_with_trust_and_local_site_mismatch(
        self,
    ) -> None:
        """Testing CertificateManager.delete_certificate with purpose=trust
        and LocalSite mismatch
        """
        local_site1 = self.create_local_site('test-site-1')
        local_site2 = self.create_local_site('test-site-2')

        cert_manager = CertificateManager()
        storage_backend = cert_manager.storage_backend

        site_storage_path = os.path.join(storage_backend.storage_path, 'sites',
                                         'test-site-1')
        cert_path = os.path.join(site_storage_path, 'certs', 'trust',
                                 'example.com__443.crt')
        key_path = os.path.join(site_storage_path, 'certs', 'trust',
                                'example.com__443.key')
        fingerprints_path = os.path.join(site_storage_path, 'fingerprints',
                                         'example.com__443.json')

        cert_manager.add_certificate(
            self.create_certificate(cert_data=TEST_TRUST_CERT_PEM),
            local_site=local_site1)

        message = 'The SSL/TLS certificate was not found.'

        with self.assertRaisesMessage(CertificateNotFoundError, message):
            cert_manager.delete_certificate(hostname='example.com',
                                            port=443)

        with self.assertRaisesMessage(CertificateNotFoundError, message):
            cert_manager.delete_certificate(hostname='example.com',
                                            port=443,
                                            local_site=local_site2)

        self.assertTrue(os.path.exists(cert_path))
        self.assertFalse(os.path.exists(key_path))
        self.assertTrue(os.path.exists(fingerprints_path))

    def test_delete_certificate_with_client_and_local_site_mismatch(
        self,
    ) -> None:
        """Testing CertificateManager.delete_certificate with purpose=client
        and LocalSite mismatch
        """
        local_site1 = self.create_local_site('test-site-1')
        local_site2 = self.create_local_site('test-site-2')

        cert_manager = CertificateManager()
        storage_backend = cert_manager.storage_backend

        site_storage_path = os.path.join(storage_backend.storage_path, 'sites',
                                         'test-site-1')
        cert_path = os.path.join(site_storage_path, 'certs', 'client',
                                 'example.com__443.crt')
        key_path = os.path.join(site_storage_path, 'certs', 'client',
                                'example.com__443.key')
        fingerprints_path = os.path.join(site_storage_path, 'fingerprints',
                                         'example.com__443.json')

        cert_manager.add_certificate(
            self.create_certificate(purpose=CertPurpose.CLIENT,
                                    cert_data=TEST_CLIENT_CERT_PEM,
                                    key_data=TEST_CLIENT_KEY_PEM),
            local_site=local_site1)

        message = 'The SSL/TLS certificate was not found.'

        with self.assertRaisesMessage(CertificateNotFoundError, message):
            cert_manager.delete_certificate(hostname='example.com',
                                            port=443)

        with self.assertRaisesMessage(CertificateNotFoundError, message):
            cert_manager.delete_certificate(hostname='example.com',
                                            port=443,
                                            local_site=local_site2)

        self.assertTrue(os.path.exists(cert_path))
        self.assertTrue(os.path.exists(key_path))
        self.assertFalse(os.path.exists(fingerprints_path))

    def test_get_certificate_with_trust(self) -> None:
        """Testing CertificateManager.get_certificate with purpose=trust"""
        local_site = self.create_local_site('test-site-1')

        cert_manager = CertificateManager()

        cert_manager.add_certificate(
            self.create_certificate(cert_data=TEST_TRUST_CERT_PEM))
        cert_manager.add_certificate(
            self.create_certificate(purpose=CertPurpose.CLIENT,
                                    cert_data=TEST_CLIENT_CERT_PEM,
                                    key_data=TEST_CLIENT_KEY_PEM))

        certificate = cert_manager.get_certificate(
            hostname='example.com',
            port=443,
            purpose=CertPurpose.TRUST,
        )

        assert certificate is not None

        self.assertAttrsEqual(
            certificate,
            {
                'cert_data': TEST_TRUST_CERT_PEM,
                'hostname': 'example.com',
                'key_data': None,
                'purpose': CertPurpose.TRUST,
                'port': 443,
            })

        # Make sure it's only accessible on the global site.
        self.assertIsNone(cert_manager.get_certificate(hostname='example.com',
                                                       port=443,
                                                       local_site=local_site))

    def test_get_certificate_with_client(self) -> None:
        """Testing CertificateManager.get_certificate with purpose=client"""
        local_site = self.create_local_site('test-site-1')

        cert_manager = CertificateManager()

        cert_manager.add_certificate(
            self.create_certificate(cert_data=TEST_TRUST_CERT_PEM))
        cert_manager.add_certificate(
            self.create_certificate(purpose=CertPurpose.CLIENT,
                                    cert_data=TEST_CLIENT_CERT_PEM,
                                    key_data=TEST_CLIENT_KEY_PEM))

        certificate = cert_manager.get_certificate(
            hostname='example.com',
            port=443,
            purpose=CertPurpose.CLIENT,
        )

        assert certificate is not None

        self.assertAttrsEqual(
            certificate,
            {
                'cert_data': TEST_CLIENT_CERT_PEM,
                'hostname': 'example.com',
                'key_data': TEST_CLIENT_KEY_PEM,
                'port': 443,
                'purpose': CertPurpose.CLIENT,
            })

        # Make sure it's only accessible on the global site.
        self.assertIsNone(cert_manager.get_certificate(
            hostname='example.com',
            port=443,
            local_site=local_site,
            purpose=CertPurpose.CLIENT,
        ))

    def test_get_certificate_with_trust_and_local_site(self) -> None:
        """Testing CertificateManager.get_certificate with purpose=trust
        and LocalSite
        """
        local_site1 = self.create_local_site('test-site-1')
        local_site2 = self.create_local_site('test-site-2')

        cert_manager = CertificateManager()

        cert_manager.add_certificate(
            self.create_certificate(cert_data=TEST_TRUST_CERT_PEM),
            local_site=local_site1,
        )
        cert_manager.add_certificate(
            self.create_certificate(
                purpose=CertPurpose.CLIENT,
                cert_data=TEST_CLIENT_CERT_PEM,
                key_data=TEST_CLIENT_KEY_PEM,
            ),
            local_site=local_site1,
        )

        certificate = cert_manager.get_certificate(
            hostname='example.com',
            port=443,
            local_site=local_site1,
        )

        assert certificate is not None

        self.assertAttrsEqual(
            certificate,
            {
                'cert_data': TEST_TRUST_CERT_PEM,
                'hostname': 'example.com',
                'key_data': None,
                'port': 443,
                'purpose': CertPurpose.TRUST,
            })

        # Make sure it's only accessible on local_site1.
        self.assertIsNone(cert_manager.get_certificate(hostname='example.com',
                                                       port=443))
        self.assertIsNone(cert_manager.get_certificate(hostname='example.com',
                                                       port=443,
                                                       local_site=local_site2))

    def test_get_certificate_with_client_and_local_site(self) -> None:
        """Testing CertificateManager.get_certificate with purpose=client
        and LocalSite
        """
        local_site1 = self.create_local_site('test-site-1')
        local_site2 = self.create_local_site('test-site-2')

        cert_manager = CertificateManager()

        cert_manager.add_certificate(
            self.create_certificate(cert_data=TEST_TRUST_CERT_PEM),
            local_site=local_site1,
        )
        cert_manager.add_certificate(
            self.create_certificate(
                purpose=CertPurpose.CLIENT,
                cert_data=TEST_CLIENT_CERT_PEM,
                key_data=TEST_CLIENT_KEY_PEM,
            ),
            local_site=local_site1,
        )

        certificate = cert_manager.get_certificate(
            hostname='example.com',
            port=443,
            purpose=CertPurpose.CLIENT,
            local_site=local_site1,
        )

        assert certificate is not None

        self.assertAttrsEqual(
            certificate,
            {
                'cert_data': TEST_CLIENT_CERT_PEM,
                'hostname': 'example.com',
                'key_data': TEST_CLIENT_KEY_PEM,
                'port': 443,
                'purpose': CertPurpose.CLIENT,
            })

        # Make sure it's only accessible on local_site1.
        self.assertIsNone(cert_manager.get_certificate(
            hostname='example.com',
            port=443,
            purpose=CertPurpose.CLIENT,
        ))
        self.assertIsNone(cert_manager.get_certificate(
            hostname='example.com',
            port=443,
            local_site=local_site2,
            purpose=CertPurpose.CLIENT,
        ))

    def test_get_certificate_with_not_found(self) -> None:
        """Testing CertificateManager.get_certificate with not found"""
        cert_manager = CertificateManager()

        self.assertIsNone(cert_manager.get_certificate(hostname='example.com',
                                                       port=443,))

    def test_get_certificate_file_paths_with_trust(self) -> None:
        """Testing CertificateManager.get_certificate_file_paths with
        purpose=trust
        """
        local_site = self.create_local_site('test-site-1')

        cert_manager = CertificateManager()
        storage_backend = cert_manager.storage_backend

        cert_manager.add_certificate(
            self.create_certificate(cert_data=TEST_TRUST_CERT_PEM))

        self.assertEqual(
            cert_manager.get_certificate_file_paths(hostname='example.com',
                                                    port=443),
            {
                'cert_file': os.path.join(storage_backend.storage_path,
                                          'certs', 'trust',
                                          'example.com__443.crt'),
            })

        # Make sure it's only accessible on the global site.
        self.assertIsNone(cert_manager.get_certificate_file_paths(
            hostname='example.com',
            port=443,
            local_site=local_site,
        ))

    def test_get_certificate_file_paths_with_client(self) -> None:
        """Testing CertificateManager.get_certificate_file_paths with
        purpose=client
        """
        local_site = self.create_local_site('test-site-1')

        cert_manager = CertificateManager()
        storage_backend = cert_manager.storage_backend

        cert_manager.add_certificate(self.create_certificate(
            cert_data=TEST_TRUST_CERT_PEM,
        ))
        cert_manager.add_certificate(self.create_certificate(
            purpose=CertPurpose.CLIENT,
            cert_data=TEST_CLIENT_CERT_PEM,
            key_data=TEST_CLIENT_KEY_PEM,
        ))

        self.assertEqual(
            cert_manager.get_certificate_file_paths(
                hostname='example.com',
                port=443,
                purpose=CertPurpose.CLIENT,
            ),
            {
                'cert_file': os.path.join(storage_backend.storage_path,
                                          'certs', 'client',
                                          'example.com__443.crt'),
                'key_file': os.path.join(storage_backend.storage_path,
                                         'certs', 'client',
                                         'example.com__443.key'),
            })

        # Make sure it's only accessible on the global site.
        self.assertIsNone(cert_manager.get_certificate_file_paths(
            hostname='example.com',
            port=443,
            purpose=CertPurpose.CLIENT,
            local_site=local_site,
        ))

    def test_get_certificate_file_paths_with_trust_and_local_site(
        self,
    ) -> None:
        """Testing CertificateManager.get_certificate_file_paths with
        purpose=trust and LocalSite
        """
        local_site1 = self.create_local_site('test-site-1')
        local_site2 = self.create_local_site('test-site-2')

        cert_manager = CertificateManager()
        storage_backend = cert_manager.storage_backend
        site_storage_path = os.path.join(storage_backend.storage_path, 'sites',
                                         'test-site-1')

        cert_manager.add_certificate(
            self.create_certificate(cert_data=TEST_TRUST_CERT_PEM),
            local_site=local_site1,
        )
        cert_manager.add_certificate(
            self.create_certificate(
                purpose=CertPurpose.CLIENT,
                cert_data=TEST_CLIENT_CERT_PEM,
                key_data=TEST_CLIENT_KEY_PEM,
            ),
            local_site=local_site1,
        )

        self.assertEqual(
            cert_manager.get_certificate_file_paths(
                hostname='example.com',
                port=443,
                local_site=local_site1,
            ),
            {
                'cert_file': os.path.join(site_storage_path, 'certs',
                                          'trust', 'example.com__443.crt'),
            })

        # Make sure it's only accessible on local_site1.
        self.assertIsNone(cert_manager.get_certificate_file_paths(
            hostname='example.com',
            port=443,
        ))
        self.assertIsNone(cert_manager.get_certificate_file_paths(
            hostname='example.com',
            port=443,
            local_site=local_site2,
        ))

    def test_get_certificate_file_paths_with_client_and_local_site(
        self,
    ) -> None:
        """Testing CertificateManager.get_certificate_file_paths with
        purpose=client and LocalSite
        """
        local_site1 = self.create_local_site('test-site-1')
        local_site2 = self.create_local_site('test-site-2')

        cert_manager = CertificateManager()
        storage_backend = cert_manager.storage_backend
        site_storage_path = os.path.join(storage_backend.storage_path, 'sites',
                                         'test-site-1')

        cert_manager.add_certificate(
            self.create_certificate(cert_data=TEST_TRUST_CERT_PEM),
            local_site=local_site1,
        )
        cert_manager.add_certificate(
            self.create_certificate(
                purpose=CertPurpose.CLIENT,
                cert_data=TEST_CLIENT_CERT_PEM,
                key_data=TEST_CLIENT_KEY_PEM,
            ),
            local_site=local_site1,
        )

        self.assertEqual(
            cert_manager.get_certificate_file_paths(
                hostname='example.com',
                port=443,
                purpose=CertPurpose.CLIENT,
                local_site=local_site1,
            ),
            {
                'cert_file': os.path.join(site_storage_path, 'certs',
                                          'client', 'example.com__443.crt'),
                'key_file': os.path.join(site_storage_path, 'certs',
                                         'client', 'example.com__443.key'),
            })

        # Make sure it's only accessible on local_site1.
        self.assertIsNone(cert_manager.get_certificate_file_paths(
            hostname='example.com',
            port=443,
            purpose=CertPurpose.CLIENT,
        ))
        self.assertIsNone(cert_manager.get_certificate_file_paths(
            hostname='example.com',
            port=443,
            local_site=local_site2,
            purpose=CertPurpose.CLIENT,
        ))

    def test_mark_certificate_verified(self) -> None:
        """Testing CertificateManager.mark_certificate_verified"""
        cert_manager = CertificateManager()
        storage_backend = cert_manager.storage_backend
        fingerprints_path = os.path.join(storage_backend.storage_path,
                                         'fingerprints',
                                         'example.com__443.json')

        cert_manager.mark_certificate_verified(
            hostname='example.com',
            port=443,
            fingerprints=self.create_certificate_fingerprints())

        self.assertTrue(os.path.exists(fingerprints_path))

        with open(fingerprints_path, 'rb') as fp:
            self.assertEqual(json.load(fp), {
                'sha1': TEST_SHA1,
                'sha256': TEST_SHA256,
            })

        # This should also be in cache.
        self.assertEqual(
            cache.get(make_cache_key(
                'rb-ssl-fingerprints:file:example.com:443')),
            {
                'sha1': TEST_SHA1,
                'sha256': TEST_SHA256,
            })

    def test_mark_certificate_verified_with_local_site(self) -> None:
        """Testing CertificateManager.mark_certificate_verified with LocalSite
        """
        local_site = self.create_local_site('test-site-1')

        cert_manager = CertificateManager()
        storage_backend = cert_manager.storage_backend
        fingerprints_path = os.path.join(storage_backend.storage_path,
                                         'sites', 'test-site-1',
                                         'fingerprints',
                                         'example.com__443.json')

        cert_manager.mark_certificate_verified(
            hostname='example.com',
            port=443,
            fingerprints=self.create_certificate_fingerprints(),
            local_site=local_site)

        self.assertTrue(os.path.exists(fingerprints_path))

        with open(fingerprints_path, 'rb') as fp:
            self.assertEqual(json.load(fp), {
                'sha1': TEST_SHA1,
                'sha256': TEST_SHA256,
            })

        # This should also be in cache.
        self.assertEqual(
            cache.get(make_cache_key(
                'rb-ssl-fingerprints:file:1:example.com:443')),
            {
                'sha1': TEST_SHA1,
                'sha256': TEST_SHA256,
            })

    def test_mark_certificate_verified_with_empty(self) -> None:
        """Testing CertificateManager.mark_certificate_verified with empty
        fingerprints
        """
        cert_manager = CertificateManager()

        message = 'One or more SSL certificate fingerprints must be provided.'

        with self.assertRaisesMessage(ValueError, message):
            cert_manager.mark_certificate_verified(
                hostname='example.com',
                port=443,
                fingerprints=CertificateFingerprints())

    def test_remove_certificate_verification(self) -> None:
        """Testing CertificateManager.remove_certificate_verification"""
        cert_manager = CertificateManager()
        storage_backend = cert_manager.storage_backend
        fingerprints_path = os.path.join(storage_backend.storage_path,
                                         'fingerprints',
                                         'example.com__443.json')

        cert_manager.mark_certificate_verified(
            hostname='example.com',
            port=443,
            fingerprints=self.create_certificate_fingerprints())
        cert_manager.remove_certificate_verification(
            hostname='example.com',
            port=443)

        self.assertFalse(os.path.exists(fingerprints_path))

        # This should no longer be in cache.
        self.assertIsNone(cache.get(make_cache_key(
            'rb-ssl-fingerprints:file:example.com:443')))

    def test_remove_certificate_verification_with_local_site(self) -> None:
        """Testing CertificateManager.remove_certificate_verification with
        LocalSite
        """
        local_site = self.create_local_site('test-site-1')

        cert_manager = CertificateManager()
        storage_backend = cert_manager.storage_backend
        fingerprints_path = os.path.join(storage_backend.storage_path,
                                         'sites', 'test-site-1',
                                         'fingerprints',
                                         'example.com__443.json')

        cert_manager.mark_certificate_verified(
            hostname='example.com',
            port=443,
            fingerprints=self.create_certificate_fingerprints(),
            local_site=local_site)
        cert_manager.remove_certificate_verification(
            hostname='example.com',
            port=443,
            local_site=local_site)

        self.assertFalse(os.path.exists(fingerprints_path))

        # This should no longer be in cache.
        self.assertIsNone(cache.get(make_cache_key(
            'rb-ssl-fingerprints:file:1:example.com:443')))

    def test_remove_certificate_verification_with_not_found(self) -> None:
        """Testing CertificateManager.remove_certificate_verification with
        fingerprints not found
        """
        cert_manager = CertificateManager()

        # This should not blow up.
        cert_manager.remove_certificate_verification(
            hostname='missing.example.com',
            port=443)

    def test_remove_certificate_verification_with_local_site_mismatch(
        self,
    ) -> None:
        """Testing CertificateManager.remove_certificate_verification with
        LocalSite mismatch
        """
        local_site1 = self.create_local_site('test-site-1')
        local_site2 = self.create_local_site('test-site-2')

        cert_manager = CertificateManager()
        storage_backend = cert_manager.storage_backend
        fingerprints_path = os.path.join(storage_backend.storage_path,
                                         'sites', 'test-site-1',
                                         'fingerprints',
                                         'example.com__443.json')

        cert_manager.mark_certificate_verified(
            hostname='example.com',
            port=443,
            fingerprints=self.create_certificate_fingerprints(),
            local_site=local_site1)
        cert_manager.remove_certificate_verification(
            hostname='example.com',
            port=443,
            local_site=local_site2)

        self.assertTrue(os.path.exists(fingerprints_path))

        # This should still be in cache.
        self.assertEqual(
            cache.get(make_cache_key(
                'rb-ssl-fingerprints:file:1:example.com:443')),
            {
                'sha1': TEST_SHA1,
                'sha256': TEST_SHA256,
            })

    def test_get_verified_fingerprints(self) -> None:
        """Testing CertificateManager.get_verified_fingerprints"""
        local_site = self.create_local_site('test-site-1')

        cert_manager = CertificateManager()

        cert_manager.mark_certificate_verified(
            hostname='example.com',
            port=443,
            fingerprints=self.create_certificate_fingerprints())

        fingerprints = cert_manager.get_verified_fingerprints(
            hostname='example.com',
            port=443)

        self.assertAttrsEqual(
            fingerprints,
            {
                'sha1': TEST_SHA1,
                'sha256': TEST_SHA256,
            })

        # Make sure it's only accessible on the global site.
        self.assertIsNone(cert_manager.get_verified_fingerprints(
            hostname='example.com',
            port=443,
            local_site=local_site))

    def test_get_verified_fingerprints_with_local_site(self) -> None:
        """Testing CertificateManager.get_verified_fingerprints with LocalSite
        """
        local_site1 = self.create_local_site('test-site-1')
        local_site2 = self.create_local_site('test-site-2')

        cert_manager = CertificateManager()

        cert_manager.mark_certificate_verified(
            hostname='example.com',
            port=443,
            fingerprints=self.create_certificate_fingerprints(),
            local_site=local_site1)

        fingerprints = cert_manager.get_verified_fingerprints(
            hostname='example.com',
            port=443,
            local_site=local_site1)

        self.assertAttrsEqual(
            fingerprints,
            {
                'sha1': TEST_SHA1,
                'sha256': TEST_SHA256,
            })

        # Make sure it's only accessible on local_site1.
        self.assertIsNone(cert_manager.get_verified_fingerprints(
            hostname='example.com',
            port=443))
        self.assertIsNone(cert_manager.get_verified_fingerprints(
            hostname='example.com',
            port=443,
            local_site=local_site2))

    def test_get_verified_fingerprints_with_not_found(self) -> None:
        """Testing CertificateManager.get_verified_fingerprints with not found
        """
        cert_manager = CertificateManager()

        self.assertIsNone(cert_manager.get_verified_fingerprints(
            hostname='missing.example.com',
            port=443))

    def test_get_verified_fingerprints_after_unverify(self) -> None:
        """Testing CertificateManager.get_verified_fingerprints after
        remove_certificate_verification
        """
        cert_manager = CertificateManager()

        cert_manager.mark_certificate_verified(
            hostname='example.com',
            port=443,
            fingerprints=self.create_certificate_fingerprints())
        cert_manager.remove_certificate_verification(
            hostname='example.com',
            port=443)

        self.assertIsNone(cert_manager.get_verified_fingerprints(
            hostname='example.com',
            port=443))

    def test_is_certificate_verified_with_match(self) -> None:
        """Testing CertificateManager.is_certificate_verified with match"""
        cert_manager = CertificateManager()

        cert_manager.mark_certificate_verified(
            hostname='example.com',
            port=443,
            fingerprints=self.create_certificate_fingerprints())

        self.assertTrue(cert_manager.is_certificate_verified(
            hostname='example.com',
            port=443,
            latest_fingerprints=self.create_certificate_fingerprints()))

    def test_is_certificate_verified_with_no_match(self) -> None:
        """Testing CertificateManager.is_certificate_verified with no match"""
        local_site = self.create_local_site('test-site-1')

        cert_manager = CertificateManager()

        cert_manager.mark_certificate_verified(
            hostname='example.com',
            port=443,
            fingerprints=self.create_certificate_fingerprints())

        self.assertFalse(cert_manager.is_certificate_verified(
            hostname='example.com',
            port=443,
            latest_fingerprints=self.create_certificate_fingerprints(
                sha256=TEST_SHA256_2)))
        self.assertFalse(cert_manager.is_certificate_verified(
            hostname='example.com',
            port=443,
            latest_fingerprints=self.create_certificate_fingerprints(),
            local_site=local_site))

    def test_is_certificate_verified_after_unverify(self) -> None:
        """Testing CertificateManager.is_certificate_verified after
        remove_certificate_verification
        """
        cert_manager = CertificateManager()

        cert_manager.mark_certificate_verified(
            hostname='example.com',
            port=443,
            fingerprints=self.create_certificate_fingerprints())
        cert_manager.remove_certificate_verification(
            hostname='example.com',
            port=443)

        self.assertFalse(cert_manager.is_certificate_verified(
            hostname='example.com',
            port=443,
            latest_fingerprints=self.create_certificate_fingerprints()))

    def test_build_ssl_context(self) -> None:
        """Testing CertificateManager.build_ssl_context with defaults"""
        cert_manager = CertificateManager()
        storage_backend = cert_manager.storage_backend

        self.spy_on(ssl.create_default_context,
                    op=kgb.SpyOpReturn(MySSLContext()))

        context = cert_manager.build_ssl_context(hostname='example.com',
                                                 port=443)
        assert isinstance(context, MySSLContext)

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

    def test_build_ssl_context_with_ca_bundle(self) -> None:
        """Testing CertificateManager.build_ssl_context with CA bundles"""
        cert_manager = CertificateManager()
        storage_backend = cert_manager.storage_backend

        self.spy_on(ssl.create_default_context,
                    op=kgb.SpyOpReturn(MySSLContext()))

        cert_manager.add_ca_bundle(
            CertificateBundle(bundle_data=TEST_CERT_BUNDLE_PEM,
                              name='my-certs'))

        context = cert_manager.build_ssl_context(hostname='example.com',
                                                 port=443)
        assert isinstance(context, MySSLContext)

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

    def test_build_ssl_context_with_trust_cert(self) -> None:
        """Testing CertificateManager.build_ssl_context with trust
        certificate
        """
        cert_manager = CertificateManager()
        storage_backend = cert_manager.storage_backend

        self.spy_on(ssl.create_default_context,
                    op=kgb.SpyOpReturn(MySSLContext()))

        cert_manager.add_certificate(
            self.create_certificate(cert_data=TEST_TRUST_CERT_PEM))

        context = cert_manager.build_ssl_context(hostname='example.com',
                                                 port=443)
        assert isinstance(context, MySSLContext)

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
                'certfiles': [],
                'keyfiles': [],
                'passwords': [],
            })

    def test_build_ssl_context_with_client_cert(self) -> None:
        """Testing CertificateManager.build_ssl_context with client
        certificate
        """
        cert_manager = CertificateManager()
        storage_backend = cert_manager.storage_backend

        self.spy_on(ssl.create_default_context,
                    op=kgb.SpyOpReturn(MySSLContext()))

        cert_manager.add_certificate(
            self.create_certificate(purpose=CertPurpose.CLIENT,
                                    cert_data=TEST_CLIENT_CERT_PEM,
                                    key_data=TEST_CLIENT_KEY_PEM))

        context = cert_manager.build_ssl_context(hostname='example.com',
                                                 port=443)
        assert isinstance(context, MySSLContext)

        self.assertAttrsEqual(
            context,
            {
                'cadatas': [],
                'cafiles': [],
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

    def test_build_ssl_context_with_all(self) -> None:
        """Testing CertificateManager.build_ssl_context with CA bundles,
        trust certificates, and client certificates
        """
        cert_manager = CertificateManager()
        storage_backend = cert_manager.storage_backend

        self.spy_on(ssl.create_default_context,
                    op=kgb.SpyOpReturn(MySSLContext()))

        cert_manager.add_ca_bundle(
            CertificateBundle(bundle_data=TEST_CERT_BUNDLE_PEM,
                              name='my-certs'))
        cert_manager.add_certificate(
            self.create_certificate(cert_data=TEST_TRUST_CERT_PEM))
        cert_manager.add_certificate(
            self.create_certificate(purpose=CertPurpose.CLIENT,
                                    cert_data=TEST_CLIENT_CERT_PEM,
                                    key_data=TEST_CLIENT_KEY_PEM))

        context = cert_manager.build_ssl_context(hostname='example.com',
                                                 port=443)
        assert isinstance(context, MySSLContext)

        self.assertAttrsEqual(
            context,
            {
                'cadatas': [],
                'cafiles': [
                    os.path.join(storage_backend.storage_path,
                                 'certs', 'trust', 'example.com__443.crt'),
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

    def test_build_ssl_context_with_local_site(self) -> None:
        """Testing CertificateManager.build_ssl_context with LocalSite"""
        local_site = self.create_local_site('test-site-1')

        cert_manager = CertificateManager()
        storage_backend = cert_manager.storage_backend
        site_storage_path = os.path.join(storage_backend.storage_path, 'sites',
                                         'test-site-1')

        self.spy_on(ssl.create_default_context,
                    op=kgb.SpyOpReturn(MySSLContext()))

        cert_manager.add_certificate(
            self.create_certificate(cert_data=TEST_TRUST_CERT_PEM),
            local_site=local_site,
        )
        cert_manager.add_certificate(
            self.create_certificate(
                purpose=CertPurpose.CLIENT,
                cert_data=TEST_CLIENT_CERT_PEM,
                key_data=TEST_CLIENT_KEY_PEM,
            ),
            local_site=local_site,
        )

        # These should not be included.
        cert_manager.add_certificate(
            self.create_certificate(cert_data=TEST_TRUST_CERT_PEM),
        )
        cert_manager.add_certificate(
            self.create_certificate(
                purpose=CertPurpose.CLIENT,
                cert_data=TEST_CLIENT_CERT_PEM,
                key_data=TEST_CLIENT_KEY_PEM,
            ),
        )

        context = cert_manager.build_ssl_context(hostname='example.com',
                                                 port=443,
                                                 local_site=local_site)
        assert isinstance(context, MySSLContext)

        self.assertAttrsEqual(
            context,
            {
                'cadatas': [],
                'cafiles': [
                    os.path.join(site_storage_path, 'certs', 'trust',
                                 'example.com__443.crt'),
                ],
                'capaths': [
                    os.path.join(site_storage_path, 'cabundles'),
                ],
                'certfiles': [
                    os.path.join(site_storage_path, 'certs', 'client',
                                 'example.com__443.crt'),
                ],
                'keyfiles': [
                    os.path.join(site_storage_path, 'certs', 'client',
                                 'example.com__443.key'),
                ],
                'passwords': [
                    None,
                ],
            })

    def test_build_urlopen_kwargs(self) -> None:
        """Testing CertificateManager.build_urlopen_kwargs with trust
        certificate
        """
        cert_manager = CertificateManager()
        storage_backend = cert_manager.storage_backend

        self.spy_on(ssl.create_default_context,
                    op=kgb.SpyOpReturn(MySSLContext()))

        cert_manager.add_certificate(
            self.create_certificate(cert_data=TEST_TRUST_CERT_PEM))

        kwargs = cert_manager.build_urlopen_kwargs(url='https://example.com')

        self.assertAttrsEqual(
            kwargs.get('context'),
            {
                'cadatas': [],
                'cafiles': [
                    os.path.join(storage_backend.storage_path, 'certs',
                                 'trust', 'example.com__443.crt'),
                ],
                'capaths': [
                    os.path.join(storage_backend.storage_path, 'cabundles'),
                ],
                'certfiles': [],
                'keyfiles': [],
                'passwords': [],
            })

    def test_build_urlopen_kwargs_with_client_cert(self) -> None:
        """Testing CertificateManager.build_urlopen_kwargs with client
        certificate
        """
        cert_manager = CertificateManager()
        storage_backend = cert_manager.storage_backend

        self.spy_on(ssl.create_default_context,
                    op=kgb.SpyOpReturn(MySSLContext()))

        cert_manager.add_certificate(
            self.create_certificate(purpose=CertPurpose.CLIENT,
                                    cert_data=TEST_CLIENT_CERT_PEM,
                                    key_data=TEST_CLIENT_KEY_PEM))

        kwargs = cert_manager.build_urlopen_kwargs(url='https://example.com')

        self.assertAttrsEqual(
            kwargs.get('context'),
            {
                'cadatas': [],
                'cafiles': [],
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

    def test_build_urlopen_kwargs_with_port(self) -> None:
        """Testing CertificateManager.build_urlopen_kwargs with port"""
        cert_manager = CertificateManager()
        storage_backend = cert_manager.storage_backend

        self.spy_on(ssl.create_default_context,
                    op=kgb.SpyOpReturn(MySSLContext()))

        cert_manager.add_certificate(
            self.create_certificate(cert_data=TEST_TRUST_CERT_PEM,
                                    port=8443))

        kwargs = cert_manager.build_urlopen_kwargs(
            url='https://example.com:8443')

        self.assertAttrsEqual(
            kwargs.get('context'),
            {
                'cadatas': [],
                'cafiles': [
                    os.path.join(storage_backend.storage_path, 'certs',
                                 'trust', 'example.com__8443.crt'),
                ],
                'capaths': [
                    os.path.join(storage_backend.storage_path, 'cabundles'),
                ],
                'certfiles': [],
                'keyfiles': [],
                'passwords': [],
            })

    def test_build_urlopen_kwargs_with_non_https(self) -> None:
        """Testing CertificateManager.build_urlopen_kwargs with port"""
        cert_manager = CertificateManager()

        self.spy_on(ssl.create_default_context,
                    op=kgb.SpyOpReturn(MySSLContext()))

        kwargs = cert_manager.build_urlopen_kwargs(url='http://example.com')
        self.assertEqual(kwargs, {})
