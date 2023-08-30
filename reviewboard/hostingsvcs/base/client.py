"""Base communication client support for hosting services.

Version Added:
    6.0:
    This replaces the client code in the old
    :py:mod:`reviewboard.hostingsvcs.service` module.
"""

from __future__ import annotations

import hashlib
import json
import logging
import ssl
from email.generator import _make_boundary as generate_boundary
from typing import Callable, Optional, TYPE_CHECKING, Tuple, Type, Union
from urllib.error import URLError
from urllib.parse import urlparse

from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.backends import default_backend
from django.utils.encoding import force_bytes, force_str

from reviewboard.deprecation import RemovedInReviewBoard70Warning
from reviewboard.hostingsvcs.base.http import (HostingServiceHTTPRequest,
                                               HostingServiceHTTPResponse)
from reviewboard.scmtools.certs import Certificate
from reviewboard.scmtools.crypto_utils import decrypt_password
from reviewboard.scmtools.errors import UnverifiedCertificateError

if TYPE_CHECKING:
    from djblets.util.typing import JSONValue
    from reviewboard.hostingsvcs.base.hosting_service import (
        BaseHostingService,
        HostingServiceCredentials,
    )
    from reviewboard.hostingsvcs.base.http import (FormFields,
                                                   HTTPHeaders,
                                                   UploadedFiles)
    from reviewboard.hostingsvcs.models import HostingServiceAccount


logger = logging.getLogger(__name__)


class HostingServiceClient:
    """Client for communicating with a hosting service's API.

    This implementation includes abstractions for performing HTTP operations,
    and wrappers for those to interpret responses as JSON data.

    Hosting service implementations can also include an override of this class
    to add additional checking (such as GitHub's checking of rate limit
    headers), or add higher-level API functionality.

    Version Changed:
        6.0:
        * Moved from :py:mod:`reviewboard.hostingsvcs.service` to
          :py:mod:`reviewboard.hostingsvcs.base.client`.
        * Deprecated JSON utility functions now emit deprecation warnings and
          will be removed in Review Board 7.
    """

    #: The HTTP request class to construct for HTTP requests.
    #:
    #: Subclasses can replace this if they need custom behavior when
    #: constructing or invoking the request.
    #:
    #: Version Added:
    #:     4.0
    http_request_cls: Type[HostingServiceHTTPRequest] = \
        HostingServiceHTTPRequest

    #: The HTTP response class to construct HTTP responses.
    #:
    #: Subclasses can replace this if they need custom ways of formatting
    #: or interpreting response data.
    #:
    #: Version Added:
    #:     4.0
    http_response_cls: Type[HostingServiceHTTPResponse] = \
        HostingServiceHTTPResponse

    #: Whether to add HTTP Basic Auth headers by default.
    #:
    #: By default, hosting services will support HTTP Basic Auth. This can be
    #: turned off if not needed.
    #:
    #: Version Added:
    #:     4.0
    use_http_basic_auth: bool = True

    #: Whether to add HTTP Digest Auth headers by default.
    #:
    #: By default, hosting services will not support HTTP Digest Auth. This
    #: can be turned on if needed.
    #:
    #: Version Added:
    #:     4.0
    use_http_digest_auth: bool = False

    ######################
    # Instance variables #
    ######################

    #: The hosting service that owns this client.
    #:
    #: Type:
    #:     The hosting service that owns this client.
    hosting_service: BaseHostingService

    def __init__(
        self,
        hosting_service: BaseHostingService,
    ) -> None:
        """Initialize the client.

        Args:
            hosting_service (reviewboard.hostingsvcs.base.hosting_service.
                             BaseHostingService):
                The hosting service that is using this client.
        """
        self.hosting_service = hosting_service

    #
    # HTTP utility methods
    #

    def http_delete(
        self,
        url: str,
        headers: Optional[HTTPHeaders] = None,
        *args,
        **kwargs,
    ) -> HostingServiceHTTPResponse:
        """Perform an HTTP DELETE on the given URL.

        Version Changed:
            4.0:
            This now returns a :py:class:`~reviewboard.hostingsvcs.base.http.
            HostingServiceHTTPResponse` instead of a 2-tuple.

        Args:
            url (str):
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
            reviewboard.hostingsvcs.base.http.HostingServiceHTTPResponse:
            The HTTP response for the request.

        Raises:
            reviewboard.hostingsvcs.errors.HostingServiceError:
                There was an error performing the request, and the error has
                been translated to a more specific hosting service error.

            urllib.error.URLError:
                There was an error performing the request, and the result is
                a raw HTTP error.
        """
        return self.http_request(url=url,
                                 headers=headers,
                                 method='DELETE',
                                 **kwargs)

    def http_get(
        self,
        url: str,
        headers: Optional[HTTPHeaders] = None,
        *args,
        **kwargs,
    ) -> HostingServiceHTTPResponse:
        """Perform an HTTP GET on the given URL.

        Version Changed:
            4.0:
            This now returns a :py:class:`reviewboard.hostingsvcs.base.http.
            HostingServiceHTTPResponse` instead of a 2-tuple.

        Args:
            url (str):
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
            reviewboard.hostingsvcs.base.http.HostingServiceHTTPResponse:
            The HTTP response for the request.

        Raises:
            reviewboard.hostingsvcs.errors.HostingServiceError:
                There was an error performing the request, and the error has
                been translated to a more specific hosting service error.

            urllib.error.URLError:
                There was an error performing the request, and the result is
                a raw HTTP error.
        """
        return self.http_request(url=url,
                                 headers=headers,
                                 method='GET',
                                 **kwargs)

    def http_head(
        self,
        url: str,
        headers: Optional[HTTPHeaders] = None,
        *args,
        **kwargs,
    ) -> HostingServiceHTTPResponse:
        """Perform an HTTP HEAD on the given URL.

        Version Added:
            4.0

        Args:
            url (str):
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
            reviewboard.hostingsvcs.base.http.HostingServiceHTTPResponse:
            The HTTP response for the request.

        Raises:
            reviewboard.hostingsvcs.errors.HostingServiceError:
                There was an error performing the request, and the error has
                been translated to a more specific hosting service error.

            urllib.error.URLError:
                There was an error performing the request, and the result is
                a raw HTTP error.
        """
        return self.http_request(url=url,
                                 headers=headers,
                                 method='HEAD',
                                 **kwargs)

    def http_post(
        self,
        url: str,
        body: Optional[bytes] = None,
        fields: Optional[FormFields] = None,
        files: Optional[UploadedFiles] = None,
        content_type: Optional[str] = None,
        headers: Optional[HTTPHeaders] = None,
        *args,
        **kwargs,
    ) -> HostingServiceHTTPResponse:
        """Perform an HTTP POST on the given URL.

        Version Changed:
            4.0:
            This now returns a :py:class:`reviewboard.hostingsvcs.base.http.
            HostingServiceHTTPResponse` instead of a 2-tuple. The response can
            be treated as a 2-tuple for older code.

        Args:
            url (str):
                The URL to perform the request on.

            body (bytes, optional):
                The request body.

                If not provided, it will be generated from the ``fields`` and
                ``files`` arguments.

            fields (dict, optional):
                Form fields to use to generate the request body.

                This argument will only be used if ``body`` is ``None``.

            files (dict, optional):
                Files to use to generate the request body.

                This argument will only be used if ``body`` is ``None``.

            content_type (str, optional):
                The content type of the request.

                If provided, it will be appended as the
                :mailheader:`Content-Type` header.

            headers (dict, optional):
                Extra headers to include with the request.

            *args (tuple):
                Additional positional arguments to pass to
                :py:meth:`http_request`.

            **kwargs (dict):
                Additional keyword arguments to pass to
                :py:meth:`http_request`.

        Returns:
            reviewboard.hostingsvcs.base.http.HostingServiceHTTPResponse:
            The HTTP response for the request.

        Raises:
            reviewboard.hostingsvcs.errors.HostingServiceError:
                There was an error performing the request, and the error has
                been translated to a more specific hosting service error.

            urllib.error.URLError:
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

    def http_put(
        self,
        url: str,
        body: Optional[bytes] = None,
        fields: Optional[FormFields] = None,
        files: Optional[UploadedFiles] = None,
        content_type: Optional[str] = None,
        headers: Optional[HTTPHeaders] = None,
        *args,
        **kwargs,
    ) -> HostingServiceHTTPResponse:
        """Perform an HTTP PUT on the given URL.

        Version Added:
            4.0

        Args:
            url (str):
                The URL to perform the request on.

            body (bytes, optional):
                The request body.

                If not provided, it will be generated from the ``fields`` and
                ``files`` arguments.

            fields (dict, optional):
                Form fields to use to generate the request body.

                This argument will only be used if ``body`` is ``None``.

            files (dict, optional):
                Files to use to generate the request body.

                This argument will only be used if ``body`` is ``None``.

            content_type (str, optional):
                The content type of the request.

                If provided, it will be appended as the
                :mailheader:`Content-Type` header.

            headers (dict, optional):
                Extra headers to include with the request.

            *args (tuple):
                Additional positional arguments to pass to
                :py:meth:`http_request`.

            **kwargs (dict):
                Additional keyword arguments to pass to
                :py:meth:`http_request`.

        Returns:
            reviewboard.hostingsvcs.base.http.HostingServiceHTTPResponse:
            The HTTP response for the request.

        Raises:
            reviewboard.hostingsvcs.errors.HostingServiceError:
                There was an error performing the request, and the error has
                been translated to a more specific hosting service error.

            urllib.error.URLError:
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

    def http_request(
        self,
        url: str,
        body: Optional[bytes] = None,
        headers: Optional[HTTPHeaders] = None,
        method: str = 'GET',
        **kwargs,
    ) -> HostingServiceHTTPResponse:
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
          - Build the :py:class:`reviewboard.hostingsvcs.base.http.
          HostingServiceHTTPRequest` object.

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
            This now returns a :py:class:`reviewboard.hostingsvcs.base.http.
            HostingServiceHTTPResponse` instead of a 2-tuple.

        Args:
            url (str):
                The URL to open.

            body (bytes, optional):
                The request body.

            headers (dict, optional):
                Headers to include in the request.

            method (str, optional):
                The HTTP method to use to perform the request.

            **kwargs (dict):
                Additional keyword arguments to pass to
                :py:meth:`build_http_request`.

        Returns:
            reviewboard.hostingsvcs.base.http.HostingServiceHTTPResponse:
            The HTTP response for the request.

        Raises:
            reviewboard.hostingsvcs.errors.HostingServiceError:
                There was an error performing the request, and the error has
                been translated to a more specific hosting service error.

            urllib.error.URLError:
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

    def get_http_credentials(
        self,
        account: HostingServiceAccount,
        username: Optional[str] = None,
        password: Optional[str] = None,
        **kwargs,
    ) -> HostingServiceCredentials:
        """Return credentials used to authenticate with the service.

        Subclasses can override this to return credentials based on the
        account or the values passed in when performing the HTTP request.
        The resulting dictionary contains keys that will be processed in
        :py:meth:`build_http_request`.

        There are a few supported keys that subclasses will generally want
        to return:

        Keys:
            username (str):
                The username, typically for use in HTTP Basic Auth or HTTP
                Digest Auth.

            password (str):
                The accompanying password.

            header (dict):
                A dictionary of authentication headers to add to the request.

        By default, this will return a ``username`` and ``password`` based on
        the request (if those values are provided by the caller).

        Args:
            account (reviewboard.hostingsvcs.models.HostingServiceAccount):
                The stored authentication data for the service.

            username (str, optional):
                An explicit username passed by the caller.

                This will override the data stored in the account, if both a
                username and password are provided.

            password (str, optional):
                An explicit password passed by the caller.

                This will override the data stored in the account, if both a
                username and password are provided.

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

    def open_http_request(
        self,
        request: HostingServiceHTTPRequest,
    ) -> HostingServiceHTTPResponse:
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
            request (reviewboard.hostingsvcs.base.http.
                     HostingServiceHTTPRequest):
                The HTTP request to open.

        Returns:
            reviewboard.hostingsvcs.base.http.HostingServiceHTTPResponse:
            The successful response information from the server.

        Raises:
            urllib.error.URLError:
                There was an error performing a request on the URL.
        """
        return request.open()

    def build_http_request(
        self,
        credentials: HostingServiceCredentials,
        **kwargs,
    ) -> HostingServiceHTTPRequest:
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
                Keyword arguments for the :py:class:`reviewboard.hostingsvcs.
                base.http.HostingServiceHTTPRequest` instance.

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

            for header, value in auth_headers.items():
                request.add_header(header, value)

        return request

    def process_http_response(
        self,
        response: HostingServiceHTTPResponse,
    ) -> HostingServiceHTTPResponse:
        """Process an HTTP response and return a result.

        This can be used by subclasses to modify a response before it gets back
        to the caller. It can also raise a :py:class:`urllib.error.URLError`
        (which will get processed by :py:meth:`process_http_error`), or a
        :py:class:`~reviewboard.hostingsvcs.errors.HostingServiceError`.

        By default, the response is returned as-is.

        Args:
            response (reviewboard.hostingsvcs.base.http.
                      HostingServiceHTTPResponse):
                The response to process.

        Returns:
            reviewboard.hostingsvcs.base.http.HostingServiceHTTPResponse:
            The resulting response.
        """
        return response

    def process_http_error(
        self,
        request: HostingServiceHTTPRequest,
        e: URLError,
    ) -> None:
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
            request (reviewboard.hostingsvcs.base.http.
                     HostingServiceHTTPRequest):
                The request that resulted in an error.

            e (urllib.error.URLError):
                The error to process.

        Raises:
            reviewboard.scmtools.errors.UnverifiedCertificateError:
                The SSL certificate was not able to be verified.
        """
        if ('CERTIFICATE_VERIFY_FAILED' not in str(e) or
            not hasattr(ssl, 'create_default_context')):
            return

        parts = urlparse(request.url)
        port = parts.port or 443

        assert parts.hostname

        cert_pem = ssl.get_server_certificate((parts.hostname, port))
        cert_der = ssl.PEM_cert_to_DER_cert(cert_pem)

        cert = x509.load_pem_x509_certificate(cert_pem.encode('ascii'),
                                              default_backend())
        issuer = cert.issuer.get_attributes_for_oid(
            NameOID.COMMON_NAME)[0].value
        subject = cert.subject.get_attributes_for_oid(
            NameOID.COMMON_NAME)[0].value

        raise UnverifiedCertificateError(
            Certificate(
                pem_data=cert_pem,
                valid_from=cert.not_valid_before.isoformat(),
                valid_until=cert.not_valid_after.isoformat(),
                issuer=force_str(issuer),
                hostname=force_str(subject),
                fingerprint=hashlib.sha256(cert_der).hexdigest()))

    #
    # JSON utility methods
    #

    def json_delete(
        self,
        *args,
        **kwargs,
    ) -> Tuple[JSONValue, HTTPHeaders]:
        """Perform an HTTP DELETE and interpret the results as JSON.

        Deprecated:
            4.0:
            Use :py:meth:`http_delete` instead, and access the
            :py:attr:`~reviewboard.hostingsvcs.base.http.
            HostingServiceHTTPResponse.json` attribute on the response for the
            JSON payload.

        Args:
            *args (tuple):
                Additional positional arguments to pass to
                :py:meth:`http_delete`.

            **kwargs (dict):
                Additional keyword arguments to pass to
                :py:meth:`http_delete`.

        Returns:
            tuple:
            A 2-tuple of:

            Tuple:
                0 (object):
                    The JSON data (in the appropriate type).

                1 (dict):
                    The HTTP response headers.

        Raises:
            reviewboard.hostingsvcs.errors.HostingServiceError:
                There was an error performing the request, and the error has
                been translated to a more specific hosting service error.

            urllib.error.URLError:
                When there is an error communicating with the URL.
        """
        RemovedInReviewBoard70Warning.warn(
            '%(class_name)s.json_delete is deprecated. Please use '
            '%(class_name)s.http_delete instead. This will be removed in '
            'Review Board 7.'
            % {
                'class_name': type(self).__name__,
            })

        return self._do_json_method(self.http_delete, *args, **kwargs)

    def json_get(
        self,
        *args,
        **kwargs,
    ) -> Tuple[JSONValue, HTTPHeaders]:
        """Perform an HTTP GET and interpret the results as JSON.

        Deprecated:
            4.0:
            Use :py:meth:`http_get` instead, and access the
            :py:attr:`~reviewboard.hostingsvcs.base.http.
            HostingServiceHTTPResponse.json` attribute on the response for
            the JSON payload.

        Args:
            *args (tuple):
                Additional positional arguments to pass to
                :py:meth:`http_get`.

            **kwargs (dict):
                Additional keyword arguments to pass to
                :py:meth:`http_get`.

        Returns:
            tuple:
            A 2-tuple of:

            Tuple:
                0 (object):
                    The JSON data (in the appropriate type).

                1 (dict):
                    The HTTP response headers.

        Raises:
            reviewboard.hostingsvcs.errors.HostingServiceError:
                There was an error performing the request, and the error has
                been translated to a more specific hosting service error.

            urllib.error.URLError:
                When there is an error communicating with the URL.
        """
        RemovedInReviewBoard70Warning.warn(
            '%(class_name)s.json_get is deprecated. Please use '
            '%(class_name)s.http_get instead. This will be removed in '
            'Review Board 7.'
            % {
                'class_name': type(self).__name__,
            })

        return self._do_json_method(self.http_get, *args, **kwargs)

    def json_post(
        self,
        *args,
        **kwargs,
    ) -> Tuple[JSONValue, HTTPHeaders]:
        """Perform an HTTP POST and interpret the results as JSON.

        Deprecated:
            4.0:
            Use :py:meth:`http_post` instead, and access the
            :py:attr:`~reviewboard.hostingsvcs.base.http.
            HostingServiceHTTPResponse.json` attribute on the response for
            the JSON payload.

        Args:
            *args (tuple):
                Additional positional arguments to pass to
                :py:meth:`http_post`.

            **kwargs (dict):
                Additional keyword arguments to pass to
                :py:meth:`http_post`.

        Returns:
            tuple:
            A 2-tuple of:

            Tuple:
                0 (object):
                    The JSON data (in the appropriate type).

                1 (dict):
                    The HTTP response headers.

        Raises:
            reviewboard.hostingsvcs.errors.HostingServiceError:
                There was an error performing the request, and the error has
                been translated to a more specific hosting service error.

            urllib.error.URLError:
                When there is an error communicating with the URL.
        """
        RemovedInReviewBoard70Warning.warn(
            '%(class_name)s.json_post is deprecated. Please use '
            '%(class_name)s.http_post instead. This will be removed in '
            'Review Board 7.'
            % {
                'class_name': type(self).__name__,
            })

        return self._do_json_method(self.http_post, *args, **kwargs)

    def _do_json_method(
        self,
        method: Callable[..., Union[Tuple[bytes, HTTPHeaders],
                                    HostingServiceHTTPResponse]],
        *args,
        **kwargs,
    ) -> Tuple[JSONValue, HTTPHeaders]:
        """Parse the result of an HTTP operation as JSON.

        Deprecated:
            4.0:
            Use :py:meth:`http_post` instead, and access the
            :py:attr:`~reviewboard.hostingsvcs.base.http.
            HostingServiceHTTPResponse.json` attribute on the response for
            the JSON payload.

        Args:
            method (callable):
                The callable to use to execute the request.

            *args (tuple):
                Positional arguments to pass to ``method``.

            **kwargs (dict):
                Keyword arguments to pass to ``method``.

        Returns:
            tuple:
            A 2-tuple of:

            Tuple:
                0 (object):
                    The JSON data (in the appropriate type).

                1 (dict):
                    The HTTP response headers.

        Raises:
            reviewboard.hostingsvcs.errors.HostingServiceError:
                There was an error performing the request, and the error has
                been translated to a more specific hosting service error.

            urllib.error.URLError:
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

    def _build_put_post_request(
        self,
        body: Optional[bytes] = None,
        fields: Optional[FormFields] = None,
        files: Optional[UploadedFiles] = None,
        content_type: Optional[str] = None,
        headers: Optional[HTTPHeaders] = None,
    ) -> Tuple[bytes, HTTPHeaders]:
        """Build a request body and headers for a HTTP PUT or POST.

        Args:
            body (bytes, optional):
                The request body content.

            fields (dict, optional):
                The form fields used to construct a request body.

                This is ignored if ``body`` is set.

            files (dict, optional):
                The uploaded files used to construct a request body.

                This is ignored if ``body`` is set.

            content_type (str, optional):
                The value used for the :mailheader:`Content-Type` header.

            headers (dict, optional):
                Additional headers to set in the request.

        Returns:
            tuple:
            A 2-tuple of:

            Tuple:
                0 (bytes):
                    The body to post.

                1 (dict):
                    The HTTP response headers.
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
    def build_form_data(
        fields: Optional[FormFields],
        files: Optional[UploadedFiles] = None,
    ) -> Tuple[bytes, str]:
        """Encode data for use in an HTTP POST.

        Args:
            fields (dict):
                A mapping of field names to values.

            files (dict, optional):
                A mapping of field names to files (:py:class:`dict`).

        Returns:
            A 2-tuple of:

            Tuple:
                0 (bytes):
                    The body to post.

                1 (dict):
                    The HTTP response headers.
        """
        boundary = HostingServiceClient._make_form_data_boundary()
        enc_boundary = boundary.encode('utf-8')
        content_parts = []

        if fields:
            for key, value in sorted(fields.items(),
                                     key=lambda pair: pair[0]):
                if isinstance(key, str):
                    key = key.encode('utf-8')

                if isinstance(value, str):
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
            for key, data in sorted(files.items(),
                                    key=lambda pair: pair[0]):
                filename = data['filename']
                content = data['content']

                if isinstance(key, str):
                    key = key.encode('utf-8')

                if isinstance(filename, str):
                    filename = filename.encode('utf-8')

                if isinstance(content, str):
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
    def _make_form_data_boundary() -> str:
        """Return a unique boundary to use for HTTP form data.

        This primary exists for the purpose of spying in unit tests.

        Returns:
            str:
            The boundary for use in the form data.
        """
        return generate_boundary()
