"""Unit tests for reviewboard.accounts.forms.pages.ProfileForm."""

from __future__ import unicode_literals

from django.contrib import messages
from django.contrib.auth.models import User
from django.test.client import RequestFactory
from kgb import SpyAgency

from reviewboard.accounts.backends import (AuthBackend,
                                           get_enabled_auth_backends)
from reviewboard.accounts.forms.pages import ProfileForm
from reviewboard.accounts.models import Profile
from reviewboard.testing import TestCase


class SandboxAuthBackend(AuthBackend):
    """Mock authentication backend to test extension sandboxing."""

    backend_id = 'test-id'
    name = 'test'
    supports_change_name = True
    supports_change_email = True

    def update_name(self, user):
        """Raise an exception to test sandboxing."""
        raise Exception

    def update_email(self, user):
        """Raise an exception to test sandboxing."""
        raise Exception


class ProfileFormTests(SpyAgency, TestCase):
    """Unit tests for reviewboard.accounts.forms.pages.ProfileForm."""

    def setUp(self):
        super(ProfileFormTests, self).setUp()

        self.factory = RequestFactory()
        self.request = self.factory.get('test')
        self.user = User.objects.create_user(username='reviewboard', email='',
                                             password='password')
        self.profile = Profile.objects.get_or_create(user=self.user)
        self.spy_on(get_enabled_auth_backends,
                    call_fake=lambda: [SandboxAuthBackend()])

        # Suppresses MessageFailure Exception at the end of save()
        self.spy_on(messages.add_message,
                    call_fake=lambda *args, **kwargs: None)

    def test_update_name_auth_backend(self):
        """Testing ProfileForm.save with error in auth_backend.update_name"""
        form = ProfileForm(page=None,
                           request=self.request,
                           user=self.user)
        form.cleaned_data = {
            'first_name': 'Barry',
            'last_name': 'Allen',
            'email': 'flash@example.com',
            'profile_private': '',
        }
        self.user.email = 'flash@example.com'

        self.spy_on(SandboxAuthBackend.update_name)

        form.save()
        self.assertTrue(SandboxAuthBackend.update_name.called)

    def test_update_email_auth_backend(self):
        """Testing ProfileForm.save with error in auth_backend.update_email"""
        form = ProfileForm(page=None, request=self.request, user=self.user)
        form.cleaned_data = {
            'first_name': 'Barry',
            'last_name': 'Allen',
            'email': 'flash@example.com',
            'profile_private': '',
        }
        self.user.first_name = 'Barry'
        self.user.last_name = 'Allen'

        self.spy_on(SandboxAuthBackend.update_email)

        form.save()
        self.assertTrue(SandboxAuthBackend.update_email.called)
