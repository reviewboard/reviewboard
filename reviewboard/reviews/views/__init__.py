"""Main application views for Review Board."""

from reviewboard.reviews.views.attachments import (ReviewFileAttachmentView,
                                                   ReviewScreenshotView)
from reviewboard.reviews.views.batch import BatchOperationView
from reviewboard.reviews.views.bug_trackers import (BugInfoboxView,
                                                    BugURLRedirectView)
from reviewboard.reviews.views.diff_fragments import (
    CommentDiffFragmentsView,
    ReviewsDiffFragmentView,
    build_diff_comment_fragments)
from reviewboard.reviews.views.diffviewer import ReviewsDiffViewerView
from reviewboard.reviews.views.email import (PreviewBatchEmailView,
                                             PreviewReplyEmailView,
                                             PreviewReviewEmailView,
                                             PreviewReviewRequestEmailView)
from reviewboard.reviews.views.download_diff import (
    DownloadDiffFileView,
    DownloadRawDiffView,
    ReviewsDownloadPatchErrorBundleView)
from reviewboard.reviews.views.mixins import ReviewRequestViewMixin
from reviewboard.reviews.views.new_review_request import NewReviewRequestView
from reviewboard.reviews.views.review_request_detail import \
    ReviewRequestDetailView
from reviewboard.reviews.views.review_request_infobox import \
    ReviewRequestInfoboxView
from reviewboard.reviews.views.review_request_updates import \
    ReviewRequestUpdatesView
from reviewboard.reviews.views.root import RootView


__all__ = [
    'BatchOperationView',
    'BugInfoboxView',
    'BugURLRedirectView',
    'CommentDiffFragmentsView',
    'DownloadDiffFileView',
    'DownloadRawDiffView',
    'NewReviewRequestView',
    'PreviewBatchEmailView',
    'PreviewReplyEmailView',
    'PreviewReviewEmailView',
    'PreviewReviewRequestEmailView',
    'ReviewFileAttachmentView',
    'ReviewRequestDetailView',
    'ReviewRequestInfoboxView',
    'ReviewRequestUpdatesView',
    'ReviewRequestViewMixin',
    'ReviewScreenshotView',
    'ReviewsDiffFragmentView',
    'ReviewsDiffViewerView',
    'ReviewsDownloadPatchErrorBundleView',
    'RootView',
    'build_diff_comment_fragments',
]

__autodoc_excludes__ = __all__
