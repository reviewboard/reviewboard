"""Providers for managing licensing options.

Version Added:
    7.1
"""

from __future__ import annotations

from typing import (ClassVar, Generic, Optional, Sequence, TYPE_CHECKING,
                    TypeVar)

from django.utils.translation import gettext as _
from typing_extensions import NotRequired, TypedDict

from reviewboard.licensing.license import LicenseInfo

if TYPE_CHECKING:
    from django.http import HttpRequest
    from djblets.util.typing import SerializableJSONValue, StrOrPromise


_LicenseInfoT = TypeVar('_LicenseInfoT', bound=LicenseInfo)


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
    url: NotRequired[Optional[str]]


class BaseLicenseProvider(Generic[_LicenseInfoT]):
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

    def get_licenses(self) -> Sequence[_LicenseInfoT]:
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
    ) -> Optional[LicenseInfo]:
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
        license_info: _LicenseInfoT,
    ) -> Optional[str]:
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
        raise NotImplementedError

    def get_license_actions(
        self,
        *,
        license_info: _LicenseInfoT,
    ) -> Sequence[LicenseAction]:
        """Return actions to display when viewing a license.

        By default, this will include the management URL for the license,
        if provided in :py:meth:`get_manage_license_url`.

        Subclasses may override this to provide custom actions.

        Args:
            license_info (reviewboard.licensing.license.LicenseInfo):
                The license information that will be displayed.

        Returns:
            list of LicenseAction:
            The list of actions to display for the license.
        """
        manage_url: Optional[str]

        try:
            manage_url = self.get_manage_license_url(license_info=license_info)
        except NotImplementedError:
            manage_url = None

        actions: list[LicenseAction] = []

        if manage_url:
            actions.append({
                'action_id': 'manage',
                'label': _('Manage your license'),
                'url': manage_url,
            })

        return actions

    def get_license_check_data(
        self,
        *,
        license_info: _LicenseInfoT,
        request: Optional[HttpRequest] = None,
    ) -> Optional[SerializableJSONValue]:
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
            object:
            The JSON-serializable value representing license state to check.
        """
        raise NotImplementedError
