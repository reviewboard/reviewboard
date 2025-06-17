"""Information on product licenses.

Version Added:
    7.1
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional, Sequence, TYPE_CHECKING

from django.utils import timezone

if TYPE_CHECKING:
    from djblets.util.typing import JSONDict


class LicenseStatus(Enum):
    """The status of a license.

    Version Added:
        7.1
    """

    #: The license has not yet been activated.
    UNLICENSED = 'unlicensed'

    #: The license is applied and active.
    LICENSED = 'licensed'

    #: The license has expired and is in a grace period.
    EXPIRED_GRACE_PERIOD = 'expired-grace-period'

    #: The license has expired and is past its grace period.
    HARD_EXPIRED = 'hard-expired'


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

    #: A backend-specific ID for this license.
    #:
    #: This may be used for communication with a license server,
    #: client-side.
    license_id: str

    #: Who the license is licensed to.
    #:
    #: This may be the company or a division of a company (cost center).
    licensed_to: str

    #: The name of the product being licensed.
    product_name: str

    #: The expiration date/time of the license.
    expires: (datetime | None) = None

    #: A backend-specific plan ID for this license.
    plan_id: (str | None) = None

    #: A display name for the plan.
    plan_name: (str | None) = None

    #: The active/expiration status of this license.
    status: LicenseStatus = LicenseStatus.UNLICENSED

    #: A descriptive summary of the license.
    #:
    #: If not provided, one will be automatically generated based off the
    #: product name and status.
    summary: str = ''

    #: Any displayable line items to show on license information.
    line_items: Sequence[str] = field(default_factory=list)

    #: Whether a new license file can be manually uploaded for this license.
    can_upload_license: bool = False

    #: The number of grace period days remaining on the license.
    #:
    #: This is only considered when the license is expired.
    grace_period_days_remaining: int = 0

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
    private_data: (JSONDict | None) = None

    def get_expires_soon(self) -> bool:
        """Return whether or not the license expires soon.

        "Soon" is defined as the result of
        :py:meth:`get_expires_soon_days_threshold`, which can be overridden
        by subclasses. By default, this is defined as within 10 days for a
        trial license or within 30 days for a non-trial license.

        This does not include the grace period.

        Returns:
            bool:
            ``True`` if the license expires soon. ``False`` if it does not,
            or if the license has already expired.
        """
        if self.status != LicenseStatus.LICENSED or not self.expires:
            return False

        days_threshold = self.get_expires_soon_days_threshold()
        days_remaining = (self.expires - timezone.now()).days

        return days_remaining <= days_threshold

    def get_expires_soon_days_threshold(self) -> int:
        """Return the number of days considered "soon" for expiration.

        This can be overridden by subclasses to change the number of days
        based on the term or renewal times of a license.

        By default, this is defined as within 10 days for a trial license or
        within 30 days for a non-trial license.

        This does not include the grace period.

        Returns:
            int:
            The number of days considered "soon" for expiration, based on
            the license state or type.
        """
        if self.is_trial:
            return 10
        else:
            return 30
