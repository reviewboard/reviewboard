"""Unit tests for reviewboard.accounts.forms.pages.ThemeForm.

Version Added:
    7.0
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import kgb
from django.contrib import messages

from reviewboard.accounts.forms.pages import ThemeForm
from reviewboard.testing import TestCase

if TYPE_CHECKING:
    from django.contrib.auth.models import User
    from django.http import HttpRequest

    from reviewboard.accounts.models import Profile


class ThemeFormTests(kgb.SpyAgency, TestCase):
    """Unit tests for ThemeForm.

    Version Added:
        7.0
    """

    ######################
    # Instance variables #
    ######################

    request: HttpRequest
    profile: Profile
    user: User

    def setUp(self) -> None:
        super(ThemeFormTests, self).setUp()

        self.request = self.create_http_request()
        self.user = self.create_user()
        self.profile = self.user.get_profile()

        # Suppresses MessageFailure Exception at the end of save()
        self.spy_on(messages.add_message)

    def test_init(self) -> None:
        """Testing ThemeForm.__init__"""
        form = ThemeForm(page=None,
                         request=self.request,
                         user=self.user)

        self.assertEqual(form.fields['ui_theme'].choices, [
            ('default', 'Default appearance (System theme)'),
            ('light', 'Light mode'),
            ('dark', 'Dark mode'),
        ])

    def test_load_with_defaults(self) -> None:
        """Testing ThemeForm.load with profile defaults"""
        form = ThemeForm(page=None,
                         request=self.request,
                         user=self.user)

        form.load()

        self.assertEqual(form['ui_theme'].initial, 'default')

    def test_load_with_ui_theme(self) -> None:
        """Testing ThemeForm.load with ui_theme"""
        self.profile.ui_theme_id = 'system'

        form = ThemeForm(page=None,
                         request=self.request,
                         user=self.user)
        form.load()

        self.assertEqual(form['ui_theme'].initial, 'system')

    def test_save(self) -> None:
        """Testing ThemeForm.save"""
        form = ThemeForm(
            page=None,
            request=self.request,
            user=self.user,
            data={
                'ui_theme': 'dark',
            })
        form.is_valid()
        self.assertTrue(form.is_valid())
        form.save()

        self.assertEqual(self.profile.ui_theme_id, 'dark')

        self.assertSpyCalledWith(
            messages.add_message,
            self.request,
            messages.INFO,
            'Your appearance settings have been saved.')
