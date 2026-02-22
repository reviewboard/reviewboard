"""Unit tests for SAML forms."""

from __future__ import annotations

from typing import ClassVar, TYPE_CHECKING

from django.contrib.auth.models import User
from djblets.siteconfig.models import SiteConfiguration

from reviewboard.accounts.sso.backends import sso_backends
from reviewboard.accounts.sso.backends.saml.forms import (SAMLLinkUserForm,
                                                          SAMLSettingsForm)
from reviewboard.accounts.sso.backends.saml.settings import (
    SAMLBinding,
    SAMLDigestAlgorithm,
    SAMLNameIDFormat,
    SAMLSignatureAlgorithm)
from reviewboard.testing import TestCase

if TYPE_CHECKING:
    from djblets.util.typing import JSONDict


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


class SAMLLinkUserFormTests(TestCase):
    """Unit tests for SAMLLinkUserForm."""

    fixtures: ClassVar[list[str]] = ['test_users']

    def test_valid_login(self) -> None:
        """Testing SAMLLinkUserForm validation in login mode"""
        form = SAMLLinkUserForm(data={
            'username': 'doc',
            'password': 'doc',
            'provision': False,
        })

        self.assertTrue(form.is_valid())

    def test_invalid_login(self) -> None:
        """Testing SAMLLinkUserForm validation with incorrect password in login
        mode
        """
        form = SAMLLinkUserForm(data={
            'username': 'doc',
            'password': 'nope',
            'provision': False,
        })

        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors['__all__'],
                         ['Please enter a correct username and password. Note '
                          'that both fields may be case-sensitive.'])

    def test_inactive_user(self) -> None:
        """Testing SAMLLinkUserForm validation with an inactive user"""
        user = User.objects.get(username='doc')
        user.is_active = False
        user.save(update_fields=['is_active'])

        form = SAMLLinkUserForm(data={
            'username': 'doc',
            'password': 'nope',
            'provision': False,
        })

        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors['__all__'],
                         ['This account is inactive.'])

    def test_provision(self) -> None:
        """Testing SAMLLinkUserForm validation in provision mode"""
        form = SAMLLinkUserForm(data={
            'username': 'doc',
            'password': 'nope',
            'provision': True,
        })

        self.assertTrue(form.is_valid())

    def test_provision_disabled(self) -> None:
        """Testing SAMLLinkUserForm validation in provision mode"""
        form = SAMLLinkUserForm(data={
            'username': 'doc',
            'password': 'nope',
            'provision': True,
        })

        settings: JSONDict = {
            'saml_automatically_provision_users': False,
        }

        with self.siteconfig_settings(settings):
            self.assertFalse(form.is_valid())
            self.assertEqual(
                form.errors['__all__'],
                ['A user account for doc does not exist. Your administrator '
                 'will need to provision an account before you can log in.'])


class SAMLSettingsFormTests(TestCase):
    """Unit tests for SAMLSettingsForm."""

    def setUp(self):
        """Set up the test case."""
        self.siteconfig = SiteConfiguration.objects.get_current()

        saml_backend = sso_backends.get('backend_id', 'saml')

        # Ensure everything is set to defaults.
        for key, value in saml_backend.siteconfig_defaults.items():
            self.siteconfig.set(key, value)

        self.siteconfig.save()

    def test_save(self):
        """Testing SAMLSettingsForm.save"""
        siteconfig = self.siteconfig

        form = SAMLSettingsForm(
            siteconfig,
            data={
                'saml_login_button_text': 'Login',
                'saml_issuer': 'https://example.com/saml/issuer',
                'saml_signature_algorithm': SAMLSignatureAlgorithm.RSA_SHA1,
                'saml_digest_algorithm': SAMLDigestAlgorithm.SHA512,
                'saml_nameid_format': SAMLNameIDFormat.PERSISTENT,
                'saml_verification_cert': VALID_CERT,
                'saml_sso_url': 'https://example.com/saml/sso',
                'saml_sso_binding_type': SAMLBinding.HTTP_POST,
                'saml_slo_url': 'https://example.com/saml/slo',
                'saml_slo_binding_type': SAMLBinding.HTTP_REDIRECT,
                'saml_require_login_to_link': False,
                'saml_attr_email': 'User.Email',
                'saml_attr_firstname': 'User.FirstName',
                'saml_attr_lastname': 'User.LastName',
                'saml_attr_fullname': 'User.FullName',
            })

        self.assertTrue(form.is_valid())
        form.save()

        siteconfig.refresh_from_db()
        self.assertEqual(siteconfig.get('saml_login_button_text'),
                         'Login')
        self.assertEqual(siteconfig.get('saml_issuer'),
                         'https://example.com/saml/issuer')
        self.assertEqual(siteconfig.get('saml_signature_algorithm'),
                         SAMLSignatureAlgorithm.RSA_SHA1)
        self.assertEqual(siteconfig.get('saml_digest_algorithm'),
                         SAMLDigestAlgorithm.SHA512)
        self.assertEqual(siteconfig.get('saml_nameid_format'),
                         SAMLNameIDFormat.PERSISTENT)
        self.assertEqual(siteconfig.get('saml_verification_cert'),
                         VALID_CERT)
        self.assertEqual(siteconfig.get('saml_sso_url'),
                         'https://example.com/saml/sso')
        self.assertEqual(siteconfig.get('saml_sso_binding_type'),
                         SAMLBinding.HTTP_POST)
        self.assertEqual(siteconfig.get('saml_slo_url'),
                         'https://example.com/saml/slo')
        self.assertEqual(siteconfig.get('saml_slo_binding_type'),
                         SAMLBinding.HTTP_REDIRECT)
        self.assertFalse(siteconfig.get('saml_require_login_to_link'))
