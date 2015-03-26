from __future__ import unicode_literals


class OwnershipError(ValueError):
    pass


class PermissionError(Exception):
    def __init__(self):
        Exception.__init__(self, None)


class PublishError(Exception):
    def __init__(self, msg):
        Exception.__init__(self, None)
        self.msg = msg

    def __str__(self):
        return 'Publish error: %s' % self.msg


class NotModifiedError(PublishError):
    """Error when a review's state is not modified."""

    def __init__(self):
        super(NotModifiedError, self).__init__(
            'The draft has no modifications.')
