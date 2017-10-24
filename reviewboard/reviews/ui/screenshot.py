from __future__ import unicode_literals

from reviewboard.reviews.ui.base import ReviewUI
from reviewboard.reviews.models import Screenshot, ScreenshotComment


class LegacyScreenshotReviewUI(ReviewUI):
    name = 'Screenshot'
    model = Screenshot
    comment_model = ScreenshotComment

    js_model_class = 'RB.ScreenshotReviewable'
    js_view_class = 'RB.ImageReviewableView'

    def get_comments(self):
        """Return all existing comments on the screenshot.

        Returns:
            list of reviewboard.reviews.screenshot_comment.ScreenshotComment:
            The list of comments for the page.
        """
        return self.obj.get_comments()

    def get_caption(self, draft=None):
        """Return the caption to show for the screenshot.

        Args:
            draft (reviewboard.reviews.models.review_request_draft.
                   ReviewRequestDraft, optional):
                The active review request draft for the user, if any.

        Returns:
            unicode:
            The caption for the screenshot.
        """
        if draft and self.obj.draft_caption:
            return self.obj.draft_caption

        return self.obj.caption

    def get_comment_link_text(self, comment):
        """Return the text to link to a comment.

        Args:
            comment (reviewboard.reviews.models.screenshot_comment.
                     ScreenshotComment):
                The comment to return text for.

        Returns:
            unicode:
            The text used to link to the comment.
        """
        return self.obj.display_name

    def get_js_model_data(self):
        return {
            'imageURL': self.obj.image.url,
            'screenshotID': self.obj.id,
        }

    def serialize_comments(self, comments):
        result = {}
        serialized_comments = \
            super(LegacyScreenshotReviewUI, self).serialize_comments(comments)

        for serialized_comment in serialized_comments:
            position = '%(x)sx%(y)s+%(w)s+%(h)s' % serialized_comment
            result.setdefault(position, []).append(serialized_comment)

        return result

    def serialize_comment(self, comment):
        data = super(LegacyScreenshotReviewUI, self).serialize_comment(
            comment)

        data.update({
            'x': comment.x,
            'y': comment.y,
            'w': comment.w,
            'h': comment.h,
        })

        return data
