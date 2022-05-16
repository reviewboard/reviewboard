import unittest

from djblets.util.decorators import simple_decorator

from reviewboard.testing.testcase import TestCase


__all__ = ['TestCase']


_online = None


def is_online():
    """Check if the host currently has access to the internet.

    This is used to skip tests that might fail if we can't do things like
    resolve hostnames or connect to third-party services. We should probably
    fix things up to run fake services locally, if possible.
    """
    global _online

    if _online is None:
        import socket
        try:
            socket.gethostbyname('google.com')
            _online = True
        except Exception:
            _online = False

    return _online


@simple_decorator
def online_only(test_func):
    """Decorate a test to check online state."""
    if not is_online():
        return unittest.skip('Host is not online')
    else:
        return lambda func: func
