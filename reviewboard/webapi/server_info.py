from __future__ import unicode_literals

from django.conf import settings
from django.contrib.sites.models import Site
from djblets.siteconfig.models import SiteConfiguration

from reviewboard import get_version_string, get_package_version, is_release
from reviewboard.site.urlresolvers import local_site_reverse


def get_server_info(request=None):
    """Returns server information for use in the API.

    This is used for the root resource and for the deprecated server
    info resource.
    """
    site = Site.objects.get_current()
    siteconfig = SiteConfiguration.objects.get_current()

    url = '%s://%s%s' % (siteconfig.get('site_domain_method'), site.domain,
                         local_site_reverse('root', request=request))

    return {
        'product': {
            'name': 'Review Board',
            'version': get_version_string(),
            'package_version': get_package_version(),
            'is_release': is_release(),
        },
        'site': {
            'url': url,
            'administrators': [
                {
                    'name': name,
                    'email': email,
                }
                for name, email in settings.ADMINS
            ],
            'time_zone': settings.TIME_ZONE,
        },
        'capabilities': {
            'diffs': {
                'base_commit_ids': True,
                'moved_files': True,
            },
            'review_requests': {
                'commit_ids': True,
            },
            'scmtools': {
                'git': {
                    'empty_files': True,
                },
                'mercurial': {
                    'empty_files': True,
                },
                'perforce': {
                    'moved_files': True,
                    'empty_files': True,
                },
                'svn': {
                    'empty_files': True,
                },
            },
            'text': {
                'markdown': True,
            },
        }
    }
