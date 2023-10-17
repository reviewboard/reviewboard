"""Unit tests for reviewboard.accounts.views.ClientLoginView.

Version Added:
    5.0.5
"""

import datetime
from typing import Optional
from urllib.parse import quote

import kgb
from django.contrib.auth.models import User
from django.template import Context
from django.utils import timezone
from django.utils.html import escape
from djblets.webapi.errors import WebAPITokenGenerationError

from reviewboard.site.urlresolvers import local_site_reverse
from reviewboard.testing import TestCase
from reviewboard.webapi.models import WebAPIToken


class ClientLoginViewTests(kgb.SpyAgency, TestCase):
    """Unit tests for reviewboard.accounts.views.ClientLoginView.

    Version Added:
        5.0.5
    """

    fixtures = ['test_users']

    def test_get(self) -> None:
        """Testing ClientLoginView GET builds a payload containing
        authentication data when the user is logged in and the client web
        login flow is enabled
        """
        self.spy_on(timezone.now, op=kgb.SpyOpReturn(
            timezone.make_aware(datetime.datetime(2023, 5, 20))))

        self.client.login(username='doc', password='doc')
        settings = {
            'client_web_login': True,
            'client_token_expiration': 5
        }

        with self.siteconfig_settings(settings):
            rsp = self.client.get(
                local_site_reverse('client-login'),
                {
                    'client-name': 'TestClient',
                    'client-url': 'http://localhost:1234/test/',
                })

        self._assert_context_equals(
            rsp.context,
            client_allowed=True,
            client_name='TestClient',
            client_url='http://localhost:1234/test/',
            username='doc',
            check_payload_token=True,
            token_expires=timezone.make_aware(datetime.datetime(2023, 5, 25)))

    def test_get_with_redirect(self) -> None:
        """Testing ClientLoginView GET with a redirect URL"""
        self.spy_on(timezone.now, op=kgb.SpyOpReturn(
            timezone.make_aware(datetime.datetime(2023, 5, 20))))

        self.client.login(username='doc', password='doc')
        settings = {
            'client_web_login': True,
            'client_token_expiration': 5
        }

        with self.siteconfig_settings(settings):
            rsp = self.client.get(
                local_site_reverse('client-login'),
                {
                    'client-name': 'TestClient',
                    'client-url': 'http://localhost:1234/test/',
                    'next': 'http://localhost:1234/page?foo=1',
                })

        self._assert_context_equals(
            rsp.context,
            client_allowed=True,
            client_name='TestClient',
            client_url='http://localhost:1234/test/',
            redirect_to='http%3A//localhost%3A1234/page%3Ffoo%3D1',
            username='doc',
            check_payload_token=True,
            token_expires=timezone.make_aware(datetime.datetime(2023, 5, 25)))

    def test_get_with_unsafe_redirect(self) -> None:
        """Testing ClientLoginView GET with an unsafe redirect URL"""
        self.spy_on(timezone.now, op=kgb.SpyOpReturn(
            timezone.make_aware(datetime.datetime(2023, 5, 20))))

        self.client.login(username='doc', password='doc')
        settings = {
            'client_web_login': True,
            'client_token_expiration': 5
        }

        with self.siteconfig_settings(settings):
            rsp = self.client.get(
                local_site_reverse('client-login'),
                {
                    'client-name': 'TestClient',
                    'client-url': 'http://localhost:1234/test/',
                    'next': 'http://unsafe-site/page?foo=1',
                })

        self._assert_context_equals(
            rsp.context,
            client_allowed=True,
            client_name='TestClient',
            client_url='http://localhost:1234/test/',
            redirect_to='',
            username='doc',
            check_payload_token=True,
            token_expires=timezone.make_aware(datetime.datetime(2023, 5, 25)))

    def test_get_with_token_generation_error(self) -> None:
        """Testing ClientLoginView GET with an API token generation error"""
        self.spy_on(WebAPIToken.objects.get_or_create_client_token,
                    op=kgb.SpyOpRaise(WebAPITokenGenerationError('fail')))

        self.client.login(username='doc', password='doc')
        settings = {
            'client_web_login': True,
            'client_token_expiration': 5
        }

        with self.siteconfig_settings(settings):
            rsp = self.client.get(
                local_site_reverse('client-login'),
                {
                    'client-name': 'TestClient',
                    'client-url': 'http://localhost:1234/test/',
                })

        tokens = WebAPIToken.objects.filter(
            user=User.objects.get(username='doc'))

        self.assertEqual(len(tokens), 0)
        self._assert_context_equals(
            rsp.context,
            client_allowed=True,
            client_name='TestClient',
            client_url='http://localhost:1234/test/',
            error='Failed to generate a unique API token for authentication. '
                  'Please reload the page to try again.',
            username='doc')

    def test_get_unauthenticated(self) -> None:
        """Testing ClientLoginView GET redirects to the login page when
        a user is not logged in
        """
        settings = {
            'client_web_login': True,
            'client_token_expiration': 5
        }

        with self.siteconfig_settings(settings):
            rsp = self.client.get(
                local_site_reverse('client-login'),
                {
                    'client-name': 'TestClient',
                    'client-url': 'http://localhost:1234/test/',
                })

        self.assertEqual(rsp.status_code, 302)

    def test_get_with_unsafe_client_url(self) -> None:
        """Testing ClientLoginView GET with an unsafe client url"""

        self.client.login(username='doc', password='doc')
        settings = {
            'client_web_login': True,
            'client_token_expiration': 5
        }

        with self.siteconfig_settings(settings):
            with self.assertLogs() as logs:
                rsp = self.client.get(
                    local_site_reverse('client-login'),
                    {
                        'client-name': 'TestClient',
                        'client-url': 'http://unsafe-url.com',
                    })

        tokens = WebAPIToken.objects.filter(
            user=User.objects.get(username='doc'))

        self.assertEqual(len(tokens), 0)
        self._assert_context_equals(
            rsp.context,
            client_allowed=False,
            client_name='TestClient',
            client_url='http://unsafe-url.com',
            username='doc')
        self.assertEqual(
            logs.records[0].getMessage(),
            ('Blocking an attempt to send authentication info '
             'to unsafe URL http://unsafe-url.com'))

    def test_get_with_client_url_no_port(self) -> None:
        """Testing ClientLoginView GET with a client url that has no port
        specified
        """
        self.spy_on(timezone.now, op=kgb.SpyOpReturn(
            timezone.make_aware(datetime.datetime(2023, 5, 20))))

        self.client.login(username='doc', password='doc')
        settings = {
            'client_web_login': True,
            'client_token_expiration': 5
        }

        with self.siteconfig_settings(settings):
            rsp = self.client.get(
                local_site_reverse('client-login'),
                {
                    'client-name': 'TestClient',
                    'client-url': 'http://localhost',
                })

        self._assert_context_equals(
            rsp.context,
            client_allowed=True,
            client_name='TestClient',
            client_url='http://localhost',
            username='doc',
            check_payload_token=True,
            token_expires=timezone.make_aware(datetime.datetime(2023, 5, 25)))

    def test_get_with_client_web_login_false(self) -> None:
        """Testing ClientLoginView GET with the client web login flow
        disabled
        """
        settings = {
            'client_web_login': False,
            'client_token_expiration': 5
        }

        with self.siteconfig_settings(settings):
            rsp = self.client.get(
                local_site_reverse('client-login'),
                {
                    'client-name': 'TestClient',
                    'client-url': 'http://localhost:1234/test/',
                })

        self.assertEqual(rsp.status_code, 404)

    def test_post(self) -> None:
        """Testing ClientLoginView POST"""
        self.client.login(username='doc', password='doc')
        settings = {
            'client_web_login': True,
            'client_token_expiration': 5
        }

        with self.siteconfig_settings(settings):
            rsp = self.client.post(
                local_site_reverse('client-login'),
                {
                    'client-name': 'TestClient',
                    'client-url': 'http://localhost:1234/test/',
                })

        self.assertEqual(rsp.status_code, 405)

    def _assert_context_equals(
        self,
        context: Context,
        client_allowed: bool,
        client_name: str,
        client_url: str,
        username: str,
        check_payload_token: Optional[bool] = False,
        error: Optional[str] = '',
        redirect_to: Optional[str] = '',
        token_expires: Optional[datetime.datetime] = None,
    ) -> None:
        """Assert that the context and JS view data matches the given values.

        Args:
            context (django.template.Context):
                The context dictionary to be tested.

            client_allowed (bool):
                The expected value for the client_allowed.

            client_name (str):
                The expected value for the client_name.

            client_url (str):
                The expected value for the client_url.

            username (str):
                The expected value for the username.

            check_payload_token (bool, optional):
                Whether to check for an API token in the payload.

            error (str, optional):
                The expected value for the error.

            redirect_to (str, optional):
                The expected value for the redirect_to.

            token_expires (datetime.datetime, optional):
                The expected value for the API token expiration.

        Raises:
            AssertionError:
                The context did not match the given values.
        """
        js_view_data = context['js_view_data']
        payload = js_view_data['payload']

        self.assertEqual(context['client_allowed'], client_allowed)
        self.assertEqual(context['client_name'], client_name)
        self.assertEqual(context['client_url'], client_url)
        self.assertEqual(context['username'], username)

        if error:
            self.assertEqual(context['error'], error)
        else:
            self.assertNotIn('error', context)

        self.assertEqual(js_view_data['clientName'], escape(client_name))
        self.assertEqual(js_view_data['clientURL'], quote(client_url))
        self.assertEqual(js_view_data['username'], username)
        self.assertEqual(js_view_data['redirectTo'], redirect_to)

        if check_payload_token:
            token = WebAPIToken.objects.get(token=payload['api_token'])
            self.assertEqual(token.user.username, username)
            self.assertEqual(token.expires, token_expires)
            self.assertEqual(token.extra_data['client_name'], client_name)
        else:
            self.assertEqual(payload, {})
