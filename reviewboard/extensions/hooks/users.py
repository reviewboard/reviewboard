"""Hooks for working with user-related information.

Version Added:
    7.1
"""

from __future__ import annotations

from djblets.extensions.hooks import BaseRegistryHook, ExtensionHookPoint

from reviewboard.accounts.user_details import (BaseUserDetailsProvider,
                                               user_details_provider_registry)


class UserDetailsProviderHook(BaseRegistryHook[BaseUserDetailsProvider],
                              metaclass=ExtensionHookPoint):
    """Hook to register custom user detail providers.

    See :ref:`user-details-provider-hook` for instructions.

    Version Added:
        7.1
    """

    registry = user_details_provider_registry
