"""Unit tests for reviewboard.certs.http.urlopen.

Version Added:
    8.1
"""

from __future__ import annotations

import os
from http.client import HTTPConnection
from typing import TYPE_CHECKING
from urllib.request import HTTPHandler, HTTPSHandler, Request

import kgb

from reviewboard.certs.cert import (CertPurpose,
                                    CertificateBundle)
from reviewboard.certs.http import urlopen
from reviewboard.certs.manager import CertificateManager
from reviewboard.certs.tests.testcases import (CaptureSSLMixin,
                                               CertificateTestCase,
                                               MockHTTPResponse,
                                               TEST_CERT_BUNDLE_PEM,
                                               TEST_CLIENT_CERT_PEM,
                                               TEST_CLIENT_KEY_PEM,
                                               TEST_TRUST_CERT_PEM)

if TYPE_CHECKING:
    from reviewboard.site.models import LocalSite


class URLOpenTests(kgb.SpyAgency, CaptureSSLMixin, CertificateTestCase):
    """Unit tests for urlopen.

    Version Added:
        8.1
    """

    def test_with_http(self) -> None:
        """Testing urlopen with http:// URLs"""
        cert_manager = CertificateManager()

        response = urlopen('http://example.com',
                           cert_manager=cert_manager)

        self.assertEqual(response.read(), b'test')

        self.assertSpyCalled(HTTPHandler.http_open)
        self.assertSpyNotCalled(HTTPSHandler.https_open)

    def test_with_https_and_certs_found(self) -> None:
        """Testing urlopen with https:// URLs and certs found in cert manager
        """
        cert_manager = CertificateManager()
        storage_backend = cert_manager.storage_backend
        self._add_cert_state(cert_manager)

        response = urlopen('https://example.com',
                           cert_manager=cert_manager)

        self.assertEqual(response.read(), b'test')

        self.assertSpyNotCalled(HTTPHandler.http_open)
        self.assertSpyCalled(HTTPSHandler.https_open)

        ssl_contexts = self.ssl_contexts
        self.assertEqual(len(ssl_contexts), 1)
        self.assertAttrsEqual(
            ssl_contexts[0],
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

    def test_with_https_and_certs_not_found(self) -> None:
        """Testing urlopen with https:// URLs and certs not found in cert
        manager
        """
        cert_manager = CertificateManager()
        storage_backend = cert_manager.storage_backend

        response = urlopen('https://other.com',
                           cert_manager=cert_manager)

        self.assertEqual(response.read(), b'test')

        self.assertSpyNotCalled(HTTPHandler.http_open)
        self.assertSpyCalled(HTTPSHandler.https_open)

        ssl_contexts = self.ssl_contexts
        self.assertEqual(len(ssl_contexts), 1)
        self.assertAttrsEqual(
            ssl_contexts[0],
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

    def test_with_http_to_https_redirect_with_certs(self) -> None:
        """Testing urlopen with http:// to https:// redirect with certs
        found in cert manager
        """
        self.unspy(HTTPConnection.getresponse)
        self.spy_on(
            HTTPConnection.getresponse,
            owner=HTTPConnection,
            op=kgb.SpyOpReturnInOrder([
                MockHTTPResponse(
                    code=302,
                    reason='Found',
                    headers={
                        'location': 'https://example.com',
                    },
                ),
                MockHTTPResponse(
                    data=b'https result',
                ),
            ]))

        cert_manager = CertificateManager()
        storage_backend = cert_manager.storage_backend
        self._add_cert_state(cert_manager)

        response = urlopen('http://first.int',
                           cert_manager=cert_manager)

        self.assertEqual(response.read(), b'https result')

        self.assertSpyCalled(HTTPHandler.http_open)
        self.assertSpyCalled(HTTPSHandler.https_open)

        ssl_contexts = self.ssl_contexts
        self.assertEqual(len(ssl_contexts), 1)
        self.assertAttrsEqual(
            ssl_contexts[0],
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

    def test_with_https_to_https_redirect(self) -> None:
        """Testing urlopen with https:// to https:// redirect"""
        self.unspy(HTTPConnection.getresponse)
        self.spy_on(
            HTTPConnection.getresponse,
            owner=HTTPConnection,
            op=kgb.SpyOpReturnInOrder([
                MockHTTPResponse(
                    code=302,
                    reason='Found',
                    headers={
                        'location': 'https://example.com',
                    },
                ),
                MockHTTPResponse(
                    data=b'https result',
                ),
            ]))

        cert_manager = CertificateManager()
        storage_backend = cert_manager.storage_backend
        self._add_cert_state(cert_manager)

        response = urlopen('https://first.int',
                           cert_manager=cert_manager)

        self.assertEqual(response.read(), b'https result')

        self.assertSpyNotCalled(HTTPHandler.http_open)
        self.assertSpyCallCount(HTTPSHandler.https_open, 2)

        ssl_contexts = self.ssl_contexts
        self.assertEqual(len(ssl_contexts), 2)
        self.assertAttrsEqual(
            ssl_contexts[0],
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
        self.assertAttrsEqual(
            ssl_contexts[1],
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

    def test_with_http_to_https_redirect_without_certs(self) -> None:
        """Testing urlopen with http:// to https:// redirect with certs
        not found in cert manager
        """
        self.unspy(HTTPConnection.getresponse)
        self.spy_on(
            HTTPConnection.getresponse,
            owner=HTTPConnection,
            op=kgb.SpyOpReturnInOrder([
                MockHTTPResponse(
                    code=302,
                    reason='Found',
                    headers={
                        'location': 'https://other.com',
                    },
                ),
                MockHTTPResponse(
                    data=b'https result',
                ),
            ]))

        cert_manager = CertificateManager()
        storage_backend = cert_manager.storage_backend

        response = urlopen('http://first.int',
                           cert_manager=cert_manager)

        self.assertEqual(response.read(), b'https result')

        self.assertSpyCalled(HTTPHandler.http_open)
        self.assertSpyCalled(HTTPSHandler.https_open)

        ssl_contexts = self.ssl_contexts
        self.assertEqual(len(ssl_contexts), 1)
        self.assertAttrsEqual(
            ssl_contexts[0],
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

    def test_with_request(self) -> None:
        """Testing urlopen with Request object"""
        cert_manager = CertificateManager()

        response = urlopen(Request(url='http://example.com'),
                           cert_manager=cert_manager)

        self.assertEqual(response.read(), b'test')

        self.assertSpyCalled(HTTPHandler.http_open)
        self.assertSpyNotCalled(HTTPSHandler.https_open)
        self.assertEqual(self.ssl_contexts, [])

    def test_with_local_site_with_cert_found(self) -> None:
        """Testing urlopen with LocalSite and certs found in cert manager"""
        local_site = self.create_local_site(name='test-site-1')

        cert_manager = CertificateManager()
        storage_backend = cert_manager.storage_backend
        self._add_cert_state(cert_manager,
                             local_site=local_site)

        response = urlopen(Request(url='https://example.com'),
                           local_site=local_site)

        self.assertEqual(response.read(), b'test')

        self.assertSpyNotCalled(HTTPHandler.http_open)
        self.assertSpyCalled(HTTPSHandler.https_open)

        base_path = os.path.join(storage_backend.storage_path,
                                 'sites', 'test-site-1',)

        ssl_contexts = self.ssl_contexts
        self.assertEqual(len(ssl_contexts), 1)
        self.assertAttrsEqual(
            ssl_contexts[0],
            {
                'cadatas': [],
                'cafiles': [
                    os.path.join(base_path, 'certs', 'trust',
                                 'example.com__443.crt'),
                ],
                'capaths': [
                    os.path.join(base_path, 'cabundles'),
                ],
                'certfiles': [
                    os.path.join(base_path, 'certs', 'client',
                                 'example.com__443.crt'),
                ],
                'keyfiles': [
                    os.path.join(base_path, 'certs', 'client',
                                 'example.com__443.key'),
                ],
                'passwords': [
                    None,
                ],
            })

    def test_with_local_site_with_cert_not_found(self) -> None:
        """Testing urlopen with LocalSite and certs found in cert manager"""
        local_site = self.create_local_site(name='test-site-1')

        cert_manager = CertificateManager()
        storage_backend = cert_manager.storage_backend

        # Add into the global state.
        self._add_cert_state(cert_manager)

        response = urlopen(Request(url='https://example.com'),
                           cert_manager=cert_manager,
                           local_site=local_site)

        self.assertEqual(response.read(), b'test')

        self.assertSpyNotCalled(HTTPHandler.http_open)
        self.assertSpyCalled(HTTPSHandler.https_open)

        base_path = os.path.join(storage_backend.storage_path,
                                 'sites', 'test-site-1',)

        ssl_contexts = self.ssl_contexts
        self.assertEqual(len(ssl_contexts), 1)
        self.assertAttrsEqual(
            ssl_contexts[0],
            {
                'cadatas': [],
                'cafiles': [],
                'capaths': [
                    os.path.join(base_path, 'cabundles'),
                ],
                'certfiles': [],
                'keyfiles': [],
                'passwords': [],
            })

    def _add_cert_state(
        self,
        cert_manager: CertificateManager,
        *,
        local_site: (LocalSite | None) = None,
    ) -> None:
        """Add testing certificate state to a CertificateManager.

        Args:
            cert_manager (reviewboard.certs.manager.CertificateManager):
                The certificate manager to add to.

            local_site (reviewboard.site.models.LocalSite, optional):
                The Local Site to bind the state to.
        """
        cert_manager.add_ca_bundle(
            CertificateBundle(
                bundle_data=TEST_CERT_BUNDLE_PEM,
                name='my-certs',
            ),
            local_site=local_site,
        )
        cert_manager.add_certificate(
            self.create_certificate(
                cert_data=TEST_TRUST_CERT_PEM,
            ),
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
