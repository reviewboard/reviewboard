from __future__ import unicode_literals

import logging

from django.http import HttpRequest
from djblets.db.query import get_object_or_none
from djblets.siteconfig.models import SiteConfiguration
from djblets.webapi.decorators import (webapi_decorator,
                                       webapi_login_required,
                                       webapi_response_errors,
                                       _find_httprequest)
from djblets.webapi.errors import (DOES_NOT_EXIST,
                                   NOT_LOGGED_IN,
                                   OAUTH_ACCESS_DENIED_ERROR,
                                   OAUTH_MISSING_SCOPE_ERROR,
                                   PERMISSION_DENIED)
from djblets.webapi.responses import WebAPIResponse, WebAPIResponseError

from reviewboard.site.models import LocalSite


logger = logging.getLogger(__name__)


@webapi_decorator
def webapi_check_login_required(view_func):
    """
    A decorator that checks whether login is required on this installation
    and, if so, checks if the user is logged in. If login is required and
    the user is not logged in, they'll get a NOT_LOGGED_IN error.
    """
    @webapi_response_errors(NOT_LOGGED_IN)
    def _check(*args, **kwargs):
        siteconfig = SiteConfiguration.objects.get_current()
        request = _find_httprequest(args)

        if (siteconfig.get("auth_require_sitewide_login") or
            (request.user.is_anonymous() and
             'HTTP_AUTHORIZATION' in request.META)):
            return webapi_login_required(view_func)(*args, **kwargs)
        else:
            return view_func(*args, **kwargs)

    _check.checks_login_required = True

    return _check


def webapi_deprecated(deprecated_in, force_error_http_status=None,
                      default_api_format=None, encoders=[]):
    """Marks an API handler as deprecated.

    ``deprecated_in`` specifies the version that first deprecates this call.

    ``force_error_http_status`` forces errors to use the specified HTTP
    status code.

    ``default_api_format`` specifies the default api format (json or xml)
    if one isn't provided.
    """
    def _dec(view_func):
        def _view(*args, **kwargs):
            if default_api_format:
                request = args[0]
                assert isinstance(request, HttpRequest)

                method_args = getattr(request, request.method, None)

                if method_args and 'api_format' not in method_args:
                    method_args = method_args.copy()
                    method_args['api_format'] = default_api_format
                    setattr(request, request.method, method_args)

            response = view_func(*args, **kwargs)

            if isinstance(response, WebAPIResponse):
                response.encoders = encoders

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


@webapi_decorator
def webapi_check_local_site(view_func):
    """Checks whether a user has access to a local site given in the URL.

    This decorator can be added to get/get_list methods to check whether or not
    a user should be able to view them given the local site name in the URL.
    """
    @webapi_response_errors(DOES_NOT_EXIST, NOT_LOGGED_IN,
                            OAUTH_ACCESS_DENIED_ERROR,
                            OAUTH_MISSING_SCOPE_ERROR, PERMISSION_DENIED)
    def _check(*args, **kwargs):
        request = _find_httprequest(args)
        local_site_name = kwargs.get('local_site_name', None)
        webapi_token = getattr(request, '_webapi_token', None)
        oauth_token = getattr(request, '_oauth2_token', None)

        if webapi_token:
            restrict_to_local_site = request._webapi_token.local_site_id
            token_type = 'API'
        elif oauth_token:
            restrict_to_local_site = oauth_token.application.local_site_id
            token_type = 'OAuth'
        else:
            restrict_to_local_site = None
            token_type = None

        if local_site_name:
            local_site = get_object_or_none(LocalSite, name=local_site_name)

            if not local_site:
                return DOES_NOT_EXIST
            elif not local_site.is_accessible_by(request.user):
                if request.user.is_authenticated():
                    logger.warning(
                        'User does not have access to local site.',
                        request=request,
                    )
                    return PERMISSION_DENIED
                else:
                    return NOT_LOGGED_IN
            elif oauth_token and not oauth_token.application.enabled:
                logger.warning(
                    'OAuth token using disabled application "%s" (%d).',
                    oauth_token.application.name,
                    oauth_token.application.pk,
                    request=request,
                )
                return PERMISSION_DENIED
            elif oauth_token and not restrict_to_local_site:
                # OAuth tokens for applications on the global site cannot be
                # used on a local site.
                logger.warning(
                    'OAuth token is for root, not local site.',
                    request=request,
                )
                return PERMISSION_DENIED
            elif (restrict_to_local_site and
                  restrict_to_local_site != local_site.pk):
                logger.warning(
                    '%s token does not have access to local site.',
                    token_type,
                    request=request,
                )
                return PERMISSION_DENIED

            kwargs['local_site'] = local_site
        elif restrict_to_local_site is not None:
            logger.warning(
                '%s token is limited to a local site but the request was for '
                'the root.',
                token_type,
                request=request,
            )
            return PERMISSION_DENIED
        else:
            kwargs['local_site'] = None

        return view_func(*args, **kwargs)

    _check.checks_local_site = True

    return _check
