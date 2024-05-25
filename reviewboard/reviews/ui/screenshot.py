"""Review UI for the legacy Screenshot object."""

from __future__ import annotations

from typing import Optional, Sequence, TYPE_CHECKING

from reviewboard.reviews.models import (
    Screenshot,
    ScreenshotComment,
)
from reviewboard.reviews.ui.base import ReviewUI, SerializedCommentBlocks
from reviewboard.reviews.ui.image import SerializedRegionComment

if TYPE_CHECKING:
    from djblets.util.typing import JSONDict

    from reviewboard.reviews.models import ReviewRequestDraft


class LegacyScreenshotReviewUI(ReviewUI[
    Screenshot,
    ScreenshotComment,
    SerializedRegionComment
]):
    """Review UI for the legacy Screenshot object."""

    name = 'Screenshot'
    model = Screenshot
    comment_model = ScreenshotComment

    js_model_class: str = 'RB.ScreenshotReviewable'
    js_view_class: str = 'RB.ImageReviewableView'

    def get_comments(self) -> Sequence[ScreenshotComment]:
        """Return all existing comments on the screenshot.

        Returns:
            list of reviewboard.reviews.screenshot_comment.ScreenshotComment:
            The list of comments for the page.
        """
        return self.obj.get_comments()

    def get_caption(
        self,
        draft: Optional[ReviewRequestDraft] = None,
    ) -> str:
        """Return the caption to show for the screenshot.

        Args:
            draft (reviewboard.reviews.models.review_request_draft.
                   ReviewRequestDraft, optional):
                The active review request draft for the user, if any.

        Returns:
            str:
            The caption for the screenshot.
        """
        assert isinstance(self.obj, Screenshot)
        if draft and self.obj.draft_caption:
            return self.obj.draft_caption

        return self.obj.caption

    def get_comment_link_text(
        self,
        comment: ScreenshotComment,
    ) -> str:
        """Return the text to link to a comment.

        Args:
            comment (reviewboard.reviews.models.screenshot_comment.
                     ScreenshotComment):
                The comment to return text for.

        Returns:
            str:
            The text used to link to the comment.
        """
        assert isinstance(self.obj, Screenshot)
        return self.obj.display_name

    def get_js_model_data(self) -> JSONDict:
        """Return data for the JavaScript model.

        Returns:
            dict:
            Data to serialize for the JavaScript model.
        """
        assert isinstance(self.obj, Screenshot)
        return {
            'imageURL': self.obj.image.url,
            'screenshotID': self.obj.pk,
        }

    def serialize_comments(
        self,
        comments: Sequence[ScreenshotComment],
    ) -> SerializedCommentBlocks[SerializedRegionComment]:
        """Serialize the comments for the screenshot.

        Args:
            comments (list of
                      reviewboard.reviews.models.ScreenshotComment):
                The comments to serialize.

        Returns:
            SerializedCommentBlocks:
            The serialized comments.
        """
        result: SerializedCommentBlocks[SerializedRegionComment] = {}

        for comment in self.flat_serialized_comments(comments):
            position = '%(x)sx%(y)s+%(width)s+%(height)s' % comment
            result.setdefault(position, []).append(comment)

        return result

    def serialize_comment(
        self,
        comment: ScreenshotComment,
    ) -> SerializedRegionComment:
        """Serialize a comment.

        Args:
            comment (reviewboard.reviews.models.ScreenshotComment):
                The comment to serialize.

        Returns:
            SerializedRegionComment:
            The serialized comment.
        """
        return {
            **super().serialize_comment(comment),
            'x': comment.x,
            'y': comment.y,
            'width': comment.w,
            'height': comment.h,
        }
