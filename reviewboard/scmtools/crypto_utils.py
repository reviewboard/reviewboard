from __future__ import unicode_literals

import base64
import os

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from django.conf import settings


AES_BLOCK_SIZE = algorithms.AES.block_size / 8


def _create_cipher(iv):
    """Create a cipher for use in symmetric encryption/decryption.

    This will use AES encryption in CFB mode (using an 8-bit shift register)
    and a random IV.

    Args:
        iv (bytes):
            The random IV to use for the cipher.

    Returns:
        cryptography.hazmat.primitives.cipher.Cipher:
        The cipher to use for encryption/decryption.
    """
    return Cipher(algorithms.AES(settings.SECRET_KEY[:16].encode('utf8')),
                  modes.CFB8(iv),
                  default_backend())


def encrypt(data):
    """Encrypt data using AES encryption.

    This uses AES encryption in CFB mode (using an 8-bit shift register) and a
    random IV (which will be prepended to the encrypted value). The encrypted
    data will be decryptable using the :py:func:`decrypt` function.

    Args:
        data (bytes):
            The data to encrypt. If a unicode string is passed in, it will be
            encoded to UTF-8 first.

    Returns:
        bytes:
        The resulting encrypted value, with the random IV prepended.
    """
    if isinstance(data, unicode):
        data = data.encode('utf8')

    iv = os.urandom(AES_BLOCK_SIZE)
    cipher = _create_cipher(iv)
    encryptor = cipher.encryptor()

    return iv + encryptor.update(data) + encryptor.finalize()


def decrypt(data):
    """Decrypt AES-encrypted data.

    This will decrypt an AES-encrypted value in CFB mode (using an 8-bit
    shift register). It expects the 16-byte cipher IV to be prepended to the
    string.

    This is intended as a counterpart for :py:func:`encrypt`.

    Args:
        data (bytes):
            The data to decrypt.

    Returns:
        bytes:
        The decrypted value.
    """
    cipher = _create_cipher(data[:AES_BLOCK_SIZE])
    decryptor = cipher.decryptor()

    return decryptor.update(data[AES_BLOCK_SIZE:]) + decryptor.finalize()


def encrypt_password(password):
    """Encrypt a password and encode as Base64.

    The password will be encrypted using AES encryption in CFB mode (using an
    8-bit shift register), and serialized into Base64.

    Args:
        password (bytes):
            The password to encrypt. If a unicode string is passed in, it will
            be encoded to UTF-8 first.

    Returns:
        bytes:
        The encrypted password encoded in Base64.
    """
    return base64.b64encode(encrypt(password))


def decrypt_password(encrypted_password):
    """Decrypt an encrypted password encoded in Base64.

    This will decrypt a Base64-encoded encrypted password (from
    :py:func:`encrypt_password`) into a usable password string.

    Args:
        encrypted_password (bytes):
            The Base64-encoded encrypted password to decrypt.

    Returns:
        bytes:
        The resulting password.
    """
    return decrypt(base64.b64decode(encrypted_password))
