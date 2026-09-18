"""Unit tests for reviewboard.extensions.hooks.SSOBackendHook.

Version Added:
    9.0
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.http import HttpResponse
from django.urls import NoReverseMatch, path, reverse

from reviewboard.accounts.sso.backends import sso_backends
from reviewboard.accounts.sso.backends.base import BaseSSOBackend
from reviewboard.extensions.hooks import SSOBackendHook
from reviewboard.extensions.tests.testcases import BaseExtensionHookTestCase

if TYPE_CHECKING:
    from django.http import HttpRequest
    from django.urls import URLPattern


def _test_view(
    request: HttpRequest,
    backend_id: str,
) -> HttpResponse:
    return HttpResponse(backend_id)


class TestSSOBackend(BaseSSOBackend):
    """An SSO backend with a single URL."""

    backend_id = 'test-sso'
    name = 'Test SSO'

    @property
    def urls(self) -> list[URLPattern]:
        """The URLs for the backend."""
        return [
            path('start/', _test_view, name='start'),
        ]


class SSOBackendHookTests(BaseExtensionHookTestCase):
    """Testing SSOBackendHook."""

    def test_register(self) -> None:
        """Testing SSOBackendHook initializing"""
        backend = TestSSOBackend()
        SSOBackendHook(self.extension, backend)

        self.assertIs(sso_backends.get('backend_id', 'test-sso'), backend)
        self.assertEqual(
            reverse('sso:test-sso:start', kwargs={'backend_id': 'test-sso'}),
            '/account/sso/test-sso/start/')

    def test_unregister(self) -> None:
        """Testing SSOBackendHook uninitializing"""
        hook = SSOBackendHook(self.extension, TestSSOBackend())
        hook.disable_hook()

        self.assertIsNone(sso_backends.get('backend_id', 'test-sso'))

        with self.assertRaises(NoReverseMatch):
            reverse('sso:test-sso:start', kwargs={'backend_id': 'test-sso'})
