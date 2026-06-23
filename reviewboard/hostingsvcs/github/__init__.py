"""Hosting service for GitHub."""

from __future__ import annotations

from reviewboard.hostingsvcs.github.forms import GitHubAuthForm
from reviewboard.hostingsvcs.github.service import GitHub


__all__ = [
    'GitHub',
    'GitHubAuthForm',
]

__autodoc_excludes__ = __all__
