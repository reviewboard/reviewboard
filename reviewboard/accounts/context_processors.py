from __future__ import unicode_literals

from reviewboard.accounts.backends import get_enabled_auth_backends
from reviewboard.accounts.models import Profile


def auth_backends(request):
    """Add the enabled authentication backends to the template context."""
    return {
        'auth_backends': get_enabled_auth_backends(),
    }


def profile(request):
    """Add the current user's profile to the template context."""
    if request.user.is_authenticated():
        profile = Profile.objects.get_or_create(user=request.user)[0]
    else:
        profile = None

    return {
        'user_profile': profile,
    }
