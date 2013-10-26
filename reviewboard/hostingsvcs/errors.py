class HostingServiceError(Exception):
    """Base class for errors related to a hosting service."""
    pass


class RepositoryError(HostingServiceError):
    """An error validating, configuring or using a repository."""
    pass


class AuthorizationError(HostingServiceError):
    pass


class InvalidPlanError(HostingServiceError):
    """Indicates an invalid plan name was used."""
    def __init__(self, plan):
        KeyError.__init__(
            self,
            '%s is not a valid plan for this hosting service' % plan)


class SSHKeyAssociationError(HostingServiceError):
    pass
