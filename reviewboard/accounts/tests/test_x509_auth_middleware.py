"""Unit tests for reviewboard.accounts.middleware.x509_auth_middleware."""

from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.middleware import SessionMiddleware
from django.http import HttpResponse
from django.test.client import RequestFactory
from djblets.siteconfig.models import SiteConfiguration

from reviewboard.accounts.backends import X509Backend
from reviewboard.accounts.middleware import x509_auth_middleware
from reviewboard.testing import TestCase


class X509AuthMiddlewareTests(TestCase):
    """Unit tests for reviewboard.accounts.middleware.x509_auth_middleware."""

    fixtures = ['test_users']

    def setUp(self):
        super(X509AuthMiddlewareTests, self).setUp()

        self.middleware = SessionMiddleware(
            x509_auth_middleware(
                lambda request: HttpResponse('')))
        self.siteconfig = SiteConfiguration.objects.get_current()

        self.enabled_settings = {
            'auth_backend': X509Backend.backend_id,
        }

        self.request = RequestFactory().get('/')
        self.request.user = AnonymousUser()
        self.request.is_secure = lambda: True

    def test_process_request_without_enabled(self):
        """Testing x509_auth_middleware without backend enabled
        """
        self.request.environ['SSL_CLIENT_S_DN_CN'] = 'doc'

        self.middleware(self.request)

        self.assertFalse(self.request.user.is_authenticated)

    def test_process_request_with_enabled_and_no_username(self):
        """Testing x509_auth_middleware with backend enabled and
        no username environment variable present
        """
        with self.siteconfig_settings(self.enabled_settings):
            self.middleware(self.request)

        self.assertFalse(self.request.user.is_authenticated)

    def test_process_request_with_enabled_and_username(self):
        """Testing x509_auth_middleware with backend enabled and
        username environment variable present
        """
        self.request.environ['SSL_CLIENT_S_DN_CN'] = 'doc'

        with self.siteconfig_settings(self.enabled_settings):
            self.middleware(self.request)

        self.assertTrue(self.request.user.is_authenticated)
        self.assertEqual(self.request.user.username, 'doc')
