"""Unit tests for reviewboard.admin.siteconfig."""

import os

from django.conf import settings
from django.urls import reverse
from djblets.siteconfig.models import SiteConfiguration

from reviewboard.admin.siteconfig import load_site_config
from reviewboard.testing.testcase import TestCase


class LoadSiteConfigTests(TestCase):
    """Unit tests for reviewboard.admin.siteconfig.load_site_config."""

    def setUp(self):
        super(LoadSiteConfigTests, self).setUp()

        self.siteconfig = SiteConfiguration.objects.get_current()

    def test_with_site_domain_method_http(self):
        """Testing load_site_config with site_domain_method=http"""
        self.siteconfig.set('site_domain_method', 'http')
        self.siteconfig.save()
        load_site_config()

        self.assertEqual(str(os.environ.get(str('HTTPS'))), str('off'))
        self.assertFalse(getattr(settings, 'CSRF_COOKIE_SECURE', None))

        # Ensure that CSRF cookie flags are set correctly.
        self.create_user(username='test-user',
                         password='test-user')

        login_url = reverse('login')
        response = self.client.get(login_url)
        csrf_cookie = response.cookies.get(settings.CSRF_COOKIE_NAME)
        self.assertIsNotNone(csrf_cookie)
        self.assertFalse(csrf_cookie['secure'])

        # Ensure that session cookie flags are set correctly.
        response = self.client.post(
            reverse('login'),
            {
                'username': 'test-user',
                'password': 'test-user',
            })

        session_cookie = response.cookies.get(settings.SESSION_COOKIE_NAME)
        self.assertIsNotNone(session_cookie)
        self.assertFalse(session_cookie['secure'])

    def test_with_site_domain_method_https(self):
        """Testing load_site_config with site_domain_method=https"""
        self.siteconfig.set('site_domain_method', 'https')
        self.siteconfig.save()
        load_site_config()

        self.assertEqual(str(os.environ.get(str('HTTPS'))), str('on'))
        self.assertTrue(getattr(settings, 'CSRF_COOKIE_SECURE', None))

        # Ensure that CSRF cookie flags are set correctly.
        login_url = reverse('login')

        self.create_user(username='test-user',
                         password='test-user')

        response = self.client.get(login_url, secure=True)
        csrf_cookie = response.cookies.get(settings.CSRF_COOKIE_NAME)
        self.assertIsNotNone(csrf_cookie)
        self.assertTrue(csrf_cookie['secure'])

        # Ensure that session cookie flags are set correctly.
        response = self.client.post(
            login_url,
            {
                'username': 'test-user',
                'password': 'test-user',
            },
            secure=True)

        session_cookie = response.cookies.get(settings.SESSION_COOKIE_NAME)
        self.assertIsNotNone(session_cookie)
        self.assertTrue(session_cookie['secure'])
