class UserVisibleError(Exception):
    """A user-visible error shown in the rendered output."""
    pass


class DiffCompatError(Exception):
    """Unknown diff compatibility version error."""
    pass
