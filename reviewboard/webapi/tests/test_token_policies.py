"""Unit tests for reviewboard.webapi.token_policies.

Version Added:
    9.0
"""

from __future__ import annotations

from djblets.registries.errors import AlreadyRegisteredError

from reviewboard.testing import TestCase
from reviewboard.webapi.models import WebAPIToken
from reviewboard.webapi.token_policies import (
    BaseWebAPITokenPolicy,
    FullAccessWebAPITokenPolicy,
    ReadOnlyWebAPITokenPolicy,
    WebAPITokenPolicyRegistry,
    webapi_token_policies,
)


class WebAPITokenPolicyRegistryTests(TestCase):
    """Unit tests for WebAPITokenPolicyRegistry.

    Version Added:
        9.0
    """

    def test_get_token_policy_with_read_only(self) -> None:
        """Testing WebAPITokenPolicyRegistry.get_token_policy with
        "read-only" ID
        """
        self.assertIs(webapi_token_policies.get_token_policy('read-only'),
                      ReadOnlyWebAPITokenPolicy)

    def test_get_token_policy_with_read_write(self) -> None:
        """Testing WebAPITokenPolicyRegistry.get_token_policy with
        "read-write" ID
        """
        self.assertIs(webapi_token_policies.get_token_policy('read-write'),
                      FullAccessWebAPITokenPolicy)

    def test_get_token_policy_with_unknown_id(self) -> None:
        """Testing WebAPITokenPolicyRegistry.get_token_policy with unknown ID
        """
        self.assertIsNone(webapi_token_policies.get_token_policy('xxx'))

    def test_get_defaults(self) -> None:
        """Testing WebAPITokenPolicyRegistry default registrations"""
        registry = WebAPITokenPolicyRegistry()

        self.assertEqual(
            list(registry),
            [
                FullAccessWebAPITokenPolicy,
                ReadOnlyWebAPITokenPolicy,
            ])

    def test_register_with_duplicate_id(self) -> None:
        """Testing WebAPITokenPolicyRegistry.register with a duplicate ID"""
        class MyTokenPolicy(BaseWebAPITokenPolicy):
            token_policy_id = 'read-only'
            name = 'My Policy'

        registry = WebAPITokenPolicyRegistry()

        message = (
            f"Could not register {MyTokenPolicy!r}: another item "
            f"({ReadOnlyWebAPITokenPolicy!r}) is already registered with "
            f"token_policy_id = read-only."
        )

        with self.assertRaisesMessage(AlreadyRegisteredError, message):
            registry.register(MyTokenPolicy)

        self.assertIs(registry.get_token_policy('read-only'),
                      ReadOnlyWebAPITokenPolicy)


class BaseWebAPITokenPolicyTests(TestCase):
    """Unit tests for BaseWebAPITokenPolicy.

    Version Added:
        9.0
    """

    def test_default_token_policy_doc(self) -> None:
        """Testing BaseWebAPITokenPolicy.default_token_policy_doc defaults to
        an empty policy
        """
        self.assertEqual(BaseWebAPITokenPolicy.default_token_policy_doc, {})


class ReadOnlyWebAPITokenPolicyTests(TestCase):
    """Unit tests for ReadOnlyWebAPITokenPolicy.

    Version Added:
        9.0
    """

    def test_attrs(self) -> None:
        """Testing ReadOnlyWebAPITokenPolicy attributes"""
        self.assertAttrsEqual(
            ReadOnlyWebAPITokenPolicy,
            {
                'default_token_policy_doc': {
                    'resources': {
                        '*': {
                            'allow': ['GET', 'HEAD', 'OPTIONS'],
                            'block': ['*'],
                        },
                    },
                },
                'name': 'Read-only',
                'token_policy_id': 'read-only',
            },
        )

    def test_policy_doc_valid(self) -> None:
        """Testing ReadOnlyWebAPITokenPolicy has a valid policy document"""
        WebAPIToken.validate_policy(
            ReadOnlyWebAPITokenPolicy.default_token_policy_doc,
        )


class FullAccessWebAPITokenPolicyTests(TestCase):
    """Unit tests for FullAccessWebAPITokenPolicy.

    Version Added:
        9.0
    """

    def test_attrs(self) -> None:
        """Testing FullAccessWebAPITokenPolicy attributes"""
        self.assertAttrsEqual(
            FullAccessWebAPITokenPolicy,
            {
                'default_token_policy_doc': {},
                'name': 'Full access',
                'token_policy_id': 'read-write',
            },
        )

    def test_policy_doc_valid(self) -> None:
        """Testing FullAccessWebAPITokenPolicy has a valid policy document"""
        WebAPIToken.validate_policy(
            FullAccessWebAPITokenPolicy.default_token_policy_doc,
        )
