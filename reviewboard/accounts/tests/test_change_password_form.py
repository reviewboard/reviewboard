"""Unit tests for reviewboard.accounts.forms.pages.ChangePasswordForm."""

from __future__ import unicode_literals

from django.contrib import messages
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test.client import RequestFactory
from kgb import SpyAgency

from reviewboard.accounts.backends import (AuthBackend,
                                           get_enabled_auth_backends)
from reviewboard.accounts.forms.pages import ChangePasswordForm
from reviewboard.accounts.models import Profile
from reviewboard.testing import TestCase


class SandboxAuthBackend(AuthBackend):
    """Mock authentication backend to test extension sandboxing."""

    backend_id = 'test-id'
    name = 'test'
    supports_change_password = True

    def authenticate(self, username, password):
        """Raise an exception to test sandboxing."""
        raise Exception

    def update_password(self, user, password):
        """Raise an exception to test sandboxing."""
        raise Exception


class ChangePasswordFormTests(SpyAgency, TestCase):
    """Unit tests for reviewboard.accounts.forms.pages.ChangePasswordForm."""

    def setUp(self):
        super(ChangePasswordFormTests, self).setUp()

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

    def test_clean_old_password_with_error_in_backend(self):
        """Testing ChangePasswordForm.clean_old_password with error in
        auth_backend.authenticate
        """
        form = ChangePasswordForm(page=None, request=self.request,
                                  user=self.user)
        form.cleaned_data = {
            'old_password': self.user.password,
        }

        self.spy_on(SandboxAuthBackend.authenticate)

        message = (
            'Unexpected error when validating the password. Please contact '
            'the administrator.'
        )

        with self.assertRaisesMessage(ValidationError, message):
            form.clean_old_password()

        self.assertTrue(SandboxAuthBackend.authenticate.called)

    def test_update_password_auth_backend(self):
        """Testing ChangePasswordForm.save with error in
        auth_backend.update_password
        """
        form = ChangePasswordForm(page=None, request=self.request,
                                  user=self.user)
        form.cleaned_data = {
            'old_password': self.user.password,
            'password1': 'password1',
            'password2': 'password1',
        }

        self.spy_on(SandboxAuthBackend.update_password)

        form.save()
        self.assertTrue(SandboxAuthBackend.update_password.called)
