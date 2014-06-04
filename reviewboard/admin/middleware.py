from __future__ import unicode_literals

import logging
import os

from django.conf import settings
from django.contrib import auth

try:
    from django.core.handlers.modpython import ModPythonRequest
except ImportError:
    class ModPythonRequest:
        pass

try:
    from django.core.handlers.wsgi import WSGIRequest
except ImportError:
    class WSGIRequest:
        pass

from djblets.siteconfig.models import SiteConfiguration

from reviewboard import initialize
from reviewboard.admin.checks import check_updates_required
from reviewboard.admin.siteconfig import load_site_config
from reviewboard.admin.views import manual_updates_required


class InitReviewBoardMiddleware(object):
    """Handles the initialization of Review Board."""
    def __init__(self, *args, **kwargs):
        super(InitReviewBoardMiddleware, self).__init__(*args, **kwargs)
        self._initialized = False

    def process_request(self, request):
        if not self._initialized:
            initialize()
            self._initialized = True


class LoadSettingsMiddleware(object):
    """
    Middleware that loads the settings on each request.
    """
    def process_request(self, request):
        try:
            siteconfig = SiteConfiguration.objects.get_current()
        except Exception as e:
            logging.critical('Unable to load SiteConfiguration: %s',
                             e, exc_info=1)
            return

        # This will be unset if the SiteConfiguration expired, since we'll
        # have a new one in the cache.
        if not hasattr(siteconfig, '_rb_settings_loaded'):
            # Load all site settings.
            load_site_config(full_reload=True)
            siteconfig._rb_settings_loaded = True

        if siteconfig.settings.get('site_domain_method', 'http') == 'https':
            request.META['wsgi.url_scheme'] = 'https'


class CheckUpdatesRequiredMiddleware(object):
    """
    Middleware that checks if manual updates need to be made on the
    installation. If updates are required, all attempts to access a
    URL will be redirected to the updates page (or an appropriate
    error response for API calls.
    """
    ALLOWED_PATHS = (
        settings.STATIC_URL,
        settings.SITE_ROOT + 'jsi18n/',
    )

    def process_view(self, request, view_func, view_args, view_kwargs):
        """
        Checks whether updates are required and returns the appropriate
        response if they are.
        """
        path_info = request.META['PATH_INFO']

        updates_required = check_updates_required()

        if updates_required and not path_info.startswith(self.ALLOWED_PATHS):
            return manual_updates_required(request, updates_required)

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
