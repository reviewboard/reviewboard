"""A hook for adding new details to the display of comments."""

from __future__ import annotations

from djblets.extensions.hooks import ExtensionHook, ExtensionHookPoint


class CommentDetailDisplayHook(ExtensionHook, metaclass=ExtensionHookPoint):
    """This hook allows adding details to the display of comments.

    The hook can provide additional details to display for a comment in a
    review and e-mails.
    """

    def render_review_comment_detail(self, comment):
        """Render additional HTML for a comment on the page.

        Subclasses must implement this to provide HTML for use on the
        review request page or review dialog.

        The result is assumed to be HTML-safe. It's important that subclasses
        escape any data as needed.

        Args:
            comment (reviewboard.reviews.models.base_comment.BaseComment):
                The comment to render HTML for,

        Returns:
            django.utils.safestring.SafeText:
            The resulting HTML for the comment. This can be an empty string.
        """
        raise NotImplementedError

    def render_email_comment_detail(self, comment, is_html):
        """Render additional text or HTML for a comment in an e-mail.

        Subclasses must implement this to provide text or HTML (depending on
        the ``is_html`` flag) for use in an e-mail.

        If rendering HTML, the result is assumed to be HTML-safe. It's
        important that subclasses escape any data as needed.

        Args:
            comment (reviewboard.reviews.models.base_comment.BaseComment):
                The comment to render HTML for,

            is_html (bool):
                Whether this must return HTML content.

        Returns:
            django.utils.safestring.SafeText:
            The resulting HTML for the comment. This can be an empty string.
        """
        raise NotImplementedError
