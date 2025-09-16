"""Password hasher to use when running tests.

Version Added:
    8.0
"""

from __future__ import annotations

from base64 import b64encode
from typing import TYPE_CHECKING

from django.conf import settings
from django.contrib.auth.hashers import BasePasswordHasher

if TYPE_CHECKING:
    from typing import Any


class TestPasswordHasher(BasePasswordHasher):
    """Password hasher to use when running tests.

    THIS IS VERY INSECURE. This only exists to provide a password hasher for
    Django to use which does not affect the performance of unit tests.
    Do not use this for production!

    Version Added:
        8.0
    """

    algorithm = 'base64'

    def salt(self) -> str:
        """Return the salt to use.

        Returns:
            str:
            The salt to use.
        """
        return ''

    def encode(
        self,
        password: str,
        salt: str,
    ) -> str:
        """Encode a password.

        Args:
            password (str):
                The password to hash.

            salt (str, unused):
                The salt to use.

        Returns:
            str:
            The value to store in the database.

        Raises:
            RuntimeError:
                The hasher was used outside of unit tests.
        """
        if not settings.RUNNING_TEST:
            raise RuntimeError(
                'TestPasswordHasher cannot be used outside of unit tests.')

        encoded = b64encode(password.encode()).decode()

        return f'{self.algorithm}${encoded}'

    def decode(
        self,
        encoded: str,
    ) -> dict[str, Any]:
        """Return a decoded database value.

        Args:
            encoded (str):
                The encoded value from the database.

        Returns:
            dict:
            A dictionary with `algorithm`, `hash`, and `salt` keys.
        """
        return {
            'algorithm': self.algorithm,
            'hash': encoded,
            'salt': None,
        }

    def verify(
        self,
        password: str,
        encoded: str,
    ) -> bool:
        """Check if a given password is correct.

        Args:
            password (str):
                The password to check.

            encoded (str):
                The stored value from the database.

        Returns:
            bool:
            Whether the password is correct.
        """
        return self.encode(password, '') == encoded

    def safe_summary(
        self,
        encoded: str,
    ) -> dict[str, Any]:
        """Return a summary of safe values.

        Args:
            encoded (str):
                The encoded value from the database.

        Returns:
            dict:
            The summary, used internally by Django.
        """
        return {
            'algorithm': self.algorithm,
        }

    def harden_runtime(
        self,
        password: str,
        encoded: str,
    ) -> None:
        """Harden the runtime of the hasher.

        This method exists in order to thwart timing attacks. For the test
        hasher it's a no-op.

        Args:
            password (str):
                The password to check.

            encoded (str):
                The encoded value from the database.
        """
        pass
