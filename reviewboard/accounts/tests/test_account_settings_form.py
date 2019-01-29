"""Unit tests for reviewboard.accounts.forms.pages.AccountSettingsForm."""

from __future__ import unicode_literals

from django.contrib.auth.models import AnonymousUser, User
from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.sessions.middleware import SessionMiddleware
from django.test.client import RequestFactory
from django.views.generic.base import View
from djblets.testing.decorators import add_fixtures

from reviewboard.accounts.forms.pages import AccountSettingsForm
from reviewboard.accounts.models import Profile
from reviewboard.accounts.pages import AccountSettingsPage
from reviewboard.testing import TestCase


class AccountSettingsFormTests(TestCase):
    """Unit tests for reviewboard.accounts.forms.pages.AccountSettingsForm."""

    @classmethod
    def setUpClass(cls):
        """Set up the test class."""
        super(AccountSettingsFormTests, cls).setUpClass()

        cls._request_factory = RequestFactory()
        cls._middleware = [
            SessionMiddleware(),
            MessageMiddleware(),
        ]

    @add_fixtures(['test_users'])
    def test_save_syntax_highlighting_disabled(self):
        """Testing AccountSettingsForm.save() with
        diffviewer_syntax_highlighting disabled
        """
        view = View()
        user = User.objects.get(username='doc')

        profile = user.get_profile()
        profile.syntax_highlighting = True
        profile.save(update_fields=('syntax_highlighting',))

        request = self._build_request(user)
        page = AccountSettingsPage(view, request, user)

        settings = {'diffviewer_syntax_highlighting': False}

        with self.siteconfig_settings(settings):
            form = AccountSettingsForm(page, request, user, data={
                'syntax_highlighting': False,
                'timezone': profile.timezone,
            })

            self.assertTrue(form.is_valid())
            form.save()

        profile = Profile.objects.get(pk=profile.pk)
        self.assertTrue(profile.syntax_highlighting)

    def _build_request(self, user=None):
        """Make a request and process it through middleware.

        Args:
            user (django.contrib.auth.models.User, optional):
                The user for the request to be authenticated for.

                If not provided, an
                :py:class:`~django.contrib.auth.models.AnonymousUser`
                will be assigned instead.

        Returns:
            django.http.HttpRequest:
            The created request.
        """
        if user is None:
            user = AnonymousUser()

        request = self._request_factory.request()
        request.user = user

        for middleware in self._middleware:
            middleware.process_request(request)

        return request
