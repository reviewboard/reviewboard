"""HTTP handler support for SSL/TLS certificate verification.

Version Added:
    8.1
"""

from __future__ import annotations

import logging
import ssl
from typing import TYPE_CHECKING
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import (
    HTTPSHandler,
    Request,
    build_opener,
)

from typelets.symbols import UNSET

from reviewboard.certs.cert import Certificate
from reviewboard.certs.errors import (CertificateVerificationError,
                                      CertificateVerificationFailureCode)
from reviewboard.certs.manager import cert_manager as default_cert_manager

if TYPE_CHECKING:
    from http.client import HTTPResponse
    from urllib.request import _DataType, _UrlopenRet

    from typelets.funcs import KwargsDict
    from typelets.symbols import Unsettable

    from reviewboard.certs.manager import CertificateManager
    from reviewboard.site.models import LocalSite


logger = logging.getLogger(__name__)


class CertificateVerificationHTTPSHandler(HTTPSHandler):
    """An urlopen handler for CertificateManager-backed HTTPS connections.

    This handler specializes :py:class:`~urllib.request.HTTPSHandler`,
    using the Certificate Manager to provide an SSL context and converting
    any SSL/TLS errors into a
    :py:class:`~reviewboard.certs.errors.CertificateVerificationError` where
    possible.

    Version Added:
        8.1
    """

    ######################
    # Instance variables #
    ######################

    #: The associated Certificate Manager for the handler.
    _cert_manager: CertificateManager

    #: Optional PEM-formatted certificate data to use for verification.
    _extra_cert_data: str | None

    #: The Local Site used for certificate lookup.
    _local_site: LocalSite | None

    #: Whether we're checking the hostname against the certificate.
    #:
    #: We're storing this under a namespace, because the handler will
    #: normally set :py:attr:`_check_hostname` and trigger a deprecation
    #: error for that argument. We're controlling this ourselves and
    #: don't want to risk informing the parent of this.
    _rb_check_hostname: bool

    def __init__(
        self,
        *,
        local_site: (LocalSite | None),
        cert_manager: (CertificateManager | None) = None,
        check_hostname: bool = True,
        extra_cert_data: (str | None) = None,
    ) -> None:
        """Initialize the handler.

        Args:
            local_site (reviewboard.site.models.LocalSite):
                The Local Site the certificates would be associated with.

            cert_manager (reviewboard.certs.manager.CertificateManager,
                          optional):
                A specific Certificate Manager instance.

                If not provided, the default will be used.

            check_hostname (bool, optional):
                Whether to verify that the hostname in the URL matches
                the hostname in the certificate.

            extra_cert_data (str, optional):
                Optional PEM-formatted certificate data to use for
                verification.
        """
        self._cert_manager = cert_manager or default_cert_manager
        self._local_site = local_site
        self._extra_cert_data = extra_cert_data
        self._rb_check_hostname = check_hostname

        # On Python 3.12+, the parent builds a default SSL context if one
        # isn't provided, loading the system certificates in the process.
        # We build our own context per-request in https_open(), so pass a
        # placeholder to avoid that wasted work.
        super().__init__(context=ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT))

    def https_open(
        self,
        req: Request,
    ) -> HTTPResponse:
        """Open an HTTPS connection, converting SSL errors if needed.

        Args:
            req (urllib.request.Request):
                The request to open.

        Returns:
            http.client.HTTPResponse:
            The response from the server.

        Raises:
            reviewboard.certs.errors.CertificateVerificationError:
                An SSL certificate verification error occurred.

            Exception:
                A non-SSL URL error occurred.
        """
        parsed_url = urlparse(req.full_url)
        hostname = parsed_url.hostname or ''
        port = parsed_url.port or 443

        if hostname:
            context = self._cert_manager.build_ssl_context(
                hostname=hostname,
                port=port,
                local_site=self._local_site,
            )

            context.check_hostname = self._rb_check_hostname

            if extra_cert_data := self._extra_cert_data:
                try:
                    context.load_verify_locations(cadata=extra_cert_data)
                except ssl.SSLError as e:
                    logger.error(
                        'Failed to load legacy certificate data into HTTPS '
                        'SSL context for %s:%s: %s',
                        hostname, port, e,
                    )
        else:
            context = None

        self._context = context

        # Specially handle SSLErrors that come from the request, and let
        # anything else bubble up.
        try:
            return super().https_open(req)
        except URLError as e:
            reason = e.reason

            if isinstance(reason, ssl.SSLError):
                self._process_ssl_error(error=reason,
                                        hostname=hostname,
                                        port=port)

            raise

    def _process_ssl_error(
        self,
        *,
        error: ssl.SSLError,
        hostname: str,
        port: int,
    ) -> None:
        """Process the SSL error and raise a suitable verification exception.

        Args:
            error (ssl.SSLError):
                The error to process.

            hostname (str):
                The hostname that was attempted.

            port (int):
                The port that was attempted.

        Raises:
            reviewboard.certs.errors.CertificateVerificationError:
                An SSL certificate verification error occurred.
        """
        # This is an SSL error. Convert it to a
        # CertificateVerificationError.
        if isinstance(error, ssl.SSLCertVerificationError):
            code = (
                CertificateVerificationFailureCode
                .for_ssl_verify_code(error.verify_code)
            )
            detail_msg = error.verify_message
        else:
            code = CertificateVerificationFailureCode.OTHER
            detail_msg = str(error)

        # Fetch the certificate from the server.
        #
        # There's a non-zero chance that it won't be the correct
        # signature (it may have been a temporary glitch or some
        # misconfigured server in a fleet), but we can't get the cert
        # from the exception.
        certificate = Certificate.create_from_server(
            hostname=hostname,
            port=port,
        )

        raise CertificateVerificationError(
            code=code,
            certificate=certificate,
            detail_msg=detail_msg,
        )


def urlopen(
    url: str | Request,
    data: (_DataType | None) = None,
    timeout: Unsettable[float | None] = UNSET,
    *,
    local_site: (LocalSite | None) = None,
    cert_manager: (CertificateManager | None) = None,
) -> _UrlopenRet:
    """A wrapper around urlopen that supports certificate management.

    This is a simple, straight-forward compatibility wrapper around
    :py:func:`urllib.request.urlopen` that makes use of a custom HTTPS
    handler for certificate management and error reporting.

    An HTTPS handler backed by the certificate manager is always added to the
    request so that HTTP to HTTPS redirects behave as expected.

    Callers that need more advanced functionality (such as those that build
    their own list of handlers) should not use this, and instead should
    make use of :py:class:`CertificateVerificationHTTPSHandler`.

    Version Added:
        8.1

    Args:
        url (str or urllib.request.Request):
            The URL to connect to or the request to issue.

        data (object, optional):
            Data to pass to the request.

        timeout (float, optional):
            An explicit timeout for the request.

        local_site (reviewboard.site.models.LocalSite, optional):
            The Local Site the certificates would be associated with.

        cert_manager (reviewboard.certs.manager.CertificateManager,
                      optional):
            A specific Certificate Manager instance.

            If not provided, the default will be used.

    Returns:
        urllib.request._UrlopenRet:
        The response data for the request.
    """
    # Build the keyword arguments to pass to the opener or to urlopen().
    urlopen_kwargs: KwargsDict = {
        'data': data,
    }

    if timeout is not UNSET:
        urlopen_kwargs['timeout'] = timeout

    # Build the HTTPS handler used for certificate lookup.
    opener = build_opener(CertificateVerificationHTTPSHandler(
        cert_manager=cert_manager or default_cert_manager,
        local_site=local_site,
    ))

    # Perform the request.
    return opener.open(url, **urlopen_kwargs)
