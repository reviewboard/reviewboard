from __future__ import unicode_literals

from django.contrib.auth.models import User
from djblets.webapi.auth import (
    WebAPIBasicAuthBackend as DjbletsWebAPIBasicAuthBackend)
from djblets.webapi.auth.backends.api_tokens import TokenAuthBackendMixin
from djblets.webapi.auth.backends.oauth2_tokens import OAuth2TokenBackendMixin

from reviewboard.accounts.backends import AuthBackend
from reviewboard.webapi.models import WebAPIToken


class TokenAuthBackend(TokenAuthBackendMixin, AuthBackend):
    """Authenticates users and their API tokens for API requests.

    This will handle authenticating users and their API tokens for API
    requests. It's only used for API requests that specify a username and a
    token.
    """

    api_token_model = WebAPIToken


class OAuth2TokenAuthBackend(OAuth2TokenBackendMixin, AuthBackend):
    """An OAuth2 token authentication backend that handles local sites.

    This is similar to :py:class:`oauth2_provider.backends.OAuth2Backend`
    except it ensures the application is enabled and either:

    * not limited to a local site; or
    * limited to the local site being requested.
    """

    def verify_request(self, request, token, user):
        """Ensure the given authentication request is valid.

        This method ensures the following:

        * The Application being used for authentication is enabled.
        * The Local Site the Application is associated with matches the Local
          Site of the current HTTP request.
        * If the Application is associated with a Local Site that site must be
          accessible to the user performing the authentication.

        Args:
            request (django.http.HttpRequest):
                The current HTTP request.

            token (oauth2_provider.models.AccessToken):
                The access token being used for authentication.

            user (django.contrib.auth.models.User):
                The user who is authenticating.

        Returns:
            bool:
            Whether or not the authentication request is valid.
        """
        application = token.application
        return (application.enabled and
                application.local_site == request.local_site and
                (not application.local_site or
                 application.local_site.is_accessible_by(user)))


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
