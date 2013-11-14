from __future__ import unicode_literals

from django.conf import settings
from django.contrib.sites.models import Site
from djblets.siteconfig.models import SiteConfiguration
from djblets.webapi.decorators import webapi_response_errors
from djblets.webapi.errors import NOT_LOGGED_IN, PERMISSION_DENIED

from reviewboard import get_version_string, get_package_version, is_release
from reviewboard.site.urlresolvers import local_site_reverse
from reviewboard.webapi.base import WebAPIResource
from reviewboard.webapi.decorators import (webapi_check_login_required,
                                           webapi_check_local_site)


class ServerInfoResource(WebAPIResource):
    """Information on the Review Board server.

    This contains product information, such as the version, and
    site-specific information, such as the main URL and list of
    administrators.
    """
    name = 'info'
    singleton = True
    mimetype_item_resource_name = 'server-info'

    @webapi_check_local_site
    @webapi_response_errors(NOT_LOGGED_IN, PERMISSION_DENIED)
    @webapi_check_login_required
    def get(self, request, *args, **kwargs):
        """Returns the information on the Review Board server."""
        site = Site.objects.get_current()
        siteconfig = SiteConfiguration.objects.get_current()

        url = '%s://%s%s' % (siteconfig.get('site_domain_method'), site.domain,
                             local_site_reverse('root', request=request))

        return 200, {
            self.item_result_key: {
                'product': {
                    'name': 'Review Board',
                    'version': get_version_string(),
                    'package_version': get_package_version(),
                    'is_release': is_release(),
                },
                'site': {
                    'url': url,
                    'administrators': [{'name': name, 'email': email}
                                       for name, email in settings.ADMINS],
                    'time_zone': settings.TIME_ZONE,
                },
                'capabilities': {
                    'diffs': {
                        'base_commit_ids': True,
                        'moved_files': True,
                    },
                    'scmtools': {
                        'perforce': {
                            'moved_files': True,
                        },
                    },
                },
            },
        }


server_info_resource = ServerInfoResource()
