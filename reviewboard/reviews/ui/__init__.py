from reviewboard.signals import initializing


def _register_review_uis(**kwargs):
    """Registers all bundled review UIs."""
    from reviewboard.reviews.ui.base import register_ui
    from reviewboard.reviews.ui.image import ImageReviewUI
    from reviewboard.reviews.ui.markdownui import MarkdownReviewUI


    register_ui(ImageReviewUI)
    register_ui(MarkdownReviewUI)


initializing.connect(_register_review_uis)
