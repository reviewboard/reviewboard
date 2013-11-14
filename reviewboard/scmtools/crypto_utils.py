from __future__ import unicode_literals

import base64
try:
    from Crypto import Random
except ImportError:
    from Crypto.Util.randpool import RandomPool as Random
from Crypto.Cipher import AES
from django.conf import settings


def _create_cipher(iv):
    return AES.new(settings.SECRET_KEY[:16], AES.MODE_CFB, iv)


def encrypt(data):
    """Encrypts data using AES encryption.

    The encrypted data will be decryptable using the decrypt() function.
    The first 16 characters of settings.SECRET_KEY are used as the
    encryption key.

    The resulting data will be a binary blob.
    """
    iv = Random.new().read(AES.block_size)
    cipher = _create_cipher(iv)
    return iv + cipher.encrypt(data)


def decrypt(data):
    """Decrypts data encrypted using the encrypt() function."""
    cipher = _create_cipher(data[:AES.block_size])
    return cipher.decrypt(data[AES.block_size:])


def encrypt_password(password):
    """Encrypts a password.

    The password will be encrypted using AES encryption, and serialized
    into base64.
    """
    return base64.b64encode(encrypt(password))


def decrypt_password(encrypted_password):
    """Decrypts a password.

    This will decrypt a base64-encoded encrypted password into a usable
    password string.
    """
    return decrypt(base64.b64decode(encrypted_password))
