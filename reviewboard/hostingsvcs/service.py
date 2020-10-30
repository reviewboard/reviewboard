"""The base hosting service class and associated definitions."""

from __future__ import unicode_literals

import base64
import hashlib
import json
import logging
import re
import ssl
from collections import OrderedDict
from email.generator import _make_boundary as generate_boundary

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from django.conf.urls import include, url
from django.dispatch import receiver
from django.utils import six
from django.utils.encoding import force_bytes, force_str, force_text
from django.utils.six.moves.urllib.error import URLError
from django.utils.six.moves.urllib.parse import (parse_qs, urlencode,
                                                 urlparse, urlunparse)
from django.utils.six.moves.urllib.request import (
    Request as BaseURLRequest,
    HTTPBasicAuthHandler,
    HTTPDigestAuthHandler,
    HTTPPasswordMgrWithDefaultRealm,
    HTTPSHandler,
    build_opener)
from django.utils.translation import ugettext_lazy as _
from djblets.registries.errors import ItemLookupError
from djblets.registries.registry import (ALREADY_REGISTERED, LOAD_ENTRY_POINT,
                                         NOT_REGISTERED)
from djblets.util.decorators import cached_property

import reviewboard.hostingsvcs.urls as hostingsvcs_urls
from reviewboard.registries.registry import EntryPointRegistry
from reviewboard.scmtools.certs import Certificate
from reviewboard.scmtools.crypto_utils import decrypt_password
from reviewboard.scmtools.errors import UnverifiedCertificateError
from reviewboard.signals import initializing


logger = logging.getLogger(__name__)


def _log_and_raise(request, msg, **fmt_dict):
    """Log and raise an exception with the given message.

    This is used when validating data going into the request, and is
    intended to help with debugging bad calls to the HTTP code.

    Version Added:
        4.0

    Args:
        msg (unicode):
            The error message as a format string.

        **fmt_dict (dict):
            Values for the error message's format string.

    Raises:
        TypeError:
            The exception containing the provided message.
    """
    msg = msg % dict({
        'method': request.method,
        'service': type(request.hosting_service),
    }, **fmt_dict)

    logger.error(msg)
    raise TypeError(msg)


class HostingServiceHTTPRequest(object):
    """A request that can use any HTTP method.

    By default, the :py:class:`urllib2.Request` class only supports HTTP GET
    and HTTP POST methods. This subclass allows for any HTTP method to be
    specified for the request.

    Version Added:
        4.0

    Attributes:
        body (str):
            The request payload body.

        headers (dict):
            The headers to send in the request. Each key and value is a native
            string.

        hosting_service (reviewboard.hostingsvcs.service.HostingService):
            The hosting service this request is associated with.

        method (unicode):
            The HTTP method to perform.

        url (unicode):
            The URL the request is being made on.
    """

    def __init__(self, url, query=None, body=None, headers=None, method='GET',
                 hosting_service=None, **kwargs):
        """Initialize the request.

        Args:
            url (unicode):
                The URL to make the request against.

            query (dict, optional):
                Query arguments to add onto the URL. These will be mixed with
                any query arguments already in the URL, and the result will
                be applied in sorted order, for cross-Python compatibility.

            body (unicode or bytes, optional):
                The payload body for the request, if using a ``POST`` or
                ``PUT`` request.

            headers (dict, optional):
                Additional headers to attach to the request.

            method (unicode, optional):
                The request method. If not provided, it defaults to a ``GET``
                request.

            hosting_service (reviewboard.hostingsvcs.service.HostingService,
                             optional):
                The hosting service this request is associated with.

            **kwargs (dict, unused):
                Additional keyword arguments for the request. This is unused,
                but allows room for expansion by subclasses.
        """
        if body is not None and not isinstance(body, bytes):
            _log_and_raise(
                self,
                'Received non-bytes body for the HTTP request for '
                '%(service)r. This is likely an implementation problem. '
                'Please make sure only byte strings are sent for the request '
                'body.')

        self.headers = {}

        if headers:
            for key, value in six.iteritems(headers):
                self.add_header(key, value)

        if query:
            parsed_url = list(urlparse(url))
            new_query = parse_qs(parsed_url[4])
            new_query.update(query)

            parsed_url[4] = urlencode(
                OrderedDict(
                    pair
                    for pair in sorted(six.iteritems(new_query),
                                       key=lambda pair: pair[0])
                ),
                doseq=True)

            url = urlunparse(parsed_url)

        self.body = body
        self.url = url
        self.query = query
        self.method = method
        self.hosting_service = hosting_service

        self._urlopen_handlers = []

    @property
    def data(self):
        """The payload data for the request.

        Deprecated:
            4.0:
            This is deprecated in favor of the :py:attr:`body` attribute.
        """
        return self.body

    def add_header(self, name, value):
        """Add a header to the request.

        Args:
            name (unicode or bytes):
                The header name.

            value (unicode or bytes):
                The header value.
        """
        if (not isinstance(name, six.text_type) or
            not isinstance(value, six.text_type)):
            _log_and_raise(
                self,
                'Received non-Unicode header %(header)r (value=%(value)r) '
                'for the HTTP request for %(service)r. This is likely an '
                'implementation problem. Please make sure only Unicode '
                'strings are sent in request headers.',
                header=name,
                value=value)

        self.headers[force_str(name).capitalize()] = force_str(value)

    def get_header(self, name, default=None):
        """Return a header from the request.

        Args:
            name (unicode):
                The header name.

            default (unicode, optional):
                The default value if the header was not found.

        Returns:
            unicode:
            The header value.
        """
        assert isinstance(name, six.text_type), (
            '%s.get_header() requires a Unicode header name'
            % self.__name__)

        return self.headers.get(force_str(name).capitalize(), default)

    def add_basic_auth(self, username, password):
        """Add HTTP Basic Authentication headers to the request.

        Args:
            username (unicode or bytes):
                The username.

            password (unicode or bytes):
                The password.
        """
        if isinstance(username, six.text_type):
            username = username.encode('utf-8')

        if isinstance(password, six.text_type):
            password = password.encode('utf-8')

        auth = b'%s:%s' % (username, password)
        self.add_header(force_text(HTTPBasicAuthHandler.auth_header),
                        'Basic %s' % force_text(base64.b64encode(auth)))

    def add_digest_auth(self, username, password):
        """Add HTTP Digest Authentication support to the request.

        Args:
            username (unicode):
                The username.

            password (unicode):
                The password.
        """
        result = urlparse(self.url)
        top_level_url = '%s://%s' % (result.scheme, result.netloc)

        password_mgr = HTTPPasswordMgrWithDefaultRealm()
        password_mgr.add_password(None, top_level_url, username, password)

        self.add_urlopen_handler(HTTPDigestAuthHandler(password_mgr))

    def add_urlopen_handler(self, handler):
        """Add a handler to invoke for the urlopen call.

        Note:
            This is dependent on a :py:mod:`urllib2`-backed request. While
            that is the default today, it may not be in the future. This
            method should be used with the knowledge that it may someday be
            deprecated, or may not work at all with special subclasses.

        Args:
            handler (urllib2.BaseHandler):
                The handler to add.
        """
        self._urlopen_handlers.append(handler)

    def open(self):
        """Open the request to the server, returning the response.

        Returns:
            HostingServiceHTTPResponse:
            The response information from the server.

        Raises:
            urllib2.URLError:
                An error occurred talking to the server, or an HTTP error
                (400+) was returned.
        """
        request = BaseURLRequest(self.url, self.body, self.headers)
        request.get_method = lambda: self.method

        hosting_service = self.hosting_service

        if hosting_service and 'ssl_cert' in hosting_service.account.data:
            # create_default_context only exists in Python 2.7.9+. Using it
            # here should be fine, however, because accepting invalid or
            # self-signed certificates is only possible when running
            # against versions that have this (see the check for
            # create_default_context below).
            context = ssl.create_default_context()
            context.load_verify_locations(
                cadata=hosting_service.account.data['ssl_cert'])
            context.check_hostname = False

            self._urlopen_handlers.append(HTTPSHandler(context=context))

        opener = build_opener(*self._urlopen_handlers)
        response = opener.open(request)

        if hosting_service:
            response_cls = hosting_service.client.http_response_cls
        else:
            response_cls = HostingServiceHTTPResponse

        return response_cls(request=self,
                            url=response.geturl(),
                            data=response.read(),
                            headers=dict(response.headers),
                            status_code=response.getcode())


class HostingServiceHTTPResponse(object):
    """An HTTP response from the server.

    This stores the URL, payload data, headers, and status code from an
    HTTP response.

    It also emulates a 2-tuple, for compatibility with legacy
    (pre-Review Board 4.0) calls, when HTTP methods returned tuples of data
    and headers.

    Version Added:
        4.0

    Attributes:
        data (bytes):
            The response data.

        headers (dict):
            The response headers. Keys and values will be native strings.

            It's recommended to call :py:meth:`get_header` to request a header.

        request (HostingServiceHTTPRequest):
            The HTTP request this is in response to.

        status_code (int):
            The HTTP status code for the response.

        url (unicode):
            The URL providing the response.
    """

    def __init__(self, request, url, data, headers, status_code):
        """Initialize the response.

        Args:
            request (HostingServiceHTTPRequest):
                The request this is in response to.

            url (unicode):
                The URL serving the response. If redirected, this may differ
                from the request URL.

            data (bytes):
                The response payload.

            headers (dict):
                The response headers.

            status_code (int):
                The response HTTP status code.
        """
        self.request = request

        if data is not None and not isinstance(data, bytes):
            # HTTP response data will be in byte strings, unless something is
            # overridden. Users should never see this in production, but
            # it'll be confusing for development. Make sure developers see
            # this through both a log message and an exception.
            _log_and_raise(
                request,
                'Received non-byte data from the HTTP %(method)s request '
                'for %(service)r. This is likely an implementation '
                'problem in a unit test or subclass. Please make sure '
                'only byte strings are sent.')

        if headers is None:
            _log_and_raise(
                request,
                'Headers response for HTTP %(method)s request for '
                '%(service)r is None. This is likely an implementation '
                'problem in a unit test. Please make sure a dictionary '
                'is returned.')

        new_headers = {}

        for key, value in six.iteritems(headers):
            if not isinstance(key, str) or not isinstance(value, str):
                _log_and_raise(
                    request,
                    'Received non-native string header %(header)r from the '
                    'HTTP %(method)s request for %(service)r. This is likely '
                    'an implementation problem in a unit test. Please '
                    'make sure only native strings are sent.',
                    header=key)

            new_headers[key.capitalize()] = value

        self.url = url
        self.data = data
        self.headers = new_headers
        self.status_code = status_code

    @cached_property
    def json(self):
        """A JSON representation of the payload data.

        Raises:
            ValueError:
                The data is not valid JSON.
        """
        data = self.data

        if data:
            # There's actual data here, so parse it and return it.
            return json.loads(data.decode('utf-8'))

        # Return whatever falsey value we received.
        return data

    def get_header(self, name, default=None):
        """Return the value of a header as a Unicode string.

        This accepts a header name with any form of capitalization. The header
        name will be normalized.

        Args:
            name (unicode):
                The header name.

            default (unicode, optional):
                The default value if the header is not set.

        Returns:
            unicode:
            The resulting header value.
        """
        return force_text(self.headers.get(force_str(name.capitalize()),
                                           default))

    def __getitem__(self, i):
        """Return an indexed item from the response.

        This is used to emulate the older 2-tuple response returned by hosting
        service HTTP request methods.

        Args:
            i (int):
                The index of the item.

        Returns:
            object:
            The object at the specified index.

            If 0, this will return :py:attr:`data`.

            If 1, this will return :py:attr:`headers`.

        Raises:
            IndexError:
                An index other than 0 or 1 was requested.
        """
        if i == 0:
            return self.data
        elif i == 1:
            return self.headers
        else:
            raise IndexError


class HostingServiceClient(object):
    """Client for communicating with a hosting service's API.

    This implementation includes abstractions for performing HTTP operations,
    and wrappers for those to interpret responses as JSON data.

    HostingService subclasses can also include an override of this class to add
    additional checking (such as GitHub's checking of rate limit headers), or
    add higher-level API functionality.

    Attributes:
        hosting_service (HostingService):
            The hosting service that owns this client.
    """

    #: The HTTP request class to construct for HTTP requests.
    #:
    #: Subclasses can replace this if they need custom behavior when
    #: constructing or invoking the request.
    #:
    #: Version Added:
    #:     4.0
    http_request_cls = HostingServiceHTTPRequest

    #: The HTTP response class to construct HTTP responses.
    #:
    #: Subclasses can replace this if they need custom ways of formatting
    #: or interpreting response data.
    #:
    #: Version Added:
    #:     4.0
    http_response_cls = HostingServiceHTTPResponse

    #: Whether to add HTTP Basic Auth headers by default.
    #:
    #: By default, hosting services will support HTTP Basic Auth. This can be
    #: turned off if not needed.
    #:
    #: Version Added:
    #:     4.0
    use_http_basic_auth = True

    #: Whether to add HTTP Digest Auth headers by default.
    #:
    #: By default, hosting services will not support HTTP Digest Auth. This
    #: can be turned on if needed.
    #:
    #: Version Added:
    #:     4.0
    use_http_digest_auth = False

    def __init__(self, hosting_service):
        """Initialize the client.

        Args:
            hosting_service (HostingService):
                The hosting service that is using this client.
        """
        self.hosting_service = hosting_service

    #
    # HTTP utility methods
    #

    def http_delete(self, url, headers=None, *args, **kwargs):
        """Perform an HTTP DELETE on the given URL.

        Version Changed:
            4.0:
            This now returns a :py:class:`HostingServiceHTTPResponse` instead
            of a 2-tuple. The response can be treated as a 2-tuple for older
            code.

        Args:
            url (unicode):
                The URL to perform the request on.

            headers (dict, optional):
                Extra headers to include with the request.

            *args (tuple):
                Additional positional arguments to pass to
                :py:meth:`http_request`.

            **kwargs (dict):
                Additional keyword arguments to pass to
                :py:meth:`http_request`.

        Returns:
            HostingServiceHTTPResponse:
            The HTTP response for the request.

        Raises:
            reviewboard.hostingsvcs.errors.HostingServiceError:
                There was an error performing the request, and the error has
                been translated to a more specific hosting service error.

            urllib2.URLError:
                There was an error performing the request, and the result is
                a raw HTTP error.
        """
        return self.http_request(url=url,
                                 headers=headers,
                                 method='DELETE',
                                 **kwargs)

    def http_get(self, url, headers=None, *args, **kwargs):
        """Perform an HTTP GET on the given URL.

        Version Changed:
            4.0:
            This now returns a :py:class:`HostingServiceHTTPResponse` instead
            of a 2-tuple. The response can be treated as a 2-tuple for older
            code.

        Args:
            url (unicode):
                The URL to perform the request on.

            headers (dict, optional):
                Extra headers to include with the request.

            *args (tuple):
                Additional positional arguments to pass to
                :py:meth:`http_request`.

            **kwargs (dict):
                Additional keyword arguments to pass to
                :py:meth:`http_request`.

        Returns:
            HostingServiceHTTPResponse:
            The HTTP response for the request.

        Raises:
            reviewboard.hostingsvcs.errors.HostingServiceError:
                There was an error performing the request, and the error has
                been translated to a more specific hosting service error.

            urllib2.URLError:
                There was an error performing the request, and the result is
                a raw HTTP error.
        """
        return self.http_request(url=url,
                                 headers=headers,
                                 method='GET',
                                 **kwargs)

    def http_head(self, url, headers=None, *args, **kwargs):
        """Perform an HTTP HEAD on the given URL.

        Version Added:
            4.0

        Args:
            url (unicode):
                The URL to perform the request on.

            headers (dict, optional):
                Extra headers to include with the request.

            *args (tuple):
                Additional positional arguments to pass to
                :py:meth:`http_request`.

            **kwargs (dict):
                Additional keyword arguments to pass to
                :py:meth:`http_request`.

        Returns:
            HostingServiceHTTPResponse:
            The HTTP response for the request.

        Raises:
            reviewboard.hostingsvcs.errors.HostingServiceError:
                There was an error performing the request, and the error has
                been translated to a more specific hosting service error.

            urllib2.URLError:
                There was an error performing the request, and the result is
                a raw HTTP error.
        """
        return self.http_request(url=url,
                                 headers=headers,
                                 method='HEAD',
                                 **kwargs)

    def http_post(self, url, body=None, fields=None, files=None,
                  content_type=None, headers=None, *args, **kwargs):
        """Perform an HTTP POST on the given URL.

        Version Changed:
            4.0:
            This now returns a :py:class:`HostingServiceHTTPResponse` instead
            of a 2-tuple. The response can be treated as a 2-tuple for older
            code.

        Args:
            url (unicode):
                The URL to perform the request on.

            body (bytes, optional):
                The request body. if not provided, it will be generated from
                the ``fields`` and ``files`` arguments.

            fields (dict, optional):
                Form fields to use to generate the request body. This argument
                will only be used if ``body`` is ``None``.

            files (dict, optional):
                Files to use to generate the request body. This argument will
                only be used if ``body`` is ``None``.

            content_type (unicode, optional):
                The content type of the request. If provided, it will be
                appended as the :mailheader:`Content-Type` header.

            headers (dict, optional):
                Extra headers to include with the request.

            *args (tuple):
                Additional positional arguments to pass to
                :py:meth:`http_request`.

            **kwargs (dict):
                Additional keyword arguments to pass to
                :py:meth:`http_request`.

        Returns:
            HostingServiceHTTPResponse:
            The HTTP response for the request.

        Raises:
            reviewboard.hostingsvcs.errors.HostingServiceError:
                There was an error performing the request, and the error has
                been translated to a more specific hosting service error.

            urllib2.URLError:
                There was an error performing the request, and the result is
                a raw HTTP error.
        """
        body, headers = self._build_put_post_request(body=body,
                                                     fields=fields,
                                                     files=files,
                                                     content_type=content_type,
                                                     headers=headers)

        return self.http_request(url=url,
                                 body=body,
                                 headers=headers,
                                 method='POST',
                                 **kwargs)

    def http_put(self, url, body=None, fields=None, files=None,
                 content_type=None, headers=None, *args, **kwargs):
        """Perform an HTTP PUT on the given URL.

        Version Added:
            4.0

        Args:
            url (unicode):
                The URL to perform the request on.

            body (bytes, optional):
                The request body. if not provided, it will be generated from
                the ``fields`` and ``files`` arguments.

            fields (dict, optional):
                Form fields to use to generate the request body. This argument
                will only be used if ``body`` is ``None``.

            files (dict, optional):
                Files to use to generate the request body. This argument will
                only be used if ``body`` is ``None``.

            content_type (unicode, optional):
                The content type of the request. If provided, it will be
                appended as the :mailheader:`Content-Type` header.

            headers (dict, optional):
                Extra headers to include with the request.

            *args (tuple):
                Additional positional arguments to pass to
                :py:meth:`http_request`.

            **kwargs (dict):
                Additional keyword arguments to pass to
                :py:meth:`http_request`.

        Returns:
            HostingServiceHTTPResponse:
            The HTTP response for the request.

        Raises:
            reviewboard.hostingsvcs.errors.HostingServiceError:
                There was an error performing the request, and the error has
                been translated to a more specific hosting service error.

            urllib2.URLError:
                There was an error performing the request, and the result is
                a raw HTTP error.
        """
        body, headers = self._build_put_post_request(body=body,
                                                     fields=fields,
                                                     files=files,
                                                     content_type=content_type,
                                                     headers=headers)

        return self.http_request(url=url,
                                 body=body,
                                 headers=headers,
                                 method='PUT',
                                 **kwargs)

    def http_request(self, url, body=None, headers=None, method='GET',
                     **kwargs):
        """Perform an HTTP request, processing and handling results.

        This constructs an HTTP request based on the specified criteria,
        returning the resulting data and headers or raising a suitable error.

        In most cases, callers will use one of the wrappers, like
        :py:meth:`http_get` or :py:meth:`http_post`. Calling this directly is
        useful if working with non-standard HTTP methods.

        Subclasses can control the behavior of HTTP requests through several
        related methods:

        * :py:meth:`get_http_credentials`
          - Return credentials for use in the HTTP request.

        * :py:meth:`build_http_request`
            - Build the :py:class:`HostingServiceHTTPRequest` object.

        * :py:meth:`open_http_request`
          - Performs the actual HTTP request.

        * :py:meth:`process_http_response`
          - Performs post-processing on a response from the service, or raises
            an error.

        * :py:meth:`process_http_error`
          - Processes a raised exception, handling it in some form or
            converting it into another error.

        See those methods for more information.

        Version Changed:
            4.0:
            This now returns a :py:class:`HostingServiceHTTPResponse` instead
            of a 2-tuple. The response can be treated as a 2-tuple for older
            code.

        Args:
            url (unicode):
                The URL to open.

            body (bytes, optional):
                The request body.

            headers (dict, optional):
                Headers to include in the request.

            method (unicode, optional):
                The HTTP method to use to perform the request.

            **kwargs (dict):
                Additional keyword arguments to pass to
                :py:meth:`build_http_request`.

        Returns:
            HostingServiceHTTPResponse:
            The HTTP response for the request.

        Raises:
            reviewboard.hostingsvcs.errors.HostingServiceError:
                There was an error performing the request, and the error has
                been translated to a more specific hosting service error.

            urllib2.URLError:
                There was an error performing the request, and the result is
                a raw HTTP error.
        """
        credentials = self.get_http_credentials(
            account=self.hosting_service.account,
            **kwargs)

        request = self.build_http_request(url=url,
                                          body=body,
                                          headers=headers,
                                          method=method,
                                          credentials=credentials,
                                          **kwargs)

        try:
            return self.process_http_response(self.open_http_request(request))
        except URLError as e:
            # This will either raise, or it will return and we'll raise.
            self.process_http_error(request, e)

            raise

    def get_http_credentials(self, account, username=None, password=None,
                             **kwargs):
        """Return credentials used to authenticate with the service.

        Subclasses can override this to return credentials based on the
        account or the values passed in when performing the HTTP request.
        The resulting dictionary contains keys that will be processed in
        :py:meth:`build_http_request`.

        There are a few supported keys that subclasses will generally want
        to return:

        ``username``:
            The username, typically for use in HTTP Basic Auth or HTTP Digest
            Auth.

        ``password``:
            The accompanying password.

        ``header``:
            A dictionary of authentication headers to add to the request.

        By default, this will return a ``username`` and ``password`` based on
        the request (if those values are provided by the caller).

        Args:
            account (reviewboard.hostingsvcs.models.HostingServiceAccount):
                The stored authentication data for the service.

            username (unicode, optional):
                An explicit username passed by the caller. This will override
                the data stored in the account, if both a username and
                password are provided.

            password (unicode, optional):
                An explicit password passed by the caller. This will override
                the data stored in the account, if both a username and
                password are provided.

            **kwargs (dict, unused):
                Additional keyword arguments passed in when making the HTTP
                request.

        Returns:
            dict:
            A dictionary of credentials for the request.
        """
        if (username is None and
            password is None and
            'password' in account.data):
            username = account.username
            password = decrypt_password(account.data['password'])

        if username is not None and password is not None:
            return {
                'username': username,
                'password': password,
            }

        return {}

    def open_http_request(self, request):
        """Perform a raw HTTP request and return the result.

        This is not meant to be called directly. Please use one of the
        following methods instead:

        * :py:meth:`http_delete`
        * :py:meth:`http_get`
        * :py:meth:`http_head`
        * :py:meth:`http_post`
        * :py:meth:`http_put`
        * :py:meth:`http_request`

        Args:
            request (HostingServiceHTTPRequest):
                The HTTP request to open.

        Returns:
            HostingServiceHTTPResponse:
            The successful response information from the server.

        Raises:
            urllib2.URLError:
                There was an error performing a request on the URL.
        """
        return request.open()

    def build_http_request(self, credentials, **kwargs):
        """Build a request object for an HTTP request.

        This constructs a :py:class:`HostingServiceHTTPRequest` containing
        the information needed to perform the HTTP request by passing the
        provided keyword arguments to the the constructor.

        If ``username`` and ``password`` are provided in ``credentials``, this
        will also add a HTTP Basic Auth header (if
        :py:attr:`use_http_basic_auth` is set) and HTTP Digest Auth Header (if
        :py:attr:`use_http_digest_auth` is set).

        Subclasses can override this to change any behavior as needed. For
        instance, adding other headers or authentication schemes.

        Args:
            credentials (dict):
                The credentials used for the request.

            **kwargs (dict, unused):
                Keyword arguments for the :py:class:`HostingServiceHTTPRequest`
                instance.

        Returns:
            HostingServiceHTTPRequest:
            The resulting request object for use in the HTTP request.
        """
        request = self.http_request_cls(hosting_service=self.hosting_service,
                                        **kwargs)

        if credentials:
            username = credentials.get('username')
            password = credentials.get('password')

            if username is not None and password is not None:
                if self.use_http_basic_auth:
                    request.add_basic_auth(username, password)

                if self.use_http_digest_auth:
                    request.add_digest_auth(username, password)

            auth_headers = credentials.get('headers') or {}

            for header, value in six.iteritems(auth_headers):
                request.add_header(header, value)

        return request

    def process_http_response(self, response):
        """Process an HTTP response and return a result.

        This can be used by subclasses to modify a response before it gets
        back to the caller. It can also raise a :py:class:`urllib2.URLError`
        (which will get processed by :py:meth:`process_http_error`), or a
        :py:class:`~reviewboard.hostingsvcs.errors.HostingServiceError`.

        By default, the response is returned as-is.

        Args:
            response (HostingServiceHTTPResponse):
                The response to process.

        Returns:
            HostingServiceHTTPResponse:
            The resulting response.
        """
        return response

    def process_http_error(self, request, e):
        """Process an HTTP error, possibly raising a result.

        This will look at the error, possibly raising a more suitable exception
        in its place. By default, it supports handling SSL signature
        verification failures.

        Subclasses can override this to provide more specific errors as needed
        by the hosting service implementation. They should always call the
        parent method as well.

        If there's no specific exception, this should just return, allowing
        the original exception to be raised.

        Args:
            request (HostingServiceHTTPRequest):
                The request that resulted in an error.

            e (urllib2.URLError):
                The error to process.

        Raises:
            reviewboard.scmtools.errors.UnverifiedCertificateError:
                The SSL certificate was not able to be verified.
        """
        if ('CERTIFICATE_VERIFY_FAILED' not in six.text_type(e) or
            not hasattr(ssl, 'create_default_context')):
            return

        parts = urlparse(request.url)
        port = parts.port or 443

        cert_pem = ssl.get_server_certificate((parts.hostname, port))
        cert_der = ssl.PEM_cert_to_DER_cert(cert_pem)

        cert = x509.load_pem_x509_certificate(cert_pem.encode('ascii'),
                                              default_backend())
        issuer = cert.issuer.get_attributes_for_oid(
            x509.oid.NameOID.COMMON_NAME)[0].value
        subject = cert.subject.get_attributes_for_oid(
            x509.oid.NameOID.COMMON_NAME)[0].value

        raise UnverifiedCertificateError(
            Certificate(
                pem_data=cert_pem,
                valid_from=cert.not_valid_before.isoformat(),
                valid_until=cert.not_valid_after.isoformat(),
                issuer=issuer,
                hostname=subject,
                fingerprint=hashlib.sha256(cert_der).hexdigest()))

    #
    # JSON utility methods
    #

    def json_delete(self, *args, **kwargs):
        """Perform an HTTP DELETE and interpret the results as JSON.

        Deprecated:
            4.0:
            Use :py:meth:`http_delete` instead, and access the
            :py:attr:`~HostingServiceHTTPResponse.json` attribute on the
            response for the JSON payload.

        Args:
            *args (tuple):
                Additional positional arguments to pass to
                :py:meth:`http_delete`.

            **kwargs (dict):
                Additional keyword arguments to pass to
                :py:meth:`http_delete`.

        Returns:
            tuple:
            A tuple of:

            * The JSON data (in the appropriate type)
            * The response headers (:py:class:`dict`)

        Raises:
            reviewboard.hostingsvcs.errors.HostingServiceError:
                There was an error performing the request, and the error has
                been translated to a more specific hosting service error.

            urllib2.URLError:
                When there is an error communicating with the URL.
        """
        return self._do_json_method(self.http_delete, *args, **kwargs)

    def json_get(self, *args, **kwargs):
        """Perform an HTTP GET and interpret the results as JSON.

        Deprecated:
            4.0:
            Use :py:meth:`http_get` instead, and access the
            :py:attr:`~HostingServiceHTTPResponse.json` attribute on the
            response for the JSON payload.

        Args:
            *args (tuple):
                Additional positional arguments to pass to
                :py:meth:`http_get`.

            **kwargs (dict):
                Additional keyword arguments to pass to
                :py:meth:`http_get`.

        Returns:
            tuple:
            A tuple of:

            * The JSON data (in the appropriate type)
            * The response headers (:py:class:`dict`)

        Raises:
            reviewboard.hostingsvcs.errors.HostingServiceError:
                There was an error performing the request, and the error has
                been translated to a more specific hosting service error.

            urllib2.URLError:
                When there is an error communicating with the URL.
        """
        return self._do_json_method(self.http_get, *args, **kwargs)

    def json_post(self, *args, **kwargs):
        """Perform an HTTP POST and interpret the results as JSON.

        Deprecated:
            4.0:
            Use :py:meth:`http_post` instead, and access the
            :py:attr:`~HostingServiceHTTPResponse.json` attribute on the
            response for the JSON payload.

        Args:
            *args (tuple):
                Additional positional arguments to pass to
                :py:meth:`http_post`.

            **kwargs (dict):
                Additional keyword arguments to pass to
                :py:meth:`http_post`.

        Returns:
            tuple:
            A tuple of:

            * The JSON data (in the appropriate type)
            * The response headers (:py:class:`dict`)

        Raises:
            reviewboard.hostingsvcs.errors.HostingServiceError:
                There was an error performing the request, and the error has
                been translated to a more specific hosting service error.

            urllib2.URLError:
                When there is an error communicating with the URL.
        """
        return self._do_json_method(self.http_post, *args, **kwargs)

    def _do_json_method(self, method, *args, **kwargs):
        """Parse the result of an HTTP operation as JSON.

        Deprecated:
            4.0:
            Use :py:meth:`http_post` instead, and access the
            :py:attr:`~HostingServiceHTTPResponse.json` attribute on the
            response for the JSON payload.

        Args:
            method (callable):
                The callable to use to execute the request.

            *args (tuple):
                Positional arguments to pass to ``method``.

            **kwargs (dict):
                Keyword arguments to pass to ``method``.

        Returns:
            tuple:
            A tuple of:

            * The JSON data (in the appropriate type)
            * The response headers (:py:class:`dict`)

        Raises:
            reviewboard.hostingsvcs.errors.HostingServiceError:
                There was an error performing the request, and the error has
                been translated to a more specific hosting service error.

            urllib2.URLError:
                When there is an error communicating with the URL.
        """
        response = method(*args, **kwargs)

        if isinstance(response, HostingServiceHTTPResponse):
            return response.json, response.headers
        elif isinstance(response, tuple):
            data, headers = response

            if data:
                data = json.loads(data.decode('utf-8'))

            return data, headers
        else:
            raise NotImplementedError('Unsupported response from %r' % method)

    def _build_put_post_request(self, body=None, fields=None, files=None,
                                content_type=None, headers=None):
        """Build a request body and headers for a HTTP PUT or POST.

        Args:
            body (bytes, optional):
                The request body content.

            fields (dict, optional):
                The form fields used to construct a request body. This is
                ignored if ``body`` is set.

            files (dict, optional):
                The uploaded files used to construct a request body. This is
                ignored if ``body`` is set.

            content_type (unicode, optional):
                The value used for the ``Content-Type`` header.

            headers (dict, optional):
                Additional headers to set in the request.

        Returns:
            tuple:
            A 2-tuple of ``(body, headers)``.
        """
        if headers:
            headers = headers.copy()
        else:
            headers = {}

        if body is None:
            if fields is not None or files is not None:
                body, content_type = self.build_form_data(fields, files)
            else:
                body = b''
        else:
            body = force_bytes(body)

        if content_type:
            headers['Content-Type'] = content_type

        headers['Content-Length'] = '%d' % len(body)

        return body, headers

    #
    # Internal utilities
    #

    @staticmethod
    def build_form_data(fields, files=None):
        """Encode data for use in an HTTP POST.

        Args:
            fields (dict):
                A mapping of field names (:py:class:`unicode`) to values.

            files (dict, optional):
                A mapping of field names (:py:class:`unicode`) to files
                (:py:class:`dict`).

        Returns:
            tuple:
            A tuple of:

            * The request content (:py:class:`bytes`).
            * The request content type (:py:class:`unicode`).
        """
        boundary = HostingServiceClient._make_form_data_boundary()
        enc_boundary = boundary.encode('utf-8')
        content_parts = []

        if fields:
            for key, value in sorted(six.iteritems(fields),
                                     key=lambda pair: pair[0]):
                if isinstance(key, six.text_type):
                    key = key.encode('utf-8')

                if isinstance(value, six.text_type):
                    value = value.encode('utf-8')

                content_parts.append(
                    b'--%(boundary)s\r\n'
                    b'Content-Disposition: form-data; name="%(key)s"\r\n'
                    b'\r\n'
                    b'%(value)s\r\n'
                    % {
                        b'boundary': enc_boundary,
                        b'key': key,
                        b'value': value,
                    }
                )

        if files:
            for key, data in sorted(six.iteritems(files),
                                    key=lambda pair: pair[0]['filename']):
                filename = data['filename']
                content = data['content']

                if isinstance(key, six.text_type):
                    key = key.encode('utf-8')

                if isinstance(filename, six.text_type):
                    filename = filename.encode('utf-8')

                if isinstance(content, six.text_type):
                    content = content.encode('utf-8')

                content_parts.append(
                    b'--%(boundary)s\r\n'
                    b'Content-Disposition: form-data; name="%(key)s";'
                    b' filename="%(filename)s"\r\n'
                    b'\r\n'
                    b'%(value)s\r\n'
                    % {
                        b'boundary': enc_boundary,
                        b'key': key,
                        b'filename': filename,
                        b'value': content,
                    }
                )

        content_parts.append(b'--%s--' % enc_boundary)

        content = b''.join(content_parts)
        content_type = 'multipart/form-data; boundary=%s' % boundary

        return content, content_type

    @staticmethod
    def _make_form_data_boundary():
        """Return a unique boundary to use for HTTP form data.

        This primary exists for the purpose of spying in unit tests.

        Returns:
            bytes:
            The boundary for use in the form data.
        """
        return generate_boundary()


class HostingService(object):
    """An interface to a hosting service for repositories and bug trackers.

    HostingService subclasses are used to more easily configure repositories
    and to make use of third party APIs to perform special operations not
    otherwise usable by generic repositories.

    A HostingService can specify forms for repository and bug tracker
    configuration.

    It can also provide a list of repository "plans" (such as public
    repositories, private repositories, or other types available to the hosting
    service), along with configuration specific to the plan. These plans will
    be available when configuring the repository.
    """

    #: The unique ID of the hosting service.
    #:
    #: This should be lowercase, and only consist of the characters a-z, 0-9,
    #: ``_``, and ``-``.
    #:
    #: Version Added:
    #:     3.0.16:
    #:     This should now be set on all custom hosting services. It will be
    #:     required in Review Board 4.0.
    hosting_service_id = None

    name = None
    plans = None
    supports_bug_trackers = False
    supports_post_commit = False
    supports_repositories = False
    supports_ssh_key_association = False
    supports_two_factor_auth = False
    supports_list_remote_repositories = False
    has_repository_hook_instructions = False

    #: Whether this service should be shown as an available option.
    #:
    #: This should be set to ``False`` when a service is no longer available
    #: to use, and should be hidden from repository configuration. The
    #: implementation can then be largely stubbed out. Users will see a
    #: message in the repository configuration page.
    #:
    #: Version Added:
    #:     3.0.17
    visible = True

    self_hosted = False
    repository_url_patterns = None

    client_class = HostingServiceClient

    #: Optional form used to configure authentication settings for an account.
    auth_form = None

    # These values are defaults that can be overridden in repository_plans
    # above.
    needs_authorization = False
    form = None
    fields = []
    repository_fields = {}
    bug_tracker_field = None

    #: A list of SCMTools IDs or names that are supported by this service.
    #:
    #: This should contain a list of SCMTool IDs that this service can work
    #: with. For backwards-compatibility, it may instead contain a list of
    #: SCMTool names (corresponding to database registration names).
    #:
    #: This may also be specified per-plan in the :py:attr:`plans`.
    #:
    #: Version Changed:
    #:     3.0.16:
    #:     Added support for SCMTool IDs. A future version will deprecate
    #:     using SCMTool names here.
    supported_scmtools = []

    #: A list of SCMTool IDs that are visible when configuring the service.
    #:
    #: This should contain a list of SCMTool IDs that this service will show
    #: when configuring a repository. It can be used to offer continued
    #: legacy support for an SCMTool without offering it when creating new
    #: repositories. If not specified, all SCMTools listed
    #: in :py:attr:`supported_scmtools` are assumed to be visible.
    #:
    #: If explicitly set, this should always be equal to or a subset of
    #: :py:attr:`supported_scmtools`.
    #:
    #: This may also be specified per-plan in the :py:attr:`plans`.
    #:
    #: Version Added:
    #:     3.0.17
    visible_scmtools = None

    def __init__(self, account):
        """Initialize the hosting service.

        Args:
            account (reviewboard.hostingsvcs.models.HostingServiceAccount):
                The account to use with the service.
        """
        assert account
        self.account = account

        self.client = self.client_class(self)

    def is_authorized(self):
        """Return whether or not the account is currently authorized.

        An account may no longer be authorized if the hosting service
        switches to a new API that doesn't match the current authorization
        records. This function will determine whether the account is still
        considered authorized.

        Returns:
            bool:
            Whether or not the associated account is authorized.
        """
        return False

    def get_password(self):
        """Return the raw password for this hosting service.

        Not all hosting services provide this, and not all would need it.
        It's primarily used when building a Subversion client, or other
        SCMTools that still need direct access to the repository itself.

        Returns:
            unicode:
            The password.
        """
        return None

    def is_ssh_key_associated(self, repository, key):
        """Return whether or not the key is associated with the repository.

        If the given key is present amongst the hosting service's deploy keys
        for the given repository, then it is considered to be associated.

        Sub-classes should implement this when the hosting service supports
        SSH key association.

        Args:
            repository (reviewboard.scmtools.models.Repository):
                The repository the key must be associated with.

            key (paramiko.PKey):
                The key to check for association.

        Returns:
            bool:
            Whether or not the key is associated with the repository.

        Raises:
            reviewboard.hostingsvcs.errors.SSHKeyAssociationError:
                If an error occured during communication with the hosting
                service.
        """
        raise NotImplementedError

    def associate_ssh_key(self, repository, key):
        """Associate an SSH key with a given repository.

        Sub-classes should implement this when the hosting service supports
        SSH key association.

        Args:
            repository (reviewboard.scmtools.models.Repository):
                The repository to associate the key with.

            key (paramiko.PKey):
                The key to add to the repository's list of deploy keys.

        Raises:
            reviewboard.hostingsvcs.errors.SSHKeyAssociationError:
                If an error occured during key association.
        """
        raise NotImplementedError

    def authorize(self, username, password, hosting_url, credentials,
                  two_factor_auth_code=None, local_site_name=None,
                  *args, **kwargs):
        """Authorize an account for the hosting service.

        Args:
            username (unicode):
                The username for the account.

            password (unicode):
                The password for the account.

            hosting_url (unicode):
                The hosting URL for the service, if self-hosted.

            credentials (dict):
                All credentials provided by the authentication form. This
                will contain the username, password, and anything else
                provided by that form.

            two_factor_auth_code (unicode, optional):
                The two-factor authentication code provided by the user.

            local_site_name (unicode, optional):
                The Local Site name, if any, that the account should be
                bound to.

            *args (tuple):
                Extra unused positional arguments.

            **kwargs (dict):
                Extra keyword arguments containing values from the
                repository's configuration.

        Raises:
            reviewboard.hostingsvcs.errors.AuthorizationError:
                The credentials provided were not valid.

            reviewboard.hostingsvcs.errors.TwoFactorAuthCodeRequiredError:
                A two-factor authentication code is required to authorize
                this account. The request must be retried with the same
                credentials and with the ``two_factor_auth_code`` parameter
                provided.
        """
        raise NotImplementedError

    def check_repository(self, path, username, password, scmtool_class,
                         local_site_name, *args, **kwargs):
        """Checks the validity of a repository configuration.

        This performs a check against the hosting service or repository
        to ensure that the information provided by the user represents
        a valid repository.

        This is passed in the repository details, such as the path and
        raw credentials, as well as the SCMTool class being used, the
        LocalSite's name (if any), and all field data from the
        HostingServiceForm as keyword arguments.

        Args:
            path (unicode):
                The repository URL.

            username (unicode):
                The username to use.

            password (unicode):
                The password to use.

            scmtool_class (type):
                The subclass of :py:class:`~reviewboard.scmtools.core.SCMTool`
                that should be used.

            local_site_name (unicode):
                The name of the local site associated with the repository, or
                ``None``.

            *args (tuple):
                Additional positional arguments, unique to each hosting
                service.

            **kwargs (dict):
                Additional keyword arguments, unique to each hosting service.

        Raises:
            reviewboard.hostingsvcs.errors.RepositoryError:
                The repository is not valid.
        """
        scmtool_class.check_repository(path, username, password,
                                       local_site_name)

    def get_file(self, repository, path, revision, *args, **kwargs):
        """Return the requested file.

        Files can only be returned from hosting services that support
        repositories.

        Args:
            repository (reviewboard.scmtools.models.Repository):
                The repository to retrieve the file from.

            path (unicode):
                The file path.

            revision (unicode):
                The revision the file should be retrieved from.

            *args (tuple):
                Ignored positional arguments.

            **kwargs (dict):
                Additional keyword arguments to pass to the SCMTool.

        Returns:
            bytes:
            The contents of the file.

        Raises:
            NotImplementedError:
                If this hosting service does not support repositories.
        """
        if not self.supports_repositories:
            raise NotImplementedError

        return repository.get_scmtool().get_file(path, revision, **kwargs)

    def get_file_exists(self, repository, path, revision, *args, **kwargs):
        """Return whether or not the given path exists in the repository.

        Args:
            repository (reviewboard.scmtools.models.Repository):
                The repository to check for file existence.

            path (unicode):
                The file path.

            revision (unicode):
                The revision to check for file existence.

            *args (tuple):
                Ignored positional arguments.

            **kwargs (dict):
                Additional keyword arguments to be passed to the SCMTool.

        Returns:
            bool:
            Whether or not the file exists at the given revision in the
            repository.

        Raises:
            NotImplementedError:
                If this hosting service does not support repositories.
        """
        if not self.supports_repositories:
            raise NotImplementedError

        return repository.get_scmtool().file_exists(path, revision, **kwargs)

    def get_branches(self, repository):
        """Return a list of all branches in the repositories.

        This should be implemented by subclasses, and is expected to return a
        list of Branch objects. One (and only one) of those objects should have
        the "default" field set to True.

        Args:
            repository (reviewboard.scmtools.models.Repository):
                The repository for which branches should be returned.

        Returns:
            list of reviewboard.scmtools.core.Branch:
            The branches.

        Raises:
            reviewboard.hostingsvcs.errors.HostingServiceError:
                There was an error fetching branches.
        """
        raise NotImplementedError

    def get_commits(self, repository, branch=None, start=None):
        """Return a list of commits backward in history from a given point.

        This should be implemented by subclasses, and is expected to return a
        list of Commit objects (usually 30, but this is flexible depending on
        the limitations of the APIs provided.

        This can be called multiple times in succession using the "parent"
        field of the last entry as the start parameter in order to paginate
        through the history of commits in the repository.

        Args:
            repository (reviewboard.scmtools.models.Repository):
                The repository to retrieve commits from.

            branch (unicode, optional):
                The branch to retrieve from. If this is not provided, the
                default branch will be used.

            start (unicode, optional):
                An optional starting revision. If this is not provided, the
                most recent commits will be returned.

        Returns:
            list of reviewboard.scmtools.core.Commit:
            The retrieved commits.

        Raises:
            reviewboard.hostingsvcs.errors.HostingServiceError:
                There was an error fetching commits.
        """
        raise NotImplementedError

    def get_change(self, repository, revision):
        """Return an individual change.

        This method should be implemented by subclasses.

        Args:
            repository (reviewboard.scmtools.models.Repository):
                The repository to get the change from.

            revision (unicode):
                The revision to retrieve.

        Returns:
            reviewboard.scmtools.core.Commit:
            The change.

        Raises:
            reviewboard.hostingsvcs.errors.HostingServiceError:
                There was an error fetching the commit.
        """
        raise NotImplementedError

    def get_remote_repositories(self, owner=None, owner_type=None,
                                filter_type=None, start=None, per_page=None,
                                **kwargs):
        """Return a list of remote repositories for the owner.

        This method should be implemented by subclasses.

        Args:
            owner (unicode, optional):
                The owner of the repositories. This is usually a username.

            owner_type (unicode, optional):
                A hosting service-specific indicator of what the owner is (such
                as a user or a group).

            filter_type (unicode, optional):
                Some hosting service-specific criteria to filter by.

            start (int, optional):
                The index to start at.

            per_page (int, optional):
                The number of results per page.

        Returns:
            reviewboard.hostingsvcs.utils.APIPaginator:
            A paginator for the returned repositories.
        """
        raise NotImplementedError

    def get_remote_repository(self, repository_id):
        """Return the remote repository for the ID.

        This method should be implemented by subclasses.

        Args:
            repository_id (unicode):
                The repository's identifier. This is unique to each hosting
                service.

        Returns:
            reviewboard.hostingsvcs.repository.RemoteRepository:
            The remote repository.

        Raises:
            django.core.excptions.ObjectDoesNotExist:
                If the remote repository does not exist.
        """
        raise NotImplementedError

    def normalize_patch(self, repository, patch, filename, revision):
        """Normalize a diff/patch file before it's applied.

        This can be used to take an uploaded diff file and modify it so that
        it can be properly applied. This may, for instance, uncollapse
        keywords or remove metadata that would confuse :command:`patch`.

        By default, this passes along the normalization to the repository's
        :py:class:`~reviewboard.scmtools.core.SCMTool`.

        Args:
            repository (reviewboard.scmtools.models.Repository):
                The repository the patch is meant to apply to.

            patch (bytes):
                The diff/patch file to normalize.

            filename (unicode):
                The name of the file being changed in the diff.

            revision (unicode):
                The revision of the file being changed in the diff.

        Returns:
            bytes:
            The resulting diff/patch file.
        """
        return repository.get_scmtool().normalize_patch(patch=patch,
                                                        filename=filename,
                                                        revision=revision)


    @classmethod
    def get_repository_fields(cls, username, hosting_url, plan, tool_name,
                              field_vars):
        """Return the repository fields based on the given plan and tool.

        If the ``plan`` argument is specified, that will be used to fill in
        some tool-specific field values. Otherwise they will be retrieved from
        the :py:class:`HostingService`'s defaults.

        Args:
            username (unicode):
                The username.

            hosting_url (unicode):
                The URL of the repository.

            plan (unicode):
                The name of the plan.

            tool_name (unicode):
                The :py:attr:`~reviewboard.scmtools.core.SCMTool.name` of the
                :py:class:`~reviewboard.scmtools.core.SCMTool`.

            field_vars (dict):
                The field values from the hosting service form.

        Returns:
            dict:
            The filled in repository fields.

        Raises:
            KeyError:
               The provided plan is not valid for the hosting service.
        """
        if not cls.supports_repositories:
            raise NotImplementedError

        # Grab the list of fields for population below. We have to do this
        # differently depending on whether or not this hosting service has
        # different repository plans.
        fields = cls.get_field(plan, 'repository_fields')

        new_vars = field_vars.copy()
        new_vars['hosting_account_username'] = username

        if cls.self_hosted:
            new_vars['hosting_url'] = hosting_url
            new_vars['hosting_domain'] = urlparse(hosting_url)[1]

        results = {}

        assert tool_name in fields

        for field, value in six.iteritems(fields[tool_name]):
            try:
                results[field] = value % new_vars
            except KeyError as e:
                logger.exception('Failed to generate %s field for hosting '
                                 'service %s using %s and %r: Missing key %s',
                                 field, cls.name, value, new_vars, e)
                raise KeyError(
                    _('Internal error when generating %(field)s field '
                      '(Missing key "%(key)s"). Please report this.') % {
                        'field': field,
                        'key': e,
                    })

        return results

    def get_repository_hook_instructions(self, request, repository):
        """Return instructions for setting up incoming webhooks.

        Subclasses can override this (and set
        `has_repository_hook_instructions = True` on the subclass) to provide
        instructions that administrators can see when trying to configure an
        incoming webhook for the hosting service.

        Args:
            request (django.http.HttpRequest):
                The current HTTP request.

            repository (reviewboard.scmtools.models.Repository):
                The repository for webhook setup instructions.

        Returns:
            django.utils.text.SafeText:
            Rendered and escaped HTML for displaying to the user.
        """
        raise NotImplementedError

    @classmethod
    def get_bug_tracker_requires_username(cls, plan=None):
        """Return whether or not the bug tracker requires usernames.

        Args:
            plan (unicode, optional):
                The name of the plan associated with the account.

        Raises:
            NotImplementedError:
                If the hosting service does not support bug tracking.
        """
        if not cls.supports_bug_trackers:
            raise NotImplementedError

        return ('%(hosting_account_username)s' in
                cls.get_field(plan, 'bug_tracker_field', ''))

    @classmethod
    def get_bug_tracker_field(cls, plan, field_vars):
        """Return the bug tracker field for the given plan.

        Args:
            plan (unicode):
                The name of the plan associated with the account.

            field_vars (dict):
                The field values from the hosting service form.

        Returns:
            unicode:
            The value of the bug tracker field.

        Raises
            KeyError:
               The provided plan is not valid for the hosting service.
        """
        if not cls.supports_bug_trackers:
            raise NotImplementedError

        bug_tracker_field = cls.get_field(plan, 'bug_tracker_field')

        if not bug_tracker_field:
            return ''

        try:
            return bug_tracker_field % field_vars
        except KeyError as e:
            logger.exception('Failed to generate %s field for hosting '
                             'service %s using %r: Missing key %s',
                             bug_tracker_field, cls.name, field_vars, e)
            raise KeyError(
                _('Internal error when generating %(field)s field '
                  '(Missing key "%(key)s"). Please report this.') % {
                    'field': bug_tracker_field,
                    'key': e,
                })

    @classmethod
    def get_field(cls, plan, name, default=None):
        """Return the value of the field for the given plan.

        If ``plan`` is not ``None``, the field will be looked up in the plan
        configuration for the service. Otherwise the hosting service's default
        value will be used.

        Args:
            plan (unicode):
                The plan name.

            name (unicode):
                The field name.

            default (unicode, optional):
                A default value if the field is not present.

        Returns:
            unicode:
            The field value.
        """
        if cls.plans:
            assert plan

            for plan_name, info in cls.plans:
                if plan_name == plan and name in info:
                    return info[name]

        return getattr(cls, name, default)


_hostingsvcs_urlpatterns = {}


class HostingServiceRegistry(EntryPointRegistry):
    """A registry for managing hosting services."""

    entry_point = 'reviewboard.hosting_services'
    lookup_attrs = ['hosting_service_id']

    errors = {
        ALREADY_REGISTERED: _(
            '"%(item)s" is already a registered hosting service.'
        ),
        LOAD_ENTRY_POINT: _(
            'Unable to load repository hosting service %(entry_point)s: '
            '%(error)s.'
        ),
        NOT_REGISTERED: _(
            '"%(attr_value)s" is not a registered hosting service.'
        ),
    }

    def __init__(self):
        super(HostingServiceRegistry, self).__init__()
        self._url_patterns = {}

    def unregister(self, service):
        """Unregister a hosting service.

        This will remove all registered URLs that the hosting service has
        defined.

        Args:
            service (type):
                The
                :py:class:`~reviewboard.hostingsvcs.service.HostingService`
                subclass.
        """
        super(HostingServiceRegistry, self).unregister(service)

        if service.hosting_service_id in self._url_patterns:
            cls_urlpatterns = self._url_patterns[service.hosting_service_id]
            hostingsvcs_urls.dynamic_urls.remove_patterns(cls_urlpatterns)
            del self._url_patterns[service.hosting_service_id]

    def process_value_from_entry_point(self, entry_point):
        """Load the class from the entry point.

        The ``id`` attribute will be set on the class from the entry point's
        name.

        Args:
            entry_point (pkg_resources.EntryPoint):
                The entry point.

        Returns:
            type:
            The :py:class:`HostingService` subclass.
        """
        cls = entry_point.load()
        cls.hosting_service_id = entry_point.name
        return cls

    def register(self, service):
        """Register a hosting service.

        This also adds the URL patterns defined by the hosting service. If the
        hosting service has a :py:attr:`HostingService.repository_url_patterns`
        attribute that is non-``None``, they will be automatically added.

        Args:
            service (type):
                The :py:class:`HostingService` subclass.
        """
        super(HostingServiceRegistry, self).register(service)

        if service.repository_url_patterns:
            cls_urlpatterns = [
                url(r'^(?P<hosting_service_id>%s)/'
                    % re.escape(service.hosting_service_id),
                    include(service.repository_url_patterns)),
            ]

            self._url_patterns[service.hosting_service_id] = cls_urlpatterns
            hostingsvcs_urls.dynamic_urls.add_patterns(cls_urlpatterns)


_hosting_service_registry = HostingServiceRegistry()


def get_hosting_services():
    """Return the list of hosting services.

    Returns:
        list:
        The :py:class:`~reviewboard.hostingsvcs.service.HostingService`
        subclasses.
    """
    return list(_hosting_service_registry)


def get_hosting_service(name):
    """Return the hosting service with the given name.

    If the hosting service is not found, None will be returned.
    """
    try:
        return _hosting_service_registry.get('hosting_service_id', name)
    except ItemLookupError:
        return None


def register_hosting_service(name, cls):
    """Register a custom hosting service class.

    A name can only be registered once. A KeyError will be thrown if attempting
    to register a second time.

    Args:
        name (unicode):
            The name of the hosting service. If the hosting service already
            has an ID assigned as
            :py:attr:`~HostingService.hosting_service_id`, that value should
            be passed. Note that this will also override any existing
            ID on the service.

        cls (type):
            The hosting service class. This should be a subclass of
            :py:class:`~HostingService`.
    """
    cls.hosting_service_id = name
    _hosting_service_registry.register(cls)


def unregister_hosting_service(name):
    """Unregister a previously registered hosting service.

    Args:
        name (unicode):
            The name of the hosting service.
    """
    try:
        _hosting_service_registry.unregister_by_attr('hosting_service_id',
                                                     name)
    except ItemLookupError as e:
        logger.error('Failed to unregister unknown hosting service "%s"',
                     name)
        raise e


@receiver(initializing, dispatch_uid='populate_hosting_services')
def _on_initializing(**kwargs):
    _hosting_service_registry.populate()


#: Legacy name for HostingServiceHTTPRequest
#:
#: Deprecated:
#:     4.0:
#:     This has been replaced by :py:class:`HostingServiceHTTPRequest`.
URLRequest = HostingServiceHTTPRequest
