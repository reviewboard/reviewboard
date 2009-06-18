from reviewboard import get_version_string, get_package_version, is_release


def version(request):
    return {
        'version': get_version_string(),
        'package_version': get_package_version(),
        'is_release': is_release(),
    }
