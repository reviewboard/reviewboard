"""Providers for managing licensing options.

Version Added:
    7.1
"""

from __future__ import annotations

from typing import Generic, TYPE_CHECKING, TypeVar

from typing_extensions import NotRequired, TypedDict

from reviewboard.licensing.license import LicenseInfo

if TYPE_CHECKING:
    from typing import ClassVar, Sequence

    from django.http import HttpRequest
    from djblets.util.typing import JSONValue, StrOrPromise

    from reviewboard.licensing.license_checks import (
        RequestCheckLicenseResult,
        ProcessCheckLicenseResult,
    )


#: A type variable for license information classes.
#:
#: Version Added:
#:    7.1
_TLicenseInfo = TypeVar('_TLicenseInfo', bound=LicenseInfo)


class LicenseAction(TypedDict):
    """An action that can be performed on a license.

    These will be displayed in the UI when displaying license information.

    Version Added:
        7.1
    """

    #: The provider-unique ID of the action.
    action_id: str

    #: The localized label for the action.
    label: StrOrPromise

    #: The URL to navigate to when clicking the action.
    #:
    #: If omitted or ``None``, it's up to the license implementation to
    #: provide JavaScript management for the action.
    url: NotRequired[str | None]


class BaseLicenseProvider(Generic[_TLicenseInfo]):
    """Base class for a provider for managing licenses.

    License providers make internal licensing information available to
    Review Board, to simplify and unify license management for multiple
    add-ons in one place.

    Version Added:
        7.1
    """

    #: The unique ID of the license provider.
    license_provider_id: ClassVar[str]

    #: The name of the JavaScript model for the license provider front-end.
    js_model_name: ClassVar[str]

    def get_licenses(self) -> Sequence[_TLicenseInfo]:
        """Return the list of available licenses.

        This may include active licenses, expired licenses, and trial
        licenses.

        Returns:
            list of reviewboard.licensing.license.LicenseInfo:
            The list of licenses provided.
        """
        raise NotImplementedError

    def get_license_by_id(
        self,
        license_id: str,
    ) -> LicenseInfo | None:
        """Return a license with the given provider-unique ID.

        This may return an active license, expired license, or trial license.

        Args:
            license_id (str):
                The provider-unique ID for the license.

        Returns:
            reviewboard.licensing.license.LicenseInfo:
            The license information, or ``None`` if not found.
        """
        raise NotImplementedError

    def get_manage_license_url(
        self,
        *,
        license_info: _TLicenseInfo,
    ) -> str | None:
        """Return the URL for managing licenses online.

        This is used to link to an outside license management portal for a
        given license.

        Args:
            license_info (reviewboard.licensing.license.LicenseInfo):
                The license information to link to in the portal.

        Returns:
            str:
            The URL to the license portal, or ``None`` if one is not
            available.
        """
        return None

    def get_license_actions(
        self,
        *,
        license_info: _TLicenseInfo,
        request: (HttpRequest | None) = None,
    ) -> Sequence[LicenseAction]:
        """Return actions to display when viewing a license.

        By default, this will be empty, though the UI may include built-in
        actions based on the license's information.

        Subclasses may override this to provide custom actions.

        Args:
            license_info (reviewboard.licensing.license.LicenseInfo):
                The license information that will be displayed.

            request (django.http.HttpRequest, optional):
                The HTTP request from the client.

        Returns:
            list of LicenseAction:
            The list of actions to display for the license.
        """
        return []

    def get_check_license_request(
        self,
        *,
        license_info: _TLicenseInfo,
        request: (HttpRequest | None) = None,
    ) -> RequestCheckLicenseResult | None:
        """Return data used to check a license for validity.

        This can be any JSON data that the license provider may want to
        send to a license portal in order to check if a license is still
        valid or if there's a newer license available.

        Args:
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
        return None

    def process_check_license_result(
        self,
        *,
        license_info: _TLicenseInfo,
        check_request_data: JSONValue,
        check_response_data: JSONValue,
        request: (HttpRequest | None) = None,
    ) -> ProcessCheckLicenseResult:
        """Process the result of a license check.

        This will take the response from a license check and process it. This
        may involve applying and saving the new license, or updating related
        state.

        The result indicates if the license is already up-to-date,
        newly-applied, or hit an error. It may also return new license
        attributes.

        Args:
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
        raise NotImplementedError

    def set_license_data(
        self,
        *,
        license_info: _TLicenseInfo,
        license_data: bytes,
        request: (HttpRequest | None) = None,
    ) -> None:
        """Manually set new license data.

        This is used to allow a user to upload a new license directly,
        if supported by the license provider.

        Subclasses that override this must validate the license and ensure
        it can be set.

        Args:
            license_info (reviewboard.licensing.license.LicenseInfo):
                The license information to convert to model data.

            license_data (bytes):
                The license data to set.

            request (django.http.HttpRequest, optional):
                The HTTP request from the client.

        Raises:
            reviewboard.licensing.errors.LicenseActionError:
                There was an error setting license data, or the license
                data was not valid for the product.
        """
        raise NotImplementedError
