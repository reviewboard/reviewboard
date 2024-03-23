"""Diff viewer view."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional, TYPE_CHECKING, cast

from django.http import HttpRequest, HttpResponse
from django.utils.translation import gettext
from typing_extensions import NotRequired, TypedDict

from reviewboard.accounts.mixins import UserProfileRequiredViewMixin
from reviewboard.attachments.models import get_latest_file_attachments
from reviewboard.diffviewer.models import DiffSet
from reviewboard.diffviewer.views import (DiffViewerContext,
                                          DiffViewerView,
                                          SerializedDiffContext)
from reviewboard.reviews.context import (ReviewRequestContext,
                                         diffsets_with_comments,
                                         has_comments_in_diffsets_excluding,
                                         interdiffs_with_comments,
                                         make_review_request_context)
from reviewboard.reviews.ui.diff import DiffReviewUI
from reviewboard.reviews.views.mixins import ReviewRequestViewMixin
from reviewboard.reviews.models import (Review,
                                        ReviewRequest,
                                        ReviewRequestDraft)

if TYPE_CHECKING:
    from reviewboard.attachments.models import FileAttachment
    from reviewboard.reviews.models import Comment, Screenshot
    from reviewboard.reviews.ui.base import SerializedCommentBlocks


class ReviewsDiffViewerContext(DiffViewerContext, ReviewRequestContext):
    """Render context for the diff viewer view.

    Version Added:
        7.0
    """

    #: The current description if the review request has been closed.
    close_description: str

    #: Whether the ``close_description`` is in rich text.
    close_description_rich_text: bool

    #: The timestamp of when the review request was closed.
    close_timestamp: Optional[datetime]

    #: All of the DiffSets connected to the review request.
    diffsets: list[DiffSet]

    #: The current review, if present.
    review: Optional[Review]

    #: The current review request details.
    review_request_details: ReviewRequest | ReviewRequestDraft

    #: The rendered HTML for the review request status.
    review_request_status_html: str

    #: The draft of the review request, if present.
    draft: Optional[ReviewRequestDraft]

    #: The timestamp of the last activity.
    last_activity_time: datetime

    #: The current set of file attachments for the review request.
    file_attachments: list[FileAttachment]

    #: All of the file attachments for the review request.
    #:
    #: This includes all current attachments, as well as old versions and files
    #: that have been removed.
    all_file_attachments: list[FileAttachment]

    #: The screenshots attached to the review request.
    #:
    #: This is a legacy item which has been replaced by the file attachments.
    screenshots: list[Screenshot]

    #: All of the diff comments for the review request.
    comments: dict[tuple[int, Optional[int], Optional[int]], list[Comment]]

    #: The image URL to use for social media links.
    social_page_image_url: Optional[str]

    #: The title text to use for social media links.
    social_page_title: str


class SerializedReviewsDiffContext(SerializedDiffContext):
    """Serialized diff context information.

    Version Added:
        7.0
    """

    #: The number of diff revisions.
    num_diffs: int

    # TODO TYPING: update with new hint structure.
    #: The hint to show for draft reviews with comments in other revisions.
    comments_hint: dict[str, Any]

    #: The list of files in the current diff view.
    files: list[SerializedReviewsDiffFile]


class SerializedDiffFileFileDiff(TypedDict):
    """Serialized information about a FileDiff inside the diff files.

    Version Added:
        7.0
    """

    #: The ID of the FileDiff.
    id: int

    #: The revision of the FileDiff.
    revision: int


class SerializedReviewsDiffFile(TypedDict):
    """Serialized information about a file in the diff.

    Version Added:
        7.0
    """

    #: The ID of the base FileDiff when viewing a commit range.
    base_filediff_id: Optional[int]

    #: Whether the file is binary.
    binary: bool

    #: Whether the file was deleted in the change.
    deleted: bool

    #: The ID of the FileDiff.
    id: int

    #: The index of the file in the list of all files.
    index: int

    #: The revision of the interdiff FileDiff, when present.
    interdiff_revision: NotRequired[int]

    #: Information about the interdiff FileDiff, when present.
    interfilediff: NotRequired[SerializedDiffFileFileDiff]

    #: Information about the FileDiff.
    filediff: SerializedDiffFileFileDiff

    #: Whether to force rendering an interdiff.
    #:
    #: This is used to ensure that reverted files render correctly.
    force_interdiff: NotRequired[bool]

    #: The filename of the modified version of the file.
    modified_filename: str

    #: The revision of the modified version of the file.
    modified_revision: str

    #: Whether the file is newly-added in the diff.
    newfile: bool

    #: The filename of the original version of the file.
    orig_filename: str

    #: The revision of the original version of the file.
    orig_revision: str

    #: Whether the file is part of a published diff.
    public: bool

    #: The serialized comments already attached to the file's diff.
    serialized_comment_blocks: SerializedCommentBlocks


class ReviewsDiffViewerView(ReviewRequestViewMixin,
                            UserProfileRequiredViewMixin,
                            DiffViewerView):
    """Renders the diff viewer for a review request.

    This wraps the base
    :py:class:`~reviewboard.diffviewer.views.DiffViewerView` to display a diff
    for the given review request and the given diff revision or range.

    The view expects the following parameters to be provided:

    ``review_request_id``:
        The ID of the ReviewRequest containing the diff to render.

    The following may also be provided:

    ``revision``:
        The DiffSet revision to render.

    ``interdiff_revision``:
        The second DiffSet revision in an interdiff revision range.

    ``local_site``:
        The LocalSite the ReviewRequest must be on, if any.

    See :py:class:`~reviewboard.diffviewer.views.DiffViewerView`'s
    documentation for the accepted query parameters.
    """

    def __init__(
        self,
        **kwargs,
    ) -> None:
        """Initialize a view for the request.

        Args:
            **kwargs (dict):
                Keyword arguments passed to :py:meth:`as_view`.
        """
        super().__init__(**kwargs)

        self.draft = None
        self.interdiffset = None

    def get(
        self,
        request: HttpRequest,
        revision: Optional[int] = None,
        interdiff_revision: Optional[int] = None,
        *args,
        **kwargs,
    ) -> HttpResponse:
        """Handle HTTP GET requests for this view.

        This will look up the review request and DiffSets, given the
        provided information, and pass them to the parent class for rendering.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            revision (int, optional):
                The revision of the diff to view. This defaults to the latest
                diff.

            interdiff_revision (int, optional):
                The revision to use for an interdiff, if viewing an interdiff.

            *args (tuple):
                Positional arguments passed to the handler.

            **kwargs (dict):
                Keyword arguments passed to the handler.

        Returns:
            django.http.HttpResponse:
            The HTTP response to send to the client.
        """
        review_request = self.review_request

        self.draft = review_request.get_draft(review_request.submitter)

        if self.draft and not self.draft.is_accessible_by(request.user):
            self.draft = None

        self.diffset = self.get_diff(revision, self.draft)

        if interdiff_revision and interdiff_revision != revision:
            # An interdiff revision was specified. Try to find a matching
            # diffset.
            self.interdiffset = self.get_diff(interdiff_revision, self.draft)

        return super().get(
            request=request,
            diffset=self.diffset,
            interdiffset=self.interdiffset,
            *args,
            **kwargs)

    def get_context_data(
        self,
        diffset: DiffSet,
        interdiffset: Optional[DiffSet],
        **kwargs,
    ) -> dict[str, Any]:
        """Return additional context data for the template.

        This provides some additional data used for rendering the diff
        viewer. This data is more specific to the reviewing functionality,
        as opposed to the data calculated by
        :py:meth:`DiffViewerView.get_context_data
        <reviewboard.diffviewer.views.DiffViewerView.get_context_data>`
        which is more focused on the actual diff.

        Args:
            diffset (reviewboard.diffviewer.models.DiffSet):
                The diffset being viewed.

            interdiffset (reviewboard.diffviewer.models.DiffSet):
                The interdiff diffset, if present.

            **kwargs (dict):
                Keyword arguments passed to the handler.

        Returns:
            dict:
            Context data used to render the template.
        """
        # Try to find an existing pending review of this diff from the
        # current user.
        pending_review = \
            self.review_request.get_pending_review(self.request.user)

        is_draft_diff = bool(self.draft and self.draft.diffset == self.diffset)
        is_draft_interdiff = bool(self.draft and
                                  self.interdiffset and
                                  self.draft.diffset == self.interdiffset)

        # Get the list of diffsets. We only want to calculate this once.
        diffsets = self.review_request.get_diffsets()
        num_diffs = len(diffsets)

        if num_diffs > 0:
            latest_diffset = diffsets[-1]
        else:
            latest_diffset = None

        if self.draft and self.draft.diffset:
            num_diffs += 1

        last_activity_time = self.review_request.get_last_activity_info(
            diffsets)['timestamp']

        review_request_details = self.draft or self.review_request

        file_attachments = list(review_request_details.get_file_attachments())
        screenshots = list(review_request_details.get_screenshots())

        latest_file_attachments = get_latest_file_attachments(file_attachments)
        social_page_image_url = self.get_social_page_image_url(
            latest_file_attachments)

        # Build the status information shown below the summary.
        close_info = self.review_request.get_close_info()

        if latest_diffset:
            status_extra_info = [{
                'text': gettext('Latest diff uploaded {timestamp}'),
                'timestamp': latest_diffset.timestamp,
            }]
        else:
            status_extra_info = []

        review_request_status_html = self.get_review_request_status_html(
            review_request_details=review_request_details,
            close_info=close_info,
            extra_info=status_extra_info)

        # Compute the lists of comments based on filediffs and interfilediffs.
        # We do this using the 'through' table so that we can select_related
        # the reviews and comments.
        comments: dict[tuple[int, Optional[int], Optional[int]],
                       list[Comment]] = {}
        q = (
            Review.comments.through.objects
            .filter(review__review_request=self.review_request)
            .select_related()
        )

        for obj in q:
            comment = obj.comment
            comment.review_obj = obj.review
            key = (comment.filediff_id, comment.interfilediff_id,
                   comment.base_filediff_id)
            comments.setdefault(key, []).append(comment)

        # Build the final context for the page.
        context = cast(
            ReviewsDiffViewerContext,
            super().get_context_data(
                diffset=diffset,
                interdiffset=interdiffset,
                **kwargs))
        context.update({
            'close_description': close_info['close_description'],
            'close_description_rich_text': close_info['is_rich_text'],
            'close_timestamp': close_info['timestamp'],
            'diffsets': diffsets,
            'review': pending_review,
            'review_request_details': review_request_details,
            'review_request_status_html': review_request_status_html,
            'draft': self.draft,
            'last_activity_time': last_activity_time,
            'file_attachments': latest_file_attachments,
            'all_file_attachments': file_attachments,
            'screenshots': screenshots,
            'comments': comments,
            'social_page_image_url': social_page_image_url,
            'social_page_title': (
                'Diff for Review Request #%s: %s'
                % (self.review_request.display_id,
                   review_request_details.summary)
            ),
        })
        context.update(make_review_request_context(
            request=self.request,
            review_request=self.review_request,
            is_diff_view=True))

        diffset_pair = (diffset, interdiffset)
        diff_context = cast(SerializedReviewsDiffContext,
                            context['diff_context'])

        diff_context.update({
            'num_diffs': num_diffs,
            'comments_hint': {
                'has_other_comments': has_comments_in_diffsets_excluding(
                    pending_review, diffset_pair),
                'diffsets_with_comments': [
                    {
                        'revision': diffset_info['diffset'].revision,
                        'is_current': diffset_info['is_current'],
                    }
                    for diffset_info in diffsets_with_comments(
                        pending_review, diffset_pair)
                ],
                'interdiffs_with_comments': [
                    {
                        'old_revision': pair['diffset'].revision,
                        'new_revision': pair['interdiff'].revision,
                        'is_current': pair['is_current'],
                    }
                    for pair in interdiffs_with_comments(
                        pending_review, diffset_pair)
                ],
            },
        })
        diff_context['revision'].update({
            'latest_revision': (latest_diffset.revision
                                if latest_diffset else None),
            'is_draft_diff': is_draft_diff,
            'is_draft_interdiff': is_draft_interdiff,
        })

        files: list[SerializedReviewsDiffFile] = []

        for f in context['files']:
            filediff = f['filediff']
            interfilediff = f['interfilediff']
            base_filediff = f['base_filediff']

            interfilediff_id: Optional[int] = None
            base_filediff_id: Optional[int] = None

            if base_filediff:
                base_filediff_id = base_filediff.pk

            if interfilediff:
                interfilediff_id = interfilediff.pk

            key = (filediff.pk, interfilediff_id, base_filediff_id)

            file_comments = comments.get(key, [])

            review_ui = DiffReviewUI(
                review_request=self.review_request,
                obj=filediff,
                base_filediff=base_filediff,
                interfilediff=interfilediff,
                request=self.request)

            data: SerializedReviewsDiffFile = {
                'base_filediff_id': base_filediff_id,
                'binary': f['binary'],
                'deleted': f['deleted'],
                'id': filediff.pk,
                'index': f['index'],
                'filediff': {
                    'id': filediff.pk,
                    'revision': filediff.diffset.revision,
                },
                'modified_filename': f['modified_filename'],
                'modified_revision': f['modified_revision'],
                'newfile': f['newfile'],
                'orig_filename': f['orig_filename'],
                'orig_revision': f['orig_revision'],
                'public': f['public'],
                'serialized_comment_blocks':
                    review_ui.serialize_comments(file_comments),
            }

            if interfilediff:
                data['interfilediff'] = {
                    'id': interfilediff.pk,
                    'revision': interfilediff.diffset.revision,
                }

            if f['force_interdiff']:
                data['force_interdiff'] = True
                data['interdiff_revision'] = f['force_interdiff_revision']

            files.append(data)

        diff_context['files'] = files

        return context
