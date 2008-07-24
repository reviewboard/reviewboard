class InvalidChangeNumberError(Exception):
    def __init__(self):
        Exception.__init__(self, None)


class ChangeNumberInUseError(Exception):
    def __init__(self, review_request=None):
        Exception.__init__(self, None)
        self.review_request = review_request


class ChangeSetError(ValueError):
    pass


class OwnershipError(ValueError):
    pass


class PermissionError(Exception):
    def __init__(self):
        Exception.__init__(self, None)
