"""Extension hook for registering a license provider.

Version Added:
    7.1
"""

from __future__ import annotations

from djblets.extensions.hooks import (BaseRegistryHook,
                                      ExtensionHookPoint)

from reviewboard.licensing.provider import BaseLicenseProvider
from reviewboard.licensing.registry import license_provider_registry


class LicenseProviderHook(BaseRegistryHook[BaseLicenseProvider],
                          metaclass=ExtensionHookPoint):
    """Extension hook for registering a license provider.

    Version Added:
        7.1
    """

    registry = license_provider_registry
