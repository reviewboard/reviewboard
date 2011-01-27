import logging
import os

from django.conf import settings
from django.contrib import auth
from django.core.handlers.modpython import ModPythonRequest
from django.core.handlers.wsgi import WSGIRequest


from reviewboard.admin.checks import check_updates_required
from reviewboard.admin.siteconfig import load_site_config
from reviewboard.admin.views import manual_updates_required


class LoadSettingsMiddleware(object):
    """
    Middleware that loads the settings on each request.
    """
    def process_request(self, request):
        # Load all site settings.
        load_site_config()


class CheckUpdatesRequiredMiddleware(object):
    """
    Middleware that checks if manual updates need to be made on the
    installation. If updates are required, all attempts to access a
    URL will be redirected to the updates page (or an appropriate
    error response for API calls.
    """
    def process_request(self, request):
        """
        Checks whether updates are required and returns the appropriate
        response if they are.
        """
        path_info = request.META['PATH_INFO']

        if (check_updates_required() and
            not path_info.startswith(settings.MEDIA_URL)):
            return manual_updates_required(request)

        # Let another handler handle this.
        return None


class X509AuthMiddleware(object):
    """
    Middleware that authenticates a user using the environment variables set by
    mod_ssl.

    Apache needs to be configured with mod_ssl. For Review Board to be usable
    with X.509 client certificate authentication, the 'SSLVerifyClient'
    configuration directive should be set to 'optional'. This will ensure that
    basic authentication will still work, allowing the post-review tool to work
    with a username and password.
    """
    def process_request(self, request):
        if ('reviewboard.accounts.backends.X509Backend'
            not in settings.AUTHENTICATION_BACKENDS):
            return None

        if not request.is_secure():
            return None

        if isinstance(request, ModPythonRequest):
            env = os.environ
        elif isinstance(request, WSGIRequest):
            env = request.environ
        else:
            # Unknown request type; bail out gracefully.
            logging.error("X509AuthMiddleware: unknown request type '%s'" %
                          type(request))
            env = {}

        x509_settings_field = getattr(settings, 'X509_USERNAME_FIELD', None)

        if x509_settings_field:
            x509_field = env.get(x509_settings_field)

            if x509_field:
                user = auth.authenticate(x509_field=x509_field)

                if user:
                    request.user = user
                    auth.login(request, user)

        return None
