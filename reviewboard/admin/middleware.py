from django.conf import settings

from reviewboard.admin.checks import check_updates_required
from reviewboard.admin.siteconfig import load_site_config
from reviewboard.admin.views import manual_updates_required
from reviewboard.webapi.json import service_not_configured


class LoadSettingsMiddleware:
    """
    Middleware that loads the settings on each request.
    """
    def process_request(self, request):
        # Load all site settings.
        load_site_config()


class CheckUpdatesRequiredMiddleware:
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
            if path_info.startswith(settings.SITE_ROOT + "api/"):
                return service_not_configured(request)

            return manual_updates_required(request)

        # Let another handler handle this.
        return None
