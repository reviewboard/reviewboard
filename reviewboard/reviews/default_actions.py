"""Default actions for the reviews app.

These have moved to :py:mod:`reviewboard.reviews.actions`. The imports here
are for legacy compatibility, and will be removed in Review Board 7.0.
"""

from reviewboard.reviews.actions import (
    CloseMenuAction,
    CloseCompletedAction as SubmitAction,
    CloseDiscardedAction as DiscardAction,
    DeleteAction,
    DownloadDiffAction,
    LegacyAddGeneralCommentAction as AddGeneralCommentAction,
    LegacyEditReviewAction as EditReviewAction,
    LegacyShipItAction as ShipItAction,
    UpdateMenuAction,
    UploadDiffAction,
    UploadFileAction)


__all__ = [
    'AddGeneralCommentAction',
    'CloseMenuAction',
    'DeleteAction',
    'DiscardAction',
    'DownloadDiffAction',
    'EditReviewAction',
    'ShipItAction',
    'SubmitAction',
    'UpdateMenuAction',
    'UploadDiffAction',
    'UploadFileAction',
]


__autodoc_excludes__ = __all__
