"""Unit test infrastructure for Review Board."""

from __future__ import annotations

import importlib
import unittest
from typing import Any, Optional, TYPE_CHECKING

from djblets.util.decorators import simple_decorator

if TYPE_CHECKING:
    from reviewboard.testing.testcase import TestCase


__all__ = [
    'TestCase',
]


_TestCase: Optional[TestCase] = None
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


def __getattr__(
    name: str,
) -> Any:
    """Return an attribute for the module.

    This will handle lazily-importing
    :py:class:`reviewboard.testing.testcase.TestCase`. The lazy import is
    necessary to avoid triggering database lookups when this module is
    imported.

    This isn't invoked for attributes defined normally in this module.

    Args:
        name (str):
            The attribute to import.

    Returns:
        object:
        The resulting attribute value.

    Raises:
        AttributeError:
            The attribute was not found.
    """
    global _TestCase

    if name == 'TestCase':
        if _TestCase is None:
            _TestCase = (
                importlib.import_module('reviewboard.testing.testcase')
                .TestCase
            )

        return _TestCase

    raise AttributeError('"module {__name__!r} has no attribute {name!r}')
