from __future__ import unicode_literals

import logging

from django.conf import settings
from djblets.siteconfig.models import SiteConfiguration

from reviewboard import initialize
from reviewboard.accounts.backends.registry import get_enabled_auth_backends
from reviewboard.accounts.backends.x509 import X509Backend
from reviewboard.admin.checks import check_updates_required
from reviewboard.admin.siteconfig import load_site_config
from reviewboard.admin.views import manual_updates_required


class InitReviewBoardMiddleware(object):
    """Handle the initialization of Review Board."""

    def __init__(self, *args, **kwargs):
        """Initialize the middleware."""
        super(InitReviewBoardMiddleware, self).__init__(*args, **kwargs)
        self._initialized = False

    def process_request(self, request):
        """Ensure that Review Board initialization code has run."""
        if not self._initialized:
            initialize()
            self._initialized = True


class LoadSettingsMiddleware(object):
    """Middleware that loads the settings on each request."""

    def process_request(self, request):
        """Ensure that the latest siteconfig is loaded."""
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
    """Middleware that checks if manual updates need to be done.

    If updates are required, all attempts to access a URL will be redirected to
    the updates page (or an appropriate error response for API calls).
    """

    ALLOWED_PATHS = (
        settings.STATIC_URL,
        settings.SITE_ROOT + 'jsi18n/',
    )

    def process_view(self, request, view_func, view_args, view_kwargs):
        """Check whether updates are required.

        This returns the appropriate response if any updates are required,
        otherwise it allows the normal code to run.
        """
        path_info = request.META['PATH_INFO']

        updates_required = check_updates_required()

        if updates_required and not path_info.startswith(self.ALLOWED_PATHS):
            return manual_updates_required(request, updates_required)

        # Let another handler handle this.
        return None


class ExtraExceptionInfoMiddleware(object):
    """Add extra debugging information to exception e-mails.

    If an exception occurs, the META field will be updated to contain
    the username and e-mail address of the user who triggered the error
    (if any), and the Local Site name (if any).
    """

    def process_exception(self, request, exception):
        """Process an exception.

        Exceptions from views are handled by sending the admin users an e-mail
        with the traceback. This adds additional information to the META
        dictionary before that happens.
        """
        if request.user.is_authenticated():
            request.META['USERNAME'] = request.user.username
            request.META['USER_EMAIL'] = request.user.email

        if hasattr(request, '_local_site_name'):
            request.META['LOCAL_SITE'] = request._local_site_name
