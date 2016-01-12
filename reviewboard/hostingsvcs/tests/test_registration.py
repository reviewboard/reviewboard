from __future__ import unicode_literals

from django.conf.urls import patterns, url
from django.core.urlresolvers import NoReverseMatch
from django.http import HttpResponse

from reviewboard.hostingsvcs.service import (HostingService,
                                             register_hosting_service,
                                             unregister_hosting_service)
from reviewboard.site.urlresolvers import local_site_reverse
from reviewboard.testing import TestCase


def hosting_service_url_test_view(request, repo_id):
    """View to test URL pattern addition when registering a hosting service"""
    return HttpResponse(str(repo_id))


class HostingServiceRegistrationTests(TestCase):
    """Unit tests for Hosting Service registration."""

    class DummyService(HostingService):
        name = 'DummyService'

    class DummyServiceWithURLs(HostingService):
        name = 'DummyServiceWithURLs'

        repository_url_patterns = patterns(
            '',

            url(r'^hooks/pre-commit/$', hosting_service_url_test_view,
                name='dummy-service-post-commit-hook'),
        )

    def tearDown(self):
        super(HostingServiceRegistrationTests, self).tearDown()

        # Unregister the service, going back to a default state. It's okay
        # if it fails.
        #
        # This will match whichever service we added for testing.
        try:
            unregister_hosting_service('dummy-service')
        except KeyError:
            pass

    def test_register_without_urls(self):
        """Testing HostingService registration"""
        register_hosting_service('dummy-service', self.DummyService)

        with self.assertRaises(KeyError):
            register_hosting_service('dummy-service', self.DummyService)

    def test_unregister(self):
        """Testing HostingService unregistration"""
        register_hosting_service('dummy-service', self.DummyService)
        unregister_hosting_service('dummy-service')

    def test_registration_with_urls(self):
        """Testing HostingService registration with URLs"""
        register_hosting_service('dummy-service', self.DummyServiceWithURLs)

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

        # Once registered, should not be able to register again
        with self.assertRaises(KeyError):
            register_hosting_service('dummy-service',
                                     self.DummyServiceWithURLs)

    def test_unregistration_with_urls(self):
        """Testing HostingService unregistration with URLs"""
        register_hosting_service('dummy-service', self.DummyServiceWithURLs)
        unregister_hosting_service('dummy-service')

        with self.assertRaises(NoReverseMatch):
            local_site_reverse(
                'dummy-service-post-commit-hook',
                kwargs={
                    'repository_id': 1,
                    'hosting_service_id': 'dummy-service',
                }),

        # Once unregistered, should not be able to unregister again
        with self.assertRaises(KeyError):
            unregister_hosting_service('dummy-service')
