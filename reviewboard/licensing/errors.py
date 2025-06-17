"""Licensing-related errors.

Version Added:
    7.1
"""

from __future__ import annotations

from djblets.util.typing import SerializableJSONDict


class LicenseActionError(Exception):
    """An error result from an action.

    Version Added:
        7.1
    """

    ######################
    # Instance variables #
    ######################

    #: The payload to return in the result.
    payload: SerializableJSONDict

    def __init__(
        self,
        message,
        *,
        payload: (SerializableJSONDict | None) = None,
    ) -> None:
        """Initialize the error.

        Args:
            message (str):
                The error message to display.

            payload (dict, optional):
                Optional payload data to return in the result.
        """
        super().__init__(message)

        self.payload = payload or {}
