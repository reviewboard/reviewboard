class EvolutionException(Exception):
    """Base class for a Django Evolution exception."""
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return str(self.msg)


class CannotSimulate(EvolutionException):
    """A mutation cannot be simulated."""


class SimulationFailure(EvolutionException):
    """A mutation simulation has failed."""


class EvolutionNotImplementedError(EvolutionException, NotImplementedError):
    """An operation is not supported by the mutation or database backend."""
