"""Base HTTP support for hosting services.

Version Added:
    6.0:
    This replaces the HTTP code in the old
    :py:mod:`reviewboard.hostingsvcs.service` module.
"""

from __future__ import annotations

import base64
import json
import logging
import ssl
from collections import OrderedDict
from typing import Any, Dict, List, NoReturn, Optional, TYPE_CHECKING, Union
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse
from urllib.request import (
    Request as BaseURLRequest,
    HTTPBasicAuthHandler,
    HTTPDigestAuthHandler,
    HTTPPasswordMgrWithDefaultRealm,
    HTTPSHandler,
    build_opener)

from django.utils.encoding import force_str
from djblets.util.decorators import cached_property
from typing_extensions import TypeAlias, TypedDict

from reviewboard.deprecation import RemovedInReviewBoard70Warning

if TYPE_CHECKING:
    from djblets.util.typing import JSONValue
    from reviewboard.hostingsvcs.base.hosting_service import BaseHostingService
    from urllib.request import BaseHandler


logger = logging.getLogger(__name__)


class UploadedFileInfo(TypedDict):
    """Information on an uploaded file.

    Version Added:
        6.0
    """

    #: The content of the file.
    #:
    #: Type:
    #:      bytes
    content: Union[bytes, str]

    #: The base name of the file.
    #:
    #: Type:
    #:      bytes
    filename: Union[bytes, str]


#: Form field data to set when performing a POST or PUT.
#:
#: Version Added:
#:     6.0
FormFields: TypeAlias = Dict[Union[bytes, str],
                             Union[bytes, str]]


#: Type for a mapping of HTTP headers for a request or response.
#:
#: Version Added:
#:     6.0
HTTPHeaders: TypeAlias = Dict[str, str]


#: Query arguments for a HTTP request.
#:
#: Version Added:
#:     6.0
QueryArgs: TypeAlias = Dict[str, Any]


#: Form field data to set when performing a POST or PUT.
#:
#: Version Added:
#:     6.0
UploadedFiles: TypeAlias = Dict[Union[bytes, str], UploadedFileInfo]


def _log_and_raise(
    request: HostingServiceHTTPRequest,
    msg: str,
    **fmt_dict,
) -> NoReturn:
    """Log and raise an exception with the given message.

    This is used when validating data going into the request, and is
    intended to help with debugging bad calls to the HTTP code.

    Version Added:
        4.0

    Args:
        request (HostingServiceHTTPRequest):
            The HTTP request.

        msg (str):
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


class HostingServiceHTTPRequest:
    """A request that can use any HTTP method.

    This provides some additional type checking and utilities for working
    with HTTP requests, headers, URL openers, and SSL certification management.

    Version Changed:
        6.0:
        * Moved from :py:mod:`reviewboard.hostingsvcs.service` to
          :py:mod:`reviewboard.hostingsvcs.base.http`.

    Version Added:
        4.0
    """

    ######################
    # Instance variables #
    ######################

    #: The request payload body, if any.
    #:
    #: Type:
    #:     bytes
    body: Optional[bytes]

    #: The headers to send in the request.
    #:
    #: Type:
    #:     dict
    headers: HTTPHeaders

    #: The hosting service this request is associated with.
    #:
    #: Type:
    #:     HostingService
    hosting_service: Optional[BaseHostingService]

    #: The HTTP method to perform.
    #:
    #: Type:
    #:     str
    method: str

    #: Query arguments added to the URL.
    #:
    #: Type:
    #:     dict
    query: Optional[QueryArgs]

    #: The URL the request is being made to.
    #:
    #: Type:
    #:     str
    url: str

    #: The list of handlers to use when making a HTTP(S) request.
    #:
    #: Type:
    #:     list
    _urlopen_handlers: List[BaseHandler]

    def __init__(
        self,
        url: str,
        query: Optional[QueryArgs] = None,
        body: Optional[bytes] = None,
        headers: Optional[HTTPHeaders] = None,
        method: str = 'GET',
        hosting_service: Optional[BaseHostingService] = None,
        **kwargs,
    ) -> None:
        """Initialize the request.

        Args:
            url (str):
                The URL to make the request against.

            query (dict, optional):
                Query arguments to add onto the URL.

                These will be mixed with any query arguments already in the
                URL, and the result will be applied in sorted order, for
                cross-Python compatibility.

            body (bytes, optional):
                The payload body for the request, if using a ``POST`` or
                ``PUT`` request.

            headers (dict, optional):
                Additional headers to attach to the request.

            method (str, optional):
                The request method. If not provided, it defaults to a ``GET``
                request.

            hosting_service (reviewboard.hostingsvcs.base.hosting_service.
                             BaseHostingService, optional):
                The hosting service this request is associated with.

            **kwargs (dict, unused):
                Additional keyword arguments for the request. This is unused,
                but allows room for expansion by subclasses.
        """
        # These must be set before any _log_and_raise() calls.
        self.method = method
        self.hosting_service = hosting_service

        if body is not None and not isinstance(body, bytes):
            _log_and_raise(
                self,
                'Received non-bytes body for the HTTP request for '
                '%(service)r. This is likely an implementation problem. '
                'Please make sure only byte strings are sent for the request '
                'body.')

        self.headers = {}

        if headers:
            for key, value in headers.items():
                self.add_header(key, value)

        if query:
            parsed_url = list(urlparse(url))
            new_query = parse_qs(parsed_url[4])
            new_query.update(query)

            parsed_url[4] = urlencode(
                OrderedDict(
                    pair
                    for pair in sorted(new_query.items(),
                                       key=lambda pair: pair[0])
                ),
                doseq=True)

            url = urlunparse(parsed_url)

        self.body = body
        self.url = url
        self.query = query

        self._urlopen_handlers = []

    @property
    def data(self) -> Optional[bytes]:
        """The payload data for the request.

        Deprecated:
            4.0:
            This is deprecated in favor of the :py:attr:`body` attribute.
        """
        RemovedInReviewBoard70Warning.warn(
            '%(class_name)s.data is deprecated in favor of '
            '%(class_name)s.body. This will be removed in Review Board 7.'
            % {
                'class_name': type(self).__name__,
            })

        return self.body

    def add_header(
        self,
        name: str,
        value: str,
    ) -> None:
        """Add a header to the request.

        Args:
            name (str):
                The header name.

            value (str):
                The header value.
        """
        if (not isinstance(name, str) or
            not isinstance(value, str)):
            _log_and_raise(
                self,
                'Received non-Unicode header %(header)r (value=%(value)r) '
                'for the HTTP request for %(service)r. This is likely an '
                'implementation problem. Please make sure only Unicode '
                'strings are sent in request headers.',
                header=name,
                value=value)

        self.headers[name.capitalize()] = value

    def get_header(
        self,
        name: str,
        default: Optional[str] = None,
    ) -> Optional[str]:
        """Return a header from the request.

        Args:
            name (str):
                The header name.

            default (str, optional):
                The default value if the header was not found.

        Returns:
            str:
            The header value.
        """
        assert isinstance(name, str), (
            '%s.get_header() requires a Unicode header name'
            % type(self).__name__)

        return self.headers.get(name.capitalize(), default)

    def add_basic_auth(
        self,
        username: Union[bytes, str],
        password: Union[bytes, str],
    ) -> None:
        """Add HTTP Basic Authentication headers to the request.

        Args:
            username (str or bytes):
                The username.

            password (str or bytes):
                The password.
        """
        if isinstance(username, str):
            username = username.encode('utf-8')

        if isinstance(password, str):
            password = password.encode('utf-8')

        auth = b'%s:%s' % (username, password)
        self.add_header(HTTPBasicAuthHandler.auth_header,
                        'Basic %s' % force_str(base64.b64encode(auth)))

    def add_digest_auth(
        self,
        username: str,
        password: str,
    ) -> None:
        """Add HTTP Digest Authentication support to the request.

        Args:
            username (str):
                The username.

            password (str):
                The password.
        """
        result = urlparse(self.url)
        top_level_url = '%s://%s' % (result.scheme, result.netloc)

        password_mgr = HTTPPasswordMgrWithDefaultRealm()
        password_mgr.add_password(None, top_level_url, username, password)

        self.add_urlopen_handler(HTTPDigestAuthHandler(password_mgr))

    def add_urlopen_handler(
        self,
        handler: BaseHandler,
    ) -> None:
        """Add a handler to invoke for the urlopen call.

        Note:
            This is dependent on a :py:mod:`urllib`-backed request. While
            that is the default today, it may not be in the future. This
            method should be used with the knowledge that it may someday be
            deprecated, or may not work at all with special subclasses.

        Args:
            handler (urllib.request.AbstractHTTPHandler):
                The handler to add.
        """
        self._urlopen_handlers.append(handler)

    def open(self) -> HostingServiceHTTPResponse:
        """Open the request to the server, returning the response.

        Returns:
            HostingServiceHTTPResponse:
            The response information from the server.

        Raises:
            urllib.error.URLError:
                An error occurred talking to the server, or an HTTP error
                (400+) was returned.
        """
        request = BaseURLRequest(url=self.url,
                                 data=self.body,
                                 headers=self.headers,
                                 method=self.method)

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


class HostingServiceHTTPResponse:
    """An HTTP response from the server.

    This stores the URL, payload data, headers, and status code from an
    HTTP response.

    Version Changed:
        6.0:
        * Moved from :py:mod:`reviewboard.hostingsvcs.service` to
          :py:mod:`reviewboard.hostingsvcs.base.http`.
        * Deprecated legacy tuple representations of this class now emit
          deprecation warnings and will be removed in Review Board 7.

    Version Added:
        4.0
    """

    ######################
    # Instance variables #
    ######################

    #: The response data.
    #:
    #: Type:
    #:     bytes
    data: bytes

    #: The HTTP response headers.
    #:
    #: It's recommended to call :py:meth:`get_header` to request a header.
    #:
    #: Type:
    #:     dict
    headers: HTTPHeaders

    #: The HTTP request this is in response to.
    #:
    #: Type:
    #:     HostingServiceHTTPRequest
    request: HostingServiceHTTPRequest

    #: The HTTP status code for the response.
    #:
    #: Type:
    #:     int
    status_code: int

    #: The URL providing the response.
    url: str

    def __init__(
        self,
        request: HostingServiceHTTPRequest,
        url: str,
        data: bytes,
        headers: HTTPHeaders,
        status_code: int,
    ) -> None:
        """Initialize the response.

        Args:
            request (HostingServiceHTTPRequest):
                The request this is in response to.

            url (str):
                The URL serving the response.

                If redirected, this may differ from the request URL.

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

        new_headers: HTTPHeaders = {}

        for key, value in headers.items():
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
    def json(self) -> JSONValue:
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

    def get_header(
        self,
        name: str,
        default: Optional[str] = None,
    ) -> Optional[str]:
        """Return the value of a header as a Unicode string.

        This accepts a header name with any form of capitalization. The header
        name will be normalized.

        Args:
            name (str):
                The header name.

            default (str, optional):
                The default value if the header is not set.

        Returns:
            str:
            The resulting header value.
        """
        return self.headers.get(name.capitalize(), default)

    def __getitem__(
        self,
        i: int,
    ) -> Any:
        """Return an indexed item from the response.

        This is used to emulate the older 2-tuple response returned by hosting
        service HTTP request methods.

        Deprecated:
            6.0:
            Callers should instead access :py:attr:`data` or :py:attr:`headers`
            on this object.

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
        RemovedInReviewBoard70Warning.warn(
            'Accessing %(class_name)s by index is deprecated. Please use '
            '%(class_name)s.data or %(class_name)s.headers instead. This '
            'will be removed in Review Board 7.'
            % {
                'class_name': type(self).__name__,
            })

        if i == 0:
            return self.data
        elif i == 1:
            return self.headers
        else:
            raise IndexError
