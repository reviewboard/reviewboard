from __future__ import unicode_literals

import nose
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
        except:
            _online = False

    return _online


@simple_decorator
def online_only(test_func):
    """Decorate a test to check online state."""
    def _test(*args, **kwargs):
        if not is_online():
            raise nose.SkipTest('Host is not online')
        return test_func(*args, **kwargs)

    return _test
