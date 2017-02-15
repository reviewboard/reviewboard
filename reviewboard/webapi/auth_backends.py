from __future__ import unicode_literals

from django.contrib.auth.models import User
from djblets.webapi.auth import (
    WebAPIBasicAuthBackend as DjbletsWebAPIBasicAuthBackend)
from djblets.webapi.auth.backends.api_tokens import TokenAuthBackendMixin

from reviewboard.accounts.backends import AuthBackend
from reviewboard.webapi.models import WebAPIToken


class TokenAuthBackend(TokenAuthBackendMixin, AuthBackend):
    """Authenticates users and their API tokens for API requests.

    This will handle authenticating users and their API tokens for API
    requests. It's only used for API requests that specify a username and a
    token.
    """

    api_token_model = WebAPIToken


class WebAPIBasicAuthBackend(DjbletsWebAPIBasicAuthBackend):
    """A specialized WebAPI Basic auth backend that supports e-mail addresses.
    """

    def get_credentials(self, request):
        """Return the credentials supplied in the request.

        If the user provides an e-mail address as the username credential, it
        will be translated to a username.

        Args:
            request (django.http.HttpRequest):
                The request containing the credentials.

        Returns:
            dict:
            A dictionary of the supplied credentials.
        """
        credentials = super(WebAPIBasicAuthBackend, self).get_credentials(
            request)

        if credentials and 'username' in credentials:
            user_exists = (
                User.objects
                .filter(username=credentials['username'])
                .exists()
            )

            if not user_exists and '@' in credentials['username']:
                users = (
                    User.objects
                    .filter(email=credentials['username'])
                    .values_list('username', flat=True)
                )

                if users:
                    credentials['username'] = users[0]

        return credentials
