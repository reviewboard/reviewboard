from reviewboard.accounts.backends import get_enabled_auth_backends


def auth_backends(request):
    """Add the enabled authentication backends to the template context."""
    return {
        'auth_backends': get_enabled_auth_backends(),
    }


def profile(request):
    """Add the current user's profile to the template context."""
    if request.user.is_authenticated:
        profile = request.user.get_profile()
    else:
        profile = None

    return {
        'user_profile': profile,
    }
