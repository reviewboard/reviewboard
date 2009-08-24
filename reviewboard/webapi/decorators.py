from djblets.siteconfig.models import SiteConfiguration
from djblets.util.decorators import simple_decorator
from djblets.webapi.decorators import webapi_login_required


@simple_decorator
def webapi_check_login_required(view_func):
    """
    A decorator that checks whether login is required on this installation
    and, if so, checks if the user is logged in. If login is required and
    the user is not logged in, they'll get a NOT_LOGGED_IN error.
    """
    def _check(request, api_format="json", *args, **kwargs):
        siteconfig = SiteConfiguration.objects.get_current()

        if siteconfig.get("auth_require_sitewide_login"):
            return webapi_login_required(view_func)(request, api_format,
                                                    *args, **kwargs)
        else:
            return view_func(request, *args, **kwargs)

    return _check
