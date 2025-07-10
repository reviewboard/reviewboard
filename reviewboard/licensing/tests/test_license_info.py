"""Unit tests for reviewboard.licensing.license.LicenseInfo.

Version Added:
    7.1
"""

from __future__ import annotations

from datetime import datetime, timedelta

import kgb
from django.utils import timezone

from reviewboard.licensing.license import LicenseInfo, LicenseStatus
from reviewboard.testing import TestCase


class LicenseInfoTests(kgb.SpyAgency, TestCase):
    """Unit tests for LicenseInfo.

    Version Added:
        7.1
    """

    def setUp(self) -> None:
        """Set up a unit test.

        This will set up a spy to ensure :py:func:`django.utils.timezone.now`
        always returns a static date/time.
        """
        super().setUp()

        self.spy_on(
            timezone.now,
            op=kgb.SpyOpReturn(timezone.make_aware(datetime(2025, 4, 19))))

    def test_get_expires_soon_with_unlicensed(self) -> None:
        """Testing LicenseInfo.get_expires_soon with unlicensed"""
        license_info = LicenseInfo(
            expires=timezone.now() + timedelta(days=1),
            license_id='test-license',
            licensed_to='Test User',
            product_name='Test Product',
            status=LicenseStatus.UNLICENSED)

        self.assertFalse(license_info.get_expires_soon())

    def test_get_expires_soon_with_no_expires(self) -> None:
        """Testing LicenseInfo.get_expires_soon without an expiration"""
        license_info = LicenseInfo(
            expires=None,
            license_id='test-license',
            licensed_to='Test User',
            product_name='Test Product',
            status=LicenseStatus.LICENSED)

        self.assertFalse(license_info.get_expires_soon())

    def test_get_expires_soon_with_trial_10_days(self) -> None:
        """Testing LicenseInfo.get_expires_soon with trial and expires in 10
        days
        """
        license_info = LicenseInfo(
            expires=timezone.now() + timedelta(days=10),
            is_trial=True,
            license_id='test-license',
            licensed_to='Test User',
            product_name='Test Product',
            status=LicenseStatus.LICENSED)

        self.assertTrue(license_info.get_expires_soon())

    def test_get_expires_soon_with_trial_11_days(self) -> None:
        """Testing LicenseInfo.get_expires_soon with trial and expires in 11
        days
        """
        license_info = LicenseInfo(
            expires=timezone.now() + timedelta(days=11),
            is_trial=True,
            license_id='test-license',
            licensed_to='Test User',
            product_name='Test Product',
            status=LicenseStatus.LICENSED)

        self.assertFalse(license_info.get_expires_soon())

    def test_get_expires_soon_with_purchased_30_days(self) -> None:
        """Testing LicenseInfo.get_expires_soon with purchased license and
        30 days
        """
        license_info = LicenseInfo(
            expires=timezone.now() + timedelta(days=30),
            license_id='test-license',
            licensed_to='Test User',
            product_name='Test Product',
            status=LicenseStatus.LICENSED)

        self.assertTrue(license_info.get_expires_soon())

    def test_get_expires_soon_with_purchased_31_days(self) -> None:
        """Testing LicenseInfo.get_expires_soon with purchased license and
        31 days
        """
        license_info = LicenseInfo(
            expires=timezone.now() + timedelta(days=31),
            license_id='test-license',
            licensed_to='Test User',
            product_name='Test Product',
            status=LicenseStatus.LICENSED)

        self.assertFalse(license_info.get_expires_soon())
