from djblets.siteconfig.models import SiteConfiguration
from djblets.util.decorators import simple_decorator
from djblets.webapi.core import WebAPIResponse, WebAPIResponseError
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
            return webapi_login_required(view_func)(request,
                                                    api_format=api_format,
                                                    *args, **kwargs)
        else:
            return view_func(request, *args, **kwargs)

    return _check


def webapi_deprecated(deprecated_in, force_error_http_status=None):
    """Marks an API handler as deprecated.

    ``deprecated_in`` specifies the version that first deprecates this call.

    ``force_error_http_status`` forces errors to use the specified HTTP
    status code.
    """
    def _dec(view_func):
        def _view(*args, **kwargs):
            response = view_func(*args, **kwargs)

            if isinstance(response, WebAPIResponseError):
                response.api_data['deprecated'] = {
                    'in_version': deprecated_in,
                }

                if (force_error_http_status and
                    isinstance(response, WebAPIResponseError)):
                    response.status_code = force_error_http_status

            return response

        return _view

    return _dec


def webapi_deprecated_in_1_5(view_func):
    return webapi_deprecated(deprecated_in='1.5',
                             force_error_http_status=200)(view_func)
