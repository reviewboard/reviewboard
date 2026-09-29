"""Unit tests for reviewboard.accounts.views.ClientLoginConfirmationView.

Version Added:
    5.0.5
"""

from __future__ import annotations

from reviewboard.site.urlresolvers import local_site_reverse
from reviewboard.testing import TestCase


class ClientLoginConfirmationViewTests(TestCase):
    """Unit tests for reviewboard.accounts.views.ClientLoginConfirmationView.

    Version Added:
        5.0.5
    """

    fixtures = ['test_users']

    #: The URL to the logout page.
    logout_url = local_site_reverse('logout')

    def test_get(self) -> None:
        """Testing ClientLoginConfirmationView GET"""
        self.client.login(username='doc', password='doc')
        settings = {
            'client_web_login': True,
        }

        with self.siteconfig_settings(settings):
            rsp = self.client.get(
                local_site_reverse('client-login-confirm'),
                {
                    'client-name': 'TestClient',
                    'client-url': 'http://localhost:1234/test/',
                })

        context = rsp.context

        self.assertEqual(context['client_name'], 'TestClient')
        self.assertEqual(context['client_url'], 'http://localhost:1234/test/')
        self.assertEqual(
            context['client_login_url'],
            '/account/client-login/?client-name=TestClient'
            '&client-url=http%3A%2F%2Flocalhost%3A1234%2Ftest%2F')
        self.assertEqual(
            context['logout_url'],
            (f'{self.logout_url}?next=%2Faccount%2Flogin%2F'
             '%3Fclient-name%3DTestClient'
             '%26client-url%3Dhttp%253A%252F%252Flocalhost%253A1234'
             '%252Ftest%252F'))
        self.assertEqual(context['username'], 'doc')

    def test_get_with_redirect(self) -> None:
        """Testing ClientLoginConfirmationView GET with a redirect URL"""
        self.client.login(username='doc', password='doc')
        settings = {
            'client_web_login': True,
        }

        with self.siteconfig_settings(settings):
            rsp = self.client.get(
                local_site_reverse('client-login-confirm'),
                {
                    'client-name': 'TestClient',
                    'client-url': 'http://localhost:1234/test/',
                    'next': 'http://localhost:1234/page?foo=1',
                })

        context = rsp.context

        self.assertEqual(context['client_name'], 'TestClient')
        self.assertEqual(context['client_url'], 'http://localhost:1234/test/')
        self.assertEqual(
            context['client_login_url'],
            '/account/client-login/?client-name=TestClient'
            '&client-url=http%3A%2F%2Flocalhost%3A1234%2Ftest%2F'
            '&next=http%3A%2F%2Flocalhost%3A1234%2Fpage%3Ffoo%3D1')

        # The client redirect part of the URL is encoded twice
        # in order to preserve any of its query parameters.
        self.assertEqual(
            context['logout_url'],
            (f'{self.logout_url}?next=%2Faccount%2Flogin%2F'
             '%3Fclient-name%3DTestClient'
             '%26client-url%3Dhttp%253A%252F%252Flocalhost%253A1234'
             '%252Ftest%252F'
             '%26next%3Dhttp%253A%252F%252Flocalhost%253A1234'
             '%252Fpage%253Ffoo%253D1'))
        self.assertEqual(context['username'], 'doc')

    def test_get_with_unsafe_redirect(self) -> None:
        """Testing ClientLoginConfirmationView GET with an unsafe
        redirect URL
        """
        self.client.login(username='doc', password='doc')
        settings = {
            'client_web_login': True,
        }

        with self.siteconfig_settings(settings):
            rsp = self.client.get(
                local_site_reverse('client-login-confirm'),
                {
                    'client-name': 'TestClient',
                    'client-url': 'http://localhost:1234/test/',
                    'next': 'http://unsafe-site/page?foo=1',
                })

        context = rsp.context

        self.assertEqual(context['client_name'], 'TestClient')
        self.assertEqual(context['client_url'], 'http://localhost:1234/test/')
        self.assertEqual(
            context['client_login_url'],
            '/account/client-login/?client-name=TestClient'
            '&client-url=http%3A%2F%2Flocalhost%3A1234%2Ftest%2F')
        self.assertEqual(
            context['logout_url'],
            (f'{self.logout_url}?next=%2Faccount%2Flogin%2F'
             '%3Fclient-name%3DTestClient'
             '%26client-url%3Dhttp%253A%252F%252Flocalhost%253A1234'
             '%252Ftest%252F'))
        self.assertEqual(context['username'], 'doc')

    def test_get_with_with_invalid_client_url(self) -> None:
        """Testing ClientLoginConfirmationView GET with a client URL that
        has an invalid port
        """
        self.client.login(username='doc', password='doc')
        settings = {
            'client_web_login': True,
        }

        with self.siteconfig_settings(settings):
            rsp = self.client.get(
                local_site_reverse('client-login-confirm'),
                {
                    'client-name': 'TestClient',
                    'client-url': 'http://localhost:abc/',
                })

        context = rsp.context

        self.assertEqual(rsp.status_code, 200)
        self.assertFalse(context['client_allowed'])
        self.assertEqual(context['client_name'], 'TestClient')
        self.assertEqual(context['client_url'], 'http://localhost:abc/')

    def test_get_unauthenticated(self) -> None:
        """Testing ClientLoginConfirmationView GET redirects to the
        login page when a user is not logged in
        """
        settings = {
            'client_web_login': True,
        }

        with self.siteconfig_settings(settings):
            rsp = self.client.get(
                local_site_reverse('client-login-confirm'),
                {
                    'client-name': 'TestClient',
                    'client-url': 'http://localhost:1234/test/',
                })

        self.assertEqual(rsp.status_code, 302)

    def test_get_client_web_login_false(self) -> None:
        """Testing ClientLoginConfirmationView GET with the client
        web login flow disabled
        """
        settings = {
            'client_web_login': False,
        }

        with self.siteconfig_settings(settings):
            rsp = self.client.get(
                local_site_reverse('client-login-confirm'),
                {
                    'client-name': 'TestClient',
                    'client-url': 'http://localhost:1234/test/',
                })

        self.assertEqual(rsp.status_code, 404)

    def test_post(self) -> None:
        """Testing ClientLoginConfirmationView POST"""
        self.client.login(username='doc', password='doc')
        settings = {
            'client_web_login': True,
        }

        with self.siteconfig_settings(settings):
            rsp = self.client.post(
                local_site_reverse('client-login-confirm'),
                {
                    'client-name': 'TestClient',
                    'client-url': 'http://localhost:1234/test/',
                })

        self.assertEqual(rsp.status_code, 405)
