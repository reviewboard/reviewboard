from __future__ import unicode_literals

from django.conf import settings
from django.contrib.sites.models import Site
from djblets.siteconfig.models import SiteConfiguration
from djblets.webapi.decorators import webapi_response_errors
from djblets.webapi.errors import NOT_LOGGED_IN, PERMISSION_DENIED

from reviewboard import get_version_string, get_package_version, is_release
from reviewboard.webapi.base import WebAPIResource
from reviewboard.webapi.decorators import (webapi_check_login_required,
                                           webapi_check_local_site)
from reviewboard.webapi.server_info import get_server_info


class ServerInfoResource(WebAPIResource):
    """Information on the Review Board server.

    This contains product information, such as the version, and
    site-specific information, such as the main URL and list of
    administrators.

    This is deprecated in favor of the data in the root resource.
    """
    name = 'info'
    singleton = True
    mimetype_item_resource_name = 'server-info'

    @webapi_check_local_site
    @webapi_response_errors(NOT_LOGGED_IN, PERMISSION_DENIED)
    @webapi_check_login_required
    def get(self, request, *args, **kwargs):
        """Returns the information on the Review Board server."""
        return 200, {
            self.item_result_key: get_server_info(request),
        }


server_info_resource = ServerInfoResource()
