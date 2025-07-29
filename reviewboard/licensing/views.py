"""Views for managing licenses.

Version Added:
    7.1
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from django.views.generic.base import ContextMixin, View
from djblets.features.decorators import feature_required

from reviewboard.licensing.features import licensing_feature
from reviewboard.licensing.registry import license_provider_registry

if TYPE_CHECKING:
    from django.http import HttpRequest, HttpResponse


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
                'attrs': license_provider.get_js_license_model_data(
                    license_info=license_info,
                    request=request),
                'model': license_provider.js_license_model_name,
                'view': license_provider.js_license_view_name,
            }
            for license_provider in license_provider_registry
            for license_info in license_provider.get_licenses()
        ]

        return render(
            request=request,
            template_name='admin/licensing.html',
            context={
                'license_entries': license_entries,
            })
