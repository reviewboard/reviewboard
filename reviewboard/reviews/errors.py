"""Error definitions for the reviews app."""

from reviewboard.actions.errors import DepthLimitExceededError


class OwnershipError(ValueError):
    """An error that occurs when a user does not own a review request."""
    pass


class PermissionError(Exception):
    """An error that occurs when a user does not have required permissions."""
    pass


class PublishError(Exception):
    """An error that occurs when attempting to publish.

    The model triggering this error may be a review request, review, or reply.
    """

    def __init__(self, message):
        super(PublishError, self).__init__('Error publishing: %s' % message)


class CloseError(Exception):
    """An error that occurs while attempting to close a review request."""

    def __init__(self, message):
        super(CloseError, self).__init__(
            'Error closing the review request: %s' % message)


class ReopenError(Exception):
    """An error that occurs while attempting to reopen a review request."""

    def __init__(self, message):
        super(ReopenError, self).__init__(
            'Error reopening the review request: %s' % message)


class RevokeShipItError(Exception):
    """An error that occurs while attempting to revoke a Ship It."""

    def __init__(self, message):
        super(RevokeShipItError, self).__init__(
            'Error revoking the Ship It: %s' % message)


class NotModifiedError(PublishError):
    """An error that occurs when a review's state is not modified."""

    def __init__(self):
        super(NotModifiedError, self).__init__(
            'The draft has no modifications.')


__all__ = (
    'CloseError',
    'NotModifiedError',
    'OwnershipError',
    'PermissionError',
    'PublishError',
    'ReopenError',
    'RevokeShipItError',

    # This is left as a forwarding import. When
    # reviewboard.reviews.actions.BaseReviewRequestAction is removed in Review
    # Board 7.0, this can go away.
    'DepthLimitExceededError',
)

__autodoc_excludes__ = (
    'DepthLimitExceededError',
)
