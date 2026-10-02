"""Unit tests for reviewboard.extensions.hooks.WebAPITokenPoliciesHook.

Version Added:
    9.0
"""

from __future__ import annotations

from reviewboard.extensions.hooks import WebAPITokenPoliciesHook
from reviewboard.extensions.tests.testcases import BaseExtensionHookTestCase
from reviewboard.webapi.token_policies import (
    BaseWebAPITokenPolicy,
    FullAccessWebAPITokenPolicy,
    ReadOnlyWebAPITokenPolicy,
    webapi_token_policies,
)


class _MyTokenPolicy(BaseWebAPITokenPolicy):
    token_policy_id = 'my-policy'
    name = 'My Policy'

    default_token_policy_doc = {
        'resources': {
            '*': {
                'allow': ['GET'],
                'block': ['*'],
            },
        },
    }


class WebAPITokenPoliciesHookTests(BaseExtensionHookTestCase):
    """Unit tests for WebAPITokenPoliciesHook.

    Version Added:
        9.0
    """

    def test_register(self) -> None:
        """Testing WebAPITokenPoliciesHook initializing"""
        extension = self.extension
        assert extension is not None

        WebAPITokenPoliciesHook(extension, [_MyTokenPolicy])

        self.assertIs(webapi_token_policies.get_token_policy('my-policy'),
                      _MyTokenPolicy)

        # The built-in policies should still be available.
        self.assertIs(webapi_token_policies.get_token_policy('read-only'),
                      ReadOnlyWebAPITokenPolicy)
        self.assertIs(webapi_token_policies.get_token_policy('read-write'),
                      FullAccessWebAPITokenPolicy)

    def test_unregister(self) -> None:
        """Testing WebAPITokenPoliciesHook uninitializing"""
        extension = self.extension
        assert extension is not None

        hook = WebAPITokenPoliciesHook(extension, [_MyTokenPolicy])

        # Disable that hook to unregister it.
        hook.disable_hook()

        self.assertIsNone(webapi_token_policies.get_token_policy('my-policy'))
