"""Views for managing licenses.

Version Added:
    7.1
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, cast
from uuid import uuid4

from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.views.decorators.csrf import csrf_protect
from django.views.generic.base import ContextMixin, View
from djblets.features.decorators import feature_required
from djblets.util.serializers import DjbletsJSONEncoder
from typelets.django.json import SerializableDjangoJSONDict

from reviewboard.licensing.errors import LicenseActionError
from reviewboard.licensing.features import licensing_feature
from reviewboard.licensing.registry import license_provider_registry

if TYPE_CHECKING:
    from django.http import HttpRequest, HttpResponse

    from reviewboard.licensing.license import LicenseInfo
    from reviewboard.licensing.provider import BaseLicenseProvider


logger = logging.getLogger(__name__)


@method_decorator(
    (
        feature_required(licensing_feature),
        staff_member_required,
        csrf_protect,
    ),
    name='dispatch',
)
class LicensesView(ContextMixin, View):
    """Displays and processes information on known product licenses.

    Upon loading, the licenses will be checked for any updates and updated
    if needed.

    Actions on licenses can be performed by sending HTTP POST requests to
    this view with the following form data:

    ``action``:
        The name of the action.

    ``action_target``:
        A generated unique ID for the license for the purpose of this view.

    All actions are considered internal and are subject to change. There are
    no API stability guarantees.

    The following actions are supported:

    ``license-update-check``:
        Generates data for a license update check request to a separate
        licensing server. This is used for automatic license updates.

    ``process-license-update``:
        Process a license update payload from a separate licensing server.
        This is used for automatic license updates.

        It takes the following form data:

        ``check_request_data``:
            The license update check request data originally generated during
            the ``license-update-check`` action.

        ``check_response_data``:
            The payload from the licensing server.

    ``upload-license``:
        Uploads new data for a license, if supported by the License Provider.

        It takes the following form data:

        ``license_data``:
            The new license data.

    Version Added:
        7.1
    """

    def get(
        self,
        request: HttpRequest,
        *args,
        **kwargs,
    ) -> HttpResponse:
        """Handle HTTP GET requests.

        This will display each known license, and handle auto-updating the
        licenses if supported by the License Providers.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            *args (tuple, unused):
                Unused positional arguments passed to the handler.

            **kwargs (dict, unused):
                Unused keyword arguments passed to the handler.

        Returns:
            django.http.HttpResponse:
            The HTTP response for the page.
        """
        license_entries = [
            {
                'license_infos': [
                    {
                        'attrs': license_provider.get_js_license_model_data(
                           license_info=license_info,
                           request=request),
                    }
                    for license_info in license_provider.get_licenses()
                ],
                'model': license_provider.js_license_model_name,
                'view': license_provider.js_license_view_name,
            }
            for license_provider in license_provider_registry
        ]

        return render(
            request=request,
            template_name='admin/licensing.html',
            context={
                'license_entries': license_entries,
            })

    def post(
        self,
        request: HttpRequest,
        *args,
        **kwargs,
    ) -> HttpResponse:
        """Handle HTTP POST requests.

        This will handle requests for license actions, dispatching out to
        the right action handler and returning a JSON payload of the
        results.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            *args (tuple, unused):
                Unused positional arguments passed to the handler.

            **kwargs (tuple, unused):
                Unused keyword arguments passed to the handler.

        Returns:
            django.http.HttpResponse:
            The HTTP response for the page.
        """
        # Pull out the details of the request.
        action = request.POST.get('action')

        try:
            if not action:
                raise LicenseActionError(_('Missing action data.'))

            action_target = request.POST.get('action_target')

            if not action_target:
                raise LicenseActionError(_('Missing action target.'))

            # Parse the action target.
            try:
                license_provider_id, license_id = action_target.split(':')
            except ValueError:
                raise LicenseActionError(_('Invalid action target.'))

            # See if that corresponds to a valid License Provider and license.
            license_provider = license_provider_registry.get_license_provider(
                license_provider_id)

            if license_provider is None:
                raise LicenseActionError(_('Invalid license provider.'))

            license_info = license_provider.get_license_by_id(license_id)

            if license_info is None:
                raise LicenseActionError(_(
                    'The license entry could not be found.'
                ))
        except LicenseActionError as e:
            return HttpResponseBadRequest(
                json.dumps({
                    'error': str(e),
                    **e.payload,
                }),
                content_type='application/json')
        except Exception as e:
            logger.exception('Unexpected error performing license action '
                             '"%s": %s',
                             action, e)

            return HttpResponseBadRequest(
                json.dumps({
                    'error': _(
                        'Unexpected error performing license action '
                        '"{action}": {message}'
                    ).format(action=action,
                             message=e)
                }),
                content_type='application/json')

        # Check which action we're performing and invoke it.
        try:
            if action == 'upload-license':
                result = self._upload_license(
                    license_info=license_info,
                    license_provider=license_provider,
                    request=request)
            elif action == 'license-update-check':
                result = self._license_update_check(
                    license_info=license_info,
                    license_provider=license_provider,
                    request=request)
            elif action == 'process-license-update':
                result = self._process_license_update_data(
                    license_info=license_info,
                    license_provider=license_provider,
                    request=request)
            else:
                raise LicenseActionError(
                    _('Unsupported license action "{action}".')
                    .format(action=action))

            return JsonResponse(result, encoder=DjbletsJSONEncoder)
        except LicenseActionError as e:
            return HttpResponseBadRequest(
                json.dumps({
                    'error': str(e),
                    **e.payload,
                }),
                content_type='application/json')
        except Exception as e:
            logger.exception('Unexpected error performing license action '
                             '"%s" for license %r on provider %r: %s',
                             action, license_info, license_provider, e)

            return HttpResponseBadRequest(
                json.dumps({
                    'error': _(
                        'Unexpected error performing license action '
                        '"{action}": {message}'
                    ).format(action=action,
                             message=e)
                }),
                content_type='application/json')

    def _license_update_check(
        self,
        *,
        license_info: LicenseInfo,
        license_provider: BaseLicenseProvider,
        request: HttpRequest,
    ) -> SerializableDjangoJSONDict:
        """Handle a license update check.

        This will request a license server URL and a payload from the License
        Provider. The client can send the payload to the license server URL to
        request a new license, or check status for a license.

        Args:
            license_info (reviewboard.licensing.license.LicenseInfo):
                Information on the license to check for updates.

            license_provider (reviewboard.licensing.provider.
                              BaseLicenseProvider):
                The License Provider managing this license.

            request (django.http.HttpRequest):
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
        check_request = license_provider.get_check_license_request(
            license_info=license_info,
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

    def _process_license_update_data(
        self,
        *,
        license_info: LicenseInfo,
        license_provider: BaseLicenseProvider,
        request: HttpRequest,
    ) -> SerializableDjangoJSONDict:
        """Handle an automated license update payload.

        This will process the payload from a license server, passing the
        result to the License Provider. That may install a new license or
        update information about a license in the backend.

        Args:
            license_info (reviewboard.licensing.license.LicenseInfo):
                Information on the license to check for updates.

            license_provider (reviewboard.licensing.provider.
                              BaseLicenseProvider):
                The License Provider managing this license.

            request (django.http.HttpRequest):
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
                    trace_id, license_provider.license_provider_id)

        # Pull out the request and response data to verify.
        try:
            check_request_data = request.POST['check_request_data']
        except KeyError:
            logger.error('[%s] Missing check_request_data for license check',
                         trace_id)

            raise LicenseActionError(
                _('Missing check_request_data value for license check. '
                  'This may be an internal error or an issue with the '
                  'licensing server. Check the Review Board server logs for '
                  'more information (error ID {trace_id}).')
                .format(trace_id=trace_id))

        logger.debug('[%s] Check request data = %r',
                     trace_id, check_request_data)

        try:
            check_response_data = request.POST['check_response_data']
        except KeyError:
            logger.error('[%s] Missing check_response_data for license check',
                         trace_id)

            raise LicenseActionError(
                _('Missing check_response_data value for license check. '
                  'This may be an internal error or an issue with the '
                  'licensing server. Check the Review Board server logs for '
                  'more information (error ID {trace_id}).')
                .format(trace_id=trace_id))

        logger.debug('[%s] Check response data = %r',
                     trace_id, check_response_data)

        if not check_response_data:
            logger.error('[%s] Empty check_response_data for license check',
                         trace_id)

            raise LicenseActionError(
                _('Empty check_response_data value for license check. '
                  'This may be an internal error or an issue with the '
                  'licensing server. Check the Review Board server logs for '
                  'more information (error ID {trace_id}).')
                .format(trace_id=trace_id))

        # Deserialize the payloads.
        try:
            check_request_payload = json.loads(check_request_data)
        except ValueError:
            logger.error('[%s] check_request_data was not valid JSON',
                         trace_id)

            raise LicenseActionError(
                _('Invalid check_request_data value for license check. '
                  'This may be an internal error or an issue with the '
                  'licensing server. Check the Review Board server logs for '
                  'more information (error ID {trace_id}).')
                .format(trace_id=trace_id))

        try:
            check_response_payload = json.loads(check_response_data)
        except ValueError:
            logger.error('[%s] check_response_data was not valid JSON',
                         trace_id)

            raise LicenseActionError(
                _('Invalid check_response_data value for license check. '
                  'This may be an internal error or an issue with the '
                  'licensing server. Check the Review Board server logs for '
                  'more information (error ID {trace_id}).')
                .format(trace_id=trace_id))

        # Pass to the License Provider and check the result.
        try:
            result = license_provider.process_check_license_result(
                license_info=license_info,
                check_request_data=check_request_payload,
                check_response_data=check_response_payload,
                request=request)
            status = result['status']
        except NotImplementedError as e:
            logger.exception('[%s] Automated license checks are enabled '
                             'for this license provider but not implemented. '
                             'This is an internal error.',
                             trace_id)

            raise LicenseActionError(
                _('The license provider implementation enables support for '
                  'automated license checks but does not provide an '
                  'implementation. This is an internal error. See the '
                  'Review Board server logs for more information (error ID '
                  '{trace_id}).')
                .format(trace_id=trace_id)
            ) from e
        except LicenseActionError as e:
            raise LicenseActionError(
                _('Error processing license update: {message}')
                .format(message=str(e)),
                payload=e.payload
            ) from e
        except Exception as e:
            logger.exception('[%s] Unexpected error checking license '
                             'result: %s',
                             trace_id, e)

            raise LicenseActionError(
                _('Unexpected error processing license update. Check the '
                  'Review Board server logs for more information (error ID '
                  '{trace_id}).')
                .format(trace_id=trace_id)
            ) from e

        logger.info('[%s] License update check complete: %s',
                    trace_id, status)

        return cast(SerializableDjangoJSONDict, result)

    def _upload_license(
        self,
        *,
        license_info: LicenseInfo,
        license_provider: BaseLicenseProvider,
        request: HttpRequest,
    ) -> SerializableDjangoJSONDict:
        """Handle a manual license upload.

        This will take the provided license data and pass it to the License
        Provider for license replacement. This is dependent on the
        capabilities of the License Provider.

        Args:
            license_info (reviewboard.licensing.license.LicenseInfo):
                Information on the license to check for updates.

            license_provider (reviewboard.licensing.provider.
                              BaseLicenseProvider):
                The License Provider managing this license.

            request (django.http.HttpRequest):
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
        license_data_fp = request.FILES.get('license_data')

        if not license_data_fp:
            raise LicenseActionError(_('No license data was found'))

        license_data = license_data_fp.read()

        # Allow any errors to bubble up.
        try:
            license_provider.set_license_data(
                license_info=license_info,
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
                             license_data, license_info, license_provider, e)

            raise LicenseActionError(_(
                'Unexpected error setting license data for this product. '
                'Check the Review Board server logs for more information.'
            ))

        # Reload the license.
        new_license_info = license_provider.get_license_by_id(
            license_info.license_id)

        if new_license_info:
            license_info_data = license_provider.get_js_license_model_data(
                license_info=new_license_info,
                request=request)
        else:
            license_info_data = None

        return {
            'license_info': license_info_data,
        }
