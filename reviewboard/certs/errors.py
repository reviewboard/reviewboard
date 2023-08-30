"""Certificate-related errors.

Version Added:
    6.0
"""

from __future__ import annotations

from typing import Optional

from django.utils.translation import gettext as _


class InvalidCertificateError(Exception):
    """An error indicating an invalid/unsupported certificate file format.

    Version Added:
        6.0
    """


class CertificateStorageError(Exception):
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
