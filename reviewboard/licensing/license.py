"""Information on product licenses.

Version Added:
    7.1
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import TYPE_CHECKING

from django.utils import timezone
from django.utils.translation import (gettext_lazy as _,
                                      ngettext_lazy as N_)
from djblets.util.typing import StrOrPromise

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from datetime import datetime
    from typing import Any


logger = logging.getLogger(__name__)


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

    def get_summary(self) -> str:
        """Return a summary for the license.

        This will return :py:attr:`summary` if provided. Otherwise, it
        will generate a suitable summary based on the state of the license.

        Subclasses can override this to provide custom summaries.

        Returns:
            str:
            The summary of the license.
        """
        summary: StrOrPromise = self.summary

        if summary:
            assert isinstance(summary, str)

            return summary

        status = self.status

        key: list[str] = []
        fmt_args: dict[str, object] = {
            'product': self.product_name,
        }

        if status != LicenseStatus.UNLICENSED:
            is_trial = self.is_trial
            plan_name = self.plan_name
            expires = self.expires

            if is_trial:
                key.append('trial')

            if plan_name:
                key.append('plan')
                fmt_args['plan'] = self.format_plan_name()

            if status == LicenseStatus.LICENSED:
                if expires is not None:
                    fmt_args['days_remaining'] = \
                        (expires - timezone.now()).days

                    if not is_trial and self.get_expires_soon():
                        key.append('expires_soon')
                else:
                    assert not is_trial
            elif status == LicenseStatus.EXPIRED_GRACE_PERIOD:
                fmt_args['days_remaining'] = self.grace_period_days_remaining

        try:
            summary = _DEFAULT_SUMMARY_FORMATS[status][tuple(key)]
        except KeyError:
            logger.error('Hit a bad license summary state for license %r: '
                         'Missing string for status=%r, key %r',
                         self, status, tuple(key))

            summary = _("{product}'s license status is unknown")

        return summary.format(**fmt_args)

    def format_plan_name(self) -> str:
        """Return a formatted version of the plan name.

        This allows a license implementation to provide a custom way of
        formatting the plan name for use in the summary.

        By default, this returns the plan name as-is.

        This may not be used if a plan name is not set.

        Returns:
            str:
            The formatted plan name.
        """
        plan_name = self.plan_name
        assert plan_name

        return plan_name

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

    def __repr__(self) -> str:
        """Return a representation of this license.

        Returns:
            str:
            The representation.
        """
        cls_name = type(self).__name__

        return (
            f'<{cls_name}'
            f'(license_id={self.license_id!r},'
            f' status={self.status!r},'
            f' product_name={self.product_name!r},'
            f' plan_id={self.plan_id!r},'
            f' plan_name={self.plan_name!r},'
            f' licensed_to={self.licensed_to!r},'
            f' is_trial={self.is_trial},'
            f' expires={self.expires!r},'
            f' grace_period_days_remaining={self.grace_period_days_remaining},'
            f' line_items={self.line_items!r}>'
        )


if TYPE_CHECKING:
    _DefaultSummaryFormats = Mapping[
        LicenseStatus,
        Mapping[tuple[str, ...], StrOrPromise],
    ]


#: Strings for the default license summaries, based on state.
#:
#: This provides a single place to look up the default summaries for a
#: license based on the trial/purchased state, presence of a plan, and
#: whether there are optional days remaining to display for the license
#: term.
#:
#: Version Added:
#:     7.1
_DEFAULT_SUMMARY_FORMATS: _DefaultSummaryFormats = {
    LicenseStatus.UNLICENSED: {
        (): _('{product} is not licensed!'),
    },

    LicenseStatus.LICENSED: {
        # Purchased license is active
        (): _('License for {product} is active'),

        # Purchased license with plan is active
        ('plan',): _('License for {product} {plan} is active'),

        # Purchased license expires soon
        ('expires_soon',): N_(
            ('License for {product} expires in {days_remaining} day'),
            ('License for {product} expires in {days_remaining} days'),
            'days_remaining'
        ),

        # Purchased license with plan expires soon
        ('plan', 'expires_soon'): N_(
            ('License for {product} {plan} expires in {days_remaining} '
             'day'),
            ('License for {product} {plan} expires in {days_remaining} '
             'days'),
            'days_remaining'
        ),

        # Trial license is active
        ('trial',): N_(
            'Trial license for {product} ends in {days_remaining} day',
            'Trial license for {product} ends in {days_remaining} days',
            'days_remaining',
        ),

        # Trial license with plan is active
        ('trial', 'plan'): N_(
            'Trial license for {product} {plan} ends in {days_remaining} day',
            'Trial license for {product} {plan} ends in {days_remaining} days',
            'days_remaining',
        ),
    },

    LicenseStatus.EXPIRED_GRACE_PERIOD: {
        # Purchased license expired with grace period
        (): N_(
            ('License for {product} expired and will stop working in '
             '{days_remaining} day'),
            ('License for {product} expired and will stop working in '
             '{days_remaining} days'),
            'days_remaining'
        ),

        # Purchased license with plan expired with grace period
        ('plan',): N_(
            ('License for {product} {plan} expired and will stop working '
             'in {days_remaining} day'),
            ('License for {product} {plan} expired and will stop working '
             'in {days_remaining} days'),
            'days_remaining'
        ),

        # Trial license expired with grace period
        ('trial',): N_(
            ('Trial license for {product} expired and will stop working in '
             '{days_remaining} day'),
            ('Trial license for {product} expired and will stop working in '
             '{days_remaining} days'),
            'days_remaining'
        ),

        # Trial license with plan expired with grace period
        ('trial', 'plan'): N_(
            ('Trial license for {product} {plan} expired and will stop '
             'working in {days_remaining} day'),
            ('Trial license for {product} {plan} expired and will stop '
             'working in {days_remaining} days'),
            'days_remaining'
        ),
    },

    LicenseStatus.HARD_EXPIRED: {
        # Purchased license hard-expired
        (): _('License for {product} expired and needs to be renewed'),

        # Purchased license with plan hard-expired
        ('plan',): _(
            'License for {product} {plan} expired and needs to be renewed'
        ),

        # Trial license hard-expired
        ('trial',): _('Trial license for {product} expired'),

        # Trial license with plan hard-expired
        ('trial', 'plan'): _('Trial license for {product} {plan} expired'),
    },
}
