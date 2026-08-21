"""Functions for retrieving server information."""

from __future__ import annotations

import os
import socket
from functools import lru_cache
from typing import TYPE_CHECKING
from urllib.parse import urljoin

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import gettext as _
from djblets.util.functional import lazy_re_compile
from djblets.siteconfig.models import SiteConfiguration

from reviewboard.site.urlresolvers import local_site_reverse

if TYPE_CHECKING:
    from re import Pattern
    from typing import Final


#: A cached path containing the site's data directory.
_data_dir: (str | None) = None


#: A regex for parsing registered Linux mount paths.
#:
#: Version Added:
#:     9.0
_MOUNT_RE: Final[Pattern[str]] = lazy_re_compile(
    r'[^ ]+ (?P<mount>[^ ]+) (?P<fs_type>[^ ]+) .+'
)


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


@lru_cache
def is_nfs_path(
    path: str,
    *,
    _mounts_path: str = '/proc/mounts',
) -> bool:
    """Return whether a path appears to be on an NFS mount.

    This makes a best-effort check to determine if a path is an NFS mount
    point. It does this by looking for a :file:`/proc/mounts` file and
    parsing it to find an entry that would be a parent of the provided path.

    It can be used to warn if using an NFS mount path for operations that
    aren't always safe on NFS.

    This is only expected to work on Linux systems. It cannot check on other
    systems.

    Results are cached and may be stale if mount points change in important
    ways while the process is running.

    Version Added:
        9.0

    Args:
        path (str):
            The path to check.

        _mounts_path (str, optional):
            The path to the mounts file.

            Callers shouldn't override this. It should only be explicitly
            set in unit tests.

    Returns:
        bool:
        ``True`` if the path appears to be on an NFS mount, or
        ``False`` otherwise.
    """
    is_nfs = False

    try:
        with open(_mounts_path, 'r') as fp:
            norm_abs_path = os.path.realpath(path) + os.sep
            best_match_len = 0

            for line in fp:
                if m := _MOUNT_RE.match(line):
                    mount_point = m.group('mount')

                    if (norm_abs_path.startswith(mount_point + os.sep) and
                        (match_len := len(mount_point)) > best_match_len):
                        # This is the best match so far. Consider it the
                        # most relevant parent, and key off the NFS flag
                        # from its filesystem type.
                        best_match_len = match_len
                        is_nfs = m.group('fs_type').startswith('nfs')
    except OSError:
        # We likely couldn't find it or read it. This is harmless. We will
        # fall back to a False result.
        pass

    return is_nfs
