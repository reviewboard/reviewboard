from __future__ import unicode_literals

import socket

from django.contrib.sites.models import Site
from django.utils import six
from django.utils.six.moves.urllib.parse import urljoin
from djblets.siteconfig.models import SiteConfiguration

from reviewboard.site.urlresolvers import local_site_reverse


def get_server_url(local_site_name=None, local_site=None, request=None):
    """Return the URL for the root of the server.

    This will construct a URL that points to the root of the server, factoring
    in whether to use HTTP or HTTPS.

    If ``local_site_name`` or ``local_site`` is provided, then the URL will be
    the root to the LocalSite's root, rather than the server's root.

    If ``request`` is provided, then the Local Site, if any, will be
    inferred from the request.
    """
    site = Site.objects.get_current()
    siteconfig = SiteConfiguration.objects.get_current()
    root = local_site_reverse('root', local_site_name=local_site_name,
                              local_site=local_site, request=request)

    return '%s://%s%s' % (siteconfig.get('site_domain_method'),
                          site.domain, root)


def build_server_url(*args, **kwargs):
    """Build an absolute URL containing the full URL to the server.

    All additional arguments passed will be appended as paths to the URL.
    """
    return urljoin(get_server_url(**kwargs), *args)


def get_hostname():
    """Return the hostname for this Review Board server.

    Returns:
        unicode:
        The hostname for the server.
    """
    return six.text_type(socket.gethostname())
