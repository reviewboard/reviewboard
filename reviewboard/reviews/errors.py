from __future__ import unicode_literals


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


class DepthLimitExceededError(ValueError):
    """An error that occurs when the maximum depth limit is exceeded.

    Review request actions cannot be arbitrarily nested. For example, if the
    depth limit is 2, then this error would be triggered if an extension tried
    to add a menu action as follows:

    .. code-block:: python

       BaseReviewRequestActionHook(self, actions=[
           DepthZeroMenuAction([
               DepthOneFirstItemAction(),
               DepthOneMenuAction([
                   DepthTwoMenuAction([  # This depth is acceptable.
                       DepthThreeTooDeepAction(),  # This action is too deep.
                   ]),
               ]),
               DepthOneLastItemAction(),
           ]),
       ])
    """

    def __init__(self, action_id, depth_limit):
        super(DepthLimitExceededError, self).__init__(
            '%s exceeds the maximum depth limit of %d'
            % (action_id, depth_limit))
