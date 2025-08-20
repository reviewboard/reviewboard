"""Error definitions for Forgejo.

Version Added:
    7.1
"""

from __future__ import annotations


class APITokenNameInUseError(Exception):
    """Error for when an API token name is already in use.

    Version Added:
        7.1
    """
