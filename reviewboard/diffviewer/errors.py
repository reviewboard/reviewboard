class UserVisibleError(Exception):
    """A user-visible error shown in the rendered output."""
    pass


class DiffCompatError(Exception):
    """Unknown diff compatibility version error."""
    pass


class DiffTooBigError(ValueError):
    def __init__(self, msg, max_diff_size):
        ValueError.__init__(self, msg)
        self.max_diff_size = max_diff_size


class EmptyDiffError(ValueError):
    pass
