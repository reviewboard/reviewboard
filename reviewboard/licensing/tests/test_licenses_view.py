"""Unit tests for reviewboard.licensing.views.LicensesView.

Version Added:
    7.1
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone as tz
from typing import TYPE_CHECKING

import kgb
from django.urls import reverse
from django.utils import timezone

from reviewboard.licensing.license import LicenseInfo, LicenseStatus
from reviewboard.licensing.provider import BaseLicenseProvider
from reviewboard.licensing.registry import (LicenseProviderRegistry,
                                            license_provider_registry)
from reviewboard.testing import TestCase

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from django.http import HttpRequest

    from reviewboard.licensing.provider import LicenseAction


class _MyLicenseProvider1(BaseLicenseProvider):
    license_provider_id = 'my-provider-1'

    def get_license_actions(
        self,
        *,
        license_info: LicenseInfo,
        request: (HttpRequest | None) = None,
    ) -> Sequence[LicenseAction]:
        return [{
            'action_id': 'test',
            'label': 'Test',
            'url': f'https://example.com/{license_info.license_id}/',
        }]

    def get_licenses(self) -> Sequence[LicenseInfo]:
        license1 = self.get_license_by_id('license1')
        license2 = self.get_license_by_id('license2')

        assert license1
        assert license2

        return [license1, license2]

    def get_license_by_id(
        self,
        license_id: str,
    ) -> LicenseInfo | None:
        if license_id == 'license1':
            return LicenseInfo(
                expires=timezone.now() + timedelta(days=100),
                license_id=license_id,
                licensed_to='Test User',
                line_items=[
                    'Line 1',
                    'Line 2',
                ],
                product_name='Test Product',
                status=LicenseStatus.UNLICENSED)
        elif license_id == 'license2':
            return LicenseInfo(
                expires=timezone.now() + timedelta(days=5),
                license_id=license_id,
                licensed_to='Test User',
                plan_id='plan1',
                plan_name='Plan 1',
                product_name='Test Product',
                status=LicenseStatus.LICENSED)
        else:
            return None

    def get_manage_license_url(
        self,
        *,
        license_info: LicenseInfo,
    ) -> str | None:
        if license_info.license_id == 'license1':
            return f'https://example.com/{license_info.license_id}/'

        return None


class _MyLicenseProvider2(BaseLicenseProvider):
    license_provider_id = 'my-provider-2'

    def get_licenses(self) -> Sequence[LicenseInfo]:
        license1 = self.get_license_by_id('license1')
        license2 = self.get_license_by_id('license2')

        assert license1
        assert license2

        return [license1, license2]

    def get_license_by_id(
        self,
        license_id: str,
    ) -> LicenseInfo | None:
        if license_id == 'license1':
            return LicenseInfo(
                expires=timezone.now() - timedelta(days=50),
                is_trial=True,
                license_id=license_id,
                licensed_to='Test User',
                product_name='Test Product',
                status=LicenseStatus.HARD_EXPIRED)
        elif license_id == 'license2':
            return LicenseInfo(
                expires=timezone.now() - timedelta(days=2),
                license_id=license_id,
                licensed_to='Test User',
                product_name='Test Product',
                status=LicenseStatus.EXPIRED_GRACE_PERIOD)
        else:
            return None


class _MyLicenseProviderRegistry(LicenseProviderRegistry):
    def get_defaults(self) -> Iterable[BaseLicenseProvider]:
        yield _MyLicenseProvider1()
        yield _MyLicenseProvider2()


class LicenseViewTests(kgb.SpyAgency, TestCase):
    """Unit tests for LicenseView.

    Version Added:
        7.1
    """

    fixtures = ['test_users']

    ######################
    # Instance variables #
    ######################

    #: A static timestamp for "now", to ease unit testing.
    now: datetime

    #: The list of license providers registered for tests.
    _license_providers: list[BaseLicenseProvider]

    @classmethod
    def setUpClass(cls) -> None:
        """Set up state for all unit tests in the class.

        This will store a static timestamp for "now" and a list of license
        providers to register for the tests.
        """
        super().setUpClass()

        license_providers = [
            _MyLicenseProvider1(),
            _MyLicenseProvider2(),
        ]

        cls._license_providers = license_providers
        cls.now = datetime(2025, 4, 21, 0, 0, 0, tzinfo=tz.utc)

    @classmethod
    def tearDownClass(cls) -> None:
        """Tear down state for the unit tests."""
        super().tearDownClass()

        cls._license_providers = []
        cls.now = None  # type: ignore

    def setUp(self) -> None:
        """Set up state for a unit test.

        This will register all the license providers and force the current
        timestamp for "now".
        """
        super().setUp()

        for license_provider in self._license_providers:
            license_provider_registry.register(license_provider)

        self.spy_on(timezone.now, op=kgb.SpyOpReturn(self.now))

    def tearDown(self) -> None:
        """Tear down state for the test.

        This will unregister all the license providers.
        """
        super().tearDown()

        for license_provider in self._license_providers:
            license_provider_registry.unregister(license_provider)

    def test_get_as_anonymous(self) -> None:
        """Testing LicenseView.get as anonymous"""
        client = self.client
        response = client.get(reverse('admin-licenses'))

        self.assertEqual(response.status_code, 302)

    def test_get_as_non_admin(self) -> None:
        """Testing LicenseView.get as non-admin user"""
        client = self.client
        self.assertTrue(self.client.login(username='dopey', password='dopey'))
        response = client.get(reverse('admin-licenses'))

        self.assertEqual(response.status_code, 302)

    def test_get_as_admin(self) -> None:
        """Testing LicenseView.get as admin"""
        client = self.client
        self.assertTrue(client.login(username='admin', password='admin'))

        response = client.get(reverse('admin-licenses'))

        self.assertEqual(response.status_code, 200)

        self.assertEqual(response.context['license_entries'], [
            {
                'attrs': {
                    'actionTarget': 'my-provider-1:license1',
                    'actions': [
                        {
                            'actionID': 'test',
                            'label': 'Test',
                            'url': 'https://example.com/license1/',
                        },
                    ],
                    'canUploadLicense': False,
                    'expiresDate': datetime(2025, 7, 30, 0, 0, tzinfo=tz.utc),
                    'expiresSoon': False,
                    'gracePeriodDaysRemaining': 0,
                    'hardExpiresDate': datetime(2025, 7, 30, 0, 0,
                                                tzinfo=tz.utc),
                    'isTrial': False,
                    'licenseID': 'license1',
                    'licensedTo': 'Test User',
                    'lineItems': [
                        'Line 1',
                        'Line 2',
                    ],
                    'manageURL': 'https://example.com/license1/',
                    'noticeHTML': '',
                    'planID': None,
                    'planName': None,
                    'productName': 'Test Product',
                    'status': 'unlicensed',
                    'summary': 'Test Product is not licensed!',
                },
                'model': 'RB.License',
                'view': 'RB.LicenseView',
            },
            {
                'attrs': {
                    'actionTarget': 'my-provider-1:license2',
                    'actions': [
                        {
                            'actionID': 'test',
                            'label': 'Test',
                            'url': 'https://example.com/license2/',
                        },
                    ],
                    'canUploadLicense': False,
                    'expiresDate': datetime(2025, 4, 26, 0, 0, tzinfo=tz.utc),
                    'expiresSoon': True,
                    'gracePeriodDaysRemaining': 0,
                    'hardExpiresDate': datetime(2025, 4, 26, 0, 0,
                                                tzinfo=tz.utc),
                    'isTrial': False,
                    'licenseID': 'license2',
                    'licensedTo': 'Test User',
                    'lineItems': [],
                    'manageURL': None,
                    'noticeHTML': '',
                    'planID': 'plan1',
                    'planName': 'Plan 1',
                    'productName': 'Test Product',
                    'status': 'licensed',
                    'summary': 'License for Test Product (Plan 1)',
                },
                'model': 'RB.License',
                'view': 'RB.LicenseView',
            },
            {
                'attrs': {
                    'actionTarget': 'my-provider-2:license1',
                    'actions': [],
                    'canUploadLicense': False,
                    'expiresDate': datetime(2025, 3, 2, 0, 0, tzinfo=tz.utc),
                    'expiresSoon': False,
                    'gracePeriodDaysRemaining': 0,
                    'hardExpiresDate': datetime(2025, 3, 2, 0, 0,
                                                tzinfo=tz.utc),
                    'isTrial': True,
                    'licenseID': 'license1',
                    'licensedTo': 'Test User',
                    'lineItems': [],
                    'manageURL': None,
                    'noticeHTML': '',
                    'planID': None,
                    'planName': None,
                    'productName': 'Test Product',
                    'status': 'hard-expired',
                    'summary': 'Expired trial license for Test Product',
                },
                'model': 'RB.License',
                'view': 'RB.LicenseView',
            },
            {
                'attrs': {
                    'actionTarget': 'my-provider-2:license2',
                    'actions': [],
                    'canUploadLicense': False,
                    'expiresDate': datetime(2025, 4, 19, 0, 0, tzinfo=tz.utc),
                    'expiresSoon': False,
                    'gracePeriodDaysRemaining': 0,
                    'hardExpiresDate': datetime(2025, 4, 19, 0, 0,
                                                tzinfo=tz.utc),
                    'isTrial': False,
                    'licenseID': 'license2',
                    'licensedTo': 'Test User',
                    'lineItems': [],
                    'manageURL': None,
                    'noticeHTML': (
                        'Your grace period is now active. Unless renewed, '
                        'Test Product will be disabled <time '
                        'class="timesince" dateTime="2025-04-19 '
                        '00:00:00+00:00"/>.'
                    ),
                    'planID': None,
                    'planName': None,
                    'productName': 'Test Product',
                    'status': 'expired-grace-period',
                    'summary': 'Expired license for Test Product',
                },
                'model': 'RB.License',
                'view': 'RB.LicenseView',
            },
        ])
