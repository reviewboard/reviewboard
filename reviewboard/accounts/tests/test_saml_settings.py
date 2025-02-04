"""Unit tests for SAML settings.

Version Added:
    7.0.4
"""

from __future__ import annotations

from reviewboard.testing import TestCase

from reviewboard.accounts.sso.backends.saml.settings import get_saml2_settings


class SAMLSettingsTests(TestCase):
    """Unit tests for SAML settings.

    Version Added:
        7.0.4
    """

    def test_advanced_config(self) -> None:
        """Testing get_saml2_settings with advanced config override"""
        django_settings = {
            'SAML_CONFIG_ADVANCED': {
                'security': {
                    'requestedAuthnContext': False,
                },
            },
        }

        with self.settings(**django_settings):
            saml_settings = get_saml2_settings()

            self.assertEqual(saml_settings['security'], {
                'requestedAuthnContext': False,
            })
