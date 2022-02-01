"""Unit tests for reviewboard.accounts.middleware.X509AuthMiddleware."""

from __future__ import unicode_literals

from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.middleware import SessionMiddleware
from django.test.client import RequestFactory
from djblets.siteconfig.models import SiteConfiguration

from reviewboard.accounts.backends import X509Backend
from reviewboard.accounts.middleware import X509AuthMiddleware
from reviewboard.testing import TestCase


class X509AuthMiddlewareTests(TestCase):
    """Unit tests for reviewboard.accounts.middleware.X509AuthMiddleware."""

    fixtures = ['test_users']

    def setUp(self):
        super(X509AuthMiddlewareTests, self).setUp()

        self.middleware = X509AuthMiddleware()
        self.siteconfig = SiteConfiguration.objects.get_current()

        self.enabled_settings = {
            'auth_backend': X509Backend.backend_id,
        }

        self.request = RequestFactory().get('/')
        self.request.user = AnonymousUser()
        self.request.is_secure = lambda: True

        SessionMiddleware().process_request(self.request)

    def test_process_request_without_enabled(self):
        """Testing X509AuthMiddleware.process_request without backend enabled
        """
        self.request.environ['SSL_CLIENT_S_DN_CN'] = 'doc'

        result = self.middleware.process_request(self.request)

        self.assertIsNone(result)
        self.assertFalse(self.request.user.is_authenticated())

    def test_process_request_with_enabled_and_no_username(self):
        """Testing X509AuthMiddleware.process_request with backend enabled and
        no username environment variable present
        """
        with self.siteconfig_settings(self.enabled_settings):
            result = self.middleware.process_request(self.request)

        self.assertIsNone(result)
        self.assertFalse(self.request.user.is_authenticated())

    def test_process_request_with_enabled_and_username(self):
        """Testing X509AuthMiddleware.process_request with backend enabled and
        username environment variable present
        """
        self.request.environ['SSL_CLIENT_S_DN_CN'] = 'doc'

        with self.siteconfig_settings(self.enabled_settings):
            result = self.middleware.process_request(self.request)

        self.assertIsNone(result)
        self.assertTrue(self.request.user.is_authenticated())
        self.assertEqual(self.request.user.username, 'doc')
