"""Signal handlers for review and review request related objects.

Version Added:
    6.0
"""

from __future__ import annotations

from typing import Type

from django.db.models.signals import pre_delete

from reviewboard.reviews.models import ReviewRequestDraft
from reviewboard.reviews.models.review_request import FileAttachmentState


def _on_review_request_draft_deleted(
    sender: Type[ReviewRequestDraft],
    instance: ReviewRequestDraft,
    using: str,
    **kwargs,
) -> None:
    """Handle any extra cleanup when a review request draft is deleted.

    Version Added:
        6.0

    Args:
        sender (type, unused):
            The sender of the signal.

        instance (reviewboard.reviews.models.ReviewRequestDraft):
            The review request draft being deleted.

        using (str, unused):
            The database alias being used.

        **kwargs (dict, unused):
            Unused additional keyword arguments.
    """
    draft_attachments = instance.get_file_attachments()

    if draft_attachments:
        # Load the data for the file attachments states.
        instance.get_file_attachments_data(
            draft_active_attachments=draft_attachments)

    for attachment in draft_attachments:
        state = instance.get_file_attachment_state(attachment)

        if state in (FileAttachmentState.NEW_REVISION,
                     FileAttachmentState.NEW):
            # This never has been and never will be published, so delete it.
            attachment.delete()

    review_request = instance.get_review_request()

    if hasattr(review_request, '_file_attachments_data'):
        # Clear the cached file attachments data.
        del review_request._file_attachments_data


def connect_signal_handlers() -> None:
    """Connect review and review request related signal handlers.

    Version Added:
        6.0
    """
    pre_delete.connect(_on_review_request_draft_deleted,
                       sender=ReviewRequestDraft)
