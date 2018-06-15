"""Unit tests for reviewboard.accounts.forms.pages.PrivacyForm."""

from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.test.client import RequestFactory

from reviewboard.accounts.forms.pages import PrivacyForm
from reviewboard.accounts.pages import PrivacyPage
from reviewboard.accounts.views import MyAccountView
from reviewboard.testing import TestCase


class PrivacyFormTests(TestCase):
    """Unit tests for reviewboard.accounts.forms.pages.PrivacyForm."""

    def setUp(self):
        super(PrivacyFormTests, self).setUp()

        self.user = User.objects.create(username='test-user')

        self.request = RequestFactory().get('/account/preferences/')
        self.request.user = self.user

        self.page = PrivacyPage(config_view=MyAccountView(),
                                request=self.request,
                                user=self.user)

    def test_init_with_privacy_enable_user_consent_true(self):
        """Testing PrivacyForm with privacy_enable_user_consent=True"""
        with self.siteconfig_settings({'privacy_enable_user_consent': True}):
            form = PrivacyForm(page=self.page,
                               request=self.request,
                               user=self.user)
            self.assertIn('consent', form.fields)
            self.assertEqual(form.save_label, 'Save')

    def test_init_with_privacy_enable_user_consent_false(self):
        """Testing PrivacyForm with privacy_enable_user_consent=False"""
        with self.siteconfig_settings({'privacy_enable_user_consent': False}):
            form = PrivacyForm(page=self.page,
                               request=self.request,
                               user=self.user)
            self.assertNotIn('consent', form.fields)
            self.assertIsNone(form.save_label)

    def test_is_visible_with_no_privacy(self):
        """Testing PrivacyForm.is_visible with no privacy details"""
        settings = {
            'privacy_enable_user_consent': False,
            'privacy_info_html': '',
        }

        with self.siteconfig_settings(settings):
            form = PrivacyForm(page=self.page,
                               request=self.request,
                               user=self.user)
            self.assertFalse(form.is_visible())

    def test_is_visible_with_consent(self):
        """Testing PrivacyForm.is_visible with consent option enabled"""
        settings = {
            'privacy_enable_user_consent': True,
            'privacy_info_html': '',
        }

        with self.siteconfig_settings(settings):
            form = PrivacyForm(page=self.page,
                               request=self.request,
                               user=self.user)
            self.assertTrue(form.is_visible())

    def test_is_visible_with_privacy_info(self):
        """Testing PrivacyForm.is_visible with privacy_info_html set"""
        settings = {
            'privacy_enable_user_consent': False,
            'privacy_info_html': 'Test.',
        }

        with self.siteconfig_settings(settings):
            form = PrivacyForm(page=self.page,
                               request=self.request,
                               user=self.user)
            self.assertTrue(form.is_visible())
