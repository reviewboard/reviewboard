"""Functions for retrieving server information."""

from __future__ import annotations

import os
import socket
from typing import Optional
from urllib.parse import urljoin

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import gettext as _
from djblets.siteconfig.models import SiteConfiguration

from reviewboard.site.urlresolvers import local_site_reverse


#: A cached path containing the site's data directory.
_data_dir: Optional[str] = None


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


def build_server_url(path=None, **kwargs):
    """Build an absolute URL containing the full URL to the server.

    A path can be supplied that will be joined to the server URL.

    Args:
        path (unicode):
            The path to append to the server URL.

        **kwargs (dict):
            Additional arguments to pass to :py:func:`get_server_url`.

    Returns:
        unicode:
        The resulting URL.
    """
    return urljoin(get_server_url(**kwargs), path)


def get_hostname():
    """Return the hostname for this Review Board server.

    Returns:
        unicode:
        The hostname for the server.
    """
    return str(socket.gethostname())


def get_data_dir() -> str:
    """Return the path to the site's data directory.

    This is always based on :envvar:`$HOME`. If this variable is not set,
    or the path does not exist, then an exception will be raised.

    Version Added:
        6.0

    Returns:
        str:
        The path to the data directory.

    Raises:
        django.core.exceptions.ImproperlyConfigured:
            The data directory path could not be found or does not exist.

            Details are in the error message.
    """
    global _data_dir

    if _data_dir != settings.SITE_DATA_DIR:
        _data_dir = settings.SITE_DATA_DIR

        if not _data_dir:
            raise ImproperlyConfigured(
                _('The site data directory could not be determined. '
                  'Please make sure your web server is using our '
                  'provided reviewboard.wsgi module for WSGI.'))

        if not os.path.exists(_data_dir):
            raise ImproperlyConfigured(
                _('The site data directory (%s) does not exist. Please '
                  'make sure you are running in the right environment with a '
                  'working site directory.') % _data_dir)

    return _data_dir
