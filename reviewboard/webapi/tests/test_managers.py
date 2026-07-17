"""Unit tests for WebAPITokenManager.

Version Added:
    5.0.5
"""

from __future__ import annotations

import datetime

import kgb
from django.contrib.auth.models import User
from django.utils import timezone
from djblets.secrets.token_generators.vendor_checksum import \
    VendorChecksumTokenGenerator

from reviewboard.testing.testcase import TestCase
from reviewboard.webapi.models import WebAPIToken


class WebAPITokenManagerTests(kgb.SpyAgency, TestCase):
    """Unit tests for WebAPITokenManager.

    Version Added:
        5.0.5
    """

    #: The token info for created tokens.
    token_info = {'token_type': 'rbp'}

    def setUp(self) -> None:
        """Set up the test case."""
        super().setUp()

        self.token_generator_id = \
            VendorChecksumTokenGenerator.token_generator_id
        self.user = User.objects.create(username='test-user')

        set_time = timezone.make_aware(datetime.datetime(2023, 1, 2, 3))
        self.spy_on(timezone.now, op=kgb.SpyOpReturn(set_time))

    def test_get_or_create_client_token_default(self) -> None:
        """Testing WebAPITokenManager.get_or_create_client_token creates
        a token with default arguments
        """
        settings = {
            'client_token_expiration': 2,
        }

        with self.siteconfig_settings(settings):
            client_token, created = \
                WebAPIToken.objects.get_or_create_client_token(
                    client_name='Test',
                    user=self.user)

            self.assertTrue(created)
            self._assert_client_token_equals(
                token=client_token,
                client_name='Test',
                expires=(timezone.now() + datetime.timedelta(days=2)),
                note='API token automatically created for Test.',
                user=self.user)

    def test_get_or_create_client_token_custom_expires(self) -> None:
        """Testing WebAPITokenManager.get_or_create_client_token creates
        a token with a custom expiration date
        """
        client_token, created = WebAPIToken.objects.get_or_create_client_token(
            client_name='Test',
            expires=timezone.now() + datetime.timedelta(days=10),
            user=self.user)

        self.assertTrue(created)
        self._assert_client_token_equals(
            token=client_token,
            client_name='Test',
            expires=timezone.now() + datetime.timedelta(days=10),
            note='API token automatically created for Test.',
            user=self.user)

    def test_get_or_create_client_token_with_create_default_extra_data(
        self,
    ) -> None:
        """Testing WebAPITokenManager.get_or_create_client_token creates a
        token with a custom default extra_data
        """
        user = self.user

        # An existing non-client token. This shouldn't be returned.
        WebAPIToken.objects.generate_token(
            token_generator_id=self.token_generator_id,
            token_info=self.token_info,
            user=user,
        )

        client_token, created = WebAPIToken.objects.get_or_create_client_token(
            client_name='Test',
            user=self.user,
            default_extra_data={
                'mykey': ['myvalue'],
            },
        )

        self.assertTrue(created)
        self.assertEqual(client_token.extra_data, {
            'mykey': ['myvalue'],
            'client_name': 'Test',
        })

    def test_get_or_create_client_token_with_create_default_policy(
        self,
    ) -> None:
        """Testing WebAPITokenManager.get_or_create_client_token creates a
        token with a custom default policy
        """
        user = self.user

        # An existing non-client token. This shouldn't be returned.
        WebAPIToken.objects.generate_token(
            token_generator_id=self.token_generator_id,
            token_info=self.token_info,
            user=user,
        )

        client_token, created = WebAPIToken.objects.get_or_create_client_token(
            client_name='Test',
            user=self.user,
            default_policy={
                'resources': {
                    '*': {
                        'allow': ['DELETE'],
                    },
                },
            },
        )

        self.assertTrue(created)
        self.assertEqual(client_token.policy, {
            'resources': {
                '*': {
                    'allow': ['DELETE'],
                },
            },
        })

    def test_get_or_create_client_token_with_create_local_site(self) -> None:
        """Testing WebAPITokenManager.get_or_create_client_token creates a
        token with a provided Local Site
        """
        user = self.user
        token_info = self.token_info
        token_generator_id = self.token_generator_id

        local_site1 = self.create_local_site(name='local-site-1')
        local_site2 = self.create_local_site(name='local-site-2')

        # An existing client token on the global site.
        WebAPIToken.objects.generate_token(
            token_generator_id=token_generator_id,
            token_info=token_info,
            user=user,
            extra_data={
                'client_name': 'Test',
            },
        )

        # An existing client token on a different Local Site.
        WebAPIToken.objects.generate_token(
            token_generator_id=token_generator_id,
            token_info=token_info,
            user=user,
            extra_data={
                'client_name': 'Test',
            },
            local_site=local_site1,
        )

        client_token, created = WebAPIToken.objects.get_or_create_client_token(
            client_name='Test',
            user=user,
            local_site=local_site2,
        )

        self.assertTrue(created)
        self.assertEqual(client_token.local_site, local_site2)

    def test_get_or_create_client_token_custom_expires_none(self) -> None:
        """Testing WebAPITokenManager.get_or_create_client_token creates
        a token with no expiration date when expires=None
        """
        client_token, created = WebAPIToken.objects.get_or_create_client_token(
            client_name='Test',
            expires=None,
            user=self.user)

        self.assertTrue(created)
        self._assert_client_token_equals(
            token=client_token,
            client_name='Test',
            expires=None,
            note='API token automatically created for Test.',
            user=self.user)

    def test_get_or_create_client_token_with_existing_extra_data(self) -> None:
        """Testing WebAPITokenManager.get_or_create_client_token returns
        an existing client token when multiple fields exist in the extra data
        """
        token = WebAPIToken.objects.generate_token(
            extra_data={
                'field_1': 'Some field',
                'client_name': 'Test',
                'field_2': 25,
            },
            token_generator_id=self.token_generator_id,
            token_info=self.token_info,
            user=self.user)

        # An existing non-client token. This shouldn't be returned.
        WebAPIToken.objects.generate_token(
            token_generator_id=self.token_generator_id,
            token_info=self.token_info,
            user=self.user)

        client_token, created = WebAPIToken.objects.get_or_create_client_token(
            client_name='Test',
            user=self.user)

        self.assertFalse(created)
        self.assertEqual(token, client_token)

    def test_get_or_create_client_token_with_existing(self) -> None:
        """Testing WebAPITokenManager.get_or_create_client_token returns
        an existing client token
        """
        token = WebAPIToken.objects.generate_token(
            extra_data={
                'client_name': 'Test',
            },
            token_generator_id=self.token_generator_id,
            token_info=self.token_info,
            user=self.user)

        # An existing non-client token. This shouldn't be returned.
        WebAPIToken.objects.generate_token(
            token_generator_id=self.token_generator_id,
            token_info=self.token_info,
            user=self.user)

        client_token, created = WebAPIToken.objects.get_or_create_client_token(
            client_name='Test',
            user=self.user)

        self.assertFalse(created)
        self.assertEqual(token, client_token)

    def test_get_or_create_client_token_with_existing_ignore_deprecated(
        self,
    ) -> None:
        """Testing WebAPITokenManager.get_or_create_client_token returns
        an existing client token and ignore_deprecated=True
        """
        user = self.user

        # A deprecated API token.
        token = WebAPIToken.objects.generate_token(
            extra_data={
                'client_name': 'Test',
            },
            token_generator_id='legacy_sha1',
            token_info={
                'attempt': 1,
                'user': user,
            },
            user=user,
        )

        client_token, created = WebAPIToken.objects.get_or_create_client_token(
            client_name='Test',
            user=user,
            ignore_deprecated=True,
        )

        self.assertTrue(created)
        self.assertNotEqual(token, client_token)

    def test_get_or_create_client_token_with_expired(self) -> None:
        """Testing WebAPITokenManager.get_or_create_client_token creates a new
        client token when the existing client token is expired
        """
        expired_token = WebAPIToken.objects.generate_token(
            expires=timezone.now() - datetime.timedelta(days=2),
            extra_data={
                'client_name': 'Test',
            },
            token_generator_id=self.token_generator_id,
            token_info=self.token_info,
            user=self.user)

        # An existing non-client token. This shouldn't be returned.
        WebAPIToken.objects.generate_token(
            expires=timezone.now() + datetime.timedelta(days=50),
            token_generator_id=self.token_generator_id,
            token_info=self.token_info,
            user=self.user)

        client_token, created = WebAPIToken.objects.get_or_create_client_token(
            client_name='Test',
            user=self.user)

        self.assertTrue(created)
        self.assertNotEqual(expired_token, client_token)

    def test_get_or_create_client_token_with_expires_soon(self) -> None:
        """Testing WebAPITokenManager.get_or_create_client_token creates a new
        client token when the existing client token is expiring soon (under
        the minimum validity period)
        """
        user = self.user
        token_info = self.token_info
        token_generator_id = self.token_generator_id

        expired_token = WebAPIToken.objects.generate_token(
            expires=timezone.now() + datetime.timedelta(seconds=4 * 60 + 59),
            extra_data={
                'client_name': 'Test',
            },
            token_generator_id=token_generator_id,
            token_info=token_info,
            user=user,
        )

        # An existing non-client token. This shouldn't be returned.
        WebAPIToken.objects.generate_token(
            expires=timezone.now() + datetime.timedelta(days=50),
            token_generator_id=token_generator_id,
            token_info=token_info,
            user=user)

        client_token, created = WebAPIToken.objects.get_or_create_client_token(
            client_name='Test',
            user=user,
        )

        self.assertTrue(created)
        self.assertNotEqual(expired_token, client_token)

    def test_get_or_create_client_token_with_invalid(self) -> None:
        """Testing WebAPITokenManager.get_or_create_client_token creates a new
        client token when the existing client token is invalid
        """
        expired_token = WebAPIToken.objects.generate_token(
            expires=None,
            extra_data={
                'client_name': 'Test',
            },
            token_generator_id=self.token_generator_id,
            token_info=self.token_info,
            user=self.user,
            valid=False)

        # An existing non-client token. This shouldn't be returned.
        WebAPIToken.objects.generate_token(
            expires=timezone.now() + datetime.timedelta(days=50),
            token_generator_id=self.token_generator_id,
            token_info=self.token_info,
            user=self.user)

        client_token, created = WebAPIToken.objects.get_or_create_client_token(
            client_name='Test',
            user=self.user)

        self.assertTrue(created)
        self.assertNotEqual(expired_token, client_token)

    def test_get_or_create_client_token_sorted_by_expires(self) -> None:
        """Testing WebAPITokenManager.get_or_create_client_token returns the
        client token with the furthest expiration date when multiple ones exist
        """
        WebAPIToken.objects.generate_token(
            expires=timezone.now() - datetime.timedelta(days=2),
            extra_data={
                'client_name': 'Test',
            },
            token_generator_id=self.token_generator_id,
            token_info=self.token_info,
            user=self.user)

        # This non-client token with the furthest expiration shouldn't
        # be returned.
        WebAPIToken.objects.generate_token(
            expires=timezone.now() + datetime.timedelta(days=50),
            token_generator_id=self.token_generator_id,
            token_info=self.token_info,
            user=self.user)

        token_furthest = WebAPIToken.objects.generate_token(
            expires=timezone.now() + datetime.timedelta(days=30),
            extra_data={
                'client_name': 'Test',
            },
            token_generator_id=self.token_generator_id,
            token_info=self.token_info,
            user=self.user)

        client_token, created = WebAPIToken.objects.get_or_create_client_token(
            client_name='Test',
            user=self.user)

        self.assertFalse(created)
        self.assertEqual(token_furthest, client_token)

    def test_get_or_create_client_token_sorted_by_expires_none(self) -> None:
        """Testing WebAPITokenManager.get_or_create_client_token returns the
        client token with no expiration date when multiple ones exist
        """
        token_furthest = WebAPIToken.objects.generate_token(
            expires=None,
            extra_data={
                'client_name': 'Test',
            },
            token_generator_id=self.token_generator_id,
            token_info=self.token_info,
            user=self.user)

        WebAPIToken.objects.generate_token(
            expires=timezone.now() + datetime.timedelta(days=365),
            extra_data={
                'client_name': 'Test',
            },
            token_generator_id=self.token_generator_id,
            token_info=self.token_info,
            user=self.user)

        client_token, created = WebAPIToken.objects.get_or_create_client_token(
            client_name='Test',
            user=self.user)

        self.assertFalse(created)
        self.assertEqual(token_furthest, client_token)

    def _assert_client_token_equals(
        self,
        token: WebAPIToken,
        client_name: str,
        expires: datetime.datetime | None,
        note: str,
        user: User,
    ) -> None:
        """Assert that the client token matches the given values.

        Args:
            token (reviewboard.webapi.models.WebAPIToken):
                The token.

            client_name (str):
                The client for the token.

            expires (datetime.datetime):
                The expiration date for the token.

            note (str):
                The note for the token.

            user (django.contrib.auth.models.User):
                The user for the token.

        Raises:
            AssertionError:
                The token is not invalid.
        """
        self.assertEqual(token.user, user)
        self.assertEqual(token.extra_data['client_name'], client_name)
        self.assertEqual(token.note, note)
        self.assertEqual(token.expires, expires)
