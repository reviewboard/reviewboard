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
from typing import Any, Dict, TypedDict, TYPE_CHECKING, Union
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse
from urllib.request import (
    Request as BaseURLRequest,
    HTTPBasicAuthHandler,
    HTTPDigestAuthHandler,
    HTTPPasswordMgrWithDefaultRealm,
    HTTPSHandler,
    build_opener)

from django.utils.encoding import force_str
from djblets.log import log_timed
from djblets.util.decorators import cached_property

from reviewboard.certs.cert import Certificate
from reviewboard.certs.manager import cert_manager
from reviewboard.deprecation import RemovedInReviewBoard90Warning

if TYPE_CHECKING:
    from urllib.request import BaseHandler

    from typelets.json import JSONValue
    from typing_extensions import Never, TypeAlias

    from reviewboard.hostingsvcs.base.hosting_service import BaseHostingService
    from reviewboard.hostingsvcs.models import HostingServiceAccount


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
    content: bytes | str

    #: The base name of the file.
    #:
    #: Type:
    #:      bytes
    filename: bytes | str


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


def _build_ssl_context_from_ssl_cert(
    *,
    hosting_account: HostingServiceAccount,
) -> ssl.SSLContext:
    """Return an SSL context for a hosting service with legacy cert data.

    This will attempt to migrate the stored ``ssl_cert`` data a hosting
    service account to a modern stored certificate that can then be
    properly managed.

    If there are any issues with migration, or if the resulting SSL
    certificate does not match the target hostname, then the stored certificate
    data will be used directly with hostname verification disabled.

    This should never be needed for hosting service accounts configured
    after Review Board 8.0.

    Version Added:
        8.0

    Args:
        hosting_account (reviewboard.hostingsvcs.models.HostingServiceAccount):
            The hosting service account to migrate.

    Returns:
        ssl.SSLContext:
        A configured SSL context with the certificate trusted.
    """
    context: (ssl.SSLContext | None) = None
    cert_data = hosting_account.data['ssl_cert']

    if hosting_url := hosting_account.hosting_url:
        local_site = hosting_account.local_site

        try:
            parsed = urlparse(hosting_url)

            if hostname := parsed.hostname:
                port = parsed.port or 443

                # Check if there's an existing certificate being managed.
                certificate = cert_manager.get_certificate(
                    hostname=hostname,
                    port=port,
                    local_site=local_site,
                )

                if certificate is None:
                    # There's no existing certificate. Generate one from
                    # the stored data and check to see if it matches the
                    # hostname. If not, we can't add it, and instead need
                    # to go the legacy `check_hostname=False` route.
                    certificate = Certificate(
                        hostname=hostname,
                        port=port,
                        cert_data=cert_data.encode('ascii'),
                    )

                    if certificate.matches_host(hostname):
                        # This is a direct match, so add this to the cert
                        # manager.
                        cert_manager.add_certificate(
                            certificate=certificate,
                            local_site=local_site,
                        )

                        del hosting_account.data['ssl_cert']
                        hosting_account.save(update_fields=('data',))
                    else:
                        # This is NOT a direct match, but the admin had
                        # previously approved this cert for this server.
                        # We'll have to keep the legacy fallback that
                        # disables hostname checks.
                        logger.warning(
                            'The approved SSL/TLS certificate stored in '
                            'hosting service account ID=%r does not match the '
                            'hostname %r for the server. Falling back to a '
                            'less-secure form of verification. Please ensure '
                            'the server has a valid certificate matching its '
                            'hostname and then upload a new certificate.',
                            hosting_account.pk, hostname,
                        )

                        certificate = None

                if certificate is not None:
                    # Use cert_manager to build the SSL context (loads the
                    # stored cert via load_verify_locations in
                    # build_ssl_context).
                    context = cert_manager.build_ssl_context(
                        hostname=hostname,
                        port=port,
                        local_site=local_site,
                    )
        except Exception:
            # This will be issued every time this cert is used, making it
            # loud and noisy in order to better catch an admin's attention.
            logger.exception(
                'Unexpected error migrating legacy ssl_cert data for hosting '
                'service account %s. Falling back to a legacy insecure '
                'SSL context.',
                hosting_account.pk,
            )

    if context is None:
        # Fall back to using the certificate data directly without hostname
        # validation.
        context = ssl.create_default_context()
        context.load_verify_locations(cadata=cert_data)
        context.check_hostname = False

    return context


def _log_and_raise(
    value: Never,
    request: HostingServiceHTTPRequest,
    msg: str,
    **fmt_dict,
) -> Never:
    """Log and raise an exception with the given message.

    This is used when validating data going into the request, and is
    intended to help with debugging bad calls to the HTTP code.

    Version Changed:
        8.0:
        Modified to take in the offending value.

    Version Added:
        4.0

    Args:
        value (object):
            The value which was not valid.

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
    msg %= dict({
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
    body: bytes | None

    #: The headers to send in the request.
    #:
    #: Type:
    #:     dict
    headers: HTTPHeaders

    #: The hosting service this request is associated with.
    #:
    #: Type:
    #:     HostingService
    hosting_service: BaseHostingService | None

    #: The HTTP method to perform.
    #:
    #: Type:
    #:     str
    method: str

    #: Query arguments added to the URL.
    #:
    #: Type:
    #:     dict
    query: QueryArgs | None

    #: The URL the request is being made to.
    #:
    #: Type:
    #:     str
    url: str

    #: The list of handlers to use when making a HTTP(S) request.
    #:
    #: Type:
    #:     list
    _urlopen_handlers: list[BaseHandler]

    def __init__(
        self,
        url: str,
        query: (QueryArgs | None) = None,
        body: (bytes | None) = None,
        headers: (HTTPHeaders | None) = None,
        method: str = 'GET',
        hosting_service: (BaseHostingService | None) = None,
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
                body,
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
    def data(self) -> bytes | None:
        """The payload data for the request.

        Deprecated:
            4.0:
            This is deprecated in favor of the :py:attr:`body` attribute.
        """
        class_name = type(self).__name__

        RemovedInReviewBoard90Warning.warn(
            f'{class_name}.data is deprecated in favor of '
            f'{class_name}.body. This will be removed in Review Board 9.'
        )

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
        if not isinstance(name, str):
            _log_and_raise(
                name,
                self,
                'Received non-Unicode header name %(header)r '
                '(value=%(data)r) for the HTTP request for %(service)r. '
                'This is likely an implementation problem. Please make sure '
                'only Unicode strings are sent in request headers.',
                header=name,
                data=value)

        if not isinstance(value, str):
            _log_and_raise(
                value,
                self,
                'Received non-Unicode header value for %(header)r '
                '(value=%(data)r) for the HTTP request for %(service)r. This '
                'is likely an implementation problem. Please make sure only '
                'Unicode strings are sent in request headers.',
                header=name,
                data=value)

        self.headers[name.capitalize()] = value

    def get_header(
        self,
        name: str,
        default: (str | None) = None,
    ) -> str | None:
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
            f'{type(self).__name__}.get_header() requires a Unicode header '
            f'name')

        return self.headers.get(name.capitalize(), default)

    def add_basic_auth(
        self,
        username: bytes | str,
        password: bytes | str,
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
        encoded = force_str(base64.b64encode(auth))

        self.add_header(HTTPBasicAuthHandler.auth_header,
                        f'Basic {encoded}')

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
        top_level_url = f'{result.scheme}://{result.netloc}'

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
        url = self.url
        method = self.method

        request = BaseURLRequest(url=url,
                                 data=self.body,
                                 headers=self.headers,
                                 method=method)

        hosting_service = self.hosting_service

        if hosting_service:
            context: (ssl.SSLContext | None)

            hosting_account = hosting_service.account

            if 'ssl_cert' in hosting_account.data:
                # There's existing legacy SSL certificate data stored in
                # the account. Convert it to a modern Certificate if
                # possible, and build a context with it. If successful,
                # 'ssl_cert' will be removed from the data.
                context = _build_ssl_context_from_ssl_cert(
                    hosting_account=hosting_account,
                )
            else:
                # This is the modern code path. Build an SSL context.
                #
                # We use build_urlopen_kwargs() as a convenience. It will
                # sanity-check the URL for HTTPS and build a context with the
                # right parameters.
                context = (
                    cert_manager.build_urlopen_kwargs(
                        url=self.url,
                        local_site=hosting_service.account.local_site,
                    )
                    .get('context')
                )

            if context is not None:
                # An SSL context was successfully built, so we can now set up
                # an HTTPS handler using it.
                self._urlopen_handlers.append(HTTPSHandler(context=context))

            timer_msg = (
                f'Performing HTTP {method} request for '
                f'{hosting_service.name} at {url}'
            )
        else:
            timer_msg = (
                f'Performing HTTP {method} request at {url}'
            )

        opener = build_opener(*self._urlopen_handlers)

        with log_timed(timer_msg,
                       logger=logger):
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
          deprecation warnings and will be removed in Review Board 8.

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
        data: bytes | None,
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

        if data is None:
            data = b''
        elif not isinstance(data, bytes):
            # HTTP response data will be in byte strings, unless something is
            # overridden. Users should never see this in production, but
            # it'll be confusing for development. Make sure developers see
            # this through both a log message and an exception.
            _log_and_raise(
                data,
                request,
                'Received non-byte data from the HTTP %(method)s request '
                'for %(service)r. This is likely an implementation '
                'problem in a unit test or subclass. Please make sure '
                'only byte strings are sent.')

        if not isinstance(headers, dict):
            _log_and_raise(
                headers,
                request,
                'Headers response for HTTP %(method)s request for %(service)r '
                'is not a dict. This is likely an implementation problem in a '
                'unit test. Please make sure a dictionary is returned.')

        new_headers: HTTPHeaders = {}

        for key, value in headers.items():
            if not isinstance(key, str):
                _log_and_raise(
                    key,
                    request,
                    'Received non string header %(header)r from the '
                    'HTTP %(method)s request for %(service)r. This is likely '
                    'an implementation problem in a unit test. Please '
                    'make sure only strings are sent.',
                    header=key)

            if not isinstance(value, str):
                _log_and_raise(
                    value,
                    request,
                    'Received non string header value %(header)r '
                    '(key=%(key)r) from the HTTP %(method)s request for '
                    '%(service)r. This is likely an implementation problem in '
                    'a unit test. Please make sure only strings are  sent.',
                    key=key,
                    header=value)

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
        default: (str | None) = None,
    ) -> str | None:
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
        class_name = type(self).__name__

        RemovedInReviewBoard90Warning.warn(
            f'Accessing {class_name} by index is deprecated. Please use '
            f'{class_name}.data or {class_name}.headers instead. This '
            'will be removed in Review Board 9.'
        )

        if i == 0:
            return self.data
        elif i == 1:
            return self.headers
        else:
            raise IndexError
