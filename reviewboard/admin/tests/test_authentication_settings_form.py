"""Unit tests for reviewboard.admin.forms.AuthenticationSettingsForm.

Version Added:
    5.0.5
"""

from djblets.siteconfig.models import SiteConfiguration

from reviewboard.admin.forms.auth_settings import \
    AuthenticationSettingsForm
from reviewboard.testing.testcase import TestCase


class AuthenticationSettingsFormTests(TestCase):
    """Unit tests for reviewboard.admin.forms.AuthenticationSettingsForm.

    Version Added:
        5.0.5
    """

    def test_load_with_none(self) -> None:
        """Test AuthenticationSettingsForm.load with no API tokens
        expiration set in siteconfig
        """
        siteconfig_settings = {
            'client_token_expiration': None,
        }

        with self.siteconfig_settings(siteconfig_settings):
            siteconfig = SiteConfiguration.objects.get_current()
            form = AuthenticationSettingsForm(siteconfig)
            form.load()

            self.assertIsNone(form['automatic_api_token_expiration'].value())

    def test_load_with_date(self) -> None:
        """Test AuthenticationSettingsForm.load with API tokens
        expiration set in siteconfig
        """
        siteconfig_settings = {
            'client_token_expiration': 10,
        }

        with self.siteconfig_settings(siteconfig_settings):
            siteconfig = SiteConfiguration.objects.get_current()
            form = AuthenticationSettingsForm(siteconfig)
            form.load()

            self.assertEqual(form['automatic_api_token_expiration'].value(),
                             10)

    def test_save_with_none(self) -> None:
        """Test AuthenticationSettingsForm.save with API tokens
        set to never expire
        """
        siteconfig_settings = {
            'client_token_expiration': 10,
        }

        with self.siteconfig_settings(siteconfig_settings):
            siteconfig = SiteConfiguration.objects.get_current()
            form = AuthenticationSettingsForm(siteconfig, data={
                'auth_backend': 'builtin',
                'automatic_api_token_expiration_0': '20',
                'automatic_api_token_expiration_1': '',
            })

            self.assertTrue(form.is_valid())

            form.save()

            self.assertIsNone(
                siteconfig.get('client_token_expiration'))

    def test_save_with_date(self) -> None:
        """Test AuthenticationSettingsForm.save with API tokens
        expiration set
        """
        siteconfig_settings = {
            'client_token_expiration': None,
        }

        with self.siteconfig_settings(siteconfig_settings):
            siteconfig = SiteConfiguration.objects.get_current()
            form = AuthenticationSettingsForm(siteconfig, data={
                'auth_backend': 'builtin',
                'automatic_api_token_expiration_0': '20',
                'automatic_api_token_expiration_1': '1',
            })

            self.assertTrue(form.is_valid())

            form.save()

            self.assertEqual(
                siteconfig.get('client_token_expiration'),
                20)
