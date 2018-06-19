from __future__ import unicode_literals


class UserQueryError(Exception):
    """An error for when a user query fails during user population.

    This error is used by authentication backends implementing the
    :py:meth:`~reviewboard.accounts.backends.base.BaseAuthBackend
    .populate_users` method to report when an error has occurred that should be
    reported back to the caller.
    """

    def __init__(self, msg):
        """Initialize the error.

        Args:
            msg (unicode):
                The error message to display.
        """
        super(Exception, self).__init__(
            'Error while populating users from the auth backend: %s'
            % msg)
