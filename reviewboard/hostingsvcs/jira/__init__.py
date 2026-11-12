"""Hosting service for JIRA.

Version Added:
    9.0:
    Split up ``reviewboard.hostingsvcs.jira``.
"""

from __future__ import annotations

from reviewboard.hostingsvcs.jira.forms import JIRAAuthForm
from reviewboard.hostingsvcs.jira.service import JIRA


__all__ = [
    'JIRA',
    'JIRAAuthForm',
]

__autodoc_excludes__ = __all__
