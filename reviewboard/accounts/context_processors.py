from __future__ import unicode_literals

from reviewboard.accounts.backends import get_enabled_auth_backends
from reviewboard.accounts.models import Profile


def auth_backends(request):
    return {
        'auth_backends': get_enabled_auth_backends(),
    }


def profile(request):
    if request.user.is_authenticated():
        profile = Profile.objects.get_or_create(user=request.user)[0]
    else:
        profile = None

    return {
        'user_profile': profile,
    }
