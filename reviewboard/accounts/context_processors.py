from reviewboard.accounts.backends import get_auth_backends


def auth_backends(request):
    return {
        'auth_backends': get_auth_backends(),
    }
