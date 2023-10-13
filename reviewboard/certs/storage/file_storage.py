"""File-based storage backend for SSL/TLS certificates.

Version Added:
    6.0
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Dict, Iterator, Optional, Tuple, Type, cast
from uuid import uuid4

from django.core.cache import cache
from django.core.files.utils import validate_file_name
from django.utils.text import slugify
from django.utils.translation import gettext as _, gettext_lazy
from djblets.cache.backend import cache_memoize, make_cache_key
from djblets.util.filesystem import safe_join
from djblets.util.functional import iterable_len, lazy_re_compile

from reviewboard.certs.cert import (CertDataFormat,
                                    Certificate,
                                    CertificateBundle,
                                    CertificateFingerprints)
from reviewboard.certs.errors import (CertificateNotFoundError,
                                      CertificateStorageError)
from reviewboard.certs.storage.base import (BaseCertificateStorageBackend,
                                            BaseStoredCertificate,
                                            BaseStoredCertificateBundle,
                                            BaseStoredCertificateFingerprints,
                                            StorageStats)
from reviewboard.site.models import AnyOrAllLocalSites, LocalSite


logger = logging.getLogger(__name__)


class FileStoredDataMixin:
    """Mixin for all file-based stored data classes.

    This contains additional information and helpers for representing errors
    and parsing storage IDs.

    Version Added:
        6.0
    """

    #: The directory name where this class's data will be stored.
    #:
    #: Type:
    #:     str
    storage_dir: str

    #: The display name of this stored data object.
    #:
    #: This will be used in error messages.
    #:
    #: Type:
    #:     str
    storage_name: str

    #: A regex used to parse storage IDs.
    #:
    #: Type:
    #:     re.Pattern
    storage_id_re: re.Pattern

    @classmethod
    def parse_storage_id(
        cls,
        storage_id: str,
    ) -> Dict[str, Any]:
        """Return data extracted from a storage ID.

        Args:
            storage_id (str):
                The storage ID to parse.

        Returns:
            dict:
            A dictionary containing parsed data for this stored data class.

        Raises:
            reviewboard.cert.errors.CertificateStorageError:
                The storage ID could not be parsed.
        """
        m = cls.storage_id_re.match(storage_id)

        if not m:
            # There was an error with the ID. Report it.
            error_id = str(uuid4())
            logger.error('[%s] Invalid SSL/TLS CA %s file-based storage '
                         'ID "%s"',
                         error_id, cls.storage_name, storage_id)

            raise CertificateStorageError(
                _('Internal error parsing a SSL/TLS %(type)s storage ID. '
                  'Administrators can find details in the Review Board '
                  'server logs (error ID %(error_id)s).')
                % {
                    'error_id': error_id,
                    'type': cls.storage_name,
                })

        local_site_name = m.group('local_site')
        local_site: Optional[LocalSite] = None

        if local_site_name is not None:
            try:
                local_site = LocalSite.objects.get(name=local_site_name)
            except LocalSite.DoesNotExist:
                # This is not ideal, but it at least gives us a semi-stable
                # result and avoids crashing unnecessarily.
                local_site = LocalSite(name=local_site_name)

        result: Dict[str, Any] = dict(m.groupdict(),
                                      local_site=local_site)

        # This is somewhat hacky, in that we're assuming knowledge of a
        # key that isn't common to all stored data objects. However, it's
        # pretty harmless, and simplifies the implementation considerably.
        if 'port' in result:
            result['port'] = int(result['port'])

        return result


class FileStoredCertificate(FileStoredDataMixin, BaseStoredCertificate):
    """File-based storage for a certificate and private key.

    This will store identifying information on the certificate (hostname and
    port), along with file paths where the certificate and private key PEM
    files can be found.

    Version Added:
        6.0
    """

    storage_dir = 'certs'
    storage_name = 'certificate'
    storage_id_re = lazy_re_compile(
        r'^(?:(?P<local_site>[^:]+):)?'
        r'(?P<hostname>[^:]+):'
        r'(?P<port>\d+)$'
    )

    ######################
    # Instance variables #
    ######################

    #: The hostname associated with the certificate.
    #:
    #: Type:
    #:     str
    _hostname: str

    #: The port associated with the certificate.
    #:
    #: Type:
    #:     int
    _port: int

    #: The path to the certificate file.
    #:
    #: Type:
    #:     str
    _cert_file_path: str

    #: The path to the key file, if found.
    #:
    #: Type:
    #:     str
    _key_file_path: Optional[str]

    def __init__(
        self,
        *,
        cert_file_path: str,
        key_file_path: Optional[str] = None,
        hostname: Optional[str] = None,
        storage_hostname: Optional[str] = None,
        port: Optional[int] = None,
        certificate: Optional[Certificate] = None,
        local_site: Optional[LocalSite] = None,
        storage_id: Optional[str] = None,
        **kwargs,
    ) -> None:
        """Initialize the stored certificate information.

        Args:
            cert_file_path (str):
                The local path to the certificate PEM file.

            key_file_path (str, optional):
                The local path to the private key PEM file, if available.

            hostname (str, optional):
                The hostname serving the certificate.

                Either this or ``certificate`` must be provided.

            storage_hostname (str, optional):
                The hostname used as part of a storage ID.

                This is provided in order to handle wildcard certificates,
                where the certificate hostname will be the requested hostname
                while the storage hostname will contain the wildcard.

            port (int, optional):
                The port on the host serving the certificate.

                Either this or ``certificate`` must be provided.

            certificate (reviewboard.certs.cert.Certificate, optional):
                The certificate in storage.

                Either this or both ``hostname`` and ``port`` must be provided.

            local_site (reviewboard.site.models.LocalSite, optional):
                The Local Site associated with the certificate.

            storage_id (str, optional):
                The ID of the certificate in storage.

                If not provided, one will be computed.

            **kwargs (dict, optional):
                Additional keyword arguments to pass to the parent
                constructor.
        """
        # If a certificate is provided, use that as the source for the
        # hostname and port.
        if certificate:
            assert hostname is None
            assert port is None

            hostname = certificate.hostname
            port = certificate.port
        else:
            assert hostname is not None
            assert port is not None

        self._cert_file_path = cert_file_path
        self._key_file_path = key_file_path

        self._hostname = hostname
        self._port = port

        # If a storage ID is not provided, generate one from the provided
        # arguments. With file-based storage, the ID is always based on
        # the hostname, port, and any Local Site name.
        if storage_id is None:
            if not storage_hostname:
                storage_hostname = hostname

            storage_id = f'{storage_hostname}:{port}'

            if local_site:
                storage_id = f'{local_site.name}:{storage_id}'

        super().__init__(certificate=certificate,
                         local_site=local_site,
                         storage_id=storage_id,
                         **kwargs)

    def get_cert_file_path(
        self,
        *,
        data_format: CertDataFormat = CertDataFormat.PEM,
    ) -> str:
        """Return the filesystem path to a certificate.

        Args:
            data_format (reviewboard.certs.cert.CertDataFormat, optional):
                The requested certificate data file format.

        Returns:
            str:
            The resulting file path.
        """
        return self._cert_file_path

    def get_key_file_path(
        self,
        *,
        data_format: CertDataFormat = CertDataFormat.PEM,
    ) -> Optional[str]:
        """Return the filesystem path to a certificate private key.

        Not all certificates will have an associated private key. If one is
        not available, this will return ``None``.

        Args:
            data_format (reviewboard.certs.cert.CertDataFormat, optional):
                The requested private key data file format.

        Returns:
            str:
            The resulting file path, or ``None`` if a private key is not
            available.
        """
        return self._key_file_path

    def load_certificate(self) -> Certificate:
        """Load and return a Certificate from storage.

        Returns:
            reviewboard.certs.cert.Certificate:
            The resulting loaded certificate.

        Raises:
            reviewboard.certs.errors.CertificateStorageError:
                There was an error loading the certificate from storage.

                Details are in the error message.
        """
        # Allow exceptions to bubble up.
        return Certificate.create_from_files(
            hostname=self._hostname,
            port=self._port,
            cert_path=self.get_cert_file_path(),
            key_path=self.get_key_file_path())

    def __repr__(self) -> str:
        """Return a string representation of the stored certificate.

        Returns:
            str:
            The string representation.
        """
        return (
            '<FileStoredCertificate(storage_id=%r, hostname=%r, port=%r, '
            'cert_file_path=%r, key_file_path=%r)>'
            % (self.storage_id, self._hostname, self._port,
               self._cert_file_path, self._key_file_path)
        )


class FileStoredCertificateBundle(FileStoredDataMixin,
                                  BaseStoredCertificateBundle):
    """File-based storage for a CA bundle.

    This will store identifying information on the CA bundle (its name),
    along with a file path where the bundle can be found.

    Version Added:
        6.0
    """

    storage_dir = 'cabundles'
    storage_name = 'CA bundle'
    storage_id_re = lazy_re_compile(
        r'^(?:(?P<local_site>[^:]+):)?'
        r'(?P<name>[^:]+)$'
    )

    ######################
    # Instance variables #
    ######################

    #: The path to the CA bundle file.
    #:
    #: Type:
    #:     str
    _bundle_file_path: str

    #: The associated name of the CA bundle.
    #:
    #: This is in :term:`slug` format.
    #:
    #: Type:
    #:     str
    _name: str

    def __init__(
        self,
        *,
        bundle_file_path: str,
        name: Optional[str] = None,
        bundle: Optional[CertificateBundle] = None,
        local_site: Optional[LocalSite] = None,
        storage_id: Optional[str] = None,
        **kwargs,
    ) -> None:
        """Initialize the stored CA bundle information>

        Args:
            bundle_file_path (str):
                The local path to the CA bundle PEM file.

            name (str, optional):
                The associated name of the CA bundle.

                Either this or ``bundle`` must be provided.

            bundle (reviewboard.certs.cert.CertificateBundle, optional):
                The CA bundle in storage.

                Either this or ``name`` must be provided.

            local_site (reviewboard.site.models.LocalSite, optional):
                The Local Site associated with the certificate.

            storage_id (str, optional):
                The ID of the certificate in storage.

                If not provided, one will be computed.

            **kwargs (dict, optional):
                Additional keyword arguments to pass to the parent
                constructor.
        """
        if bundle:
            assert name is None
            name = bundle.name
        else:
            assert name is not None

        assert name == slugify(name)

        self._name = name
        self._bundle_file_path = bundle_file_path

        # If a storage ID is not provided, generate one from the provided
        # arguments. With file-based storage, the ID is always based on
        # the hostname, port, and any Local Site name.
        if storage_id is None:
            storage_id = name

            if local_site:
                storage_id = f'{local_site.name}:{storage_id}'

        super().__init__(bundle=bundle,
                         local_site=local_site,
                         storage_id=storage_id,
                         **kwargs)

    def get_bundle_file_path(
        self,
        *,
        data_format: CertDataFormat = CertDataFormat.PEM,
    ) -> str:
        """Return the filesystem path to a certificate bundle.

        Args:
            data_format (reviewboard.certs.cert.CertDataFormat, optional):
                The requested certificate bundle data file format.

        Returns:
            str:
            The resulting file path.
        """
        return self._bundle_file_path

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
        # Allow exceptions to bubble up.
        return CertificateBundle.create_from_file(
            name=self._name,
            path=self._bundle_file_path)

    def __repr__(self) -> str:
        """Return a string representation of the stored certificate bundle.

        Returns:
            str:
            The string representation.
        """
        return (
            '<FileStoredCertificateBundle(storage_id=%r, name=%r, '
            'bundle_file_path=%r)>'
            % (self.storage_id, self._name, self._bundle_file_path)
        )


class FileStoredCertificateFingerprints(FileStoredDataMixin,
                                        BaseStoredCertificateFingerprints):
    """File-based storage for certificate fingerprints.

    This will store identifying information on the fingerprints (hostname and
    port), along with a file path where the serialized fingerprints data can be
    found.

    Version Added:
        6.0
    """

    storage_dir = 'fingerprints'
    storage_name = 'fingerprints'
    storage_id_re = lazy_re_compile(
        r'^(?:(?P<local_site>[^:]+):)?'
        r'(?P<hostname>[^:]+):'
        r'(?P<port>\d+)$'
    )

    ######################
    # Instance variables #
    ######################

    #: The path to the fingerprints file.
    #:
    #: Type:
    #:     str
    _fingerprints_file_path: str

    #: The hostname associated with the certificate fingerprints.
    #:
    #: Type:
    #:     str
    _hostname: str

    #: The port associated with the certificate fingerprints.
    #:
    #: Type:
    #:     int
    _port: int

    def __init__(
        self,
        *,
        hostname: str,
        port: int,
        fingerprints_file_path: str,
        local_site: Optional[LocalSite] = None,
        storage_id: Optional[str] = None,
        **kwargs,
    ) -> None:
        """Initialize the stored certificate fingerprints information.

        Args:
            hostname (str):
                The hostname serving the certificate.

            port (int):
                The port on the host serving the certificate.

            fingerprints_file_path (str):
                The local path to the fingerprints data file.

            local_site (reviewboard.site.models.LocalSite, optional):
                The Local Site associated with the certificate.

            storage_id (str, optional):
                The ID of the certificate fingerprints in storage.

                If not provided, one will be computed.

            **kwargs (dict, optional):
                Additional keyword arguments to pass to the parent
                constructor.
        """
        self._hostname = hostname
        self._port = port
        self._fingerprints_file_path = fingerprints_file_path

        # If a storage ID is not provided, generate one from the provided
        # arguments. With file-based storage, the ID is always based on
        # the hostname, port, and any Local Site name.
        if storage_id is None:
            storage_id = f'{hostname}:{port}'

            if local_site:
                storage_id = f'{local_site.name}:{storage_id}'

        super().__init__(local_site=local_site,
                         storage_id=storage_id,
                         **kwargs)

    def load_fingerprints(self) -> CertificateFingerprints:
        """Load and return the certificate fingerprints data from storage.

        Returns:
            reviewboard.certs.cert.CertificateFingerprints:
            The resulting loaded certificate fingerprints

        Raises:
            reviewboard.certs.errors.CertificateStorageError:
                There was an error loading the fingerprints from storage.

                Details are in the error message.
        """
        try:
            with open(self._fingerprints_file_path, 'r') as fp:
                return CertificateFingerprints.from_json(json.load(fp))
        except (IOError, ValueError) as e:
            error_id = str(uuid4())
            logger.error('[%s] Error loading SSL/TLS certificate '
                         'fingerprints file "%s": %s',
                         error_id, self._fingerprints_file_path, e)

            raise CertificateStorageError(
                _('Error loading SSL/TLS certificate fingerprints. '
                  'Administrators can find details in the Review Board '
                  'server logs (error ID %(error_id)s).')
                % {
                    'error_id': error_id,
                })

    def __repr__(self) -> str:
        """Return a string representation of the stored fingerprints.

        Returns:
            str:
            The string representation.
        """
        return (
            '<FileStoredCertificateFingerprints(storage_id=%r, hostname=%r, '
            'port=%r, fingerprints_file_path=%r)>'
            % (self.storage_id, self._hostname, self._port,
               self._fingerprints_file_path)
        )


class FileCertificateStorageBackend(BaseCertificateStorageBackend[
    FileStoredCertificate,
    FileStoredCertificateBundle,
    FileStoredCertificateFingerprints,
]):
    """File-based storage for SSL/TLS certificates.

    This storage backend will store certificates, CA bundles, and fingerprints
    in the following patterned locations under the certificate store directory
    for this backend::

        cabundles/<slug>.pem
        certs/<hostname>__<port>.crt
        certs/<hostname>__<port>.key
        certs/__.<hostname>__<port>.crt
        certs/__.<hostname>__<port>.key
        fingerprints/<hostname>__<port>.json
        sites/<local_site_name>/cabundles/<slug>.pem
        sites/<local_site_name>/certs/<hostname>__<port>.crt
        sites/<local_site_name>/certs/<hostname>__<port>.key
        sites/<local_site_name>/certs/__.<hostname>__<port>.crt
        sites/<local_site_name>/certs/__.<hostname>__<port>.key
        sites/<local_site_name>/fingerprints/<hostname>__<port>.json

    Iterating through data involves scanning these directories for information,
    and possibly opening each file. This can involve a lot of IO for large
    numbers of certificates, but is fine in most simple deployments. Using
    CA bundles, rather than individual certificates, can help keep using
    performant.

    For multi-server deployments, Power Pack's synchronized certificate storage
    is recommended (available in Power Pack 6 and up).

    Version Added:
        6.0
    """

    backend_id = 'file'
    name = gettext_lazy('File-based storage')

    _cabundle_re = lazy_re_compile(r'(?P<basename>.+)\.pem')

    _cert_re = lazy_re_compile(
        r'(?P<basename>(?P<hostname>(?:__)?[A-Za-z0-9.-]+)__'
        r'(?P<port>\d+))\.crt'
    )

    _fingerprints_json_re = lazy_re_compile(
        r'(?P<hostname>(?:__)?[A-Za-z0-9.-]+)__(?P<port>\d+)\.json'
    )

    def get_stats(
        self,
        *,
        local_site: AnyOrAllLocalSites = None,
        **kwargs,
    ) -> StorageStats:
        """Return statistics on the certificates managed by the backend.

        This will include the total number of stored certificates, CA bundles,
        and verified fingerprints across zero, one, or all Local Sites.

        It also includes state UUIDs that represent the current states of the
        backend.

        Args:
            local_site (reviewboard.site.models.LocalSite or
                        reviewboard.site.models.LocalSite.ALL, optional):
                An optional LocalSite bound to the stats.

                If ``None``, the global site will be used.

            **kwargs (dict, unused):
                Additional keyword arguments, for future expansion.

        Returns:
            reviewboard.certs.storage.base.StorageStats:
            The computed or cached storage statistics.
        """
        def _gen_stats() -> StorageStats:
            return StorageStats(
                ca_bundle_count=iterable_len(
                    self.iter_stored_ca_bundles(
                        local_site=local_site)),
                cert_count=iterable_len(
                    self.iter_stored_certificates(
                        local_site=local_site)),
                fingerprint_count=iterable_len(
                    self.iter_stored_fingerprints(
                        local_site=local_site)),
                state_uuid=str(uuid4()))

        cache_key = self._build_stats_cache_key(local_site=local_site)

        return cast(StorageStats, cache_memoize(cache_key, _gen_stats))

    def add_ca_bundle(
        self,
        bundle: CertificateBundle,
        *,
        local_site: Optional[LocalSite] = None,
        **kwargs,
    ) -> FileStoredCertificateBundle:
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

            **kwargs (dict, unused):
                Additional keyword arguments, for future expansion.

        Returns:
            FileStoredCertificateBundle:
            The resulting stored certificate bundle.

        Raises:
            reviewboard.cert.errors.CertificateStorageError:
                There as an error storing this certificate.
        """
        name = bundle.name

        bundle_file_path = self._build_ca_bundle_file_path(
            name=name,
            local_site=local_site,
            create_parents_if_missing=True)
        assert bundle_file_path

        # Allow exceptions to bubble up.
        bundle.write_bundle_file(bundle_file_path)

        self._invalidate_stats_cache(local_site=local_site)

        return FileStoredCertificateBundle(
            bundle=bundle,
            bundle_file_path=bundle_file_path,
            local_site=local_site,
            storage=self)

    def delete_ca_bundle(
        self,
        *,
        name: str,
        local_site: Optional[LocalSite] = None,
        **kwargs,
    ) -> None:
        """Delete a root CA bundle from storage.

        Args:
            bundle (reviewboard.certs.cert.CertificateBundle):
                The bundle to add.

            local_site (reviewboard.site.models.LocalSite, optional):
                An optional LocalSite that owns the certificate.

                If ``None``, the global site will be used.

            **kwargs (dict, unused):
                Additional keyword arguments, for future expansion.

        Raises:
            reviewboard.cert.errors.CertificateStorageError:
                There was an error deleting this CA bundle.
        """
        bundle_file_path = self._build_ca_bundle_file_path(
            name=name,
            local_site=local_site,
            if_exists=True)

        if not bundle_file_path:
            raise CertificateNotFoundError()

        try:
            os.unlink(bundle_file_path)
        except IOError as e:
            error_id = str(uuid4())
            logger.error('[%s] Unable to delete SSL/TLS bundle file at '
                         '"%s": %s',
                         error_id, bundle_file_path, e)

            raise CertificateStorageError(
                _('Error deleting SSL/TLS CA bundle. Administrators can '
                  'find details in the Review Board server logs (error '
                  'ID %(error_id)s).')
                % {
                    'error_id': error_id,
                })

        self._invalidate_stats_cache(local_site=local_site)

    def delete_ca_bundle_by_id(
        self,
        storage_id: str,
        **kwargs,
    ) -> None:
        """Delete a root CA bundle from storage identified by ID.

        Args:
            storage_id (str):
                The ID of the CA bundle to delete.

            **kwargs (dict, unused):
                Additional keyword arguments, for future expansion.

        Raises:
            reviewboard.cert.errors.CertificateStorageError:
                There was an error deleting this CA bundle.
        """
        self.delete_ca_bundle(
            **FileStoredCertificateBundle.parse_storage_id(storage_id))

    def get_stored_ca_bundle(
        self,
        *,
        name: str,
        local_site: Optional[LocalSite] = None,
        **kwargs,
    ) -> Optional[FileStoredCertificateBundle]:
        """Return a root CA bundle in storage.

        Args:
            name (str):
                The unique name of the CA bundle in storage.

            local_site (reviewboard.site.models.LocalSite, optional):
                An optional LocalSite that owns the certificate.

                If ``None``, the global site will be used.

            **kwargs (dict, unused):
                Additional keyword arguments, for future expansion.

        Returns:
            FileStoredCertificateBundle:
            The stored certificate bundle in storage, or ``None`` if not found.

        Raises:
            reviewboard.cert.errors.CertificateStorageError:
                There was an error retrieving this CA bundle.
        """
        bundle_file_path = self._build_ca_bundle_file_path(
            name=name,
            local_site=local_site,
            if_exists=True)

        if not bundle_file_path:
            return None

        return FileStoredCertificateBundle(
            name=name,
            bundle_file_path=bundle_file_path,
            local_site=local_site,
            storage=self)

    def get_stored_ca_bundle_by_id(
        self,
        storage_id: str,
        **kwargs,
    ) -> Optional[FileStoredCertificateBundle]:
        """Return a root CA bundle in storage identified by ID.

        Args:
            storage_id (str):
                The ID of the CA bundle in storage.

            **kwargs (dict, unused):
                Additional keyword arguments, for future expansion.

        Returns:
            FileStoredCertificateBundle:
            The stored certificate bundle in storage, or ``None`` if not found.

        Raises:
            reviewboard.cert.errors.CertificateStorageError:
                There was an error retrieving this CA bundle.
        """
        return self.get_stored_ca_bundle(
            **FileStoredCertificateBundle.parse_storage_id(storage_id))

    def iter_stored_ca_bundles(
        self,
        *,
        local_site: AnyOrAllLocalSites = None,
        start: int = 0,
        **kwargs,
    ) -> Iterator[FileStoredCertificateBundle]:
        """Iterate through all root CA bundles in storage.

        Args:
            local_site (reviewboard.site.models.LocalSite, optional):
                An optional LocalSite that owns the certificate.

                If ``None``, the global site will be used.

            start (int, optional):
                The 0-based index within the list of root CA bundles to start
                iterating at.

            **kwargs (dict, unused):
                Additional keyword arguments, for future expansion.

        Yields:
            FileStoredCertificateBundle:
            Each stored certificate bundle in storage.

        Raises:
            reviewboard.cert.errors.CertificateStorageError:
                There was an error iterating through CA bundles.
        """
        entries = self._iter_stored_data_files(
            stored_data_cls=FileStoredCertificateBundle,
            file_pattern=self._cabundle_re,
            local_site=local_site,
            start=start)

        for entry_path, entry_local_site, m in entries:
            yield FileStoredCertificateBundle(
                storage=self,
                name=m.group('basename'),
                bundle_file_path=entry_path,
                local_site=entry_local_site)

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
        return self._build_data_dir_path(
            stored_data_cls=FileStoredCertificateBundle,
            local_site=local_site)

    def add_certificate(
        self,
        certificate: Certificate,
        *,
        local_site: Optional[LocalSite] = None,
        **kwargs,
    ) -> FileStoredCertificate:
        """Add a certificate to storage.

        The certificate's hostname and port along with ``local_site`` are
        considered unique within the storage backend. If there's an existing
        certificate with this information, it will be removed.

        Args:
            certificate (reviewboard.certs.cert.Certificate):
                The certificate to add.

            local_site (reviewboard.site.models.LocalSite, optional):
                An optional LocalSite that owns the certificate.

                If ``None``, the global site will be used.

            **kwargs (dict, unused):
                Additional keyword arguments, for future expansion.

        Returns:
            FileStoredCertificate:
            The resulting stored certificate.

        Raises:
            reviewboard.cert.errors.CertificateStorageError:
                There was an error storing this certificate.
        """
        hostname = certificate.hostname
        port = certificate.port

        # Write the certificate.
        cert_file_path = self._build_cert_file_path(
            hostname=hostname,
            port=port,
            ext='crt',
            local_site=local_site,
            create_parents_if_missing=True)
        assert cert_file_path

        # Allow exceptions to bubble up.
        certificate.write_cert_file(cert_file_path)

        # Make sure any key is deleted.
        key_file_path = self._build_cert_file_path(
            hostname=hostname,
            port=port,
            ext='key',
            local_site=local_site)
        assert key_file_path

        if os.path.exists(key_file_path):
            try:
                os.unlink(key_file_path)
            except IOError as e:
                logger.error('Error deleting SSL/TLS certificate '
                             'private key file "%s": %s',
                             key_file_path, e)

        if certificate.key_data:
            # Write the private key. Allow exceptions to bubble up.
            certificate.write_key_file(key_file_path)
        else:
            key_file_path = None

        self._invalidate_stats_cache(local_site=local_site)

        # Build the storage ID for this certificate.
        return FileStoredCertificate(
            certificate=certificate,
            cert_file_path=cert_file_path,
            key_file_path=key_file_path,
            local_site=local_site,
            storage=self)

    def delete_certificate(
        self,
        *,
        hostname: str,
        port: int,
        local_site: Optional[LocalSite] = None,
        **kwargs,
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

            **kwargs (dict, unused):
                Additional keyword arguments, for future expansion.

        Raises:
            reviewboard.cert.errors.CertificateStorageError:
                There was an error deleting this certificate.
        """
        cert_file_path = self._build_cert_file_path(
            hostname=hostname,
            port=port,
            ext='crt',
            local_site=local_site,
            if_exists=True)

        if not cert_file_path:
            raise CertificateNotFoundError()

        key_file_path = self._build_cert_file_path(
            hostname=hostname,
            port=port,
            ext='key',
            local_site=local_site,
            if_exists=True)

        try:
            os.unlink(cert_file_path)
        except IOError as e:
            error_id = str(uuid4())
            logger.error('[%s] Unable to delete SSL/TLS certificate file at '
                         '"%s": %s',
                         error_id, cert_file_path, e)

            raise CertificateStorageError(
                _('Error deleting SSL/TLS certificate. Administrators can '
                  'find details in the Review Board server logs (error '
                  'ID %(error_id)s).')
                % {
                    'error_id': error_id,
                })

        if key_file_path:
            try:
                os.unlink(key_file_path)
            except IOError as e:
                error_id = str(uuid4())
                logger.error('[%s] Unable to delete SSL/TLS private key file '
                             'at "%s": %s',
                             error_id, cert_file_path, e)

                raise CertificateStorageError(
                    _('Error deleting SSL/TLS private key. Administrators '
                      'can find details in the Review Board server logs '
                      '(error ID %(error_id)s).')
                    % {
                        'error_id': error_id,
                    })

        self._invalidate_stats_cache(local_site=local_site)

    def delete_certificate_by_id(
        self,
        storage_id: str,
        **kwargs,
    ) -> None:
        """Delete a certificate from storage.

        Args:
            storage_id (str):
                The ID of the certificate to delete.

            **kwargs (dict, unused):
                Additional keyword arguments, for future expansion.

        Raises:
            reviewboard.cert.errors.CertificateStorageError:
                There was an error deleting this certificate.
        """
        self.delete_certificate(
            **FileStoredCertificate.parse_storage_id(storage_id))

    def get_stored_certificate(
        self,
        *,
        hostname: str,
        port: int,
        local_site: Optional[LocalSite] = None,
        **kwargs,
    ) -> Optional[FileStoredCertificate]:
        """Return a certificate from storage.

        Args:
            hostname (str):
                The hostname of the certificate in storage.

            port (int):
                The port on the host serving the certificate.

            local_site (reviewboard.site.models.LocalSite, optional):
                An optional LocalSite that owns the certificate.

                If ``None``, the global site will be used.

            **kwargs (dict, unused):
                Additional keyword arguments, for future expansion.

        Returns:
            FileStoredCertificate:
            The stored certificate in storage, or ``None`` if not found.

        Raises:
            reviewboard.cert.errors.CertificateStorageError:
                There was an error retrieving this certificate.
        """
        cert_file_path = self._build_cert_file_path(
            hostname=hostname,
            port=port,
            ext='crt',
            local_site=local_site,
            if_exists=True)

        if cert_file_path:
            storage_hostname = hostname
        else:
            # Look for a wildcard cert.
            storage_hostname = self._build_wildcard_hostname(hostname)

            cert_file_path = self._build_cert_file_path(
                hostname=storage_hostname,
                port=port,
                ext='crt',
                local_site=local_site,
                if_exists=True)

            if not cert_file_path:
                return None

        key_file_path = self._build_cert_file_path(
            hostname=storage_hostname,
            port=port,
            ext='key',
            local_site=local_site,
            if_exists=True)

        return FileStoredCertificate(
            hostname=hostname,
            port=port,
            storage_hostname=storage_hostname,
            cert_file_path=cert_file_path,
            key_file_path=key_file_path,
            local_site=local_site,
            storage=self)

    def get_stored_certificate_by_id(
        self,
        storage_id: str,
        **kwargs,
    ) -> Optional[FileStoredCertificate]:
        """Return a certificate from storage identified by ID.

        Args:
            storage_id (str):
                The ID of the certificate in storage.

            **kwargs (dict, unused):
                Additional keyword arguments, for future expansion.

        Returns:
            FileStoredCertificate:
            The stored certificate in storage, or ``None`` if not found.

        Raises:
            reviewboard.cert.errors.CertificateStorageError:
                There was an error retrieving this certificate.
        """
        return self.get_stored_certificate(
            **FileStoredCertificate.parse_storage_id(storage_id))

    def iter_stored_certificates(
        self,
        *,
        local_site: AnyOrAllLocalSites = None,
        start: int = 0,
        **kwargs,
    ) -> Iterator[FileStoredCertificate]:
        """Iterate through all certificates in storage.

        Args:
            local_site (reviewboard.site.models.LocalSite or
                        reviewboard.site.models.LocalSite.ALL, optional):
                An optional LocalSite that owns the certificates.

                If ``None``, the global site will be used.

            start (int, optional):
                The 0-based index within the list of root CA bundles to start
                iterating at.

            **kwargs (dict, unused):
                Additional keyword arguments, for future expansion.

        Yields:
            BaseStoredCertificate:
            Each stored certificate in storage.

        Raises:
            reviewboard.cert.errors.CertificateStorageError:
                There was an error iterating through stored certificates.
        """
        key_file_path: Optional[str]

        entries = self._iter_stored_data_files(
            stored_data_cls=FileStoredCertificate,
            file_pattern=self._cert_re,
            local_site=local_site,
            start=start)

        for cert_file_path, cert_local_site, m in entries:
            basename = m.group('basename')
            key_file_path = os.path.join(os.path.dirname(cert_file_path),
                                         f'{basename}.key')

            if not os.path.exists(key_file_path):
                key_file_path = None

            hostname = m.group('hostname')

            if hostname.startswith('__'):
                hostname = '*.%s' % hostname[3:]

            yield FileStoredCertificate(
                hostname=hostname,
                port=int(m.group('port')),
                cert_file_path=cert_file_path,
                key_file_path=key_file_path,
                local_site=cert_local_site,
                storage=self)

    def add_fingerprints(
        self,
        fingerprints: CertificateFingerprints,
        *,
        hostname: str,
        port: int,
        local_site: Optional[LocalSite] = None,
        **kwargs,
    ) -> FileStoredCertificateFingerprints:
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

            **kwargs (dict, unused):
                Additional keyword arguments, for future expansion.

        Returns:
            BaseStoredCertificateFingerprints:
            The resulting stored certificate fingerprints.

        Raises:
            reviewboard.cert.errors.CertificateStorageError:
                There was an error storing these fingerprints.
        """
        path = self._build_fingerprints_file_path(
            hostname=hostname,
            port=port,
            local_site=local_site,
            create_parents_if_missing=True)
        assert path

        # Read/write the fingerprints data.
        try:
            with open(path, 'w') as fp:
                json.dump(fingerprints.to_json(), fp)
        except IOError as e:
            error_id = str(uuid4())
            logger.error('[%s] Unable to write SSL/TLS fingerprints '
                         'file at "%s": %s',
                         error_id, path, e)

            raise CertificateStorageError(
                _('Error writing SSL/TLS certificate fingerprints. '
                  'Administrators can find details in the Review Board '
                  'server logs (error ID %(error_id)s).')
                % {
                    'error_id': error_id,
                })

        self._invalidate_stats_cache(local_site=local_site)

        return FileStoredCertificateFingerprints(
            fingerprints=fingerprints,
            hostname=hostname,
            port=port,
            fingerprints_file_path=path,
            local_site=local_site,
            storage=self)

    def delete_fingerprints(
        self,
        *,
        hostname: str,
        port: int,
        local_site: Optional[LocalSite] = None,
        **kwargs,
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

            **kwargs (dict, unused):
                Additional keyword arguments, for future expansion.

        Raises:
            reviewboard.cert.errors.CertificateNotFoundErro:
                The fingerprints were not found.

            reviewboard.cert.errors.CertificateStorageError:
                There was an error deleting these fingerprints.
        """
        fingerprints_file_path = self._build_fingerprints_file_path(
            hostname=hostname,
            port=port,
            local_site=local_site,
            if_exists=True)

        if not fingerprints_file_path:
            raise CertificateNotFoundError()

        try:
            os.unlink(fingerprints_file_path)
        except IOError as e:
            error_id = str(uuid4())
            logger.error('[%s] Unable to delete SSL/TLS certificate '
                         'fingerprints file at "%s": %s',
                         error_id, fingerprints_file_path, e)

            raise CertificateStorageError(
                _('Error deleting SSL/TLS certificate fingerprints. '
                  'Administrators can find details in the Review Board '
                  'server logs (error ID %(error_id)s).')
                % {
                    'error_id': error_id,
                })

        self._invalidate_stats_cache(local_site=local_site)

    def delete_fingerprints_by_id(
        self,
        storage_id: str,
        **kwargs,
    ) -> None:
        """Delete certificate fingerprints from storage identified by ID.

        Args:
            storage_id (str):
                The ID of the certificate fingerprints to delete.

            **kwargs (dict, unused):
                Additional keyword arguments, for future expansion.

        Raises:
            reviewboard.cert.errors.CertificateStorageError:
                There was an error deleting these fingerprints.
        """
        self.delete_fingerprints(
            **FileStoredCertificateFingerprints.parse_storage_id(storage_id))

    def get_stored_fingerprints(
        self,
        *,
        hostname: str,
        port: int,
        local_site: Optional[LocalSite] = None,
        **kwargs,
    ) -> Optional[FileStoredCertificateFingerprints]:
        """Return certificate fingerprints from storage.

        Args:
            hostname (str):
                The hostname of the certificate in storage.

            port (int):
                The port on the host serving the certificate.

            local_site (reviewboard.site.models.LocalSite, optional):
                An optional LocalSite that owns the certificate.

                If ``None``, the global site will be used.

            **kwargs (dict, unused):
                Additional keyword arguments, for future expansion.

        Returns:
            BaseStoredCertificateFingerprints:
            The stored certificate fingerprints, or ``None`` if not found.

        Raises:
            reviewboard.cert.errors.CertificateStorageError:
                There was an error retrieving these fingerprints.
        """
        path = self._build_fingerprints_file_path(
            hostname=hostname,
            port=port,
            local_site=local_site,
            if_exists=True)

        if not path:
            return None

        return FileStoredCertificateFingerprints(
            hostname=hostname,
            port=port,
            fingerprints_file_path=path,
            local_site=local_site,
            storage=self)

    def get_stored_fingerprints_by_id(
        self,
        storage_id: str,
        **kwargs,
    ) -> Optional[FileStoredCertificateFingerprints]:
        """Return certificate fingerprints from storage identified by ID.

        Args:
            storage_id (str):
                The ID of the certificate fingerprints in storage.

            **kwargs (dict, unused):
                Additional keyword arguments, for future expansion.

        Returns:
            CertificateFingerprints:
            The stored certificate fingerprints, or ``None`` if not found.

        Raises:
            reviewboard.cert.errors.CertificateStorageError:
                There was an error retrieving these fingerprints.
        """
        return self.get_stored_fingerprints(
            **FileStoredCertificateFingerprints.parse_storage_id(storage_id))

    def iter_stored_fingerprints(
        self,
        *,
        local_site: AnyOrAllLocalSites = None,
        start: int = 0,
        **kwargs,
    ) -> Iterator[FileStoredCertificateFingerprints]:
        """Iterate through all certificate fingerprints in storage.

        Args:
            local_site (reviewboard.site.models.LocalSite or
                        reviewboard.site.models.LocalSite.ALL, optional):
                An optional LocalSite that owns the certificate fingerprints.

                If ``None``, the global site will be used.

            start (int, optional):
                The 0-based index within the list of root CA bundles to start
                iterating at.

            **kwargs (dict, unused):
                Additional keyword arguments, for future expansion.

        Yields:
            FileStoredCertificateFingerprints:
            Each stored certificate fingerprints in storage.

        Raises:
            reviewboard.cert.errors.CertificateStorageError:
                There was an error iterating through these fingerprints.
        """

        entries = self._iter_stored_data_files(
            stored_data_cls=FileStoredCertificateFingerprints,
            file_pattern=self._fingerprints_json_re,
            local_site=local_site,
            start=start)

        for entry_path, entry_local_site, m in entries:
            yield FileStoredCertificateFingerprints(
                hostname=m.group('hostname'),
                port=int(m.group('port')),
                fingerprints_file_path=entry_path,
                local_site=entry_local_site,
                storage=self)

    def _invalidate_stats_cache(
        self,
        *,
        local_site: Optional[LocalSite],
    ) -> None:
        """Invalidate the file storage stats cache information.

        Args:
            local_site (reviewboard.site.models.LocalSite, optional):
                The Local Site value associated with the stats key.
        """
        cache.delete_many([
            make_cache_key(self._build_stats_cache_key(
                local_site=local_site)),
            make_cache_key(self._build_stats_cache_key(
                local_site=LocalSite.ALL)),
        ])

    def _iter_stored_data_dirs(
        self,
        stored_data_cls: Type[FileStoredDataMixin],
        *,
        local_site: AnyOrAllLocalSites = None,
    ) -> Iterator[Tuple[str, Optional[LocalSite]]]:
        """Iterate through data directories.

        This will yield absolute paths to directories where data may be
        stored, based on a data storage class.

        If a Local Site is provided, one path will be yielded containing the
        Local Site's directory within the stored data path.

        if no Local Site is provided, one path will be yielded containing the
        global site data directory within the stored data path.

        If all Local Sites are requested, then this will yield every Local
        Site path and the top-level path.

        Args:
            stored_data_cls (type):
                The stored data class representing files to iterate through.

            local_site (reviewboard.site.models.LocalSite or
                        reviewboard.site.models.LocalSite.ALL, optional):
                An optional Local Site value to filter by.

        Yields:
            tuple:
            A 2-tuple of results:

            Tuple:
                0 (str):
                    The path to the data directory.

                1 (reviewboard.site.models.LocalSite):
                    The path's associated Local Site, or ``None`` for the
                    global site.
        """
        if local_site is LocalSite.ALL:
            # Yield the top-level (non-Local Site) data.
            yield self._build_data_dir_path(stored_data_cls), None

            sites_path = os.path.join(self.storage_path, 'sites')

            if os.path.exists(sites_path):
                # There's Local Site data. Try to efficiently iterate through
                # any Local Sites for directory names we find and yield those
                # paths and Local Sites.
                with os.scandir(sites_path) as entries:
                    local_site_names = [
                        _path.name
                        for _path in entries
                        if _path.is_dir()
                    ]

                if local_site_names:
                    local_sites = (
                        LocalSite.objects
                        .filter(name__in=local_site_names)
                        .iterator()
                    )

                    for path_local_site in local_sites:
                        yield (
                            self._build_data_dir_path(
                                stored_data_cls,
                                local_site=path_local_site),
                            path_local_site,
                        )
        else:
            yield (
                self._build_data_dir_path(stored_data_cls,
                                          local_site=local_site),
                local_site,
            )

    def _iter_stored_data_files(
        self,
        stored_data_cls: Type[FileStoredDataMixin],
        *,
        file_pattern: re.Pattern,
        local_site: AnyOrAllLocalSites = None,
        start: int = 0,
    ) -> Iterator[Tuple[str, Optional[LocalSite], re.Match]]:
        """Iterate through all files in the specified data directories.

        This will iterate through all the files in each data directory
        provided by :py:meth:`_iter_data_dirs`. Results are filtered by
        file pattern and by a starting index.

        Files not matching the pattern are ignored, and will not count toward
        identifying the starting index.

        Note that while a starting index may be supplied, it cannot
        immediately seek to the corresponding index in results. That means
        that this may be slower the further into the results the caller
        indexes. For large deployments where this may matter, Power Pack's
        synchronized certificate management is recommended.

        Args:
            stored_data_cls (type):
                The stored data class representing files to iterate through.

            file_pattern (re.Pattern):
                The regex file pattern to match.

                This may contain capture groups, which will be available in
                each yielded result.

            local_site (reviewboard.site.models.LocalSite or
                        reviewboard.site.models.LocalSite.ALL, optional):
                An optional Local Site value to filter by.

            start (int, optional):
                The starting index for file results.

        Yields:
            tuple:
            A 3-tuple representing a matched file:

            Tuple:
                0 (str):
                    The absolute path to the file.

                1 (reviewboard.site.models.LocalSite):
                    The path's associated Local Site, or ``None`` for the
                    global site.

                2 (re.Match):
                    The regex match object for the supplied pattern.
        """
        i: int = 0
        dirs = self._iter_stored_data_dirs(stored_data_cls,
                                           local_site=local_site)

        for dir_entry, dir_local_site in dirs:
            if not os.path.exists(dir_entry):
                continue

            with os.scandir(dir_entry) as file_entries:
                norm_file_entries = sorted(
                    (
                        _file_entry
                        for _file_entry in file_entries
                        if _file_entry.is_file()
                    ),
                    key=lambda _file_entry: _file_entry.name)

                for file_entry in norm_file_entries:
                    m = file_pattern.match(file_entry.name)

                    if m and i >= start:
                        # This is a valid match. Yield to the caller.
                        yield file_entry.path, dir_local_site, m
                        i += 1

    def _build_data_dir_path(
        self,
        stored_data_cls: Type[FileStoredDataMixin],
        *,
        local_site: Optional[LocalSite] = None,
    ) -> str:
        """Return a path to a data file.

        Args:
            stored_data_cls (type):
                The stored data class representing files to iterate through.

            local_site (reviewboard.site.models.LocalSite, optional):
                An optional Local Site for the data directory.
        """
        path = self.storage_path

        if local_site:
            path = safe_join(path, 'sites', local_site.name)

        return os.path.join(path, stored_data_cls.storage_dir)

    def _build_data_file_path(
        self,
        *,
        stored_data_cls: Type[FileStoredDataMixin],
        filename: str,
        local_site: Optional[LocalSite] = None,
        create_parents_if_missing: bool = False,
        if_exists: bool = False,
    ) -> Optional[str]:
        """Return a path to a data file.

        Args:
            stored_data_cls (type):
                The stored data class representing files to iterate through.

            filename (str):
                The filename to append to the data directory.

            local_site (reviewboard.site.models.LocalSite, optional):
                An optional Local Site for the data directory.

            create_parents_if_missing (bool, optional):
                Whether to create all parent directories to the file, if
                it does not already exist.

            if_exists (bool, optional):
                Whether to only return a result if the path exists.

        Returns:
            str:
            The resulting file path.

            This will be ``None`` if passing ``if_exists=True`` and the path
            does not exist.

        Raises:
            django.core.exceptions.SuspiciousFileOperation:
                One of the generated paths was outside of an expected
                directory.

            reviewboard.cert.errors.CertificateStorageError:
                There was an error creating parent directories.
        """
        assert filename
        validate_file_name(filename)

        data_path = self._build_data_dir_path(stored_data_cls,
                                              local_site=local_site)
        file_path = safe_join(data_path, filename)

        if if_exists and not os.path.exists(file_path):
            return None

        if create_parents_if_missing and not os.path.exists(data_path):
            try:
                os.makedirs(data_path, 0o700, exist_ok=True)
            except Exception as e:
                error_id = str(uuid4())
                logger.error('[%s] Error creating SSL/TLS data directory '
                             '"%s": %s',
                             error_id, data_path, e)

                raise CertificateStorageError(
                    _('Error creating SSL/TLS data storage directory. '
                      'Administrators can find details in the Review Board '
                      'server logs (error ID %(error_id)s).')
                    % {
                        'error_id': error_id,
                    })

        return file_path

    def _build_cert_file_path(
        self,
        *,
        hostname: str,
        port: int,
        ext: str,
        **kwargs,
    ) -> Optional[str]:
        """Return a path to a certificate file.

        Args:
            hostname (str):
                The hostname serving the certificate.

            port (int):
                The port on the host serving the certificate.

            ext (str):
                The extension for the filename.

            **kwargs (dict):
                Additional keyword arguments to pass to
                :py:meth:`_build_data_file_path`.

        Returns:
            str:
            The resulting certificate file path, or ``None`` if passing
            ``if_exists=True`` and the path does not exist.

        Raises:
            django.core.exceptions.SuspiciousFileOperation:
                One of the generated paths was outside of an expected
                directory.

            reviewboard.cert.errors.CertificateStorageError:
                There was an error creating parent directories.
        """
        return self._build_data_file_path(
            stored_data_cls=FileStoredCertificate,
            filename=self._build_host_filename(hostname=hostname,
                                               port=port,
                                               ext=ext),
            **kwargs)

    def _build_ca_bundle_file_path(
        self,
        *,
        name: str,
        **kwargs,
    ) -> Optional[str]:
        """Return a path to a CA bundle file.

        Args:
            name (str):
                The name of the bundle file.

                This must be in :term:`slug` format.

            **kwargs (dict):
                Additional keyword arguments to pass to
                :py:meth:`_build_data_file_path`.

        Returns:
            str:
            The resulting CA bundle file path, or ``None`` if passing
            ``if_exists=True`` and the path does not exist.

        Raises:
            django.core.exceptions.SuspiciousFileOperation:
                One of the generated paths was outside of an expected
                directory.

            reviewboard.cert.errors.CertificateStorageError:
                There was an error creating parent directories.
        """
        assert name == slugify(name)

        return self._build_data_file_path(
            stored_data_cls=FileStoredCertificateBundle,
            filename=f'{name}.pem',
            **kwargs)

    def _build_fingerprints_file_path(
        self,
        *,
        hostname: str,
        port: int,
        **kwargs,
    ) -> Optional[str]:
        """Return a path to a certificate fingerprints file.

        Args:
            hostname (str):
                The hostname serving the certificate.

            port (int):
                The port on the host serving the certificate.

            **kwargs (dict):
                Additional keyword arguments to pass to
                :py:meth:`_build_data_file_path`.

        Returns:
            str:
            The resulting certificate file path, or ``None`` if passing
            ``if_exists=True`` and the path does not exist.

        Raises:
            django.core.exceptions.SuspiciousFileOperation:
                One of the generated paths was outside of an expected
                directory.

            reviewboard.cert.errors.CertificateStorageError:
                There was an error creating parent directories.
        """
        return self._build_data_file_path(
            stored_data_cls=FileStoredCertificateFingerprints,
            filename=self._build_host_filename(hostname=hostname,
                                               port=port,
                                               ext='json'),
            **kwargs)

    def _build_host_filename(
        self,
        *,
        hostname: str,
        port: int,
        ext: str,
    ) -> str:
        """Return a base filename for a hostname, port, and extension.

        This will take care of normalizing wildcard hostnames to filenames.

        Args:
            hostname (str):
                The hostname for the certificate.

                This may be a wildcard hostname.

            port (int):
                The port for the certificate.

            ext (str):
                The file extension.

        Returns:
            str:
            The resulting filename.
        """
        if hostname.startswith('*'):
            return f'__{hostname[1:]}__{port}.{ext}'
        else:
            return f'{hostname}__{port}.{ext}'

    def _build_wildcard_hostname(
        self,
        hostname: str,
    ) -> str:
        """Return a wildcard hostname for a given hostname.

        This will strip off the leading name on the hostname and replace it
        with a wildcard. A hostname of ``test.example.com`` will be converted
        to ``*.example.com``.

        Args:
            hostname (str):
                The hostname to turn into a wildcard.

        Returns:
            str:
            The resulting wildcard hostname.
        """
        hostname = hostname.split('.', 1)[1]

        return f'*.{hostname}'

    def _build_stats_cache_key(
        self,
        *,
        local_site: AnyOrAllLocalSites,
    ) -> str:
        """Return a cache key for file-based storage stats.

        This will not be prefixed or normalized. It's expected to be passed
        to :py:func:`~djblets.cache.backend.cache_memoize` or
        to :py:func:`~djblets.cache.backend.make_cache_key`.

        Args:
            local_site (reviewboard.site.models.LocalSite or
                        reviewboard.site.models.LocalSite.ALL, optional):
                An optional LocalSite bound to the stats.

                If ``None``, the global site will be used.

        Returns:
            str:
            The resulting cached key.
        """
        key = 'stats-file-cert-storage'

        if local_site is None:
            key = f'{key}'
        elif local_site is LocalSite.ALL:
            key = f'{key}:local-site-all'
        else:
            key = f'{key}:local-site-{local_site.pk}'

        return key
