from __future__ import unicode_literals

from reviewboard.signals import initializing


def _register_review_uis(**kwargs):
    """Registers all bundled review UIs."""
    from reviewboard.reviews.ui.base import register_ui
    from reviewboard.reviews.ui.image import ImageReviewUI
    from reviewboard.reviews.ui.markdownui import MarkdownReviewUI
    from reviewboard.reviews.ui.text import TextBasedReviewUI

    register_ui(ImageReviewUI)
    register_ui(MarkdownReviewUI)
    register_ui(TextBasedReviewUI)


initializing.connect(_register_review_uis)
