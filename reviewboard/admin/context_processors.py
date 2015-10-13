from __future__ import unicode_literals

from reviewboard import (get_manual_url, get_package_version,
                         get_version_string, is_release, VERSION)


def version(request):
    """Return a dictionary with version information."""
    return {
        'version': get_version_string(),
        'package_version': get_package_version(),
        'is_release': is_release(),
        'version_raw': VERSION,
        'RB_MANUAL_URL': get_manual_url(),
    }
