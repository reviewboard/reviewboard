"""Providers for managing licensing options.

Version Added:
    7.1
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Final, Generic, TYPE_CHECKING, cast
from uuid import uuid4

from django.utils.html import format_html
from django.utils.translation import gettext as _
from typelets.django.json import SerializableDjangoJSONDict
from typing_extensions import TypeVar

from reviewboard.licensing.errors import LicenseActionError
from reviewboard.licensing.license import LicenseInfo, LicenseStatus

if TYPE_CHECKING:
    from collections.abc import Sequence
    from typing import ClassVar

    from django.http import HttpRequest
    from typelets.json import JSONDictImmutable, JSONValue
    from typelets.django.json import SerializableDjangoJSONList

    from reviewboard.licensing.actions import (LicenseAction,
                                               LicenseActionData,
                                               LicenseActionHandler)
    from reviewboard.licensing.license import LicenseLineItem
    from reviewboard.licensing.license_checks import (
        RequestCheckLicenseResult,
        ProcessCheckLicenseResult,
    )


logger = logging.getLogger(__name__)


#: A type variable for license information classes.
#:
#: Version Added:
#:    7.1
_TLicenseInfo = TypeVar('_TLicenseInfo',
                        bound=LicenseInfo,
                        default=LicenseInfo)


class BaseLicenseProvider(Generic[_TLicenseInfo]):
    """Base class for a provider for managing licenses.

    License providers make internal licensing information available to
    Review Board, to simplify and unify license management for multiple
    add-ons in one place.

    A license provider can control what licenses they want to expose for
    display purposes, handle checking for changes to licenses (new, updated,
    or removed), and can provide custom actions that can be invoked via an
    action button.

    Version Added:
        7.1
    """

    #: A set of built-in actions common to all license providers.
    BUILTIN_ACTIONS: Final[set[str]] = {
        'license-update-check',
        'process-license-update',
        'upload-license',
    }

    #: The unique ID of the license provider.
    license_provider_id: ClassVar[str]

    #: The name of the JavaScript model for the license front-end.
    js_license_model_name: ClassVar[str] = 'RB.License'

    #: The name of the JavaScript view for the license front-end.
    js_license_view_name: ClassVar[str] = 'RB.LicenseView'

    #: Custom actions that can be handled by the license provider.
    #:
    #: Each action must correspond to a :samp:`handle_{actionname}_action`
    #: method.
    custom_actions: set[str] = set()

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
    ) -> _TLicenseInfo | None:
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
    ) -> list[LicenseAction]:
        """Return actions to display when viewing a license.

        By default, this may contain Manage License and Update License
        actions. Subclasses may override this to provide custom actions.

        Args:
            license_info (reviewboard.licensing.license.LicenseInfo):
                The license information that will be displayed.

            request (django.http.HttpRequest, optional):
                The HTTP request from the client.

        Returns:
            list of reviewboard.licensing.actions.LicenseAction:
            The list of actions to display for the license.
        """
        actions: list[LicenseAction] = []

        manage_url = self.get_manage_license_url(license_info=license_info)

        if manage_url:
            actions.append({
                'action_id': 'manage-license',
                'label': _('Manage your license'),
                'primary': True,
                'url': manage_url,
            })

        if license_info.can_upload_license:
            actions.append({
                'action_id': 'upload-license',
                'label': _('Upload a new license file'),
            })

        return actions

    def get_license_line_items(
        self,
        *,
        license_info: _TLicenseInfo,
        request: (HttpRequest | None) = None,
    ) -> Sequence[LicenseLineItem]:
        """Return line items to display when viewing a license.

        Line items may contain information or even custom HTML describing
        an important aspect of a license.

        By default, this will contain any line items assigned to the license.
        Subclasses may override this to provide additional information.

        Args:
            license_info (reviewboard.licensing.license.LicenseInfo):
                The license information that will be displayed.

            request (django.http.HttpRequest, optional):
                The HTTP request from the client.

        Returns:
            list of reviewboard.licensing.license.LicenseLineItem:
            The list of line items to display for the license.
        """
        return license_info.line_items

    def get_check_license_request(
        self,
        *,
        action_data: JSONDictImmutable,
        license_info: _TLicenseInfo,
        request: (HttpRequest | None) = None,
    ) -> RequestCheckLicenseResult | None:
        """Return data used to check a license for validity.

        This can be any JSON data that the license provider may want to
        send to a license portal in order to check if a license is still
        valid or if there's a newer license available.

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
        return None

    def get_js_license_model_data(
        self,
        *,
        license_info: _TLicenseInfo,
        request: (HttpRequest | None) = None,
    ) -> SerializableDjangoJSONDict:
        """Return data for the JavaScript license model.

        This provides all the data needed by the JavaScript license model
        to display and manage the license in the UI.

        Args:
            license_info (reviewboard.licensing.license.LicenseInfo):
                The license information to convert to model data.

            request (django.http.HttpRequest, optional):
                The HTTP request from the client.

        Returns:
            typelets.django.json.SerializableDjangoJSONDict:
            The data for the JavaScript license model.
        """
        is_trial = license_info.is_trial
        plan_name = license_info.plan_name
        product = license_info.product_name
        status = license_info.status

        # Calculate expiration information.
        expires = license_info.expires
        grace_period_days = license_info.grace_period_days_remaining
        hard_expires_date: datetime | None

        if expires and grace_period_days:
            hard_expires_date = expires + timedelta(days=grace_period_days)
        else:
            hard_expires_date = expires

        # Generate a notice, if needed.
        notice_html: str = ''

        if status == LicenseStatus.EXPIRED_GRACE_PERIOD:
            # NOTE: This is in Ink syntax, not raw HTML.
            datetime_ink = format_html(
                '<time class="timesince" dateTime="{expires_date}"/>',
                expires_date=hard_expires_date)

            notice_html = format_html(
                _('Your grace period is now active. Unless renewed, '
                  '{product} will be disabled {datetime_ink}.'),
                datetime_ink=datetime_ink,
                product=product)

        # Build actions for the license.
        actions_data: SerializableDjangoJSONList = [
            {
                'actionID': action['action_id'],
                'label': action['label'],
                **{
                    result_key: cast(JSONValue, action.get(action_key))
                    for result_key, action_key in (
                        ('callArgs', 'call_args'),
                        ('extraData', 'extra_data'),
                        ('primary', 'primary'),
                        ('url', 'url')
                    )
                    if action.get(action_key)
                },
            }
            for action in self.get_license_actions(license_info=license_info)
        ]

        # Build line items for the license.
        line_items_data: SerializableJSONList = [
            {
                'content': line_item['content'],
                **{
                    result_key: cast(JSONValue, line_item.get(line_item_key))
                    for result_key, line_item_key in (
                        ('contentIsHTML', 'content_is_html'),
                        ('icon', 'icon'),
                    )
                    if line_item.get(line_item_key)
                },
            }
            for line_item in self.get_license_line_items(
                license_info=license_info)
        ]

        return {
            'actionTarget': (
                f'{self.license_provider_id}:{license_info.license_id}'
            ),
            'actions': actions_data,
            'canUploadLicense': license_info.can_upload_license,
            'expiresDate': expires,
            'expiresSoon': license_info.get_expires_soon(),
            'gracePeriodDaysRemaining': grace_period_days,
            'hardExpiresDate': hard_expires_date,
            'isTrial': is_trial,
            'licenseID': license_info.license_id,
            'licensedTo': license_info.licensed_to,
            'lineItems': line_items_data,
            'manageURL': self.get_manage_license_url(
                license_info=license_info),
            'noticeHTML': notice_html,
            'planID': license_info.plan_id,
            'planName': plan_name,
            'productName': product,
            'status': status.value,
            'summary': license_info.get_summary(),
        }

    def process_check_license_result(
        self,
        *,
        action_data: LicenseActionData,
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
            action_data (reviewboard.licensing.actions.LicenseActionData):
                Data provided in the request to the action.

                This will correspond to HTTP POST data if processing via an
                HTTP request from the client.

            license_info (reviewboard.licensing.license.LicenseInfo):
                The license information to convert to model data.

            check_request_data (typelets.json.JSONValue):
                The original request data sent to the license check.

            check_response_data (typelets.json.JSONValue):
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

    def call_action(
        self,
        action_id: str,
        *,
        license_info: _TLicenseInfo,
        action_data: LicenseActionData = {},
        request: (HttpRequest | None) = None,
    ) -> SerializableDjangoJSONDict:
        """Call and handle a registered license action.

        This is used to perform license action requests from the UI or within
        the server for purposes such as license update checks and activation.

        Custom handlers can include the following standard fields in a JSON
        response:

        Keys:
            license_infos (list of dict, optional):
                A mapping of license IDs to attributes. Any new licenses will
                be added to the display. Any licenses set to ``None`` will
                be removed from the display. Anything else will be updated.

            redirect_url (str, optional):
                A URL to redirect on the client.

        Args:
            action_data (dict):
                Data provided in the request to the action.

                This will correspond to HTTP POST data if processing via an
                HTTP request from the client.

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
                An error invoking an action in the License Provider. This
                will result in a suitable error message for the client.
        """
        norm_action_id = action_id.replace('-', '_')
        handler_name = f'handle_{norm_action_id}_action'

        handler: (LicenseActionHandler | None) = None

        if (action_id in self.BUILTIN_ACTIONS or
            action_id in self.custom_actions):
            try:
                handler = getattr(self, handler_name)
            except AttributeError:
                pass

        if handler is None:
            raise LicenseActionError(
                _('Unsupported license action "{action}".')
                .format(action=action_id))

        return handler(license_info=license_info,
                       action_data=action_data,
                       request=request)

    def handle_license_update_check_action(
        self,
        *,
        action_data: LicenseActionData,
        license_info: _TLicenseInfo,
        request: HttpRequest | None,
    ) -> SerializableDjangoJSONDict:
        """Handle a license update check.

        This will request a license server URL and a payload from the License
        Provider. The client can send the payload to the license server URL to
        request a new license, or check status for a license.

        Args:
            action_data (dict):
                Data provided in the request to the action.

                This will correspond to HTTP POST data if processing via an
                HTTP request from the client.

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
                An error invoking an action in the License Provider. This
                will result in a suitable error message for the client.
        """
        check_request = self.get_check_license_request(
            license_info=license_info,
            action_data=action_data,
            request=request)

        if not check_request:
            return {
                'canCheck': False,
            }

        return {
            'canCheck': True,
            'checkStatusURL': check_request['url'],
            'credentials': check_request.get('credentials'),
            'data': check_request['data'],
            'headers': check_request.get('headers'),
        }

    def handle_process_license_update_action(
        self,
        *,
        action_data: LicenseActionData,
        license_info: _TLicenseInfo,
        request: HttpRequest | None,
    ) -> SerializableDjangoJSONDict:
        """Handle an automated license update payload.

        This will process the payload from a license server, passing the
        result to the License Provider. That may install a new license or
        update information about a license in the backend.

        Args:
            action_data (dict):
                Data provided in the request to the action.

                This will correspond to HTTP POST data if processing via an
                HTTP request from the client.

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
                An error with the data or with invoking the actions in the
                License Provider. This will result in a suitable error
                message for the client.
        """
        trace_id = str(uuid4())

        logger.info('[%s] Checking license update response for License '
                    'Provider %r',
                    trace_id, self.license_provider_id)

        # Pull out the request and response data to verify.
        try:
            check_request_data = action_data['check_request_data']
        except KeyError:
            logger.error('[%s] Missing check_request_data for license check',
                         trace_id)

            raise LicenseActionError(
                _(
                    'Missing check_request_data value for license check. '
                    'This may be an internal error or an issue with the '
                    'licensing server. Check the Review Board server logs '
                    'for more information (error ID {trace_id}).'
                ).format(trace_id=trace_id))

        logger.debug('[%s] Check request data = %r',
                     trace_id, check_request_data)

        try:
            check_response_data = action_data['check_response_data']
        except KeyError:
            logger.error('[%s] Missing check_response_data for license check',
                         trace_id)

            raise LicenseActionError(
                _(
                    'Missing check_response_data value for license check. '
                    'This may be an internal error or an issue with the '
                    'licensing server. Check the Review Board server logs '
                    'for more information (error ID {trace_id}).'
                ).format(trace_id=trace_id))

        logger.debug('[%s] Check response data = %r',
                     trace_id, check_response_data)

        if not check_response_data:
            logger.error('[%s] Empty check_response_data for license check',
                         trace_id)

            raise LicenseActionError(
                _(
                    'Empty check_response_data value for license check. '
                    'This may be an internal error or an issue with the '
                    'licensing server. Check the Review Board server logs '
                    'for more information (error ID {trace_id}).'
                ).format(trace_id=trace_id))

        # Pass to the License Provider and check the result.
        try:
            result = self.process_check_license_result(
                action_data=action_data,
                license_info=license_info,
                check_request_data=check_request_data,
                check_response_data=check_response_data,
                request=request)
            status = result['status']
        except NotImplementedError as e:
            logger.exception('[%s] Automated license checks are enabled '
                             'for this license provider but not implemented. '
                             'This is an internal error.',
                             trace_id)

            raise LicenseActionError(
                _(
                    'The license provider implementation enables support for '
                    'automated license checks but does not provide an '
                    'implementation. This is an internal error. See the '
                    'Review Board server logs for more information (error ID '
                    '{trace_id}).'
                ).format(trace_id=trace_id)
            ) from e
        except LicenseActionError as e:
            raise LicenseActionError(
                _(
                    'Error processing license update: {message}'
                ).format(message=str(e)),
                payload=e.payload,
            ) from e
        except Exception as e:
            logger.exception('[%s] Unexpected error checking license '
                             'result: %s',
                             trace_id, e)

            raise LicenseActionError(
                _(
                    'Unexpected error processing license update. Check the '
                    'Review Board server logs for more information (error ID '
                    '{trace_id}).'
                ).format(trace_id=trace_id)
            ) from e

        logger.info('[%s] License update check complete: %s',
                    trace_id, status)

        return cast(SerializableDjangoJSONDict, result)

    def handle_upload_license_action(
        self,
        *,
        action_data: LicenseActionData,
        license_info: _TLicenseInfo,
        request: HttpRequest | None,
    ) -> SerializableDjangoJSONDict:
        """Handle a manual license upload.

        This will take the provided license data and pass it to the License
        Provider for license replacement. This is dependent on the
        capabilities of the License Provider.

        Args:
            action_data (dict):
                Data provided in the request to the action.

                This will correspond to HTTP POST data if processing via an
                HTTP request from the client.

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
        license_data: (bytes | None) = None

        if request:
            license_data_fp = request.FILES.get('license_data')

            if license_data_fp is not None:
                license_data = license_data_fp.read()

        if not license_data:
            raise LicenseActionError(_('No license data was found'))

        # Allow any errors to bubble up.
        try:
            self.set_license_data(license_info=license_info,
                                  license_data=license_data,
                                  request=request)
        except NotImplementedError:
            raise LicenseActionError(_(
                'Licenses for this product cannot be uploaded manually.'
            ))
        except LicenseActionError:
            # Let this error bubble up.
            raise
        except Exception as e:
            logger.exception('Unexpected error setting license data %r for '
                             'license %r on provider %r: %s',
                             license_data, license_info, self, e)

            raise LicenseActionError(_(
                'Unexpected error setting license data for this product. '
                'Check the Review Board server logs for more information.'
            ))

        # Reload the license.
        new_license_info = self.get_license_by_id(license_info.license_id)

        if new_license_info:
            license_info_data = self.get_js_license_model_data(
                license_info=new_license_info,
                request=request)
        else:
            license_info_data = None

        return {
            'license_info': license_info_data,
        }
