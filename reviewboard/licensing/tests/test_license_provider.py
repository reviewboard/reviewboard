"""Unit tests for reviewboard.licensing.provider.BaseLicenseProvider.

Version Added:
    7.1
"""

from __future__ import annotations

from datetime import datetime, timezone as tz
from uuid import uuid4

import kgb
from django.utils import timezone

from reviewboard.licensing.errors import LicenseActionError
from reviewboard.testing import TestCase
from reviewboard.licensing.license_checks import \
    ProcessCheckLicenseResultStatus
from reviewboard.licensing.tests.providers import (
    BasicTestsLicenseProvider,
    ExpiredTestsLicenseProvider,
)


class BaseLicenseProviderTests(kgb.SpyAgency, TestCase):
    """Unit tests for BaseLicenseProvider.

    Version Added:
        7.1
    """

    ######################
    # Instance variables #
    ######################

    #: A static timestamp for "now", to ease unit testing.
    now: datetime

    @classmethod
    def setUpClass(cls) -> None:
        """Set up state for all unit tests in the class.

        This will store a static timestamp for "now" and a list of license
        providers to register for the tests.
        """
        super().setUpClass()

        cls.now = datetime(2025, 4, 21, 0, 0, 0, tzinfo=tz.utc)

    @classmethod
    def tearDownClass(cls) -> None:
        """Tear down state for the unit tests."""
        super().tearDownClass()

        cls.now = None  # type: ignore

    def setUp(self) -> None:
        """Set up state for a unit test.

        This will register all the license providers and force the current
        timestamp for "now".
        """
        super().setUp()

        self.spy_on(timezone.now, op=kgb.SpyOpReturn(self.now))

    def test_call_action_with_invalid_action(self) -> None:
        """Testing BaseLicenseProvider.call_action with invalid action"""
        license_provider = ExpiredTestsLicenseProvider()

        license_info = license_provider.get_license_by_id('license1')
        assert license_info is not None

        message = 'Unsupported license action "xxx".'

        with self.assertRaisesMessage(LicenseActionError, message):
            license_provider.call_action(action_id='xxx',
                                         license_info=license_info)

    def test_action_license_update_check(self) -> None:
        """Testing BaseLicenseProvider action "license-update-check"
        """
        license_provider = BasicTestsLicenseProvider()

        license_info = license_provider.get_license_by_id('license1')
        assert license_info is not None

        result = license_provider.call_action(
            'license-update-check',
            license_info=license_info)

        self.assertEqual(result, {
            'canCheck': True,
            'checkStatusURL': 'https://example.com/license1/check/',
            'credentials': None,
            'data': {
                'license_id': 'license1',
                'something': 'special',
                'version': '1.0',
            },
            'headers': None,
            'sessionToken': 'abc123',
        })

    def test_action_license_update_check_not_supported(self) -> None:
        """Testing BaseLicenseProvider action "license-update-check" not
        supported
        """
        license_provider = ExpiredTestsLicenseProvider()

        license_info = license_provider.get_license_by_id('license1')
        assert license_info is not None

        result = license_provider.call_action(
            'license-update-check',
            license_info=license_info)

        self.assertEqual(result, {
            'canCheck': False,
        })

    def test_action_process_license_update_and_applied(self) -> None:
        """Testing BaseLicenseProvider action "process-license-update" and
        new license data applied
        """
        license_provider = BasicTestsLicenseProvider()

        license_info = license_provider.get_license_by_id('license2')
        assert license_info is not None

        result = license_provider.call_action(
            'process-license-update',
            action_data={
                'check_request_data': {
                    'license_id': 'license1',
                    'something': 'special',
                    'version': '1.0',
                },
                'check_response_data': {
                    'updated': True,
                    'version': '1.0',
                },
            },
            license_info=license_info)

        self.assertEqual(result, {
            'status': ProcessCheckLicenseResultStatus.APPLIED,
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
                    'expiresDate': datetime(2026, 4, 21, 0, 0, 0,
                                            tzinfo=tz.utc),
                    'expiresSoon': False,
                    'gracePeriodDaysRemaining': 0,
                    'hardExpiresDate': datetime(2026, 4, 21, 0, 0, 0,
                                                tzinfo=tz.utc),
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
                        'License for Test Product Super Mega Power Bundle '
                        'Pro Enterprise is active'
                    ),
                },
            },
        })

    def test_action_process_license_update_and_has_latest(self) -> None:
        """Testing BaseLicenseProvider action "process-license-update" and
        already has latest data
        """
        license_provider = BasicTestsLicenseProvider()

        license_info = license_provider.get_license_by_id('license2')
        assert license_info is not None

        result = license_provider.call_action(
            'process-license-update',
            action_data={
                'action_target': 'basic-tests-provider:license2',
                'check_request_data': {
                    'license_id': 'license1',
                    'something': 'special',
                    'version': '1.0',
                },
                'check_response_data': {
                    'latest': True,
                    'version': '1.0',
                },
            },
            license_info=license_info)

        self.assertEqual(result, {
            'status': ProcessCheckLicenseResultStatus.HAS_LATEST,
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
                    'expiresDate': datetime(2025, 4, 26, 0, 0, 0,
                                            tzinfo=tz.utc),
                    'expiresSoon': True,
                    'gracePeriodDaysRemaining': 0,
                    'hardExpiresDate': datetime(2025, 4, 26, 0, 0, 0,
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
                    'summary': (
                        'License for Test Product Plan 1 expires in 5 days'
                    ),
                },
            },
        })

    def test_action_process_license_update_and_error(self) -> None:
        """Testing BaseLicenseProvider action "process-license-update" and
        error
        """
        license_provider = BasicTestsLicenseProvider()

        license_info = license_provider.get_license_by_id('license2')
        assert license_info is not None

        message = (
            'Error processing license update: Invalid version from '
            'the licensing server! Oh no!'
        )

        with self.assertRaisesMessage(LicenseActionError, message):
            license_provider.call_action(
                'process-license-update',
                action_data={
                    'check_request_data': {
                        'license_id': 'license1',
                        'something': 'special',
                        'version': '1.0',
                    },
                    'check_response_data': {
                        'latest': True,
                        'version': '2.0',
                    },
                },
                license_info=license_info)

    def test_action_process_license_update_no_check_data(self) -> None:
        """Testing BaseLicenseProvider action "process-license-update" and
        missing check_request_data
        """
        trace_id = '00000000-0000-0000-0000-000000000001'
        self.spy_on(uuid4, op=kgb.SpyOpReturn(trace_id))

        license_provider = BasicTestsLicenseProvider()

        license_info = license_provider.get_license_by_id('license2')
        assert license_info is not None

        message = (
            f'Missing check_request_data value for license check. This '
            f'may be an internal error or an issue with the licensing '
            f'server. Check the Review Board server logs for more '
            f'information (error ID {trace_id}).'
        )

        with self.assertRaisesMessage(LicenseActionError, message):
            license_provider.call_action(
                'process-license-update',
                license_info=license_info)

    def test_action_process_license_update_no_response_data(self) -> None:
        """Testing BaseLicenseProvider action "process-license-update" and
        missing check_response_data
        """
        trace_id = '00000000-0000-0000-0000-000000000001'
        self.spy_on(uuid4, op=kgb.SpyOpReturn(trace_id))

        license_provider = BasicTestsLicenseProvider()

        license_info = license_provider.get_license_by_id('license2')
        assert license_info is not None

        message = (
            f'Missing check_response_data value for license check. This '
            f'may be an internal error or an issue with the licensing '
            f'server. Check the Review Board server logs for more '
            f'information (error ID {trace_id}).'
        )

        with self.assertRaisesMessage(LicenseActionError, message):
            license_provider.call_action(
                'process-license-update',
                action_data={
                    'check_request_data': '"abc123"',
                },
                license_info=license_info)

    def test_action_custom(self) -> None:
        """Testing BaseLicenseProvider custom actions"""
        license_provider = BasicTestsLicenseProvider()

        license_info = license_provider.get_license_by_id('license1')
        assert license_info is not None

        result = license_provider.call_action(
            'test',
            action_data={
                'data1': 'value1',
                'data2': 123,
            },
            license_info=license_info)

        self.assertEqual(
            result,
            {
                'ok': 'yep',
                'got_action_data': {
                    'data1': 'value1',
                    'data2': 123,
                },
            })
