from __future__ import unicode_literals


class HostingServiceError(Exception):
    """Base class for errors related to a hosting service."""
    def __init__(self, message, http_code=None, help_link=None,
                 help_link_text=None):
        super(HostingServiceError, self).__init__(message)

        self.http_code = http_code
        self.help_link = help_link
        self.help_link_text = help_link_text

        if help_link and not help_link_text:
            raise ValueError('help_link_text cannot be empty')


class HostingServiceAPIError(HostingServiceError):
    """An API error from a hosting service.

    This represents an error from the hosting service's API. It contains
    the error message, HTTP code, and the parsed response payload.

    HostingServiceAPIError instances can be further turned into other error
    types, or raised directly, if the error message is suitable for display.

    Attributes:
        http_code (int):
            The HTTP code for the error.

        rsp (object):
            The parsed payload for the error, if available.
    """

    def __init__(self, msg=None, http_code=None, rsp=None):
        """Initialize the error.

        Args:
            msg (unicode, optional):
                The error message from the service.

            http_code (int, optional):
                The HTTP code for the error.

            rsp (object, optional):
                The parsed payload for the error.
        """
        super(HostingServiceAPIError, self).__init__(msg)

        self.http_code = http_code
        self.rsp = rsp


class RepositoryError(HostingServiceError):
    """An error validating, configuring or using a repository."""
    pass


class AuthorizationError(HostingServiceError):
    pass


class TwoFactorAuthCodeRequiredError(AuthorizationError):
    """Response from a service indicating a two-factor auth code is required.

    Some services will indicate, after an authorization attempt, that a
    two-factor authorization code must be provided to complete authorization.
    Services can raise this error, along with a helpful message, to
    inform the user and the repository form of this.
    """
    pass


class InvalidPlanError(HostingServiceError):
    """Indicates an invalid plan name was used."""
    def __init__(self, plan):
        HostingServiceError.__init__(
            self,
            '%s is not a valid plan for this hosting service' % plan)


class SSHKeyAssociationError(HostingServiceError):
    pass
