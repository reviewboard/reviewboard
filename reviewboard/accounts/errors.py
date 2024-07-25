"""Errors for the accounts app."""

from __future__ import annotations


class UserQueryError(Exception):
    """An error for when a user query fails during user population.

    This error is used by authentication backends implementing the
    :py:meth:`~reviewboard.accounts.backends.base.BaseAuthBackend
    .populate_users` method to report when an error has occurred that should be
    reported back to the caller.
    """

    def __init__(
        self,
        msg: str,
    ) -> None:
        """Initialize the error.

        Args:
            msg (str):
                The error message to display.
        """
        super().__init__(
            f'Error while populating users from the auth backend: {msg}')
