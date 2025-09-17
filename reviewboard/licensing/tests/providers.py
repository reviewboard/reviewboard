"""License providers common to unit tests.

Version Added:
    7.1
"""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

from django.utils import timezone

from reviewboard.licensing.errors import LicenseActionError
from reviewboard.licensing.license import LicenseInfo, LicenseStatus
from reviewboard.licensing.license_checks import (
    ProcessCheckLicenseResult,
    ProcessCheckLicenseResultStatus,
)
from reviewboard.licensing.provider import BaseLicenseProvider

if TYPE_CHECKING:
    from collections.abc import Sequence

    from django.http import HttpRequest
    from djblets.util.typing import JSONValue, SerializableJSONDict

    from reviewboard.licensing.license_checks import RequestCheckLicenseResult
    from reviewboard.licensing.provider import (LicenseAction,
                                                LicenseActionData)


class BasicTestsLicenseProvider(BaseLicenseProvider):
    """Sample license provider used for unit tests.

    This provides the following licenses:

    * ``license1``

      Unlicensed, expiring in 100 days.

      Includes line items.

    * ``license2``

      Licensed, expiring in 5 days.

      Includes a plan ID and name.

    This also provides a custom ``test`` action and license updating.

    Version Added:
        7.1
    """

    license_provider_id = 'basic-tests-provider'

    custom_actions = {
        'test',
    }

    def get_license_actions(
        self,
        *,
        license_info: LicenseInfo,
        request: (HttpRequest | None) = None,
    ) -> Sequence[LicenseAction]:
        """Return actions to display when viewing a license.

        This will return a custom "test" action.

        Args:
            license_info (reviewboard.licensing.license.LicenseInfo):
                The license information that will be displayed.

            request (django.http.HttpRequest, optional):
                The HTTP request from the client.

        Returns:
            list of LicenseAction:
            The list of actions to display for the license.
        """
        return [{
            'action_id': 'test',
            'label': 'Test',
            'url': f'https://example.com/{license_info.license_id}/',
        }]

    def get_licenses(self) -> Sequence[LicenseInfo]:
        """Return the list of available licenses.

        Returns:
            list of reviewboard.licensing.license.LicenseInfo:
            The list of licenses provided.
        """
        license1 = self.get_license_by_id('license1')
        license2 = self.get_license_by_id('license2')

        assert license1
        assert license2

        return [license1, license2]

    def get_license_by_id(
        self,
        license_id: str,
    ) -> LicenseInfo | None:
        """Return a license with the given provider-unique ID.

        Args:
            license_id (str):
                The provider-unique ID for the license.

        Returns:
            reviewboard.licensing.license.LicenseInfo:
            The license information, or ``None`` if not found.
        """
        if license_id == 'license1':
            return LicenseInfo(
                expires=timezone.now() + timedelta(days=100),
                license_id=license_id,
                licensed_to='Test User',
                line_items=[
                    {
                        'content': 'Line 1',
                        'icon': 'ink-i-info',
                    },
                    {
                        'content': '<strong>Line 2</strong>',
                        'content_is_html': True,
                    },
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
        """Return the URL for managing licenses online.

        Args:
            license_info (reviewboard.licensing.license.LicenseInfo):
                The license information to link to in the portal.

        Returns:
            str:
            The URL to the license portal, or ``None`` if one is not
            available.
        """
        if license_info.license_id == 'license1':
            return f'https://example.com/{license_info.license_id}/'

        return None

    def get_check_license_request(
        self,
        *,
        action_data: LicenseActionData,
        license_info: LicenseInfo,
        request: (HttpRequest | None) = None,
    ) -> RequestCheckLicenseResult | None:
        """Return data used to check a license for validity.

        Args:
            action_data (dict):
                Data provided in the request to the action.

                This will correspond to HTTP POST data if processing via an
                HTTP request from the client.

            license_info (reviewboard.licensing.license.LicenseInfo):
                The license information that will be checked.

            request (django.http.HttpRequest, optional):
                The HTTP request from the client, if any.

        Returns:
            reviewboard.licensing.license_checks.RequestCheckLicenseResult:
            The state used to control the license check, or ``None`` if checks
            are not supported.

        Raises:
            reviewboard.licensing.errors.LicenseActionError:
                There was an error generating data for this request.
        """
        return {
            'data': {
                'license_id': license_info.license_id,
                'something': 'special',
                'version': '1.0',
            },
            'url': f'https://example.com/{license_info.license_id}/check/'
        }

    def process_check_license_result(
        self,
        *,
        action_data: LicenseActionData,
        license_info: LicenseInfo,
        check_request_data: JSONValue,
        check_response_data: JSONValue,
        request: (HttpRequest | None) = None,
    ) -> ProcessCheckLicenseResult:
        """Process the result of a license check.

        Args:
            action_data (dict):
                Data provided in the request to the action.

                This will correspond to HTTP POST data if processing via an
                HTTP request from the client.

            license_info (reviewboard.licensing.license.LicenseInfo):
                The license information to convert to model data.

            check_request_data (djblets.util.typing.JSONValue):
                The original request data sent to the license check.

            check_response_data (djblets.util.typing.JSONValue):
                The response data from the license check.

            request (django.http.HttpRequest, optional):
                The HTTP request from the client.

        Returns:
            reviewboard.licensing.license_checks.ProcessCheckLicenseResult:
            The processed result of the license check.

        Raises:
            NotImplementedError:
                This method must be implemented by subclasses.

            reviewboard.licensing.errors.LicenseActionError:
                There was an error processing license data, or the license
                data was not valid for the product.
        """
        assert isinstance(check_response_data, dict)

        if check_response_data.get('version') != '1.0':
            raise LicenseActionError(
                'Invalid version from the licensing server! Oh no!'
            )

        status: ProcessCheckLicenseResultStatus

        if check_response_data.get('updated'):
            status = ProcessCheckLicenseResultStatus.APPLIED
            license_info.expires = timezone.now() + timedelta(days=365)
            license_info.plan_id = 'smpbpe1'
            license_info.plan_name = 'Super Mega Power Bundle Pro Enterprise'
        elif check_response_data.get('latest'):
            status = ProcessCheckLicenseResultStatus.HAS_LATEST
        else:
            status = ProcessCheckLicenseResultStatus.ERROR_APPLYING

        return {
            'license_infos': {
                'license1': self.get_js_license_model_data(
                    license_info=license_info),
            },
            'status': status,
        }

    def handle_test_action(
        self,
        *,
        action_data: LicenseActionData,
        license_info: LicenseInfo,
        request: HttpRequest | None,
    ) -> SerializableJSONDict:
        """Handle a "test" action.

        This will just send a sample payload back to the caller.

        Args:
            action_data (dict):
                Data provided in the request to the action.

            license_info (reviewboard.licensing.license.LicenseInfo):
                Information on the license to check for updates.

            request (django.http.HttpRequest, optional):
                The HTTP request from the client.

        Returns:
            dict:
            The JSON-serializable dictionary of results to send back to the
            client.

        Raises:
            reviewboard.licensing.errors.LicenseActionError:
                An error with the data or with invoking the upload in the
                License Provider. This will result in a suitable error
                message for the client.
        """
        return {
            'got_action_data': action_data,
            'ok': 'yep',
        }


class ExpiredTestsLicenseProvider(BaseLicenseProvider):
    """Sample license provider used for expiration unit tests.

    This provides the following licenses:

    * ``license1``

      Hard-expired 50 days ago.

    * ``license2``

      Expired, in grace period as of 2 days ago.

    Version Added:
        7.1
    """

    license_provider_id = 'expired-tests-provider'

    def get_licenses(self) -> Sequence[LicenseInfo]:
        """Return the list of available licenses.

        Returns:
            list of reviewboard.licensing.license.LicenseInfo:
            The list of licenses provided.
        """
        license1 = self.get_license_by_id('license1')
        license2 = self.get_license_by_id('license2')

        assert license1
        assert license2

        return [license1, license2]

    def get_license_by_id(
        self,
        license_id: str,
    ) -> LicenseInfo | None:
        """Return a license with the given provider-unique ID.

        Args:
            license_id (str):
                The provider-unique ID for the license.

        Returns:
            reviewboard.licensing.license.LicenseInfo:
            The license information, or ``None`` if not found.
        """
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
                grace_period_days_remaining=3,
                license_id=license_id,
                licensed_to='Test User',
                product_name='Test Product',
                status=LicenseStatus.EXPIRED_GRACE_PERIOD)
        else:
            return None
