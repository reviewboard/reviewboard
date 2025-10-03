"""Views for managing licenses.

Version Added:
    7.1
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

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

    from reviewboard.licensing.provider import LicenseActionData


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
        action_data: LicenseActionData = {}

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

            action_data_json = request.POST.get('action_data')

            if action_data_json:
                try:
                    action_data = json.loads(action_data_json)

                    if not isinstance(action_data, dict):
                        raise ValueError(_(
                            'Must be a mapping of key/value arguments.'
                        ))
                except Exception as e:
                    raise LicenseActionError(_(
                        'Invalid action data: {error}.'
                    ).format(error=e))
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

        # Invoke the action on the license provider.
        try:
            result = license_provider.call_action(
                action_id=action,
                license_info=license_info,
                action_data=action_data,
                request=request)

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
