"""Unit tests for SAML views."""

from xml.etree import ElementTree

import kgb
from django.contrib.auth.models import User
from django.urls import reverse

from reviewboard.accounts.sso.backends.saml.views import (SAMLACSView,
                                                          SAMLLinkUserView,
                                                          SAMLSLSView)
from reviewboard.testing import TestCase


VALID_CERT = """-----BEGIN CERTIFICATE-----
MIICZjCCAc+gAwIBAgIBADANBgkqhkiG9w0BAQ0FADBQMQswCQYDVQQGEwJ1czEL
MAkGA1UECAwCQ0ExFjAUBgNVBAoMDUJlYW5iYWcsIEluYy4xHDAaBgNVBAMME2h0
dHBzOi8vZXhhbXBsZS5jb20wHhcNMjIwNTA2MTU0NjI1WhcNMjMwNTA2MTU0NjI1
WjBQMQswCQYDVQQGEwJ1czELMAkGA1UECAwCQ0ExFjAUBgNVBAoMDUJlYW5iYWcs
IEluYy4xHDAaBgNVBAMME2h0dHBzOi8vZXhhbXBsZS5jb20wgZ8wDQYJKoZIhvcN
AQEBBQADgY0AMIGJAoGBANCsbj4mvUiQERBy80R7yqA6hU3FMM4siC2UcUS3ltFF
grkVOAPr+zUnrdadmAiTH35AB94oMzf0Qh8OJCr7wG5JQm686TRkVm2xUxhJUcoq
7LjBTKeEXBcrEzdNlagFXxHUSz5bPSdwDt/zbOfe+9RZKeb4FggFCEYw/mi69+Dx
AgMBAAGjUDBOMB0GA1UdDgQWBBS4cP9Y+IM7ZHZChUDdx68QExTZUDAfBgNVHSME
GDAWgBS4cP9Y+IM7ZHZChUDdx68QExTZUDAMBgNVHRMEBTADAQH/MA0GCSqGSIb3
DQEBDQUAA4GBALht5/NfJU+GxYfQKiGkZ4Ih/T/48rzXAT7/7f61s7w72UR2S5e2
WsR7/JPkZ5+u5mCgmABjNcd9NzaBM2RfSrrurwbjXMQ8nb/+REvhXXJ4STsS48y5
bef2JtIf7mGDw8/KsUrAA2jEIpCedToGyQxyE6GdN5b69ITWvyAemnIM
-----END CERTIFICATE-----"""


class SAMLViewTests(kgb.SpyAgency, TestCase):
    """Unit tests for SAML views."""

    fixtures = ['test_users']

    def test_metadata_view(self):
        """Testing SAMLMetadataView"""
        settings = {
            'saml_enabled': True,
            'saml_verification_cert': VALID_CERT,
        }

        with self.siteconfig_settings(settings):
            url = reverse('sso:saml:metadata', kwargs={'backend_id': 'saml'})
            rsp = self.client.get(url)

            self.assertEqual(rsp.status_code, 200)

            root = ElementTree.fromstring(rsp.content)

            namespaces = {'md': 'urn:oasis:names:tc:SAML:2.0:metadata'}

            descriptor = root.find('md:SPSSODescriptor', namespaces)
            assert descriptor is not None

            sls = descriptor.find('md:SingleLogoutService', namespaces)
            assert sls is not None

            self.assertEqual(
                sls.get('Binding'),
                'urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect')
            self.assertEqual(
                sls.get('Location'),
                'http://example.com/account/sso/saml/sls/')

            acs = descriptor.find('md:AssertionConsumerService', namespaces)
            assert acs is not None

            self.assertEqual(
                acs.get('Binding'),
                'urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST')
            self.assertEqual(
                acs.get('Location'),
                'http://example.com/account/sso/saml/acs/')

    def test_get_link_user_existing_account(self):
        """Testing SAMLLinkUserView form render with existing account"""
        settings = {
            'saml_enabled': True,
            'saml_require_login_to_link': True,
        }

        with self.siteconfig_settings(settings):
            session = self.client.session
            session['sso'] = {
                'user_data': {
                    'id': 'doc',
                    'first_name': 'Doc',
                    'last_name': 'Dwarf',
                    'email': 'doc@example.com',
                },
            }
            session.save()

            url = reverse('sso:saml:link-user', kwargs={'backend_id': 'saml'})
            rsp = self.client.get(url)

            self.assertEqual(rsp.status_code, 200)

            context = rsp.context
            self.assertEqual(context['user'].username, 'doc')
            self.assertEqual(context['mode'],
                             SAMLLinkUserView.Mode.CONNECT_EXISTING_ACCOUNT)

    def test_get_link_user_existing_account_email_match(self):
        """Testing SAMLLinkUserView form render with existing account matching
        email address
        """
        settings = {
            'saml_enabled': True,
            'saml_require_login_to_link': True,
        }

        with self.siteconfig_settings(settings):
            session = self.client.session
            session['sso'] = {
                'user_data': {
                    'id': 'doc2',
                    'first_name': 'Doc',
                    'last_name': 'Dwarf',
                    'email': 'doc@example.com',
                },
            }
            session.save()

            url = reverse('sso:saml:link-user', kwargs={'backend_id': 'saml'})
            rsp = self.client.get(url)

            self.assertEqual(rsp.status_code, 200)

            context = rsp.context
            self.assertEqual(context['user'].username, 'doc')
            self.assertEqual(context['mode'],
                             SAMLLinkUserView.Mode.CONNECT_EXISTING_ACCOUNT)

    def test_get_link_user_existing_account_email_username_match(self):
        """Testing SAMLLinkUserView form render with existing account matching
        username from email address
        """
        settings = {
            'saml_enabled': True,
            'saml_require_login_to_link': True,
        }

        with self.siteconfig_settings(settings):
            session = self.client.session
            session['sso'] = {
                'user_data': {
                    'id': 'doc2',
                    'first_name': 'Doc',
                    'last_name': 'Dwarf',
                    'email': 'doc@example.org',
                },
            }
            session.save()

            url = reverse('sso:saml:link-user', kwargs={'backend_id': 'saml'})
            rsp = self.client.get(url)

            self.assertEqual(rsp.status_code, 200)

            context = rsp.context
            self.assertEqual(context['user'].username, 'doc')
            self.assertEqual(context['mode'],
                             SAMLLinkUserView.Mode.CONNECT_EXISTING_ACCOUNT)

    def test_get_link_user_no_match(self):
        """Testing SAMLLinkUserView form render with no match"""
        settings = {
            'saml_enabled': True,
            'saml_require_login_to_link': True,
        }

        with self.siteconfig_settings(settings):
            session = self.client.session
            session['sso'] = {
                'user_data': {
                    'id': 'doc2',
                    'first_name': 'Doc',
                    'last_name': 'Dwarf',
                    'email': 'doc2@example.org',
                },
            }
            session.save()

            url = reverse('sso:saml:link-user', kwargs={'backend_id': 'saml'})
            rsp = self.client.get(url)

            self.assertEqual(rsp.status_code, 200)

            context = rsp.context
            self.assertEqual(context['user'], None)
            self.assertEqual(context['mode'],
                             SAMLLinkUserView.Mode.PROVISION)

    def test_post_link_user_login(self):
        """Testing SAMLLinkUserView form POST with login"""
        settings = {
            'saml_enabled': True,
            'saml_require_login_to_link': True,
        }

        with self.siteconfig_settings(settings):
            session = self.client.session
            session['sso'] = {
                'user_data': {
                    'id': 'doc2',
                    'first_name': 'Doc',
                    'last_name': 'Dwarf',
                    'email': 'doc@example.com',
                },
            }
            session.save()

            user = User.objects.get(username='doc')
            self.assertFalse(user.linked_accounts.exists())

            url = reverse('sso:saml:link-user', kwargs={'backend_id': 'saml'})
            rsp = self.client.post(url, {
                'username': 'doc',
                'password': 'doc',
                'provision': False,
            })

            self.assertEqual(rsp.status_code, 302)

            linked_accounts = list(user.linked_accounts.all())

            self.assertEqual(len(linked_accounts), 1)
            linked_account = linked_accounts[0]
            self.assertEqual(linked_account.service_id, 'sso:saml')
            self.assertEqual(linked_account.service_user_id, 'doc2')

    def test_post_link_user_provision(self):
        """Testing SAMLLinkUserView form POST with provision"""
        settings = {
            'saml_enabled': True,
            'saml_require_login_to_link': True,
        }

        with self.siteconfig_settings(settings):
            session = self.client.session
            session['sso'] = {
                'user_data': {
                    'id': 'sleepy',
                    'first_name': 'Sleepy',
                    'last_name': 'Dwarf',
                    'email': 'sleepy@example.com',
                },
            }
            session.save()

            self.assertFalse(User.objects.filter(username='sleepy').exists())

            url = reverse('sso:saml:link-user', kwargs={'backend_id': 'saml'})
            rsp = self.client.post(url, {
                'username': '',
                'password': '',
                'provision': True,
            })

            self.assertEqual(rsp.status_code, 302)

            user = User.objects.get(username='sleepy')
            self.assertEqual(user.first_name, 'Sleepy')
            self.assertEqual(user.last_name, 'Dwarf')
            self.assertEqual(user.email, 'sleepy@example.com')

            linked_accounts = list(user.linked_accounts.all())

            self.assertEqual(len(linked_accounts), 1)
            linked_account = linked_accounts[0]
            self.assertEqual(linked_account.service_id, 'sso:saml')
            self.assertEqual(linked_account.service_user_id, 'sleepy')

    def test_post_assertion_replay_countermeasures(self):
        """Testing SAMLACSView POST replay attack countermeasures"""
        class FakeAuth:
            def process_response(*args, **kwargs):
                pass

            def get_last_message_id(self):
                return 'message-id'

            def get_last_assertion_id(self):
                return 'assertion-id'

            def get_last_error_reason(self):
                return None

            def get_nameid(self):
                return 'username'

            def get_attribute(self, attr):
                return ['a']

            def get_attributes(self):
                return {}

            def get_session_index(self):
                return 1

        fake_auth = FakeAuth()

        self.spy_on(SAMLACSView.get_saml_auth,
                    op=kgb.SpyOpReturn(fake_auth),
                    owner=SAMLACSView)

        settings = {
            'saml_enabled': True,
        }

        with self.siteconfig_settings(settings):
            url = reverse('sso:saml:acs', kwargs={'backend_id': 'saml'})

            # First one should succeed and redirect us to the link user view.
            rsp = self.client.post(url, {})
            self.assertEqual(rsp.status_code, 302)

            # Second one should fail.
            rsp = self.client.post(url, {})
            self.assertEqual(rsp.status_code, 400)
            self.assertEqual(rsp.content,
                             b'SAML message IDs have already been used')

    def test_get_sls_replay_countermeasures(self):
        """Testing SAMLSLSView GET replay attack countermeasures"""
        class FakeAuth:
            def process_slo(*args, **kwargs):
                pass

            def get_last_message_id(self):
                return 'message-id'

            def get_last_request_id(self):
                return 'request-id'

            def get_last_error_reason(self):
                return None

        fake_auth = FakeAuth()

        self.spy_on(SAMLSLSView.get_saml_auth,
                    op=kgb.SpyOpReturn(fake_auth),
                    owner=SAMLSLSView)

        settings = {
            'saml_enabled': True,
        }

        with self.siteconfig_settings(settings):
            url = reverse('sso:saml:sls', kwargs={'backend_id': 'saml'})

            # First one should succeed and redirect us to the link user view.
            rsp = self.client.get(url, {})
            self.assertEqual(rsp.status_code, 302)

            # Second one should fail.
            rsp = self.client.get(url, {})
            self.assertEqual(rsp.status_code, 400)
            self.assertEqual(rsp.content,
                             b'SAML message IDs have already been used')
