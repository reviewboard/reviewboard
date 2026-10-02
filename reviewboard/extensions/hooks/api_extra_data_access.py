"""A hook for setting access states on extra data fields.

Deprecated:
    9.0:
    This will be removed in Review Board 11.
"""

from __future__ import annotations

from housekeeping import module_moved

from reviewboard.deprecation import RemovedInReviewBoard11_0Warning
from reviewboard.extensions.hooks.webapi import APIExtraDataAccessHook


module_moved(
    warning_cls=RemovedInReviewBoard11_0Warning,
    old_module_name=__name__,
    new_module_name='reviewboard.extensions.hooks',
)


__all__ = [
    'APIExtraDataAccessHook',
]
