"""A hook for adding avatar services."""

from __future__ import annotations

from djblets.extensions.hooks import BaseRegistryHook, ExtensionHookPoint

from reviewboard.avatars import avatar_services


class AvatarServiceHook(BaseRegistryHook, metaclass=ExtensionHookPoint):
    """"A hook for adding avatar services.

    This hook will register services with the avatar services registry and
    unregister them when the hook is shut down.
    """

    registry = avatar_services

    def initialize(self, service):
        """Initialize the avatar service hook with the given service.

        Args:
            service (type):
                The avatar service class to register.

                This must be a subclass of
                :py:class:`djblets.avatars.services.base.AvatarService`.
        """
        super(AvatarServiceHook, self).initialize(service)
