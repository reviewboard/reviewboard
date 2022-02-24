import logging

from django.conf import settings
from djblets.siteconfig.models import SiteConfiguration

from reviewboard import initialize
from reviewboard.admin.checks import check_updates_required
from reviewboard.admin.siteconfig import load_site_config
from reviewboard.admin.views import manual_updates_required


logger = logging.getLogger(__name__)


_initialized = False


def init_review_board_middleware(get_response):
    """Handle the initialization of Review Board.

    Args:
        get_response (callable):
            The method to execute the view.
    """
    def middleware(request):
        """Ensure that Review Board initialization code has run.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

        Returns:
            django.http.HttpResponse:
            The response object.
        """
        global _initialized

        if not _initialized:
            initialize()
            _initialized = True

        return get_response(request)

    return middleware


def load_settings_middleware(get_response):
    """Middleware that loads the settings on each request.

    Args:
        get_response (callable):
            The method to execute the view.
    """
    def middleware(request):
        """Ensure that the latest siteconfig is loaded.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

        Returns:
            django.http.HttpResponse:
            The response object.
        """
        try:
            siteconfig = SiteConfiguration.objects.get_current()
        except Exception as e:
            logger.critical('Unable to load SiteConfiguration: %s',
                            e, exc_info=True)
            return

        # This will be unset if the SiteConfiguration expired, since we'll
        # have a new one in the cache.
        if not hasattr(siteconfig, '_rb_settings_loaded'):
            # Load all site settings.
            load_site_config(full_reload=True)
            siteconfig._rb_settings_loaded = True

        if siteconfig.settings.get('site_domain_method', 'http') == 'https':
            request.META['wsgi.url_scheme'] = 'https'

        return get_response(request)

    return middleware


def check_updates_required_middleware(get_response):
    """Middleware that checks if manual updates need to be done.

    If updates are required, all attempts to access a URL will be redirected to
    the updates page (or an appropriate error response for API calls).

    Args:
        get_response (callable):
            The method to execute the view.
    """
    ALLOWED_PATHS = (
        settings.STATIC_URL,
        settings.SITE_ROOT + 'jsi18n/',
    )

    def middleware(request):
        """Check whether updates are required.

        This returns the appropriate response if any updates are required,
        otherwise it allows the normal code to run.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

        Returns:
            django.http.HttpResponse:
            The response object.
        """
        path_info = request.META['PATH_INFO']

        updates_required = check_updates_required()

        if updates_required and not path_info.startswith(ALLOWED_PATHS):
            return manual_updates_required(request, updates_required)

        return get_response(request)

    return middleware


class ExtraExceptionInfoMiddleware(object):
    """Add extra debugging information to exception e-mails.

    If an exception occurs, the META field will be updated to contain
    the username and e-mail address of the user who triggered the error
    (if any), and the Local Site name (if any).
    """

    def __init__(self, get_response):
        """Initialize the middleware.

        Args:
            get_response (callable):
                The method to call to get the response object.
        """
        self.get_response = get_response

    def process_exception(self, request, exception):
        """Process an exception.

        Exceptions from views are handled by sending the admin users an e-mail
        with the traceback. This adds additional information to the META
        dictionary before that happens.
        """
        if request.user.is_authenticated:
            request.META['USERNAME'] = request.user.username
            request.META['USER_EMAIL'] = request.user.email

        if hasattr(request, '_local_site_name'):
            request.META['LOCAL_SITE'] = request._local_site_name

    def __call__(self, request):
        """Run the middleware.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

        Returns:
            django.http.HttpResponse:
            The response object.
        """
        return self.get_response(request)
