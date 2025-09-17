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

    def test_get_summary_with_custom_summary(self) -> None:
        """Testing LicenseInfo.get_summary with custom summary"""
        license_info = LicenseInfo(
            product_name='Test Product',
            license_id='test-license',
            licensed_to='Test User',
            summary='This is my custom summary')

        self.assertEqual(license_info.get_summary(),
                         'This is my custom summary')

    def test_get_summary_with_unlicensed(self) -> None:
        """Testing LicenseInfo.get_summary with unlicensed state"""
        license_info = LicenseInfo(
            product_name='Test Product',
            license_id='test-license',
            licensed_to='Test User',
            status=LicenseStatus.UNLICENSED)

        self.assertEqual(license_info.get_summary(),
                         'Test Product is not licensed!')

    def test_get_summary_with_licensed(self) -> None:
        """Testing LicenseInfo.get_summary with purchased license"""
        license_info = LicenseInfo(
            product_name='Test Product',
            license_id='test-license',
            licensed_to='Test User',
            status=LicenseStatus.LICENSED)

        self.assertEqual(license_info.get_summary(),
                         'License for Test Product is active')

    def test_get_summary_with_licensed_plan(self) -> None:
        """Testing LicenseInfo.get_summary with purchased license with plan"""
        license_info = LicenseInfo(
            product_name='Test Product',
            license_id='test-license',
            licensed_to='Test User',
            plan_name='Super Plan',
            status=LicenseStatus.LICENSED)

        self.assertEqual(license_info.get_summary(),
                         'License for Test Product Super Plan is active')

    def test_get_summary_with_licensed_expires_soon(self) -> None:
        """Testing LicenseInfo.get_summary with purchased license expires
        soon
        """
        license_info = LicenseInfo(
            expires=timezone.now() + timedelta(days=10),
            product_name='Test Product',
            license_id='test-license',
            licensed_to='Test User',
            status=LicenseStatus.LICENSED)

        self.assertEqual(license_info.get_summary(),
                         'License for Test Product expires in 10 days')

    def test_get_summary_with_licensed_plan_expires_soon(self) -> None:
        """Testing LicenseInfo.get_summary with purchased license with plan
        expires soon
        """
        license_info = LicenseInfo(
            expires=timezone.now() + timedelta(days=10),
            product_name='Test Product',
            license_id='test-license',
            licensed_to='Test User',
            plan_name='Super Plan',
            status=LicenseStatus.LICENSED)

        self.assertEqual(license_info.get_summary(),
                         'License for Test Product Super Plan expires in '
                         '10 days')

    def test_get_summary_with_trial(self) -> None:
        """Testing LicenseInfo.get_summary with trial license"""
        license_info = LicenseInfo(
            expires=timezone.now() + timedelta(days=10),
            product_name='Test Product',
            license_id='test-license',
            licensed_to='Test User',
            is_trial=True,
            status=LicenseStatus.LICENSED)

        self.assertEqual(license_info.get_summary(),
                         'Trial license for Test Product ends in 10 days')

    def test_get_summary_with_trial_1_day_remaining(self) -> None:
        """Testing LicenseInfo.get_summary with trial license with 1 day
        remaining
        """
        license_info = LicenseInfo(
            expires=timezone.now() + timedelta(days=1),
            product_name='Test Product',
            license_id='test-license',
            licensed_to='Test User',
            is_trial=True,
            status=LicenseStatus.LICENSED)

        self.assertEqual(license_info.get_summary(),
                         'Trial license for Test Product ends in 1 day')

    def test_get_summary_with_trial_plan(self) -> None:
        """Testing LicenseInfo.get_summary with trial license with plan"""
        license_info = LicenseInfo(
            expires=timezone.now() + timedelta(days=10),
            product_name='Test Product',
            license_id='test-license',
            licensed_to='Test User',
            plan_name='Super Plan',
            is_trial=True,
            status=LicenseStatus.LICENSED)

        self.assertEqual(license_info.get_summary(),
                         'Trial license for Test Product Super Plan ends '
                         'in 10 days')

    def test_get_summary_with_trial_plan_1_day_remaining(self) -> None:
        """Testing LicenseInfo.get_summary with trial license with plan with
        1 day remaining
        """
        license_info = LicenseInfo(
            expires=timezone.now() + timedelta(days=1),
            product_name='Test Product',
            license_id='test-license',
            licensed_to='Test User',
            plan_name='Super Plan',
            is_trial=True,
            status=LicenseStatus.LICENSED)

        self.assertEqual(license_info.get_summary(),
                         'Trial license for Test Product Super Plan ends '
                         'in 1 day')

    def test_get_summary_with_expired_license(self) -> None:
        """Testing LicenseInfo.get_summary with expired license"""
        license_info = LicenseInfo(
            expires=timezone.now() - timedelta(days=10),
            grace_period_days_remaining=5,
            product_name='Test Product',
            license_id='test-license',
            licensed_to='Test User',
            status=LicenseStatus.EXPIRED_GRACE_PERIOD)

        self.assertEqual(license_info.get_summary(),
                         'License for Test Product expired and will stop '
                         'working in 5 days')

    def test_get_summary_with_expired_license_1_day_remaining(self) -> None:
        """Testing LicenseInfo.get_summary with expired license and 1 day
        remaining
        """
        license_info = LicenseInfo(
            expires=timezone.now() - timedelta(days=10),
            grace_period_days_remaining=1,
            product_name='Test Product',
            license_id='test-license',
            licensed_to='Test User',
            status=LicenseStatus.EXPIRED_GRACE_PERIOD)

        self.assertEqual(license_info.get_summary(),
                         'License for Test Product expired and will stop '
                         'working in 1 day')

    def test_get_summary_with_expired_license_plan(self) -> None:
        """Testing LicenseInfo.get_summary with expired license with plan"""
        license_info = LicenseInfo(
            expires=timezone.now() - timedelta(days=10),
            grace_period_days_remaining=5,
            product_name='Test Product',
            license_id='test-license',
            licensed_to='Test User',
            plan_name='Super Plan',
            status=LicenseStatus.EXPIRED_GRACE_PERIOD)

        self.assertEqual(license_info.get_summary(),
                         'License for Test Product Super Plan expired '
                         'and will stop working in 5 days')

    def test_get_summary_with_expired_license_plan_1_day_remaining(
        self,
    ) -> None:
        """Testing LicenseInfo.get_summary with expired license with plan"""
        license_info = LicenseInfo(
            expires=timezone.now() - timedelta(days=10),
            grace_period_days_remaining=1,
            product_name='Test Product',
            license_id='test-license',
            licensed_to='Test User',
            plan_name='Super Plan',
            status=LicenseStatus.EXPIRED_GRACE_PERIOD)

        self.assertEqual(license_info.get_summary(),
                         'License for Test Product Super Plan expired '
                         'and will stop working in 1 day')

    def test_get_summary_with_expired_trial(self) -> None:
        """Testing LicenseInfo.get_summary with expired trial license"""
        license_info = LicenseInfo(
            expires=timezone.now() - timedelta(days=10),
            grace_period_days_remaining=5,
            product_name='Test Product',
            license_id='test-license',
            licensed_to='Test User',
            is_trial=True,
            status=LicenseStatus.EXPIRED_GRACE_PERIOD)

        self.assertEqual(license_info.get_summary(),
                         'Trial license for Test Product expired and will '
                         'stop working in 5 days')

    def test_get_summary_with_expired_trial_1_day_remaining(self) -> None:
        """Testing LicenseInfo.get_summary with expired trial license with
        1 day remaining
        """
        license_info = LicenseInfo(
            expires=timezone.now() - timedelta(days=10),
            grace_period_days_remaining=1,
            product_name='Test Product',
            license_id='test-license',
            licensed_to='Test User',
            is_trial=True,
            status=LicenseStatus.EXPIRED_GRACE_PERIOD)

        self.assertEqual(license_info.get_summary(),
                         'Trial license for Test Product expired and will '
                         'stop working in 1 day')

    def test_get_summary_with_expired_trial_plan(self) -> None:
        """Testing LicenseInfo.get_summary with expired trial license with
        plan
        """
        license_info = LicenseInfo(
            expires=timezone.now() - timedelta(days=10),
            grace_period_days_remaining=5,
            product_name='Test Product',
            license_id='test-license',
            licensed_to='Test User',
            plan_name='Super Plan',
            is_trial=True,
            status=LicenseStatus.EXPIRED_GRACE_PERIOD)

        self.assertEqual(license_info.get_summary(),
                         'Trial license for Test Product Super Plan '
                         'expired and will stop working in 5 days')

    def test_get_summary_with_expired_trial_plan_1_day_remaining(
        self,
    ) -> None:
        """Testing LicenseInfo.get_summary with expired trial license with
        plan and 1 day remaining
        """
        license_info = LicenseInfo(
            expires=timezone.now() - timedelta(days=10),
            grace_period_days_remaining=1,
            product_name='Test Product',
            license_id='test-license',
            licensed_to='Test User',
            plan_name='Super Plan',
            is_trial=True,
            status=LicenseStatus.EXPIRED_GRACE_PERIOD)

        self.assertEqual(license_info.get_summary(),
                         'Trial license for Test Product Super Plan '
                         'expired and will stop working in 1 day')

    def test_get_summary_with_hard_expired_license(self) -> None:
        """Testing LicenseInfo.get_summary with hard-expired license"""
        license_info = LicenseInfo(
            expires=timezone.now() - timedelta(days=10),
            grace_period_days_remaining=5,
            product_name='Test Product',
            license_id='test-license',
            licensed_to='Test User',
            status=LicenseStatus.HARD_EXPIRED)

        self.assertEqual(license_info.get_summary(),
                         'License for Test Product expired and needs to be '
                         'renewed')

    def test_get_summary_with_hard_expired_license_plan(self) -> None:
        """Testing LicenseInfo.get_summary with hard-expired license with plan
        """
        license_info = LicenseInfo(
            expires=timezone.now() - timedelta(days=10),
            grace_period_days_remaining=5,
            product_name='Test Product',
            license_id='test-license',
            licensed_to='Test User',
            plan_name='Super Plan',
            status=LicenseStatus.HARD_EXPIRED)

        self.assertEqual(license_info.get_summary(),
                         'License for Test Product Super Plan expired '
                         'and needs to be renewed')

    def test_get_summary_with_hard_expired_trial(self) -> None:
        """Testing LicenseInfo.get_summary with hard-expired trial license"""
        license_info = LicenseInfo(
            expires=timezone.now() - timedelta(days=10),
            grace_period_days_remaining=5,
            product_name='Test Product',
            license_id='test-license',
            licensed_to='Test User',
            is_trial=True,
            status=LicenseStatus.HARD_EXPIRED)

        self.assertEqual(license_info.get_summary(),
                         'Trial license for Test Product expired')

    def test_get_summary_with_hard_expired_trial_plan(self) -> None:
        """Testing LicenseInfo.get_summary with hard-expired trial license
        with plan
        """
        license_info = LicenseInfo(
            expires=timezone.now() - timedelta(days=10),
            grace_period_days_remaining=5,
            product_name='Test Product',
            license_id='test-license',
            licensed_to='Test User',
            plan_name='Super Plan',
            is_trial=True,
            status=LicenseStatus.HARD_EXPIRED)

        self.assertEqual(license_info.get_summary(),
                         'Trial license for Test Product Super Plan '
                         'expired')
