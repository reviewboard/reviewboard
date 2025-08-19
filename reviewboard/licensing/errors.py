"""Licensing-related errors.

Version Added:
    7.1
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typelets.django.json import SerializableDjangoJSONDict


class LicenseActionError(Exception):
    """An error result from an action.

    Version Added:
        7.1
    """

    ######################
    # Instance variables #
    ######################

    #: The payload to return in the result.
    payload: SerializableDjangoJSONDict

    def __init__(
        self,
        message: str,
        *,
        payload: (SerializableDjangoJSONDict | None) = None,
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
