"""Unit tests for reviewboard.accounts.forms.pages.PrivacyForm."""

from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.core.cache import cache
from django.test.client import RequestFactory
from djblets.privacy.consent import (get_consent_requirements_registry,
                                     get_consent_tracker)
from djblets.privacy.consent.common import PolicyConsentRequirement

from reviewboard.accounts.forms.pages import PrivacyForm
from reviewboard.accounts.pages import AccountPage
from reviewboard.accounts.views import MyAccountView
from reviewboard.testing import TestCase


class MyAccountViewTests(TestCase):
    """Unit tests for MyAccountView."""

    fixtures = ['test_users']

    def tearDown(self):
        super(MyAccountViewTests, self).tearDown()

        cache.clear()

    def test_render_all_accept_requirements(self):
        """Testing MyAccountView renders all forms when a user has accepted all
        requirements
        """
        settings = {
            'privacy_enable_user_consent': True,
        }
        user = User.objects.get(username='doc')
        get_consent_tracker().record_consent_data_list(
            user,
            [
                requirement.build_consent_data(granted=True)
                for requirement in get_consent_requirements_registry()
            ])

        request = RequestFactory().get('/account/preferences')
        request.user = User.objects.get(username='doc')
        view = MyAccountView()

        self.client.login(username='doc', password='doc')

        with self.siteconfig_settings(settings):
            rsp = self.client.get('/account/preferences/')

            self.assertEqual(rsp.status_code, 200)
            context = rsp.context

            self.assertEqual(context['render_sidebar'], True)
            self.assertEqual(
                {
                    type(page)
                    for page in context['pages']
                    if page.is_visible()
                },
                {
                    account_page
                    for account_page in AccountPage.registry
                    if account_page(view, request, request.user).is_visible()
                })

    def test_render_all_reject_requirements(self):
        """Testing MyAccountView renders all forms when a user has rejected all
        consent decisions
        """
        settings = {
            'privacy_enable_user_consent': True,
        }
        user = User.objects.get(username='doc')
        get_consent_tracker().record_consent_data_list(
            user,
            [
                requirement.build_consent_data(granted=False)
                for requirement in get_consent_requirements_registry()
            ])

        request = RequestFactory().get('/account/preferences')
        request.user = User.objects.get(username='doc')
        view = MyAccountView()

        self.client.login(username='doc', password='doc')

        with self.siteconfig_settings(settings):
            rsp = self.client.get('/account/preferences/')

            self.assertEqual(rsp.status_code, 200)
            context = rsp.context

            self.assertEqual(context['render_sidebar'], True)
            self.assertEqual(
                {
                    type(page)
                    for page in context['pages']
                },
                {
                    account_page
                    for account_page in AccountPage.registry
                    if account_page(view, request, request.user).is_visible()
                })

    def test_render_only_privacy_form_if_missing_consent(self):
        """Testing MyAccountView only renders privacy form when a user has
        pending consent decisions
        """
        settings = {
            'privacy_enable_user_consent': True,
        }

        self.client.login(username='doc', password='doc')

        with self.siteconfig_settings(settings):
            rsp = self.client.get('/account/preferences/')

        self.assertEqual(rsp.status_code, 200)
        context = rsp.context

        self.assertEqual(context['render_sidebar'], False)
        self.assertEqual(len(context['forms']), 1)
        self.assertIsInstance(context['forms'][0], PrivacyForm)

    def test_render_only_privacy_form_if_reject_policy_grant_others(self):
        """Testing MyAccountView only renders privacy policy when a user has
        rejected the privacy policy/terms of service and granted all other
        requirements
        """
        settings = {
            'privacy_enable_user_consent': True,
            'privacy_policy_url': 'https://example.com',
            'terms_of_service_url': 'https://example.com',
        }

        user = User.objects.get(username='doc')

        # Accept all consent requirements *except* the policy.
        get_consent_tracker().record_consent_data_list(
            user,
            [
                requirement.build_consent_data(
                    granted=not isinstance(requirement,
                                           PolicyConsentRequirement))
                for requirement in get_consent_requirements_registry()
            ])

        self.client.login(username='doc', password='doc')

        with self.siteconfig_settings(settings):
            rsp = self.client.get('/account/preferences/')

        self.assertEqual(rsp.status_code, 200)
        context = rsp.context

        self.assertEqual(context['render_sidebar'], False)
        self.assertEqual(len(context['forms']), 1)
        self.assertIsInstance(context['forms'][0], PrivacyForm)

    def test_render_only_privacy_form_if_reject_policy_reject_others(self):
        """Testing MyAccountView only renders privacy policy when a user has
        rejected the privacy policy/terms of service and rejected all other
        requirements
        """
        settings = {
            'privacy_enable_user_consent': True,
            'privacy_policy_url': 'https://example.com',
            'terms_of_service_url': 'https://example.com',
        }

        user = User.objects.get(username='doc')

        # Accept all consent requirements *except* the policy.
        get_consent_tracker().record_consent_data_list(
            user,
            [
                requirement.build_consent_data(granted=False)
                for requirement in get_consent_requirements_registry()
            ])

        self.client.login(username='doc', password='doc')

        with self.siteconfig_settings(settings):
            rsp = self.client.get('/account/preferences/')

        self.assertEqual(rsp.status_code, 200)
        context = rsp.context

        self.assertEqual(context['render_sidebar'], False)
        self.assertEqual(len(context['forms']), 1)
        self.assertIsInstance(context['forms'][0], PrivacyForm)

    def test_redirect_privacy_form(self):
        """Testing MyAccountView redirects to previous URL when saving the
        privacy form if a next URL is provided
        """
        settings = {
            'privacy_enable_user_consent': True,
        }

        self.client.login(username='doc', password='doc')

        with self.siteconfig_settings(settings):
            rsp = self.client.post(
                '/account/preferences/',
                dict({
                    'next_url': '/some-page/',
                    'form_target': PrivacyForm.form_id,
                }, **{
                    'consent_%s_choice' % requirement.requirement_id: 'allow'
                    for requirement in get_consent_requirements_registry()

                }))

        self.assertEqual(rsp.status_code, 302)
        self.assertEqual(rsp.url, 'http://testserver/some-page/')
