"""Internal support for handling deprecations in Review Board.

The version-specific objects in this module are not considered stable between
releases, and may be removed at any point. The base objects are considered
stable.
"""

from __future__ import unicode_literals

import warnings


class BaseRemovedInReviewBoardVersionWarning(DeprecationWarning):
    """Base class for a Review Board deprecation warning.

    All version-specific deprecation warnings inherit from this, allowing
    callers to check for Review Board deprecations without being tied to a
    specific version.
    """

    @classmethod
    def warn(cls, message, stacklevel=2):
        """Emit the deprecation warning.

        This is a convenience function that emits a deprecation warning using
        this class, with a suitable default stack level. Callers can provide
        a useful message and a custom stack level.

        Args:
            message (unicode):
                The message to show in the deprecation warning.

            stacklevel (int, optional):
                The stack level for the warning.
        """
        warnings.warn(message, cls, stacklevel=stacklevel + 1)


class RemovedInReviewBoard40Warning(BaseRemovedInReviewBoardVersionWarning):
    """Deprecations for features removed in Review Board 4.0.

    Note that this class will itself be removed in Review Board 4.0. If you
    need to check against Review Board deprecation warnings, please see
    :py:class:`BaseRemovedInReviewBoardVersionWarning`.
    """


class RemovedInReviewBoard50Warning(BaseRemovedInReviewBoardVersionWarning):
    """Deprecations for features removed in Review Board 5.0.

    Note that this class will itself be removed in Review Board 5.0. If you
    need to check against Review Board deprecation warnings, please see
    :py:class:`BaseRemovedInReviewBoardVersionWarning`. Alternatively, you
    can use the alias for this class,
    :py:data:`RemovedInNextReviewBoardVersionWarning`.
    """


#: An alias for the next release of Djblets where features would be removed.
RemovedInNextReviewBoardVersionWarning = RemovedInReviewBoard50Warning
