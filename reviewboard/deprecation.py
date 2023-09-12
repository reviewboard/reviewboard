"""Internal support for handling deprecations in Review Board.

The version-specific objects in this module are not considered stable between
releases, and may be removed at any point. The base objects are considered
stable.
"""

import warnings

from housekeeping import BaseRemovedInWarning


class BaseRemovedInReviewBoardVersionWarning(BaseRemovedInWarning):
    """Base class for a Review Board deprecation warning.

    All version-specific deprecation warnings inherit from this, allowing
    callers to check for Review Board deprecations without being tied to a
    specific version.
    """

    product = 'Review Board'


class RemovedInReviewBoard70Warning(BaseRemovedInReviewBoardVersionWarning):
    """Deprecations for features scheduled for removal in Review Board 7.0.

    Note that this class will itself be removed in Review Board 7.0. If you
    need to check against Review Board deprecation warnings, please see
    :py:class:`BaseRemovedInReviewBoardVersionWarning`. Alternatively, you
    can use the alias for this class,
    :py:data:`RemovedInNextReviewBoardVersionWarning`.
    """

    version = '7.0'


class RemovedInReviewBoard80Warning(BaseRemovedInReviewBoardVersionWarning):
    """Deprecations for features scheduled for removal in Review Board 8.0.

    Note that this class will itself be removed in Review Board 8.0. If you
    need to check against Review Board deprecation warnings, please see
    :py:class:`BaseRemovedInReviewBoardVersionWarning`.
    """

    version = '8.0'


#: An alias for the next release of Review Board where features will be
#: removed.
RemovedInNextReviewBoardVersionWarning = RemovedInReviewBoard70Warning
