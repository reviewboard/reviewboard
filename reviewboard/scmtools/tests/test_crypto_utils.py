from __future__ import unicode_literals

import warnings

from django.test.utils import override_settings

from reviewboard.scmtools.crypto_utils import (aes_decrypt,
                                               aes_encrypt,
                                               decrypt,
                                               decrypt_password,
                                               encrypt,
                                               encrypt_password,
                                               get_default_aes_encryption_key)
from reviewboard.testing.testcase import TestCase


@override_settings(SECRET_KEY='abcdefghijklmnopqrstuvwxyz012345')
class CryptoUtilsTests(TestCase):
    """Unit tests for reviewboard.scmtools.crypto_utils."""

    PLAIN_TEXT = 'this is a test 123 ^&*'
    CUSTOM_KEY = b'0123456789abcdef'

    def test_aes_decrypt(self):
        """Testing aes_decrypt"""
        # The encrypted value was made with PyCrypto, to help with
        # compatibility testing from older installs.
        encrypted = (
            b'\xfb\xdc\xb5h\x15\xa1\xb2\xdc\xec\xf1\x14\xa9\xc6\xab\xb2J\x10'
            b'\'\xd4\xf6&\xd4k9\x82\xf6\xb5\x8bmu\xc8E\x9c\xac\xc5\x04@B'
        )

        self.assertEqual(aes_decrypt(encrypted), self.PLAIN_TEXT)

    def test_aes_decrypt_with_custom_key(self):
        """Testing aes_decrypt with custom key"""
        # The encrypted value was made with PyCrypto, to help with
        # compatibility testing from older installs.
        encrypted = (
            b'\x9cd$e\xb1\x9e\xe0z\xb8[\x9e!\xf2h\x90\x8d\x82f%G4\xc2\xf0'
            b'\xda\x8dr\x81ER?S6\x12%7\x98\x89\x90'
        )

        self.assertEqual(aes_decrypt(encrypted, key=self.CUSTOM_KEY),
                         self.PLAIN_TEXT)

    def test_aes_encrypt(self):
        """Testing aes_encrypt"""
        # The encrypted value will change every time, since the iv changes,
        # so we can't compare a direct value. Instead, we need to ensure that
        # we can decrypt what we encrypt.
        self.assertEqual(aes_decrypt(aes_encrypt(self.PLAIN_TEXT)),
                         self.PLAIN_TEXT)

    def test_aes_encrypt_with_custom_key(self):
        """Testing aes_encrypt with custom key"""
        # The encrypted value will change every time, since the iv changes,
        # so we can't compare a direct value. Instead, we need to ensure that
        # we can decrypt what we encrypt.
        encrypted = aes_encrypt(self.PLAIN_TEXT, key=self.CUSTOM_KEY)

        self.assertEqual(aes_decrypt(encrypted, key=self.CUSTOM_KEY),
                         self.PLAIN_TEXT)

    def test_decrypt(self):
        """Testing decrypt (deprecated)"""
        # The encrypted value was made with PyCrypto, to help with
        # compatibility testing from older installs.
        encrypted = (
            b'\xfb\xdc\xb5h\x15\xa1\xb2\xdc\xec\xf1\x14\xa9\xc6\xab\xb2J\x10'
            b'\'\xd4\xf6&\xd4k9\x82\xf6\xb5\x8bmu\xc8E\x9c\xac\xc5\x04@B'
        )

        with warnings.catch_warnings(record=True) as w:
            self.assertEqual(decrypt(encrypted), self.PLAIN_TEXT)
            self.assertEqual(
                unicode(w[0].message),
                'decrypt() is deprecated. Use aes_decrypt() instead.')

    def test_encrypt(self):
        """Testing encrypt (deprecated)"""
        with warnings.catch_warnings(record=True) as w:
            # The encrypted value will change every time, since the iv changes,
            # so we can't compare a direct value. Instead, we need to ensure
            # that we can decrypt what we encrypt.
            self.assertEqual(aes_decrypt(encrypt(self.PLAIN_TEXT)),
                             self.PLAIN_TEXT)
            self.assertEqual(
                unicode(w[0].message),
                'encrypt() is deprecated. Use aes_encrypt() instead.')

    def test_decrypt_password(self):
        """Testing decrypt_password"""
        # The encrypted value was made with PyCrypto, to help with
        # compatibility testing from older installs.
        encrypted = b'AjsUGevO3UiVH7iN3zO9vxvqr5X5ozuAbOUByTATsitkhsih1Zc='

        self.assertEqual(decrypt_password(encrypted), self.PLAIN_TEXT)

    def test_decrypt_password_with_custom_key(self):
        """Testing decrypt_password with custom key"""
        # The encrypted value was made with PyCrypto, to help with
        # compatibility testing from older installs.
        encrypted = b'/pOO3VWHRXd1ZAeHZo8MBGQsNClD4lS7XK9WAydt8zW/ob+e63E='

        self.assertEqual(decrypt_password(encrypted, key=self.CUSTOM_KEY),
                         self.PLAIN_TEXT)

    def test_encrypt_password(self):
        """Testing encrypt_password"""
        # The encrypted value will change every time, since the iv changes,
        # so we can't compare a direct value. Instead, we need to ensure that
        # we can decrypt what we encrypt.
        self.assertEqual(
            decrypt_password(encrypt_password(self.PLAIN_TEXT)),
            self.PLAIN_TEXT)

    def test_encrypt_password_with_custom_key(self):
        """Testing encrypt_password with custom key"""
        # The encrypted value will change every time, since the iv changes,
        # so we can't compare a direct value. Instead, we need to ensure that
        # we can decrypt what we encrypt.
        encrypted = encrypt_password(self.PLAIN_TEXT, key=self.CUSTOM_KEY)

        self.assertEqual(decrypt_password(encrypted, key=self.CUSTOM_KEY),
                         self.PLAIN_TEXT)

    def test_get_default_aes_encryption_key(self):
        """Testing get_default_aes_encryption_key"""
        self.assertEqual(get_default_aes_encryption_key(), 'abcdefghijklmnop')
