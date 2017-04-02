from __future__ import unicode_literals

from django.test.utils import override_settings

from reviewboard.scmtools.crypto_utils import (decrypt,
                                               decrypt_password,
                                               encrypt,
                                               encrypt_password)
from reviewboard.testing.testcase import TestCase


@override_settings(SECRET_KEY='abcdefghijklmnopqrstuvwxyz012345')
class CryptoUtilsTests(TestCase):
    """Unit tests for reviewboard.scmtools.crypto_utils."""

    PLAIN_TEXT = 'this is a test 123 ^&*'

    def test_decrypt(self):
        """Testing decrypt"""
        # The encrypted value was made with PyCrypto, to help with
        # compatibility testing from older installs.
        encrypted = (
            b'\xfb\xdc\xb5h\x15\xa1\xb2\xdc\xec\xf1\x14\xa9\xc6\xab\xb2J\x10'
            b'\'\xd4\xf6&\xd4k9\x82\xf6\xb5\x8bmu\xc8E\x9c\xac\xc5\x04@B'
        )

        self.assertEqual(decrypt(encrypted), self.PLAIN_TEXT)

    def test_encrypt(self):
        """Testing encrypt"""
        # The encrypted value will change every time, since the iv changes,
        # so we can't compare a direct value. Instead, we need to ensure that
        # we can decrypt what we encrypt.
        self.assertEqual(decrypt(encrypt(self.PLAIN_TEXT)),
                         self.PLAIN_TEXT)

    def test_decrypt_password(self):
        """Testing decrypt_password"""
        # The encrypted value was made with PyCrypto, to help with
        # compatibility testing from older installs.
        encrypted = b'AjsUGevO3UiVH7iN3zO9vxvqr5X5ozuAbOUByTATsitkhsih1Zc='

        self.assertEqual(decrypt_password(encrypted), self.PLAIN_TEXT)

    def test_encrypt_password(self):
        """Testing encrypt_password"""
        # The encrypted value will change every time, since the iv changes,
        # so we can't compare a direct value. Instead, we need to ensure that
        # we can decrypt what we encrypt.
        self.assertEqual(
            decrypt_password(encrypt_password(self.PLAIN_TEXT)),
            self.PLAIN_TEXT)
