"""Certificates, fingerprints, and bundles.

Version Added:
    6.0
"""

from __future__ import annotations

import logging
import os
import re
import socket
import ssl

from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING
from uuid import uuid4

from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.x509.oid import NameOID
from django.utils import timezone as django_timezone
from django.utils.encoding import force_str
from django.utils.functional import cached_property
from django.utils.text import slugify
from django.utils.translation import gettext as _
from djblets.util.symbols import UNSET, Unsettable
from typelets.runtime import raise_invalid_type
from typing_extensions import Self

from reviewboard.certs.errors import (CertificateNotFoundError,
                                      CertificateStorageError,
                                      InvalidCertificateFormatError)

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from typing import Final, TypeVar

    from typelets.django.json import (SerializableDjangoJSONDict,
                                      SerializableDjangoJSONDictImmutable)

    _T = TypeVar('_T')


logger = logging.getLogger(__name__)


_CERT_PEM_RE = re.compile(
    br'-----BEGIN CERTIFICATE-----[\r\n]+'
    br'[A-Za-z0-9+/\r\n]+=*[\r\n]+'
    br'-----END CERTIFICATE-----'
)

_PRIVATE_KEY_PEM_RE = re.compile(
    br'-----BEGIN PRIVATE KEY-----[\r\n]+'
    br'[A-Za-z0-9+/\r\n]+=*[\r\n]+'
    br'-----END PRIVATE KEY-----'
)


def _format_fingerprint(
    fingerprint: bytes,
) -> str:
    """Return a string representation of a fingerprint.

    This will be in ``AA:BB:CC...`` format.

    Version Added:
        6.0

    Args:
        fingerprint (bytes):
            The raw fingerprint data to format.

    Returns:
        str:
        The formatted string representation.
    """
    return ':'.join(
        '%02X' % c
        for c in fingerprint
    )


class CertDataFormat(Enum):
    """Certificate data formats.

    Version Added:
        6.0
    """

    #: PEM-formatted certificate data.
    PEM = 'PEM'


class CertPurpose(Enum):
    """The purpose of a certificate.

    Version Added:
        8.0
    """

    #: A certificate used to verify and trust a server.
    TRUST = 'trust'

    #: A certificate used to identify the client for authentication.
    CLIENT = 'client'


class CertificateFingerprints:
    """Representation of certificate fingerprints.

    Version Added:
        6.0
    """

    #: Regex for matching a SHA1 fingerprint.
    #:
    #: Version Added:
    #:     8.0
    SHA1_FINGERPRINT_RE = re.compile(r'(?:[0-9A-F]{2}:){19}[0-9A-F]{2}',
                                     re.IGNORECASE)

    #: Regex for matching a SHA1 string.
    #:
    #: Version Added:
    #:     8.0
    SHA1_RE = re.compile(r'[0-9A-F]{40}',
                         re.IGNORECASE)

    #: Regex for matching a SHA256 fingerprint.
    #:
    #: Version Added:
    #:     8.0
    SHA256_FINGERPRINT_RE = re.compile(r'(?:[0-9A-F]{2}:){31}[0-9A-F]{2}',
                                       re.IGNORECASE)

    #: Regex for matching a SHA256 string.
    #:
    #: Version Added:
    #:     8.0
    SHA256_RE = re.compile(r'[0-9A-F]{64}',
                           re.IGNORECASE)

    #: Mapping of string lengths to pattern/attr/normalization flags.
    #:
    #: This works as a simple table to quickly locate a proper pattern,
    #: corresponding attribute for the constructor, and a flag indicating
    #: whether to perform normalization of the value.
    #:
    #: Version Added:
    #:     8.0
    _FINGERPRINT_INFO_BY_LENGTH: Final[Mapping[
        int,
        tuple[re.Pattern, str, bool],
    ]] = {
        40: (SHA1_RE, 'sha1', True),
        59: (SHA1_FINGERPRINT_RE, 'sha1', False),
        64: (SHA256_RE, 'sha256', True),
        95: (SHA256_FINGERPRINT_RE, 'sha256', False),
    }

    ######################
    # Instance variables #
    ######################

    #: The human-readable SHA1 fingerprint.
    sha1: (str | None) = None

    #: The human-readable SHA256 fingerprint.
    sha256: (str | None) = None

    @classmethod
    def from_json(
        cls,
        data: SerializableDjangoJSONDictImmutable,
    ) -> Self:
        """Return a new instance from a serialized JSON payload.

        The payload is expected to be in the following format:

        Keys:
            sha1 (str, optional):
                The human-readable SHA1 fingerprint in ``AA:BB:CC...`` form.

            sha256 (str, optional):
                The human-readable SHA256 fingerprint in ``AA:BB:CC...`` form.

        Args:
            data (dict):
                The JSON dictionary containing the fingerprint information.

        Returns:
            CertificateFingerprints:
            The parsed fingerprints instance.
        """
        sha1 = data.get('sha1') or None
        sha256 = data.get('sha256') or None

        if sha1 is not None and not isinstance(sha1, str):
            logger.warning('Got non-string value %r for "sha1" key for '
                           'fingerprint data=%r',
                           sha1, data)
            sha1 = None

        if sha256 is not None and not isinstance(sha256, str):
            logger.warning('Got non-string value %r for "sha256" key for '
                           'fingerprint data=%r',
                           sha256, data)
            sha256 = None

        return cls(sha1=sha1,
                   sha256=sha256)

    @classmethod
    def from_string(
        cls,
        fingerprint: str,
    ) -> Self | None:
        """Return a new instance from a single fingerprint string.

        This will normalize the provided fingerprint (stripping any
        whitespace), determine if this is SHA-1 or SHA-256, and then return a
        new instance if the value is supported.

        Version Added:
            8.0

        Args:
            fingerprint (str):
                The fingerprint string in ``AA:BB:CC...`` format.

        Returns:
            reviewboard.certs.cert.CertificateFingerprints:
            The resulting fingerprints instance, or ``None`` if the
            string length doesn't match a known algorithm.
        """
        fingerprint = fingerprint.strip()
        length = len(fingerprint)

        # This will look for the normalized fingerprint format and the
        # raw SHA format for both SHA256 and SHA1 variations. To keep
        # this performant, we'll key off the fingerprint pattern, field,
        # and normalization flag by length. If the length is a match but
        # nothing else is, we don't want to proceed with other checks.
        try:
            sha_re, field, normalize = cls._FINGERPRINT_INFO_BY_LENGTH[length]

            if sha_re.fullmatch(fingerprint):
                if normalize:
                    fingerprint = ':'.join(
                        fingerprint[i:i + 2]
                        for i in range(0, length, 2)
                    )

                return cls(**{
                    field: fingerprint.upper()
                })
        except KeyError:
            pass

        return None

    @classmethod
    def from_x509_cert(
        cls,
        x509_cert: x509.Certificate,
    ) -> Self:
        """Return a new instance from a Cryptography X509 certificate.

        Args:
            x509_cert (cryptography.x509.Certificate):
                The Cryptography certificate used to load the fingerprints.

        Returns:
            CertificateFingerprints:
            The loaded fingerprints instance.
        """
        return cls(
            sha1=_format_fingerprint(x509_cert.fingerprint(hashes.SHA1())),
            sha256=_format_fingerprint(x509_cert.fingerprint(hashes.SHA256())))

    def __init__(
        self,
        *,
        sha1: (str | None) = None,
        sha256: (str | None) = None,
    ) -> None:
        """Initialize the certificate fingerprints instance.

        Args:
            sha1 (str):
                The SHA1 fingerprint in ``AA:BB:CC...`` format.

            shaw256 (str):
                The SHA256 fingerprint in ``AA:BB:CC...`` format.
        """
        self.sha1 = sha1
        self.sha256 = sha256

    def to_json(self) -> SerializableDjangoJSONDictImmutable:
        """Serialize the fingerprints to a JSON payload.

        Returns:
            dict:
            The resulting JSON payload, containing:

            Keys:
                sha1 (str, optional):
                    A human-readable SHA1 fingerprint in ``AA:BB:CC...``
                    form.

                sha256 (str, optional):
                    A human-readable SHA256 fingerprint in ``AA:BB:CC...``
                    form.

            These keys will only be present if there are fingerprints
            available.
        """
        data: SerializableDjangoJSONDict = {}

        if self.sha1:
            data['sha1'] = self.sha1

        if self.sha256:
            data['sha256'] = self.sha256

        return data

    def is_empty(self) -> bool:
        """Return whether these fingerprints are empty.

        Returns:
            bool:
            ``True`` if the fingerprints are empty (no fingerprints are
            stored). ``False`` if there are fingerprints available.
        """
        return not bool(self.sha1) and not bool(self.sha256)

    def matches(
        self,
        other: CertificateFingerprints,
    ) -> bool:
        """Return whether one set of fingerprints matches another.

        This will compare any available fingerprints between two instances,
        returning whether there's a match.

        Args:
            other (CertificateFingerprints):
                The other instance to compare to.

        Returns:
            bool:
            ``True`` if there is a match between two instances. ``False``
            if there is not.
        """
        if self.is_empty() or other.is_empty():
            return False

        has_sha1 = self.sha1 is not None and other.sha1 is not None
        has_sha256 = self.sha256 is not None and other.sha256 is not None

        if not has_sha1 and not has_sha256:
            # There's nothing we can compare.
            return False

        # We now know that there's something to compare. We'll either be
        # comparing Nones safely, or we'll be comparing actual fingerprints.
        sha1_match = not has_sha1 or self.sha1 == other.sha1
        sha256_match = not has_sha256 or self.sha256 == other.sha256

        return sha1_match and sha256_match

    def __eq__(
        self,
        other: object,
    ) -> bool:
        """Return whether this object is equal to another.

        Two objects are equal if they're both
        :py:class:`CertificateFingerprints` instances and contain the same
        signatures.

        Args:
            other (object):
                The object to compare this to.

        Returns:
            bool:
            ``True`` if they are equal. ``False`` if they are not.
        """
        return (
            isinstance(other, CertificateFingerprints) and
            self.sha1 == other.sha1 and
            self.sha256 == other.sha256
        )

    def __repr__(self) -> str:
        """Return a string representation of the instance.

        Returns:
            str:
            The string representation.
        """
        return (
            '<CertificateFingerprints(sha1=%(sha1)r, sha256=%(sha256)r)>'
            % {
                'sha1': self.sha1,
                'sha256': self.sha256,
            }
        )


class Certificate:
    """A representation of a SSL/TLS certificate.

    This may be an incomplete representation, with only the hostname and at
    least one fingerprint being required. It can be used to convey information
    about certificates from a server or tool, or used to provide data for
    storage.

    There are two types of certificates:

    * Trust certificates.

      These are used to verify a remote server's certificate during TLS.
      These may be root CA certificates, intermediate CA certificates,
      self-signed server certificates, or other certificates used as trust
      anchors.

      They do not include a private key.

    * Client certificates.

      These are used to authenticate Review Board with a remote service during
      mutual TLS. This requires an associated private key.

    Consumers should take care not to modify any certificate data after
    loading. While it's possible to change the data, doing so can lead to
    incorrect results, as some data is computed and then cached on the
    instance and cannot be updated later.

    Version Changed:
        8.0:
        Added explicit support for specifying a certificate purpose.

    Version Added:
        6.0
    """

    ######################
    # Instance variables #
    ######################

    #: The loaded certificate data.
    #:
    #: This will always be available for stored certificates, but may not be
    #: available as part of error responses.
    #:
    #: If available, it will match the format specified in
    #: :py:attr:`data_format`.
    cert_data: bytes | None

    #: The format for the loaded certificate and private key data.
    data_format: CertDataFormat

    #: The hostname that would serve this certificate.
    #:
    #: Note that this may be a wildcard domain (e.g., ``*.example.com``).
    hostname: str

    #: The loaded private key data, if available.
    #:
    #: This will match the format specified in :py:attr:`data_format`.
    key_data: bytes | None

    #: The port on the host that would serve this certificate.
    port: int

    #: The purpose set for a certificate.
    #:
    #: This defines whether the certificate is used for trusting a remote
    #: server or authenticating Review Board with a service.
    #:
    #: Version Added:
    #:     8.0
    purpose: CertPurpose

    #: Fingerprints for the certificate.
    #:
    #: If not provided during construction, this will be loaded from
    #: :py:attr`cert_data` when needed (and if :py:attr:`cert_data` is
    #: provided).
    _fingerprints: Unsettable[CertificateFingerprints | None]

    #: The issuer (usually the hostname) of the certificate.
    #:
    #: If not provided during construction, this will be loaded from
    #: :py:attr`cert_data` when needed (and if :py:attr:`cert_data` is
    #: provided).
    _issuer: Unsettable[str | None]

    #: The subject (usually the hostname) of the certificate.
    #:
    #: If not provided during construction, this will be loaded from
    #: :py:attr`cert_data` when needed (and if :py:attr:`cert_data` is
    #: provided).
    _subject: Unsettable[str | None]

    #: The first date/time in which the certificate is valid.
    #:
    #: If not provided during construction, this will be loaded from
    #: :py:attr`cert_data` when needed (and if :py:attr:`cert_data` is
    #: provided).
    _valid_from: Unsettable[datetime | None]

    #: The last date/time in which the certificate is valid.
    #:
    #: If not provided during construction, this will be loaded from
    #: :py:attr`cert_data` when needed (and if :py:attr:`cert_data` is
    #: provided).
    _valid_through: Unsettable[datetime | None]

    @classmethod
    def create_from_files(
        cls,
        *,
        hostname: str,
        port: int,
        cert_path: str,
        key_path: (str | None) = None,
        data_format: CertDataFormat = CertDataFormat.PEM,
        purpose: CertPurpose = CertPurpose.TRUST,
    ) -> Self:
        """Return an instance parsed from a PEM bundle file.

        Version Changed:
            8.0:
            * Added the ``purpose`` argument.
            * This may now raise :py:exc:`ValueError` if providing an invalid
              combination of arguments.

        Args:
            hostname (str):
                The primary hostname the certificate represents, used for
                lookup.

            port (int):
                The port that served the certificate.

            cert_path (str):
                The path to the local certificate file.

            key_path (str):
                The path to the local private key.

            data_format (CertDataFormat, optional):
                The format of the data stored in ``cert_path``.

            purpose (CertPurpose, optional):
                The purpose of the certificate.

                This sets whether the certificate should be used to trust
                a remote server or authenticate Review Board.

                By default, the purpose is to trust the server.

                Version Added:
                    8.0

        Raises:
            ValueError:
                One or more arguments were invalid.

                Version Added:
                    8.0

            reviewboard.certs.errors.CertificateNotFoundError:
                One or more of the certificate files was not found.

            reviewboard.certs.errors.CertificateStorageError:
                There was an error loading the CA bundle.

                Details are in the error message.
        """
        # Validate the arguments based on the purpose of the certificate.
        if purpose == CertPurpose.TRUST:
            if key_path:
                raise ValueError(_(
                    'key_path cannot be provided when passing '
                    'purpose=CertPurpose.TRUST.'
                ))
        elif purpose == CertPurpose.CLIENT:
            if not key_path:
                raise ValueError(_(
                    'key_path must be provided when passing '
                    'purpose=CertPurpose.CLIENT.'
                ))
        else:
            raise_invalid_type(
                purpose,
                _(
                    'Received an invalid value for purpose= ({purpose})'
                ).format(purpose=purpose),
            )

        # Validate the file paths.
        if not cert_path:
            raise ValueError(_(
                'A certificate path must be provided.'
            ))

        if not os.path.exists(cert_path):
            raise CertificateNotFoundError(
                _('The SSL/TLS certificate was not found.'))

        if key_path and not os.path.exists(key_path):
            raise CertificateNotFoundError(
                _('The SSL/TLS private key was not found.'))

        try:
            with open(cert_path, 'rb') as fp:
                cert_data = fp.read()
        except IOError as e:
            error_id = str(uuid4())
            logger.error('[%s] Error reading SSL/TLS certificate file '
                         '"%s": %s',
                         error_id, cert_path, e)

            raise CertificateStorageError(
                _('Error reading SSL/TLS certificate file. Administrators can '
                  'find details in the Review Board server logs (error '
                  'ID %(error_id)s).')
                % {
                    'error_id': error_id,
                })

        if _CERT_PEM_RE.search(cert_data) is None:
            raise InvalidCertificateFormatError(data=cert_data,
                                                path=cert_path)

        if key_path is not None:
            try:
                with open(key_path, 'rb') as fp:
                    key_data = fp.read()
            except IOError as e:
                error_id = str(uuid4())
                logger.error('[%s] Error reading SSL/TLS private key file '
                             '"%s": %s',
                             error_id, cert_path, e)

                raise CertificateStorageError(
                    _('Error reading SSL/TLS private key file. Administrators '
                      'can find details in the Review Board server logs '
                      '(error ID %(error_id)s).')
                    % {
                        'error_id': error_id,
                    })

            if _PRIVATE_KEY_PEM_RE.search(key_data) is None:
                raise InvalidCertificateFormatError(data=key_data,
                                                    path=key_path)
        else:
            key_data = None

        return cls(hostname=hostname,
                   port=port,
                   cert_data=cert_data,
                   key_data=key_data,
                   purpose=purpose,
                   data_format=data_format)

    @classmethod
    def create_from_server(
        cls,
        *,
        hostname: str,
        port: int,
    ) -> Self | None:
        """Return a Certificate from a remote server.

        This is useful when inspecting a server or preparing an error
        response when certificate validation fails.

        Version Added:
            7.1

        Args:
            hostname (str):
                The hostname of the server.

            port (int):
                The port of the server.

        Returns:
            Certificate:
            The fetched certificate, or ``None`` if it could not be fetched.
        """
        try:
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE

            with socket.create_connection((hostname, port),
                                          timeout=10) as sock:
                with context.wrap_socket(sock,
                                         server_hostname=hostname) as ssock:
                    der_cert = ssock.getpeercert(binary_form=True)

            if not der_cert:
                raise ValueError('Returned certificate was empty.')

            pem_cert = ssl.DER_cert_to_PEM_cert(der_cert).encode('ascii')

            return cls(
                hostname=hostname,
                port=port,
                cert_data=pem_cert,
            )
        except Exception as e:
            logger.warning('Failed to fetch server certificate from %s:%s: %s',
                           hostname, port, e)

            return None

    def __init__(
        self,
        *,
        hostname: str,
        port: int,
        cert_data: (bytes | None) = None,
        key_data: (bytes | None) = None,
        data_format: CertDataFormat = CertDataFormat.PEM,
        purpose: CertPurpose = CertPurpose.TRUST,
        fingerprints: Unsettable[CertificateFingerprints] = UNSET,
        issuer: Unsettable[str] = UNSET,
        subject: Unsettable[str] = UNSET,
        valid_from: Unsettable[datetime] = UNSET,
        valid_through: Unsettable[datetime] = UNSET,
    ) -> None:
        """Initialize the certificate.

        Version Changed:
            8.0:
            Added the ``purpose`` argument.

        Args:
            hostname (str):
                The hostname that would serve this certificate.

            port (int):
                The port on the host that would serve this certificate.

            cert_data (bytes):
                The loaded certificate data.

                This must be in the format defined by ``data_format``.

            key_data (bytes, optional):
                The loaded private key data, if available.

                This must be in the format defined by ``data_format``.

            data_format (CertDataFormat, optional):
                The format used for ``cert_data`` and ``key_data``.

                This currently only accepts PEM-encoded data.

            purpose (CertPurpose, optional):
                The purpose of the certificate.

                This sets whether the certificate should be used to trust
                a remote server or authenticate Review Board.

                By default, the purpose is to trust the server.

                Version Added:
                    8.0

            subject (str, optional):
                The subject (usually the hostname) of the certificate.

                If not provided, this will be loaded from ``cert_data`` when
                needed (and if ``cert_data`` is provided).

            issuer (str, optional):
                The issuer of the certificate.

                If not provided, this will be loaded from ``cert_data`` when
                needed (and if ``cert_data`` is provided).

            valid_from (datetime, optional):
                The first date/time in which the certificate is valid.

                This must have a timezone associated with it.

                If not provided, this will be loaded from ``cert_data`` when
                needed (and if ``cert_data`` is provided).

            valid_through (datetime, optional):
                The last date/time in which the certificate is valid.

                This must have a timezone associated with it.

                If not provided, this will be loaded from ``cert_data`` when
                needed (and if ``cert_data`` is provided).

            fingerprints (CertificateFingerprints, optional):
                Fingerprints to set for the certificate.

                If not provided, this will be loaded from ``cert_data`` when
                needed (and if ``cert_data`` is provided).

        Raises:
            ValueError:
                One or more arguments were invalid.
        """
        # Validate the arguments based on the purpose of the certificate.
        #
        # Note that this Certificate may represent an incomplete state, so
        # it may not have the cert/key data. However, if it does have cert
        # data, we can at least verify the key data against it.
        if purpose == CertPurpose.TRUST:
            if key_data:
                raise ValueError(_(
                    'key_data cannot be provided when passing '
                    'purpose=CertPurpose.TRUST.'
                ))
        elif purpose == CertPurpose.CLIENT:
            if cert_data and not key_data:
                raise ValueError(_(
                    'key_data must be provided when passing '
                    'purpose=CertPurpose.CLIENT.'
                ))
        else:
            raise_invalid_type(
                purpose,
                _(
                    'Received an invalid value for purpose= ({purpose})'
                ).format(purpose=purpose),
            )

        if valid_from is not UNSET and django_timezone.is_naive(valid_from):
            raise ValueError('valid_from must contain a timezone.')

        if (valid_through is not UNSET and
            django_timezone.is_naive(valid_through)):
            raise ValueError('valid_through must contain a timezone.')

        self.cert_data = cert_data
        self.data_format = data_format
        self.hostname = hostname
        self.key_data = key_data
        self.port = port
        self.purpose = purpose
        self._fingerprints = fingerprints
        self._issuer = issuer
        self._subject = subject
        self._valid_from = valid_from
        self._valid_through = valid_through

    @property
    def fingerprints(self) -> CertificateFingerprints | None:
        """Fingerprints for the certificate.

        Type:
            CertificateFingerprints
        """
        fingerprints = self._fingerprints

        if fingerprints is UNSET:
            x509_cert = self.x509_cert

            if x509_cert is None:
                fingerprints = None
            else:
                fingerprints = CertificateFingerprints.from_x509_cert(
                    x509_cert)

            self._fingerprints = fingerprints

        return fingerprints

    @cached_property
    def x509_cert(self) -> x509.Certificate | None:
        """A Cryptography X509 Certificate representing this certificate.

        This will be created from the loaded from the certificate data stored
        in :py:attr:`cert_data`. The created instance will be locally cached
        for future lookups.

        If certificate data is not available, this will be ``None``.

        Type:
            cryptography.x509.Certificate
        """
        if self.cert_data is None:
            return None

        assert self.data_format == CertDataFormat.PEM, (
            'Certificate must use PEM format.'
        )
        assert self.cert_data, (
            'Certificate data must be loaded.'
        )

        return x509.load_pem_x509_certificate(self.cert_data)

    @property
    def subject(self) -> str | None:
        """The subject of the certificate.

        Type:
            str
        """
        subject = self._subject

        if subject is UNSET:
            subject = self._get_x509_attr(str, 'subject')
            self._subject = subject

        return subject

    @cached_property
    def subject_alternative_names(self) -> Sequence[str]:
        """The Subject Alternative Names of the certificate.

        This will include the string values for any DNS and IP addresses
        found in the Subject Alternative Names extension of the certificate,
        if present.

        Version Added:
            8.0

        Type:
            list of str
        """
        x509_cert = self.x509_cert

        if not x509_cert:
            return []

        try:
            san_ext = (
                x509_cert.extensions
                .get_extension_for_class(x509.SubjectAlternativeName)
            )

            return [
                str(item.value)
                for item in san_ext.value
                if isinstance(item, (x509.DNSName, x509.IPAddress))
            ]
        except x509.ExtensionNotFound:
            # The extension wasn't found in the cert, so return an empty list.
            return []
        except Exception as e:
            logger.exception('Unexpected error retrieving SAN values for '
                             'x509 cert %r: %s',
                             x509_cert, e)

            return []

    @property
    def issuer(self) -> str | None:
        """The issuer of the certificate.

        Type:
            str
        """
        issuer = self._issuer

        if issuer is UNSET:
            issuer = self._get_x509_attr(str, 'issuer')
            self._issuer = issuer

        return issuer

    @property
    def valid_from(self) -> datetime | None:
        """The date/time in which the certificate is first valid.

        Type:
            datetime.datetime
        """
        valid_from = self._valid_from

        if valid_from is UNSET:
            valid_from = self._get_x509_attr(datetime, 'not_valid_before')
            self._valid_from = valid_from

        return valid_from

    @property
    def valid_through(self) -> datetime | None:
        """The last date/time in which the certificate is valid.

        Type:
            datetime.datetime
        """
        valid_through = self._valid_through

        if valid_through is UNSET:
            valid_through = self._get_x509_attr(datetime, 'not_valid_after')
            self._valid_through = valid_through

        return valid_through

    @property
    def is_valid(self) -> bool:
        """Whether this certificate is still considered valid.

        The certificate is valid if the current date/time is within its
        validity date range.

        Type:
            bool
        """
        valid_from = self.valid_from
        valid_through = self.valid_through

        return (valid_from is not None and
                valid_through is not None and
                valid_from <= django_timezone.now() <= valid_through)

    @property
    def is_wildcard(self) -> bool:
        """Whether this is a wildcard certificate.

        Wildcard certificates pertain to multiple domains (e.g.,
        ``*.example.com``, ``*a.example.com``, or ``b*.example.com``).

        Type:
            bool
        """
        return '*' in self.hostname

    def to_json(self) -> SerializableDjangoJSONDictImmutable:
        """Serialize the certificate to data ready to be serialized to JSON.

        Returns:
            dict:
            The resulting JSON payload, containing:

            Keys:
                fingerprints (dict):
                    A dictionary of fingerprints for the certificate, or
                    ``None`` if not available.

                hostname (str):
                    The hostname serving the certificate.

                issuer (str):
                    The issuer of the certificate, or ``None`` if not
                    available.

                port (int):
                    The port on the host serving the certificate.

                purpose (str):
                    The purpose of the certificate.

                    Version Added:
                        8.0

                subject (str):
                    The subject of the certificate, or ``None`` if not
                    available.

                valid_from (str):
                    The first date/time in which the certificate is valid, or
                    ``None`` if not available.

                    This will be in :term:`ISO8601 format`.

                valid_through (str):
                    The last date/time in which the certificate is valid, or
                    ``None`` if not available.

                    This will be in :term:`ISO8601 format`.
        """
        return {
            'fingerprints': self.fingerprints,
            'hostname': self.hostname,
            'issuer': self.issuer,
            'port': self.port,
            'purpose': self.purpose.value,
            'subject': self.subject,
            'valid_from': self.valid_from,
            'valid_through': self.valid_through,
        }

    def write_cert_file(
        self,
        path: str,
    ) -> None:
        """Write the certificate data to a file.

        Args:
            path (str):
                The file path where the certificate data will be written.

        Raises:
            reviewboard.certs.errors.CertificateStorageError:
                There was an error writing the file.
        """
        cert_data = self.cert_data

        assert cert_data, 'Cannot write empty certificate data to file.'

        try:
            with open(path, 'wb') as fp:
                fp.write(cert_data)
        except IOError as e:
            error_id = str(uuid4())
            logger.error('[%s] Error writing SSL/TLS certificate file '
                         '"%s": %s',
                         error_id, path, e)

            raise CertificateStorageError(
                _('Error writing SSL/TLS certificate file. Administrators can '
                  'find details in the Review Board server logs (error '
                  'ID %(error_id)s).')
                % {
                    'error_id': error_id,
                })

    def write_key_file(
        self,
        path: str,
    ) -> None:
        """Write the private key data to a file.

        Args:
            path (str):
                The file path where the private key data will be written.

        Raises:
            reviewboard.certs.errors.CertificateStorageError:
                There was an error writing the file.
        """
        key_data = self.key_data

        assert key_data, 'Cannot write empty certificate key data to file.'

        try:
            with open(path, 'wb') as fp:
                fp.write(key_data)
        except IOError as e:
            error_id = str(uuid4())
            logger.error('[%s] Error writing SSL/TLS private key file '
                         '"%s": %s',
                         error_id, path, e)

            raise CertificateStorageError(
                _('Error writing SSL/TLS private key file. Administrators can '
                  'find details in the Review Board server logs (error '
                  'ID %(error_id)s).')
                % {
                    'error_id': error_id,
                })

    def _get_x509_attr(
        self,
        attr_type: type[_T],
        field_name: str,
    ) -> _T | None:
        """Return a normalized value for an X509.Certificate attribute.

        Any "Name" fields will be converted to a string.

        Any datetime fields will be made aware, using UTC.

        If the certificate could not be loaded, this will always return
        ``None``.

        Args:
            field_name (str):
                The name of the field on the certificate.

        Returns:
            object:
            The resulting value, or ``None``.
        """
        value: (_T | None) = None
        x509_cert = self.x509_cert

        if x509_cert is not None:
            x509_value = getattr(x509_cert, field_name)

            if isinstance(x509_value, x509.Name):
                x509_value = force_str(
                    x509_value
                    .get_attributes_for_oid(NameOID.COMMON_NAME)[0]
                    .value
                )
            elif (isinstance(x509_value, datetime) and
                  django_timezone.is_naive(x509_value)):
                x509_value = django_timezone.make_aware(x509_value,
                                                        timezone=timezone.utc)

            assert isinstance(x509_value, attr_type)

            value = x509_value

        return value

    def __repr__(self) -> str:
        """Return a string representation of the instance.

        Returns:
            str:
            The string representation.
        """
        return (
            f'<Certificate(hostname={self.hostname!r},'
            f' port={self.port!r},'
            f' purpose={self.purpose},'
            f' fingerprints={self.fingerprints!r})>'
        )


class CertificateBundle:
    """A bundle of root and intermediary certificates.

    This represents a "CA bundle," which specifies a root certificate and any
    necessary intermediary certificates used to validate other certificates,
    including those signed using an in-house certificate authority.

    Consumers should take care not to modify any certificate data after
    loading. While it's possible to change the data, doing so can lead to
    incorrect results, as some data is computed and then cached on the
    instance and cannot be updated later.

    Version Added:
        6.0
    """

    ######################
    # Instance variables #
    ######################

    #: The loaded data of the certificate bundle.
    bundle_data: bytes

    #: The format for the loaded certificate and private key data.
    data_format: CertDataFormat

    #: The name of this bundle.
    #:
    #: This is in :term:`slug` format.
    name: str

    @classmethod
    def create_from_file(
        cls,
        *,
        name: str,
        path: str,
    ) -> Self:
        """Return an instance parsed from a PEM bundle file.

        Args:
            name (str):
                The name of this bundle file.

                This must be in :term:`slug` format.

            path (str):
                The path to the file.

        Raises:
            reviewboard.certs.errors.CertificateStorageError:
                There was an error loading the CA bundle.

                Details are in the error message.
        """
        if not os.path.exists(path):
            raise CertificateNotFoundError(
                _('The SSL/TLS CA bundle was not found.'))

        try:
            with open(path, 'rb') as fp:
                data = fp.read()
        except IOError as e:
            error_id = str(uuid4())
            logger.error('[%s] Error reading SSL/TLS CA bundle file '
                         '"%s": %s',
                         error_id, path, e)

            raise CertificateStorageError(
                _('Error loading SSL/TLS CA bundle file. Administrators can '
                  'find details in the Review Board server logs (error '
                  'ID %(error_id)s).')
                % {
                    'error_id': error_id,
                })

        if _CERT_PEM_RE.search(data) is None:
            raise InvalidCertificateFormatError(data=data,
                                                path=path)

        return cls(bundle_data=data,
                   data_format=CertDataFormat.PEM,
                   name=name)

    def __init__(
        self,
        *,
        bundle_data: bytes,
        data_format: CertDataFormat = CertDataFormat.PEM,
        name: str = 'certs',
    ) -> None:
        """Initialize the certificate bundle.

        Args:
            bundle_data (bytes):
                The loaded data of the certificate bundle.

            data_format (CertDataFormat, optional):
                The format used for ``contents``.

                This currently only accepts PEM-encoded data.

            name (str, optional):
                The name of the certificate bundle.
        """
        if name != slugify(name):
            raise ValueError(
                _('The certificate bundle name "%(name)s" must be in '
                  '"slug" format (using characters "a-z", "0-9", "-").')
                % {
                    'name': name,
                })

        self.bundle_data = bundle_data
        self.data_format = data_format
        self.name = name

    def write_bundle_file(
        self,
        path: str,
    ) -> None:
        """Write the certificate bundle data to a file.

        Args:
            path (str):
                The file path where the certificate bundle data will be
                written.

        Raises:
            reviewboard.certs.errors.CertificateStorageError:
                There was an error writing the file.
        """
        try:
            with open(path, 'wb') as fp:
                fp.write(self.bundle_data)
        except IOError as e:
            error_id = str(uuid4())
            logger.error('[%s] Error writing SSL/TLS CA bundle file '
                         '"%s": %s',
                         error_id, path, e)

            raise CertificateStorageError(
                _('Error writing SSL/TLS CA bundle file. Administrators can '
                  'find details in the Review Board server logs (error '
                  'ID %(error_id)s).')
                % {
                    'error_id': error_id,
                })
