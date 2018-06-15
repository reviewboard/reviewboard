"""Unit tests for reviewboard.accounts.decorators.valid_prefs_required."""

from __future__ import unicode_literals

from django.contrib.auth.models import AnonymousUser, User
from django.http import HttpResponse, HttpResponseRedirect
from django.test.client import RequestFactory
from djblets.privacy.consent import (get_consent_requirements_registry,
                                     get_consent_tracker)

from reviewboard.accounts.decorators import valid_prefs_required
from reviewboard.accounts.models import Profile
from reviewboard.testing import TestCase


class ValidPrefsRequiredTests(TestCase):
    """Unit tests for reviewboard.accounts.decorators.valid_prefs_required."""

    @classmethod
    def setUpClass(cls):
        super(ValidPrefsRequiredTests, cls).setUpClass()

        cls.request_factory = RequestFactory()

    def setUp(self):
        super(ValidPrefsRequiredTests, self).setUp()

        self.user = User.objects.create(username='test-user')

        self.request = self.request_factory.get('/')
        self.request.user = self.user

    def test_with_anonymous_user(self):
        """Testing @valid_prefs_required with anonymous user"""
        self.request.user = AnonymousUser()

        with self.siteconfig_settings({'privacy_enable_user_consent': True}):
            response = self._view_func(self.request)

        self.assertIs(type(response), HttpResponse)

    def test_with_consent_not_required(self):
        """Testing @valid_prefs_required with privacy_enable_user_consent=False
        """
        with self.siteconfig_settings({'privacy_enable_user_consent': False}):
            response = self._view_func(self.request)

        self.assertIs(type(response), HttpResponse)

    def test_with_consent_required_and_new_profile(self):
        """Testing @valid_prefs_required with privacy_enable_user_consent=True
        and new user profile
        """
        self.assertFalse(Profile.objects.filter(user=self.user).exists())

        with self.siteconfig_settings({'privacy_enable_user_consent': True}):
            response = self._view_func(self.request)

        self.assertIs(type(response), HttpResponseRedirect)
        self.assertEqual(response.url, '/account/preferences/?next=/')

    def test_with_consent_required_and_consent_pending(self):
        """Testing @valid_prefs_required with privacy_enable_user_consent=True
        and pending consent
        """
        Profile.objects.create(user=self.user)

        consent_tracker = get_consent_tracker()
        all_consent = consent_tracker.get_all_consent(self.user)
        self.assertEqual(all_consent, {})

        with self.siteconfig_settings({'privacy_enable_user_consent': True}):
            response = self._view_func(self.request)

        self.assertIs(type(response), HttpResponseRedirect)
        self.assertEqual(response.url, '/account/preferences/?next=/')

    def test_with_consent_required_and_no_consent_pending(self):
        """Testing @valid_prefs_required with privacy_enable_user_consent=True
        and no pending consent
        """
        Profile.objects.create(user=self.user)

        consent_tracker = get_consent_tracker()
        consent_tracker.record_consent_data_list(
            self.user,
            [
                consent_requirement.build_consent_data(granted=True)
                for consent_requirement in get_consent_requirements_registry()
            ])

        all_consent = consent_tracker.get_all_consent(self.user)
        self.assertNotEqual(all_consent, {})

        with self.siteconfig_settings({'privacy_enable_user_consent': True}):
            response = self._view_func(self.request)

        self.assertIs(type(response), HttpResponse)

    def test_with_consent_required_pending_consent_enabled_decorator(self):
        """Testing @valid_prefs_required with disbled_consent_checks= set to a
        function that always returns False
        """
        @valid_prefs_required(disable_consent_checks=lambda request: False)
        def view_func(request):
            return HttpResponse()

        with self.siteconfig_settings({'privacy_enable_user_consent': True}):
            response = view_func(self.request)

        self.assertIs(type(response), HttpResponseRedirect)

    def test_with_consent_required_pending_consent_disabled_decorator(self):
        """Testing @valid_prefs_required with disbled_consent_checks= set to a
        function that always returns True
        """
        @valid_prefs_required(disable_consent_checks=lambda request: True)
        def view_func(request):
            return HttpResponse()

        with self.siteconfig_settings({'privacy_enable_user_consent': True}):
            response = view_func(self.request)

        self.assertIs(type(response), HttpResponse)

    def test_with_consent_required_pending_consent_decorator_function(self):
        """Testing @valid_prefs_required with disbled_consent_checks= set to a
        function
        """
        def disable_consent_checks(request):
            return 'disable-consent-checks' in request.GET

        @valid_prefs_required(disable_consent_checks=disable_consent_checks)
        def view_func(request):
            return HttpResponse()

        with self.siteconfig_settings({'privacy_enable_user_consent': True}):
            response = view_func(self.request)

        self.assertIs(type(response), HttpResponseRedirect)

        request = self.request_factory.get('/?disable-consent-checks')
        request.user = self.user

        with self.siteconfig_settings({'privacy_enable_user_consent': True}):
            response = view_func(request)

        self.assertIs(type(response), HttpResponse)

    @staticmethod
    @valid_prefs_required
    def _view_func(request):
        return HttpResponse()
