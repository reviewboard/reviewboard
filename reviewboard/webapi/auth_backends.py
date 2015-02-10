from __future__ import unicode_literals

import logging

from djblets.webapi.auth import WebAPIAuthBackend

from reviewboard.accounts.backends import AuthBackend
from reviewboard.webapi.models import WebAPIToken


class TokenAuthBackend(AuthBackend):
    """Authenticates users and their API tokens for API requests.

    This is used only for API requests that specify a username and a token.
    """
    def authenticate(self, token=None, **kwargs):
        if not token:
            return None

        # Find the WebAPIToken matching the token parameter passed in.
        # Once we have it, we'll need to perform some additional checks on
        # the user.
        q = WebAPIToken.objects.filter(token=token).select_related('user')

        try:
            webapi_token = q.get()
        except WebAPIToken.DoesNotExist:
            return None

        user = webapi_token.user

        if not user.is_active:
            return None

        # Store this temporarily. We'll be using it to store some session
        # state.
        user._webapi_token = webapi_token

        return user


class WebAPITokenAuthBackend(WebAPIAuthBackend):
    """Authenticates users using their generated API token.

    This will check the HTTP_AUTHORIZATION header for a "token <token>"
    value. If found, it will attempt to find the user that owns the
    token, and authenticate that user.
    """
    def get_credentials(self, request):
        http_auth = request.META['HTTP_AUTHORIZATION']
        parts = http_auth.split(' ')

        if parts[0] != 'token':
            return None

        if len(parts) != 2:
            logging.warning('APITokenWebAPIAuthBackend: Missing token in '
                            'HTTP_AUTHORIZATION header %s',
                            http_auth, extra={'request': request})
            return None

        return {
            'token': parts[1],
        }

    def login_with_credentials(self, request, **credentials):
        """Logs the user in with the given credentials.

        This performs the standard authentication operations, and then
        stores some session state for any restrictions specified by the
        token.
        """
        result = super(WebAPITokenAuthBackend, self).\
            login_with_credentials(request, **credentials)

        if result[0]:
            user = request.user
            webapi_token = user._webapi_token
            del user._webapi_token

            request.session['webapi_token_id'] = webapi_token.pk
            request._webapi_token = webapi_token

        return result
