"""A Review UI for diffs.

Version Added:
    7.0
"""

from __future__ import annotations

from typing import Optional, Sequence, TYPE_CHECKING

from reviewboard.diffviewer.models import FileDiff
from reviewboard.reviews.models import Comment
from reviewboard.reviews.ui.base import (ReviewUI,
                                         SerializedComment,
                                         SerializedCommentBlocks)

if TYPE_CHECKING:
    from django.http import HttpRequest

    from reviewboard.reviews.models import ReviewRequest


class SerializedDiffComment(SerializedComment):
    """Serialized comment data for diffs.

    This must be kept in sync with the definitions in
    :file:`reviewboard/static/rb/js/reviews/models/commentData.ts`.

    Version Added:
        7.0
    """

    #: The line number that the comment starts on.
    line: int

    #: The number of lines that the comment spans.
    num_lines: int


class DiffReviewUI(ReviewUI[FileDiff, Comment, SerializedDiffComment]):
    """A Review UI for diffs.

    Version Added:
        7.0
    """

    name = 'Diff'

    js_model_class: str = 'RB.DiffReviewable'
    js_view_class: str = 'RB.DiffReviewableView'

    ######################
    # Instance variables #
    ######################

    #: The FileDiff for the base change in a commit range.
    base_filediff: Optional[FileDiff]

    #: The tip FileDiff when viewing an interdiff.
    interfilediff: Optional[FileDiff]

    def __init__(
        self,
        *,
        review_request: ReviewRequest,
        obj: FileDiff,
        base_filediff: Optional[FileDiff],
        interfilediff: Optional[FileDiff],
        request: HttpRequest,
    ) -> None:
        """Initialize the Review UI.

        Args:
            review_request (reviewboard.reviews.models.review_request.
                            ReviewRequest):
                The review request containing the object to review.

            obj (reviewboard.diffviewer.models.FileDiff):
                The object being reviewed.

            base_filediff (reviewboard.diffviewer.models.FileDiff):
                The base filediff to use, when viewing a commit range.

            interfilediff (reviewboard.diffviewer.models.FileDiff):
                The interdiff to use, when viewing an interdiff.

            request (django.http.HttpRequest):
                The HTTP request.
        """
        assert isinstance(obj, FileDiff)

        super().__init__(
            review_request=review_request,
            obj=obj)

        self.base_filediff = base_filediff
        self.interfilediff = interfilediff
        self.request = request

    def serialize_comments(
        self,
        comments: Sequence[Comment],
    ) -> SerializedCommentBlocks[SerializedDiffComment]:
        """Serialize the comments for the diff.

        Args:
            comments (list of reviewboard.reviews.models.Comment):
                The list of objects to serialize.

        Returns:
            SerializedCommentBlocks:
            The serialized comments.
        """
        result: SerializedCommentBlocks[SerializedDiffComment] = {}

        for comment in self.flat_serialized_comments(comments):
            key = f'{comment["line"]}-{comment["num_lines"]}'

            result.setdefault(key, []).append(comment)

        return result

    def serialize_comment(
        self,
        comment: Comment,
    ) -> SerializedDiffComment:
        """Serialize a comment.

        Args:
            comment (reviewboard.reviews.models.Comment):
                The comment to serialize.

        Returns:
            SerializedDiffComment:
            The serialized comment.
        """
        return {
            **super().serialize_comment(comment),
            'line': comment.first_line,
            'num_lines': comment.num_lines,
        }
