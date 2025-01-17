"""Tests for reviewboard.extensions.hooks.UserDetailsProviderHook.

Version Added:
    7.1
"""

from __future__ import annotations

from reviewboard.accounts.user_details import (BaseUserDetailsProvider,
                                               user_details_provider_registry)
from reviewboard.extensions.hooks import UserDetailsProviderHook
from reviewboard.extensions.tests.testcases import BaseExtensionHookTestCase


class MyUserDetailsProvider(BaseUserDetailsProvider):
    user_details_provider_id = 'my-user-details-provider'


class UserDetailsProviderHookTests(BaseExtensionHookTestCase):
    """Tests for UserDetailsProviderHook."""

    def test_register(self) -> None:
        """Testing UserDetailsProviderHook initializing"""
        provider = MyUserDetailsProvider()
        UserDetailsProviderHook(self.extension, provider)

        self.assertIs(
            user_details_provider_registry.get_user_details_provider(
                'my-user-details-provider'),
            provider)

    def test_unregister(self) -> None:
        """Testing UserDetailsProviderHook uninitializing"""
        hook = UserDetailsProviderHook(self.extension, MyUserDetailsProvider())
        hook.disable_hook()

        self.assertIsNone(
            user_details_provider_registry.get_user_details_provider(
                'my-user-details-provider'))
