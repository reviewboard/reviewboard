"""Certificate-related errors.

Version Added:
    6.0
"""

from __future__ import annotations

from enum import IntEnum
from typing import List, Optional, TYPE_CHECKING

from django.utils.translation import gettext as _, ngettext as N_

if TYPE_CHECKING:
    from reviewboard.certs.cert import (Certificate,
                                        CertificateFingerprints)


class CertificateVerificationFailureCode(IntEnum):
    """Error codes indicating a SSL/TLS certificate verification failure.

    These represent the main types of verification errors that Review Board
    may be able to automatically handle or present to the user in some form.

    There is no guarantee of a one-to-one mapping of failure codes to OpenSSL
    or SCM-specific SSL failures.

    The raw enum values should be considered opaque. Please refer only to the
    names.

    Version Added:
        6.0
    """

    #: There's an error not covered by the built-in failure codes.
    OTHER = -1

    #: The certificate is not trusted.
    #:
    #: This may be self-signed or using an unknown Certificate Authority.
    NOT_TRUSTED = 0

    #: The certificate has expired.
    EXPIRED = 1

    #: The certificate is not yet valid.
    NOT_YET_VALID = 2

    #: The hostname does not match the certificate.
    HOSTNAME_MISMATCH = 3


class BaseCertificateError(Exception):
    """Base class for all SSL/TLS certificate errors.

    Version Added:
        6.0
    """


class InvalidCertificateError(BaseCertificateError):
    """An error indicating an invalid/unsupported certificate file format.

    Version Added:
        6.0
    """


class CertificateStorageError(BaseCertificateError):
    """An error indicating a problem accessing or storing certificate data.

    Version Added:
        6.0
    """


class CertificateNotFoundError(CertificateStorageError):
    """An error indicating a certificate data was not found.

    Version Added:
        6.0
    """

    def __init__(
        self,
        msg: Optional[str] = None,
    ) -> None:
        """Initialize the error.

        Args:
            msg (str, optional):
                The optional custom error message.
        """
        super().__init__(msg or _('The SSL/TLS certificate was not found.'))


class InvalidCertificateFormatError(CertificateStorageError):
    """An error indicating an invalid/unsupported certificate file format.

    Version Added:
        6.0
    """

    ######################
    # Instance variables #
    ######################

    #: The loaded certificate data.
    #:
    #: Type:
    #:     bytes
    data: bytes

    #: The optional path to the certificate file.
    #:
    #: Type:
    #:     str
    path: Optional[str]

    def __init__(
        self,
        msg: Optional[str] = None,
        *,
        data: bytes,
        path: Optional[str] = None,
    ) -> None:
        """Initialize the error.

        Args:
            msg (str, optional):
                The optional custom error message.

            data (bytes):
                The loaded certificate data.

            path (str, optional):
                The optional path to the certificate file.
        """
        if not msg:
            if path:
                msg = _(
                    'Invalid certificate file found at "%s". This was '
                    'not in a supported format.'
                ) % path
            else:
                msg = _(
                    'Invalid certificate data (%r). This was not in a '
                    'supported format.'
                ) % b'%s...%s' % (data[:10], data[-10:])

        super().__init__(msg)

        self.data = data
        self.path = path


class CertificateVerificationError(BaseCertificateError):
    """An error indicating that certificate could not be verified.

    This is used to communicate that a certificate could not be verified,
    allowing code to present the verification error to a user or attempt a
    retry.

    Version Added:
        6.0:
        This replaces the legacy
        :py:class:`reviewboard.scmtools.errors.UnverifiedCertificateError`.
    """

    ######################
    # Instance variables #
    ######################

    #: The certificate details being presented, if available.
    #:
    #: Type:
    #:     reviewboard.certs.cert.Certificate
    certificate: Optional[Certificate]

    #: The reason the certificate could not be verified.
    #:
    #: Type:
    #:     CertificateVerificationFailureCode
    code: CertificateVerificationFailureCode

    #: Detailed text specifying why the certificate was not verified.
    #:
    #: This may represent an underlying error string from OpenSSL or another
    #: library.
    #:
    #: Type:
    #:     str
    detail_msg: Optional[str]

    #: A generic message for the certificate error.
    #:
    #: This won't include the extra certificate details, allowing a handler
    #: to represent those details separately.
    #:
    #: Type:
    #:     str
    generic_msg: str

    def __init__(
        self,
        msg: Optional[str] = None,
        *,
        code: CertificateVerificationFailureCode,
        certificate: Optional[Certificate] = None,
        detail_msg: Optional[str] = None,
    ) -> None:
        """Initialize the error message.

        This will compute a suitable default error message, based on the
        certificate and any failures.

        Args:
            msg (str, optional):
                An explicit error message to display.

            code (CertificateVerificationFailureCode):
                A verification code specifying the reason for the failure.

            detail_msg (str, optional):
                An optional detailed message specifying why the certificate was
                not verified.

                This may represent an underlying error string from OpenSSL or
                another library.

            certificate (reviewboard.certs.cert.Certificate, optional):
                The certificate details being presented, if any.
        """
        self.certificate = certificate
        self.code = code
        self.detail_msg = detail_msg

        super().__init__(self.build_message(msg))

    def build_message(
        self,
        msg: Optional[str],
    ) -> str:
        """Return a message for the error.

        This will compute details to show in the error message, and provide
        a default error message if one is not provided.

        Error messages may contain the following format string indicators:

        ``%(code)s``:
            The error code identifying the problem.

        ``%(hostname)s``:
            The hostname reflected in the certificate.

        Subclasses can override this or provide custom format messages in
        order to more accurately represent certificate failures.

        Args:
            msg (str):
                An optional custom templated error message.

        Returns:
            str:
            The resulting message for the error.
        """
        hostname: Optional[str] = None

        certificate = self.certificate
        code = self.code

        if certificate is not None:
            hostname = certificate.hostname

        if msg is None:
            if code == CertificateVerificationFailureCode.EXPIRED:
                if certificate is not None:
                    msg = _(
                        'The SSL certificate provided by %(hostname)s has '
                        'expired and can no longer be used.'
                    )
                else:
                    msg = _(
                        'The SSL certificate provided by the server has '
                        'expired and can no longer be used.'
                    )
            elif code == CertificateVerificationFailureCode.NOT_YET_VALID:
                if certificate is not None:
                    msg = _(
                        'The SSL certificate provided by %(hostname)s is not '
                        'yet valid and cannot be used.'
                    )
                else:
                    msg = _(
                        'The SSL certificate provided by the server is not '
                        'yet valid and cannot be used.'
                    )
            elif code == CertificateVerificationFailureCode.HOSTNAME_MISMATCH:
                if certificate is not None:
                    msg = _(
                        'The SSL certificate provided by %(hostname)s does '
                        'not match its hostname and may not be safe.'
                    )
                else:
                    msg = _(
                        'The SSL certificate provided by the server does '
                        'not match its hostname and may not be safe.'
                    )
            elif code == CertificateVerificationFailureCode.NOT_TRUSTED:
                if certificate is not None:
                    msg = _(
                        'The SSL certificate provided by %(hostname)s has not '
                        'been signed by a trusted Certificate Authority and '
                        'may not be safe. The certificate needs to be '
                        'verified in Review Board before the server can be '
                        'accessed.'
                    )
                else:
                    msg = _(
                        'The SSL certificate provided by the server has not '
                        'been signed by a trusted Certificate Authority and '
                        'may not be safe. The certificate needs to be '
                        'verified in Review Board before the server can be '
                        'accessed.'
                    )
            else:
                if certificate is not None:
                    msg = _(
                        'The SSL certificate provided by %(hostname)s could '
                        'not be verified and may not be safe. The certificate '
                        'must be valid and verified in Review Board before '
                        'the server can be accessed.'
                    )
                else:
                    msg = _(
                        'The SSL certificate provided by the server could not '
                        'be verified and may not be safe. The certificate '
                        'must be valid and verified in Review Board before '
                        'the server can be accessed.'
                    )

        msg = msg % {
            'code': self.code.name,
            'hostname': hostname,
        }

        self.generic_msg = msg

        if certificate is not None:
            msg = _('%(message)s Certificate details: %(cert_details)s') % {
                'cert_details': self.build_cert_details(),
                'message': msg,
            }

        return msg

    def build_cert_details(self) -> str:
        """Return details to show in the certificate error.

        This will include the hostname, port, issuer, and fingerprints, if
        any or all of those are available.

        Returns:
            str:
            The certificate details to show.
        """
        fingerprints: Optional[CertificateFingerprints] = None
        cert_details: List[str] = []
        certificate = self.certificate

        if certificate is not None:
            fingerprints = certificate.fingerprints
            issuer = certificate.issuer

            cert_details += [
                _('hostname="%s"') % certificate.hostname,
                _('port=%s') % certificate.port,
            ]

            if issuer:
                cert_details.append(_('issuer="%s"') % issuer)

            # Normalize the fingerprints, making sure we never have to work
            # with empty fingerprints.
            if fingerprints is not None and not fingerprints.is_empty():
                fingerprint_pairs: List[str] = []

                if fingerprints.sha1:
                    fingerprint_pairs.append(_('SHA1=%s')
                                             % fingerprints.sha1)

                if fingerprints.sha256:
                    fingerprint_pairs.append(_('SHA256=%s')
                                             % fingerprints.sha256)

                cert_details.append(
                    N_('fingerprint=%s',
                       'fingerprints=%s',
                       len(fingerprint_pairs))
                    % '; '.join(fingerprint_pairs))

        return ', '.join(cert_details)
