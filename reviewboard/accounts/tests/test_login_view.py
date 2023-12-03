"""Unit tests for reviewboard.accounts.views.LoginView.

Version Added:
    5.0.5
"""

from reviewboard.site.urlresolvers import local_site_reverse
from reviewboard.testing import TestCase


class LoginViewTests(TestCase):
    """Unit tests for reviewboard.accounts.views.LoginView.

    Version Added:
        5.0.5
    """

    fixtures = ['test_users']

    def test_login_with_redirect(self) -> None:
        """Testing LoginView GET with a local redirect URL"""
        rsp = self.client.get(
            local_site_reverse('login'),
            {
                'next': '/users?foo=1&bar=baz'
            })
        context = rsp.context

        self.assertEqual(context['next'], '/users?foo=1&bar=baz')

    def test_get_client_web_login(self) -> None:
        """Testing LoginView GET sets the redirect field to the client web
        login page when the request indicates the client web login flow and the
        flow is enabled
        """
        settings = {
            'client_web_login': True,
        }
        client_login_url = local_site_reverse('client-login')

        with self.siteconfig_settings(settings):
            rsp = self.client.get(
                local_site_reverse('login'),
                {
                    'client-name': 'TestClient',
                    'client-url': 'http://localhost:8080/test/',
                })

        context = rsp.context

        self.assertEqual(context['client_name'], 'TestClient')
        self.assertEqual(context['client_url'], 'http://localhost:8080/test/')
        self.assertEqual(context['next'],
                         (f'{client_login_url}?client-name=TestClient'
                          '&client-url=http://localhost:8080/test/'))

    def test_get_client_web_login_with_redirect(self) -> None:
        """Testing LoginView GET with the client web login flow encodes
        and passes along a redirect URL if one was given
        """
        settings = {
            'client_web_login': True,
        }
        client_login_url = local_site_reverse('client-login')

        with self.siteconfig_settings(settings):
            rsp = self.client.get(
                local_site_reverse('login'),
                {
                    'client-name': 'TestClient',
                    'client-url': 'http://localhost:8080/test/',
                    'next': 'http://localhost:8080/page?foo=1',
                })

        context = rsp.context

        self.assertEqual(context['client_name'], 'TestClient')
        self.assertEqual(context['client_url'], 'http://localhost:8080/test/')
        self.assertEqual(
            context['next'],
            (f'{client_login_url}?client-name=TestClient'
             '&client-url=http://localhost:8080/test/'
             '&next=http%3A//localhost%3A8080/page%3Ffoo%3D1'))

    def test_get_client_web_login_logged_in(self) -> None:
        """Testing LoginView GET redirects to the client web login
        confirmation page when the request indicates the client web login
        flow and the flow is enabled
        """
        settings = {
            'client_web_login': True,
        }
        client_login_confirm_url = local_site_reverse('client-login-confirm')

        self.client.login(username='doc', password='doc')

        with self.siteconfig_settings(settings):
            rsp = self.client.get(
                local_site_reverse('login'),
                {
                    'client-name': 'TestClient',
                    'client-url': 'http://localhost:8080/test/',
                })

        self.assertRedirects(
            rsp,
            (f'{client_login_confirm_url}?client-name=TestClient'
             '&client-url=http://localhost:8080/test/'))

    def test_get_client_web_login_false(self) -> None:
        """Testing LoginView GET does not set the redirect field to the
        client web login page when the request indicates the client web login
        flow and the flow is not enabled
        """
        settings = {
            'client_web_login': False,
        }

        client_login_url = local_site_reverse('client-login')

        with self.siteconfig_settings(settings):
            rsp = self.client.get(
                local_site_reverse('login'),
                {
                    'client-name': 'TestClient',
                    'client-url': 'http://localhost:8080/test/',
                })

        context = rsp.context

        self.assertNotIn('client_name', context)
        self.assertNotIn('client_url', context)
        self.assertNotEqual(context['next'],
                            (f'{client_login_url}?client-name=TestClient'
                             '&client-url=http://localhost:8080/test/'))

    def test_get_with_redirect_url(self) -> None:
        """Testing LoginView GET with a next= URL"""
        login_url = local_site_reverse('login')

        rsp = self.client.get(
            login_url,
            {
                'next': '/test/',
            })

        self.assertEqual(rsp.context['next'], '/test/')

    def test_get_with_redirect_login_loop(self) -> None:
        """Testing LoginView GET breaks a redirect login loop to the same login
        URL
        """
        login_url = local_site_reverse('login')

        rsp = self.client.get(
            login_url,
            {
                'next': login_url,
            })

        self.assertEqual(rsp.context['next'], '')

    def test_get_with_redirect_logout_loop(self) -> None:
        """Testing LoginView GET breaks a redirect login -> logout loop"""
        rsp = self.client.get(
            local_site_reverse('login'),
            {
                'next': local_site_reverse('logout'),
            })

        self.assertEqual(rsp.context['next'], '')

    def test_get_with_authenticated(self) -> None:
        """Testing LoginView GET when authenticated"""
        client = self.client
        client.login(username='doc',
                     password='doc')

        rsp = client.get(local_site_reverse('login'))
        self.assertRedirects(rsp,
                             local_site_reverse('root'),
                             fetch_redirect_response=False)

    def test_get_with_authenticated_and_next(self) -> None:
        """Testing LoginView GET when authenticated and custom next= URL"""
        client = self.client
        client.login(username='doc',
                     password='doc')

        rsp = client.get(
            local_site_reverse('login'),
            {
                'next': '/test/',
            })

        self.assertRedirects(rsp,
                             '/test/',
                             fetch_redirect_response=False)

    def test_get_with_authenticated_and_login_loop(self) -> None:
        """Testing LoginView GET when authenticated and login loop"""
        client = self.client
        client.login(username='doc',
                     password='doc')

        login_url = local_site_reverse('login')

        rsp = client.get(
            login_url,
            {
                'next': login_url,
            })

        self.assertRedirects(rsp,
                             local_site_reverse('root'),
                             fetch_redirect_response=False)

    def test_get_with_authenticated_and_logout_loop(self) -> None:
        """Testing LoginView GET when authenticated and logout loop"""
        client = self.client
        client.login(username='doc',
                     password='doc')

        rsp = client.get(
            local_site_reverse('login'),
            {
                'next': local_site_reverse('logout'),
            })

        self.assertRedirects(rsp,
                             local_site_reverse('root'),
                             fetch_redirect_response=False)
