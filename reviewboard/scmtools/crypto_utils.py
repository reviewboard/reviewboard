from __future__ import unicode_literals

import base64
import os
import warnings

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from django.conf import settings
from django.utils import six

from reviewboard.deprecation import RemovedInReviewBoard40Warning


AES_BLOCK_SIZE = algorithms.AES.block_size / 8


def _create_cipher(iv, key):
    """Create a cipher for use in symmetric encryption/decryption.

    This will use AES encryption in CFB mode (using an 8-bit shift register)
    and a random IV.

    Args:
        iv (bytes):
            The random IV to use for the cipher.

        key (bytes):
            The encryption key to use.

    Returns:
        cryptography.hazmat.primitives.cipher.Cipher:
        The cipher to use for encryption/decryption.

    Raises:
        ValueError:
            The encryption key was not in the right format.
    """
    if not isinstance(key, bytes):
        raise ValueError('The encryption key must be of type "bytes", not "%s"'
                         % type(key))

    return Cipher(algorithms.AES(key),
                  modes.CFB8(iv),
                  default_backend())


def get_default_aes_encryption_key():
    """Return the default AES encryption key for the install.

    The default key is the first 16 characters (128 bits) of
    :django:setting:`SECRET_KEY`.

    Returns:
        bytes:
        The default encryption key.
    """
    return settings.SECRET_KEY[:16].encode('utf8')


def aes_encrypt(data, key=None):
    """Encrypt data using AES encryption.

    This uses AES encryption in CFB mode (using an 8-bit shift register) and a
    random IV (which will be prepended to the encrypted value). The encrypted
    data will be decryptable using the :py:func:`aes_decrypt` function.

    Args:
        data (bytes):
            The data to encrypt. If a unicode string is passed in, it will be
            encoded to UTF-8 first.

        key (bytes, optional):
            The optional custom encryption key to use. If not supplied, the
            default encryption key (from
            :py:func:`get_default_aes_encryption_key)` will be used.

    Returns:
        bytes:
        The resulting encrypted value, with the random IV prepended.

    Raises:
        ValueError:
            The encryption key was not in the right format.
    """
    if isinstance(data, six.text_type):
        data = data.encode('utf8')

    iv = os.urandom(AES_BLOCK_SIZE)
    cipher = _create_cipher(iv, key or get_default_aes_encryption_key())
    encryptor = cipher.encryptor()

    return iv + encryptor.update(data) + encryptor.finalize()


def aes_decrypt(data, key=None):
    """Decrypt AES-encrypted data.

    This will decrypt an AES-encrypted value in CFB mode (using an 8-bit
    shift register). It expects the 16-byte cipher IV to be prepended to the
    string.

    This is intended as a counterpart for :py:func:`aes_encrypt`.

    Args:
        data (bytes):
            The data to decrypt.

        key (bytes, optional):
            The optional custom encryption key to use. This must match the key
            used for encryption. If not supplied, the default encryption key
            (from :py:func:`get_default_aes_encryption_key)` will be used.

    Returns:
        bytes:
        The decrypted value.

    Raises:
        ValueError:
            The encryption key was not in the right format.
    """
    cipher = _create_cipher(data[:AES_BLOCK_SIZE],
                            key or get_default_aes_encryption_key())
    decryptor = cipher.decryptor()

    return decryptor.update(data[AES_BLOCK_SIZE:]) + decryptor.finalize()


def encrypt_password(password, key=None):
    """Encrypt a password and encode as Base64.

    The password will be encrypted using AES encryption in CFB mode (using an
    8-bit shift register), and serialized into Base64.

    Args:
        password (bytes):
            The password to encrypt. If a unicode string is passed in, it will
            be encoded to UTF-8 first.

        key (bytes, optional):
            The optional custom encryption key to use. If not supplied, the
            default encryption key (from
            :py:func:`get_default_aes_encryption_key)` will be used.

    Returns:
        bytes:
        The encrypted password encoded in Base64.

    Raises:
        ValueError:
            The encryption key was not in the right format.
    """
    return base64.b64encode(aes_encrypt(password, key=key))


def decrypt_password(encrypted_password, key=None):
    """Decrypt an encrypted password encoded in Base64.

    This will decrypt a Base64-encoded encrypted password (from
    :py:func:`encrypt_password`) into a usable password string.

    Args:
        encrypted_password (bytes):
            The Base64-encoded encrypted password to decrypt.

        key (bytes, optional):
            The optional custom encryption key to use. This must match the key
            used for encryption. If not supplied, the default encryption key
            (from :py:func:`get_default_aes_encryption_key)` will be used.

    Returns:
        bytes:
        The resulting password.

    Raises:
        ValueError:
            The encryption key was not in the right format.
    """
    return aes_decrypt(base64.b64decode(encrypted_password), key=key)


# The following are deprecated. They're likely not used anywhere, but we
# want to notify callers anyway.
def decrypt(data):
    """Decrypt AES-encrypted data.

    .. deprecated: 2.5.10

       Use :py:func:`aes_decrypt` instead.

    Args:
        data (bytes):
            The data to decrypt.

    Returns:
        bytes:
        The decrypted value.
    """
    warnings.warn('decrypt() is deprecated. Use aes_decrypt() instead.',
                  RemovedInReviewBoard40Warning)

    return aes_decrypt(data)


def encrypt(data):
    """Encrypt data using AES encryption.

    .. deprecated: 2.5.10

       Use :py:func:`aes_encrypt` instead.

    Args:
        data (bytes):
            The data to encrypt. If a unicode string is passed in, it will be
            encoded to UTF-8 first.

    Returns:
        bytes:
        The resulting encrypted value, with the random IV prepended.
    """
    warnings.warn('encrypt() is deprecated. Use aes_encrypt() instead.',
                  RemovedInReviewBoard40Warning)

    return aes_encrypt(data)
