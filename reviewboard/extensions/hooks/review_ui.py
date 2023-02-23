"""A hook for adding new Review UIs."""

from __future__ import annotations

from djblets.extensions.hooks import ExtensionHook, ExtensionHookPoint

from reviewboard.reviews.ui.base import register_ui, unregister_ui


class ReviewUIHook(ExtensionHook, metaclass=ExtensionHookPoint):
    """This hook allows integration of Extension-defined Review UIs.

    This accepts a list of Review UIs specified by the Extension and
    registers them when the hook is created. Likewise, it unregisters
    the same list of Review UIs when the Extension is disabled.
    """

    def initialize(self, review_uis):
        """Initialize the hook.

        This will register the list of review UIs for use in reviewing
        file attachments.

        Args:
            review_uis (list of type):
                The list of review UI classes to register. Each must be a
                subclass of
                :py:class:`~reviewboard.reviews.ui.base.FileAttachmentReviewUI`.

        Raises:
            TypeError:
                The provided review UI class is not of a compatible type.
        """
        self.review_uis = review_uis

        for review_ui in self.review_uis:
            register_ui(review_ui)

    def shutdown(self):
        """Shut down the hook.

        This will unregister the list of review UIs.
        """
        for review_ui in self.review_uis:
            unregister_ui(review_ui)
