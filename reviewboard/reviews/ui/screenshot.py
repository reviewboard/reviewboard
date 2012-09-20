from reviewboard.reviews.ui.base import ReviewUI
from reviewboard.reviews.models import Screenshot, ScreenshotComment


class LegacyScreenshotReviewUI(ReviewUI):
    model = Screenshot
    comment_model = ScreenshotComment
    template_name = 'reviews/ui/screenshot.html'
    object_key = 'screenshot'
