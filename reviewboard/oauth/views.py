"""OAuth2 views."""

from __future__ import unicode_literals

from oauth2_provider.views import AuthorizationView as BaseAuthorizationView


class AuthorizationView(BaseAuthorizationView):
    """An authorization view that uses our own template."""

    template_name = 'oauth/authorize.html'
