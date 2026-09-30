"""A hook for adding capabilities to the API server info payload.

Deprecated:
    9.0:
    This will be removed in Review Board 11.
"""

from __future__ import annotations

from housekeeping import module_moved

from reviewboard.deprecation import RemovedInReviewBoard11_0Warning
from reviewboard.extensions.hooks.webapi import WebAPICapabilitiesHook


module_moved(
    warning_cls=RemovedInReviewBoard11_0Warning,
    old_module_name=__name__,
    new_module_name='reviewboard.extensions.hooks',
)


__all__ = [
    'WebAPICapabilitiesHook',
]
