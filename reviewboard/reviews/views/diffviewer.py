"""Diff viewer view."""

from __future__ import annotations

import itertools
import logging
from datetime import datetime
from typing import Optional, TYPE_CHECKING, cast

from django.http import HttpRequest, HttpResponse
from django.utils.translation import gettext
from typing_extensions import NotRequired, TypeAlias, TypedDict

from reviewboard.accounts.mixins import UserProfileRequiredViewMixin
from reviewboard.attachments.models import get_latest_file_attachments
from reviewboard.diffviewer.commit_utils import get_base_and_tip_commits
from reviewboard.diffviewer.models import DiffCommit, DiffSet, FileDiff
from reviewboard.diffviewer.views import (DiffViewerContext,
                                          DiffViewerView,
                                          SerializedDiffContext)
from reviewboard.reviews.context import (ReviewRequestContext,
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

    CommentsDict: TypeAlias = dict[tuple[int, Optional[int], Optional[int]],
                                   list[Comment]]


logger = logging.getLogger(__name__)


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
    comments: CommentsDict


class SerializedDiffsetWithComments(TypedDict):
    """Serialized information about a diff with comments.

    Version Added:
        7.0
    """

    #: Whether this diff is currently being viewed.
    is_current: bool

    #: The revision of the DiffSet.
    revision: int


class SerializedInterdiffsetWithComments(TypedDict):
    """Serialized information about an interdiff with comments.

    Version Added:
        7.0
    """

    #: Whether this interdiff is currently being viewed.
    is_current: bool

    #: The new diff revision in the interdiff pair.
    new_revision: int

    #: The old diff revision in the interdiff pair.
    old_revision: int


class SerializedCommitWithComments(TypedDict):
    """Serialized information about a commit with comments.

    Version Added:
        7.0
    """

    #: The commit ID of the base commit in the commit range.
    base_commit_id: Optional[str]

    #: The PK of the base DiffCommit in the commit range.
    base_commit_pk: Optional[int]

    #: Whether this commit range is currently being viewed.
    is_current: bool

    #: The revision of the diff that contains this commit range.
    revision: int

    #: The commit ID of the tip commit in the commit range.
    tip_commit_id: str

    #: The PK of the tip DiffCommit in the commit range.
    tip_commit_pk: int


class SerializedCommentsHint(TypedDict):
    """Serialized information about comments in other revisions.

    Version Added:
        7.0
    """

    #: The set of commit ranges that have draft comments.
    commits_with_comments: list[SerializedCommitWithComments]

    #: The set of diffs that have draft comments.
    diffsets_with_comments: list[SerializedDiffsetWithComments]

    #: Whether there are draft comments in other revisions.
    has_other_comments: bool

    #: The set of interdiffs that have draft comments.
    interdiffs_with_comments: list[SerializedInterdiffsetWithComments]


class SerializedReviewsDiffContext(SerializedDiffContext):
    """Serialized diff context information.

    Version Added:
        7.0
    """

    #: The hint to show for draft reviews with comments in other revisions.
    comments_hint: SerializedCommentsHint

    #: The list of files in the current diff view.
    files: list[SerializedReviewsDiffFile]

    #: The number of diff revisions.
    num_diffs: int


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
    ) -> ReviewsDiffViewerContext:
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
        review_request = self.review_request
        draft = self.draft
        draft_diffset = draft and draft.diffset

        # Try to find an existing pending review of this diff from the
        # current user.
        pending_review = review_request.get_pending_review(self.request.user)

        is_draft_diff = draft_diffset == self.diffset
        is_draft_interdiff = bool(self.interdiffset and
                                  draft_diffset == self.interdiffset)

        # Get the list of diffsets. We only want to calculate this once.
        diffsets = review_request.get_diffsets()
        num_diffs = len(diffsets)

        if num_diffs > 0:
            latest_diffset = diffsets[-1]
        else:
            latest_diffset = None

        if draft_diffset:
            num_diffs += 1

        # We'll need this for later lookups. The diffsets returned by
        # get_diffsets() already have the filediffs pre-fetched.
        filediffs_by_id: dict[int, FileDiff] = {}

        for ds in diffsets:
            for filediff in ds.files.all():
                filediffs_by_id[filediff.pk] = filediff

        last_activity_time = review_request.get_last_activity_info(
            diffsets)['timestamp']

        review_request_details = draft or review_request

        file_attachments = list(review_request_details.get_file_attachments())
        screenshots = list(review_request_details.get_screenshots())

        latest_file_attachments = get_latest_file_attachments(file_attachments)
        social_page_image_url = self.get_social_page_image_url(
            latest_file_attachments)

        # Build the status information shown below the summary.
        close_info = review_request.get_close_info()

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
        comments: CommentsDict = {}
        q = (
            Review.comments.through.objects
            .filter(review__review_request=review_request)
            .select_related()
        )

        for obj in q:
            comment = obj.comment
            comment.review_obj = obj.review
            key = (comment.filediff_id, comment.interfilediff_id,
                   comment.base_filediff_id)
            comments.setdefault(key, []).append(comment)

        base_commit_id: Optional[int] = None
        base_commit: Optional[DiffCommit] = None
        tip_commit_id: Optional[int] = None
        tip_commit: Optional[DiffCommit] = None

        if diffset.commit_count and not interdiffset:
            # Base and tip commit selection is not supported in interdiffs.
            raw_base_commit_id = self.request.GET.get('base-commit-id')
            raw_tip_commit_id = self.request.GET.get('tip-commit-id')

            if raw_base_commit_id is not None:
                try:
                    base_commit_id = int(raw_base_commit_id)
                except ValueError:
                    pass

            if raw_tip_commit_id is not None:
                try:
                    tip_commit_id = int(raw_tip_commit_id)
                except ValueError:
                    pass

        all_commits: list[DiffCommit] = list(DiffCommit.objects.filter(
            diffset__history__pk=review_request.diffset_history_id))

        if base_commit_id or tip_commit_id:
            base_commit, tip_commit = get_base_and_tip_commits(
                base_commit_id,
                tip_commit_id,
                commits=all_commits)

        # Build the final context for the page.
        context = cast(
            ReviewsDiffViewerContext,
            super().get_context_data(
                diffset=diffset,
                interdiffset=interdiffset,
                all_commits=all_commits,
                base_commit=base_commit,
                tip_commit=tip_commit,
                **kwargs))

        context.update({
            'close_description': close_info['close_description'],
            'close_description_rich_text': close_info['is_rich_text'],
            'close_timestamp': close_info['timestamp'],
            'diffsets': diffsets,
            'review': pending_review,
            'review_request_details': review_request_details,
            'review_request_status_html': review_request_status_html,
            'draft': draft,
            'last_activity_time': last_activity_time,
            'file_attachments': latest_file_attachments,
            'all_file_attachments': file_attachments,
            'screenshots': screenshots,
            'comments': comments,
        })

        context.update(make_review_request_context(
            request=self.request,
            review_request=review_request,
            is_diff_view=True,
            social_page_title=(
                f'Diff for Review Request #{review_request.display_id}: '
                f'{review_request_details.summary}'),
            social_page_image_url=social_page_image_url))

        diff_context = cast(SerializedReviewsDiffContext,
                            context['diff_context'])

        diff_context.update({
            'num_diffs': num_diffs,
            'comments_hint': self._get_comments_hint(
                pending_review=pending_review,
                all_comments=comments,
                all_diffsets=diffsets,
                all_commits=all_commits,
                filediffs_by_id=filediffs_by_id,
                current_diffset=diffset,
                current_interdiffset=interdiffset,
                current_base_commit=base_commit,
                current_tip_commit=tip_commit,
            ),
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
                review_request=review_request,
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

    def _get_comments_hint(
        self,
        *,
        pending_review: Optional[Review],
        all_comments: CommentsDict,
        all_diffsets: list[DiffSet],
        all_commits: list[DiffCommit],
        filediffs_by_id: dict[int, FileDiff],
        current_diffset: DiffSet,
        current_interdiffset: Optional[DiffSet],
        current_base_commit: Optional[DiffCommit],
        current_tip_commit: Optional[DiffCommit],
    ) -> SerializedCommentsHint:
        """Return the comments hint for the diff viewer.

        Args:
            pending_review (reviewboard.reviews.models.Review):
                The user's pending review, if any.

            all_comments (dict):
                All diff comments on the review request, sorted by which
                revision they're on.

            all_diffsets (list of reviewboard.diffviewer.models.DiffSet):
                All DiffSets on the review request.

            filediffs_by_id (dict):
                A mapping from FileDiff PK to the object.

            current_diffset (reviewboard.diffviewer.models.DiffSet):
                The current diffset being viewed.

            current_interdiffset (reviewboard.diffviewer.models.DiffSet):
                The current interdiffset, if the user is viewing an interdiff.

            current_base_commit (reviewboard.diffviewer.models.DiffCommit):
                The current base commit, if the user is viewing a commit range.

            current_tip_commit (reviewboard.diffviewer.models.DiffCommit):
                The current tip commit, if the user is viewing a commit range.

        Returns:
            SerializedCommentsHint:
            The comments hint to send to the client UI.
        """
        hint: SerializedCommentsHint = {
            'commits_with_comments': [],
            'diffsets_with_comments': [],
            'has_other_comments': False,
            'interdiffs_with_comments': [],
        }

        if pending_review is None:
            return hint

        pending_comments: list[Comment] = []

        # TODO: we need to also include file attachment comments that are part
        # of the diff.

        for comment in itertools.chain(*all_comments.values()):
            review = comment.get_review()

            if review.pk == pending_review.pk:
                pending_comments.append(comment)

        diffsets_by_id: dict[int, DiffSet] = {
            diffset.pk: diffset
            for diffset in all_diffsets
        }

        # The diffsets already have the filediffs pre-fetched.
        filediffs_by_id: dict[int, FileDiff] = {}

        for diffset in all_diffsets:
            for filediff in diffset.files.all():
                filediffs_by_id[filediff.pk] = filediff

        # A set of DiffSet IDs for diffs that have comments.
        diffset_ids_with_comments: set[int] = set()

        # A set of ID pairs for interdiffs that have comments.
        interdiffset_ids_with_comments: set[tuple[int, int]] = set()

        # A set of DiffSet ID plus two DiffCommit IDs for comments on commit
        # ranges.
        commit_ranges_with_comments: set[tuple[int, int, int]] = \
            set()

        # Value to use when the base commit ID for a comment is None, so that
        # commit_ranges_with_comments is sortable.
        NO_BASE_COMMIT = -1

        for comment in pending_comments:
            filediff = filediffs_by_id[comment.filediff_id]
            diffset_id = filediff.diffset_id

            if comment.interfilediff_id is not None:
                interfilediff = filediffs_by_id[comment.interfilediff_id]
                interdiffset_ids_with_comments.add(
                    (diffset_id, interfilediff.diffset_id))
            elif filediff.commit_id is None:
                diffset_ids_with_comments.add(diffset_id)
            else:
                tip_commit_id = filediff.commit_id
                base_filediff_id = comment.base_filediff_id

                if base_filediff_id is None:
                    base_commit_id = NO_BASE_COMMIT
                else:
                    base_filediff = filediffs_by_id[base_filediff_id]
                    base_commit_id = base_filediff.commit_id

                commit_ranges_with_comments.add(
                    (diffset_id, base_commit_id, tip_commit_id))

        commits_by_id: dict[int, DiffCommit] = {
            commit.pk: commit
            for commit in all_commits
        }

        has_other_comments: bool = False

        # Find all diffsets that have comments.
        current_is_diffset = (
            current_interdiffset is None and
            current_tip_commit is None and
            current_base_commit is None)
        diffsets_with_comments: list[SerializedDiffsetWithComments] = []

        for diffset_id in sorted(diffset_ids_with_comments):
            is_current = (current_is_diffset and
                          current_diffset.pk == diffset_id)

            if not is_current:
                has_other_comments = True

            diffsets_with_comments.append({
                'is_current': is_current,
                'revision': diffsets_by_id[diffset_id].revision,
            })

        # Now find all interdiffs that have comments.
        current_is_interdiffset = current_interdiffset is not None
        interdiffsets_with_comments: \
            list[SerializedInterdiffsetWithComments] = []

        for base_id, tip_id in sorted(interdiffset_ids_with_comments):
            base_diffset = diffsets_by_id[base_id]
            tip_diffset = diffsets_by_id[tip_id]

            is_current = (current_is_interdiffset and
                          current_diffset.pk == base_id and
                          current_interdiffset.pk == tip_id)

            if not is_current:
                has_other_comments = True

            interdiffsets_with_comments.append({
                'is_current': is_current,
                'new_revision': tip_diffset.revision,
                'old_revision': base_diffset.revision,
            })

        # Now find all commit ranges that have comments.
        current_is_commit_range = current_tip_commit is not None
        commits_with_comments: list[SerializedCommitWithComments] = []

        for diffset_id, base_commit_id, tip_commit_id in \
            sorted(commit_ranges_with_comments):
            diffset = diffsets_by_id[diffset_id]

            if base_commit_id == NO_BASE_COMMIT:
                # An unspecified base commit ID in the comment means that the
                # selected range started at the first commit in the series for
                # the diffset.
                base_commit: DiffCommit

                for commit in all_commits:
                    if commit.parent_id == diffset.base_commit_id:
                        base_commit = commit
                        break
                else:
                    logger.error('Unable to find base commit for diffset %s',
                                 diffset_id)
                    continue

                base_commit_pk = None
            else:
                base_commit = commits_by_id[base_commit_id]
                base_commit_pk = base_commit.pk

            tip_commit = commits_by_id[tip_commit_id]

            is_current = (
                current_is_commit_range and
                current_diffset.pk == diffset_id and
                current_tip_commit.pk == tip_commit_id and
                ((current_base_commit is None and
                  base_commit_id == NO_BASE_COMMIT) or
                 (current_base_commit is not None and
                  current_base_commit.pk == base_commit_id)))

            if not is_current:
                has_other_comments = True

            # Comments on commits are a little bit odd in that the
            # base_filediff_id and corresponding base_commit_id are actually
            # the parent commit of the one which is selected in the range
            # selector. We therefore want to serialize the PK of the
            # base_commit but the commit_id of the child of the base_commit
            base_commit_commit_id: Optional[str] = None

            if base_commit_id is NO_BASE_COMMIT:
                base_commit_commit_id = base_commit.commit_id
            else:
                for commit in all_commits:
                    if commit.parent_id == base_commit.commit_id:
                        base_commit_commit_id = commit.commit_id
                        break
                else:
                    logger.error('Unable to find parent commit for comment '
                                 'base commit pk=%s',
                                 base_commit_id)

            commits_with_comments.append({
                'base_commit_id': base_commit_commit_id,
                'base_commit_pk': base_commit_pk,
                'revision': diffset.revision,
                'is_current': is_current,
                'tip_commit_id': tip_commit.commit_id,
                'tip_commit_pk': tip_commit.pk,
            })

        hint['commits_with_comments'] = commits_with_comments
        hint['diffsets_with_comments'] = diffsets_with_comments
        hint['has_other_comments'] = has_other_comments
        hint['interdiffs_with_comments'] = interdiffsets_with_comments

        return hint
