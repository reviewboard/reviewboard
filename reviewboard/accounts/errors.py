class UserQueryError(Exception):
    def __init__(self, msg):
        Exception.__init__(self, None)
        self.msg = msg

    def __str__(self):
        return 'User query error: %s' % self.msg
