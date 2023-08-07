"""Base support for certificate storage backends.

Version Added:
    6.0
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Generic, Iterator, Optional, TYPE_CHECKING, TypeVar

from typing_extensions import TypedDict

from reviewboard.certs.cert import CertDataFormat
from reviewboard.certs.errors import CertificateNotFoundError

if TYPE_CHECKING:
    from djblets.util.typing import StrOrPromise
    from reviewboard.certs.cert import (Certificate,
                                        CertificateBundle,
                                        CertificateFingerprints)
    from reviewboard.site.models import LocalSite, AnyOrAllLocalSites


logger = logging.getLogger(__name__)


class BaseStoredData(ABC):
    """Base class for a stored certificate-related data.

    Version Added:
        6.0
    """

    ######################
    # Instance variables #
    ######################

    #: The Local Site owning this stored certificate.
    #:
    #: Type:
    #:     reviewboard.site.models.LocalSite
    local_site: Optional[LocalSite]

    #: The storage backend managing this certificate.
    #:
    #: Type:
    #:     BaseCertificateStorageBackend
    storage: BaseCertificateStorageBackend

    #: A unique ID for this data in the storage backend.
    #:
    #: This should be considered an opaque value outside of the storage
    #: backend.
    #:
    #: Type:
    #:     str
    storage_id: Optional[str]

    def __init__(
        self,
        *,
        storage: BaseCertificateStorageBackend,
        storage_id: Optional[str] = None,
        local_site: Optional[LocalSite] = None,
    ) -> None:
        """Initialize the stored data.

        Args:
            storage (BaseCertificateStorageBackend):
                The storage backend managing this stored certificate.

            storage_id (str, optional):
                The opaque ID of the stored data in the backend.

            local_site (reviewboard.site.models.LocalSite, optional):
                The Local Site owning this stored certificate.
        """
        self.storage = storage
        self.storage_id = storage_id
        self.local_site = local_site


class BaseStoredCertificate(BaseStoredData):
    """Base class for a stored certificate.

    These represent a certificate stored in the backend, associating
    certificate data with backend-specific data such as a storage ID.

    Backends must subclass this in order to implement the following:

    * :py:meth:`get_cert_file_path`
    * :py:meth:`get_key_file_path`
    * :py:meth:`load_certificate`

    Version Added:
        6.0
    """

    ######################
    # Instance variables #
    ######################

    #: The certificate data being stored.
    #:
    #: Type:
    #:     reviewboard.certs.cert.Certificate
    _certificate: Optional[Certificate]

    def __init__(
        self,
        *,
        storage: BaseCertificateStorageBackend,
        certificate: Optional[Certificate] = None,
        storage_id: Optional[str] = None,
        local_site: Optional[LocalSite] = None,
    ) -> None:
        """Initialize the stored certificate.

        Args:
            storage (BaseCertificateStorageBackend):
                The storage backend managing this stored certificate.

            certificate (reviewboard.certs.cert.Certificate, optional):
                The certificate data being stored.

            storage_id (str, optional):
                The opaque ID of the stored data in the backend.

            local_site (reviewboard.site.models.LocalSite, optional):
                The Local Site owning this stored certificate.
        """
        super().__init__(storage=storage,
                         storage_id=storage_id,
                         local_site=local_site)
        self._certificate = certificate

    @property
    def certificate(self) -> Certificate:
        """The Certificate data in storage.

        Type:
            reviewboard.certs.cert.Certificate

        Raises:
            reviewboard.certs.errors.CertificateStorageError:
                There was an error loading the certificate from storage.

                Details are in the error message.
        """
        if self._certificate is None:
            self._certificate = self.load_certificate()

        return self._certificate

    @abstractmethod
    def get_cert_file_path(
        self,
        *,
        data_format: CertDataFormat = CertDataFormat.PEM,
    ) -> str:
        """Return the filesystem path to a certificate.

        This must be implemented by subclasses.

        Args:
            data_format (reviewboard.certs.cert.CertDataFormat, optional):
                The requested certificate data file format.

        Returns:
            str:
            The resulting file path.
        """
        raise NotImplementedError

    @abstractmethod
    def get_key_file_path(
        self,
        *,
        data_format: CertDataFormat = CertDataFormat.PEM,
    ) -> Optional[str]:
        """Return the filesystem path to a certificate private key.

        Not all certificates will have an associated private key. If one is
        not available, this will return ``None``.

        This must be implemented by subclasses.

        Args:
            data_format (reviewboard.certs.cert.CertDataFormat, optional):
                The requested private key data file format.

        Returns:
            str:
            The resulting file path, or ``None`` if a private key is not
            available.
        """
        raise NotImplementedError

    @abstractmethod
    def load_certificate(self) -> Certificate:
        """Load and return a Certificate from storage.

        This must be implemented by subclasses.

        Returns:
            reviewboard.certs.cert.Certificate:
            The resulting loaded certificate.

        Raises:
            reviewboard.certs.errors.CertificateStorageError:
                There was an error loading the certificate from storage.

                Details are in the error message.
        """
        raise NotImplementedError


class BaseStoredCertificateBundle(BaseStoredData):
    """Base class for a stored CA bundle.

    These represent a root CA bundle in the backend, associating root and
    intermediary certificate data with backend-specific data such as a
    storage ID.

    Backends must subclass this in order to implement the following:

    * :py:meth:`load_bundle`

    Version Added:
        6.0
    """

    ######################
    # Instance variables #
    ######################

    #: The certificate bundle data being stored.
    #:
    #: Type:
    #:     reviewboard.certs.cert.CertificateBundle
    _bundle: Optional[CertificateBundle]

    def __init__(
        self,
        *,
        storage: BaseCertificateStorageBackend,
        bundle: Optional[CertificateBundle] = None,
        storage_id: Optional[str] = None,
        local_site: Optional[LocalSite] = None,
    ) -> None:
        """Initialize the stored certificate.

        Args:
            storage (BaseCertificateStorageBackend):
                The storage backend managing this stored certificate.

            bundle (reviewboard.certs.cert.CertificateBundle, optional):
                The certificate bundle data being stored.

            storage_id (str, optional):
                The opaque ID of the stored data in the backend.

            local_site (reviewboard.site.models.LocalSite, optional):
                The Local Site owning this stored certificate.
        """
        super().__init__(storage=storage,
                         storage_id=storage_id,
                         local_site=local_site)

        self._bundle = bundle

    @property
    def bundle(self) -> CertificateBundle:
        """The CA bundle data in storage.

        Type:
            reviewboard.certs.cert.CertificateBundle

        Raises:
            reviewboard.certs.errors.CertificateStorageError:
                There was an error loading the CA bundle from storage.

                Details are in the error message.
        """
        if self._bundle is None:
            self._bundle = self.load_bundle()

        return self._bundle

    @abstractmethod
    def get_bundle_file_path(
        self,
        *,
        data_format: CertDataFormat = CertDataFormat.PEM,
    ) -> str:
        """Return the filesystem path to a certificate bundle.

        This must be implemented by subclasses.

        Args:
            data_format (reviewboard.certs.cert.CertDataFormat, optional):
                The requested certificate bundle data file format.

        Returns:
            str:
            The resulting file path.
        """
        raise NotImplementedError

    @abstractmethod
    def load_bundle(self) -> CertificateBundle:
        """Load and return the CA bundle data from storage.

        Returns:
            reviewboard.certs.cert.CertificateBundle:
            The resulting loaded CA bundle.

        Raises:
            reviewboard.certs.errors.CertificateStorageError:
                There was an error loading the CA bundle from storage.

                Details are in the error message.
        """
        raise NotImplementedError


class BaseStoredCertificateFingerprints(BaseStoredData):
    """Base class for stored certificate fingerprints.

    These represent fingerprints that can be used to verify a server-issued
    certificate, associating them with backend-specific data such as a
    storage ID.

    Backends must subclass this in order to implement the following:

    * :py:meth:`load_fingerprints`

    Version Added:
        6.0
    """

    ######################
    # Instance variables #
    ######################

    #: The fingerprints data being stored.
    #:
    #: Type:
    #:     reviewboard.certs.cert.CertificateFingerprints
    _fingerprints: Optional[CertificateFingerprints]

    def __init__(
        self,
        *,
        storage: BaseCertificateStorageBackend,
        fingerprints: Optional[CertificateFingerprints] = None,
        storage_id: Optional[str] = None,
        local_site: Optional[LocalSite] = None,
    ) -> None:
        """Initialize the stored certificate.

        Args:
            storage (BaseCertificateStorageBackend):
                The storage backend managing this stored certificate.

            fingerprints (reviewboard.certs.cert.CertificateFingerprints):
                The certificate fingerprints data being stored.

            storage_id (str, optional):
                The opaque ID of the stored data in the backend.

            local_site (reviewboard.site.models.LocalSite, optional):
                The Local Site owning this stored certificate.
        """
        super().__init__(storage=storage,
                         storage_id=storage_id,
                         local_site=local_site)

        self._fingerprints = fingerprints

    @property
    def fingerprints(self) -> CertificateFingerprints:
        """The certificate fingerprint data in storage.

        Type:
            reviewboard.certs.cert.CertificateFingerprints

        Raises:
            reviewboard.certs.errors.CertificateStorageError:
                There was an error loading the fingerprints from storage.

                Details are in the error message.
        """
        if self._fingerprints is None:
            self._fingerprints = self.load_fingerprints()

        return self._fingerprints

    @abstractmethod
    def load_fingerprints(self) -> CertificateFingerprints:
        """Load and return the certificate fingerprint data from storage.

        Returns:
            reviewboard.certs.cert.CertificateFingerprints:
            The resulting loaded fingerprints.

        Raises:
            reviewboard.certs.errors.CertificateStorageError:
                There was an error loading the fingerprints from storage.

                Details are in the error message.
        """
        raise NotImplementedError


class StorageStats(TypedDict):
    """Statistics about the content in a storage backend.

    This contains counts for stored CA bundles, certificates, and verified
    fingerprints. Along with this, it contains a UUID representing the current
    generation of the stats, which is useful for caching.

    Version Added:
        6.0
    """

    #: The number of stored CA bundles.
    ca_bundle_count: int

    #: The number of stored certificates.
    cert_count: int

    #: The number of stored verified fingerprints.
    fingerprint_count: int

    #: A UUID specific to the current state of the content in the backend.
    #:
    #: This can be used to help with caching and invalidation of other state.
    state_uuid: str


_StoredCertT = TypeVar(
    '_StoredCertT',
    bound=BaseStoredCertificate)
_StoredCertBundleT = TypeVar(
    '_StoredCertBundleT',
    bound=BaseStoredCertificateBundle)
_StoredCertFingerprintsT = TypeVar(
    '_StoredCertFingerprintsT',
    bound=BaseStoredCertificateFingerprints)


class BaseCertificateStorageBackend(
    ABC,
    Generic[_StoredCertT, _StoredCertBundleT, _StoredCertFingerprintsT],
):
    """Base class for a certificate storage backend.

    Store backends are responsible for storing certificate and private key
    data, CA bundles, and fingerprint verfication information.

    Backends must be able to persist certificates, private keys, and CA bundles
    on the filesystem for the lifetime of the web server process in order to
    allow consumers to access them on demand.

    Subclasses must implement the following attributes:

    * :py:attr:`backend_id`
    * :py:attr:`name`

    And the following methods:

    * :py:meth:`add_ca_bundle`
    * :py:meth:`add_certificate`
    * :py:meth:`add_fingerprints`
    * :py:meth:`delete_ca_bundle`
    * :py:meth:`delete_certificate`
    * :py:meth:`delete_fingerprints`
    * :py:meth:`get_stats`
    * :py:meth:`get_stored_ca_bundle_by_id`
    * :py:meth:`get_stored_ca_bundle`
    * :py:meth:`get_stored_certificate_by_id`
    * :py:meth:`get_stored_certificate`
    * :py:meth:`get_stored_fingerprints_by_id`
    * :py:meth:`get_stored_fingerprints`
    * :py:meth:`iter_ca_bundles`
    * :py:meth:`iter_stored_ca_bundles`
    * :py:meth:`iter_stored_certificates`
    * :py:meth:`iter_stored_fingerprints`

    Version Added:
        6.0
    """

    #: The ID of this storage backend.
    #:
    #: This must be provided by subclasses, and must be unique.
    #:
    #: Type:
    #:     str
    backend_id: Optional[str] = None

    #: The display name of the storage backend.
    #:
    #: This must be provided by subclasses.
    #:
    #: Type:
    #:     str
    name: Optional[StrOrPromise] = ''

    ######################
    # Instance variables #
    ######################

    #: The path to the local filesystem storage usable by this backend.
    #:
    #: This is set when constructing the backend, and should not be changed.
    #: All filesystem operations must be limited to directories under this
    #: path.
    #:
    #: Type:
    #:     str
    storage_path: str

    def __init__(
        self,
        storage_path: str,
    ) -> None:
        """Initialize the storage backend."""
        assert self.backend_id, 'backend_id must be set.'
        assert self.name, 'name must be set.'

        self.storage_path = storage_path

    @abstractmethod
    def get_stats(
        self,
        *,
        local_site: AnyOrAllLocalSites = None,
    ) -> StorageStats:
        """Return statistics on the certificates managed by the backend.

        This will include the total number of stored certificates, CA bundles,
        and verified fingerprints across zero, one, or all Local Sites.

        It also includes state UUIDs that represent the current states of the
        backend.

        Subclasses must ensure that any modifications to storage result in
        updates to this UUID. They may also want to ensure information is
        properly cached for a period of time, and invalidated upon
        modification.

        Args:
            local_site (reviewboard.site.models.LocalSite or
                        reviewboard.site.models.LocalSite.ALL, optional):
                An optional LocalSite bound to the stats.

                If ``None``, the global site will be used.

        Returns:
            StorageStats:
            The computed or cached storage statistics.

        Raises:
            reviewboard.cert.errors.CertificateStorageError:
                There was an error looking up cetificate stats.
        """
        raise NotImplementedError

    @abstractmethod
    def add_ca_bundle(
        self,
        bundle: CertificateBundle,
        *,
        local_site: Optional[LocalSite] = None,
    ) -> _StoredCertBundleT:
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
            BaseStoredCertificateBundle:
            The resulting stored certificate bundle.

        Raises:
            reviewboard.cert.errors.CertificateStorageError:
                There was an error storing this CA bundle.
        """
        raise NotImplementedError

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

            local_site (reviewboard.site.models.LocalSite, optional):
                An optional LocalSite that owns the certificate.

                If ``None``, the global site will be used.

        Raises:
            reviewboard.cert.errors.CertificateNotFoundError:
                The CA bundle was not found.

            reviewboard.cert.errors.CertificateStorageError:
                There was an error deleting this CA bundle.
        """
        stored_bundle = self.get_stored_ca_bundle(
            name=name,
            local_site=local_site)

        if stored_bundle is None:
            raise CertificateNotFoundError()

        assert stored_bundle.storage_id is not None

        self.delete_ca_bundle_by_id(stored_bundle.storage_id)

    @abstractmethod
    def delete_ca_bundle_by_id(
        self,
        storage_id: str,
    ) -> None:
        """Delete a root CA bundle from storage identified by ID.

        Args:
            storage_id (str):
                The ID of the CA bundle to delete.

        Raises:
            reviewboard.cert.errors.CertificateNotFoundError:
                The fingerprints were not found.

            reviewboard.cert.errors.CertificateStorageError:
                There was an error deleting this CA bundle.
        """
        raise NotImplementedError

    @abstractmethod
    def get_stored_ca_bundle(
        self,
        *,
        name: str,
        local_site: Optional[LocalSite] = None,
    ) -> Optional[_StoredCertBundleT]:
        """Return a root CA bundle in storage.

        Args:
            name (str):
                The unique name of the CA bundle in storage.

            local_site (reviewboard.site.models.LocalSite, optional):
                An optional LocalSite that owns the certificate.

                If ``None``, the global site will be used.

        Returns:
            BaseStoredCertificateBundle:
            The stored certificate bundle in storage, or ``None`` if not found.

        Raises:
            reviewboard.cert.errors.CertificateStorageError:
                There was an error retrieving this CA bundle.
        """
        raise NotImplementedError

    @abstractmethod
    def get_stored_ca_bundle_by_id(
        self,
        storage_id: str,
    ) -> Optional[_StoredCertBundleT]:
        """Return a root CA bundle in storage identified by ID.

        Args:
            storage_id (str):
                The ID of the CA bundle in storage.

        Returns:
            BaseStoredCertificateBundle:
            The stored certificate bundle in storage, or ``None`` if not found.

        Raises:
            reviewboard.cert.errors.CertificateStorageError:
                There was an error retrieving this CA bundle.
        """
        raise NotImplementedError

    @abstractmethod
    def iter_stored_ca_bundles(
        self,
        *,
        local_site: AnyOrAllLocalSites = None,
        start: int = 0,
    ) -> Iterator[_StoredCertBundleT]:
        """Iterate through all root CA bundles in storage.

        Args:
            local_site (reviewboard.site.models.LocalSite, optional):
                An optional LocalSite that owns the certificate.

                If ``None``, the global site will be used.

            start (int, optional):
                The 0-based index within the list of root CA bundles to start
                iterating at.

        Yields:
            BaseStoredCertificateBundle:
            Each stored certificate bundle in storage.

        Raises:
            reviewboard.cert.errors.CertificateStorageError:
                There was an error iterating through CA bundles.
        """
        raise NotImplementedError

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
        raise NotImplementedError

    @abstractmethod
    def add_certificate(
        self,
        certificate: Certificate,
        *,
        local_site: Optional[LocalSite] = None,
    ) -> _StoredCertT:
        """Add a certificate to storage.

        The certificate's hostname and port along with ``local_site`` are
        considered unique within the storage backend. If there's an existing
        certificate with this information, it will be replaced.

        Args:
            certificate (reviewboard.certs.cert.Certificate):
                The certificate to add.

            local_site (reviewboard.site.models.LocalSite, optional):
                An optional LocalSite that owns the certificate.

                If ``None``, the global site will be used.

        Returns:
            BaseStoredCertificate:
            The resulting stored certificate.

        Raises:
            reviewboard.cert.errors.CertificateStorageError:
                There was an error storing this certificate.
        """
        raise NotImplementedError

    def delete_certificate(
        self,
        *,
        hostname: str,
        port: int,
        local_site: Optional[LocalSite] = None,
    ) -> None:
        """Delete a certificate from storage.

        Args:
            hostname (str):
                The hostname of the certificate in storage.

            port (int):
                The port on the host serving the certificate.

            local_site (reviewboard.site.models.LocalSite, optional):
                An optional LocalSite that owns the certificate.

                If ``None``, the global site will be used.

        Raises:
            reviewboard.cert.errors.CertificateNotFoundError:
                The fingerprints were not found.

            reviewboard.cert.errors.CertificateStorageError:
                There was an error deleting this certificate.
        """
        stored_certificate = self.get_stored_certificate(
            hostname=hostname,
            port=port,
            local_site=local_site)

        if stored_certificate is None:
            raise CertificateNotFoundError()

        assert stored_certificate.storage_id

        self.delete_certificate_by_id(stored_certificate.storage_id)

    @abstractmethod
    def delete_certificate_by_id(
        self,
        storage_id: str,
    ) -> None:
        """Delete a certificate from storage.

        Args:
            storage_id (str):
                The ID of the certificate to delete.

        Raises:
            reviewboard.cert.errors.CertificateNotFoundError:
                The fingerprints were not found.

            reviewboard.cert.errors.CertificateStorageError:
                There was an error deleting this certificate.
        """
        raise NotImplementedError

    @abstractmethod
    def get_stored_certificate(
        self,
        *,
        hostname: str,
        port: int,
        local_site: Optional[LocalSite] = None,
    ) -> Optional[_StoredCertT]:
        """Return a certificate from storage.

        Args:
            hostname (str):
                The hostname of the certificate in storage.

            port (int):
                The port on the host serving the certificate.

            local_site (reviewboard.site.models.LocalSite, optional):
                An optional LocalSite that owns the certificate.

                If ``None``, the global site will be used.

        Returns:
            BaseStoredCertificate:
            The stored certificate in storage, or ``None`` if not found.

        Raises:
            reviewboard.cert.errors.CertificateStorageError:
                There was an error retrieving this certificate.
        """
        raise NotImplementedError

    @abstractmethod
    def get_stored_certificate_by_id(
        self,
        storage_id: str,
    ) -> Optional[_StoredCertT]:
        """Return a certificate from storage identified by ID.

        Args:
            storage_id (str):
                The ID of the certificate in storage.

        Returns:
            BaseStoredCertificate:
            The stored certificate in storage, or ``None`` if not found.

        Raises:
            reviewboard.cert.errors.CertificateStorageError:
                There was an error retrieving this certificate.
        """
        raise NotImplementedError

    @abstractmethod
    def iter_stored_certificates(
        self,
        *,
        local_site: AnyOrAllLocalSites = None,
        start: int = 0,
    ) -> Iterator[_StoredCertT]:
        """Iterate through all certificates in storage.

        Args:
            local_site (reviewboard.site.models.LocalSite or
                        reviewboard.site.models.LocalSite.ALL, optional):
                An optional LocalSite that owns the certificates.

                If ``None``, the global site will be used.

            start (int, optional):
                The 0-based index within the list of root CA bundles to start
                iterating at.

        Yields:
            BaseStoredCertificate:
            Each stored certificate in storage.

        Raises:
            reviewboard.cert.errors.CertificateStorageError:
                There was an error iterating through stored certificates.
        """
        raise NotImplementedError

    @abstractmethod
    def add_fingerprints(
        self,
        fingerprints: CertificateFingerprints,
        *,
        hostname: str,
        port: int,
        local_site: Optional[LocalSite] = None,
    ) -> _StoredCertFingerprintsT:
        """Add verified certificate fingerprints to storage.

        The ``hostname``, ``port``, and ``local_site`` values taken together
        must be unique within a storage backend.

        Backends may store this together with the certificates or separately.

        Args:
            hostname (str):
                The hostname serving the certificate.

            port (int):
                The port on the host serving the certificate.

            fingerprints (reviewboard.certs.cert.CertificateFingerprints):
                The certificate fingerprints to add.

            local_site (reviewboard.site.models.LocalSite, optional):
                An optional LocalSite that owns the certificate.

                If ``None``, the global site will be used.

        Returns:
            BaseStoredCertificateFingerprints:
            The resulting stored certificate fingerprints.

        Raises:
            reviewboard.cert.errors.CertificateStorageError:
                There was an error storing these fingerprints.
        """
        raise NotImplementedError

    def delete_fingerprints(
        self,
        *,
        hostname: str,
        port: int,
        local_site: Optional[LocalSite] = None,
    ) -> None:
        """Delete certificate fingerprints from storage.

        Args:
            hostname (str):
                The hostname of the certificate in storage.

            port (int):
                The port on the host serving the certificate.

            local_site (reviewboard.site.models.LocalSite, optional):
                An optional LocalSite that owns the certificate.

                If ``None``, the global site will be used.

        Raises:
            reviewboard.cert.errors.CertificateNotFoundError:
                The fingerprints were not found.

            reviewboard.cert.errors.CertificateStorageError:
                There was an error deleting these fingerprints.
        """
        stored_fingerprints = self.get_stored_fingerprints(
            hostname=hostname,
            port=port,
            local_site=local_site)

        if stored_fingerprints is None:
            raise CertificateNotFoundError()

        assert stored_fingerprints.storage_id is not None

        self.delete_fingerprints_by_id(
            stored_fingerprints.storage_id)

    @abstractmethod
    def delete_fingerprints_by_id(
        self,
        storage_id: str,
    ) -> None:
        """Delete certificate fingerprints from storage identified by ID.

        Args:
            storage_id (str):
                The ID of the certificate fingerprints to delete.

        Raises:
            reviewboard.cert.errors.CertificateNotFoundError:
                The fingerprints were not found.

            reviewboard.cert.errors.CertificateStorageError:
                There was an error deleting these fingerprints.
        """
        raise NotImplementedError

    @abstractmethod
    def iter_stored_fingerprints(
        self,
        *,
        local_site: AnyOrAllLocalSites = None,
        start: int = 0,
    ) -> Iterator[_StoredCertFingerprintsT]:
        """Iterate through all certificate fingerprints in storage.

        Args:
            local_site (reviewboard.site.models.LocalSite or
                        reviewboard.site.models.LocalSite.ALL, optional):
                An optional LocalSite that owns the certificate fingerprints.

                If ``None``, the global site will be used.

            start (int, optional):
                The 0-based index within the list of root CA bundles to start
                iterating at.

        Yields:
            BaseStoredCertificateFingerprints:
            Each stored certificate fingerprints in storage.

        Raises:
            reviewboard.cert.errors.CertificateStorageError:
                There was an error iterating through these fingerprints.
        """
        raise NotImplementedError

    @abstractmethod
    def get_stored_fingerprints(
        self,
        *,
        hostname: str,
        port: int,
        local_site: Optional[LocalSite] = None,
    ) -> Optional[_StoredCertFingerprintsT]:
        """Return certificate fingerprints from storage.

        Args:
            hostname (str):
                The hostname of the certificate in storage.

            port (int):
                The port on the host serving the certificate.

            local_site (reviewboard.site.models.LocalSite, optional):
                An optional LocalSite that owns the certificate.

                If ``None``, the global site will be used.

        Returns:
            BaseStoredCertificateFingerprints:
            The stored certificate fingerprints, or ``None`` if not found.

        Raises:
            reviewboard.cert.errors.CertificateStorageError:
                There was an error retrieving these fingerprints.
        """
        raise NotImplementedError

    @abstractmethod
    def get_stored_fingerprints_by_id(
        self,
        storage_id: str,
    ) -> Optional[_StoredCertFingerprintsT]:
        """Return certificate fingerpritns from storage identified by ID.

        Args:
            storage_id (str):
                The ID of the certificate fingerprints in storage.

        Returns:
            CertificateFingerprints:
            The stored certificate fingerprints, or ``None`` if not found.

        Raises:
            reviewboard.cert.errors.CertificateStorageError:
                There was an error retrieving these fingerprints.
        """
        raise NotImplementedError
