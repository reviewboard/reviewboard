"""Information on product licenses.

Version Added:
    7.1
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Optional, Sequence, TYPE_CHECKING

if TYPE_CHECKING:
    from djblets.util.typing import JSONDict


class LicenseStatus(Enum):
    """The status of a license.

    Version Added:
        7.1
    """

    #: The license has not yet been activated.
    NOT_ACTIVATED = 'not-activated'

    #: The license is active.
    ACTIVE = 'active'

    #: The license has expired and is in a grace period.
    GRACE_PERIOD = 'grace-period'

    #: The license has expired.
    EXPIRED = 'expired'


@dataclass
class LicenseInfo:
    """Information on a license.

    This may be an active, expired, or trial license.

    License providers should use this to communicate information about a
    license to the rest of Review Board, but generally will have their own
    more tailored license structure behind it. This is not intended as a
    fully-featured license model.

    Version Added:
        7.1
    """

    #: The expiration date/time of the license.
    expires: Optional[datetime]

    #: A backend-specific ID for this license.
    #:
    #: This may be used for communication with a license server,
    #: client-side.
    license_id: str

    #: Who the license is licensed to.
    #:
    #: This may be the company or a division of a company (cost center).
    licensed_to: str

    #: Any displayable line items to show on license information.
    line_items: Sequence[str]

    #: A backend-specific plan ID for this license.
    plan_id: Optional[str]

    #: A display name for the plan.
    plan_name: Optional[str]

    #: The name of the product being licensed.
    product_name: str

    #: The active/expiration status of this license.
    status: LicenseStatus

    #: A descriptive summary of the license.
    summary: str

    #: Whether this is a trial license.
    is_trial: bool = False

    #: The backend-specific license instance.
    #:
    #: This is used purely for the convenience of a license provider.
    #: It may be ``None``.
    license_instance: Any = None

    #: Any private data needed by the LicenseProvider.
    #:
    #: This is only for private use by the LicenseProvider, and not for
    #: the API or any public display.
    private_data: Optional[JSONDict] = None
