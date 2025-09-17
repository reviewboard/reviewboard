"""License action definitions.

Version Added:
    7.1
"""

from __future__ import annotations

from typing import Mapping, Protocol, TYPE_CHECKING

from djblets.util.typing import JSONValue
from typing_extensions import TypedDict

if TYPE_CHECKING:
    from django.http import HttpRequest
    from djblets.util.typing import SerializableJSONDict, StrOrPromise
    from typing_extensions import NotRequired, TypeAlias

    from reviewboard.licensing.license import LicenseInfo


#: Data passed to an action handler.
#:
#: This is a mapping of string keys to JSON values.
#:
#: Version Added:
#:     7.1
LicenseActionData: TypeAlias = Mapping[str, JSONValue]


class LicenseAction(TypedDict):
    """An action that can be performed on a license.

    These will be displayed in the UI when displaying license information.

    Version Added:
        7.1
    """

    #: The provider-unique ID of the action.
    action_id: str

    #: The localized label for the action.
    label: StrOrPromise

    #: The URL to navigate to when clicking the action.
    #:
    #: If omitted or ``None``, it's up to the license implementation to
    #: provide JavaScript management for the action.
    url: NotRequired[str | None]


class LicenseActionHandler(Protocol):
    """Protocol for a method used to handle a license action request.

    This is the signature required for any :samp:`handle_{action}_action`
    methods on a license provider.

    Version Added:
        7.1
    """

    def __call__(
        self,
        *,
        license_info: LicenseInfo,
        action_data: LicenseActionData,
        request: HttpRequest | None,
    ) -> SerializableJSONDict:
        ...
