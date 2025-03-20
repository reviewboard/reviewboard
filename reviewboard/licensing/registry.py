"""Registry management for license providers.

Version Added:
    7.1
"""

from __future__ import annotations

from typing import Optional

from reviewboard.licensing.provider import BaseLicenseProvider
from reviewboard.registries.registry import OrderedRegistry


class LicenseProviderRegistry(OrderedRegistry[BaseLicenseProvider]):
    """A registry managing license providers.

    This is used to register new license providers and look them up by ID.

    Version Added:
        7.1
    """

    lookup_attrs = ('license_provider_id',)

    def get_license_provider(
        self,
        license_provider_id: str,
    ) -> Optional[BaseLicenseProvider]:
        """Return the license provider for a given ID.

        Args:
            license_provider_id (str):
                The ID of the license provider to return.

        Returns:
            reviewboard.licensing.provider.BaseLicenseProvider:
            The license provider matching the ID, or ``None`` if not found.
        """
        return self.get('license_provider_id', license_provider_id)


#: The registry managing license providers.
#:
#: Version Added:
#:     7.1
license_provider_registry = LicenseProviderRegistry()
