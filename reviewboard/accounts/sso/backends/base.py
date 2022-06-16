"""Base classes for SSO backends.

Version Added:
    5.0
"""

from django.contrib import auth
from djblets.siteconfig.models import SiteConfiguration

from reviewboard.accounts.backends import StandardAuthBackend


class BaseSSOBackend(object):
    """Base class for SSO backends.

    Version Added:
        5.0
    """

    #: The ID of this SSO backend.
    #:
    #: Type:
    #:     str
    backend_id = None

    #: The name of this SSO backend.
    #:
    #: Type:
    #:     str
    name = None

    #: The form used for settings.
    #:
    #: This must be a subclass of
    #: :py:class:`~djblets.siteconfig.forms.SiteSettingsForm`.
    #:
    #: Type:
    #:     type
    settings_form = None

    #: The defaults for siteconfig entries.
    #:
    #: Type:
    #:     dict
    siteconfig_defaults = {}

    #: The text to show in the label for the login button.
    #:
    #: Type:
    #:     str
    login_label = None

    #: The URL to the login flow.
    #:
    #: Type:
    #:     str
    login_url = None

    #: The class type for the view handling the initial login request.
    #:
    #: Type:
    #:     type
    login_view_cls = None

    #: A list of URLs to register.
    #:
    #: Type:
    #:     list
    urls = []

    def __init__(self):
        """Initialize the SSO backend."""

    def is_available(self):
        """Return whether this backend is available.

        Returns:
            tuple:
            A two-tuple. The items in the tuple are:

            1. A bool indicating whether the backend is available.
            2. If the first element is ``False``, this will be a user-visible
               string indicating the reason why the backend is not available.
               If the backend is available, this element will be ``None``.
        """
        raise NotImplementedError

    def is_enabled(self):
        """Return whether this backend is enabled.

        Returns:
            bool:
            ``True`` if this SSO backend is enabled.
        """
        siteconfig = SiteConfiguration.objects.get_current()
        return siteconfig.get('%s_enabled' % self.backend_id, False)

    def login_user(self, request, user):
        """Log in the given user.

        Args:
            request (django.http.HttpRequest):
                The HTTP request.

            user (django.contrib.auth.models.User):
                The user to log in.
        """
        user.backend = '%s.%s' % (StandardAuthBackend.__module__,
                                  StandardAuthBackend.__name__)
        auth.login(request, user)
