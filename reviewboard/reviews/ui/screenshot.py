"""Review UI for the legacy Screenshot object."""

from __future__ import annotations

from typing import List, Optional, TYPE_CHECKING, cast

from reviewboard.reviews.ui.base import ReviewUI
from reviewboard.reviews.models import (
    BaseComment,
    Screenshot,
    ScreenshotComment,
)

if TYPE_CHECKING:
    from djblets.util.typing import JSONDict

    from reviewboard.reviews.models import ReviewRequestDraft


class LegacyScreenshotReviewUI(ReviewUI):
    """Review UI for the legacy Screenshot object."""

    name = 'Screenshot'
    model = Screenshot
    comment_model = ScreenshotComment

    js_model_class: str = 'RB.ScreenshotReviewable'
    js_view_class: str = 'RB.ImageReviewableView'

    def get_comments(self) -> List[ScreenshotComment]:
        """Return all existing comments on the screenshot.

        Returns:
            list of reviewboard.reviews.screenshot_comment.ScreenshotComment:
            The list of comments for the page.
        """
        assert isinstance(self.obj, Screenshot)
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
        comments: List[ScreenshotComment],
    ) -> JSONDict:
        """Serialize the comments for the screenshot.

        Args:
            comments (list of reviewboard.reviews.models.
                      screenshot_comment.ScreenshotComment):
                The comments to serialize.

        Returns:
            dict:
            The serialized comments.
        """
        result: JSONDict = {}
        serialized_comments = super().serialize_comments(
            cast(List[BaseComment], comments))

        for serialized_comment in serialized_comments:
            position = '%(x)sx%(y)s+%(w)s+%(h)s' % serialized_comment
            result.setdefault(position, []).append(serialized_comment)

        return result

    def serialize_comment(
        self,
        comment: ScreenshotComment,
    ) -> JSONDict:
        """Serialize a comment.

        Args:
            comment (reviewboard.reviews.models.screenshot_comment.
                     ScreenshotComment):
                The comment to serialize.

        Returns:
            dict:
            The serialized comment.
        """
        data = super(LegacyScreenshotReviewUI, self).serialize_comment(
            comment)

        data.update({
            'x': comment.x,
            'y': comment.y,
            'w': comment.w,
            'h': comment.h,
        })

        return data
