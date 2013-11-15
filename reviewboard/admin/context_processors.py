from __future__ import unicode_literals

from reviewboard import (get_version_string, get_package_version, is_release,
                         VERSION)


def version(request):
    return {
        'version': get_version_string(),
        'package_version': get_package_version(),
        'is_release': is_release(),
        'version_raw': VERSION,
    }
