"""Error definitions for attachments.

Version Added:
    5.0
"""

from __future__ import annotations


class FileTooBigError(ValueError):
    """The supplied file was too large.

    Version Added:
        5.0
    """

    ######################
    # Instance variables #
    ######################

    #: The maximum size (in bytes) of file attachments.
    max_attachment_size: int

    def __init__(
        self,
        message: str,
        *,
        max_attachment_size: int,
    ) -> None:
        """Initialize the error.

        Args:
            message (str):
                The error message to display.

            max_attachment_size (int):
                The maximum allowable attachment file size, in bytes.
        """
        super().__init__(message)
        self.max_attachment_size = max_attachment_size
