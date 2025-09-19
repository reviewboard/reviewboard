"""License check processing types.

Version Added:
    7.1
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

from typing_extensions import NotRequired, TypedDict

if TYPE_CHECKING:
    from collections.abc import Mapping

    from typelets.django.json import SerializableDjangoJSONDict


# TODO: Switch to StrEnum when we're on Python 3.11+.
class ProcessCheckLicenseResultStatus(str, Enum):
    """Status results for license check processing.

    This represents the possible outcomes when checking for and applying new
    updates to licenses.

    Version Added:
        7.1
    """

    #: A new license has been applied.
    APPLIED = 'applied'

    #: There was an error applying a new license.
    ERROR_APPLYING = 'error-applying'

    #: The latest license is already applied.
    HAS_LATEST = 'has-latest'


class RequestCheckLicenseResult(TypedDict):
    """Result of requesting a license check.

    This provides data and information needed to perform a client-side check
    with a license server.

    Version Added:
        7.1
    """

    #: The data to send to the license server.
    #:
    #: If this is a dictionary, it will be sent as HTTP form data.
    #:
    #: If this is a string (such as a JSON-encoded string), it will be sent
    #: as the POST body.
    data: Mapping[str, str] | str

    #: The URL to the license server.
    url: str

    #: Credentials to pass in the request to the server.
    credentials: NotRequired[Mapping[str, str]]

    #: HTTP headers to pass in the request to the server.
    headers: NotRequired[Mapping[str, str]]

    #: An optional session token sent back along with a license response.
    session_token: NotRequired[str]


class ProcessCheckLicenseResult(TypedDict):
    """Result of processing a license check.

    This contains the status of the license check and any associated license
    information.

    Version Added:
        7.1
    """

    #: The status of the license check.
    status: ProcessCheckLicenseResultStatus

    #: Optional license information returned from the check.
    #:
    #: This is a map of license IDs to serialized license dictionaries. If
    #: the serialized dictionary is None, the license is considered to be
    #: removed.
    license_info: NotRequired[Mapping[str, SerializableDjangoJSONDict | None]]
