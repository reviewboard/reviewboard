#
# auth.py -- Authentication helpers for webapi
#
# Copyright (c) 2007-2009  Christian Hammond
# Copyright (c) 2007-2009  David Trowbridge
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

from __future__ import unicode_literals

import logging
import re

from django.conf import settings
from django.contrib import auth
from django.core.exceptions import ImproperlyConfigured
from django.utils import six
from django.views.decorators.http import require_POST

from djblets.webapi.decorators import webapi
from djblets.webapi.errors import LOGIN_FAILED
from djblets.webapi.responses import WebAPIResponse, WebAPIResponseError


_auth_backends = []


class WebAPIAuthBackend(object):
    """Handles a form of authentication for the web API.

    This can be overridden to provide custom forms of authentication, or to
    support multiple types of authentication.

    More than one authentication backend can be used with the web API. In that
    case, the client can make the determination about which to use.

    Auth backends generally need to only override the `get_credentials`
    method, though more specialized ones may override other methods as well.

    They must also provide `www_auth_scheme` which is a WWW-Authenticate
    scheme value.
    """
    www_auth_scheme = None

    SENSITIVE_CREDENTIALS_RE = \
        re.compile('api|token|key|secret|password|signature', re.I)

    def get_auth_headers(self, request):
        """Returns extra authentication headers for the response."""
        return {}

    def authenticate(self, request):
        """Authenticates a request against this auth backend.

        This will fetch the credentials and attempt an authentication against
        those credentials.

        This function must return None to indicate it should be skipped
        and another backend should be tried, or a tuple indicating the
        success/failure and additional details for the client.

        The tuple is in the form of:

            (is_successful, error_message, headers)

        The error message and headers can be None to use the default error
        message and headers from the LOGIN_FAILED error. In most cases,
        they should be None, unless there are more specific instructions
        needed for authenticating.
        """
        credentials = self.get_credentials(request)

        if not credentials:
            return None

        if isinstance(credentials, dict):
            result = self.login_with_credentials(request, **credentials)
        else:
            assert isinstance(credentials, tuple)
            result = credentials

        return result

    def get_credentials(self, request):
        """Returns credentials provided in the request.

        This returns a dictionary of all credentials necessary for this
        auth backend. By default, this expects 'username' and 'password',
        though more specialized auth backends may provide other information.
        These credentials will be passed to `login_with_credentials`.

        This function must be implemented by the subclass.
        """
        raise NotImplementedError

    def login_with_credentials(self, request, **credentials):
        """Logs in against the main authentication backends.

        This takes the provided credentials from the request (as returned by
        `get_credentials`) and attempts a login against the main
        authentication backends used by Django.
        """
        result = self.validate_credentials(request, **credentials)

        if result is not None:
            return result

        log_extra = {
            'request': request,
        }

        cleaned_credentials = self.clean_credentials_for_display(credentials)
        logging.debug(
            'Attempting authentication on API: %s',
            ', '.join([
                '%s=%s' % pair
                for pair in six.iteritems(cleaned_credentials)
            ]),
            extra=log_extra)

        user = auth.authenticate(**credentials)

        if user and user.is_active:
            auth.login(request, user)

            return True, None, None

        logging.debug("API Login failed. No valid user found.",
                      extra=log_extra)
        auth.logout(request)

        return False, None, None

    def validate_credentials(self, request, **credentials):
        """Validates that credentials are valid.

        This is called before we attempt to authenticate with the credentials,
        and can short-circuit the rest of the authentication process,
        returning a result tuple if desired. If None is returned,
        authentication proceeds as normal.

        By default, this will attempt to bypass authentication if the
        current user is already logged in and matches the authenticated
        user (if and only if 'username' appears in the credentials).

        Subclasses can override this to provide more specific behavior for
        their sets of credentials, or to disable this entirely.
        """
        # Don't authenticate if a user is already logged in and the
        # username matches.
        #
        # Note that this does mean that a new password will fail. However,
        # the user is already logged in, and querying the backend for every
        # request is excessive, so it's a tradeoff. The user already has
        # access to the server at this point anyway.
        if (request.user.is_authenticated() and
            request.user.username == credentials.get('username')):
            return True, None, None

        return None

    def clean_credentials_for_display(self, credentials):
        """Cleans up a credentials dictionary, removing sensitive information.

        This will take a credentials dictionary and mask anything sensitive,
        preparing it for output to a log file.
        """
        clean_credentials = {}

        for key, value in six.iteritems(credentials):
            if self.SENSITIVE_CREDENTIALS_RE.search(key):
                clean_credentials[key] = '************'
            else:
                clean_credentials[key] = value

        return clean_credentials


class WebAPIBasicAuthBackend(WebAPIAuthBackend):
    """Handles HTTP Basic Authentication for the web API."""
    www_auth_scheme = 'Basic realm="Web API"'

    def get_credentials(self, request):
        parts = request.META['HTTP_AUTHORIZATION'].split(' ')
        realm = parts[0]

        if realm != 'Basic':
            return None

        try:
            encoded_auth = parts[1]
            username, password = encoded_auth.decode('base64').split(':', 1)
        except Exception:
            logging.warning("Failed to parse HTTP_AUTHORIZATION header %s" %
                            request.META['HTTP_AUTHORIZATION'],
                            exc_info=1,
                            extra={'request': request})
            return None

        return {
            'username': username,
            'password': password,
        }


def check_login(request):
    """Checks if a login request was made.

    If the client specifies a HTTP_AUTHORIZATION header, this will attempt
    to authenticate using a supported authentication method.
    """
    if 'HTTP_AUTHORIZATION' in request.META:
        for auth_backend_cls in get_auth_backends():
            result = auth_backend_cls().authenticate(request)

            if result is not None:
                return result

    return None


def get_auth_backends():
    """Returns the list of web API authentication backends.

    This defaults to WebAPIBasicAuthBackend, for HTTP Basic Auth, but can be
    overridden by setting settings.WEB_API_AUTH_BACKENDS to a list of
    class paths.
    """
    global _auth_backends

    if not _auth_backends:
        class_paths = getattr(
            settings, 'WEB_API_AUTH_BACKENDS', [
                'djblets.webapi.auth.WebAPIBasicAuthBackend',
            ])

        _auth_backends = []

        for class_path in class_paths:
            i = class_path.rfind('.')
            module, attr = class_path[:i], class_path[i + 1:]

            try:
                mod = __import__(module, {}, {}, [attr])
            except ImportError as e:
                raise ImproperlyConfigured(
                    'Error importing web API auth backend %s: %s'
                    % (module, e))

            try:
                _auth_backends.append(getattr(mod, attr))
            except AttributeError:
                raise ImproperlyConfigured(
                    'Module "%s" does not define a "%s" class for the web API '
                    'auth backend'
                    % (module, attr))

    return _auth_backends


def reset_auth_backends():
    """Resets the list of authentication backends.

    The list will be recomputed the next time an authentication backend needs
    to be used.
    """
    global _auth_backends

    _auth_backends = []


@require_POST
@webapi
def account_login(request, *args, **kwargs):
    username = request.POST.get('username', None)
    password = request.POST.get('password', None)

    user = auth.authenticate(username=username, password=password)

    if not user or not user.is_active:
        return WebAPIResponseError(request, LOGIN_FAILED)

    auth.login(request, user)

    return WebAPIResponse(request)


@webapi
def account_logout(request, *args, **kwargs):
    auth.logout(request)
    return WebAPIResponse(request)
