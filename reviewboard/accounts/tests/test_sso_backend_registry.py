"""Unit tests for the SSO backend registry."""

from django.http import HttpResponse
from django.urls import NoReverseMatch, path, reverse
from djblets.registries.errors import AlreadyRegisteredError, ItemLookupError

from reviewboard.accounts.sso.backends import sso_backends
from reviewboard.accounts.sso.backends.base import BaseSSOBackend
from reviewboard.testing import TestCase


def backend_test_view(request, backend_id):
    return HttpResponse(str(backend_id))


class SSOBackendRegistryTests(TestCase):
    """Unit tests for the SSO backend registry."""

    class DummyBackend(BaseSSOBackend):
        backend_id = 'dummy'
        name = 'Dummy'

    class DummyBackendWithURLs(BaseSSOBackend):
        backend_id = 'dummy-with-urls'
        name = 'DummyWithURLs'

        @property
        def urls(self):
            return [
                path('sso-endpoint/',
                     backend_test_view,
                     name='dummy-backend-sso-endpoint')
            ]

    def setUp(self):
        """Set up the test case."""
        self.dummy_backend = self.DummyBackend()
        self.dummy_backend_with_urls = self.DummyBackendWithURLs()

    def tearDown(self):
        """Tear down the test case."""
        super(SSOBackendRegistryTests, self).tearDown()

        try:
            sso_backends.unregister(self.dummy_backend)
        except ItemLookupError:
            pass

        try:
            sso_backends.unregister(self.dummy_backend_with_urls)
        except ItemLookupError:
            pass

    def test_register_without_urls(self):
        """Testing SSO backend registration"""
        sso_backends.register(self.dummy_backend)

        with self.assertRaises(AlreadyRegisteredError):
            sso_backends.register(self.dummy_backend)

    def test_unregister_without_urls(self):
        """Testing SSO backend unregistration"""
        sso_backends.register(self.dummy_backend)
        sso_backends.unregister(self.dummy_backend)

    def test_register_with_urls(self):
        """Testing SSO backend registration with URLs"""
        sso_backends.register(self.dummy_backend_with_urls)

        self.assertEqual(
            reverse(
                'sso:dummy-with-urls:dummy-backend-sso-endpoint',
                kwargs={
                    'backend_id': 'dummy-with-urls',
                }),
            '/account/sso/dummy-with-urls/sso-endpoint/')

        with self.assertRaises(AlreadyRegisteredError):
            sso_backends.register(self.dummy_backend_with_urls)

    def test_unregister_with_urls(self):
        """Testing SSO backend registration with URLs"""
        sso_backends.register(self.dummy_backend_with_urls)
        sso_backends.unregister(self.dummy_backend_with_urls)

        with self.assertRaises(NoReverseMatch):
            reverse(
                'sso:dummy-with-urls:dummy-backend-sso-endpoint',
                kwargs={
                    'backend_id': 'dummy-with-urls',
                })
