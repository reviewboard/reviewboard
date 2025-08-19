"""Unit tests for Hosting Service registration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.http import HttpResponse
from django.urls import NoReverseMatch, path
from djblets.registries.errors import AlreadyRegisteredError, ItemLookupError

from reviewboard.deprecation import RemovedInReviewBoard90Warning
from reviewboard.hostingsvcs.base.hosting_service import BaseHostingService
from reviewboard.hostingsvcs.base.registry import hosting_service_registry
from reviewboard.hostingsvcs.service import (register_hosting_service,
                                             unregister_hosting_service)
from reviewboard.site.urlresolvers import local_site_reverse
from reviewboard.testing import TestCase

if TYPE_CHECKING:
    from django.http import HttpRequest


def hosting_service_url_test_view(
    request: HttpRequest,
    repo_id: int,
) -> HttpResponse:
    """View to test URL pattern addition when registering a hosting service.

    Args:
        request (django.http.HttpRequest):
            The HTTP request.

        repo_id (int):
            The ID of the repository.

    Returns:
        django.http.HttpResponse:
        A fake response.
    """
    return HttpResponse(str(repo_id))


class HostingServiceRegistrationTests(TestCase):
    """Unit tests for Hosting Service registration."""

    class _DummyService(BaseHostingService):
        name = 'DummyService'
        hosting_service_id = 'dummy-service'

    class _DummyServiceWithURLs(BaseHostingService):
        name = 'DummyServiceWithURLs'
        hosting_service_id = 'dummy-service'

        repository_url_patterns = [
            path('hooks/pre-commit/',
                 hosting_service_url_test_view,
                 name='dummy-service-post-commit-hook'),
        ]

    def tearDown(self) -> None:
        """Tear down the test case."""
        super().tearDown()

        # Unregister the service, going back to a default state. It's okay
        # if it fails.
        #
        # This will match whichever service we added for testing.
        try:
            hosting_service_registry.unregister_by_id('dummy-service')
        except ItemLookupError:
            pass

    def test_register_without_urls(self) -> None:
        """Testing HostingService registration"""
        hosting_service_registry.register(self._DummyService)

        with self.assertRaises(AlreadyRegisteredError):
            hosting_service_registry.register(self._DummyService)

    def test_unregister(self) -> None:
        """Testing HostingService unregistration"""
        hosting_service_registry.register(self._DummyService)
        hosting_service_registry.unregister(self._DummyService)

    def test_registration_with_urls(self) -> None:
        """Testing HostingService registration with URLs"""
        hosting_service_registry.register(self._DummyServiceWithURLs)

        self.assertEqual(
            local_site_reverse(
                'dummy-service-post-commit-hook',
                kwargs={
                    'repository_id': 1,
                    'hosting_service_id': 'dummy-service',
                }),
            '/repos/1/dummy-service/hooks/pre-commit/')

        self.assertEqual(
            local_site_reverse(
                'dummy-service-post-commit-hook',
                local_site_name='test-site',
                kwargs={
                    'repository_id': 1,
                    'hosting_service_id': 'dummy-service',
                }),
            '/s/test-site/repos/1/dummy-service/hooks/pre-commit/')

        # Once registered, should not be able to register again.
        with self.assertRaises(AlreadyRegisteredError):
            hosting_service_registry.register(self._DummyServiceWithURLs)

    def test_unregistration_with_urls(self) -> None:
        """Testing HostingService unregistration with URLs"""
        hosting_service_registry.register(self._DummyServiceWithURLs)
        hosting_service_registry.unregister(self._DummyServiceWithURLs)

        with self.assertRaises(NoReverseMatch):
            local_site_reverse(
                'dummy-service-post-commit-hook',
                kwargs={
                    'repository_id': 1,
                    'hosting_service_id': 'dummy-service',
                })

        # Once unregistered, should not be able to unregister again.
        with self.assertRaises(ItemLookupError):
            hosting_service_registry.unregister(self._DummyServiceWithURLs)

    def test_legacy_register_methods(self) -> None:
        """Testing legacy register and unregister methods"""
        message = (
            '`reviewboard.hostingsvcs.service.register_hosting_service()` '
            'has moved to `reviewboard.hostingsvcs.base.registry.'
            'HostingServiceRegistry.register`. The old function is '
            'deprecated and will be removed in Review Board 9.0.'
        )

        with self.assertWarns(RemovedInReviewBoard90Warning, message):
            register_hosting_service('dummy-service', self._DummyService)

        message = (
            '`reviewboard.hostingsvcs.service.unregister_hosting_service()` '
            'has moved to `reviewboard.hostingsvcs.base.registry.'
            'HostingServiceRegistry.unregister_by_id`. The old function is '
            'deprecated and will be removed in Review Board 9.0.'
        )

        with self.assertWarns(RemovedInReviewBoard90Warning, message):
            unregister_hosting_service('dummy-service')
