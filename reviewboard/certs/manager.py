"""Main interface for managing and looking up SSL/TLS certificates.

Any code that needs to look up SSL/TLS certificates or CA bundles for local
are expected to use :py:class:`CertificateManager`. There's a
:py:data:`cert_manager` instance available for use.

Version Added:
    6.0
"""

from __future__ import annotations

import logging
import os
import ssl
from typing import Optional, TYPE_CHECKING, cast
from urllib.parse import urlparse

from django.core.cache import cache
from django.utils.functional import SimpleLazyObject
from django.utils.text import slugify
from django.utils.translation import gettext as _
from djblets.cache.backend import cache_memoize, make_cache_key
from djblets.siteconfig.models import SiteConfiguration
from djblets.util.filesystem import safe_join
from djblets.util.typing import (KwargsDict,
                                 SerializableJSONDictImmutable)
from typing_extensions import Final, NotRequired, TypeAlias, TypedDict

from reviewboard.admin.server import get_data_dir
from reviewboard.certs.cert import CertificateFingerprints
from reviewboard.certs.errors import (CertificateNotFoundError,
                                      InvalidCertificateError)
from reviewboard.certs.storage import cert_storage_backend_registry
from reviewboard.certs.storage.base import (BaseCertificateStorageBackend,
                                            BaseStoredCertificate,
                                            BaseStoredCertificateBundle,
                                            BaseStoredCertificateFingerprints)

if TYPE_CHECKING:
    from reviewboard.certs.cert import Certificate, CertificateBundle
    from reviewboard.site.models import LocalSite

    _CertStorageBackend: TypeAlias = BaseCertificateStorageBackend[
        BaseStoredCertificate,
        BaseStoredCertificateBundle,
        BaseStoredCertificateFingerprints,
    ]


logger = logging.getLogger(__name__)


class CertificateFilePaths(TypedDict):
    """A dictionary of file paths for a certificate and private key.

    Version Added:
        6.0
    """

    #: The absolute path to a certificate file.
    #:
    #: Type:
    #:     str
    cert_file: str

    #: The absolute path to a private key file.
    #:
    #: This is only included if a private key is present.
    #:
    #: Type:
    #:     str
    key_file: NotRequired[str]


class CertificateManager:
    """A manager for looking up and working with SSL/TLS certificates.

    The certificate manager is used to perform common certificate management
    and lookup operations and to mark certificates as verified. It's the
    primary interface between communication channels and stored certificates.

    Any code that communicates with an external server that may be protected
    by a TLS/SSL certificate is expected to use the certificate manager to
    retrieve fingerprints, certificate data, certificate paths, or CA bundles
    and pass them to the communication code, in order to ensure that
    certificates can be verified.

    Access to the underlying :py:attr:`storage_backend` is available, for
    code that needs to more closely manage the storage of certificate-related
    information.

    Additional storage backends can be registered and configured, providing
    other options for certificate storage management.

    To set a custom storage backend, set the ``certs_storage_backend``
    setting in the Site Configuration and specify the registered ID of the
    storage backend.

    Version Added:
        6.0
    """

    #: The ID of the default storage backend.
    #:
    #: Type:
    #:     str
    DEFAULT_STORAGE_ID: Final[str] = 'file'

    ######################
    # Instance variables #
    ######################

    #: The root path for certificate storage.
    #:
    #: All storage backends will have a subdirectory within here that they
    #: can use for reading/writing certificate storage data.
    #:
    #: Type:
    #:     str
    _root_storage_path: str

    #: A loaded instance of the current storage backend.
    #:
    #: Type:
    #:     reviewboard.certs.storage.base.BaseCertificateStorageBackend
    _storage_backend: Optional[_CertStorageBackend]

    def __init__(self) -> None:
        """Initialize the certificate manager."""
        self._storage_backend = None
        self._root_storage_path = os.path.join(get_data_dir(), 'rb-certs')

    @property
    def storage_backend(self) -> _CertStorageBackend:
        """The current configured storage backend.

        If the storage backend is not loaded, or the last-accessed backend
        is no longer the configured backend, then a new one will be loaded and
        returned.

        If a new storage backend cannot be loaded, then the default file-based
        storage backend will be used.

        Consumers are encouraged to assign the results to a local variable
        before use, rather than repeatedly calling this. However, they should
        not hold onto an instance beyond the lifetime of a HTTP request.

        Type:
            reviewboard.certs.storage.base.BaseCertificateStorageBackend
        """
        siteconfig = SiteConfiguration.objects.get_current()
        configured_backend_id = siteconfig.get('certs_storage_backend',
                                               default=self.DEFAULT_STORAGE_ID)

        if not isinstance(configured_backend_id, str):
            logger.error('Site configuration key "certs_storage_backend" '
                         'has a non-string value (%r). Falling back to '
                         '"%s".',
                         configured_backend_id, self.DEFAULT_STORAGE_ID)
            configured_backend_id = self.DEFAULT_STORAGE_ID

        backend = self._storage_backend

        if backend is None or configured_backend_id != backend.backend_id:
            # We need to set and return a new storage backend. Either we
            # didn't have one loaded before or it changed due to a
            # configuration change.
            backend_cls = cert_storage_backend_registry.get_backend(
                configured_backend_id)

            if backend_cls is None:
                logger.error('Unable to load SSL/TLS certificate storage '
                             'backend "%s". Falling back to file-based '
                             'storage.',
                             configured_backend_id)

                backend_cls = cert_storage_backend_registry.get_backend(
                    self.DEFAULT_STORAGE_ID)
                assert backend_cls is not None

            assert backend_cls.backend_id
            storage_path = safe_join(self._root_storage_path,
                                     slugify(backend_cls.backend_id))

            backend = backend_cls(storage_path=storage_path)
            self._storage_backend = backend

        return backend

    def add_ca_bundle(
        self,
        bundle: CertificateBundle,
        *,
        local_site: Optional[LocalSite] = None,
    ) -> BaseStoredCertificateBundle:
        """Add a root CA bundle to storage.

        The certificate bundle's name along with ``local_site`` are considered
        unique within the storage backend. If there's an existing bundle with
        this information, it will be replaced.

        Args:
            bundle (reviewboard.certs.cert.CertificateBundle):
                The bundle to add.

            local_site (reviewboard.site.models.LocalSite, optional):
                An optional LocalSite that owns the certificate.

                If ``None``, the global site will be used.

        Returns:
            reviewboard.certs.storage.base.BaseStoredCertificateBundle:
            The stored data for the certificate bundle.
        """
        return self.storage_backend.add_ca_bundle(bundle,
                                                  local_site=local_site)

    def delete_ca_bundle(
        self,
        *,
        name: str,
        local_site: Optional[LocalSite] = None,
    ) -> None:
        """Delete a root CA bundle from storage.

        Args:
            name (str):
                The unique name of the CA bundle in storage.

                This is in :term:`slug` format.

            local_site (reviewboard.site.models.LocalSite, optional):
                An optional LocalSite that owns the certificate.

                If ``None``, the global site will be used.

        Raises:
            reviewboard.cert.errors.CertificateNotFoundError:
                The CA bundle was not found.

            reviewboard.cert.errors.CertificateStorageError:
                There was an error deleting this CA bundle.
        """
        self.storage_backend.delete_ca_bundle(name=name,
                                              local_site=local_site)

    def get_ca_bundle(
        self,
        *,
        name: str,
        local_site: Optional[LocalSite] = None,
    ) -> Optional[CertificateBundle]:
        """Return a CA bundle.

        Args:
            name (str):
                The unique name of the CA bundle in storage.

                This is in :term:`slug` format.

            local_site (reviewboard.site.models.LocalSite, optional):
                An optional LocalSite that owns the bundle.

                If ``None``, the global site will be used.

        Returns:
            CertificateBundle:
            The resulting certificate bundle.
        """
        stored_bundle = self.storage_backend.get_stored_ca_bundle(
            name=name,
            local_site=local_site)

        if not stored_bundle:
            return None

        return stored_bundle.bundle

    def get_ca_bundles_dir(
        self,
        *,
        local_site: Optional[LocalSite] = None,
    ) -> str:
        """Return a path containing all CA bundle files.

        Args:
            local_site (reviewboard.site.models.LocalSite, optional):
                An optional LocalSite that owns the bundles.

                If ``None``, the global site will be used.

        Returns:
            str:
            The path to the bundles directory.
        """
        return self.storage_backend.get_ca_bundles_dir(local_site=local_site)

    def add_certificate(
        self,
        certificate: Certificate,
        *,
        local_site: Optional[LocalSite] = None,
    ) -> BaseStoredCertificate:
        """Add a certificate to storage.

        Once added, the certificate's fingerprints will also be marked as
        verified.

        Args:
            certificate (reviewboard.certs.cert.Certificate):
                The certificate to add.

            local_site (reviewboard.site.models.LocalSite, optional):
                An optional LocalSite that will own the certificate.

                If ``None``, the global site will be used.

        Returns:
            reviewboard.certs.storage.base.BaseStoredCertificate:
            The stored data for the certificate.

        Raises:
            reviewboard.certs.errors.InvalidCertificateError:
                The provided certificate is invalid and can't be stored.
        """
        try:
            certificate.x509_cert
        except Exception:
            raise InvalidCertificateError(
                _("The provided certificate data is invalid or corrupt and "
                  "can't be stored."))

        assert certificate.fingerprints is not None

        stored_cert = self.storage_backend.add_certificate(
            certificate=certificate,
            local_site=local_site)

        # Make sure this is marked as verified.
        self.mark_certificate_verified(
            hostname=certificate.hostname,
            port=certificate.port,
            local_site=local_site,
            fingerprints=certificate.fingerprints)

        return stored_cert

    def delete_certificate(
        self,
        *,
        hostname: str,
        port: int,
        local_site: Optional[LocalSite] = None,
    ) -> None:
        """Delete a certificate from storage.

        Once deleted, the certificate's fingerprints will no longer be marked
        as verified.

        Args:
            hostname (str):
                The hostname of the certificate to delete.

            port (int):
                The port that served the certificate.

            local_site (reviewboard.site.models.LocalSite, optional):
                An optional LocalSite that owns the certificate.

                If ``None``, the global site will be used.
        """
        self.storage_backend.delete_certificate(
            hostname=hostname,
            port=port,
            local_site=local_site)

        # Remove any verification information for this certificate.
        self.remove_certificate_verification(
            hostname=hostname,
            port=port,
            local_site=local_site)

    def get_certificate(
        self,
        *,
        hostname: str,
        port: int,
        local_site: Optional[LocalSite] = None,
    ) -> Optional[Certificate]:
        """Return a certificate for the given host and port.

        Args:
            hostname (str):
                The hostname matching the certificate.

            port (int):
                The port serving the certificate.

            local_site (reviewboard.site.models.LocalSite, optional):
                An optional LocalSite that owns the certificate.

                If ``None``, the global site will be used.

        Returns:
            reviewboard.certs.storage.base.BaseStoredCertificate:
            The resulting certificate, or ``None`` if not found.

        Raises:
            reviewboard.cert.errors.CertificateStorageError:
                There was an error retrieving this certificate.
        """
        stored_cert = self.storage_backend.get_stored_certificate(
            hostname=hostname,
            port=port,
            local_site=local_site)

        if not stored_cert:
            return None

        return stored_cert.certificate

    def get_certificate_file_paths(
        self,
        *,
        hostname: str,
        port: int,
        local_site: Optional[LocalSite] = None,
    ) -> Optional[CertificateFilePaths]:
        """Return file paths for a certificate.

        Args:
            hostname (str):
                The hostname matching the certificate.

            port (int):
                The port serving the certificate.

            local_site (reviewboard.site.models.LocalSite, optional):
                An optional LocalSite that owns the certificate.

                If ``None``, the global site will be used.

        Returns:
            CertificateFilePaths:
            The dictionary of file paths, or ``None`` if no paths are found.

        Raises:
            reviewboard.cert.errors.CertificateStorageError:
                There was an error retrieving this certificate.
        """
        # TODO: Cache this in the future, to avoid repeated lookups.
        #       We will need to invalidate on cert updates.
        stored_cert = self.storage_backend.get_stored_certificate(
            hostname=hostname,
            port=port,
            local_site=local_site)

        if not stored_cert:
            return None

        result: CertificateFilePaths = {
            'cert_file': stored_cert.get_cert_file_path(),
        }

        key_file_path = stored_cert.get_key_file_path()

        if key_file_path:
            result['key_file'] = key_file_path

        return result

    def mark_certificate_verified(
        self,
        *,
        hostname: str,
        port: int,
        fingerprints: CertificateFingerprints,
        local_site: Optional[LocalSite] = None,
    ) -> None:
        """Mark a certificate as verified.

        The verification information will be stored in the certificate storage
        backend. It will also be cached in the cache backend for fast
        retrieval and subsequent verification.

        Args:
            hostname (str):
                The hostname that served the certificate.

            port (int):
                The port that served the certificate.

            fingerprints (reviewboard.certs.cert.CertificateFingerprints):
                The fingerprints to store in the verification storage.

                It's recommended to make this as thorough as possible, in
                order to more accurately match fingerprints that may come
                from different communication channels.

            local_site (reviewboard.site.models.LocalSite, optional):
                An optional LocalSite to associate with the verification
                information.

                If ``None``, the global site will be used.

        Raises:
            reviewboard.certs.errors.InvalidCertificateError:
                The fingerprints were empty.
        """
        if fingerprints.is_empty():
            raise ValueError(
                'One or more SSL certificate fingerprints must be provided.'
            )

        # Store the fingerprints for verification in the backend.
        self.storage_backend.add_fingerprints(
            fingerprints,
            hostname=hostname,
            port=port,
            local_site=local_site)

        # Store this key in cache for efficient lookup.
        cache_key = self._build_fingerprints_cache_key(
            hostname=hostname,
            port=port,
            local_site=local_site)

        cache.set(make_cache_key(cache_key), fingerprints.to_json())

    def remove_certificate_verification(
        self,
        *,
        hostname: str,
        port: int,
        local_site: Optional[LocalSite] = None,
    ) -> None:
        """Remove verification information for a certificate.

        Fingerprints for this certificate will no longer be returned as
        verified.

        Args:
            hostname (str):
                The hostname that served the certificate.

            port (int):
                The port that served the certificate.

            local_site (reviewboard.site.models.LocalSite, optional):
                An optional LocalSite to associate with the verification
                information.

                If ``None``, the global site will be used.
        """
        # Store the fingerprints for verification in the backend.
        try:
            self.storage_backend.delete_fingerprints(
                hostname=hostname,
                port=port,
                local_site=local_site)
        except CertificateNotFoundError:
            # We can safely ignore this. The data wasn't found in storage,
            # which is the end goal anyway.
            pass

        # Remove any cached information about these fingerprints.
        cache.delete(make_cache_key(self._build_fingerprints_cache_key(
            hostname=hostname,
            port=port,
            local_site=local_site)))

    def get_verified_fingerprints(
        self,
        *,
        hostname: str,
        port: int,
        local_site: Optional[LocalSite] = None,
    ) -> Optional[CertificateFingerprints]:
        """Return certificate fingerprints from storage.

        Args:
            hostname (str):
                The hostname that served the certificate.

            port (int):
                The port that served the certificate.

            local_site (reviewboard.site.models.LocalSite, optional):
                An optional LocalSite to associate with the verification
                information.

                If ``None``, the global site will be used.

        Returns:
            reviewboard.certs.cert.CertificateFingerprints:
            The resulting fingerprints, or ``None`` if not found in storage.
        """
        cache_key = self._build_fingerprints_cache_key(
            hostname=hostname,
            port=port,
            local_site=local_site)

        def _get_stored() -> Optional[SerializableJSONDictImmutable]:
            stored_fingerprints = self.storage_backend.get_stored_fingerprints(
                hostname=hostname,
                port=port,
                local_site=local_site)

            if stored_fingerprints is None:
                return None

            return stored_fingerprints.fingerprints.to_json()

        data = cast(Optional[SerializableJSONDictImmutable],
                    cache_memoize(cache_key, _get_stored))

        if not data:
            return None

        return CertificateFingerprints.from_json(data)

    def is_certificate_verified(
        self,
        *,
        hostname: str,
        port: int,
        latest_fingerprints: CertificateFingerprints,
        local_site: Optional[LocalSite] = None,
    ) -> bool:
        """Return whether a certificate is verified.

        This will determine verification based on the fingerprints. If one or
        more fingerprints match, and no fingerprints fail to match, then the
        certificate is considered verified.

        The result will be cached in the cache backend for fast retrieval and
        subsequent verification.

        Args:
            hostname (str):
                The hostname of the server to check for verification.

            port (int):
                The port of the server to check for verification.

            latest_fingerprints (reviewboard.certs.cert.
                                 CertificateFingerprints):
                The latest fingerprints from the server to check verified
                fingerprints against.

            local_site (reviewboard.site.models.LocalSite, optional):
                An optional LocalSite the stored verification information
                would be associated with.

                If ``None``, the global site will be used.

        Returns:
            bool:
            ``True`` if the fingerprints have been verified. ``False`` if
            they have not.
        """
        verified_fingerprints = self.get_verified_fingerprints(
            hostname=hostname,
            port=port,
            local_site=local_site)

        return (verified_fingerprints is not None and
                verified_fingerprints.matches(latest_fingerprints))

    def build_ssl_context(
        self,
        *,
        hostname: str,
        port: int,
        local_site: Optional[LocalSite] = None,
    ) -> ssl.SSLContext:
        """Return a configured SSL context for the given host.

        The resulting :py:class:`ssl.SSLContext` will be configured to use
        the CA bundles and certificates applicable to this host, port, and
        Local Site.

        Args:
            hostname (str):
                The hostname of the server to connect to.

            port (int):
                The port of the server to connect to.

            local_site (reviewboard.site.models.LocalSite, optional):
                The Local Site that owns any stored certificates.

        Returns:
            ssl.SSLContext:
            The resulting SSL context.
        """
        cabundles_dir = self.get_ca_bundles_dir(local_site=local_site)
        cert_paths = self.get_certificate_file_paths(hostname=hostname,
                                                     port=port,
                                                     local_site=local_site)

        context = ssl.create_default_context()
        context.load_verify_locations(capath=cabundles_dir)

        if cert_paths:
            context.load_cert_chain(certfile=cert_paths['cert_file'],
                                    keyfile=cert_paths.get('key_file'))

        return context

    def build_urlopen_kwargs(
        self,
        *,
        url: str,
        local_site: Optional[LocalSite] = None,
    ) -> KwargsDict:
        """Return SSL-related keyword arguments for a urlopen request.

        This will build keyword arguments that can be passed when calling
        :py:func:`urllib.request.urlopen`.

        If connecting to a HTTPS-based site, the keyword arguments will contain
        a pre-configured SSL context based on any stored CA bundles or
        certificates.

        If not connecting to a HTTPS-based site, this will be an empty
        dictionary.

        Args:
            url (str):
                The URL to connect to.

            local_site (reviewboard.site.models.LocalSite, optional):
                The Local Site that owns any stored certificates.

        Returns:
            dict:
            The dictionary of keyword arguments.
        """
        parsed_url = urlparse(url)

        if parsed_url and parsed_url.hostname and parsed_url.scheme == 'https':
            return {
                'context': self.build_ssl_context(
                    hostname=parsed_url.hostname,
                    port=parsed_url.port or 443,
                    local_site=local_site),
            }

        return {}

    def _build_fingerprints_cache_key(
        self,
        *,
        hostname: str,
        port: int,
        local_site: Optional[LocalSite],
    ) -> str:
        """Return a cache key for verification.

        This key should be normalized before going into cache.

        Args:
            hostname (str):
                The hostname to include in the cache key.

            port (int):
                The port to include in the cache key.

            local_site (reviewboard.site.models.LocalSite):
                An optional LocalSite to include in the cache key.

        Returns:
            str:
            The resulting cache key.
        """
        backend_id = self.storage_backend.backend_id
        key = f'rb-ssl-fingerprints:{backend_id}'

        if local_site:
            key = f'{key}:{local_site.pk}'

        key = f'{key}:{hostname}:{port}'

        return key


#: The main certificate manager for Review Board.
#:
#: Version Added:
#:     6.0
#:
#: Type:
#:     CertificateManager
cert_manager: Final[CertificateManager] = \
    cast(CertificateManager, SimpleLazyObject(CertificateManager))
