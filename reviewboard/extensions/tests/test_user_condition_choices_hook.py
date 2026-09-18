"""Tests for reviewboard.extensions.hooks.UserConditionChoicesHook.

Version Added:
    9.0
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from djblets.conditions.choices import BaseConditionStringChoice

from reviewboard.accounts.conditions import (
    UserConditionChoiceMixin,
    user_condition_choices,
)
from reviewboard.extensions.hooks import UserConditionChoicesHook
from reviewboard.extensions.tests.testcases import BaseExtensionHookTestCase

if TYPE_CHECKING:
    from django.contrib.auth.models import User


class _MyUserRoleChoice(UserConditionChoiceMixin,
                        BaseConditionStringChoice):
    choice_id = 'my-user-role'
    name = 'User role'

    def get_match_value(self, user: User, **kwargs) -> str | None:
        return user.get_profile().extra_data.get('my_role')


class UserConditionChoicesHookTests(BaseExtensionHookTestCase):
    """Tests for UserConditionChoicesHook.

    Version Added:
        9.0
    """

    def test_register(self) -> None:
        """Testing UserConditionChoicesHook initializing"""
        UserConditionChoicesHook(self.extension, [
            _MyUserRoleChoice,
        ])

        self.assertIn(_MyUserRoleChoice, user_condition_choices)

    def test_unregister(self) -> None:
        """Testing UserConditionChoicesHook uninitializing"""
        hook = UserConditionChoicesHook(self.extension, [
            _MyUserRoleChoice,
        ])
        hook.disable_hook()

        self.assertNotIn(_MyUserRoleChoice, user_condition_choices)
