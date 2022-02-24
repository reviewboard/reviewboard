"""Middleware for account-related functionality."""

import pytz
from django.conf import settings
from django.contrib import auth
from django.utils import timezone
from djblets.siteconfig.models import SiteConfiguration

from reviewboard.accounts.backends import X509Backend


def timezone_middleware(get_response):
    """Middleware that activates the user's local timezone.

    Args:
        get_response (callable):
            The method to execute the view.
    """
    def middleware(request):
        """Activate the user's selected timezone for this request.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

        Returns:
            django.http.HttpResponse:
            The response object.
        """
        if request.user.is_authenticated:
            try:
                user = request.user.get_profile()
                timezone.activate(pytz.timezone(user.timezone))
            except pytz.UnknownTimeZoneError:
                pass

        return get_response(request)

    return middleware


def update_last_login_middleware(get_response):
    """Middleware that updates a user's last login time more frequently.

    This will update the user's stored login time if it's been more than 30
    minutes since they last made a request. This helps turn the login time into
    a recent activity time, providing a better sense of how often people are
    actively using Review Board.

    Args:
        get_response (callable):
            The method to execute the view.
    """
    #: The smallest period of time between login time updates.
    UPDATE_PERIOD_SECS = 30 * 60  # 30 minutes

    def middleware(request):
        """Process the request and update the login time.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

        Returns:
            django.http.HttpResponse:
            The response object.
        """
        user = request.user

        if user.is_authenticated:
            now = timezone.now()
            delta = now - request.user.last_login

            if delta.total_seconds() >= UPDATE_PERIOD_SECS:
                user.last_login = now
                user.save(update_fields=('last_login',))

        return get_response(request)

    return middleware


def x509_auth_middleware(get_response):
    """Middleware that authenticates a user using X.509 certificates.

    If Review Board is configured to use the X.509 authentication backend, this
    will automatically authenticate the user using the environment variables
    set by mod_ssl.

    Apache needs to be configured with mod_ssl. For Review Board to be usable
    with X.509 client certificate authentication, the ``SSLVerifyClient``
    configuration directive should be set to ``optional``. This will ensure
    that basic authentication will still work, allowing clients to work with a
    username and password.

    Args:
        get_response (callable):
            The method to execute the view.
    """
    def middleware(request):
        """Log in users by their certificate if using X.509 authentication.

        This will only log in a user if the request environment (*not* the
        headers) are populated with a pre-verified username, and the request
        is being handled over HTTPS.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

        Returns:
            django.http.HttpResponse:
            The response object.
        """
        siteconfig = SiteConfiguration.objects.get_current()

        if (request.is_secure() and
            siteconfig.get('auth_backend') == X509Backend.backend_id):
            x509_settings_field = getattr(settings, 'X509_USERNAME_FIELD',
                                          None)

            if x509_settings_field == 'CUSTOM':
                x509_settings_field = getattr(settings,
                                              'X509_CUSTOM_USERNAME_FIELD',
                                              None)

            if x509_settings_field:
                x509_field = request.environ.get(x509_settings_field)

                if x509_field:
                    user = auth.authenticate(request=request,
                                             x509_field=x509_field)

                    if user:
                        request.user = user
                        auth.login(request, user)

        return get_response(request)

    return middleware
