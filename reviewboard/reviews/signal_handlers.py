"""Signal handlers for review and review request related objects.

Version Added:
    6.0
"""

from __future__ import annotations

from django.db.models.signals import pre_delete

from reviewboard.reviews.models import (ReviewRequest,
                                        ReviewRequestDraft)
from reviewboard.reviews.models.review_request import FileAttachmentState


def _on_review_request_draft_deleted(
    sender: type[ReviewRequestDraft],
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

    changedesc = instance.changedesc

    if changedesc and not changedesc.review_request.exists():
        changedesc.delete()

    diffset = instance.diffset

    if (diffset and
        diffset.pk is not None and
        diffset.history is None):
        diffset.delete()

    review_request = instance.get_review_request()

    if hasattr(review_request, '_file_attachments_data'):
        # Clear the cached file attachments data.
        del review_request._file_attachments_data


def _on_review_request_deleted(
    sender: type[ReviewRequest],
    instance: ReviewRequest,
    using: str,
    **kwargs,
) -> None:
    """Handle extra cleanup when a review request is deleted.

    Version Added:
        7.0

    Args:
        sender (type, unused):
            The sender of the signal.

        instance (reviewboard.reviews.models.ReviewRequest):
            The review request being deleted.

        using (str, unused):
            The database alias being used.

        **kwargs (dict, unused):
            Unused additional keyword arguments.
    """
    # We defined a bunch of these things using ManyToMany fields, when they
    # really ought to have been foreign keys. We therefore can't rely on
    # cascade, and need to clean them all up manually when the review request
    # is deleted.
    instance.changedescs.all().delete()

    if (instance.file_attachments_count or
        instance.inactive_file_attachments_count):
        instance.file_attachment_histories.all().delete()

        if instance.file_attachments_count:
            instance.file_attachments.all().delete()

        if instance.inactive_file_attachments_count:
            instance.inactive_file_attachments.all().delete()

    if instance.screenshots_count:
        instance.screenshots.all().delete()

    if instance.inactive_screenshots_count:
        instance.inactive_screenshots.all().delete()

    instance.diffset_history.delete()


def connect_signal_handlers() -> None:
    """Connect review and review request related signal handlers.

    Version Added:
        6.0
    """
    pre_delete.connect(_on_review_request_draft_deleted,
                       sender=ReviewRequestDraft)
    pre_delete.connect(_on_review_request_deleted,
                       sender=ReviewRequest)
