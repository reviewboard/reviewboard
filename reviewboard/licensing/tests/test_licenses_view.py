"""Unit tests for reviewboard.licensing.views.LicensesView.

Version Added:
    7.1
"""

from __future__ import annotations

import json
from datetime import datetime, timezone as tz
from uuid import uuid4

import kgb
from django.urls import reverse
from django.utils import timezone
from djblets.features.testing import override_feature_check

from reviewboard.licensing.features import licensing_feature
from reviewboard.licensing.provider import BaseLicenseProvider
from reviewboard.licensing.registry import license_provider_registry
from reviewboard.licensing.tests.providers import (
    BasicTestsLicenseProvider,
    ExpiredTestsLicenseProvider,
)
from reviewboard.testing import TestCase


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
            BasicTestsLicenseProvider(),
            ExpiredTestsLicenseProvider(),
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

    @override_feature_check(licensing_feature, True)
    def test_get_as_anonymous(self) -> None:
        """Testing LicenseView.get as anonymous"""
        client = self.client
        response = client.get(reverse('admin-licenses'))

        self.assertEqual(response.status_code, 302)

    @override_feature_check(licensing_feature, True)
    def test_get_as_non_admin(self) -> None:
        """Testing LicenseView.get as non-admin user"""
        client = self.client
        self.assertTrue(
            self.client.login(username='dopey', password='dopey'))

        response = client.get(reverse('admin-licenses'))

        self.assertEqual(response.status_code, 302)

    @override_feature_check(licensing_feature, True)
    def test_get_as_admin(self) -> None:
        """Testing LicenseView.get as admin"""
        client = self.client
        self.assertTrue(client.login(username='admin', password='admin'))

        response = client.get(reverse('admin-licenses'))

        self.assertEqual(response.status_code, 200)

        self.assertEqual(response.context['license_entries'], [
            {
                'license_infos': [
                    {
                        'attrs': {
                            'actionTarget': 'basic-tests-provider:license1',
                            'actions': [
                                {
                                    'actionID': 'test',
                                    'label': 'Test',
                                    'url': 'https://example.com/license1/',
                                },
                            ],
                            'canUploadLicense': False,
                            'expiresDate': datetime(2025, 7, 30, 0, 0,
                                                    tzinfo=tz.utc),
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
                    },
                    {
                        'attrs': {
                            'actionTarget': 'basic-tests-provider:license2',
                            'actions': [
                                {
                                    'actionID': 'test',
                                    'label': 'Test',
                                    'url': 'https://example.com/license2/',
                                },
                            ],
                            'canUploadLicense': False,
                            'expiresDate': datetime(2025, 4, 26, 0, 0,
                                                    tzinfo=tz.utc),
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
                    },
                ],
                'model': 'RB.License',
                'view': 'RB.LicenseView',
            },
            {
                'license_infos': [
                    {
                        'attrs': {
                            'actionTarget': 'expired-tests-provider:license1',
                            'actions': [],
                            'canUploadLicense': False,
                            'expiresDate': datetime(2025, 3, 2, 0, 0,
                                                    tzinfo=tz.utc),
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
                            'summary': (
                                'Expired trial license for Test Product'
                            ),
                        },
                    },
                    {
                        'attrs': {
                            'actionTarget': 'expired-tests-provider:license2',
                            'actions': [],
                            'canUploadLicense': False,
                            'expiresDate': datetime(2025, 4, 19, 0, 0,
                                                    tzinfo=tz.utc),
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
                                'Your grace period is now active. Unless '
                                'renewed, Test Product will be disabled <time '
                                'class="timesince" dateTime="2025-04-19 '
                                '00:00:00+00:00"/>.'
                            ),
                            'planID': None,
                            'planName': None,
                            'productName': 'Test Product',
                            'status': 'expired-grace-period',
                            'summary': 'Expired license for Test Product',
                        },
                    },
                ],
                'model': 'RB.License',
                'view': 'RB.LicenseView',
            },
        ])

    @override_feature_check(licensing_feature, True)
    def test_post_as_anonymous(self) -> None:
        """Testing LicenseView.post as anonymous"""
        client = self.client
        response = client.post(reverse('admin-licenses'))

        self.assertEqual(response.status_code, 302)

    @override_feature_check(licensing_feature, True)
    def test_post_as_non_admin(self) -> None:
        """Testing LicenseView.post as non-admin user"""
        client = self.client
        self.assertTrue(self.client.login(username='dopey', password='dopey'))
        response = client.post(reverse('admin-licenses'))

        self.assertEqual(response.status_code, 302)

    @override_feature_check(licensing_feature, True)
    def test_post_with_no_action(self) -> None:
        """Testing LicenseView.post as admin with no action"""
        client = self.client
        self.assertTrue(client.login(username='admin', password='admin'))

        response = client.post(reverse('admin-licenses'))

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {
            'error': 'Missing action data.',
        })

    @override_feature_check(licensing_feature, True)
    def test_post_with_no_action_target(self) -> None:
        """Testing LicenseView.post as admin with no action_target"""
        client = self.client
        self.assertTrue(client.login(username='admin', password='admin'))

        response = client.post(reverse('admin-licenses'), {
            'action': 'xxx',
        })

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {
            'error': 'Missing action target.',
        })

    @override_feature_check(licensing_feature, True)
    def test_post_with_invalid_action_target(self) -> None:
        """Testing LicenseView.post as admin with invalid action_target"""
        client = self.client
        self.assertTrue(client.login(username='admin', password='admin'))

        response = client.post(reverse('admin-licenses'), {
            'action': 'xxx',
            'action_target': 'xxx',
        })

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {
            'error': 'Invalid action target.',
        })

    @override_feature_check(licensing_feature, True)
    def test_post_with_license_not_found(self) -> None:
        """Testing LicenseView.post as admin with license not found"""
        client = self.client
        self.assertTrue(client.login(username='admin', password='admin'))

        response = client.post(reverse('admin-licenses'), {
            'action': 'xxx',
            'action_target': 'expired-tests-provider:xxx',
        })

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {
            'error': 'The license entry could not be found.',
        })

    @override_feature_check(licensing_feature, True)
    def test_post_with_invalid_action(self) -> None:
        """Testing LicenseView.post as admin with invalid action"""
        client = self.client
        self.assertTrue(client.login(username='admin', password='admin'))

        response = client.post(reverse('admin-licenses'), {
            'action': 'xxx',
            'action_target': 'expired-tests-provider:license1',
        })

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {
            'error': 'Unsupported license action "xxx".',
        })

    @override_feature_check(licensing_feature, True)
    def test_post_with_license_update_check(self) -> None:
        """Testing LicenseView.post as admin with action="license-update-check"
        """
        client = self.client
        self.assertTrue(client.login(username='admin', password='admin'))

        response = client.post(reverse('admin-licenses'), {
            'action': 'license-update-check',
            'action_target': 'basic-tests-provider:license1',
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            'canCheck': True,
            'checkStatusURL': 'https://example.com/license1/check/',
            'credentials': None,
            'data': {
                'license_id': 'license1',
                'something': 'special',
                'version': '1.0',
            },
            'headers': None,
        })

    @override_feature_check(licensing_feature, True)
    def test_post_with_license_update_check_not_supported(self) -> None:
        """Testing LicenseView.post as admin with action="license-update-check"
        not supported
        """
        client = self.client
        self.assertTrue(client.login(username='admin', password='admin'))

        response = client.post(reverse('admin-licenses'), {
            'action': 'license-update-check',
            'action_target': 'expired-tests-provider:license1',
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            'canCheck': False,
        })

    @override_feature_check(licensing_feature, True)
    def test_post_with_process_license_update_and_applied(self) -> None:
        """Testing LicenseView.post as admin with
        action="process-license-update" and new license data applied
        """
        trace_id = '00000000-0000-0000-0000-000000000001'
        self.spy_on(uuid4, op=kgb.SpyOpReturn(trace_id))

        client = self.client
        self.assertTrue(client.login(username='admin', password='admin'))

        response = client.post(reverse('admin-licenses'), {
            'action': 'process-license-update',
            'action_target': 'basic-tests-provider:license2',
            'check_request_data': json.dumps({
                'license_id': 'license1',
                'something': 'special',
                'version': '1.0',
            }),
            'check_response_data': json.dumps({
                'updated': True,
                'version': '1.0',
            }),
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            'status': 'applied',
            'license_infos': {
                'license1': {
                    'actionTarget': 'basic-tests-provider:license2',
                    'actions': [
                        {
                            'actionID': 'test',
                            'label': 'Test',
                            'url': 'https://example.com/license2/',
                        },
                    ],
                    'canUploadLicense': False,
                    'expiresDate': '2026-04-21T00:00:00Z',
                    'expiresSoon': False,
                    'gracePeriodDaysRemaining': 0,
                    'hardExpiresDate': '2026-04-21T00:00:00Z',
                    'isTrial': False,
                    'licenseID': 'license2',
                    'licensedTo': 'Test User',
                    'lineItems': [],
                    'manageURL': None,
                    'noticeHTML': '',
                    'planID': 'smpbpe1',
                    'planName': 'Super Mega Power Bundle Pro Enterprise',
                    'productName': 'Test Product',
                    'status': 'licensed',
                    'summary': (
                        'License for Test Product (Super Mega Power Bundle '
                        'Pro Enterprise)'
                    ),
                },
            },
        })

    @override_feature_check(licensing_feature, True)
    def test_post_with_process_license_update_and_has_latest(self) -> None:
        """Testing LicenseView.post as admin with
        action="process-license-update" and already has latest data
        """
        trace_id = '00000000-0000-0000-0000-000000000001'
        self.spy_on(uuid4, op=kgb.SpyOpReturn(trace_id))

        client = self.client
        self.assertTrue(client.login(username='admin', password='admin'))

        response = client.post(reverse('admin-licenses'), {
            'action': 'process-license-update',
            'action_target': 'basic-tests-provider:license2',
            'check_request_data': json.dumps({
                'license_id': 'license1',
                'something': 'special',
                'version': '1.0',
            }),
            'check_response_data': json.dumps({
                'latest': True,
                'version': '1.0',
            }),
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            'status': 'has-latest',
            'license_infos': {
                'license1': {
                    'actionTarget': 'basic-tests-provider:license2',
                    'actions': [
                        {
                            'actionID': 'test',
                            'label': 'Test',
                            'url': 'https://example.com/license2/',
                        },
                    ],
                    'canUploadLicense': False,
                    'expiresDate': '2025-04-26T00:00:00Z',
                    'expiresSoon': True,
                    'gracePeriodDaysRemaining': 0,
                    'hardExpiresDate': '2025-04-26T00:00:00Z',
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
            },
        })

    @override_feature_check(licensing_feature, True)
    def test_post_with_process_license_update_and_error(self) -> None:
        """Testing LicenseView.post as admin with
        action="process-license-update" and error
        """
        trace_id = '00000000-0000-0000-0000-000000000001'
        self.spy_on(uuid4, op=kgb.SpyOpReturn(trace_id))

        client = self.client
        self.assertTrue(client.login(username='admin', password='admin'))

        response = client.post(reverse('admin-licenses'), {
            'action': 'process-license-update',
            'action_target': 'basic-tests-provider:license2',
            'check_request_data': json.dumps({
                'license_id': 'license1',
                'something': 'special',
                'version': '1.0',
            }),
            'check_response_data': json.dumps({
                'latest': True,
                'version': '2.0',
            }),
        })

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {
            'error': (
                'Error processing license update: Invalid version from '
                'the licensing server! Oh no!'
            ),
        })

    @override_feature_check(licensing_feature, True)
    def test_post_with_process_license_update_no_check_data(self) -> None:
        """Testing LicenseView.post as admin with
        action="process-license-update" and missing check_request_data
        """
        trace_id = '00000000-0000-0000-0000-000000000001'
        self.spy_on(uuid4, op=kgb.SpyOpReturn(trace_id))

        client = self.client
        self.assertTrue(client.login(username='admin', password='admin'))

        response = client.post(reverse('admin-licenses'), {
            'action': 'process-license-update',
            'action_target': 'basic-tests-provider:license2',
        })

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {
            'error': (
                f'Missing check_request_data value for license check. This '
                f'may be an internal error or an issue with the licensing '
                f'server. Check the Review Board server logs for more '
                f'information (error ID {trace_id}).'
            ),
        })

    @override_feature_check(licensing_feature, True)
    def test_post_with_process_license_update_no_response_data(self) -> None:
        """Testing LicenseView.post as admin with
        action="process-license-update" and missing check_response_data
        """
        trace_id = '00000000-0000-0000-0000-000000000001'
        self.spy_on(uuid4, op=kgb.SpyOpReturn(trace_id))

        client = self.client
        self.assertTrue(client.login(username='admin', password='admin'))

        response = client.post(reverse('admin-licenses'), {
            'action': 'process-license-update',
            'action_target': 'basic-tests-provider:license2',
            'check_request_data': '"abc123"',
        })

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {
            'error': (
                f'Missing check_response_data value for license check. This '
                f'may be an internal error or an issue with the licensing '
                f'server. Check the Review Board server logs for more '
                f'information (error ID {trace_id}).'
            ),
        })

    @override_feature_check(licensing_feature, True)
    def test_post_with_process_license_update_invalid_check_data(self) -> None:
        """Testing LicenseView.post as admin with
        action="process-license-update" and non-JSON check_response_data
        """
        trace_id = '00000000-0000-0000-0000-000000000001'
        self.spy_on(uuid4, op=kgb.SpyOpReturn(trace_id))

        client = self.client
        self.assertTrue(client.login(username='admin', password='admin'))

        response = client.post(reverse('admin-licenses'), {
            'action': 'process-license-update',
            'action_target': 'basic-tests-provider:license2',
            'check_request_data': 'xxx',
            'check_response_data': '"def456"',
        })

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {
            'error': (
                f'Invalid check_request_data value for license check. This '
                f'may be an internal error or an issue with the licensing '
                f'server. Check the Review Board server logs for more '
                f'information (error ID {trace_id}).'
            ),
        })

    @override_feature_check(licensing_feature, True)
    def test_post_with_process_license_update_invalid_response_data(
        self,
    ) -> None:
        """Testing LicenseView.post as admin with
        action="process-license-update" and non-JSON check_response_data
        """
        trace_id = '00000000-0000-0000-0000-000000000001'
        self.spy_on(uuid4, op=kgb.SpyOpReturn(trace_id))

        client = self.client
        self.assertTrue(client.login(username='admin', password='admin'))

        response = client.post(reverse('admin-licenses'), {
            'action': 'process-license-update',
            'action_target': 'basic-tests-provider:license2',
            'check_request_data': '"abc123"',
            'check_response_data': 'xxx',
        })

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {
            'error': (
                f'Invalid check_response_data value for license check. This '
                f'may be an internal error or an issue with the licensing '
                f'server. Check the Review Board server logs for more '
                f'information (error ID {trace_id}).'
            ),
        })
