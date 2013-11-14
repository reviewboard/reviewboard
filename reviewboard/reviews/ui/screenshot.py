from __future__ import unicode_literals

from reviewboard.reviews.ui.base import ReviewUI
from reviewboard.reviews.models import Screenshot, ScreenshotComment


class LegacyScreenshotReviewUI(ReviewUI):
    name = 'Screenshot'
    model = Screenshot
    comment_model = ScreenshotComment

    js_model_class = 'RB.ScreenshotReviewable'
    js_view_class = 'RB.ImageReviewableView'

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
