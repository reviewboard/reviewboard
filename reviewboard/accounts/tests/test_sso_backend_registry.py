"""Unit tests for the SSO backend registry."""

from __future__ import annotations

import kgb
from django.http import HttpResponse
from django.urls import NoReverseMatch, path, reverse
from djblets.registries import registry as djblets_registry
from djblets.registries.errors import AlreadyRegisteredError, ItemLookupError
from importlib_metadata import EntryPoint

from reviewboard.accounts.sso.backends import sso_backends
from reviewboard.accounts.sso.backends.base import BaseSSOBackend
from reviewboard.testing import TestCase


def backend_test_view(request, backend_id):
    return HttpResponse(str(backend_id))


class EntryPointBackend(BaseSSOBackend):
    """A backend loaded through a fake entry point."""

    backend_id = 'entry-point-backend'
    name = 'Entry Point Backend'


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


class SSOBackendRegistryEntryPointTests(kgb.SpyAgency, TestCase):
    """Unit tests for loading SSO backends from entry points."""

    def tearDown(self) -> None:
        """Tear down the test case."""
        super().tearDown()

        # Drop any backends loaded from fake entry points. The registry will
        # repopulate with the real backends on next access.
        sso_backends.reset()

    def test_get_defaults_with_entry_point(self) -> None:
        """Testing SSOBackendRegistry.get_defaults with an entry point"""
        self._spy_entry_points(EntryPoint(
            name='entry-point-backend',
            value='reviewboard.accounts.tests.test_sso_backend_registry:'
                  'EntryPointBackend',
            group='reviewboard.sso_backends'))

        sso_backends.reset()

        backend = sso_backends.get('backend_id', 'entry-point-backend')
        self.assertIsInstance(backend, EntryPointBackend)

        # The built-in backends must still be present.
        self.assertIsNotNone(sso_backends.get('backend_id', 'saml'))

    def test_get_defaults_with_entry_point_error(self) -> None:
        """Testing SSOBackendRegistry.get_defaults with an entry point that
        fails to load
        """
        self._spy_entry_points(EntryPoint(
            name='bad-backend',
            value='reviewboard.accounts.tests.test_sso_backend_registry:'
                  'MissingBackend',
            group='reviewboard.sso_backends'))

        sso_backends.reset()

        with self.assertLogs(logger='djblets.registries.registry',
                             level='ERROR') as logs:
            self.assertIsNotNone(sso_backends.get('backend_id', 'saml'))

        self.assertEqual(len(logs.output), 1)
        self.assertIn('Error loading SSO backend bad-backend', logs.output[0])
        self.assertIsNone(sso_backends.get('backend_id', 'bad-backend'))

    def _spy_entry_points(
        self,
        entry_point: EntryPoint,
    ) -> None:
        """Fake the SSO backend entry points.

        Other entry point groups are left alone.

        Args:
            entry_point (importlib_metadata.EntryPoint):
                The entry point to return for ``reviewboard.sso_backends``.
        """
        def _entry_points(*, group: str, **kwargs) -> list[EntryPoint]:
            if group == 'reviewboard.sso_backends':
                return [entry_point]

            return djblets_registry.entry_points.call_original(group=group,
                                                               **kwargs)

        self.spy_on(djblets_registry.entry_points,
                    call_fake=_entry_points)
