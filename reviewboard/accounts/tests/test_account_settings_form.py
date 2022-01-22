"""Unit tests for reviewboard.accounts.forms.pages.AccountSettingsForm."""

from django.contrib.auth.models import User
from django.views.generic.base import View
from djblets.testing.decorators import add_fixtures

from reviewboard.accounts.forms.pages import AccountSettingsForm
from reviewboard.accounts.models import Profile
from reviewboard.accounts.pages import AccountSettingsPage
from reviewboard.testing import TestCase


class AccountSettingsFormTests(TestCase):
    """Unit tests for reviewboard.accounts.forms.pages.AccountSettingsForm."""

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

        request = self.create_http_request()
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
