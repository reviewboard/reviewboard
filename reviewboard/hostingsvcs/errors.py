from __future__ import unicode_literals


class HostingServiceError(Exception):
    """Base class for errors related to a hosting service."""
    pass


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
        KeyError.__init__(
            self,
            '%s is not a valid plan for this hosting service' % plan)


class SSHKeyAssociationError(HostingServiceError):
    pass
