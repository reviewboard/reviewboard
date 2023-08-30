"""Certificate storage backend registry.

Version Added:
    6.0
"""

from __future__ import annotations

from typing import Iterator, Optional, Type

from django.utils.translation import gettext_lazy as _
from djblets.registries.registry import (ALREADY_REGISTERED,
                                         NOT_REGISTERED)

from reviewboard.registries.registry import Registry
from reviewboard.certs.storage.base import BaseCertificateStorageBackend


class CertificateStorageBackendRegistry(
    Registry[Type[BaseCertificateStorageBackend]]
):
    """Registry for managing certificate storage backends.

    By default, this includes the file-based storage backend. Extensions can
    register additional backends, which can then be activated for certificate
    storage management.

    Version Added:
        6.0
    """

    lookup_attrs = ('backend_id',)

    errors = {
        ALREADY_REGISTERED: _(
            '"%(item)s" is already a registered certificate storage backend.'
        ),
        NOT_REGISTERED: _(
            '"%(attr_value)s" is not a registered certificate storage backend.'
        ),
    }

    def get_backend(
        self,
        backend_id: str,
    ) -> Optional[Type[BaseCertificateStorageBackend]]:
        """Return a storage backend class with the given ID.

        Args:
            backend_id (str):
                The ID of the storage backend.

        Returns:
            type:
            The storage backend class, or ``None`` if not found.
        """
        return self.get('backend_id', backend_id)

    def get_defaults(self) -> Iterator[Type[BaseCertificateStorageBackend]]:
        """Return the default storage backend classes.

        Yields:
            type:
            Each default storage backend class.
        """
        from reviewboard.certs.storage.file_storage import \
            FileCertificateStorageBackend

        yield FileCertificateStorageBackend
