"""Signal handlers for file attachments.

Version Added:
    6.0
"""

from __future__ import annotations

from typing import Type

from django.db.models.signals import pre_delete

from reviewboard.attachments.models import FileAttachment


def _on_file_attachment_deleted(
    sender: Type[FileAttachment],
    instance: FileAttachment,
    using: str,
    **kwargs,
) -> None:
    """Handle any extra cleanup when a file attachment is deleted.

    This will ensure that any files associated with the file attachment
    are removed from the filesystem.

    Version Added:
        6.0

    Args:
        sender (type, unused):
            The sender of the signal.

        instance (reviewboard.attachments.models.FileAttachment):
            The file attachment being deleted.

        using (str, unused):
            The database alias being used.

        **kwargs (dict, unused):
            Unused additional keyword arguments.
    """
    instance.mimetype_handler.delete_associated_files()
    instance.file.delete(save=False)


def connect_signal_handlers() -> None:
    """Connect file attachment related signal handlers.

    Version Added:
        6.0
    """
    pre_delete.connect(_on_file_attachment_deleted,
                       sender=FileAttachment)
