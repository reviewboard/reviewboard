"""Authentication helpers for GitHub App connections.

These build the JSON Web Tokens used to authenticate as a GitHub App. A JWT
signed with the app's private key authenticates app-level API calls, such as
minting installation access tokens or reading installation details.

The logic lives here, rather than on the client, so both the hosting service
client and the admin connection views can build app JWTs without depending on
each other.

Version Added:
    9.0
"""

from __future__ import annotations

import base64
import json
import time
from typing import TYPE_CHECKING

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from reviewboard.scmtools.crypto_utils import (
    decrypt_password,
    encrypt_password,
)

if TYPE_CHECKING:
    from reviewboard.hostingsvcs.github.accounts import GitHubAppRecordData


#: The offset for the expiration timestamp.
#:
#: Version Added:
#:     9.0
_EXPIRATION_OFFSET = 600


#: The offset for the issued-at timestamp.
#:
#: Version Added:
#:     9.0
_ISSUED_AT_OFFSET = -60


def _b64url(
    raw: bytes,
) -> bytes:
    """Return URL-safe Base64-encoded data without padding.

    This is the encoding used for the segments of a JWT.

    Version Added:
        9.0

    Args:
        raw (bytes):
            The data to encode.

    Returns:
        bytes:
        The encoded data.
    """
    return base64.urlsafe_b64encode(raw).rstrip(b'=')


def load_app_private_key(
    github_app: GitHubAppRecordData,
) -> str:
    """Return the decrypted PEM private key from app-record data.

    The PEM private key is Base64-encoded before encryption, because
    :py:func:`~reviewboard.scmtools.crypto_utils.decrypt_password` rejects
    multi-line content. This reverses that transform.

    Version Added:
        9.0

    Args:
        github_app (reviewboard.hostingsvcs.github.accounts.
                    GitHubAppRecordData):
            The ``github_app`` data stored on the app-record account.

    Returns:
        str:
        The decrypted PEM private key.
    """
    return base64.b64decode(
        decrypt_password(github_app.private_key)).decode('utf-8')


def encrypt_app_private_key(
    private_key_pem: str,
) -> str:
    """Validate a PEM private key and return its encrypted form.

    This is the inverse of :py:func:`load_app_private_key`. The key is checked
    to be a usable RSA private key before it is stored, so a bad paste is
    caught at entry rather than when the next app JWT is signed. The PEM is
    Base64-encoded before encryption because
    :py:func:`~reviewboard.scmtools.crypto_utils.encrypt_password` is paired
    with a decrypt that rejects multi-line content.

    Version Added:
        9.0

    Args:
        private_key_pem (str):
            The PEM private key to store.

    Returns:
        str:
        The encrypted, storage-ready private key.

    Raises:
        ValueError:
            The value is not a valid RSA PEM private key.
    """
    try:
        key = serialization.load_pem_private_key(
            private_key_pem.encode('utf-8'),
            password=None)
    except (ValueError, TypeError) as e:
        raise ValueError(
            'The private key is not a valid PEM private key.'
        ) from e

    if not isinstance(key, rsa.RSAPrivateKey):
        raise ValueError('The private key must be an RSA private key.')

    return encrypt_password(
        base64.b64encode(private_key_pem.encode('utf-8'))
        .decode('ascii'))


def build_app_jwt(
    *,
    app_id: int,
    private_key_pem: str,
) -> str:
    """Build a JWT for authenticating as a GitHub App.

    The JWT is signed with the app's private key using RS256. It is used for
    app-level API requests, such as minting installation access tokens or
    reading installation details.

    Version Added:
        9.0

    Args:
        app_id (int):
            The GitHub App's ID, used as the ``iss`` claim.

        private_key_pem (str):
            The app's PEM private key.

    Returns:
        str:
        The encoded, signed JWT.
    """
    now = int(time.time())
    header = {
        'alg': 'RS256',
        'typ': 'JWT',
    }
    claims = {
        'iss': app_id,
        'iat': now + _ISSUED_AT_OFFSET,
        'exp': now + _EXPIRATION_OFFSET,
    }

    signing_input = b'.'.join([
        _b64url(json.dumps(header, separators=(',', ':')).encode('utf-8')),
        _b64url(json.dumps(claims, separators=(',', ':')).encode('utf-8')),
    ])

    key = serialization.load_pem_private_key(
        private_key_pem.encode('utf-8'), password=None)
    assert isinstance(key, rsa.RSAPrivateKey)

    signature = key.sign(
        signing_input, padding.PKCS1v15(), hashes.SHA256())

    return (signing_input + b'.' + _b64url(signature)).decode('ascii')


def build_app_jwt_from_data(
    github_app: GitHubAppRecordData,
) -> str:
    """Build an app JWT from an app-record data.

    This is a convenience wrapper that decrypts the private key and builds the
    JWT in one step.

    Version Added:
        9.0

    Args:
        github_app (reviewboard.hostingsvcs.github.accounts.
                    GitHubAppRecordData):
            The ``github_app`` data stored on the app-record account. This must
            contain the app credentials (``app_id`` and ``private_key``).

    Returns:
        str:
        The encoded, signed JWT.
    """
    return build_app_jwt(
        app_id=github_app.app_id,
        private_key_pem=load_app_private_key(github_app))
