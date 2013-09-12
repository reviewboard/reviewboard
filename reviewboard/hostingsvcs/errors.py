class AuthorizationError(Exception):
    pass


class InvalidPlanError(KeyError):
    """Indicates an invalid plan name was used."""
    def __init__(self, plan):
        KeyError.__init__(
            self,
            '%s is not a valid plan for this hosting service' % plan)


class SSHKeyAssociationError(Exception):
    pass
