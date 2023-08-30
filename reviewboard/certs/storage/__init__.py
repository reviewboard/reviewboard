"""Storage backend support for SSL/TLS certificates.

Version Added:
    6.0
"""

from __future__ import annotations

from typing import cast

from djblets.registries.importer import lazy_import_registry

from reviewboard.certs.storage.registry import \
    CertificateStorageBackendRegistry


#: The registry managing available storage backends.
#:
#: Version Added:
#:     6.0
#:
#: Type:
#:     reviewboard.certs.storage.registry.CertificateStorageBackendRegistry
#:
cert_storage_backend_registry = cast(
    CertificateStorageBackendRegistry,
    lazy_import_registry('reviewboard.certs.storage.registry',
                         'CertificateStorageBackendRegistry'))
