"""Exception classes for accounts."""

from __future__ import annotations

from django.utils.translation import gettext as _


class LoginNotAllowedError(Exception):
    """An error when a user login is not allowed.

    This error is used when a user cannot log in, for example, if the user is
    marked inactive.

    Version Added:
        6.0.3
    """

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
            _('Error while populating users from the auth backend: {}')
            .format(msg))
