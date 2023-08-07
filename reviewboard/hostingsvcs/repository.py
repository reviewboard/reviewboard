"""Representations of remote repositories.

This is pending deprecation. Consumers should update their imports to use
the classes in :py:mod:`reviewboard.hostingsvcs.base.repository`.
"""

from reviewboard.hostingsvcs.base.repository import RemoteRepository


__all__ = [
    'RemoteRepository',
]


__autodoc_excludes__ = __all__
