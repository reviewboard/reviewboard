"""The base hosting service class and associated definitions.

This is pending deprecation. Consumers should update their imports to use
the classes in :py:mod:`reviewboard.hostingsvcs.base.forms`.
"""

from __future__ import annotations

from typing_extensions import deprecated

from reviewboard.deprecation import RemovedInReviewBoard90Warning
from reviewboard.hostingsvcs.base import forms


# This can't use housekeeping.ClassMovedMixin because that interferes with the
# form metaclass.
@deprecated(
    '`reviewboard.hostingsvcs.forms.HostingServiceAuthForm` has moved '
    'to `reviewboard.hostingsvcs.base.forms.BaseHostingServiceAuthForm`. '
    'The old class name is deprecated and will be removed in Review Board '
    '9.0',
    category=RemovedInReviewBoard90Warning)
class HostingServiceAuthForm(forms.BaseHostingServiceAuthForm):
    """Base form for handling authentication information for a hosting account.

    Deprecated:
        7.1:
        This has been moved to :py:class:`reviewboard.hostingsvcs.base.forms.
        BaseHostingServiceAuthForm`. The legacy import will be removed in
        Review Board 9.
    """


# This can't use housekeeping.ClassMovedMixin because that interferes with the
# form metaclass.
@deprecated(
    '`reviewboard.hostingsvcs.forms.HostingServiceForm` has moved '
    'to `reviewboard.hostingsvcs.base.forms.'
    'BaseHostingServiceRepositoryForm`. The old class name is deprecated and '
    'will be removed in Review Board '
    '9.0',
    category=RemovedInReviewBoard90Warning)
class HostingServiceForm(forms.BaseHostingServiceRepositoryForm):
    """Base form for collecting information for a hosting service repository.

    Deprecated:
        7.1:
        This has been moved to :py:class:`reviewboard.hostingsvcs.base.forms.
        BaseHostingServiceRepositoryForm`. The legacy import will be removed in
        Review Board 9.
    """


__all__ = [
    'HostingServiceAuthForm',
    'HostingServiceForm',
]
