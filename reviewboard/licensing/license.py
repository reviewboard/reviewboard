"""Information on product licenses.

Version Added:
    7.1
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from django.utils import timezone

if TYPE_CHECKING:
    from collections.abc import Sequence
    from typing import Any


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

    ######################
    # Instance variables #
    ######################

    #: Whether a new license file can be manually uploaded for this license.
    can_upload_license: bool

    #: The expiration date/time of the license.
    expires: datetime | None

    #: The number of grace period days remaining on the license.
    #:
    #: This is only considered when the license is expired.
    grace_period_days_remaining: int

    #: Whether this is a trial license.
    is_trial: bool

    #: A backend-specific ID for this license.
    #:
    #: This may be used for communication with a license server,
    #: client-side.
    license_id: str

    #: The backend-specific license instance.
    #:
    #: This is used purely for the convenience of a license provider.
    #: It may be ``None``.
    license_instance: Any

    #: Who the license is licensed to.
    #:
    #: This may be the company or a division of a company (cost center).
    licensed_to: str

    #: Any displayable line items to show on license information.
    line_items: Sequence[str]

    #: A backend-specific plan ID for this license.
    plan_id: str | None

    #: A display name for the plan.
    plan_name: str | None

    #: The name of the product being licensed.
    product_name: str

    #: The active/expiration status of this license.
    status: LicenseStatus

    #: A descriptive summary of the license.
    #:
    #: If not provided, one will be automatically generated based off the
    #: product name and status.
    summary: str

    def __init__(
        self,
        *,
        license_id: str,
        licensed_to: str,
        product_name: str,
        can_upload_license: bool = False,
        expires: (datetime | None) = None,
        grace_period_days_remaining: int = 0,
        is_trial: bool = False,
        license_instance: Any = None,
        line_items: (Sequence[str] | None) = None,
        plan_id: (str | None) = None,
        plan_name: (str | None) = None,
        status: LicenseStatus = LicenseStatus.UNLICENSED,
        summary: str = '',
    ) -> None:
        """Initialize the license information.

        Args:
            licensed_id (str):
                A backend-specific ID for this license.

                This may be used for communication with a license server,
                client-side.

            licensed_to (str):
                Who the license is licensed to.

                This may be the company or a division of a company (cost
                center).

            product_name (str):
                The name of the product being licensed.

            can_upload_license (bool, optional):
                Whether a new license file can be manually uploaded for
                this license.

            expires (datetime.datetime, optional):
                The expiration date/time of the license.

            grace_period_days_remaining (int, optional):
                The number of grace period days remaining on the license.

                This is only considered when the license is expired.

            is_trial (bool, optional):
                Whether this is a trial license.

            license_instance (object, optional):
                The backend-specific license instance.

                This is used purely for the convenience of a license provider.
                It may be ``None``.

            line_items (Sequence[str], optional):
                Any displayable line items to show on license information.

            plan_id (str, optional):
                A backend-specific plan ID for this license.

            plan_name (str, optional):
                A display name for the plan.

            status (LicenseStatus, optional):
                The active/expiration status of this license.

            summary (str, optional):
                A descriptive summary of the license.

                If not provided, one will be automatically generated based
                off the product name and status.
        """
        self.license_id = license_id
        self.licensed_to = licensed_to
        self.product_name = product_name
        self.can_upload_license = can_upload_license
        self.expires = expires
        self.grace_period_days_remaining = grace_period_days_remaining
        self.is_trial = is_trial
        self.license_instance = license_instance
        self.line_items = line_items or []
        self.plan_id = plan_id
        self.plan_name = plan_name
        self.status = status
        self.summary = summary

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
