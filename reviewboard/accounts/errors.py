class UserQueryError(Exception):
    """An error for when a user query fails.

    This error is used by authentication backends implementing the query_users
    method to report when an error has occurred that should be reported back to
    the webapi.
    """

    def __init__(self, msg):
        """Initialize the error."""
        Exception.__init__(self, None)
        self.msg = msg

    def __str__(self):
        """Return a string representation of the error."""
        return 'User query error: %s' % self.msg
