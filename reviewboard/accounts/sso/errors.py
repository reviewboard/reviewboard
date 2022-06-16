"""Error definitions for SSO.

Version Added:
    5.0
"""


class InvalidUsernameError(ValueError):
    """Error for when a username is invalid.

    Version Added:
        5.0
    """


class BadSSOResponseError(ValueError):
    """Error for when we get a bad response from the SSO provider.

    Version Added:
        5.0
    """
