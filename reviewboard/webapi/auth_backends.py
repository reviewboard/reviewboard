from __future__ import unicode_literals

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
